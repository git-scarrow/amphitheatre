#!/usr/bin/env python3
"""Stage CivicBowl *context + horizon* meshes + a deterministic context plan.

OFFLINE (no Unreal). Companion to ``gen_review_meshes.py`` — but it writes a
SEPARATE artifact set (``context_plan.json`` + ``meshes/ctx_*.obj``) under the
same ``build/unreal_scene/`` dir, and never reads or rewrites the audited
``scene_plan.json``. Everything it emits lands under the ``Context/`` Outliner
root, asserted disjoint from the audited design folders.

What it builds (v0 — every layer declared in data/unreal_context_manifest.json):
  bay_water_plane      flat surface at 579.45 ft NAVD88, NNW of the site
  bay_shoreline_ref    OSM shoreline ribbon if present, else a straight proxy
  distant_horizon_band tall thin reference band far NNW (atmospheric)
  city_massing         extruded OSM footprints (generic 8 m) — if OSM present
  city_roads           OSM road ribbons                       — if OSM present
  sun_sky_sunset       CALCULATED sun az/el (NOAA) -> light/sky config records
  sunset_review_camera one camera: upper seat over the stage toward the bay

City layers need ``data/context/osm_petoskey_*.geojson`` (fetch via
``fetch_osm_context.py``); absent them they are recorded as DEFERRED with the
exact expected input path. Output is sorted + carries source sha for provenance,
no timestamps, so ``gen`` + ``git diff`` is a reproducibility check.

    python scripts/unreal/gen_context.py            # -> build/unreal_scene/context_plan.json
    python scripts/unreal/gen_context.py --out DIR --repo /path/to/amphitheatre
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import civicbowl_common as cb   # noqa: E402
import context_common as ctx    # noqa: E402

try:
    import numpy as np
    import shapely.geometry as sg
    from shapely.ops import linemerge, unary_union, split
    from shapely.prepared import prep
    import trimesh
except Exception as exc:  # pragma: no cover
    print(f"[gen-context] missing geometry dep ({exc.__class__.__name__}: {exc}).\n"
          "      Install into the repo venv: shapely trimesh numpy mapbox_earcut", file=sys.stderr)
    raise

# MESH baking matrix: East pre-negated to cancel UE's OBJ-import Y flip, so the
# imported mesh lands on the true enu_to_ue frame (not mirror-imaged). Sun + camera
# below use cb.enu_to_ue directly (placed, not OBJ-round-tripped) and stay true.
UE_MAT = np.array([[r[0], r[1], r[2], 0.0] for r in cb.ENU_TO_UE_MESH_LINEAR] + [[0, 0, 0, 1.0]], float)

# simplified bay-plane extent — canonical in context_common (shared with verify).
BAY_NEAR_N_M = ctx.BAY_NEAR_N_M
BAY_FAR_N_M = ctx.BAY_FAR_N_M
BAY_HALF_E_M = ctx.BAY_HALF_E_M
HORIZON_RANGE_M = 5200.0     # far band distance along the bay-view axis
HORIZON_HALF_W_M = 2600.0
HORIZON_HEIGHT_M = 120.0
ROAD_WIDTH_M = 5.0
# Ribbon width (m, full carriageway/path) by OSM highway class — was a single 5 m
# for everything, which made footways/service drives read like multi-lane streets.
ROAD_WIDTH_BY_TYPE_M = {
    "motorway": 12.0, "trunk": 9.0, "primary": 9.0, "secondary": 7.0, "tertiary": 6.0,
    "unclassified": 5.0, "residential": 5.0, "living_street": 4.0, "raceway": 8.0,
    "service": 3.5, "track": 3.0, "pedestrian": 4.0,
    "footway": 1.5, "path": 1.2, "cycleway": 2.0, "steps": 1.2,
}
SLAB_T = 0.15


def _smooth_z(zs, k=2):
    """Moving-average smooth of a per-vertex elevation list to damp 2 m-DEM jitter
    so draped ribbons don't read jagged. k = half-window."""
    if len(zs) <= 2:
        return list(zs)
    out = []
    for i in range(len(zs)):
        lo, hi = max(0, i - k), min(len(zs), i + k + 1)
        out.append(sum(zs[lo:hi]) / (hi - lo))
    return out


def _to_ue(mesh):
    mesh.apply_transform(UE_MAT)
    return mesh


def flat_quad(e0, e1, n0, n1, z):
    """Horizontal rectangle in ENU at height z (two triangles), baked to UE."""
    v = [[e0, n0, z], [e1, n0, z], [e1, n1, z], [e0, n1, z]]
    f = [[0, 1, 2], [0, 2, 3]]
    return _to_ue(trimesh.Trimesh(vertices=np.array(v, float), faces=np.array(f), process=False))


def vertical_band(e0, e1, n, z0, z1):
    """Vertical rectangle (a far backdrop band) in ENU, baked to UE."""
    v = [[e0, n, z0], [e1, n, z0], [e1, n, z1], [e0, n, z1]]
    f = [[0, 1, 2], [0, 2, 3]]
    return _to_ue(trimesh.Trimesh(vertices=np.array(v, float), faces=np.array(f), process=False))


def ribbon(coords_enu, z, width):
    line = sg.LineString(coords_enu)
    poly = line.buffer(width / 2.0, cap_style=2, join_style=2)
    if poly.is_empty:
        return None
    m = trimesh.creation.extrude_polygon(poly, height=SLAB_T)
    m.apply_translation((0, 0, z - SLAB_T))
    return _to_ue(m)


def extrude_poly_enu(ring_enu, base_z, height):
    poly = sg.Polygon(ring_enu)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        return None, None
    m = trimesh.creation.extrude_polygon(poly, height=height)
    m.apply_translation((0, 0, base_z))
    return _to_ue(m), poly


def harbor_wall(coords_enu, base_z, width, height):
    """A thin extruded wall (breakwater / pier) along an ENU centreline, sitting on
    the water at base_z and rising `height` metres — so it reads as a structure IN
    the water, not a fused land tongue. Baked to UE."""
    line = sg.LineString(coords_enu)
    poly = line.buffer(width / 2.0, cap_style=2, join_style=2)
    if poly.is_empty:
        return None
    m = trimesh.creation.extrude_polygon(poly, height=height)
    m.apply_translation((0, 0, base_z))
    return _to_ue(m)


HARBOR_REL = "data/context/osm_petoskey_harbor.geojson"
WATER_EDGE_REL = "data/context/osm_petoskey_water_edge.geojson"


def _water_plane_covers(e, n):
    """True where the (visible) bay water plane lies under (e,n). Terrain is only
    ever dropped where water actually shows, so the clip never punches sky holes."""
    return (BAY_NEAR_N_M <= n <= BAY_FAR_N_M) and (-ctx_be() <= e <= ctx_be())


def _land_mask(root, warnings):
    """Prepared LAND polygon = the side of the OSM bay shoreline containing the site,
    minus the marina/harbour basin. Used to clip the 3DEP terrain so the coast follows
    the authoritative shoreline (not the noisy DEM water-elevation contour) and the
    harbor basin reads as water. Returns (prepared, polygon) or (None, None)."""
    wpath = os.path.join(root, WATER_EDGE_REL)
    if not os.path.exists(wpath):
        warnings.append("land_mask: no water_edge.geojson — terrain NOT clipped to shoreline")
        return None, None
    tf = _transformer()
    segs = []
    for f in cb.geojson_features(wpath):
        if (f.get("properties") or {}).get("role") != "bay_shoreline":
            continue
        g = f["geometry"]
        chunks = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
        for ch in chunks:
            pts = [_lonlat_to_enu(tf, c[0], c[1]) for c in ch]
            if len(pts) >= 2:
                segs.append(sg.LineString(pts))
    if not segs:
        warnings.append("land_mask: no bay_shoreline features — terrain NOT clipped")
        return None, None
    merged = linemerge(unary_union(segs))
    if merged.geom_type == "MultiLineString":
        merged = max(merged.geoms, key=lambda l: l.length)
    coords = list(merged.coords)
    arr = np.array(coords)
    half = ctx_be() + 300.0
    Emin = min(arr[:, 0].min(), -half) - 300.0
    Emax = max(arr[:, 0].max(), half) + 300.0
    Nmin = -1600.0
    Nmax = arr[:, 1].max() + 400.0
    bbox = sg.box(Emin, Nmin, Emax, Nmax)

    def _ext(p_in, p_out, d=12000.0):
        vx, vy = p_out[0] - p_in[0], p_out[1] - p_in[1]
        L = math.hypot(vx, vy) or 1.0
        return (p_out[0] + vx / L * d, p_out[1] + vy / L * d)

    line = sg.LineString([_ext(coords[1], coords[0])] + coords + [_ext(coords[-2], coords[-1])])
    pieces = list(split(bbox, line).geoms)
    land = unary_union([g for g in pieces if g.contains(sg.Point(0.0, 0.0))])
    if land.is_empty or land.area > 0.97 * bbox.area:
        warnings.append("land_mask: shoreline did not cleanly split the bbox — terrain NOT clipped")
        return None, None
    # carve the explicitly-tagged marina/harbour basin out of the land
    hpath = os.path.join(root, HARBOR_REL)
    if os.path.exists(hpath):
        marinas = []
        for f in cb.geojson_features(hpath):
            if (f.get("properties") or {}).get("kind") != "marina":
                continue
            ring = f["geometry"]["coordinates"][0]
            poly = sg.Polygon([_lonlat_to_enu(tf, c[0], c[1]) for c in ring]).buffer(0)
            if not poly.is_empty:
                marinas.append(poly)
        if marinas:
            land = land.difference(unary_union(marinas))
    return prep(land), land


def _lonlat_to_enu(transformer, lon, lat):
    x_ft, y_ft = transformer.transform(lon, lat)   # EPSG:4326 -> EPSG:6494 ft
    return cb.ft_xy_to_enu(x_ft, y_ft)


def _in_corridor(corr, e, n) -> bool:
    """True if ENU point (e,n) is inside the bay-view sightline strip (bay side)."""
    ox, oy = corr["origin_enu_m"]; de, dn = corr["dir_to_bay"]
    re, rn = e - ox, n - oy
    along = re * de + rn * dn
    perp = abs(re * (-dn) + rn * de)
    return along >= 0 and perp <= corr["half_width_m"]


# ── foreground (3DEP) terrain helpers ────────────────────────────────────────
PED_HIGHWAYS = {"footway", "path", "steps", "pedestrian", "cycleway", "track"}
FG_DEM_REL = "data/context/dem/foreground_3dep.tif"
CITY_DEM_REL = "data/context/dem/city_3dep.tif"   # city-wide 3DEP for draping city layers


def draped_ribbon(coords_enu, zs, width, z_offset=0.05):
    """Terrain-following ribbon: a single-surface strip through the polyline whose
    vertices sit at the per-vertex sampled elevations ``zs`` (+ a small z_offset to
    avoid z-fighting). Replaces the old flat ``ribbon`` for draped paths/roads."""
    pts = np.array(coords_enu, float)
    if len(pts) < 2:
        return None
    half = width / 2.0
    verts, faces = [], []
    for i in range(len(pts)):
        if i == 0:
            tan = pts[1] - pts[0]
        elif i == len(pts) - 1:
            tan = pts[-1] - pts[-2]
        else:
            tan = pts[i + 1] - pts[i - 1]
        L = math.hypot(tan[0], tan[1])
        if L < 1e-9:
            nx, ny = 0.0, 1.0
        else:
            nx, ny = -tan[1] / L, tan[0] / L     # left-perpendicular unit
        z = float(zs[i]) + z_offset
        verts.append([pts[i][0] + nx * half, pts[i][1] + ny * half, z])
        verts.append([pts[i][0] - nx * half, pts[i][1] - ny * half, z])
    for i in range(len(pts) - 1):
        a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3
        faces.append([a, b, c]); faces.append([b, d, c])
    return _to_ue(trimesh.Trimesh(vertices=np.array(verts, float), faces=np.array(faces), process=False))


def _sample_dem_lonlat(dem, transformer, lon, lat):
    """Elevation (m) at a lon/lat from a (arr,transform) DEM, or None if off-grid."""
    if dem is None:
        return None
    x_ft, y_ft = transformer.transform(lon, lat)
    return _dem_z_at(dem[0], dem[1], x_ft, y_ft)


def _load_dem(path):
    """Return (Z[m] masked array, affine transform, nodata) for the EPSG:6494 DEM."""
    import rasterio
    with rasterio.open(path) as ds:
        arr = ds.read(1).astype("float64")
        nodata = ds.nodata
        tr = ds.transform
    if nodata is not None:
        arr[arr == nodata] = np.nan
    arr[arr < -1e4] = np.nan          # guard against sentinel voids
    return arr, tr


def _dem_z_at(arr, tr, x_ft, y_ft):
    """Nearest-cell elevation (m) for an EPSG:6494 (x,y) ft point, or None if off-grid/void."""
    col, row = (~tr) * (x_ft, y_ft)
    c, r = int(round(col)), int(round(row))
    if r < 0 or c < 0 or r >= arr.shape[0] or c >= arr.shape[1]:
        return None
    z = arr[r, c]
    return None if not np.isfinite(z) else float(z)


def _dem_mesh_enu(arr, tr, stride, min_n_m, keep=None):
    """Build a decimated ground mesh (ENU m, baked to UE) from the EPSG:6494 DEM,
    keeping only cells with local North >= ``min_n_m`` so it never overlaps the
    audited project terrain. ``keep(e,n)`` (optional) further restricts cells —
    used to clip the mesh to land (drop the bay/harbor where water shows).
    Returns (mesh, extent[emin,emax,nmin,nmax,ztop]) or (None,None)."""
    ny, nx = arr.shape
    rows = list(range(0, ny, stride))
    cols = list(range(0, nx, stride))
    idx = {}                          # (ri,ci) -> vertex index
    verts, faces = [], []
    emin = nmin = float("inf"); emax = nmax = ztop = float("-inf")
    for ri, r in enumerate(rows):
        for ci, c in enumerate(cols):
            x_ft, y_ft = tr * (c + 0.5, r + 0.5)
            e, n = cb.ft_xy_to_enu(x_ft, y_ft)
            z = arr[r, c]
            if n < min_n_m or not np.isfinite(z):
                continue
            if keep is not None and not keep(e, n):
                continue
            idx[(ri, ci)] = len(verts)
            verts.append((e, n, z))
            emin, emax = min(emin, e), max(emax, e)
            nmin, nmax = min(nmin, n), max(nmax, n)
            ztop = max(ztop, z)
    if len(verts) < 3:
        return None, None
    for ri in range(len(rows) - 1):
        for ci in range(len(cols) - 1):
            a = idx.get((ri, ci)); b = idx.get((ri, ci + 1))
            c2 = idx.get((ri + 1, ci)); d = idx.get((ri + 1, ci + 1))
            if a is not None and b is not None and c2 is not None:
                faces.append((a, c2, b))
            if b is not None and c2 is not None and d is not None:
                faces.append((b, c2, d))
    if not faces:
        return None, None
    m = trimesh.Trimesh(vertices=np.array(verts, float), faces=np.array(faces), process=False)
    return _to_ue(m), [emin, emax, nmin, nmax, ztop]


def _dem_mesh_keep(arr, tr, stride, keep_fn):
    """Decimated ground mesh from the EPSG:6494 DEM, keeping only cells where
    ``keep_fn(e, n)`` is True (used to carve out the design + foreground terrain
    footprints so the city ground never z-fights them). Returns (mesh, extent)."""
    ny, nx = arr.shape
    rows = list(range(0, ny, stride)); cols = list(range(0, nx, stride))
    idx = {}; verts = []; faces = []
    emin = nmin = float("inf"); emax = nmax = ztop = float("-inf")
    for ri, r in enumerate(rows):
        for ci, c in enumerate(cols):
            x_ft, y_ft = tr * (c + 0.5, r + 0.5)
            e, n = cb.ft_xy_to_enu(x_ft, y_ft)
            z = arr[r, c]
            if not np.isfinite(z) or not keep_fn(e, n):
                continue
            idx[(ri, ci)] = len(verts); verts.append((e, n, z))
            emin, emax = min(emin, e), max(emax, e)
            nmin, nmax = min(nmin, n), max(nmax, n); ztop = max(ztop, z)
    if len(verts) < 3:
        return None, None
    for ri in range(len(rows) - 1):
        for ci in range(len(cols) - 1):
            a = idx.get((ri, ci)); b = idx.get((ri, ci + 1))
            c2 = idx.get((ri + 1, ci)); d = idx.get((ri + 1, ci + 1))
            if a is not None and b is not None and c2 is not None:
                faces.append((a, c2, b))
            if b is not None and c2 is not None and d is not None:
                faces.append((b, c2, d))
    if not faces:
        return None, None
    m = trimesh.Trimesh(vertices=np.array(verts, float), faces=np.array(faces), process=False)
    return _to_ue(m), [emin, emax, nmin, nmax, ztop]


def build(root: str, out: str) -> dict:
    ctx.assert_disjoint_from_design()
    man = ctx.load_context_manifest(root)
    problems = ctx.validate_manifest(man)
    if problems:
        raise SystemExit("[gen-context] manifest invalid:\n  " + "\n  ".join(problems))

    mesh_dir = os.path.join(out, "meshes")
    os.makedirs(mesh_dir, exist_ok=True)
    actors: list[dict] = []
    lights: list[dict] = []
    cameras: list[dict] = []
    deferred: list[dict] = []
    warnings: list[str] = []

    def _group_for(lm, layer):
        # New context categories nest under Context/<category>/<layer>; the legacy
        # backdrop/lighting/review layers keep their existing Context/<layer> folder
        # so the accepted scene's HIDDEN proxies are never moved.
        cat = (lm or {}).get("category")
        if cat in ("City_LoFi", "Foreground_HiFi"):
            return f"{ctx.CONTEXT_FOLDER_ROOT}/{cat}/{layer}"
        return f"{ctx.CONTEXT_FOLDER_ROOT}/{layer}"

    def emit(name, mesh, layer, role, tags, anchor=None, extent=None, label_text=None):
        rel = f"meshes/{name}.obj"
        if mesh is not None:
            mesh.export(os.path.join(out, rel), file_type="obj")
        lm = ctx.layer_by_name(man, layer)
        actors.append({
            "name": name, "group": _group_for(lm, layer),
            "mesh": rel if mesh is not None else None,
            "place_at_anchor": anchor, "scale": cb.UE_SCALE,
            "layer": layer, "category": (lm or {}).get("category"),
            "obstruction_role": role,
            "label_text": label_text,
            "source_type": lm.get("source_type"), "accuracy_class": lm.get("accuracy_class"),
            "intended_use": lm.get("intended_use"),
            "included_in_verification": lm.get("included_in_verification", False),
            "extent_enu_m": extent,     # [emin,emax,nmin,nmax, ztop] for the obstruction gate
            "tags": sorted(set(tags)),
        })

    # 0) LAND mask — clip 3DEP terrain to the authoritative OSM shoreline so the
    # coast follows real data (not the noisy DEM water contour) and the harbor basin
    # reads as water. A cell is dropped only where the visible water plane shows,
    # so the clip never punches sky holes outside the water footprint.
    land_prep, _land_poly = _land_mask(root, warnings)

    def _water_keep(e, n):
        if land_prep is None:
            return True
        return land_prep.contains(sg.Point(e, n)) or not _water_plane_covers(e, n)

    # 1) bay water plane (always) -------------------------------------------------
    emit("ctx_bay_water_plane", flat_quad(-ctx_be(), ctx_be(), BAY_NEAR_N_M, BAY_FAR_N_M, ctx.WATER_ELEV_M),
         "bay_water_plane", "backdrop",
         ["context", "approximate", "backdrop", "use:review", "water_elev_navd88_ft:579.45"],
         extent=[-ctx_be(), ctx_be(), BAY_NEAR_N_M, BAY_FAR_N_M, ctx.WATER_ELEV_M])

    # 2) shoreline reference (OSM if present, else straight proxy) ----------------
    shore_path = os.path.join(root, "data/context/shoreline.geojson")
    if os.path.exists(shore_path):
        transformer = _transformer()
        feats = cb.geojson_features(shore_path)
        for i, f in enumerate(sorted(feats, key=lambda x: json.dumps(x, sort_keys=True))):
            if f["geometry"]["type"] != "LineString":
                continue
            enu = [_lonlat_to_enu(transformer, c[0], c[1]) for c in f["geometry"]["coordinates"]]
            emit(f"ctx_shoreline_{i:03d}", ribbon(enu, ctx.WATER_ELEV_M + 0.2, 3.0),
                 "bay_shoreline_ref", "backdrop",
                 ["context", "OSM", "ODbL", "backdrop", "use:reference"])
    else:
        # straight proxy perpendicular to the bay-view axis at the water near-edge
        proxy = [(-ctx_be(), BAY_NEAR_N_M), (ctx_be(), BAY_NEAR_N_M)]
        emit("ctx_shoreline_proxy", ribbon(proxy, ctx.WATER_ELEV_M + 0.2, 4.0),
             "bay_shoreline_ref", "backdrop",
             ["context", "PROXY", "schematic", "backdrop", "use:reference", "must_label"])
        warnings.append("bay_shoreline_ref: no data/context/shoreline.geojson — straight-line PROXY drawn")

    # 3) distant horizon band (always; atmospheric) ------------------------------
    corr = ctx.corridor_geometry(root)
    if corr:
        ox, oy = corr["origin_enu_m"]; de, dn = corr["dir_to_bay"]
        cx, cy = ox + de * HORIZON_RANGE_M, oy + dn * HORIZON_RANGE_M
        # band perpendicular to the axis, centred on the far point
        px, py = -dn, de  # perpendicular unit
        e0, n0 = cx + px * -HORIZON_HALF_W_M, cy + py * -HORIZON_HALF_W_M
        e1, n1 = cx + px * HORIZON_HALF_W_M, cy + py * HORIZON_HALF_W_M
        # vertical_band wants a constant-n band; approximate with a wide N-aligned band
        emit("ctx_distant_horizon_band",
             vertical_band(min(e0, e1), max(e0, e1), (n0 + n1) / 2,
                           ctx.WATER_ELEV_M, ctx.WATER_ELEV_M + HORIZON_HEIGHT_M),
             "distant_horizon_band", "backdrop",
             ["context", "atmospheric", "non_metric", "backdrop", "use:cinematic", "must_label"])

    # 4) + 5) city massing + roads (OSM if present, else deferred) ----------------
    bpath = os.path.join(root, "data/context/osm_petoskey_buildings.geojson")
    rpath = os.path.join(root, "data/context/osm_petoskey_roads.geojson")
    # city-wide 3DEP DEM used to DRAPE city massing/roads/parks onto real terrain
    # (instead of the old water-datum placeholder). None -> water-datum fallback.
    city_dem = _load_dem(os.path.join(root, CITY_DEM_REL)) if os.path.exists(os.path.join(root, CITY_DEM_REL)) else None
    if city_dem is None:
        warnings.append("city_3dep.tif missing — city layers fall back to water datum (placeholder)")

    # 4a) city GROUND surface — mesh the city 3DEP so massing/roads sit on visible
    # ground (was: only ribbons+blocks on the invisible DEM -> sky showed between).
    # Carved around the audited design terrain + the foreground corridor (no z-fight).
    cg_layer = ctx.layer_by_name(man, "city_ground")
    if city_dem is not None and cg_layer is not None:
        arr_c, tr_c = city_dem

        def _keep_city(e, n):
            if -136.0 <= e <= 109.0 and -127.0 <= n <= 119.0:
                return False                      # carve the bowl / design terrain
            if n >= 118.0 and -665.0 <= e <= 523.0:
                return False                      # carve the foreground 3DEP corridor
            return _water_keep(e, n)              # clip to land (drop bay/harbor water)
        gmesh, gext = _dem_mesh_keep(arr_c, tr_c, int(cg_layer.get("decimate_stride", 6)), _keep_city)
        if gmesh is not None:
            emit("ctx_city_ground", gmesh, "city_ground", "none",
                 ["context", "3DEP", "USGS", "public_domain", "city_ground_surface", "use:review"],
                 extent=gext)
        else:
            warnings.append("city_ground: no mesh produced")
    elif cg_layer is not None:
        deferred.append({"layer": "city_ground", "reason": "no city DEM",
                         "expected_input": cg_layer.get("expected_input")})

    blayer = ctx.layer_by_name(man, "city_massing")
    if os.path.exists(bpath):
        transformer = _transformer()
        gen_h = float(blayer.get("generic_height_m", 8.0))
        ms_height = _ms_height_lookup(root, transformer)   # Microsoft ML heights (real, ~54% cover)
        lidar_height = _lidar_height_lookup(root, transformer, city_dem)  # 3DEP LiDAR, near-pit
        corr = ctx.corridor_geometry(root)
        n_corr = n_ph = n_ms = n_lid = 0
        osm_cents = []   # ENU centroids of OSM buildings, for Microsoft backfill dedup
        feats = sorted(cb.geojson_features(bpath), key=lambda f: (f["properties"] or {}).get("osm_id", 0))
        for f in feats:
            ring = f["geometry"]["coordinates"][0]
            enu = [_lonlat_to_enu(transformer, c[0], c[1]) for c in ring]
            props = f["properties"] or {}
            # Buildings in the bay-view sightline strip are KEPT (was: dropped). They are
            # the actual subject of the obstruction question (e.g. Beards Brewery north of
            # the pit); tag them so the corridor gate / analysis can evaluate them.
            in_corr = bool(corr and any(_in_corridor(corr, e, n) for (e, n) in enu))
            n_corr += int(in_corr)
            # base elevation = median 3DEP terrain under the footprint; else water datum
            zs = [z for z in (_sample_dem_lonlat(city_dem, transformer, c[0], c[1]) for c in ring) if z is not None]
            base_z = sorted(zs)[len(zs) // 2] if zs else ctx.WATER_ELEV_M
            placeholder = not zs
            n_ph += int(placeholder)
            # height: prefer Microsoft ML height at the footprint centroid, then OSM
            # tags, then the building-type typology heuristic.
            ce = sum(e for e, _ in enu) / len(enu); cn = sum(n for _, n in enu) / len(enu)
            osm_cents.append((ce, cn))
            lid_h = lidar_height(ring) if lidar_height else None
            ms_h = ms_height(ce, cn) if ms_height else None
            if lid_h and lid_h > 1.5:
                h = lid_h; hsrc = "lidar_height"; n_lid += 1
            elif ms_h and ms_h > 0:
                h = ms_h; hsrc = "ms_height"; n_ms += 1
            elif _tagged_height(props):
                h = _height_from_tags(props, gen_h); hsrc = "tagged_height"
            else:
                h = _height_from_tags(props, gen_h); hsrc = "typology_height"
            mesh, poly = extrude_poly_enu(enu, base_z, h)   # base on terrain
            if mesh is None:
                continue
            ex = poly.bounds  # (emin,nmin,emax,nmax)
            nm = props.get("name")
            emit(f"ctx_bldg_{props.get('osm_id')}", mesh, "city_massing", "occluder",
                 ["context", "OSM", "ODbL", "approximate_massing", "use:review", "must_label",
                  f"height_m:{h:g}", hsrc,
                  "placeholder_water_datum" if placeholder else "base_on_3dep"]
                 + (["in_bay_view_corridor"] if in_corr else [])
                 + ([f"name:{nm}"] if nm else []),
                 extent=[ex[0], ex[2], ex[1], ex[3], base_z + h])
        if n_corr:
            warnings.append(f"city_massing: {n_corr} building(s) sit in the bay-view corridor — KEPT for "
                            f"obstruction analysis (e.g. Beards Brewery north of the pit)")
        if n_ph:
            warnings.append(f"city_massing: {n_ph} building(s) outside city DEM -> water-datum placeholder")
        warnings.append(f"city_massing heights: {n_lid} LiDAR-measured + {n_ms} Microsoft ML (rest OSM tag/typology)")

        # BACKFILL: add Microsoft footprints that OSM is missing (no OSM building within
        # 12 m), so gaps like the building across the street from the pit get filled.
        # MS geometry + MS height (or 7 m), draped on the city DEM, same corridor tagging.
        n_back = 0
        ms_path = os.path.join(root, MS_BUILDINGS_REL)
        if osm_cents and os.path.exists(ms_path):
            from scipy.spatial import cKDTree
            otree = cKDTree(np.array(osm_cents))
            for f in cb.geojson_features(ms_path):
                if f["geometry"]["type"] != "Polygon":
                    continue
                ring = f["geometry"]["coordinates"][0]
                enu = [_lonlat_to_enu(transformer, c[0], c[1]) for c in ring]
                ce = sum(e for e, _ in enu) / len(enu); cn = sum(n for _, n in enu) / len(enu)
                if otree.query([ce, cn])[0] <= 12.0:
                    continue                       # OSM already has this building
                zs = [z for z in (_sample_dem_lonlat(city_dem, transformer, c[0], c[1]) for c in ring) if z is not None]
                base_z = sorted(zs)[len(zs) // 2] if zs else ctx.WATER_ELEV_M
                hh = (f["properties"] or {}).get("height")
                lid_h = lidar_height(ring) if lidar_height else None
                if lid_h and lid_h > 1.5:
                    h, hsrc = lid_h, "lidar_height"
                elif hh and hh > 0:
                    h, hsrc = float(hh), "ms_height"
                else:
                    h, hsrc = 7.0, "typology_height"
                mesh, poly = extrude_poly_enu(enu, base_z, h)
                if mesh is None:
                    continue
                in_corr = bool(corr and any(_in_corridor(corr, e, n) for (e, n) in enu))
                ex = poly.bounds
                emit(f"ctx_bldg_ms_{n_back}", mesh, "city_massing", "occluder",
                     ["context", "Microsoft", "ODbL", "backfill_ms", "approximate_massing", "use:review",
                      f"height_m:{h:g}", hsrc]
                     + (["in_bay_view_corridor"] if in_corr else []),
                     extent=[ex[0], ex[2], ex[1], ex[3], base_z + h])
                n_back += 1
            if n_back:
                warnings.append(f"city_massing: backfilled {n_back} Microsoft-only building(s) where OSM had none")
    else:
        deferred.append({"layer": "city_massing", "reason": "no OSM building input",
                         "expected_input": blayer.get("expected_input")})
        warnings.append("city_massing DEFERRED — run scripts/unreal/fetch_osm_context.py --run")

    rlayer = ctx.layer_by_name(man, "city_roads")
    if os.path.exists(rpath):
        transformer = _transformer()
        feats = sorted(cb.geojson_features(rpath), key=lambda f: (f["properties"] or {}).get("osm_id", 0))
        for f in feats:
            props = f["properties"] or {}
            hw = props.get("highway")
            width = ROAD_WIDTH_BY_TYPE_M.get(hw, 4.0)   # was uniform 5 m for everything
            enu = []; zs = []
            for c in f["geometry"]["coordinates"]:
                e, n = _lonlat_to_enu(transformer, c[0], c[1])
                z = _sample_dem_lonlat(city_dem, transformer, c[0], c[1])
                enu.append((e, n)); zs.append(z if z is not None else ctx.WATER_ELEV_M)
            if len(enu) < 2:
                continue
            ph = all(_sample_dem_lonlat(city_dem, transformer, c[0], c[1]) is None
                     for c in f["geometry"]["coordinates"])
            emit(f"ctx_road_{props.get('osm_id')}",
                 draped_ribbon(enu, _smooth_z(zs), width), "city_roads", "none",
                 ["context", "OSM", "ODbL", "approximate", "use:reference",
                  f"highway:{hw}", f"width_m:{width:g}",
                  "placeholder_water_datum" if ph else "draped_3dep"])
    else:
        deferred.append({"layer": "city_roads", "reason": "no OSM road input",
                         "expected_input": rlayer.get("expected_input")})

    # 5b) city parks — OSM open-space polygons as flat green pads -----------------
    ppath = os.path.join(root, "data/context/osm_petoskey_parks.geojson")
    if os.path.exists(ppath):
        transformer = _transformer()
        feats = sorted(cb.geojson_features(ppath), key=lambda f: (f["properties"] or {}).get("osm_id", 0))
        for f in feats:
            if f["geometry"]["type"] != "Polygon":
                continue
            ring = f["geometry"]["coordinates"][0]
            enu = [_lonlat_to_enu(transformer, c[0], c[1]) for c in ring]
            zs = [z for z in (_sample_dem_lonlat(city_dem, transformer, c[0], c[1]) for c in ring) if z is not None]
            base_z = sorted(zs)[len(zs) // 2] if zs else ctx.WATER_ELEV_M  # median terrain under park
            mesh, _ = extrude_poly_enu(enu, base_z, 0.2)   # thin pad on terrain
            if mesh is None:
                continue
            emit(f"ctx_park_{(f['properties'] or {}).get('osm_id')}", mesh, "city_parks", "none",
                 ["context", "OSM", "ODbL", "open_space", "use:review",
                  "placeholder_water_datum" if not zs else "base_on_3dep"])
    else:
        deferred.append({"layer": "city_parks", "reason": "no OSM parks input",
                         "expected_input": ctx.layer_by_name(man, "city_parks").get("expected_input")})

    # 5c) city labels — OSM place nodes as text markers (no mesh) -----------------
    lpath = os.path.join(root, "data/context/osm_petoskey_places.geojson")
    if os.path.exists(lpath):
        transformer = _transformer()
        feats = sorted(cb.geojson_features(lpath), key=lambda f: (f["properties"] or {}).get("osm_id", 0))
        for f in feats:
            name = (f["properties"] or {}).get("name")
            if not name:
                continue
            lon, lat = f["geometry"]["coordinates"]
            e, n = _lonlat_to_enu(transformer, lon, lat)
            anchor = list(cb.enu_to_ue(e, n, ctx.WATER_ELEV_M + 20.0))   # float text above datum
            emit(f"ctx_label_{(f['properties'] or {}).get('osm_id')}", None, "city_labels", "none",
                 ["context", "OSM", "ODbL", "label", "use:reference",
                  f"place:{(f['properties'] or {}).get('place')}"],
                 anchor=anchor, label_text=name)
    else:
        deferred.append({"layer": "city_labels", "reason": "no OSM places input",
                         "expected_input": ctx.layer_by_name(man, "city_labels").get("expected_input")})

    # 5d) bay edge — cartographic LINE (Lake Michigan relation edge), NOT a slab --
    wpath = os.path.join(root, "data/context/osm_petoskey_water_edge.geojson")
    bay_feats = []
    if os.path.exists(wpath):
        transformer = _transformer()
        feats = sorted(cb.geojson_features(wpath), key=lambda f: (f["properties"] or {}).get("osm_id", 0))
        bay_feats = [f for f in feats if (f["properties"] or {}).get("role") == "bay_shoreline"]
        for i, f in enumerate(bay_feats):
            enu = [_lonlat_to_enu(transformer, c[0], c[1]) for c in f["geometry"]["coordinates"]]
            emit(f"ctx_bay_edge_{i:03d}", ribbon(enu, ctx.WATER_ELEV_M + 0.3, 3.0),
                 "bay_edge_cartographic", "backdrop",
                 ["context", "OSM", "ODbL", "cartographic_edge", "use:review", "not_a_slab"])
        if not bay_feats:
            warnings.append("bay_edge_cartographic: water_edge.geojson has no role=bay_shoreline features")
    else:
        deferred.append({"layer": "bay_edge_cartographic", "reason": "no OSM water edge input",
                         "expected_input": ctx.layer_by_name(man, "bay_edge_cartographic").get("expected_input")})

    # 5e) FOREGROUND terrain — 3DEP DEM mesh north of the audited project terrain --
    fg = ctx.layer_by_name(man, "fg_terrain")
    dem_path = os.path.join(root, FG_DEM_REL)
    dem = None
    if os.path.exists(dem_path):
        dem = _load_dem(dem_path)
        arr, tr = dem
        stride = int(fg.get("decimate_stride", 3))
        min_n = float(fg.get("min_north_local_m", 120.0))
        mesh, extent = _dem_mesh_enu(arr, tr, stride, min_n, keep=_water_keep)
        if mesh is not None:
            emit("ctx_fg_terrain", mesh, "fg_terrain", "none",
                 ["context", "3DEP", "USGS", "public_domain", "real_terrain", "use:review",
                  f"stride:{stride}", f"min_north_m:{min_n:g}"],
                 extent=extent)
        else:
            warnings.append("fg_terrain: DEM produced no mesh north of the clip line")
    else:
        deferred.append({"layer": "fg_terrain", "reason": "no 3DEP DEM",
                         "expected_input": fg.get("expected_input")})

    # 5e2) HARBOR structures — OSM breakwaters + piers redrawn as thin walls sitting
    # ON the water (the terrain under them was clipped away in §0), so they read as
    # structures surrounded by water instead of one fused land peninsula. The long
    # breakwater carries the Bayfront pierhead light.
    hs_layer = ctx.layer_by_name(man, "harbor_structures")
    hpath = os.path.join(root, HARBOR_REL)
    if hs_layer is not None and os.path.exists(hpath):
        transformer = _transformer()
        feats = sorted(cb.geojson_features(hpath),
                       key=lambda f: (f["properties"] or {}).get("osm_id", 0))
        wz = ctx.WATER_ELEV_M
        n_struct = 0
        for f in feats:
            props = f["properties"] or {}
            kind = props.get("kind")
            if kind not in ("breakwater", "pier", "groyne"):
                continue                          # marina polygon is a carve, not a mesh
            if f["geometry"]["type"] != "LineString":
                continue
            enu = [_lonlat_to_enu(transformer, c[0], c[1]) for c in f["geometry"]["coordinates"]]
            if len(enu) < 2:
                continue
            is_bw = kind in ("breakwater", "groyne")
            width = 7.0 if is_bw else 3.0
            height = 2.2 if is_bw else 1.2        # above the water plane
            mesh = harbor_wall(enu, wz, width, height)
            if mesh is None:
                continue
            emit(f"ctx_harbor_{kind}_{props.get('osm_id')}", mesh,
                 "harbor_structures", "backdrop",
                 ["context", "OSM", "ODbL", f"man_made:{kind}", "use:review", "in_water"])
            n_struct += 1
        if n_struct == 0:
            warnings.append("harbor_structures: no breakwater/pier lines in harbor geojson")
    elif hs_layer is not None:
        deferred.append({"layer": "harbor_structures", "reason": "no OSM harbor input",
                         "expected_input": hs_layer.get("expected_input")})

    # 5f) FOREGROUND paths — OSM pedestrian ways draped on the 3DEP terrain --------
    if dem is not None and os.path.exists(rpath):
        arr, tr = dem
        min_n = float(fg.get("min_north_local_m", 120.0))
        transformer = _transformer()
        feats = sorted(cb.geojson_features(rpath), key=lambda f: (f["properties"] or {}).get("osm_id", 0))
        n_paths = 0
        for f in feats:
            props = f["properties"] or {}
            if props.get("highway") not in PED_HIGHWAYS:
                continue
            pts = []
            for c in f["geometry"]["coordinates"]:
                x_ft, y_ft = transformer.transform(c[0], c[1])
                e, n = cb.ft_xy_to_enu(x_ft, y_ft)
                z = _dem_z_at(arr, tr, x_ft, y_ft)
                if z is None or n < min_n:
                    continue
                pts.append((e, n, z))
            if len(pts) < 2:
                continue
            # drape PER-VERTEX on the 3DEP foreground (was: flat at per-path mean z)
            enu2d = [(p[0], p[1]) for p in pts]
            rib = draped_ribbon(enu2d, [p[2] for p in pts], 1.5)
            if rib is None:
                continue
            emit(f"ctx_fgpath_{props.get('osm_id')}", rib, "fg_paths", "none",
                 ["context", "OSM", "ODbL", "draped_3dep_pervertex", "use:reference",
                  f"highway:{props.get('highway')}"])
            n_paths += 1
        if n_paths == 0:
            warnings.append("fg_paths: no pedestrian ways fell within the foreground corridor")
    else:
        deferred.append({"layer": "fg_paths", "reason": "needs 3DEP DEM + OSM roads",
                         "expected_input": ctx.layer_by_name(man, "fg_paths").get("expected_input")})

    # 5g) foreground waterfront / treatment-cell / canopy — declared, deferred v0 --
    for lyr, reason in (
        ("fg_waterfront_edge", "covered by bay_edge_cartographic in v0; distinct near-shore detail TBD"),
        ("fg_treatment_cell_edge", "read-only echo of audited geometry — pending confirmation"),
        ("fg_canopy", "no canopy data fetched yet")):
        deferred.append({"layer": lyr, "reason": reason,
                         "expected_input": (ctx.layer_by_name(man, lyr) or {}).get("expected_input")})

    # 6) sun/sky — CALCULATED solar position -> light config (always) ------------
    events = ctx.resolve_solar_events()
    for key, ev in events.items():
        az = ev.get("azimuth_deg"); el = ev.get("elevation_apparent_deg")
        if az is None:
            warnings.append(f"solar event {key}: not resolved"); continue
        # unit vector TO the sun in ENU, then to the UE frame
        elr, azr = math.radians(el), math.radians(az)
        to_sun_enu = (math.cos(elr) * math.sin(azr), math.cos(elr) * math.cos(azr), math.sin(elr))
        to_sun_ue = list(cb.enu_to_ue(*to_sun_enu))
        lights.append({
            "name": f"ctx_sun_{key}", "group": f"{ctx.CONTEXT_FOLDER_ROOT}/sun_sky_sunset",
            "event": key, "label": ev["label"], "local_time": ev.get("local"), "utc": ev.get("utc"),
            "azimuth_deg": az, "elevation_apparent_deg": el,
            "elevation_true_deg": ev.get("elevation_true_deg"),
            "to_sun_unit_ue": [round(v, 6) for v in to_sun_ue],
            "tags": ["context", "computed_solar_NOAA", "use:cinematic",
                     f"az:{az:.1f}", f"el:{el:.1f}", f"event:{key}"],
        })

    # 7) sunset review camera — upper seat over the stage toward the bay ---------
    cam = _sunset_camera(root)
    if cam:
        cameras.append(cam)
    else:
        warnings.append("sunset_review_camera: could not resolve seating/axis geometry")

    plan = {
        "schema": "civicbowl-context-plan/0.1",
        "map_package": cb.MAP_PACKAGE, "mesh_package_dir": cb.MESH_PACKAGE_DIR,
        "context_root": ctx.CONTEXT_FOLDER_ROOT,
        "design_roots": sorted(ctx.design_folder_roots()),
        "frame_note": "context meshes baked in the UE frame via the same handedness-correct "
                      "ENU->UE map as the design path; actors at origin, markers at UE coords, scale x100",
        "site": man.get("site"),
        "corridor": ctx.corridor_geometry(root),
        "solar_events": events,
        "actors": actors, "lights": lights, "cameras": cameras,
        "deferred": deferred, "warnings": warnings,
        "manifest_sha12": cb.sha256_12(os.path.join(root, ctx.CONTEXT_MANIFEST)),
    }
    with open(os.path.join(out, ctx.CONTEXT_PLAN), "w") as fh:
        json.dump(plan, fh, indent=1, sort_keys=True)
    return plan


# small helpers kept after build() for readability ---------------------------
def ctx_be():
    return BAY_HALF_E_M


def _transformer():
    from pyproj import Transformer
    # EPSG:4326 (lon/lat) -> EPSG:6494 (ft), always_xy
    return Transformer.from_crs("EPSG:4326", "EPSG:6494", always_xy=True)


def _tagged_height(props: dict) -> bool:
    return bool(props.get("height") or props.get("building:levels"))


# Approximate massing heights (m) by OSM building type, used when no height/levels
# tag exists (OSM coverage here is ~0%). Still APPROXIMATE — a typology heuristic,
# not surveyed heights — but reads better than a single generic value.
BUILDING_TYPE_HEIGHTS_M = {
    "house": 6.0, "detached": 6.0, "bungalow": 5.0, "cabin": 4.0, "hut": 3.0,
    "garage": 3.0, "garages": 3.0, "shed": 3.0, "roof": 4.0, "carport": 3.0,
    "apartments": 12.0, "residential": 9.0, "dormitory": 12.0, "terrace": 8.0,
    "retail": 7.0, "commercial": 9.0, "office": 12.0, "supermarket": 8.0,
    "industrial": 8.0, "warehouse": 9.0, "manufacture": 9.0,
    "school": 9.0, "university": 12.0, "college": 12.0, "kindergarten": 6.0,
    "church": 14.0, "cathedral": 18.0, "chapel": 9.0, "temple": 12.0,
    "hospital": 15.0, "hotel": 15.0, "civic": 10.0, "public": 10.0,
    "government": 12.0, "stadium": 18.0, "grandstand": 10.0, "sports_hall": 11.0,
    "yes": 7.0,
}


def _height_from_tags(props: dict, generic: float) -> float:
    if props.get("height"):
        try:
            return float(str(props["height"]).split()[0])
        except ValueError:
            pass
    if props.get("building:levels"):
        try:
            return float(props["building:levels"]) * 3.0
        except ValueError:
            pass
    return BUILDING_TYPE_HEIGHTS_M.get(props.get("building"), generic)


MS_BUILDINGS_REL = "data/context/ms_buildings.geojson"


def _ms_height_lookup(root, transformer):
    """Nearest-centroid lookup of Microsoft GlobalMLBuildingFootprints heights (m),
    keyed in ENU metres. Returns a function(e, n) -> height or None. Only MS records
    with a REAL height (not -1) are indexed; OSM massing falls back to the typology
    heuristic where MS has no nearby footprint."""
    path = os.path.join(root, MS_BUILDINGS_REL)
    if not os.path.exists(path):
        return None
    from scipy.spatial import cKDTree
    pts, hts = [], []
    for f in cb.geojson_features(path):
        h = (f["properties"] or {}).get("height")
        if h is None or h in (-1, -1.0) or f["geometry"]["type"] != "Polygon":
            continue
        ring = f["geometry"]["coordinates"][0]
        lon_c = sum(c[0] for c in ring) / len(ring); lat_c = sum(c[1] for c in ring) / len(ring)
        pts.append(_lonlat_to_enu(transformer, lon_c, lat_c)); hts.append(float(h))
    if not pts:
        return None
    tree = cKDTree(np.array(pts)); harr = np.array(hts)

    def lookup(e, n, max_d=20.0):
        d, i = tree.query([e, n])
        return float(harr[i]) if d <= max_d else None
    return lookup


# LiDAR first-return DSM (ft, EPSG:6494). Prefer the city-wide mosaic; fall back to
# the near-pit DSM. Built from 3DEP LAZ tiles via PDAL (writers.gdal max Z).
CITY_DSM_REL = "data/context/dem/city_dsm.tif"
PIT_DSM_REL = "data/context/dem/pit_dsm.tif"


def _lidar_height_lookup(root, transformer, dtm):
    """LiDAR-MEASURED building height: first-return DSM (3DEP LAZ) minus the bare-earth
    DTM, sampled over the footprint. Returns function(ring_lonlat) -> height m or None.
    Covers wherever the 3DEP LAZ tiles reach (city-wide mosaic if built)."""
    dsm_p = next((os.path.join(root, p) for p in (CITY_DSM_REL, PIT_DSM_REL)
                  if os.path.exists(os.path.join(root, p))), None)
    if dsm_p is None or dtm is None:
        return None
    dsm = _load_dem(dsm_p)   # (arr, tr); Z in FEET

    def height(ring_lonlat):
        hs = []
        cs = list(ring_lonlat)
        clon = sum(c[0] for c in cs) / len(cs); clat = sum(c[1] for c in cs) / len(cs)
        for lon, lat in cs + [(clon, clat)]:
            x_ft, y_ft = transformer.transform(lon, lat)
            zd = _dem_z_at(dsm[0], dsm[1], x_ft, y_ft)        # ft (surface)
            zg = _dem_z_at(dtm[0], dtm[1], x_ft, y_ft)        # m (bare earth)
            if zd is None or zg is None:
                continue
            h = zd * cb.FT_TO_M - zg
            if 0.5 < h < 45.0:                                # plausible building height
                hs.append(h)
        if len(hs) < 3:
            return None
        hs.sort()
        return hs[int(len(hs) * 0.75)]                        # ~roof (75th pct, reject ground/edges)
    return height


def _sunset_camera(root: str) -> dict | None:
    corr = ctx.corridor_geometry(root)
    feats = cb.geojson_features(os.path.join(root, "unreal_export/geo/seating_rows.geojson"))
    if not corr or not feats:
        return None
    # pick the highest (rearmost) seating centroid as the eye; +1.5 m eye height
    best = None
    for f in feats:
        ring = f["geometry"]["coordinates"][0]
        es = [cb.ft_xy_to_enu(p[0], p[1]) for p in ring]
        e = sum(p[0] for p in es) / len(es); n = sum(p[1] for p in es) / len(es)
        z = (f["properties"] or {}).get("proposed_elev_navd88_ft") or (f["properties"] or {}).get("elev_navd88_ft")
        z = cb.ft_z_to_m(float(z)) if z is not None else None
        if z is not None and (best is None or z > best[2]):
            best = (e, n, z)
    if best is None:
        return None
    eye = (best[0], best[1], best[2] + 1.5)
    ox, oy = corr["origin_enu_m"]; de, dn = corr["dir_to_bay"]
    # look down the bay-view axis toward the bay/horizon, at the water elevation
    tgt = (ox + de * 1500.0, oy + dn * 1500.0, ctx.WATER_ELEV_M + 30.0)
    return {
        "name": "ctx_cam_sunset_review", "group": f"{ctx.CONTEXT_FOLDER_ROOT}/sunset_review_camera",
        "position_m": list(cb.enu_to_ue(*eye)), "look_at_m": list(cb.enu_to_ue(*tgt)),
        "fov": 50.0, "scale": cb.UE_SCALE,
        "intended_use": "cinematic",
        "tags": ["context", "camera", "use:cinematic", "aim:bay_view_axis_330", "upper_seat_eye"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--out", default=None, help="output dir (default: <repo>/build/unreal_scene)")
    args = ap.parse_args()
    root = cb.repo_root(args.repo)
    out = os.path.abspath(args.out) if args.out else os.path.join(root, "build", "unreal_scene")
    os.makedirs(out, exist_ok=True)
    plan = build(root, out)
    nb = sum(1 for a in plan["actors"] if a["obstruction_role"] == "occluder")
    print(f"[gen-context] repo   : {root}")
    print(f"[gen-context] out    : {out}/{ctx.CONTEXT_PLAN}")
    print(f"[gen-context] actors : {len(plan['actors'])}  (occluders: {nb})  "
          f"lights: {len(plan['lights'])}  cameras: {len(plan['cameras'])}")
    print(f"[gen-context] context root : {plan['context_root']}  (design roots: {plan['design_roots']})")
    for ev, d in plan["solar_events"].items():
        print(f"[gen-context] solar {ev}: {d.get('local')}  az={d.get('azimuth_deg')}  "
              f"el_app={d.get('elevation_apparent_deg')}")
    if plan["deferred"]:
        print(f"[gen-context] DEFERRED: {', '.join(d['layer'] for d in plan['deferred'])}")
    if plan["warnings"]:
        print(f"[gen-context] warnings: {len(plan['warnings'])} (see context_plan.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
