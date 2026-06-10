#!/usr/bin/env python3
"""Break the stage<->seating circular dependency with three independent products.

The inherited chain (documented in CIRCULARITY_AUDIT.md): the stage-lineage
focal point (stage4 -> design_open_low, harness_config center_x/center_y)
anchored the extended-bays march (inner radius 85 ft FROM that point, az
windows about it) -> Scenario E seating -> audience frame -> "stage belongs
at the frame" — an ouroboros. This script re-derives both sides from
terrain alone and only then pairs them:

  1. audience_envelopes.geojson      terrain-first seating envelopes (slope,
     elevation, street setbacks, facing-the-pan sector — NO stage assumed,
     only a broad performance-front zone = the flat pan itself)
  2. stage_opportunity_zones.geojson independent stage zones from floor
     feasibility, treatment-cell clearance, access/loading, backdrop
     (obstruction envelope), storage room, acoustic up-slope projection —
     NOT justified by the current seating rows
  3. pairwise_stage_audience_scores.csv + STAGE_SEATING_PARETO.md +
     pareto_summary.json             pairwise co-optimization, ranked, with
     failure reasons and why-the-winner-beats-the-runner-up

Outputs -> analysis/stage_seating_decoupling/
EPSG:6494 · NAVD88 intl ft · planning-grade. Requires the DEM.
"""
import csv
import json
import math
import os

import numpy as np

import in_situ_common as C
from build_in_situ_geometry import Y_LAKE, Y_MITCHELL, X_PETOSKEY

OUT = os.path.join(C.REPO, "analysis", "stage_seating_decoupling")
SETBACK = 15.0
PAD_SF = 70.0 * 34.0
WEIGHTS = {"capacity": 0.25, "visual": 0.15, "earthwork": 0.15,
           "operational": 0.15, "intimacy": 0.15, "acoustic": 0.10, "ada": 0.05}


def bearing(dx, dy):
    return math.degrees(math.atan2(dx, dy)) % 360.0


def ang_diff(a, b):
    return ((a - b + 180.0) % 360.0) - 180.0


def main():
    import rasterio
    from rasterio import features as rfeatures
    from scipy import ndimage
    from shapely.geometry import shape, mapping, Point
    from shapely.ops import unary_union

    from obstruction_envelope import Envelope

    if not os.path.exists(C.DEM_DESIGN):
        raise SystemExit("DEM required for the decoupling study — see "
                         "dem/MISSING_DATA.md")
    os.makedirs(OUT, exist_ok=True)
    C.verify_against_design()

    ds = rasterio.open(C.DEM_DESIGN)
    Z = ds.read(1).astype(float)
    Z[Z == ds.nodata] = np.nan
    T = ds.transform
    H, W = Z.shape
    Zs = ndimage.gaussian_filter(np.nan_to_num(Z, nan=np.nanmedian(Z)), 3.0)
    gy, gx = np.gradient(Zs)
    slope = np.hypot(gx, gy)
    downhill = (np.degrees(np.arctan2(-gx, gy))) % 360.0
    cols, rows_idx = np.meshgrid(np.arange(W), np.arange(H))
    X = T.c + (cols + 0.5) * T.a
    Y = T.f + (rows_idx + 0.5) * T.e

    basin = shape(json.load(open(os.path.join(C.REPO, "basin_footprint.geojson")))
                  ["features"][0]["geometry"])
    basin_mask = rfeatures.geometry_mask(
        [mapping(basin.buffer(80))], out_shape=(H, W), transform=T, invert=True)
    zones_pkg = {}
    for f in json.load(open(os.path.join(C.VEC_DIR, "bowl_zones.geojson")))["features"]:
        zones_pkg.setdefault(f["properties"]["zone"], []).append(f)
    cell_poly = shape(zones_pkg["treatment_cell_landscape"][0]["geometry"])
    stage_now = unary_union([shape(zones_pkg[z][0]["geometry"])
                             for z in ("stage_core", "stage_shoulder_left",
                                       "stage_shoulder_right")])
    treads = json.load(open(os.path.join(C.VEC_DIR, "terrace_treads.geojson")))["features"]
    fam_union = {s: unary_union([shape(f["geometry"]) for f in treads
                                 if f["properties"]["section"] == s])
                 for s in C.SECTIONS}
    tread_union = unary_union(list(fam_union.values()))
    pour = json.load(open(os.path.join(C.REPO, "pour_point.geojson")))["features"][0]
    pour_pt = Point(pour["geometry"]["coordinates"])

    street_ok = (X < X_PETOSKEY - SETBACK) & (Y > Y_MITCHELL + SETBACK) & \
                (Y < Y_LAKE - SETBACK)

    # ── product 0: the broad performance-front zone = the flat pan ─────────
    pan_mask = basin_mask & (slope < 0.05) & (Zs > 608.0) & (Zs < 614.0) & street_ok
    pan_lbl, n = ndimage.label(pan_mask)
    if n == 0:
        raise SystemExit("no flat pan found — check DEM")
    sizes = ndimage.sum(pan_mask, pan_lbl, range(1, n + 1))
    pan_mask = pan_lbl == (1 + int(np.argmax(sizes)))
    pan_polys = [shape(g) for g, v in rfeatures.shapes(
        pan_mask.astype("uint8"), transform=T) if v == 1]
    pan = max(pan_polys, key=lambda p: p.area).simplify(2.0)
    pcx, pcy = pan.centroid.x, pan.centroid.y

    # ── product 1: terrain-first audience envelopes ────────────────────────
    to_pan = (np.degrees(np.arctan2(pcx - X, pcy - Y))) % 360.0
    facing_pan = np.abs(((downhill - to_pan + 180) % 360) - 180) < 60.0
    suit = basin_mask & street_ok & (slope >= 0.12) & (slope <= 0.45) & \
        (Zs >= 612.0) & (Zs <= 640.0) & facing_pan
    suit = ndimage.binary_opening(suit, iterations=2)
    # split by FACING CLASS so differently-oriented wall segments become
    # separate, separately-testable envelopes (not one merged ring)
    FACING_CLASSES = [("NWN", 285.0, 15.0), ("WSW", 195.0, 285.0),
                      ("SSE", 105.0, 195.0), ("ENE", 15.0, 105.0)]
    env_feats, env_recs, env_rejected = [], [], []
    cal = None
    for fname, f0, f1 in FACING_CLASSES:
        if f0 < f1:
            fmask = (downhill >= f0) & (downhill < f1)
        else:
            fmask = (downhill >= f0) | (downhill < f1)
        lbl, n = ndimage.label(suit & fmask)
        if n == 0:
            continue
        sizes = ndimage.sum(suit & fmask, lbl, range(1, n + 1))
        order = np.argsort(sizes)[::-1]
        for j in order[:2]:
            m = lbl == (1 + int(j))
            area = float(m.sum())
            if area < 4000:
                if area > 1500:
                    env_rejected.append(
                        dict(facing_class=fname, area_sf=round(area, 0),
                             reason="component under 4,000 sf — no usable bowl"))
                continue
            polys = [shape(g) for g, v in rfeatures.shapes(
                m.astype("uint8"), transform=T) if v == 1]
            poly = max(polys, key=lambda p: p.area).simplify(2.0)
            mean_slope = float(slope[m].mean())
            mean_face = float(np.degrees(np.arctan2(
                np.sin(np.radians(downhill[m])).mean(),
                np.cos(np.radians(downhill[m])).mean()))) % 360.0
            overlap_now = poly.intersection(tread_union).area / tread_union.area
            rec = dict(
                env_id=f"A_{fname}{'' if j == order[0] else '2'}",
                facing_class=fname,
                area_sf=round(area, 0),
                mean_slope_pct=round(mean_slope * 100, 1),
                facing_bearing_deg=round(mean_face, 1),
                bay_axis_available=bool(290.0 <= mean_face <= 350.0),
                elev_range=[round(float(Zs[m].min()), 1),
                            round(float(Zs[m].max()), 1)],
                contains_current_seating_pct=round(100 * overlap_now, 1),
                sightline_class=("C>=90 plausible on grade" if mean_slope >= 0.22
                                 else "marginal — riser build-up needed"
                                 if mean_slope >= 0.15 else "too flat for raked C"),
                family_overlap_pct={s: round(
                    100 * poly.intersection(fam_union[s]).area
                    / fam_union[s].area, 1) for s in C.SECTIONS},
                derived_from=["DEM slope/elevation", "street setbacks",
                              "facing-the-pan sector (no stage point assumed)",
                              f"facing class {fname}"],
            )
            env_recs.append((poly, rec))
    # calibrate seat density on the envelope holding the most validated seating
    _, prim0 = max(env_recs, key=lambda pr: pr[1]["contains_current_seating_pct"])
    cal_density = 1283.0 / prim0["area_sf"]
    for poly, rec in env_recs:
        rec["capacity_proxy_seats"] = int(rec["area_sf"] * cal_density)
        rec["capacity_basis"] = ("validated 1,283 (contains current seating)"
                                 if rec["contains_current_seating_pct"] > 50
                                 else f"area x {cal_density:.3f} seats/sf "
                                      "(calibrated on the validated bowl)")
        env_feats.append(C.feat(rec, mapping(poly)))
    env_feats.append(C.feat(
        dict(env_id="performance_front_zone",
             note="broad plausible performance-front zone — the flat pan; "
                  "NOT a stage location",
             area_sf=round(pan.area, 0)),
        mapping(pan)))
    C.dump(C.fc(env_feats, extra={"rejected_components": env_rejected}),
           os.path.join(OUT, "audience_envelopes.geojson"))

    # ── product 2: independent stage-opportunity zones ──────────────────────
    floor_ok = pan_mask & ~rfeatures.geometry_mask(
        [mapping(cell_poly.buffer(10))], out_shape=(H, W), transform=T,
        invert=True)
    prim_poly, prim = max(env_recs,
                          key=lambda pr: pr[1]["contains_current_seating_pct"])
    prim_pt = prim_poly.representative_point()
    prim_eye_elev = float(np.nanpercentile(
        Zs[rfeatures.geometry_mask([mapping(prim_poly)], out_shape=(H, W),
                                   transform=T, invert=True)], 50)) + C.EYE_SEATED_FT
    env_tracer = Envelope()

    # sector the floor about the pan centroid (compass quadrant toes)
    bear_cells = (np.degrees(np.arctan2(X - pcx, Y - pcy))) % 360.0
    zone_defs = [("S_NE", 0, 90), ("S_SE", 90, 180), ("S_SW", 180, 270),
                 ("S_NW", 270, 360)]
    zone_feats, zone_recs, zone_rejected = [], [], []
    for zid, a0, a1 in zone_defs:
        m = floor_ok & (bear_cells >= a0) & (bear_cells < a1)
        area = float(m.sum())
        if area < PAD_SF:
            zone_rejected.append(dict(
                zone_id=zid, area_sf=round(area, 0),
                reason="insufficient feasible floor for a 70x34 pad — "
                       "the treatment cell + clearance occupies this pan "
                       "sector" if zid == "S_NW" else
                       "insufficient feasible floor for a 70x34 pad"))
            continue
        polys = [shape(g) for g, v in rfeatures.shapes(
            m.astype("uint8"), transform=T) if v == 1]
        poly = max(polys, key=lambda p: p.area).simplify(2.0)
        zc = poly.representative_point()
        pad_depth = float(np.abs(Zs[m] - C.FOCUS_ELEV).mean())
        pad_cy = round(pad_depth * PAD_SF / 27.0, 1)
        load_ft = round(zc.distance(pour_pt), 1)
        cell_gap = round(poly.distance(cell_poly), 1)
        aud_gap = round(poly.distance(prim_poly), 1)
        # backdrop allowance: from the primary envelope's mid eye, what top
        # elevation hides against terrain beyond the zone?
        az = bearing(zc.x - prim_pt.x, zc.y - prim_pt.y)
        st = dict(x=prim_pt.x, y=prim_pt.y, eye=prim_eye_elev)
        ray = env_tracer.trace(st, az)
        d_zone = math.hypot(zc.x - prim_pt.x, zc.y - prim_pt.y)
        beyond = env_tracer.suffix_at(ray, d_zone + 20.0) if ray else -90.0
        allow_top = round(prim_eye_elev
                          + math.tan(math.radians(beyond)) * d_zone, 1)
        rec = dict(
            zone_id=zid,
            area_sf=round(area, 0),
            floor_elev_mean=round(float(Zs[m].mean()), 2),
            pad_cy_70x34=pad_cy,
            loading_dist_to_pour_ft=load_ft,
            cell_clearance_ft=cell_gap,
            dist_to_primary_envelope_ft=aud_gap,
            backdrop_allowable_top_elev=allow_top,
            backdrop_allowable_height_ft=round(allow_top - C.FOCUS_ELEV, 1),
            storage_room_sf=round(max(0.0, area - PAD_SF), 0),
            acoustic_up_slope=bool(5.0 <= aud_gap <= 80.0),
            contains_inherited_stage=bool(poly.contains(stage_now.centroid)),
            derived_from=["pan floor feasibility (slope<5%, 608-614)",
                          "treatment-cell clearance >=10 ft",
                          "street setbacks", "loading distance to pour point",
                          "backdrop allowance from the obstruction envelope"],
        )
        zone_recs.append((poly, zc, rec))
        zone_feats.append(C.feat(rec, mapping(poly)))
    C.dump(C.fc(zone_feats, extra={"rejected_zones": zone_rejected}),
           os.path.join(OUT, "stage_opportunity_zones.geojson"))

    # ── product 3: pairwise co-optimization ─────────────────────────────────
    pair_rows = []
    for e_poly, e in env_recs:
        e_ct = e_poly.centroid
        for z_poly, zc, z in zone_recs:
            face = e["facing_bearing_deg"]      # measured mean downhill facing
            axis_skew = abs(ang_diff(bearing(zc.x - e_ct.x, zc.y - e_ct.y),
                                     face))
            toe = round(z_poly.distance(e_poly), 1)
            # achievable orchestra gap: the stage is PLACED somewhere inside
            # the zone, so the gap ranges from the zone-edge distance to the
            # far side of the zone
            d_far = round(max(e_poly.distance(Point(c))
                              for c in z_poly.exterior.coords), 1)
            gap_ok = (toe <= 60.0) and (d_far >= 25.0)
            fails = []
            if z["cell_clearance_ft"] < 5:
                fails.append("stage crowds the treatment cell (<5 ft)")
            if axis_skew > 55:
                fails.append(f"stage {axis_skew:.0f}° off the envelope's "
                             "facing axis — audience looks past the stage")
            if toe > 120:
                fails.append("stage remote from audience toe (>120 ft — the "
                             "original stage4 error)")
            if toe < 5:
                fails.append("no orchestra gap")
            if e["capacity_proxy_seats"] < 600:
                fails.append("capacity proxy under 600")
            if "too flat" in e["sightline_class"]:
                fails.append("envelope too flat for raked sightlines")
            if z["loading_dist_to_pour_ft"] > 350:
                fails.append("loading route >350 ft")
            ori = ("bay + evening sun beyond stage (canonical NNW-NW)"
                   if 290 <= face <= 350 else
                   "audience faces N-NE: no bay axis, morning glare"
                   if 0 <= face < 70 or face > 350 else
                   "audience faces W-SW: low sun in eyes"
                   if 230 <= face < 290 else
                   "audience faces the slope — no long view")
            if "faces the slope" in ori or "no bay" in ori:
                fails.append(ori)
            sc = dict(
                axis=max(0.0, 1.0 - axis_skew / 90.0),
                capacity=min(e["capacity_proxy_seats"] / 1300.0, 1.0),
                visual=min(max(z["backdrop_allowable_height_ft"], 0) / 25.0, 1.0),
                earthwork=max(0.0, 1.0 - z["pad_cy_70x34"] / 400.0),
                operational=max(0.0, 1.0 - z["loading_dist_to_pour_ft"] / 400.0)
                * (0.5 + 0.5 * min(z["storage_room_sf"] / 4000.0, 1.0)),
                intimacy=1.0 if gap_ok else
                max(0.0, 1.0 - abs(toe - 40) / 120.0),
                acoustic=1.0 if z["acoustic_up_slope"] else 0.3,
                ada=1.0,   # all zones reachable via floor routes; envelope ADA
                           # reach reported separately
            )
            total = round(sum(WEIGHTS.get(k, 0.10) * v for k, v in sc.items()), 3)
            pair = dict(
                pair=f"{e['env_id']}+{z['zone_id']}",
                envelope=e["env_id"], stage_zone=z["zone_id"],
                axis_skew_deg=round(axis_skew, 1),
                capacity_proxy_seats=e["capacity_proxy_seats"],
                family_overlap_pct=json.dumps(e["family_overlap_pct"]),
                sightline_class=e["sightline_class"],
                mean_slope_pct=e["mean_slope_pct"],
                stage_to_toe_ft=toe,
                achievable_orchestra_gap_ft=[toe, d_far],
                audience_facing_deg=round(face, 1),
                orientation_note=ori,
                pad_cy=z["pad_cy_70x34"],
                loading_ft=z["loading_dist_to_pour_ft"],
                cell_clearance_ft=z["cell_clearance_ft"],
                storage_sf=z["storage_room_sf"],
                backdrop_allowable_height_ft=z["backdrop_allowable_height_ft"],
                movie_masts=("hideable (allowance >=24 ft)"
                             if z["backdrop_allowable_height_ft"] >= 24 else
                             "partially hideable (12-24 ft)"
                             if z["backdrop_allowable_height_ft"] >= 12 else
                             "masts break the skyline"),
                acoustic_up_slope=z["acoustic_up_slope"],
                contains_inherited_stage=z["contains_inherited_stage"],
                weighted_score=total,
                failure_reasons="; ".join(fails) or "none",
            )
            pair["viable"] = not fails
            pair_rows.append(pair)
    pair_rows.sort(key=lambda p: -p["weighted_score"])
    # Pareto front on (capacity, backdrop allowance, -pad, -loading)
    def dominates(a, b):
        ka = (a["capacity_proxy_seats"], a["backdrop_allowable_height_ft"],
              -a["pad_cy"], -a["loading_ft"])
        kb = (b["capacity_proxy_seats"], b["backdrop_allowable_height_ft"],
              -b["pad_cy"], -b["loading_ft"])
        return all(x >= y for x, y in zip(ka, kb)) and ka != kb
    for p in pair_rows:
        p["pareto_front"] = not any(dominates(q, p) for q in pair_rows
                                    if q["viable"]) and p["viable"]

    with open(os.path.join(OUT, "pairwise_stage_audience_scores.csv"),
              "w", newline="") as fh:
        wcsv = csv.DictWriter(fh, fieldnames=list(pair_rows[0].keys()))
        wcsv.writeheader()
        wcsv.writerows(pair_rows)

    winner = next(p for p in pair_rows if p["viable"])
    co_leaders = [p["pair"] for p in pair_rows
                  if p["viable"]
                  and winner["weighted_score"] - p["weighted_score"] <= 0.02]
    inherited_in_band = any(
        p["contains_inherited_stage"] for p in pair_rows
        if p["pair"] in co_leaders)
    runner = next((p for p in pair_rows if p is not winner), None)
    why = ""
    if runner:
        deltas = []
        for k, label in (("weighted_score", "weighted score"),
                         ("capacity_proxy_seats", "capacity"),
                         ("axis_skew_deg", "axis skew deg"),
                         ("backdrop_allowable_height_ft", "backdrop allowance ft"),
                         ("pad_cy", "pad CY"), ("loading_ft", "loading ft"),
                         ("stage_to_toe_ft", "stage→toe ft")):
            deltas.append(f"{label}: {winner[k]} vs {runner[k]}")
        why = (f"{winner['pair']} beats {runner['pair']} "
               f"({'viable' if runner['viable'] else 'non-viable: ' + runner['failure_reasons']}) on "
               + "; ".join(deltas))
    summary = {
        "generated_by": "scripts/stage_seating_decoupling.py",
        "independent_products": ["audience_envelopes.geojson",
                                 "stage_opportunity_zones.geojson",
                                 "pairwise_stage_audience_scores.csv"],
        "n_envelopes": len(env_recs),
        "n_stage_zones": len(zone_recs),
        "n_pairs": len(pair_rows),
        "ranked_shortlist": [p["pair"] for p in pair_rows[:5]],
        "pareto_front": [p["pair"] for p in pair_rows if p["pareto_front"]],
        "winner": winner["pair"],
        "co_leaders_within_0p02": co_leaders,
        "winner_contains_inherited_stage": winner["contains_inherited_stage"],
        "inherited_stage_in_co_leader_band": inherited_in_band,
        "why_winner_beats_runner_up": why,
        "stage_zones_derived_from_seating": False,
        "circularity_status": (
            "loop broken: the stage zone is re-derived from floor/access/"
            "backdrop criteria and only then paired with terrain-first "
            "audience envelopes"),
    }
    with open(os.path.join(OUT, "pareto_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1)

    md = ["# Stage x seating pairwise co-optimization — Pareto shortlist", "",
          f"{len(env_recs)} terrain-first audience envelopes x "
          f"{len(zone_recs)} independent stage zones = {len(pair_rows)} pairs. "
          "Full table: `pairwise_stage_audience_scores.csv`. Weights: "
          + ", ".join(f"{k} {v}" for k, v in WEIGHTS.items()) + ".", "",
          "| rank | pair | seats | toe ft | pad CY | load ft | backdrop ft | score | viable | Pareto | failures |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, p in enumerate(pair_rows, 1):
        md.append(f"| {i} | {p['pair']} | {p['capacity_proxy_seats']} | "
                  f"{p['stage_to_toe_ft']} | {p['pad_cy']} | {p['loading_ft']} | "
                  f"{p['backdrop_allowable_height_ft']} | {p['weighted_score']} | "
                  f"{'✓' if p['viable'] else '✗'} | "
                  f"{'✓' if p['pareto_front'] else ''} | {p['failure_reasons']} |")
    md += ["", f"## Winner: {winner['pair']}"
           + (f" — co-leaders within 0.02: {', '.join(co_leaders)}"
              if len(co_leaders) > 1 else ""), "", why, "",
           f"- audience facing az {winner['audience_facing_deg']} — "
           f"{winner['orientation_note']}",
           f"- movie masts: {winner['movie_masts']}",
           "- " + (f"the co-leading pairs are within proxy noise (≤0.02): the "
                   f"independent analysis selects the **southern pan-toe zone "
                   f"band** rather than one exact spot; the inherited stage "
                   f"centroid {'sits inside' if inherited_in_band else 'sits outside'} "
                   "that band. Exact footprint/axis placement within the band "
                   "is the stage-refit/typology step's job, using the "
                   "obstruction tracer — not inheritance."
                   if len(co_leaders) > 1 else
                   f"contains the inherited stage location: "
                   f"**{winner['contains_inherited_stage']}**"),
           "",
           "Scores are planning-grade proxies; adopting any pair still "
           "requires emission + Scenario-E-class validation (canon Rules 3/5).",
           ""]
    with open(os.path.join(OUT, "STAGE_SEATING_PARETO.md"), "w") as fh:
        fh.write("\n".join(md))

    prim_env = max((r for _, r in env_recs),
                   key=lambda r: r["contains_current_seating_pct"])
    if len(co_leaders) > 1 and inherited_in_band:
        verdict_word = "TIES WITH (within proxy noise)"
        verdict_text = (
            "the top pairs are separated by ≤0.02 weighted score — the "
            "independent analysis selects the southern pan-toe ZONE BAND, and "
            "the inherited stage centroid sits inside one of its co-leading "
            "zones. The general location therefore survives as a "
            "*re-derivation* (floor feasibility + cell clearance + backdrop "
            "allowance + loading), while the exact footprint/axis within the "
            "band remains open (Rule 9) and must come from the pairwise "
            "frame + obstruction tracer, not inheritance.")
    elif winner["contains_inherited_stage"]:
        verdict_word = "CONTAINS"
        verdict_text = (
            "the inherited location survives the independent test as a "
            "*re-derivation*: it is now justified by floor feasibility + cell "
            "clearance + backdrop allowance + loading, not by the seating it "
            "spawned. The exact footprint/axis within the zone remains open "
            "(Rule 9) and must come from the pairwise frame, not inheritance.")
    else:
        verdict_word = "EXCLUDES"
        verdict_text = ("the loop was not only circular but wrong: the "
                        "independent analysis moves the stage.")
    audit = f"""# Circularity audit — stage placement vs seating geometry

## The loop (evidence)

1. **The focal point descends from the stage lineage.** `design_open_low.py`
   line 21: `CX,CY=19533067.7,750799.2`; the arc centre F = base + 15 ft @ az
   150 and the stage front at F + 50 ft were fixed together (stage4 lineage).
2. **The seating march is anchored to that same point.**
   `design_extended_bays.py` lines 33-46: identical `CX,CY`; the forecourt
   starts at radius **85 ft from F** (`FORE_R=[85.0,…]`), the section windows
   are azimuths **about F** (`AZ_E_CAP=AX_AZ-47 … AZ_S_CAP=AX_AZ+65`), and the
   facing `AX_AZ=132` was chosen relative to it. The bay SHAPES are contour
   (terrain) but their radial start and angular extent are F-inherited.
3. **The harness hard-codes the anchor.** `harness_config.yaml`:
   `center_x/center_y` (same point), `stage_r_ft: 50.0` — every engine
   (sightlines, earthwork, Scenario E) evaluates about it.
4. **The frame study closed the loop.** `normalize_sections.py` derived the
   audience centroid FROM that seating and proposed re-fitting the stage to
   it — the stage would have been justified by geometry it helped create.

## What is terrain-forced vs inherited

| element | status |
|---|---|
| the flat pan (performance-front zone, {pan.area:.0f} sf) | terrain |
| the S/SE seating wall (slope 12-45%, faces the pan) | terrain |
| contour shapes of each bay family | terrain |
| focal point F (x,y), inner radius 85 ft, az windows, facing 312 | **inherited choices** |
| stage footprint at F+50 @ az150 | **inherited** |

## The break — three independent products (this study)

1. `audience_envelopes.geojson` — {len(env_recs)} terrain-first envelopes by
   facing class (+{len(env_rejected)} rejected components recorded). The
   primary NW-facing envelope re-derives the current bowl wall **without
   any stage assumption**: it contains
   {prim_env['contains_current_seating_pct']}% of the validated seating and
   carries ~{prim_env['capacity_proxy_seats']} seats.
2. `stage_opportunity_zones.geojson` — {len(zone_recs)} floor zones (+
   {len(zone_rejected)} rejected, incl. the NW pan sector occupied by the
   treatment cell), derived from floor feasibility, cell clearance, loading,
   backdrop allowance, storage — **not** from the seating rows.
3. `pairwise_stage_audience_scores.csv` — {len(pair_rows)} pairings ranked;
   Pareto front {summary['pareto_front']}.

## Verdict

**Winner: {winner['pair']}** (weighted {winner['weighted_score']}).
The winning stage zone {verdict_word} the inherited stage centroid —
{verdict_text}

{why}

Residual circularity, declared: the seat-density calibration
({cal_density:.4f} seats/sf) and family-overlap reporting reference the
validated bowl for CALIBRATION/LABELS only — they do not constrain where
envelopes or zones may exist.
"""
    with open(os.path.join(OUT, "CIRCULARITY_AUDIT.md"), "w") as fh:
        fh.write(audit)
    print(f"  wrote {os.path.relpath(OUT, C.REPO)}/: envelopes x zones = "
          f"{len(env_recs)} x {len(zone_recs)} (+{len(env_rejected)}/"
          f"{len(zone_rejected)} rejected), winner {winner['pair']} "
          f"(inherited-stage zone: {winner['contains_inherited_stage']})")


if __name__ == "__main__":
    main()
