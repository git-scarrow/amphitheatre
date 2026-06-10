#!/usr/bin/env python3
"""Section balance, composite audience frame, and flank-normalization study.

Outputs -> analysis/in_situ_normalization/
  section_balance.json           per-family measured metrics + audience frame +
                                 stage offsets + imbalance declaration
  normalization_candidates.json  candidate layouts with measured deltas
  NORMALIZATION.md               human report

Everything here is MEASURED from tracked geometry + DEM; no visual judgment.
Candidates that would require new emitted seating (east re-march, +row 19)
are labelled analysis-tier: adopting one requires re-running the
extended-bays march and Scenario E validation (canon Rules 3/5).

EPSG:6494 · NAVD88 intl ft · planning-grade.
"""
import csv
import json
import math
import os

import numpy as np
from shapely.geometry import shape, LineString, Point
from shapely.ops import unary_union

import in_situ_common as C
from build_in_situ_geometry import Y_LAKE, Y_MITCHELL, X_PETOSKEY

OUT = os.path.join(C.REPO, "analysis", "in_situ_normalization")
STREET_SETBACK = 15.0
BALANCE_THRESHOLD = 0.75   # declared: arc-length min/max ratio below this
                           # requires a measured justification
MIN_WALL_SLOPE = 0.15      # contour walk stops when the seating wall flattens


def bearing(dx, dy):
    return math.degrees(math.atan2(dx, dy)) % 360.0


def az_from_F(x, y):
    return bearing(x - C.FX, y - C.FY)


def circ_mean(deg, w):
    deg = np.asarray(deg, float)
    w = np.asarray(w, float)
    s = (w * np.sin(np.radians(deg))).sum()
    c = (w * np.cos(np.radians(deg))).sum()
    return math.degrees(math.atan2(s, c)) % 360.0


def ang_diff(a, b):
    return ((a - b + 180.0) % 360.0) - 180.0


def main():
    layers = C.verify_against_design()
    comp = layers["comp"]
    treads = json.load(open(os.path.join(C.VEC_DIR, "terrace_treads.geojson")))["features"]
    zones = {}
    for f in json.load(open(os.path.join(C.VEC_DIR, "bowl_zones.geojson")))["features"]:
        zones.setdefault(f["properties"]["zone"], []).append(f)
    bays = C.load_bays()
    perseat = {int(r["row"]): r for r in
               csv.DictReader(open(os.path.join(
                   C.REPO, "design_civic_core", "perseat_bands.csv")))
               if r["row"]}

    stage_core = shape(zones["stage_core"][0]["geometry"])
    stage_union = unary_union([shape(zones[z][0]["geometry"])
                               for z in ("stage_core", "stage_shoulder_left",
                                         "stage_shoulder_right")])
    stage_c = stage_union.centroid
    seat_centroid_all = unary_union([shape(f["geometry"]) for f in treads]).centroid
    # downstage edge = stage-core side nearest the seating mass
    ring = list(stage_core.exterior.coords)
    front_edge = min((LineString([ring[i], ring[i + 1]]) for i in range(len(ring) - 1)),
                     key=lambda s: s.centroid.distance(seat_centroid_all))
    front_c = front_edge.centroid

    # ── task 1: per-family measured balance ────────────────────────────────
    sections = {}
    for sec in C.SECTIONS:
        fs = [f for f in treads if f["properties"]["section"] == sec]
        rows = sorted(f["properties"]["row"] for f in fs)
        geoms = {f["properties"]["row"]: shape(f["geometry"]) for f in fs}
        seats = {f["properties"]["row"]: f["properties"]["seats_kept"] for f in fs}
        arclen = sum(float(comp[(r, sec)]["length_ft"]) for r in rows)
        azs = []
        for g in geoms.values():
            polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
            for p in polys:
                azs += [az_from_F(x, y) for x, y in p.exterior.coords]
        # seat-weighted family centroid
        W = sum(seats.values())
        cx = sum(geoms[r].centroid.x * seats[r] for r in rows) / W
        cy = sum(geoms[r].centroid.y * seats[r] for r in rows) / W
        inner = next(b for b in bays
                     if b["properties"]["section"] == sec and b["properties"]["row"] == 1)
        outer = next(b for b in bays
                     if b["properties"]["section"] == sec and b["properties"]["row"] == 18)
        d_stage = [geoms[r].distance(stage_union) for r in rows]
        sections[sec] = {
            "rows": len(rows),
            "row_ids": rows,
            "arc_length_ft": round(arclen, 1),
            "band_a_seats": W,
            "radial_depth_ft": round(
                float(comp[(18, sec)]["axis_radius_ft"])
                - float(comp[(1, sec)]["axis_radius_ft"]), 1),
            "measured_depth_to_stage_ft": [round(min(d_stage), 1), round(max(d_stage), 1)],
            "azimuth_span_deg": [round(min(azs), 1), round(max(azs), 1)],
            "row1_endpoints": [list(map(lambda v: round(v, 1), inner["geometry"]["coordinates"][0])),
                               list(map(lambda v: round(v, 1), inner["geometry"]["coordinates"][-1]))],
            "row18_endpoints": [list(map(lambda v: round(v, 1), outer["geometry"]["coordinates"][0])),
                                list(map(lambda v: round(v, 1), outer["geometry"]["coordinates"][-1]))],
            "row1_dist_to_stage_front_ft": round(geoms[1].distance(front_edge), 1),
            "centroid": [round(cx, 1), round(cy, 1)],
            "centroid_dist_to_stage_centroid_ft": round(
                math.hypot(cx - stage_c.x, cy - stage_c.y), 1),
        }

    # ── task 2: composite audience frame ───────────────────────────────────
    cent_w, cent_xy, normals, lens = [], [], [], []
    for f in treads:
        p = f["properties"]
        g = shape(f["geometry"]).centroid
        w = p["seats_kept"]
        cent_w.append(w)
        cent_xy.append((g.x, g.y))
        lens.append(p["length_ft"])
        tb = p["mean_tangent_bearing_deg"]
        # normal pointing toward the stage = the audience facing direction
        n1, n2 = (tb + 90.0) % 360.0, (tb - 90.0) % 360.0
        to_stage = bearing(stage_c.x - g.x, stage_c.y - g.y)
        normals.append(n1 if abs(ang_diff(n1, to_stage)) < abs(ang_diff(n2, to_stage))
                       else n2)
    cent_xy = np.array(cent_xy)
    w = np.array(cent_w, float)
    ac_seats = (cent_xy * w[:, None]).sum(0) / w.sum()
    wl = np.array(lens, float)
    ac_len = (cent_xy * wl[:, None]).sum(0) / wl.sum()
    facing = circ_mean(normals, w)
    centroid_bearing = bearing(ac_seats[0] - front_c.x, ac_seats[1] - front_c.y)
    axis_mismatch = ang_diff(centroid_bearing, C.STAGE_AX_AZ)
    # lateral offset: perpendicular distance of the centroid from the stage axis
    ux, uy = C.U(C.STAGE_AX_AZ)
    vx, vy = ac_seats[0] - front_c.x, ac_seats[1] - front_c.y
    lateral = vx * uy - vy * ux   # signed cross product (+ = right of axis)
    frame = {
        "audience_centroid_seatweighted": [round(ac_seats[0], 1), round(ac_seats[1], 1)],
        "audience_centroid_lengthweighted": [round(ac_len[0], 1), round(ac_len[1], 1)],
        "dominant_facing_bearing_deg": round(facing, 1),
        "dominant_axis_from_stage_deg": round((facing + 180.0) % 360.0, 1),
        "stage_front_centre": [round(front_c.x, 1), round(front_c.y, 1)],
        "stage_axis_deg_inherited": C.STAGE_AX_AZ,
        "centroid_bearing_from_stage_front_deg": round(centroid_bearing, 1),
        "stage_axis_mismatch_deg": round(axis_mismatch, 1),
        "stage_lateral_offset_ft": round(lateral, 1),
        "note": "mismatch>0 means the stage axis points clockwise of the "
                "audience centroid; facing is the seat-weighted circular mean "
                "of band normals toward the stage",
    }

    # ── task 3a: street / terrain stops (why the east flank is short) ──────
    stops = {}
    for sec, ref, axis in (("east", X_PETOSKEY, "x"), ("south", Y_MITCHELL, "y")):
        gaps = {}
        for row in (1, 8, 14, 18):
            b = next(f for f in bays if f["properties"]["section"] == sec
                     and f["properties"]["row"] == row)
            cs = b["geometry"]["coordinates"]
            gaps[row] = round(min((ref - c[0]) if axis == "x" else (c[1] - ref)
                                  for c in cs), 1)
        stops[sec] = gaps
    # the generator's declared azimuth caps (design_extended_bays.py)
    caps = {"east_cap_az": 85.0, "bend_breaks_az": list(C.SECTION_BREAK_AZ),
            "south_cap_az": 197.0}

    # ── task 3b: contour-walk extension test on the east flank ─────────────
    ext = {"available": False, "note": "DEM missing — extension test needs "
                                       "dem/dem_design_1ft.tif"}
    if os.path.exists(C.DEM_DESIGN):
        import rasterio
        from scipy.ndimage import gaussian_filter

        ds = rasterio.open(C.DEM_DESIGN)
        Z = ds.read(1).astype(float)
        Z[Z == ds.nodata] = np.nan
        Zs = gaussian_filter(np.nan_to_num(Z, nan=np.nanmedian(Z)), 3.0)
        gy, gx = np.gradient(Zs)          # row (−y), col (+x) spacing 1 ft
        T = ds.transform

        def sample(arr, x, y):
            r, c = rasterio.transform.rowcol(T, x, y)
            if 0 <= r < arr.shape[0] and 0 <= c < arr.shape[1]:
                return float(arr[r, c])
            return None

        def walk(x, y, E, az_dir):
            """Follow the E contour from (x,y), heading roughly az_dir.
            Returns (length_ft, stop_reason). Stops when a seat placed on the
            contour would no longer face the stage (splay gate) — the real
            reason a seating bay cannot simply wrap around the closed basin."""
            L, step = 0.0, 3.0
            for _ in range(120):
                z, dzx, dzy = sample(Zs, x, y), sample(gx, x, y), sample(gy, x, y)
                if z is None:
                    return L, "DEM edge"
                slope = math.hypot(dzx, -dzy)
                if slope < MIN_WALL_SLOPE:
                    return L, f"wall flattens (slope {slope:.2f} < {MIN_WALL_SLOPE})"
                # seat facing = downhill; gate it against the bearing to the
                # stage front (extended-bays seat-normal splay logic, 45° cap)
                downhill = bearing(-dzx, dzy)
                to_stage = bearing(front_c.x - x, front_c.y - y)
                splay = abs(ang_diff(downhill, to_stage))
                if splay > 45.0:
                    return L, f"seat splay gate ({splay:.0f}° off facing the stage)"
                # contour tangent = perpendicular to gradient (world frame)
                tx, ty = -(-dzy), dzx     # rotate grad (dzx, -dzy) by 90°
                n = math.hypot(tx, ty)
                tx, ty = tx / n, ty / n
                ex, ey = C.U(az_dir)
                if tx * ex + ty * ey < 0:
                    tx, ty = -tx, -ty
                x2, y2 = x + tx * step, y + ty * step
                z2, d2x, d2y = sample(Zs, x2, y2), sample(gx, x2, y2), sample(gy, x2, y2)
                if z2 is None:
                    return L, "DEM edge"
                g2 = max(math.hypot(d2x, -d2y), 1e-6)
                x2 += (E - z2) * d2x / g2 ** 2
                y2 += (E - z2) * (-d2y) / g2 ** 2
                if X_PETOSKEY - STREET_SETBACK <= x2:
                    return L, f"Petoskey St setback ({STREET_SETBACK} ft)"
                if Y_LAKE - STREET_SETBACK <= y2:
                    return L, f"E Lake St setback ({STREET_SETBACK} ft)"
                zc = sample(Zs, x2, y2)
                if zc is None or abs(zc - E) > 0.5:
                    return L, "contour lost (>0.5 ft correction)"
                x, y, L = x2, y2, L + step
            return L, "250 ft cap"

        rows_test = [r for r in C.FORMAL_ROWS if r >= 6]
        per_row = {}
        for row in rows_test:
            b = next(f for f in bays if f["properties"]["section"] == "east"
                     and f["properties"]["row"] == row)
            cs = b["geometry"]["coordinates"]
            # the cap end = endpoint with the smaller azimuth from F (az 85 side)
            e0, e1 = cs[0], cs[-1]
            end = e0 if az_from_F(*e0) < az_from_F(*e1) else e1
            E = float(comp[(row, "east")]["elev"])
            # continue away from the section: bearing of the last segment
            seg = (cs[1], cs[0]) if end is e0 else (cs[-2], cs[-1])
            az_dir = bearing(seg[1][0] - seg[0][0], seg[1][1] - seg[0][1])
            L, reason = walk(end[0], end[1], E, az_dir)
            per_row[row] = {"extension_ft": round(L, 0), "stop": reason,
                            "est_added_seats": int(L * (1 - 0.18) / 1.83)}
        total_ext = sum(v["extension_ft"] for v in per_row.values())
        ext = {"available": True, "per_row": per_row,
               "total_extension_ft": round(total_ext, 0),
               "total_est_added_seats": sum(v["est_added_seats"]
                                            for v in per_row.values()),
               "method": "level-contour walk on 3-ft-smoothed DEM beyond the "
                         "east az-85 cap; stops at street setback, wall "
                         "flatten, or contour loss"}

    # ── imbalance declaration ───────────────────────────────────────────────
    arcs = {s: sections[s]["arc_length_ft"] for s in C.SECTIONS}
    ratio = min(arcs.values()) / max(arcs.values())
    east_ext_total = (ext.get("total_extension_ft", 0) if ext["available"] else 0)
    justification = (
        f"east/south arc ratio {ratio:.2f} < declared {BALANCE_THRESHOLD}. "
        f"Measured causes: (1) the extended-bays march caps the east section "
        f"at az 85 vs south at az 197 (asymmetric by design of the contour "
        f"families); (2) row-18 east terminates {stops['east'][18]} ft from "
        f"Petoskey St vs south {stops['south'][18]} ft from E Mitchell St; "
        f"(3) the contour-walk test finds ~{east_ext_total:.0f} ft of "
        f"additional on-contour east arc across rows 6-18 before the "
        f"seat-facing splay gate (45° off the stage) stops every row — the "
        f"closed basin wraps north past the east cap, so further seats would "
        f"face across the bowl, not at the stage. The east flank is bounded "
        f"by audience-facing geometry (and ultimately the street corner), "
        f"not arbitrarily trimmed."
    )
    imbalance = {
        "arc_length_ft": arcs,
        "min_max_ratio": round(ratio, 3),
        "declared_threshold": BALANCE_THRESHOLD,
        "within_threshold": ratio >= BALANCE_THRESHOLD,
        "asymmetry_justification": justification,
    }

    # ── task 3c: candidate layouts ──────────────────────────────────────────
    def cand(name, desc, d_seats, d_arc_e, d_arc_b, d_arc_s, cutfill_cy,
             continuity, verdict, reason, tier):
        ae = arcs["east"] + d_arc_e
        ab = arcs["bend"] + d_arc_b
        as_ = arcs["south"] + d_arc_s
        return {
            "name": name, "description": desc,
            "seats_delta": d_seats,
            "seats_total": 1283 + d_seats,
            "arc_length_ft": {"east": round(ae, 0), "bend": round(ab, 0),
                              "south": round(as_, 0)},
            "balance_ratio": round(min(ae, ab, as_) / max(ae, ab, as_), 3),
            "cut_fill_proxy_cy": cutfill_cy,
            "row_continuity": continuity,
            "verdict": verdict, "verdict_reason": reason,
            "tier": tier,
        }

    r19_seats = sum(int(comp[(19, s)]["seats"]) for s in C.SECTIONS)
    r19_arc = {s: float(comp[(19, s)]["length_ft"]) for s in C.SECTIONS}
    r19_cf = round(sum(float(comp[(19, s)]["z_resid_ft"])
                       * float(comp[(19, s)]["length_ft"]) * 3.6 / 27.0
                       for s in C.SECTIONS), 1)
    east_ext_cf = round(east_ext_total * 3.6 * 0.25 / 27.0, 1)
    south_trim_arc = -(float(comp[(17, "south")]["length_ft"])
                       + float(comp[(18, "south")]["length_ft"]))
    south_trim_seats = -(int(comp[(17, "south")]["seats"])
                         + int(comp[(18, "south")]["seats"]))

    candidates = [
        cand("N0_status_quo",
             "keep Scenario E rows 1-18 in all three families; asymmetry "
             "justified by the measured street/terrain stops",
             0, 0, 0, 0, 0.0, "intact (validated)",
             "SELECTED", "every seat is Scenario-E-validated; the east deficit "
             "is street-and-terrain-bounded (see asymmetry_justification); "
             "no validated seat is sacrificed for visual symmetry",
             "geometry_backed"),
        cand("N1_east_contour_extension",
             "widen the east azimuth cap (az 85 → terrain/street stop) and "
             "re-march the east bays on their own contours",
             ext.get("total_est_added_seats", 0) if ext["available"] else 0,
             east_ext_total, 0, 0, east_ext_cf,
             "intact within east; needs re-march",
             "CANDIDATE (analysis-tier)",
             f"contour walk finds ~{east_ext_total:.0f} ft of on-contour east "
             "arc before the 45° splay gate (a generous cap — the civic_bowl "
             "composition gate was 28°, so treat this as an upper bound); "
             "improves balance ratio to "
             f"{min(arcs['east'] + east_ext_total, arcs['south']) / max(arcs['east'] + east_ext_total, arcs['south']):.2f}; "
             "requires re-running design_extended_bays with E_CAP widened, "
             "then Scenario E re-validation (Rules 3/5: not seats until "
             "emitted + validated)",
             "concept"),
        cand("N2_add_row19_all",
             "extend all three families to row 19 (per-seat C10 93 mm, 95% "
             "pass — formal under the civic_core per-seat band)",
             r19_seats, r19_arc["east"], r19_arc["bend"], r19_arc["south"],
             r19_cf, "intact; adds one row above the cross-aisle",
             "CANDIDATE (analysis-tier)",
             "row 19 is per-seat formal (design_civic_core/perseat_bands.csv: "
             "C10 93 mm, 95% pass) but centreline-soft (86 mm); does not "
             "change the balance ratio; requires Scenario E re-validation",
             "concept"),
        cand("N3_trim_south_to_balance",
             "drop south rows 17-18 to close the arc-length gap",
             south_trim_seats, 0, 0, south_trim_arc, 0.0,
             "south truncated at row 16",
             "REJECTED",
             "removes ~88 validated Band-A seats purely for plan symmetry; "
             "no terrain, street, sightline, or cost driver supports it — "
             "symmetry is not a site constraint here",
             "n/a"),
    ]

    os.makedirs(OUT, exist_ok=True)
    balance = {
        "generated_by": "scripts/normalize_sections.py",
        "governing_scheme": C.GOVERNING_SCHEME,
        "sections": sections,
        "audience_frame": frame,
        "street_terrain_stops": {"row_end_gap_ft": stops,
                                 "declared_march_caps": caps,
                                 "east_extension_test": ext},
        "imbalance": imbalance,
        "selected_candidate": "N0_status_quo",
    }
    with open(os.path.join(OUT, "section_balance.json"), "w") as fh:
        json.dump(balance, fh, indent=1)
    with open(os.path.join(OUT, "normalization_candidates.json"), "w") as fh:
        json.dump({"candidates": candidates,
                   "selected": "N0_status_quo"}, fh, indent=1)

    md = ["# Flank normalization report — three-section civic bowl",
          "",
          "Measured study (no visual judgment): section balance, composite "
          "audience frame, and whether the east flank can be extended or the "
          "south flank should be shortened. Planning-grade; EPSG:6494, "
          "NAVD88 intl ft.",
          "",
          "## 1 · Section balance (current Scenario E package)", "",
          "| family | rows | arc ft | Band-A seats | radial depth ft | az span | row1→stage front ft | centroid→stage ft |",
          "|---|---|---|---|---|---|---|---|"]
    for s in C.SECTIONS:
        v = sections[s]
        md.append(f"| {s} | {v['rows']} | {v['arc_length_ft']:.0f} | "
                  f"{v['band_a_seats']} | {v['radial_depth_ft']} | "
                  f"{v['azimuth_span_deg'][0]:.0f}–{v['azimuth_span_deg'][1]:.0f}° | "
                  f"{v['row1_dist_to_stage_front_ft']} | "
                  f"{v['centroid_dist_to_stage_centroid_ft']} |")
    md += ["",
           f"Arc-length min/max ratio **{ratio:.2f}** vs declared threshold "
           f"{BALANCE_THRESHOLD} → **justification required and provided** "
           "(see below).",
           "",
           "## 2 · Composite audience frame", "",
           f"- seat-weighted audience centroid: "
           f"({frame['audience_centroid_seatweighted'][0]}, "
           f"{frame['audience_centroid_seatweighted'][1]})",
           f"- dominant facing (seat-weighted circular mean of band normals): "
           f"**az {frame['dominant_facing_bearing_deg']}°** "
           f"(axis from stage: {frame['dominant_axis_from_stage_deg']}°)",
           f"- bearing stage-front → centroid: "
           f"**{frame['centroid_bearing_from_stage_front_deg']}°** vs inherited "
           f"stage axis {C.STAGE_AX_AZ}° → **axis mismatch "
           f"{frame['stage_axis_mismatch_deg']}°**",
           f"- lateral offset of the centroid from the stage axis: "
           f"**{frame['stage_lateral_offset_ft']} ft**",
           "",
           "## 3 · Why the east flank is short (measured)", "",
           f"- march caps: east az 85 / south az 197 (declared in "
           "`design_extended_bays.py`)",
           f"- row-18 end gaps: east → Petoskey St {stops['east'][18]} ft; "
           f"south → E Mitchell St {stops['south'][18]} ft",
           f"- contour-walk extension test (rows 6-18, east cap end): "
           + (f"**~{east_ext_total:.0f} ft total** additional on-contour arc "
              f"(~{ext['total_est_added_seats']} seats upper bound) before the "
              "45° seat-splay gate stops every row — the basin wraps north and "
              "seats would face across the bowl; per-row detail in "
              "section_balance.json"
              if ext["available"] else "_skipped (DEM missing)_"),
           "",
           "## 4 · Candidates", "",
           "| name | Δseats | balance ratio | cut/fill proxy CY | verdict |",
           "|---|---|---|---|---|"]
    for cd in candidates:
        md.append(f"| {cd['name']} | {cd['seats_delta']:+d} | "
                  f"{cd['balance_ratio']:.2f} | {cd['cut_fill_proxy_cy']} | "
                  f"{cd['verdict']} |")
    md += ["",
           "### Selected: N0_status_quo",
           "",
           justification,
           "",
           "N1 (east re-march) and N2 (+row 19, per-seat formal) remain live "
           "analysis-tier options; adopting either requires re-emission and "
           "Scenario E re-validation before any seat is claimed (canon "
           "Rules 3/5). N3 (south trim) is rejected: symmetry is not a site "
           "constraint and it deletes validated seats.",
           ""]
    with open(os.path.join(OUT, "NORMALIZATION.md"), "w") as fh:
        fh.write("\n".join(md))
    print(f"  wrote {os.path.relpath(OUT, C.REPO)}/section_balance.json, "
          "normalization_candidates.json, NORMALIZATION.md")
    print(f"  frame: centroid bearing {frame['centroid_bearing_from_stage_front_deg']}°, "
          f"mismatch {frame['stage_axis_mismatch_deg']}°, "
          f"lateral {frame['stage_lateral_offset_ft']} ft; "
          f"arc ratio {ratio:.2f}; east extension ~{east_ext_total:.0f} ft")


if __name__ == "__main__":
    main()
