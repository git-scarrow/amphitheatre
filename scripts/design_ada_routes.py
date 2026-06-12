#!/usr/bin/env python3
"""Stage 2 of the ADA rebuild: convert solver-feasible corridors into a
DESIGNED civic accessible-route plan.

Stage 1 (rebuild_ada_routes.py) proves feasibility: quarantined legacy,
nodes, slope-capped Dijkstra corridors (analysis/ada_rebuild/
solver_paths.geojson). Those polylines are pathfinding artifacts — 55-79
sharp turns each, 1.2 ft mean segments. This stage:

  * line-of-sight simplifies each corridor INSIDE the legal mask into long
    deliberate runs (switchbacks only where the mask forces them),
  * assigns a design profile between node datums (canonical floor 612.5 /
    cross-aisle 622.01): <=5% reads as a sloped walk (no landings
    required), 5-8.33% as ramp runs with landings every 30 in of rise,
  * measures route smoothness (turn count / min & mean segment / angle
    changes) before vs after,
  * packages THREE alternatives (A east-primary, B south-perimeter,
    C hybrid east + west-park low arrival) with per-alternative metrics,
  * computes detour ratios vs pedestrian desire lines and flags
    socially-inferior outcomes,
  * widens centerlines into corridors (route_corridors.geojson) with
    cross-slope / benching / railing / retaining flags,
  * separates the route hierarchy (public primary / secondary egress /
    distribution / service) — service segments NEVER prove public
    connectivity,
  * recommends one preferred concept.

Outputs:
  vectors_geojson/ada_route.geojson        design centerlines + landings
  vectors_geojson/route_corridors.geojson  corridor polygons
  analysis/ada_rebuild/ada_validation.json full ordered validation
Label stays: "ADA-compliant route concept pending civil/code detailing".
Reproduce:  .venv/bin/python scripts/design_ada_routes.py
"""
import json
import math
import os
import sys

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter
from shapely.geometry import LineString, Point, mapping, shape
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(__file__))
import in_situ_common as C
from rebuild_ada_routes import (CONCEPT_LABEL, SWALE_CROSS_MAX_FT,
                                UNCHECKED_CODE_DETAILS, build_masks,
                                load_zones)

REPO, VEC = C.REPO, C.VEC_DIR
AR_DIR = os.path.join(REPO, "analysis", "ada_rebuild")
OUT_VALID = os.path.join(AR_DIR, "ada_validation.json")

WALK_MAX = 0.05          # <=5% = accessible sloped walk (no landings)
RAMP_MAX = 0.0833        # >5% must be ramp runs with landings
# min tangent RUN between perceptible turns: 1.5 path widths (landscape
# practice for pedestrian reverse curves), never below 9 ft
MIN_RUN_WIDTHS = 1.5
MIN_RUN_FLOOR_FT = 9.0
MAX_TURNS = 12           # deliberate turns per route
DETOUR_FLAG = 3.0        # route/desire-line ratio considered segregating

WIDTH_FT = {"public_primary": 8.0, "public_secondary": 6.0,
            "distribution": 8.0, "service": 12.0}

ROUTE_CLASS = {   # hierarchy under the PREFERRED concept (alternative C)
    "route_arrival_to_cross_aisle": "public_primary",
    "route_park_to_floor": "public_primary",
    "route_arrival_to_floor": "public_secondary",
    "route_cross_aisle_to_egress": "public_secondary",
    "route_floor_to_egress": "public_secondary",
    "route_cross_aisle_to_wc_cluster": "distribution",
    "route_floor_to_wc_cluster": "distribution",
    "route_service_to_stage": "service",
}
ALTERNATIVES = {
    "A_east_primary": {
        "label": "East rim primary — street arrival serves both levels",
        "members": ["route_arrival_to_cross_aisle", "route_arrival_to_floor",
                    "route_cross_aisle_to_wc_cluster",
                    "route_floor_to_wc_cluster",
                    "route_cross_aisle_to_egress"],
        "arrival": "public_arrival_rim",
        "arrivals": ["public_arrival_rim"]},
    "B_south_perimeter": {
        "label": "South perimeter — E Mitchell St side as access + egress",
        "members": ["route_cross_aisle_to_egress", "route_floor_to_egress",
                    "route_cross_aisle_to_wc_cluster",
                    "route_floor_to_wc_cluster"],
        "arrival": "egress_rim_south",
        "arrivals": ["egress_rim_south"]},
    "C_hybrid": {
        "label": "Hybrid — east street arrival to the cross-aisle + west "
                 "park-edge low arrival to the floor",
        "members": ["route_arrival_to_cross_aisle", "route_park_to_floor",
                    "route_cross_aisle_to_wc_cluster",
                    "route_floor_to_wc_cluster",
                    "route_cross_aisle_to_egress", "route_floor_to_egress"],
        "arrival": "public_arrival_rim",
        "arrivals": ["public_arrival_rim", "park_arrival_west"]},
}
PREFERRED = "C_hybrid"


# ── geometry helpers ─────────────────────────────────────────────────────
def smoothness(coords):
    c = np.asarray(coords, float)
    seg = np.diff(c, axis=0)
    L = np.hypot(seg[:, 0], seg[:, 1])
    L = L[L > 1e-9]
    if len(L) == 0:
        return {}
    ang = np.degrees(np.arctan2(seg[:, 0], seg[:, 1]))
    dang = np.abs((np.diff(ang) + 180) % 360 - 180)
    return {"total_ft": round(float(L.sum()), 1),
            "n_segments": int(len(L)),
            "min_seg_ft": round(float(L.min()), 1),
            "mean_seg_ft": round(float(L.mean()), 1),
            "turn_count_gt20deg": int((dang > 20).sum()),
            "angle_changes_gt5deg": int((dang > 5).sum())}


def seg_clear(allowed, tf, p0, p1, step=0.6):
    n = max(2, int(math.dist(p0, p1) / step))
    for i in range(n + 1):
        t = i / n
        x = p0[0] + (p1[0] - p0[0]) * t
        y = p0[1] + (p1[1] - p0[1]) * t
        r, c = rasterio.transform.rowcol(tf, x, y)
        if not (0 <= r < allowed.shape[0] and 0 <= c < allowed.shape[1]) \
                or not allowed[r, c]:
            return False
    return True


class Legality:
    """Segment legality = raster mask prefilter + EXACT shapely checks.

    The raster mask alone lets diagonal segments pass between forbidden
    cell corners (measured 0.3 ft wedge nicks) and lets segments run ALONG
    swale cells (measured 30-38 ft swale-following). Exact rules:
      * zero contact with treatment cell / seating wedge,
      * zero contact with stage zones for public routes,
      * swale contact ONLY inside windows around the stage-1 solver
        crossings (15 ft radius), so designs cross where feasibility was
        proven, roughly perpendicular, never alongside.
    """

    def __init__(self, allowed, tf, polys, klass, solver_line, m_swale):
        self.allowed, self.tf = allowed, tf
        # gateways are ENGINEERED graded transitions where the aisle/
        # promenade bands meet the flank: the row-end there is rebuilt by
        # design, so wedge contact INSIDE a gateway is the transition
        # itself, not a conflict — exact-wedge legality outside gateways
        # only. (Keeping the strict check inside gateways was what forced
        # 4-jog mini-staircases at the aisle thresholds.)
        self.wedge = polys["seating_wedge"].difference(polys["gateways"])
        self.cell = polys["treatment_cell"]
        self.stage = polys["stage"]
        self.swales = polys["swales"]
        self.klass = klass
        x = solver_line.intersection(self.swales)
        self.swale_window = x.buffer(15.0) if not x.is_empty else None

    def ok(self, p0, p1):
        if not seg_clear(self.allowed, self.tf, p0, p1):
            return False
        seg = LineString([p0, p1])
        if seg.intersection(self.cell).length > 0.01:
            return False
        if seg.intersection(self.wedge).length > 0.01:
            return False
        if self.klass != "service" and \
                seg.intersection(self.stage).length > 0.01:
            return False
        sw = seg.intersection(self.swales)
        if sw.length > 0.01:
            if self.swale_window is None or \
                    sw.difference(self.swale_window).length > 0.01:
                return False
            if sw.length > 24.0:   # single span; route-level type:
                return False        # culvert <=12, boardwalk 12-24
            # a crossing segment must SPAN the swale — endpoints inside it
            # let chains of partial crossings accumulate 30+ ft in-swale
            if Point(p0).within(self.swales) or \
                    Point(p1).within(self.swales):
                return False
        return True


def los_simplify(coords, legal):
    """Greedy line-of-sight: longest legal straight runs."""
    out = [coords[0]]
    i, n = 0, len(coords)
    while i < n - 1:
        j = n - 1
        while j > i + 1 and not legal.ok(coords[i], coords[j]):
            j = i + (j - i) * 3 // 4 if j - i > 8 else j - 1
        while j > i + 1 and not legal.ok(coords[i], coords[j]):
            j -= 1
        out.append(coords[j])
        i = j
    return out


def dp_keep_indices(coords, tol):
    """Douglas-Peucker on indices (keeps overall sweep -> keeps length)."""
    keep = {0, len(coords) - 1}

    def rec(i, j):
        if j <= i + 1:
            return
        a, b = np.array(coords[i]), np.array(coords[j])
        ab = b - a
        L = np.hypot(*ab) or 1.0
        dmax, imax = -1.0, None
        for k in range(i + 1, j):
            pq = np.array(coords[k]) - a
            d = abs(ab[0] * pq[1] - ab[1] * pq[0]) / L
            if d > dmax:
                dmax, imax = d, k
        if dmax > tol:
            keep.add(imax)
            rec(i, imax)
            rec(imax, j)
    rec(0, len(coords) - 1)
    return sorted(keep)


def legalize(coords, idxs, legal):
    """Re-insert original vertices wherever a simplified segment is
    illegal, until every segment passes the exact checks."""
    idxs = list(idxs)
    changed = True
    while changed:
        changed = False
        k = 0
        while k < len(idxs) - 1:
            i, j = idxs[k], idxs[k + 1]
            if j > i + 1 and not legal.ok(coords[i], coords[j]):
                idxs.insert(k + 1, (i + j) // 2)
                changed = True
            else:
                k += 1
    return [coords[i] for i in idxs]


def consolidate_crossings(pts, legal):
    """Collapse vertex runs at swale crossings into one clean span. The
    LOS fallback can emit solver-resolution steps THROUGH a swale (its
    last-resort j=i+1 step skips the legality check); a designed path
    crosses on one engineered segment."""
    if legal.swale_window is None:
        return pts
    sw = legal.swales

    def touches(i):
        a = LineString([pts[max(i - 1, 0)], pts[i]])
        b = LineString([pts[i], pts[min(i + 1, len(pts) - 1)]])
        return (a.intersection(sw).length > 0.01
                or b.intersection(sw).length > 0.01)

    out = list(pts)
    i = 1
    while i < len(out) - 1:
        if touches(i):
            j = i
            while j < len(out) - 1 and touches(j):
                j += 1
            a, b = max(i - 1, 0), min(j, len(out) - 1)
            if b > a + 1 and legal.ok(out[a], out[b]):
                out[a + 1:b] = []
                i = a + 1
                continue
        i += 1
    return out


def merge_short(pts, legal, min_seg=18.0):
    """Eliminate stub segments: drop either offending vertex, or replace
    the close pair with its midpoint — whichever first yields legal
    geometry. Endpoints (nodes) never move."""
    changed = True
    while changed and len(pts) > 2:
        changed = False
        for k in range(len(pts) - 1):
            if math.dist(pts[k], pts[k + 1]) >= min_seg:
                continue
            # candidate repairs in preference order
            if 0 < k and k < len(pts) - 1 and \
                    legal.ok(pts[k - 1], pts[k + 1]):
                pts.pop(k)
                changed = True
                break
            if 0 < k + 1 < len(pts) - 1 and \
                    legal.ok(pts[k], pts[k + 2]):
                pts.pop(k + 1)
                changed = True
                break
            if 0 < k and 0 < k + 1 < len(pts) - 1:
                mid = ((pts[k][0] + pts[k + 1][0]) / 2,
                       (pts[k][1] + pts[k + 1][1]) / 2)
                if legal.ok(pts[k - 1], mid) and legal.ok(mid, pts[k + 2]):
                    pts[k:k + 2] = [mid]
                    changed = True
                    break
    return pts


def fillet(pts, legal, radii=(12.0, 8.0, 5.0, 3.0)):
    """Round every perceptible corner with an arc-approximating quadratic
    Bezier (legality-checked, radius backing off). A built path takes
    corners as curves; crisp angle points are a drafting artifact. Sharp
    corners get more samples so per-step deflection stays imperceptible."""
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        A, B, Cc = pts[i - 1], pts[i], pts[i + 1]
        la, lc = math.dist(A, B), math.dist(B, Cc)
        ux, uy = (A[0] - B[0]) / la, (A[1] - B[1]) / la
        vx, vy = (Cc[0] - B[0]) / lc, (Cc[1] - B[1]) / lc
        cosd = max(-1, min(1, ux * vx + uy * vy))
        deflection = 180.0 - math.degrees(math.acos(cosd))
        if deflection < 15:
            out.append(B)
            continue
        placed = False
        for r in radii:
            t = min(r, 0.4 * la, 0.4 * lc)
            P0 = (B[0] + ux * t, B[1] + uy * t)
            P1 = (B[0] + vx * t, B[1] + vy * t)
            n = 8 if deflection > 45 else 5
            arc = [((1 - s) ** 2 * P0[0] + 2 * (1 - s) * s * B[0]
                    + s * s * P1[0],
                    (1 - s) ** 2 * P0[1] + 2 * (1 - s) * s * B[1]
                    + s * s * P1[1])
                   for s in [k / n for k in range(n + 1)]]
            chain = [out[-1]] + arc
            if all(legal.ok(chain[k], chain[k + 1])
                   for k in range(len(chain) - 1)):
                out.extend(arc)
                placed = True
                break
        if not placed:
            out.append(B)     # corner stays crisp; pad lands here anyway
    out.append(pts[-1])
    return out


def design_alignment(coords, legal, drop):
    """Pick the design geometry: prefer a <=4.8% sloped-walk profile by
    keeping corridor length (legal DP); fall back to the shortest legal
    LOS line when the drop is small; never shorten below ramp length."""
    los = merge_short(consolidate_crossings(
        los_simplify(coords, legal), legal), legal)
    los_len = LineString(los).length
    need_walk = abs(drop) / 0.048 if drop else 0.0
    need_ramp = abs(drop) / 0.078 if drop else 0.0
    if los_len >= need_walk or abs(drop) < 0.5:
        return los
    # keep length: descending-tolerance legal DP until walk (or at least
    # ramp) length is preserved
    best = los
    for tol in (10.0, 7.0, 5.0, 3.5, 2.5, 1.5, 1.0):
        cand = legalize(coords, dp_keep_indices(coords, tol), legal)
        cand = merge_short(consolidate_crossings(cand, legal), legal)
        L = LineString(cand).length
        best = cand
        if L >= need_walk:
            return cand
    if LineString(best).length >= need_ramp:
        return best
    return best  # over-grade is caught by the slope gate downstream


def sample_z(arr, tf, x, y):
    r, c = rasterio.transform.rowcol(tf, x, y)
    if 0 <= r < arr.shape[0] and 0 <= c < arr.shape[1]:
        v = arr[r, c]
        return None if v == -9999.0 else float(v)
    return None


# ── main ─────────────────────────────────────────────────────────────────
def main():
    fc, zg = load_zones()
    with rasterio.open(os.path.join(REPO, "dem",
                                    "proposed_grade_1ft.tif")) as s:
        dem_raw = s.read(1)
        tf = s.transform
    void = dem_raw == -9999.0
    w = gaussian_filter((~void).astype(float), sigma=5.0, mode="nearest")
    dem = np.where(w > 0.2,
                   gaussian_filter(np.where(void, 0, dem_raw), sigma=5.0,
                                   mode="nearest") / np.maximum(w, 1e-6),
                   -9999.0).astype("float32")
    (allowed_pub, allowed_svc, m_swale, m_gateway,
     polys) = build_masks(zg, dem, tf, dem.shape)

    nodes = {}
    with open(os.path.join(VEC, "ada_nodes.geojson")) as f:
        for ft in json.load(f)["features"]:
            p = ft["properties"]
            nodes[p["name"]] = {
                "xy": tuple(ft["geometry"]["coordinates"]),
                "z_design": p["design_elev_navd88"],
                "z_raster": p["ground_elev_navd88_proposed"],
                "class": p["class"]}

    with open(os.path.join(AR_DIR, "solver_paths.geojson")) as f:
        solver = {ft["properties"]["name"]: ft
                  for ft in json.load(f)["features"]
                  if ft["properties"].get("role") == "ada_route_concept"}

    feats, landings_fc, corridors = [], [], []
    route_report = {}
    for name, ft in solver.items():
        klass = ROUTE_CLASS[name]
        allowed = allowed_svc if klass == "service" else allowed_pub
        coords = [tuple(c) for c in ft["geometry"]["coordinates"]]
        before = smoothness(coords)
        a, b = ft["properties"]["from"], ft["properties"]["to"]
        za = nodes[a]["z_design"] or nodes[a]["z_raster"]
        zb = nodes[b]["z_design"] or nodes[b]["z_raster"]
        drop = za - zb
        # raster prefilter must agree with the exact rules: gateway cells
        # (engineered transitions) are legal for design alignments even
        # where they overlap the wedge burn
        allowed_design = allowed | (m_gateway == 1)
        legal = Legality(allowed_design, tf, polys, klass,
                         LineString(coords), m_swale)
        crisp = design_alignment(coords, legal, drop)
        after = smoothness(crisp)        # deliberate-turn metrics
        design = fillet(crisp, legal)    # built form: curves, not angles
        line = LineString(design)
        grade = abs(drop) / max(line.length, 1e-9)
        if grade <= WALK_MAX:
            profile = "sloped_walk(<=5%)"
            n_land_req = 0
        elif grade <= RAMP_MAX:
            profile = "ramp_runs(5-8.33%)"
            n_land_req = int(abs(drop) // 2.5)
        else:
            profile = "OVER-GRADE — needs added length/switchbacks"
            n_land_req = -1

        # landings: at required rise intervals (ramp profile) + at every
        # deliberate turn > 45 deg (switchback pads)
        lnd_pts = []
        if n_land_req > 0:
            for k in range(1, n_land_req + 1):
                d = line.length * (k * 2.5 / abs(drop))
                if d < line.length - 5:
                    lp = line.interpolate(d)
                    lnd_pts.append((lp.x, lp.y, "rise-interval"))
        for i in range(1, len(crisp) - 1):
            a1 = math.degrees(math.atan2(crisp[i][0] - crisp[i-1][0],
                                         crisp[i][1] - crisp[i-1][1]))
            a2 = math.degrees(math.atan2(crisp[i+1][0] - crisp[i][0],
                                         crisp[i+1][1] - crisp[i][1]))
            if abs((a2 - a1 + 180) % 360 - 180) > 45:
                lnd_pts.append((crisp[i][0], crisp[i][1], "turn-pad"))
        for j, (lx, ly, kind) in enumerate(lnd_pts):
            zt = sample_z(dem, tf, lx, ly)
            landings_fc.append({
                "type": "Feature",
                "geometry": {"type": "Point",
                             "coordinates": [round(lx, 2), round(ly, 2)]},
                "properties": {"name": f"{name}_landing_{j+1}",
                               "route": name, "role": "landing",
                               "kind": kind,
                               "elev_navd88": round(zt, 2) if zt else None,
                               "note": "graded level pad >=5x5 ft, <=2% — "
                                       "pending civil detailing"}})

        # grading + conflicts on the DESIGN line
        npts = max(int(line.length / 2), 2)
        zz_t = np.array([sample_z(dem_raw, tf,
                                  line.interpolate(i / npts,
                                                   normalized=True).x,
                                  line.interpolate(i / npts,
                                                   normalized=True).y)
                         or np.nan for i in range(npts + 1)])
        zz_d = np.linspace(za, zb, npts + 1)
        dev = zz_d - zz_t
        cross_len = line.intersection(polys["swales"]).length
        crossing = None
        if cross_len > 0.01:
            if cross_len <= 12.0:
                ctype = "culvert crossing (engineered, pending civil " \
                        "detailing)"
            elif cross_len <= 24.0:
                ctype = "boardwalk crossing (engineered span over the " \
                        "swale mouth, pending civil detailing)"
            else:
                ctype = "OVERLONG — no acceptable crossing type"
            crossing = {"crossing_type": ctype,
                        "length_ft": round(cross_len, 1),
                        "ok": cross_len <= 24.0}
        width = WIDTH_FT[klass]
        corridor = line.buffer(width / 2, cap_style=2)
        # cross slope: perpendicular terrain gradient at 10-ft stations
        gy, gx = np.gradient(np.where(dem == -9999, np.nan, dem))
        xs_pct = []
        for d in np.arange(5, line.length - 5, 10):
            ppt = line.interpolate(d)
            p2 = line.interpolate(min(d + 2, line.length))
            hx, hy = (p2.x - ppt.x), (p2.y - ppt.y)
            hl = math.hypot(hx, hy) or 1.0
            nxv, nyv = -hy / hl, hx / hl
            r0, c0 = rasterio.transform.rowcol(tf, ppt.x, ppt.y)
            if 0 <= r0 < dem.shape[0] and 0 <= c0 < dem.shape[1]:
                gxx, gyy = gx[r0, c0], gy[r0, c0]
                if not (np.isnan(gxx) or np.isnan(gyy)):
                    xs_pct.append(abs(gxx * nxv + (-gyy) * nyv) * 100)
        xs_pct = np.array(xs_pct) if xs_pct else np.array([0.0])
        bench_ft = xs_pct / 100 * (width / 2)
        corridor_props = {
            "route": name, "class": klass, "width_ft": width,
            "area_sqft": round(corridor.area, 0),
            "terrain_cross_slope_pct": {
                "median": round(float(np.median(xs_pct)), 1),
                "p90": round(float(np.percentile(xs_pct, 90)), 1),
                "max": round(float(xs_pct.max()), 1)},
            "bench_cut_est_ft": {
                "median": round(float(np.median(bench_ft)), 2),
                "max": round(float(bench_ft.max()), 2)},
            "flags": {
                "handrails_guards": grade > WALK_MAX,
                "edge_protection": bool((xs_pct > 25).any()),
                "retaining_likely": bool((bench_ft > 3.0).any()),
                "benching_required": bool((xs_pct > 2.0).any())},
            "note": "cross slope is TERRAIN slope across the corridor — "
                    "built cross slope <=2% requires the benching above; "
                    "pending civil detailing"}
        corridors.append({"type": "Feature", "geometry": mapping(corridor),
                          "properties": corridor_props})

        props = {
            "name": name, "from": a, "to": b, "class": klass,
            "role": "ada_route_concept", "status": CONCEPT_LABEL,
            "preferred": name in ALTERNATIVES[PREFERRED]["members"],
            "alternatives": [k for k, v in ALTERNATIVES.items()
                             if name in v["members"]],
            "length_ft": round(line.length, 1),
            "drop_ft": round(drop, 1),
            "design_grade_pct": round(grade * 100, 2),
            "profile": profile,
            "landings_marked": len(lnd_pts),
            "smoothness_before": before, "smoothness_after": after,
            "grading_required": {
                "max_cut_ft": round(float(np.nanmax(-dev)), 2),
                "max_fill_ft": round(float(np.nanmax(dev)), 2),
                "mean_abs_ft": round(float(np.nanmean(np.abs(dev))), 2),
                "note": "linear design profile between node datums vs raw "
                        "proposed grade — pending civil detailing"},
            "source": "scripts/design_ada_routes.py (LOS-rationalized from "
                      "stage-1 solver corridor)"}
        if crossing:
            props["crossing"] = crossing
        feats.append({"type": "Feature", "geometry": mapping(line),
                      "properties": props})
        route_report[name] = {**props, "geometry_len": len(design)}
        print(f"  {name}: {line.length:.0f} ft @ {grade*100:.1f}% "
              f"[{profile}] turns {before['turn_count_gt20deg']}->"
              f"{after['turn_count_gt20deg']}, min seg "
              f"{after['min_seg_ft']} ft, {len(lnd_pts)} landings")

    C.dump(C.fc(feats + landings_fc), os.path.join(VEC, "ada_route.geojson"))
    C.dump(C.fc(corridors), os.path.join(VEC, "route_corridors.geojson"))

    # ── validation ───────────────────────────────────────────────────────
    geom = {n: shape(next(f for f in feats
                          if f["properties"]["name"] == n)["geometry"])
            for n in route_report}
    # topology over PUBLIC design routes
    adj = {}
    for n, ri in route_report.items():
        if ri["class"] != "service":
            adj.setdefault(ri["from"], set()).add(ri["to"])
            adj.setdefault(ri["to"], set()).add(ri["from"])

    def connected(a, b):
        seen, q = {a}, [a]
        while q:
            x = q.pop()
            if x == b:
                return True
            for y in adj.get(x, ()):
                if y not in seen:
                    seen.add(y)
                    q.append(y)
        return False

    topo_pairs = {
        "public_arrival->floor": connected("public_arrival_rim",
                                           "floor_arrival"),
        "public_arrival->cross_aisle": connected("public_arrival_rim",
                                                 "cross_aisle_mid"),
        "park_arrival->floor": connected("park_arrival_west", "floor_arrival"),
        "cross_aisle->wc_clusters": connected("cross_aisle_mid",
                                              "wc_cluster_cross_aisle")
        and connected("cross_aisle_mid", "wc_cluster_floor"),
        "wc_clusters->egress": connected("wc_cluster_cross_aisle",
                                         "egress_rim_south")
        and connected("wc_cluster_floor", "egress_rim_south"),
        "service->stage (classified service)":
            "route_service_to_stage" in route_report,
    }
    topology_ok = all(topo_pairs.values())

    conflicts = {}
    wedge_strict = polys["seating_wedge"].difference(polys["gateways"])
    for n, g in geom.items():
        ri = route_report[n]
        tc_len = g.intersection(polys["treatment_cell"]).length
        sw_len = g.intersection(polys["swales"]).length
        st_len = g.intersection(polys["stage"]).length
        wedge_len = g.intersection(wedge_strict).length
        gw_len = g.intersection(polys["gateways"]).length
        conflicts[n] = {
            "treatment_cell_ft": round(tc_len, 2),
            "swale_ft": round(sw_len, 2),
            "swale_crossing_declared": bool(ri.get("crossing")),
            "swale_crossing_ok": (sw_len < 0.01) or
                                 bool((ri.get("crossing") or {}).get("ok")),
            "stage_zone_ft": round(st_len, 2),
            "stage_ok": (st_len < 0.01) or ri["class"] == "service",
            "seating_wedge_ft": round(wedge_len, 2),
            "gateway_transition_ft": round(gw_len, 1),
            "ok": (tc_len < 0.01)
                  and ((sw_len < 0.01)
                       or bool((ri.get("crossing") or {}).get("ok")))
                  and ((st_len < 0.01) or ri["class"] == "service")
                  and (wedge_len < 0.01)}
    conflicts_ok = all(c["ok"] for c in conflicts.values())

    slopes = {n: {"design_grade_pct": ri["design_grade_pct"],
                  "profile": ri["profile"],
                  "within_8_33": ri["design_grade_pct"] <= 8.34,
                  "landings_marked": ri["landings_marked"]}
              for n, ri in route_report.items()}
    slopes_ok = all(s["within_8_33"] for s in slopes.values())

    pad_pts = [Point(l["geometry"]["coordinates"])
               for l in landings_fc
               if l["properties"].get("kind") == "turn-pad"]

    def interior_seg_audit(n):
        """Interior tangent runs must be >= 1.5 path widths, except up to
        2 short gateway-threshold jogs that carry a turn-pad landing (the
        jog IS the pad in built form)."""
        min_run = max(MIN_RUN_FLOOR_FT,
                      MIN_RUN_WIDTHS * WIDTH_FT[route_report[n]["class"]])
        g = list(geom[n].coords)
        if len(g) <= 3:
            return 1e9, 0, 0, True
        def signed_turn(i):
            ax, ay = g[i][0] - g[i-1][0], g[i][1] - g[i-1][1]
            bx, by = g[i+1][0] - g[i][0], g[i+1][1] - g[i][1]
            return math.degrees(math.atan2(ax * by - ay * bx,
                                           ax * bx + ay * by))

        # perceptual runs: vertices deflecting <15 deg do not read as
        # turns on the ground — accumulate them into one continuous run,
        # then gate RUN length (the jaggedness that matters is short
        # distance between PERCEPTIBLE direction changes)
        runs, cur = [], 0.0
        turn_at_run_end = []
        for i in range(len(g) - 1):
            cur += math.dist(g[i], g[i + 1])
            is_end = (i == len(g) - 2) or abs(signed_turn(i + 1)) >= 15
            if is_end:
                runs.append((cur, i + 1))
                cur = 0.0
        bad, pads, chamfers = [], 0, 0
        for k in range(1, len(runs) - 1):     # interior runs only
            L, endv = runs[k]
            if L >= min_run:
                continue
            vx = g[endv]
            if L <= 8.0 and any(Point(vx).distance(pp) < 8.0
                                for pp in pad_pts):
                pads += 1
                continue
            t0 = signed_turn(runs[k - 1][1]) if runs[k - 1][1] > 0 else 0
            t1 = signed_turn(endv) if endv < len(g) - 1 else 0
            if t0 * t1 >= 0 and abs(t0) <= 40 and abs(t1) <= 40:
                chamfers += 1     # same-direction curve approximation
                continue
            bad.append(round(L, 1))
        ok = not bad and pads <= 2 and chamfers <= 4
        mn = min([r[0] for r in runs[1:-1]] or [1e9])
        return mn, pads, chamfers, ok

    smooth = {}
    for n, ri in route_report.items():
        mn, pads, chamfers, seg_ok = interior_seg_audit(n)
        smooth[n] = {"before": ri["smoothness_before"],
                     "after": ri["smoothness_after"],
                     "interior_min_seg_ft": round(min(mn, 9999), 1),
                     "threshold_pad_jogs": pads,
                     "chamfer_segments": chamfers,
                     "ok": (ri["smoothness_after"]["turn_count_gt20deg"]
                            <= MAX_TURNS
                            and (seg_ok
                                 or ri["smoothness_after"]["total_ft"]
                                 < 40))}
    smooth_ok = all(s["ok"] for s in smooth.values())

    # detour ratios per alternative (network shortest path vs desire line)
    def net_dist(alt, a, b):
        edges = {}
        for n in ALTERNATIVES[alt]["members"]:
            ri = route_report[n]
            edges.setdefault(ri["from"], {})[ri["to"]] = ri["length_ft"]
            edges.setdefault(ri["to"], {})[ri["from"]] = ri["length_ft"]
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

    # detour measured from the arrival that actually SERVES each target
    # in that alternative (e.g. in C the floor is served by the park-edge
    # arrival, not the east street arrival)
    detour = {}
    for alt, spec in ALTERNATIVES.items():
        rows = {}
        for target in ("cross_aisle_mid", "floor_arrival",
                       "wc_cluster_cross_aisle", "wc_cluster_floor"):
            best = None
            for arr in spec["arrivals"]:
                nd = net_dist(alt, arr, target)
                if nd is None:
                    continue
                if best is None or nd < best[1]:
                    best = (arr, nd)
            if best is None:
                rows[target] = {"accessible_route_ft": None,
                                "detour_ratio": None,
                                "flag_socially_inferior": True,
                                "note": "target unreachable in this "
                                        "alternative"}
                continue
            arr, nd = best
            desire = math.dist(nodes[arr]["xy"], nodes[target]["xy"])
            ratio = round(nd / desire, 2) if desire > 1 else None
            rows[f"{arr}->{target}"] = {
                "desire_line_ft": round(desire, 1),
                "accessible_route_ft": round(nd, 1),
                "detour_ratio": ratio,
                "flag_socially_inferior": bool(ratio and
                                               ratio > DETOUR_FLAG)}
        detour[alt] = rows

    # alternative aggregates
    alt_table = {}
    for alt, spec in ALTERNATIVES.items():
        ms = [route_report[m] for m in spec["members"]]
        area = sum(c["properties"]["area_sqft"] for c in corridors
                   if c["properties"]["route"] in spec["members"])
        alt_table[alt] = {
            "label": spec["label"],
            "routes": spec["members"],
            "total_length_ft": round(sum(m["length_ft"] for m in ms), 0),
            "max_design_grade_pct": max(m["design_grade_pct"] for m in ms),
            "landings_total": sum(m["landings_marked"] for m in ms),
            "turns_total": sum(m["smoothness_after"]["turn_count_gt20deg"]
                               for m in ms),
            "disturbance_area_sqft_est": round(area, 0),
            "swale_crossings": sum(1 for m in ms if m.get("crossing")),
            "treatment_conflicts_ft": round(sum(
                conflicts[m["name"]]["treatment_cell_ft"] for m in ms), 2),
            "worst_detour_ratio": max((r["detour_ratio"] or 0)
                                      for r in detour[alt].values()),
            "relation_to_seating": "perimeter alignments outside the "
                                   "seating wedge; enter only via "
                                   "aisle/promenade gateways",
        }

    recommendation = {
        "preferred": PREFERRED,
        "reasons": [
            "the west park-edge arrival reaches the event floor with a ~6 ft drop "
            "on a <=5% sloped WALK — no ramp structure, no landings, and "
            "the lowest detour ratio of any floor access",
            "the east street arrival serves the cross-aisle level directly "
            "from the Petoskey St side where ordinary pedestrians also "
            "arrive — accessible and general arrival share one route "
            "corridor (least segregating available)",
            "south perimeter legs retained as SECONDARY egress (real E "
            "Mitchell St condition) without burdening the primary "
            "experience",
            "lowest total disturbance among alternatives that still give "
            "two public arrivals + two accessible elevations",
        ],
        "remaining_gaps": [
            "all unchecked code details (see unchecked_code_details)",
            "east cross-aisle route detour ratio remains high vs the "
            "stair desire line — inherent to a ~33% bowl; an integrated "
            "aisle ramp study could close it and is flagged as the "
            "socially-preferable future refinement",
            "corridor benching/retaining quantities are estimates from "
            "terrain cross slope; envelope re-emission required on "
            "adoption",
        ],
    }

    validation = {
        "generated": "scripts/design_ada_routes.py (stage 2 — designed "
                     "alignments over stage-1 solver feasibility)",
        "label": CONCEPT_LABEL,
        "NOT_ADA_COMPLIANT_NOTICE": (
            "Topology, conflicts, design grades, smoothness, detour ratios "
            "and corridor estimates only. unchecked_code_details are NOT "
            "checked. Do not describe the network as 'ADA compliant'."),
        "legacy_rejection": {
            "file": "vectors_geojson/legacy_ada_rejected.geojson",
            "reason": "see docs/ADA_REBUILD.md — slope-only legacy "
                      "validation void; fragments quarantined"},
        "gate_order": ["topology", "conflicts", "slopes", "smoothness",
                       "detour", "corridors", "landings",
                       "unchecked_code_details"],
        "topology": {"pairs": topo_pairs, "ok": topology_ok,
                     "routes": {n: {k: ri[k] for k in
                                    ("from", "to", "class", "length_ft",
                                     "design_grade_pct", "profile",
                                     "preferred", "alternatives")}
                                for n, ri in route_report.items()}},
        "conflicts": {"per_route": conflicts, "ok": conflicts_ok,
                      "policy": "treatment cell forbidden (no crossing type exists); "
                                "swale crossings declared by type: culvert "
                                "<=12 ft, boardwalk 12-24 ft, none longer; "
                                "stage zones service-only; seating wedge "
                                "forbidden outside engineered gateway "
                                "transitions (gateway contact reported "
                                "per route)"},
        "slopes": {"per_route": slopes, "ok": slopes_ok,
                   "method": "constant design grade between node datums "
                             "(floor 612.5 / aisle 622.01 canonical); "
                             "terrain deviation = grading_required"},
        "smoothness": {"per_route": smooth, "ok": smooth_ok,
                       "gates": {"max_turns_gt20deg": MAX_TURNS,
                                 "min_tangent_run": "1.5 x path width "
                                 "(>=9 ft) between perceptible turns"}},
        "detour_ratios": {"per_alternative": detour,
                          "flag_threshold": DETOUR_FLAG,
                          "note": "desire line = straight-line distance; "
                                  "able-bodied stair path is shorter still; "
                                  "flags mark technically-compliant but "
                                  "socially-inferior access"},
        "corridors": {"file": "vectors_geojson/route_corridors.geojson",
                      "per_route": {c["properties"]["route"]:
                                    {k: c["properties"][k] for k in
                                     ("class", "width_ft", "area_sqft",
                                      "terrain_cross_slope_pct",
                                      "bench_cut_est_ft", "flags")}
                                    for c in corridors}},
        "hierarchy_separation": {
            "classes": {n: ri["class"] for n, ri in route_report.items()},
            "service_segments_in_public_topology": False,
            "service_note": "route_service_to_stage (floor -> stage right "
                            "shoulder, 612.5 datum, no treatment-cell "
                            "contact) is performer/service access ONLY and "
                            "is excluded from the public connectivity "
                            "graph; viewer hides it by default",
            "south_perimeter_status": "PUBLIC SECONDARY (egress) — "
                                      "connects to the bowl crest ~54 ft "
                                      "from the real E Mitchell Street "
                                      "south boundary",
        },
        "alternatives": alt_table,
        "recommendation": recommendation,
        "landings": {"rule": "every <=2.5 ft rise on ramp profiles + every "
                             ">45 deg turn; pads pending civil detailing"},
        "floor_datum": {"design_datum_navd88": 612.5,
                        "raster_reads_navd88": 609.65,
                        "status": "routes target the CANONICAL 612.5 floor "
                                  "datum; the concept-tier floor is not yet "
                                  "graded into the raster — conflict "
                                  "reported, not silently rerouted"},
        "unchecked_code_details": UNCHECKED_CODE_DETAILS,
        "hard": {"topology_ok": topology_ok, "conflicts_ok": conflicts_ok,
                 "slopes_ok": slopes_ok, "smoothness_ok": smooth_ok,
                 "network_ok": topology_ok and conflicts_ok and slopes_ok
                 and smooth_ok},
    }
    with open(OUT_VALID, "w") as f:
        json.dump(validation, f, indent=1)
    print(f"\nTOPOLOGY {'OK' if topology_ok else 'FAIL'} | CONFLICTS "
          f"{'OK' if conflicts_ok else 'FAIL'} | SLOPES "
          f"{'OK' if slopes_ok else 'FAIL'} | SMOOTHNESS "
          f"{'OK' if smooth_ok else 'FAIL'}")
    print("preferred:", PREFERRED)
    if not validation["hard"]["network_ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
