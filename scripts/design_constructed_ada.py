#!/usr/bin/env python3
"""Concept D — constructed accessible route / cut-ramp alternatives.

Stage 2 (design_ada_routes.py) is preserved as Concept C: the naturalistic
promenade that follows what the landscape gives. This script asks the
opposite question: what does the BEST USER ROUTE cost if we cut it
deliberately — formal ramp runs, benching, low walls, intentional cut/fill,
seats displaced where the ramp claims the fan?

Alternatives (all start from the real public arrivals, floor datum 612.5):
  D1 integrated aisle-ramp  — switchback stacks ON the east|bend hinge
     (az 118): arrival -> cross-aisle -> event floor, landings at the
     distribution levels. Maximum centrality; the ramp claims tread length
     where it crosses rows (quantified exactly from terrace_treads).
  D2 diagonal terrace cut   — two long 8.33% legs cutting diagonally
     across the upper fan (rows 11-18) from arrival to the cross-aisle;
     floor reached via Concept C's west park walk.
  D3 hybrid                 — D1's upper stack (arrival -> cross-aisle)
     + Concept C's west park-edge floor walk + C egress legs.

Every concept is reported with the full cost sheet: length, drop, slopes,
ramp-classified length, runs, landings, turns, detour ratios, corridor
width, POST-GRADING cross-slope (designed bench 1.5%), cut/fill CY, max
depths, wall/curb/rail zones, swale/treatment conflicts, seats displaced,
sightline/stage impacts — and a documented dignity/directness score.

Outputs:
  vectors_geojson/route_corridors_D.geojson   corridors+centerlines+landings
  dem/proposed_ada_grade_delta_D.tif          design-surface minus proposed
                                              grade over the preferred D
  analysis/ada_rebuild/ada_validation.json    merged: adds "concepts" block
Label stays: "ADA-compliant route concept pending civil/code detailing".
Reproduce:  .venv/bin/python scripts/design_constructed_ada.py
"""
import json
import math
import os
import sys

import numpy as np
import rasterio

sys.path.insert(0, os.path.dirname(__file__))
import in_situ_common as C
from shapely.geometry import LineString, Point, mapping, shape
from shapely.ops import unary_union

from design_ada_routes import (CONCEPT_LABEL, corridor_surface_metrics,
                               sample_z, smoothness)
from rebuild_ada_routes import axis_pt, load_zones, U

REPO, VEC = C.REPO, C.VEC_DIR
AR_DIR = os.path.join(REPO, "analysis", "ada_rebuild")
VALID_PATH = os.path.join(AR_DIR, "ada_validation.json")
DELTA_TIF = os.path.join(REPO, "dem", "proposed_ada_grade_delta_D.tif")

RUN_GRADE = 0.0833        # formal ramp run grade
RUN_RISE = 2.5            # max rise per run (30 in) -> 30 ft runs
LANDING_FT = 5.0          # landing pads 5x5 ft min (60x60 in)
RAMP_W = 8.0              # constructed corridor width
DETOUR_FLAG = 3.0

DIGNITY_RUBRIC = {
    "base": 100,
    "directness": "-12 pts per detour-ratio unit above 1.5 (worst SERVED "
                  "pair)",
    "perimeter_penalty": "-15 if >50% of primary access length lies outside "
                         "the seating fan / behind the rim (reads as "
                         "back-of-house or perimeter-only)",
    "shared_arrival": "+10 if the accessible route IS the general arrival "
                      "path (no separate accessible door)",
    "in_bowl_arrival": "+10 if the route delivers users INTO the bowl with "
                       "everyone else (central aisle / shared promenade), "
                       "not at a remote corner",
    "integration": "+10 wheelchair clusters adjacent to companion seats on "
                   "primary sightlines (all concepts: yes, by node design)",
    "note": "design-judgment heuristic with documented weights — not a "
            "code metric",
}


# ── parametric constructed geometry ──────────────────────────────────────
def switchback_stack(az_deg, r_top, z_top, r_bot, z_bot, run_half=15.0):
    """Formal switchback ramp stack centered on a radial (hinge) ray.
    Runs are tangent (circumferential), descending radially; a landing at
    every turn. Returns (centerline pts, [(x, y, kind)...] landings,
    n_runs, ramp_len)."""
    drop = z_top - z_bot
    n_runs = max(int(math.ceil(abs(drop) / RUN_RISE)), 1)
    ax, ay = U(az_deg)
    tx, ty = U(az_deg + 90.0)

    def P(r, t):
        return (C.FX + r * ax + t * tx, C.FY + r * ay + t * ty)

    rs = np.linspace(r_top, r_bot, n_runs + 1)
    pts = [P(rs[0], 0.0)]
    landings = []
    side = 1.0
    ramp_len = 0.0
    for k in range(n_runs):
        rise_k = min(RUN_RISE, abs(drop) - k * RUN_RISE)
        run_len = rise_k / RUN_GRADE
        half = min(run_half, run_len / 2.0)
        r_run = (rs[k] + rs[k + 1]) / 2.0
        a = P(r_run, -side * half)
        b = P(r_run, side * half)
        pts.extend([a, b])
        ramp_len += run_len
        landings.append((b[0], b[1], "switchback landing 5x5 ft"))
        side = -side
    pts.append(P(rs[-1], 0.0))
    if landings:
        landings.pop()      # bottom threshold, not a turn
    return pts, landings, n_runs, ramp_len


def diagonal_cut(az0, r0, z0, az1, r1, z1, az_turn, r_turn):
    """Deliberate graded promenade cutting diagonally across the fan as a
    Z of two straight legs through an explicit turn point. Leg drops are
    apportioned by length; per-leg grade is REPORTED and must be <=8.33%
    (a previous version silently produced a 45 ft / 39% 'ramp' when the
    sweep collapsed — constructed grades are now gated downstream)."""
    drop = abs(z0 - z1)
    A = axis_pt(az0, r0)
    T = axis_pt(az_turn, r_turn)
    B = axis_pt(az1, r1)
    L1, L2 = math.dist(A, T), math.dist(T, B)
    total = L1 + L2
    g1 = drop * (L1 / total) / max(L1, 1e-9)
    g2 = drop * (L2 / total) / max(L2, 1e-9)
    pts = [A, T, B]
    landings = [(T[0], T[1], "directional landing 5x5 ft")]
    return pts, landings, 2, total, max(g1, g2)


# ── impact measurement ───────────────────────────────────────────────────
def seat_impact(corridor, treads_fc):
    """Tread features are POLYGON bands: displaced seats = seats_kept x
    (intersection AREA / band area). Also reports SEVERED rows: bands the
    corridor splits into two remaining pieces (dead-end row segments —
    egress re-planning, a cost beyond the directly displaced seats).
    Rows merely SHORTENED at an end are not severed."""
    lost, rows, severed = 0.0, {}, []
    for f in treads_fc["features"]:
        pr = f["properties"]
        g = shape(f["geometry"])
        a = g.intersection(corridor).area
        if a > 0.5:
            frac = a / max(g.area, 1e-9)
            lost += pr["seats_kept"] * frac
            rows[f"{pr['section']} r{pr['row']}"] = \
                round(frac * pr["length_ft"], 1)
            rem = g.difference(corridor)
            parts = [q for q in (rem.geoms if rem.geom_type
                                 == "MultiPolygon" else [rem])
                     if q.area > 0.1 * g.area]
            if len(parts) >= 2:
                severed.append(f"{pr['section']} r{pr['row']}")
    return round(lost, 0), rows, severed


def main():
    fc, zg = load_zones()
    with rasterio.open(os.path.join(REPO, "dem",
                                    "proposed_grade_1ft.tif")) as s:
        dem_raw = s.read(1)
        tf = s.transform
        rmeta = s.meta.copy()
    treads_fc = json.load(open(os.path.join(VEC, "terrace_treads.geojson")))
    nodes = {}
    for f in json.load(open(os.path.join(VEC, "ada_nodes.geojson")))["features"]:
        p = f["properties"]
        nodes[p["name"]] = {"xy": tuple(f["geometry"]["coordinates"]),
                            "z": p["design_elev_navd88"]
                            or p["ground_elev_navd88_proposed"]}
    cell = shape(zg["treatment_cell_landscape"][0]["geometry"])
    swales = unary_union([shape(f["geometry"])
                          for f in zg["drainage_swale"]])
    stage = unary_union([shape(zg[k][0]["geometry"]) for k in
                         ("stage_core", "stage_shoulder_left",
                          "stage_shoulder_right")])
    valid = json.load(open(VALID_PATH))
    c_routes = valid["topology"]["routes"]

    z_arr = 639.4            # arrival crest (raster at node)
    z_aisle, z_floor = 622.01, 612.5

    # ----- constructed elements ------------------------------------------
    elements = {}

    arr = nodes["public_arrival_rim"]["xy"]
    # explicit junction node where the hinge meets the cross-aisle band
    jct = axis_pt(118.0, 121.0)
    nodes["hinge_aisle_jct"] = {"xy": jct, "z": z_aisle}

    # D1 upper: hinge stack arrival -> hinge/aisle junction
    pts_u, lnd_u, runs_u, ramp_u = switchback_stack(118.0, 158.0, z_arr,
                                                    124.0, z_aisle)
    elements["D_hinge_stack_upper"] = {
        "pts": [arr] + pts_u + [jct], "landings": lnd_u,
        "runs": runs_u, "ramp_len": ramp_u,
        "z0": z_arr, "z1": z_aisle,
        "from": "public_arrival_rim", "to": "hinge_aisle_jct",
        "desc": "integrated switchback stack on the east|bend hinge "
                "(rows 11-18 band) landing on the cross-aisle at the "
                "hinge junction"}
    # level aisle connectors from the junction (existing aisle band)
    elements["D_jct_to_wc"] = {
        "pts": [jct, nodes["wc_cluster_cross_aisle"]["xy"]],
        "landings": [], "runs": 0, "ramp_len": 0.0,
        "z0": z_aisle, "z1": z_aisle,
        "from": "hinge_aisle_jct", "to": "wc_cluster_cross_aisle",
        "desc": "level distribution along the existing cross-aisle band"}
    elements["D_jct_to_mid"] = {
        "pts": [jct, nodes["cross_aisle_mid"]["xy"]],
        "landings": [], "runs": 0, "ramp_len": 0.0,
        "z0": z_aisle, "z1": z_aisle,
        "from": "hinge_aisle_jct", "to": "cross_aisle_mid",
        "desc": "level distribution along the existing cross-aisle band"}

    # D1 lower: hinge stack junction -> floor + level run to floor node
    pts_l, lnd_l, runs_l, ramp_l = switchback_stack(118.0, 115.0, z_aisle,
                                                    88.0, z_floor)
    elements["D_hinge_stack_lower"] = {
        "pts": [jct] + pts_l + [nodes["floor_arrival"]["xy"]],
        "landings": lnd_l, "runs": runs_l, "ramp_len": ramp_l,
        "z0": z_aisle, "z1": z_floor,
        "from": "hinge_aisle_jct", "to": "floor_arrival",
        "desc": "integrated switchback stack continuing the hinge through "
                "rows 1-8 to the event floor at the 612.5 datum"}

    # D2: diagonal terrace cut across rows 11-18, arriving AT the cluster.
    # Turn point az 165 / r 141 sizes both legs so each grades ~8.0-8.1%
    # over the 17.4 ft drop (a compliant Z needs ~210+ ft of travel).
    pts_d, lnd_d, legs_d, len_d, grade_d = diagonal_cut(
        118.0, 159.0, z_arr, 126.0, 123.0, z_aisle,
        az_turn=165.0, r_turn=141.0)
    elements["D_diagonal_cut"] = {
        "pts": [arr] + pts_d + [nodes["wc_cluster_cross_aisle"]["xy"]],
        "landings": lnd_d, "runs": legs_d,
        "ramp_len": len_d, "z0": z_arr, "z1": z_aisle,
        "from": "public_arrival_rim", "to": "wc_cluster_cross_aisle",
        "desc": "two-leg diagonal graded promenade cut across the upper "
                "fan (rows 11-18) arriving directly at the wheelchair "
                "cluster"}

    # ----- per-element measurement ---------------------------------------
    el_report, el_features = {}, []
    for name, el in elements.items():
        line = LineString(el["pts"])
        corridor = line.buffer(RAMP_W / 2, cap_style=2)
        surface = corridor_surface_metrics(line, el["z0"], el["z1"],
                                           RAMP_W, dem_raw, tf)
        seats, rows, severed = seat_impact(corridor, treads_fc)
        drop = el["z0"] - el["z1"]
        sm = smoothness(el["pts"])
        rep = {
            "desc": el["desc"], "from": el["from"], "to": el["to"],
            "length_ft": round(line.length, 1),
            "drop_ft": round(drop, 2),
            "avg_running_slope_pct": round(drop / line.length * 100, 2),
            "max_running_slope_pct": round(
                max(drop / max(el["ramp_len"], 1e-9), 0.0) * 100
                if el["ramp_len"] else 0.0, 2),
            "compliant_grade": bool(
                (drop / max(el["ramp_len"], 1e-9) <= 0.0834)
                if el["ramp_len"] else True),
            "ramp_classified_len_gt5pct_ft": round(el["ramp_len"], 0),
            "ramp_runs": el["runs"],
            "landings": {"count": len(el["landings"]),
                         "size": "5x5 ft min (60x60 in), <=2% any "
                                 "direction — pending civil detailing"},
            "turn_count": sm.get("turn_count_gt20deg"),
            "corridor_width_ft": RAMP_W,
            "grading": {k: surface[k] for k in
                        ("cut_cy", "fill_cy", "max_cut_ft", "max_fill_ft")},
            "designed_cross_slope_pct": surface["designed_cross_slope_pct"],
            "wall_curb_rail_zones": surface["wall_curb_rail_zones"],
            "treatment_cell_ft": round(
                line.intersection(cell).length, 2),
            "swale_ft": round(line.intersection(swales).length, 2),
            "stage_zone_ft": round(line.intersection(stage).length, 2),
            "seats_displaced": seats,
            "rows_cut": rows,
            "rows_severed": severed,
            "sightline_impact": ("ramp guards/walls rise beside cut rows — "
                                 "adjacent-seat C-value restudy REQUIRED "
                                 "before adoption"
                                 + ("; SEVERS rows mid-tread into dead-end "
                                    "segments (egress re-planning) and "
                                    "raises a railed line across the fan's "
                                    "visual field" if severed else ""))
                                if seats else "none",
            "unresolved": ["surface material", "edge protection detail",
                           "handrails/guards", "drainage at runs/landings",
                           "lighting"],
        }
        el_report[name] = rep
        el_features.append({"type": "Feature", "geometry": mapping(corridor),
                            "properties": {"role": "corridor",
                                           "element": name, **{
                                k: rep[k] for k in
                                ("desc", "length_ft", "corridor_width_ft",
                                 "seats_displaced")},
                                "grading": rep["grading"]}})
        el_features.append({"type": "Feature", "geometry": mapping(line),
                            "properties": {"role": "centerline",
                                           "element": name,
                                           "profile": surface["profile"],
                                           "status": CONCEPT_LABEL}})
        for (lx, ly, kind) in el["landings"]:
            el_features.append({"type": "Feature",
                                "geometry": {"type": "Point",
                                             "coordinates": [round(lx, 2),
                                                             round(ly, 2)]},
                                "properties": {"role": "landing",
                                               "element": name,
                                               "note": kind}})

    # ----- concept assembly ----------------------------------------------
    def c_leg(nm):
        r = c_routes[nm]
        return {"length_ft": r["length_ft"], "from": r["from"],
                "to": r["to"], "reused_from_C": True}

    CONCEPTS = {
        "D1_integrated_aisle_ramp": {
            "label": "Integrated aisle-ramp on the east|bend hinge — "
                     "arrival, cross-aisle, floor on one central line",
            "constructed": ["D_hinge_stack_upper", "D_jct_to_wc",
                            "D_jct_to_mid", "D_hinge_stack_lower"],
            "reused_C": ["route_cross_aisle_to_wc_cluster",
                         "route_floor_to_wc_cluster",
                         "route_cross_aisle_to_egress",
                         "route_floor_to_egress"],
            "arrivals": ["public_arrival_rim"]},
        "D2_diagonal_terrace_cut": {
            "label": "Diagonal terrace cut across the upper fan to the "
                     "cross-aisle; floor via the west park walk",
            "constructed": ["D_diagonal_cut"],
            "reused_C": ["route_park_to_floor",
                         "route_cross_aisle_to_wc_cluster",
                         "route_floor_to_wc_cluster",
                         "route_cross_aisle_to_egress",
                         "route_floor_to_egress"],
            "arrivals": ["public_arrival_rim", "park_arrival_west"]},
        "D3_hybrid_short_ramp": {
            "label": "Hybrid: D1 upper stack to the cross-aisle + west "
                     "park walk to the floor",
            "constructed": ["D_hinge_stack_upper", "D_jct_to_wc",
                            "D_jct_to_mid"],
            "reused_C": ["route_park_to_floor",
                         "route_cross_aisle_to_wc_cluster",
                         "route_floor_to_wc_cluster",
                         "route_cross_aisle_to_egress",
                         "route_floor_to_egress"],
            "arrivals": ["public_arrival_rim", "park_arrival_west"]},
    }

    # network shortest path per concept (public legs only)
    def net_dist(edges, a, b):
        import heapq
        dist = {a: 0.0}
        pq = [(0.0, a)]
        while pq:
            d, x = heapq.heappop(pq)
            if x == b:
                return d
            if d > dist.get(x, 1e18):
                continue
            for y, wgt in edges.get(x, {}).items():
                nd = d + wgt
                if nd < dist.get(y, 1e18):
                    dist[y] = nd
                    heapq.heappush(pq, (nd, y))
        return None

    def concept_metrics(key, spec):
        edges = {}

        def add(a, b, L):
            edges.setdefault(a, {})[b] = min(edges.get(a, {}).get(b, 1e18), L)
            edges.setdefault(b, {})[a] = min(edges.get(b, {}).get(a, 1e18), L)
        for nm in spec["constructed"]:
            r = el_report[nm]
            add(r["from"], r["to"], r["length_ft"])
        for nm in spec["reused_C"]:
            r = c_routes[nm]
            add(r["from"], r["to"], r["length_ft"])
        # detours from the SERVING arrival
        det, worst = {}, 0.0
        for target in ("cross_aisle_mid", "floor_arrival",
                       "wc_cluster_cross_aisle", "wc_cluster_floor"):
            best = None
            for a in spec["arrivals"]:
                nd = net_dist(edges, a, target)
                if nd is not None and (best is None or nd < best[1]):
                    best = (a, nd)
            if best is None:
                det[target] = None
                continue
            a, nd = best
            desire = math.dist(nodes[a]["xy"], nodes[target]["xy"])
            ratio = round(nd / desire, 2)
            worst = max(worst, ratio)
            det[f"{a}->{target}"] = {"desire_line_ft": round(desire, 1),
                                     "route_ft": round(nd, 1),
                                     "detour_ratio": ratio,
                                     "flag_socially_inferior":
                                         ratio > DETOUR_FLAG}
        cons = [el_report[nm] for nm in spec["constructed"]]
        seats = sum(c["seats_displaced"] for c in cons)
        grades_ok = all(c["compliant_grade"] for c in cons)
        # dignity: documented heuristic
        score = 100.0 - 12.0 * max(0.0, worst - 1.5)
        # perimeter character of the PRIMARY access legs
        if key.startswith("D"):
            perimeter = False        # constructed legs live in the bowl
        else:
            perimeter = True
        if perimeter:
            score -= 15
        score += 10        # shared arrival (all concepts use public ways)
        if any("hinge" in nm or "diagonal" in nm
               for nm in spec["constructed"]):
            score += 10    # delivers users into the bowl centrally
        score += 10        # clusters integrated w/ companions (node design)
        return {
            "label": spec["label"],
            "constructed_elements": {nm: el_report[nm]
                                     for nm in spec["constructed"]},
            "reused_concept_C_legs": {nm: c_leg(nm)
                                      for nm in spec["reused_C"]},
            "totals": {
                "constructed_length_ft": round(sum(c["length_ft"]
                                                   for c in cons), 0),
                "network_length_ft": round(sum(c["length_ft"]
                                               for c in cons)
                                           + sum(c_routes[nm]["length_ft"]
                                                 for nm in spec["reused_C"]),
                                           0),
                "ramp_runs": sum(c["ramp_runs"] for c in cons),
                "landings": sum(c["landings"]["count"] for c in cons),
                "cut_cy": round(sum(c["grading"]["cut_cy"] for c in cons), 1),
                "fill_cy": round(sum(c["grading"]["fill_cy"]
                                     for c in cons), 1),
                "max_cut_ft": max((c["grading"]["max_cut_ft"]
                                   for c in cons), default=0),
                "max_fill_ft": max((c["grading"]["max_fill_ft"]
                                    for c in cons), default=0),
                "seats_displaced": seats,
                "rows_severed": sorted({r for c in cons
                                        for r in c.get("rows_severed",
                                                       [])}),
                "treatment_cell_ft": sum(c["treatment_cell_ft"]
                                         for c in cons),
                "swale_ft": sum(c["swale_ft"] for c in cons),
                "stage_zone_ft": sum(c["stage_zone_ft"] for c in cons),
            },
            "detour": det,
            "worst_served_detour_ratio": worst,
            "constructed_grades_compliant": grades_ok,
            "dignity_directness_score": round(score, 0)
            if grades_ok else 0.0,
            "valid": grades_ok,
        }

    concepts = {k: concept_metrics(k, v) for k, v in CONCEPTS.items()}
    for k, cv in concepts.items():
        if not cv.get("valid", True):
            print(f"  !! {k}: NON-COMPLIANT constructed grade — concept "
                  "invalidated (score zeroed)")

    # Concept C rollup with the same dignity rubric
    c_det = valid["detour_ratios"]["per_alternative"]["C_hybrid"]
    c_worst = max((r.get("detour_ratio") or 0) for r in c_det.values())
    c_score = 100.0 - 12.0 * max(0.0, c_worst - 1.5)
    c_score -= 15      # primary legs are perimeter promenades (by design)
    c_score += 10      # shared arrival promenade
    c_score += 0       # arrives at aisle/floor edges, not bowl center
    c_score += 10      # clusters integrated
    concepts["C_naturalistic_promenade"] = {
        "label": "Concept C — naturalistic promenade / low-ramp "
                 "classification (Stage 2, preserved)",
        "totals": {"network_length_ft": round(sum(
            r["length_ft"] for n, r in c_routes.items()
            if r.get("preferred")), 0),
            "cut_cy": round(sum(
                c["grading"]["cut_cy"] for c in
                valid["corridors"]["per_route"].values()
                if "grading" in c), 1),
            "fill_cy": round(sum(
                c["grading"]["fill_cy"] for c in
                valid["corridors"]["per_route"].values()
                if "grading" in c), 1),
            "seats_displaced": 0,
            "treatment_cell_ft": 0.0},
        "detour": c_det,
        "worst_served_detour_ratio": c_worst,
        "dignity_directness_score": round(c_score, 0),
        "note": "full per-route detail lives in the stage-2 sections of "
                "this file (topology/conflicts/slopes/smoothness/"
                "corridors)"}

    # ----- preferred D + recommendation ----------------------------------
    d_keys = [k for k in concepts
              if k.startswith("D") and concepts[k].get("valid")]
    if not d_keys:
        raise SystemExit("no valid Concept D alternative — all constructed "
                         "grades non-compliant")
    pref_d = max(d_keys, key=lambda k:
                 concepts[k]["dignity_directness_score"]
                 - concepts[k]["totals"]["seats_displaced"] * 0.15)
    recommendation = {
        "preferred_D": pref_d,
        "governing_recommendation": None,   # filled below
        "tradeoff": None,
    }
    cD = concepts[pref_d]
    cC = concepts["C_naturalistic_promenade"]
    recommendation["tradeoff"] = (
        f"{pref_d}: dignity {cD['dignity_directness_score']:.0f} vs C "
        f"{cC['dignity_directness_score']:.0f}; seats displaced "
        f"{cD['totals']['seats_displaced']:.0f} vs 0; constructed cut "
        f"{cD['totals']['cut_cy']} CY + fill {cD['totals']['fill_cy']} CY "
        f"vs C bench {cC['totals']['cut_cy']}+{cC['totals']['fill_cy']} CY")
    # terrain bound: a compliant route cannot be shorter than drop/8.33%,
    # so the detour ratio has a FLOOR set by the bowl itself
    tb = {}
    for target, z_t in (("cross_aisle_mid", z_aisle),
                        ("wc_cluster_cross_aisle", z_aisle),
                        ("floor_arrival", z_floor),
                        ("wc_cluster_floor", z_floor)):
        desire = math.dist(arr, nodes[target]["xy"])
        min_len = (z_arr - z_t) / RUN_GRADE
        tb[target] = {"desire_ft": round(desire, 1),
                      "min_compliant_route_ft": round(min_len, 0),
                      "terrain_bound_detour_ratio":
                          round(min_len / desire, 2)}
    recommendation["terrain_bound_detour"] = {
        "pairs": tb,
        "finding": "the bowl's drop at 8.33% max grade puts a FLOOR of "
                   "~4-5x under every detour ratio from the east arrival "
                   "— no constructed route can reach 'direct'; reshaping "
                   "buys a bounded improvement (C ~7-9x -> best D ~4-6x), "
                   "never parity with the stair desire line"}
    # decision rule, documented: D governs only if it beats C on dignity
    # by >=20 pts, displaces <60 seats (<5% of 1,283) AND severs no row
    # mid-tread (severance creates dead-end egress segments + a railed
    # line across the fan's visual field — costs borne by OTHER patrons
    # that the user-experience dignity score does not price).
    if (cD["dignity_directness_score"]
            - cC["dignity_directness_score"] >= 20
            and cD["totals"]["seats_displaced"] < 60
            and not cD["totals"]["rows_severed"]):
        recommendation["governing_recommendation"] = pref_d
    else:
        recommendation["governing_recommendation"] = \
            "C_naturalistic_promenade"
    recommendation["rule"] = ("D governs if dignity advantage >=20 pts AND "
                              "seats displaced <60 (<5% of 1,283) AND no "
                              "rows severed mid-tread; otherwise C governs "
                              "and the preferred D is carried as the "
                              "design-development alternative")

    # ----- outputs ---------------------------------------------------------
    for ftr in el_features:
        ftr["properties"]["concepts"] = [k for k, v in CONCEPTS.items()
                                         if ftr["properties"].get("element")
                                         in v["constructed"]]
    C.dump(C.fc(el_features), os.path.join(VEC, "route_corridors_D.geojson"))

    # delta raster over the preferred D's constructed corridors
    delta = np.full(dem_raw.shape, -9999.0, dtype="float32")
    for nm in CONCEPTS[pref_d]["constructed"]:
        el = elements[nm]
        line = LineString(el["pts"])
        L = line.length
        n = max(int(L / 1.0), 2)
        for i in range(n + 1):
            d = L * i / n
            ppt = line.interpolate(d)
            p2 = line.interpolate(min(d + 1.0, L))
            hx, hy = p2.x - ppt.x, p2.y - ppt.y
            hl = math.hypot(hx, hy) or 1.0
            nxv, nyv = -hy / hl, hx / hl
            z_c = el["z0"] + (el["z1"] - el["z0"]) * d / L
            for o in np.arange(-RAMP_W / 2, RAMP_W / 2 + 0.5, 1.0):
                x, y = ppt.x + nxv * o, ppt.y + nyv * o
                r, cc = rasterio.transform.rowcol(tf, x, y)
                if 0 <= r < delta.shape[0] and 0 <= cc < delta.shape[1]:
                    zt = dem_raw[r, cc]
                    if zt != -9999.0:
                        delta[r, cc] = (z_c - o * 0.015) - zt
    rmeta.update(dtype="float32", nodata=-9999.0, compress="deflate")
    with rasterio.open(DELTA_TIF, "w", **rmeta) as dst:
        dst.write(delta, 1)

    valid["concepts"] = concepts
    valid["dignity_rubric"] = DIGNITY_RUBRIC
    valid["recommendation_c_vs_d"] = recommendation
    valid["concept_C_status"] = (
        "PRESERVED as the naturalistic promenade / low-ramp-classification "
        "concept; NOT ADA compliant until corridor cross-slope and surface "
        "sections are resolved in civil detailing")
    with open(VALID_PATH, "w") as f:
        json.dump(valid, f, indent=1)

    print("── Concept D cost sheets ──")
    for k in d_keys + ["C_naturalistic_promenade"]:
        t = concepts[k]["totals"]
        print(f"{k}: dignity {concepts[k]['dignity_directness_score']:.0f}, "
              f"worst detour {concepts[k]['worst_served_detour_ratio']}, "
              f"seats -{t.get('seats_displaced', 0):.0f}, "
              f"severed {len(t.get('rows_severed', []))} rows, "
              f"cut {t.get('cut_cy', '—')} CY / fill {t.get('fill_cy', '—')} CY")
    print("preferred D:", pref_d)
    print("GOVERNING:", recommendation["governing_recommendation"])


if __name__ == "__main__":
    main()
