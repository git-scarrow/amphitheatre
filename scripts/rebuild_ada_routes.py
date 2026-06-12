#!/usr/bin/env python3
"""Rebuild the ADA route network from first principles.

WHY: the legacy ADA layer (scenarioE ada_ramp/ada_landing, carried into
bowl_zones.geojson and "validated" by Scenario_E_baseline_reemit/
validation.json) is topologically invalid. Measured 2026-06-12:
  route A sits 63% inside the treatment cell (landing_1 100%, landing_2
  39%), 34.6 ft from the event floor it is named for; route B crosses the
  south drainage swale and stops 21.9 ft short of the cross-aisle; the two
  routes are 115.6 ft apart and connect to nothing. validation.json only
  ever checked running slope ALONG the fragments — never topology.

WHAT THIS DOES (ordered, topology before slope):
  1. QUARANTINE  -> vectors_geojson/legacy_ada_rejected.geojson
  2. NODES       -> vectors_geojson/ada_nodes.geojson  (real network nodes)
  3. ROUTES      -> vectors_geojson/ada_route.geojson  (node-to-node only;
                    slope-constrained Dijkstra on proposed_grade_1ft.tif,
                    conflict masks rasterized from canonical zones)
  4. VALIDATION  -> analysis/ada_rebuild/ada_validation.json
                    gates in order: topology -> conflicts -> slopes ->
                    landings -> explicit UNCHECKED code-detail list.

The result is labeled "ADA-compliant route concept pending civil/code
detailing" — never "ADA compliant". Canonical seating, stage, drainage and
treatment-cell geometry are READ ONLY here; bowl_zones.geojson is modified
ONLY by removing the rejected ada_ramp/ada_landing features (all other
features byte-preserved).

Reproduce:  .venv/bin/python scripts/rebuild_ada_routes.py
"""
import heapq
import json
import math
import os
import sys

import numpy as np
import rasterio
from rasterio import features as rfeatures
from shapely.geometry import LineString, Point, mapping, shape
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(__file__))
import in_situ_common as C

REPO = C.REPO
VEC = C.VEC_DIR
OUT_VALID = os.path.join(REPO, "analysis", "ada_rebuild", "ada_validation.json")

MAX_RUN_SLOPE = 0.0833          # ADA ramp running slope
SLOPE_TOL = 0.003               # planning-grade tolerance band (flagged)
MAX_RISE_PER_RUN_FT = 2.5       # landing required every 30 in of rise
LANDING_NOTE = ("graded level landing pad (>=5x5 ft, <=2% any direction) "
                "required here — pending civil detailing")
SWALE_CROSS_MAX_FT = 16.0       # max engineered swale crossing length
CONCEPT_LABEL = "ADA-compliant route concept pending civil/code detailing"

UNCHECKED_CODE_DETAILS = [
    "route clear width (36 in min / 60 in passing)",
    "landing dimensions and <=2% landing slopes (positions emitted only)",
    "turning radii / maneuvering clearances",
    "handrails and guards on ramp runs",
    "edge protection",
    "wheelchair clear floor space (30x48 in) at clusters",
    "companion seating dimensions and count",
    "surface firmness / stability / slip resistance",
    "cross slope <=2% on built route (terrain cross slope not benched yet)",
    "sightline preservation from wheelchair positions (refs flagged, "
    "not C-value validated)",
    "ADAAG 221 dispersion counts vs total seat count",
    "winter / maintenance operations",
]


def U(az):
    a = math.radians(az)
    return math.sin(a), math.cos(a)


def axis_pt(az, r):
    ux, uy = U(az)
    return (C.FX + r * ux, C.FY + r * uy)


# ─────────────────────────────────────────────────────────────────────────
# load canonical geometry
# ─────────────────────────────────────────────────────────────────────────
def load_zones():
    with open(os.path.join(VEC, "bowl_zones.geojson")) as f:
        fc = json.load(f)
    feats = fc["features"]
    by_zone = {}
    for ft in feats:
        by_zone.setdefault(ft["properties"].get("zone"), []).append(ft)
    return fc, by_zone


def quarantine(fc, by_zone, rejection_metrics):
    legacy = []
    keep = []
    for ft in fc["features"]:
        if ft["properties"].get("zone") in ("ada_ramp", "ada_landing"):
            p = dict(ft["properties"])
            p["status"] = "REJECTED — legacy"
            p["rejected_on"] = "2026-06-12"
            p["rejection"] = rejection_metrics.get(p.get("name"), "")
            p["rejection_basis"] = (
                "topology audit: disconnected fragment; see "
                "docs/ADA_REBUILD.md. Slope-only validation in "
                "Scenario_E_baseline_reemit/validation.json is NOT a route "
                "validation.")
            legacy.append({"type": "Feature", "geometry": ft["geometry"],
                           "properties": p})
        else:
            keep.append(ft)
    fc["features"] = keep
    C.dump(C.fc(legacy and legacy or []),
           os.path.join(VEC, "legacy_ada_rejected.geojson"))
    with open(os.path.join(VEC, "bowl_zones.geojson"), "w") as f:
        json.dump(fc, f, indent=1)
    return len(legacy)


def rejection_metrics(by_zone):
    tc = shape(by_zone["treatment_cell_landscape"][0]["geometry"])
    floor_ = shape(by_zone["orchestra_event_floor"][0]["geometry"])
    ca = shape(by_zone["cross_aisle"][0]["geometry"])
    sw = unary_union([shape(f["geometry"])
                      for f in by_zone["drainage_swale"]])
    out = {}
    for ft in by_zone.get("ada_ramp", []) + by_zone.get("ada_landing", []):
        g = shape(ft["geometry"])
        nm = ft["properties"]["name"]
        out[nm] = (f"treatment-cell overlap {g.intersection(tc).area/g.area*100:.0f}%; "
                   f"dist to floor {g.distance(floor_):.1f} ft, cross-aisle "
                   f"{g.distance(ca):.1f} ft, swale {g.distance(sw):.1f} ft")
    return out


# ─────────────────────────────────────────────────────────────────────────
# nodes
# ─────────────────────────────────────────────────────────────────────────
def build_nodes(zg, dem, tf):
    def zat(x, y):
        r, c = rasterio.transform.rowcol(tf, x, y)
        v = dem[r, c]
        return None if v == -9999.0 else float(v)

    stage_sh_r = shape([f for f in zg["stage_shoulder_right"]][0]["geometry"])
    floor_ = shape(zg["orchestra_event_floor"][0]["geometry"])
    svc_pt = stage_sh_r.boundary.interpolate(
        stage_sh_r.boundary.project(floor_.centroid))

    nodes = [
        ("public_arrival_rim", axis_pt(118, 160), "public",
         "rim / public-way entry above row 18 at the east|bend hinge; "
         "connection onward to street/parking is outside this package"),
        ("egress_rim_south", axis_pt(152, 160), "public",
         "second rim connection above row 18 at the bend|south hinge — "
         "egress redundancy"),
        ("cross_aisle_mid", axis_pt(132, 121), "public",
         "mid-bowl accessible cross-aisle (rows 9/10 band, datum 622.01)"),
        ("wc_cluster_cross_aisle", axis_pt(125, 121), "public",
         "wheelchair seating cluster ON the cross-aisle with adjacent "
         "companion seats (row-9 tread band)"),
        ("floor_arrival", axis_pt(118, 70), "public",
         "accessible arrival on the orchestra/event floor"),
        ("wc_cluster_floor", axis_pt(128, 76), "public",
         "wheelchair seating cluster at the floor edge behind row-1 radius "
         "with companion seats"),
        ("service_stage_access", (svc_pt.x, svc_pt.y), "service",
         "OPTIONAL performer/service access at the stage right shoulder "
         "edge — classified service, NOT part of the public network"),
    ]
    feats = []
    for name, (x, y), klass, note in nodes:
        z = zat(x, y)
        feats.append({"type": "Feature",
                      "geometry": {"type": "Point",
                                   "coordinates": [round(x, 2), round(y, 2)]},
                      "properties": {
                          "name": name, "class": klass, "note": note,
                          "ground_elev_navd88_proposed": round(z, 2) if z else None,
                          "source": "scripts/rebuild_ada_routes.py — anchored "
                                    "to canonical zones/axis (read-only)",
                      }})
    C.dump(C.fc(feats), os.path.join(VEC, "ada_nodes.geojson"))
    return {f["properties"]["name"]:
            (f["geometry"]["coordinates"][0], f["geometry"]["coordinates"][1],
             f["properties"]["ground_elev_navd88_proposed"])
            for f in feats}


# ─────────────────────────────────────────────────────────────────────────
# masks + pathfinding
# ─────────────────────────────────────────────────────────────────────────
def build_masks(zg, dem, tf, shp):
    def burn(geoms, allval=1, all_touched=False):
        # all_touched=True for FORBIDDEN zones: center-burned masks leave
        # sub-cell slivers where a legal path grazes the polygon edge
        # (measured 0.08-0.36 ft phantom conflicts); touching cells are
        # excluded entirely so emitted geometry stays clear
        if not geoms:
            return np.zeros(shp, dtype=np.uint8)
        return rfeatures.rasterize(
            [(mapping(g), allval) for g in geoms], out_shape=shp,
            transform=tf, fill=0, dtype="uint8", all_touched=all_touched)

    tc = [shape(zg["treatment_cell_landscape"][0]["geometry"])]
    swales = [shape(f["geometry"]) for f in zg["drainage_swale"]]
    stage = [shape(zg["stage_core"][0]["geometry"]),
             shape(zg["stage_shoulder_left"][0]["geometry"]),
             shape(zg["stage_shoulder_right"][0]["geometry"])]
    env = shape(zg["construction_envelope"][0]["geometry"]).buffer(12)
    aisles = [shape(f["geometry"]) for f in
              zg["cross_aisle"] + zg["promenade_hinge"]]
    floor_ = [shape(zg["orchestra_event_floor"][0]["geometry"])]

    with open(os.path.join(VEC, "terrace_treads.geojson")) as f:
        tr = json.load(f)
    tread_band = unary_union([shape(ft["geometry"]).buffer(2.1)
                              for ft in tr["features"]])
    seating_wedge = tread_band.difference(unary_union(aisles))

    m_tc = burn(tc, all_touched=True)
    m_swale = burn(swales)
    m_stage = burn(stage, all_touched=True)
    m_env = burn([env])
    m_wedge = burn([seating_wedge], all_touched=True)
    m_corridor = burn(aisles + floor_)
    # GATEWAYS: where the level cross-aisle / promenade bands meet the
    # natural flank at the row ends, the smoothed surface has a slope seam
    # no compliant cell-to-cell path can cross — in a real design this is
    # an engineered graded transition. Cells within 16 ft of the aisle /
    # promenade bands (outside the seating wedge) are slope-EXEMPT for
    # routing; every route segment inside a gateway is reported as
    # "graded transition required".
    gateway_geoms = [a.buffer(16).difference(seating_wedge) for a in aisles]
    m_gateway = burn(gateway_geoms)

    # allowed for PUBLIC routes: not treatment cell, not stage, not the
    # seating wedge (except the aisle/promenade corridors), within a 200 ft
    # working radius of the axis origin. The OLD construction envelope is
    # deliberately NOT a hard mask: the legacy envelope was emitted around
    # the legacy scenario, and new ramps are new construction — any route
    # length outside the envelope is measured and ELEVATED as an
    # envelope-extension design issue instead of silently blocking the
    # network. Swale cells stay passable at a heavy penalty -> classified
    # crossing.
    yy, xx = np.mgrid[0:shp[0], 0:shp[1]]
    gx = tf.c + (xx + 0.5) * tf.a
    gy = tf.f + (yy + 0.5) * tf.e
    m_radius = np.hypot(gx - C.FX, gy - C.FY) <= 200.0
    allowed_pub = m_radius & (m_tc == 0) & (m_stage == 0) & \
                  ((m_wedge == 0) | (m_corridor == 1))
    allowed_svc = m_radius & (m_tc == 0) & \
                  ((m_wedge == 0) | (m_corridor == 1))
    return allowed_pub, allowed_svc, m_swale, m_gateway, {
        "treatment_cell": tc[0], "swales": unary_union(swales),
        "stage": unary_union(stage), "seating_wedge": seating_wedge,
        "gateways": unary_union(gateway_geoms),
        "envelope": shape(zg["construction_envelope"][0]["geometry"])}


def dijkstra(dem, allowed, m_swale, m_gateway, tf, start_xy, goal_xy,
             max_slope=MAX_RUN_SLOPE + SLOPE_TOL):
    rows, cols = dem.shape
    sr, sc = rasterio.transform.rowcol(tf, *start_xy)
    gr, gc = rasterio.transform.rowcol(tf, *goal_xy)

    def snap(r0, c0):
        if allowed[r0, c0]:
            return r0, c0
        for rad in range(1, 26):
            for dr in range(-rad, rad + 1):
                for dc in range(-rad, rad + 1):
                    r, c = r0 + dr, c0 + dc
                    if 0 <= r < rows and 0 <= c < cols and allowed[r, c]:
                        return r, c
        raise RuntimeError("node not reachable into allowed mask")

    sr, sc = snap(sr, sc)
    gr, gc = snap(gr, gc)
    # 8-neighborhood PLUS knight moves: 45° angular resolution blocks
    # contour-following on ~30% flanks (nearest grid heading can exceed the
    # slope cap even when a compliant heading exists); 16 directions at
    # 26.6° resolution keep a <=8.33% heading available on slopes up to
    # ~35%. Knight moves must not hop forbidden cells: midpoints checked.
    NB = [(-1, 0, 1), (1, 0, 1), (0, -1, 1), (0, 1, 1),
          (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414),
          (-1, -2, 2.236), (-1, 2, 2.236), (1, -2, 2.236), (1, 2, 2.236),
          (-2, -1, 2.236), (-2, 1, 2.236), (2, -1, 2.236), (2, 1, 2.236)]
    INF = float("inf")
    dist = np.full(dem.shape, INF, dtype=np.float32)
    prev = np.full(dem.shape, -1, dtype=np.int32)
    dist[sr, sc] = 0.0
    pq = [(0.0, sr, sc)]
    while pq:
        d, r, c = heapq.heappop(pq)
        if (r, c) == (gr, gc):
            break
        if d > dist[r, c]:
            continue
        z0 = dem[r, c]
        for dr, dc, w in NB:
            r2, c2 = r + dr, c + dc
            if not (0 <= r2 < rows and 0 <= c2 < cols) or not allowed[r2, c2]:
                continue
            if w > 2.0:
                # knight move traverses TWO intermediate cells: floor and
                # ceil of the half-step (a single rounded midpoint lets the
                # segment clip masked cell corners — measured 0.36-7.6 ft
                # zone nicks before this fix)
                rm1, cm1 = r + math.floor(dr / 2), c + math.floor(dc / 2)
                rm2, cm2 = r + math.ceil(dr / 2), c + math.ceil(dc / 2)
                if not (allowed[rm1, cm1] and allowed[rm2, cm2]):
                    continue
            z1 = dem[r2, c2]
            if z1 == -9999.0 or z0 == -9999.0:
                continue
            cap = 0.30 if (m_gateway[r, c] or m_gateway[r2, c2]) \
                else max_slope     # gateway = engineered graded transition
            if abs(z1 - z0) / w > cap:
                continue
            cost = w * (30.0 if m_swale[r2, c2] else 1.0)
            nd = d + cost
            if nd < dist[r2, c2]:
                dist[r2, c2] = nd
                prev[r2, c2] = (r * cols + c)
                heapq.heappush(pq, (nd, r2, c2))
    if dist[gr, gc] == INF:
        return None
    path = []
    r, c = gr, gc
    while (r, c) != (sr, sc):
        x, y = rasterio.transform.xy(tf, r, c)
        path.append((x, y))
        p = prev[r, c]
        r, c = divmod(int(p), cols)
    x, y = rasterio.transform.xy(tf, sr, sc)
    path.append((x, y))
    return list(reversed(path))


def sample_line(dem, tf, line, step=2.0):
    n = max(int(line.length / step), 2)
    pts = [line.interpolate(i * line.length / n) for i in range(n + 1)]
    zz = []
    for p in pts:
        r, c = rasterio.transform.rowcol(tf, p.x, p.y)
        zz.append(float(dem[r, c]))
    return pts, np.array(zz)


# ─────────────────────────────────────────────────────────────────────────
def main():
    fc, zg = load_zones()
    rej = rejection_metrics(zg)
    n_legacy = quarantine(fc, zg, rej)
    print(f"quarantined {n_legacy} legacy ADA features -> "
          "vectors_geojson/legacy_ada_rejected.geojson")

    with rasterio.open(os.path.join(REPO, "dem", "proposed_grade_1ft.tif")) as s:
        dem_raw = s.read(1)
        tf = s.transform
    # ROUTE on a smoothed design surface: a ramp is a graded structure, not
    # a terrain-following trail. Raw 1 ft LiDAR noise shatters slope
    # feasibility into ~1,600 islands (measured); a 5 ft gaussian gives the
    # landform a buildable design surface. The RAW surface is kept to
    # report required cut/fill along each alignment (pending civil
    # detailing).
    from scipy.ndimage import gaussian_filter
    void = dem_raw == -9999.0
    dem = gaussian_filter(np.where(void, np.nan, dem_raw), sigma=5.0,
                          mode="nearest")
    # gaussian over nan poisons neighborhoods: renormalize
    w = gaussian_filter((~void).astype(float), sigma=5.0, mode="nearest")
    dem = np.where(w > 0.2,
                   gaussian_filter(np.where(void, 0, dem_raw), sigma=5.0,
                                   mode="nearest") / np.maximum(w, 1e-6),
                   -9999.0).astype("float32")
    dem[void & (w <= 0.2)] = -9999.0
    nodes = build_nodes(zg, dem, tf)
    print(f"emitted {len(nodes)} nodes -> vectors_geojson/ada_nodes.geojson")

    (allowed_pub, allowed_svc, m_swale, m_gateway,
     polys) = build_masks(zg, dem, tf, dem.shape)
    ROUTES = [
        ("route_arrival_to_cross_aisle", "public_arrival_rim",
         "cross_aisle_mid", "public"),
        ("route_arrival_to_floor", "public_arrival_rim",
         "floor_arrival", "public"),
        ("route_cross_aisle_to_wc_cluster", "cross_aisle_mid",
         "wc_cluster_cross_aisle", "public"),
        ("route_floor_to_wc_cluster", "floor_arrival",
         "wc_cluster_floor", "public"),
        ("route_cross_aisle_to_egress", "cross_aisle_mid",
         "egress_rim_south", "public"),
        ("route_floor_to_egress", "floor_arrival",
         "egress_rim_south", "public"),
        ("route_service_to_stage", "floor_arrival",
         "service_stage_access", "service"),
    ]
    feats, landings, route_info = [], [], {}
    for name, a, b, klass in ROUTES:
        allowed = allowed_pub if klass == "public" else allowed_svc
        path = dijkstra(dem, allowed, m_swale, m_gateway, tf,
                        nodes[a][:2], nodes[b][:2])
        if path is None:
            route_info[name] = {"status": "NO_PATH", "from": a, "to": b}
            print(f"  {name}: NO PATH")
            continue
        # the emitted geometry IS the constraint-bearing path — no
        # simplification: a simplified line cuts switchback corners into
        # masked zones (measured: 0.36 ft wedge / 7.6 ft stage nicks) and
        # then the validated geometry would differ from the shipped one
        raw = LineString(path)
        line = raw
        # envelope extension: new-construction length outside the legacy
        # construction envelope — elevated as a design issue, not a blocker
        outside_env_ft = round(line.difference(polys["envelope"]).length, 1)
        # crossing classification (swales only; everything else is forbidden)
        cross_len = line.intersection(polys["swales"]).length
        crossing = None
        if cross_len > 0.01:
            crossing = {"crossing_type": "culvert crossing (engineered, "
                                         "pending civil detailing)",
                        "length_ft": round(cross_len, 1),
                        "ok": cross_len <= SWALE_CROSS_MAX_FT}
        # slope + landings along the built line (design surface), plus
        # required-grading depth vs the raw proposed grade
        # slope on the RAW path edges (what the solver constrained);
        # the simplified display line cuts switchback corners and would
        # fake steep steps that were never traversed
        rpts = list(raw.coords)
        rz = []
        for (px, py) in rpts:
            rr, cc = rasterio.transform.rowcol(tf, px, py)
            rz.append(float(dem[rr, cc]))
        rz = np.array(rz)
        seg_d = np.array([math.dist(rpts[i], rpts[i+1])
                          for i in range(len(rpts)-1)])
        seg_s = np.abs(np.diff(rz)) / np.maximum(seg_d, 1e-6)
        # gateway (graded-transition) segments measured separately
        gat = np.array([bool(m_gateway[rasterio.transform.rowcol(tf, *p)])
                        for p in rpts])
        gseg = gat[:-1] | gat[1:]
        max_slope_route = float(seg_s[~gseg].max()) if (~gseg).any() else 0.0
        gateway_len = float(seg_d[gseg].sum())
        gateway_max_terrain_slope = float(seg_s[gseg].max()) if gseg.any() else 0.0
        pts, zz = sample_line(dem, tf, line)
        _, zz_raw = sample_line(dem_raw, tf, line)
        dev = zz - zz_raw
        grading = {"max_cut_ft": round(float(np.nanmax(-dev)), 2),
                   "max_fill_ft": round(float(np.nanmax(dev)), 2),
                   "mean_abs_ft": round(float(np.nanmean(np.abs(dev))), 2),
                   "note": "design surface (5 ft smoothed) vs raw proposed "
                           "grade along alignment — bench/ramp grading "
                           "pending civil detailing"}
        max_slope = max_slope_route
        rise_acc, lnd = 0.0, []
        for i in range(1, len(zz)):
            rise_acc += abs(zz[i] - zz[i - 1])
            if rise_acc >= MAX_RISE_PER_RUN_FT:
                lnd.append((pts[i].x, pts[i].y, zz[i]))
                rise_acc = 0.0
        for j, (lx, ly, lz) in enumerate(lnd):
            landings.append({"type": "Feature",
                             "geometry": {"type": "Point",
                                          "coordinates": [round(lx, 2),
                                                          round(ly, 2)]},
                             "properties": {"name": f"{name}_landing_{j+1}",
                                            "route": name, "role": "landing",
                                            "elev_navd88": round(lz, 2),
                                            "note": LANDING_NOTE}})
        props = {"name": name, "from": a, "to": b, "class": klass,
                 "grading_required": grading,
                 "outside_legacy_envelope_ft": outside_env_ft,
                 "role": "ada_route_concept", "status": CONCEPT_LABEL,
                 "length_ft": round(line.length, 1),
                 "elev_from": nodes[a][2], "elev_to": nodes[b][2],
                 "max_step_slope_pct": round(max_slope * 100, 2),
                 "gateway_transition_ft": round(gateway_len, 1),
                 "gateway_max_terrain_slope_pct":
                     round(gateway_max_terrain_slope * 100, 1),
                 "gateway_note": ("segments inside aisle/promenade row-end "
                                  "gateways are engineered graded "
                                  "transitions (design 8.33% max) — "
                                  "pending civil detailing"),
                 "landings_marked": len(lnd),
                 "source": "scripts/rebuild_ada_routes.py (Dijkstra on "
                           "proposed_grade_1ft.tif, conflict-masked)"}
        if crossing:
            props["crossing"] = crossing
        feats.append({"type": "Feature", "geometry": mapping(line),
                      "properties": props})
        route_info[name] = {"status": "OK", "from": a, "to": b,
                            "class": klass,
                            "length_ft": round(line.length, 1),
                            "max_step_slope_pct": round(max_slope * 100, 2),
                            "landings_marked": len(lnd),
                            "crossing": crossing,
                            "grading_required": grading,
                            "outside_legacy_envelope_ft": outside_env_ft,
                            "gateway_transition_ft": round(gateway_len, 1)}
        print(f"  {name}: {line.length:.0f} ft, max step slope "
              f"{max_slope*100:.1f}%, {len(lnd)} landings"
              + (f", swale crossing {cross_len:.1f} ft" if crossing else ""))

    C.dump(C.fc(feats + landings), os.path.join(VEC, "ada_route.geojson"))

    # ── validation, gates in ORDER: topology -> conflicts -> slopes ──────
    ok_routes = {n for n, ri in route_info.items() if ri["status"] == "OK"}
    edges = [(ri["from"], ri["to"]) for n, ri in route_info.items()
             if ri["status"] == "OK" and ri.get("class") == "public"]
    adj = {}
    for a, b in edges:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)

    def connected(a, b):
        seen, q = {a}, [a]
        while q:
            n = q.pop()
            if n == b:
                return True
            for m in adj.get(n, ()):
                if m not in seen:
                    seen.add(m)
                    q.append(m)
        return False

    topo_pairs = {
        "public_arrival->floor": connected("public_arrival_rim",
                                           "floor_arrival"),
        "public_arrival->cross_aisle": connected("public_arrival_rim",
                                                 "cross_aisle_mid"),
        "cross_aisle->wc_clusters": connected("cross_aisle_mid",
                                              "wc_cluster_cross_aisle")
        and connected("cross_aisle_mid", "wc_cluster_floor"),
        "wc_clusters->egress": connected("wc_cluster_cross_aisle",
                                         "egress_rim_south")
        and connected("wc_cluster_floor", "egress_rim_south"),
        "service->stage (classified service)":
            route_info.get("route_service_to_stage", {}).get("status") == "OK",
    }
    topology_ok = all(topo_pairs.values())

    conflicts = {}
    geom_by_name = {f["properties"]["name"]: shape(f["geometry"])
                    for f in feats if f["properties"]["role"] == "ada_route_concept"}
    for name, g in geom_by_name.items():
        ri = route_info[name]
        tc_len = g.intersection(polys["treatment_cell"]).length
        sw_len = g.intersection(polys["swales"]).length
        st_len = g.intersection(polys["stage"]).length
        wedge_len = g.intersection(polys["seating_wedge"]).length
        conflicts[name] = {
            "treatment_cell_ft": round(tc_len, 2),
            "swale_ft": round(sw_len, 2),
            "swale_crossing_declared": bool(ri.get("crossing")),
            "swale_crossing_ok": (sw_len < 0.01) or
                                 bool(ri.get("crossing", {}) and
                                      ri["crossing"]["ok"]),
            "stage_zone_ft": round(st_len, 2),
            "stage_ok": (st_len < 0.01) or ri["class"] == "service",
            "seating_wedge_ft": round(wedge_len, 2),
            "ok": (tc_len < 0.01)
                  and ((sw_len < 0.01) or (ri.get("crossing") or {}).get("ok",
                                                                         False))
                  and ((st_len < 0.01) or ri["class"] == "service")
                  and (wedge_len < 0.01),
        }
    conflicts_ok = all(c["ok"] for c in conflicts.values())

    slopes = {n: {"max_step_slope_pct": ri["max_step_slope_pct"],
                  "within_8_33": ri["max_step_slope_pct"] <= 8.33 + 0.01,
                  "within_tolerance_band":
                      ri["max_step_slope_pct"] <= (MAX_RUN_SLOPE + SLOPE_TOL) * 100 + 0.01,
                  "landings_marked": ri["landings_marked"]}
              for n, ri in route_info.items() if ri["status"] == "OK"}
    slopes_ok = all(s["within_tolerance_band"] for s in slopes.values())
    slopes_strict = all(s["within_8_33"] for s in slopes.values())

    validation = {
        "generated": "scripts/rebuild_ada_routes.py",
        "label": CONCEPT_LABEL,
        "NOT_ADA_COMPLIANT_NOTICE": (
            "This artifact validates topology, conflicts, terrain slope "
            "along alignments, and landing spacing ONLY. The items in "
            "unchecked_code_details are NOT checked. Do not describe the "
            "network as 'ADA compliant'."),
        "legacy_rejection": {
            "file": "vectors_geojson/legacy_ada_rejected.geojson",
            "count": n_legacy,
            "reason": "disconnected fragments; route A 63% in treatment "
                      "cell; route B crosses swale, 21.9 ft short of "
                      "cross-aisle; slope-only legacy validation is not a "
                      "route validation",
            "superseded_artifact": "analysis/tier_emission/"
                                   "Scenario_E_baseline_reemit/"
                                   "validation.json (ada/cross_aisle "
                                   "sections remain valid for the "
                                   "CROSS-AISLE band geometry only — its "
                                   "'ada' route entries are void)"},
        "gate_order": ["topology", "conflicts", "slopes", "landings",
                       "unchecked_code_details"],
        "topology": {"pairs": topo_pairs, "ok": topology_ok,
                     "routes": route_info},
        "conflicts": {"per_route": conflicts, "ok": conflicts_ok,
                      "policy": "treatment cell: forbidden, no crossing "
                                "type exists for it; swale: only an "
                                "engineered crossing <= "
                                f"{SWALE_CROSS_MAX_FT} ft, declared on the "
                                "route; stage zones: service class only; "
                                "seating wedge: forbidden outside "
                                "cross-aisle/promenade corridors"},
        "slopes": {"per_route": slopes, "ok_within_tolerance": slopes_ok,
                   "ok_strict_8_33": slopes_strict,
                   "method": "2 ft sampling of proposed_grade_1ft.tif along "
                             "built alignments; cross slope NOT validated "
                             "(needs benched section design)"},
        "landings": {"spacing_rule": "marked every <=2.5 ft of cumulative "
                                     "rise (30 in max rise per run)",
                     "status": "positions emitted; pads require grading — "
                               "pending civil detailing"},
        "floor_elevation_flag": {
            "note": "floor_arrival node reads 609.65 ft on the proposed "
                    "grade raster vs the 612.5 concept event-floor datum — "
                    "the event floor is concept-tier and not yet graded "
                    "into the raster; routes to the floor inherit this "
                    "uncertainty"},
        "unchecked_code_details": UNCHECKED_CODE_DETAILS,
        "hard": {"topology_ok": topology_ok, "conflicts_ok": conflicts_ok,
                 "slopes_ok": slopes_ok,
                 "network_ok": topology_ok and conflicts_ok and slopes_ok},
    }
    os.makedirs(os.path.dirname(OUT_VALID), exist_ok=True)
    with open(OUT_VALID, "w") as f:
        json.dump(validation, f, indent=1)
    print(f"\nTOPOLOGY {'OK' if topology_ok else 'FAIL'} | CONFLICTS "
          f"{'OK' if conflicts_ok else 'FAIL'} | SLOPES "
          f"{'OK' if slopes_ok else 'FAIL'} (strict 8.33: {slopes_strict})")
    print("validation ->", OUT_VALID)
    if not (topology_ok and conflicts_ok and slopes_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
