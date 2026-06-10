#!/usr/bin/env python3
"""Stage-shape study: utilitarian typologies under the visual-envelope rule.

RULE (replaces "low stage only"): a stage candidate is acceptable if its
roof, canopy, rigging, masts, storage, side walls or back-of-house mass
stays within the ALREADY-OBSTRUCTED sightline envelope (the NW rim/terrain
silhouette traced by scripts/obstruction_envelope.py), or if any NEW
obstruction is quantified and judged minor. Height is never a rejection
reason by itself.

Inputs
  analysis/in_situ_normalization/section_balance.json   audience frame
  analysis/stage_seating_decoupling/pareto_summary.json independent zone band
  scripts/obstruction_envelope.Envelope                 DEM ray tracer

Placements (all inside the independently-derived southern pan-toe band):
  P_inherited  the as-built front centre, axis 150 (tested, not assumed)
  P_lat        axis 150 kept (preserves the az-330 bay axis), front centre
               shifted laterally onto the audience-frame axis (~the
               stage-refit sweep's best feasible az150_lat-20)
  P_frame      axis turned to the audience-centroid bearing (audience-axis
               path; bay-axis deviation reported)

Typologies (each scored at P_lat; deck-only also at the other placements):
  T1 deck_only · T2 covered_civic (thin roof) · T3 acoustic_canopy (no back
  wall) · T4 asymmetric_utility (BOH tucked into the most-hidden upstage
  corner) · T5 movie_capable (removable masts; screen is night-only)
  T6 side_framed_acoustic (open upstage slot) · T7 hybrid (core + faceted
  apron + service canopy + corner BOH)

Per candidate: incremental obstruction by family (bay / treatment-cell
foreground / sky separately), frame fit, per-section stage-front→row-1,
cell clearance, pad volumes, operational scoring, constructability.

Outputs -> analysis/in_situ_normalization/stage_typology_scores.json,
STAGE_SHAPE_STUDY.md. EPSG:6494 · NAVD88 intl ft · planning-grade.
"""
import json
import math
import os

import numpy as np
from shapely.geometry import shape, Polygon, Point, LineString
from shapely.ops import unary_union
from shapely import affinity

import in_situ_common as C
from obstruction_envelope import Envelope

OUT = os.path.join(C.REPO, "analysis", "in_situ_normalization")
DECK_Z = (C.FOCUS_ELEV, C.FOCUS_ELEV + 1.0)
MINOR_BAY_PCT = 10.0      # new bay blockage above this (any family) = flagged
NO_MEANINGFUL_PCT = 2.0


def U(az):
    return C.U(az)


def rect(P, axis_az, w_half, u_from, u_to):
    """Rectangle in stage frame: u toward audience along axis_az, w lateral.
    u_from/u_to measured from the front centre P (positive toward audience)."""
    ux, uy = U(axis_az)
    wx, wy = U(axis_az + 90.0)
    c = []
    for uu, ww in ((u_from, -w_half), (u_from, w_half),
                   (u_to, w_half), (u_to, -w_half)):
        c.append((P[0] + ux * uu + wx * ww, P[1] + uy * uu + wy * ww))
    return Polygon(c)


def typologies(P, az, best_corner_w):
    """Each typology = list of (label, polygon, z_bot, z_top, solid_note)."""
    deck = ("deck", rect(P, az, 35.0, -34.0, 0.0), *DECK_Z, "deck slab")
    t = {}
    t["T1_deck_only"] = [deck]
    t["T2_covered_civic"] = [
        deck,
        ("roof", rect(P, az, 37.0, -36.0, 2.0),
         C.FOCUS_ELEV + 20.0, C.FOCUS_ELEV + 22.0,
         "thin roof slab on slender posts (posts <0.5 deg, not modelled)"),
    ]
    t["T3_acoustic_canopy"] = [
        deck,
        ("canopy", rect(P, az, 36.0, -34.0, -14.0),
         C.FOCUS_ELEV + 14.0, C.FOCUS_ELEV + 18.0,
         "curved acoustic canopy over the upstage half; open below; NO back wall"),
    ]
    t["T4_asymmetric_utility"] = [
        deck,
        ("boh", affinity.translate(rect(P, az, 12.0, -50.0, -34.0),
                                   xoff=U(az + 90)[0] * best_corner_w * 23.0,
                                   yoff=U(az + 90)[1] * best_corner_w * 23.0),
         C.FOCUS_ELEV, C.FOCUS_ELEV + 12.0,
         "24x16x12 back-of-house block tucked into the most-hidden upstage corner"),
    ]
    masts = []
    for s in (-1.0, 1.0):
        masts.append((f"mast_{'l' if s < 0 else 'r'}",
                      affinity.translate(rect(P, az, 1.0, -35.0, -33.0),
                                         xoff=U(az + 90)[0] * s * 33.0,
                                         yoff=U(az + 90)[1] * s * 33.0),
                      C.FOCUS_ELEV, C.FOCUS_ELEV + 26.0,
                      "removable screen mast (seasonal; screen itself is "
                      "night-only and not a permanent element)"))
    t["T5_movie_capable"] = [deck] + masts
    t["T6_side_framed_acoustic"] = [
        deck,
        ("wing_l", affinity.translate(rect(P, az, 1.0, -34.0, -14.0),
                                      xoff=U(az + 90)[0] * -36.0,
                                      yoff=U(az + 90)[1] * -36.0),
         C.FOCUS_ELEV, C.FOCUS_ELEV + 12.0, "solid side wing, lateral only"),
        ("wing_r", affinity.translate(rect(P, az, 1.0, -34.0, -14.0),
                                      xoff=U(az + 90)[0] * 36.0,
                                      yoff=U(az + 90)[1] * 36.0),
         C.FOCUS_ELEV, C.FOCUS_ELEV + 12.0, "solid side wing, lateral only"),
    ]
    t["T7_hybrid"] = [
        deck,
        ("apron", rect(P, az, 26.0, 0.0, 12.0), *DECK_Z,
         "faceted forecourt apron at deck level"),
        ("service_canopy", rect(P, az, 22.0, -32.0, -8.0),
         C.FOCUS_ELEV + 18.0, C.FOCUS_ELEV + 21.0,
         "overhead service/lighting canopy"),
        ("boh", affinity.translate(rect(P, az, 8.0, -46.0, -34.0),
                                   xoff=U(az + 90)[0] * best_corner_w * 27.0,
                                   yoff=U(az + 90)[1] * best_corner_w * 27.0),
         C.FOCUS_ELEV, C.FOCUS_ELEV + 10.0, "16x12x10 corner BOH"),
    ]
    return t


OPERATIONAL = {
    # deck_w, deck_d are filled per placement; scores 0-5 with stated basis
    "T1_deck_only": dict(
        wings=1, ceremony=4, concert=2, movie=2, rigging=0, weather=0,
        storage=0, acoustic=1,
        constructability=1,
        basis="bare 70x34 deck; PA/lighting fully temporary every event; no "
              "cover, no rig points, gear trucked per event"),
    "T2_covered_civic": dict(
        wings=2, ceremony=5, concert=4, movie=4, rigging=4, weather=4,
        storage=1, acoustic=3,
        constructability=3,
        basis="thin roof = rain-safe civic programming + permanent rig "
              "points; open all sides"),
    "T3_acoustic_canopy": dict(
        wings=2, ceremony=4, concert=4, movie=3, rigging=3, weather=2,
        storage=1, acoustic=4,
        basis="upstage canopy projects sound up the bowl without a back "
              "wall; partial rain cover",
        constructability=3),
    "T4_asymmetric_utility": dict(
        wings=3, ceremony=4, concert=3, movie=3, rigging=1, weather=1,
        storage=4, acoustic=2,
        basis="on-site storage/green room transforms operations; deck "
              "otherwise bare",
        constructability=2),
    "T5_movie_capable": dict(
        wings=1, ceremony=4, concert=3, movie=5, rigging=2, weather=0,
        storage=0, acoustic=1,
        basis="dedicated removable masts make movie night one-crew; masts "
              "double as PA points",
        constructability=2),
    "T6_side_framed_acoustic": dict(
        wings=4, ceremony=4, concert=4, movie=3, rigging=2, weather=1,
        storage=2, acoustic=4,
        basis="side wings give lateral reflection + true wing space; "
              "upstage slot stays open to the bay",
        constructability=2),
    "T7_hybrid": dict(
        wings=3, ceremony=5, concert=5, movie=4, rigging=4, weather=3,
        storage=3, acoustic=4,
        basis="performance core + apron for ceremonies + service canopy "
              "rig + corner BOH: the full utilitarian kit",
        constructability=4),
}


def main():
    C.verify_against_design()
    frame = json.load(open(os.path.join(
        OUT, "section_balance.json")))["audience_frame"]
    pareto = json.load(open(os.path.join(
        C.REPO, "analysis", "stage_seating_decoupling", "pareto_summary.json")))
    env = Envelope()

    treads = json.load(open(os.path.join(C.VEC_DIR,
                                         "terrace_treads.geojson")))["features"]
    row1 = {s: unary_union([shape(f["geometry"]) for f in treads
                            if f["properties"]["section"] == s
                            and f["properties"]["row"] == 1])
            for s in C.SECTIONS}
    zones = {}
    for f in json.load(open(os.path.join(C.VEC_DIR,
                                         "bowl_zones.geojson")))["features"]:
        zones.setdefault(f["properties"]["zone"], []).append(f)
    cell = shape(zones["treatment_cell_landscape"][0]["geometry"])
    corridor = shape(next(
        f for f in json.load(open(os.path.join(
            C.VEC_DIR, "site_context.geojson")))["features"]
        if f["properties"]["kind"] == "bay_view_corridor")["geometry"])

    acx, acy = frame["audience_centroid_seatweighted"]
    fx0, fy0 = frame["stage_front_centre"]
    ux, uy = U(C.STAGE_AX_AZ)
    wx, wy = U(C.STAGE_AX_AZ + 90.0)
    lat = frame["stage_lateral_offset_ft"]
    placements = {
        "P_inherited": dict(P=(fx0, fy0), az=C.STAGE_AX_AZ),
        "P_lat": dict(P=(fx0 + wx * lat, fy0 + wy * lat), az=C.STAGE_AX_AZ),
        "P_frame": dict(P=(fx0 + wx * lat * 0.5, fy0 + wy * lat * 0.5),
                        az=frame["centroid_bearing_from_stage_front_deg"]),
    }

    # precompute rays per station over the working sector
    az_grid = np.arange(255.0, 360.0, 1.0)
    rays = {}
    for st in env.stations:
        rays[(st["section"], st["band"])] = {
            az: env.trace(st, az) for az in az_grid}

    def placement_metrics(P, az):
        b_cent = (math.degrees(math.atan2(acx - P[0], acy - P[1]))) % 360.0
        mism = ((b_cent - az + 180) % 360) - 180
        vxx, vyy = acx - P[0], acy - P[1]
        uxx, uyy = U(az)
        lat_off = vxx * uyy - vyy * uxx
        deck = rect(P, az, 35.0, -34.0, 0.0)
        # downstage edge: the u=0 side of the rect (exterior ring points 2-3)
        front = LineString([deck.exterior.coords[2], deck.exterior.coords[3]])
        return dict(
            axis_mismatch_deg=round(mism, 1),
            lateral_offset_ft=round(lat_off, 1),
            front_to_row1_ft={s: round(row1[s].distance(front), 1)
                              for s in C.SECTIONS},
            cell_clearance_ft=round(deck.distance(cell), 1),
            deck_overlaps_cell=bool(deck.intersects(cell)),
        )

    def score_elements(elements):
        """Incremental obstruction vs the baseline envelope, per family.

        Area-weighted: blocked angular degrees are summed over ALL rays of
        the family's stations and divided by the total visible degrees, so a
        narrow mast that kills three rays reads as a small share of the bay,
        not "100% of the rays it crosses". Foreground (cell) blockage uses
        the RAW element band — the rim behind the cell cannot hide a mass
        standing in front of it."""
        out = {}
        for sec in C.SECTIONS:
            bay_blk = bay_tot = cell_blk = cell_tot = 0.0
            sky_sum, n_rays, n_cross = 0.0, 0, 0
            for band in ("front", "mid", "upper"):
                st = next(s for s in env.stations
                          if s["section"] == sec and s["band"] == band)
                for az in az_grid:
                    ray = rays[(sec, band)][az]
                    if ray is None:
                        continue
                    n_rays += 1
                    if ray["bay_band"]:
                        bay_tot += ray["bay_band"][1] - ray["bay_band"][0]
                    if ray["cell_band"]:
                        cell_tot += ray["cell_band"][1] - ray["cell_band"][0]
                    ex, ey = U(az)
                    rline = LineString(
                        [(st["x"] + ex * 6, st["y"] + ey * 6),
                         (st["x"] + ex * 760, st["y"] + ey * 760)])
                    bands = []
                    for label, poly, zb, zt, note in elements:
                        hit = rline.intersection(poly)
                        if hit.is_empty:
                            continue
                        pts = []
                        for g in getattr(hit, "geoms", [hit]):
                            pts += list(g.coords)
                        d0 = min(math.hypot(px - st["x"], py - st["y"])
                                 for px, py in pts)
                        bands.append((
                            math.degrees(math.atan2(zb - st["eye"], d0)),
                            math.degrees(math.atan2(zt - st["eye"], d0)),
                            d0))
                    if not bands:
                        continue
                    n_cross += 1
                    skyline = max(ray["sil"],
                                  ray["horizon"] if ray["bay_band"] else -90.0)
                    bay_f = cell_f = sky_d = 0.0
                    for lo, hi, d0 in bands:
                        if ray["bay_band"]:
                            blo, bhi = ray["bay_band"]
                            bay_f = max(bay_f, max(
                                0.0, min(hi, bhi) - max(lo, blo)))
                        if ray["cell_band"]:
                            clo, chi, dcn, dcf = ray["cell_band"]
                            if dcn > d0:   # cell lies beyond the element
                                cell_f = max(cell_f, max(
                                    0.0, min(hi, chi) - max(lo, clo)))
                        sky_d = max(sky_d, max(0.0, hi - max(skyline, lo)))
                    bay_blk += bay_f
                    cell_blk += cell_f
                    sky_sum += sky_d
            out[sec] = dict(
                rays_total=n_rays,
                rays_crossing=n_cross,
                new_bay_blocked_pct=round(100 * bay_blk / bay_tot, 1)
                if bay_tot > 0 else 0.0,
                new_cell_blocked_pct=round(100 * cell_blk / cell_tot, 1)
                if cell_tot > 0 else 0.0,
                new_sky_blocked_deg_mean=round(sky_sum / n_rays, 3)
                if n_rays else 0.0,
            )
        return out

    # P_opt: constrained search — keep the az-150 bay axis, slide laterally
    # toward the frame and pull the deck upstage until every family keeps a
    # workable orchestra gap. (The naive full-shift P_lat touches east row 1;
    # P_frame touches south row 1 — the row-1 pocket forbids a clean zero.)
    # This is canon Rule 9 path 3 territory: residuals are declared, not hidden.
    placements_search = []
    for s in (np.arange(0.0, lat - 0.01, -0.5) if lat < 0 else [0.0]):
        for t in np.arange(0.0, 14.01, 0.5):
            P = (fx0 + wx * s - ux * t, fy0 + wy * s - uy * t)
            m = placement_metrics(P, C.STAGE_AX_AZ)
            min_gap = min(m["front_to_row1_ft"].values())
            if min_gap >= 12.0 and m["cell_clearance_ft"] >= 15.0 \
                    and not m["deck_overlaps_cell"]:
                placements_search.append((abs(m["lateral_offset_ft"]),
                                          float(s), float(t), P))
    if placements_search:
        _, s_opt, t_opt, P_opt = min(placements_search)
        placements["P_opt"] = dict(P=P_opt, az=C.STAGE_AX_AZ)

    # axis comparison: deck-only at all placements
    axis_table = {name: placement_metrics(**pl)
                  for name, pl in placements.items()}
    sel_name = "P_opt" if "P_opt" in placements else "P_lat"
    sel = placements[sel_name]

    # most-hidden upstage corner for BOH typologies: trace both corners
    corner_scores = {}
    for s in (-1.0, 1.0):
        test = [("probe",
                 affinity.translate(rect(sel["P"], sel["az"], 12.0, -50.0, -34.0),
                                    xoff=U(sel["az"] + 90)[0] * s * 23.0,
                                    yoff=U(sel["az"] + 90)[1] * s * 23.0),
                 C.FOCUS_ELEV, C.FOCUS_ELEV + 12.0, "")]
        sc = score_elements(test)
        corner_scores[s] = sum(v["new_bay_blocked_pct"]
                               + v["new_sky_blocked_deg_mean"]
                               for v in sc.values())
    best_corner = min(corner_scores, key=corner_scores.get)

    results = {}
    for name, elements in typologies(sel["P"], sel["az"], best_corner).items():
        obs = score_elements(elements)
        worst_bay = max(v["new_bay_blocked_pct"] for v in obs.values())
        worst_cell = max(v["new_cell_blocked_pct"] for v in obs.values())
        if worst_bay > MINOR_BAY_PCT:
            verdict = (f"FLAGGED — {worst_bay}% of a family's visible bay "
                       "band newly blocked; redesign the offending mass or "
                       "justify explicitly (NOT a height rejection)")
        elif worst_cell > 35.0:
            verdict = (f"ACCEPTABLE w/ CAVEAT — bay clear (≤{worst_bay}%) but "
                       f"{worst_cell}% of a family's treatment-cell foreground "
                       "newly blocked; relocate the mass or accept the meadow "
                       "loss for that family explicitly")
        elif worst_bay <= NO_MEANINGFUL_PCT:
            verdict = "ACCEPTABLE — no meaningful new bay obstruction"
        else:
            verdict = ("ACCEPTABLE (minor) — new bay obstruction quantified "
                       f"at ≤{worst_bay}% of the visible band")
        opaque_upstage = any("wall" in lbl and poly.intersects(corridor)
                             for lbl, poly, *_ in elements)
        op = dict(OPERATIONAL[name])
        op_total = sum(v for k, v in op.items()
                       if k not in ("basis", "constructability"))
        results[name] = dict(
            elements=[dict(label=l, z_bottom=zb, z_top=zt,
                           height_ft=round(zt - C.FOCUS_ELEV, 1), note=nt)
                      for l, p, zb, zt, nt in elements],
            incremental_obstruction=obs,
            worst_new_bay_pct=worst_bay,
            worst_new_cell_pct=worst_cell,
            opaque_wall_in_bay_corridor=opaque_upstage,
            operational=op,
            operational_total=op_total,
            verdict=verdict,
            non_negotiables=dict(
                full_enclosure=False, permanent_fly_tower=False,
                permanent_water=False,
                acoustic_claim="qualitative plausibility only — no shell "
                               "performance claim",
            ),
        )

    payload = dict(
        generated_by="scripts/stage_shape_study.py",
        governing_scheme=C.GOVERNING_SCHEME,
        visual_envelope_rule=(
            "mass hiding below the terrain silhouette behind it adds no "
            "obstruction; new bay/cell/sky blockage is measured per family; "
            f"bay ≤{NO_MEANINGFUL_PCT}% none / ≤{MINOR_BAY_PCT}% minor / "
            "above = flagged-not-height-rejected"),
        frame_source=dict(
            file="analysis/in_situ_normalization/section_balance.json",
            audience_centroid=frame["audience_centroid_seatweighted"]),
        independent_zone_test=dict(
            file="analysis/stage_seating_decoupling/pareto_summary.json",
            co_leader_band=pareto["co_leaders_within_0p02"],
            inherited_in_band=pareto["inherited_stage_in_co_leader_band"],
            note="placements lie inside the independently-derived southern "
                 "pan-toe zone band"),
        placement_axis_comparison=axis_table,
        selected_placement=dict(
            name=sel_name, front_centre=[round(sel["P"][0], 1),
                                         round(sel["P"][1], 1)],
            axis_az=sel["az"],
            reason="constrained search keeping the az-330 bay axis: slide "
                   "laterally toward the frame + pull upstage until every "
                   "family keeps a >=12 ft orchestra gap and >=15 ft cell "
                   "clearance — the row-1 pocket forbids zeroing the offset "
                   "(P_lat touches east row 1, P_frame touches south row 1); "
                   "residual offset declared per Rule 9 path 3"),
        boh_corner=("west/left" if best_corner < 0 else "east/right"),
        rule9_status="open — this study produces the tested candidate set "
                     "for the Rule 9 decision; it does not adopt one",
        typologies=results,
    )
    with open(os.path.join(OUT, "stage_typology_scores.json"), "w") as fh:
        json.dump(payload, fh, indent=1)

    md = ["# Stage shape study — utilitarian typologies under the "
          "visual-envelope rule", "",
          payload["visual_envelope_rule"], "",
          "## Placement (frame fit; deck-only)", "",
          "| placement | axis | mismatch° | lateral ft | front→row1 e/b/s ft | cell gap ft |",
          "|---|---|---|---|---|---|"]
    for n, m in axis_table.items():
        fr = m["front_to_row1_ft"]
        md.append(f"| {n} | {placements[n]['az']:.1f} | "
                  f"{m['axis_mismatch_deg']} | {m['lateral_offset_ft']} | "
                  f"{fr['east']}/{fr['bend']}/{fr['south']} | "
                  f"{m['cell_clearance_ft']} |")
    md += ["", f"Selected: **{sel_name}** — "
           + payload["selected_placement"]["reason"], "",
           "## Typologies at the selected placement", "",
           "| typology | max elem ft | worst new bay % | worst new cell % | "
           "op total /40 | constructability | verdict |",
           "|---|---|---|---|---|---|---|"]
    for n, r in results.items():
        hmax = max(e["height_ft"] for e in r["elements"])
        md.append(f"| {n} | {hmax:.0f} | {r['worst_new_bay_pct']} | "
                  f"{r['worst_new_cell_pct']} | {r['operational_total']} | "
                  f"{r['operational']['constructability']}/5 | "
                  f"{r['verdict'].split(' — ')[0]} |")
    md += ["", "Per-family bay/cell/sky increments, element lists, and "
           "operational bases: `stage_typology_scores.json`. The screen in "
           "T5 is night-only; masts are removable and scored standing.",
           "", "Rule 9 remains OPEN: this is the tested candidate set, "
           "not an adoption.", ""]
    with open(os.path.join(OUT, "STAGE_SHAPE_STUDY.md"), "w") as fh:
        fh.write("\n".join(md))
    print("  wrote analysis/in_situ_normalization/stage_typology_scores.json, "
          "STAGE_SHAPE_STUDY.md")
    for n, r in results.items():
        print(f"  {n:24s} bay {r['worst_new_bay_pct']:5.1f}%  cell "
              f"{r['worst_new_cell_pct']:5.1f}%  op {r['operational_total']:2d}"
              f"  {r['verdict'].split(' — ')[0]}")


if __name__ == "__main__":
    main()
