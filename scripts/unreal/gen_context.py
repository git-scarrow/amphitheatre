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
    import trimesh
except Exception as exc:  # pragma: no cover
    print(f"[gen-context] missing geometry dep ({exc.__class__.__name__}: {exc}).\n"
          "      Install into the repo venv: shapely trimesh numpy mapbox_earcut", file=sys.stderr)
    raise

UE_MAT = np.array([[r[0], r[1], r[2], 0.0] for r in cb.ENU_TO_UE_LINEAR] + [[0, 0, 0, 1.0]], float)

# simplified bay-plane extent — canonical in context_common (shared with verify).
BAY_NEAR_N_M = ctx.BAY_NEAR_N_M
BAY_FAR_N_M = ctx.BAY_FAR_N_M
BAY_HALF_E_M = ctx.BAY_HALF_E_M
HORIZON_RANGE_M = 5200.0     # far band distance along the bay-view axis
HORIZON_HALF_W_M = 2600.0
HORIZON_HEIGHT_M = 120.0
ROAD_WIDTH_M = 5.0
SLAB_T = 0.15


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


def _lonlat_to_enu(transformer, lon, lat):
    x_ft, y_ft = transformer.transform(lon, lat)   # EPSG:4326 -> EPSG:6494 ft
    return cb.ft_xy_to_enu(x_ft, y_ft)


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

    def emit(name, mesh, layer, role, tags, anchor=None, extent=None):
        rel = f"meshes/{name}.obj"
        if mesh is not None:
            mesh.export(os.path.join(out, rel), file_type="obj")
        lm = ctx.layer_by_name(man, layer)
        actors.append({
            "name": name, "group": f"{ctx.CONTEXT_FOLDER_ROOT}/{layer}",
            "mesh": rel if mesh is not None else None,
            "place_at_anchor": anchor, "scale": cb.UE_SCALE,
            "layer": layer, "obstruction_role": role,
            "source_type": lm.get("source_type"), "accuracy_class": lm.get("accuracy_class"),
            "intended_use": lm.get("intended_use"),
            "included_in_verification": lm.get("included_in_verification", False),
            "extent_enu_m": extent,     # [emin,emax,nmin,nmax, ztop] for the obstruction gate
            "tags": sorted(set(tags)),
        })

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
    blayer = ctx.layer_by_name(man, "city_massing")
    if os.path.exists(bpath):
        transformer = _transformer()
        gen_h = float(blayer.get("generic_height_m", 8.0))
        feats = sorted(cb.geojson_features(bpath), key=lambda f: (f["properties"] or {}).get("osm_id", 0))
        for f in feats:
            ring = f["geometry"]["coordinates"][0]
            enu = [_lonlat_to_enu(transformer, c[0], c[1]) for c in ring]
            props = f["properties"] or {}
            h = _height_from_tags(props, gen_h)
            mesh, poly = extrude_poly_enu(enu, ctx.WATER_ELEV_M, h)  # base draped at water datum (v0)
            if mesh is None:
                continue
            ex = poly.bounds  # (emin,nmin,emax,nmax)
            emit(f"ctx_bldg_{props.get('osm_id')}", mesh, "city_massing", "occluder",
                 ["context", "OSM", "ODbL", "approximate_massing", "use:review", "must_label",
                  f"height_m:{h:g}", "generic_height" if not _tagged_height(props) else "tagged_height"],
                 extent=[ex[0], ex[2], ex[1], ex[3], ctx.WATER_ELEV_M + h])
    else:
        deferred.append({"layer": "city_massing", "reason": "no OSM building input",
                         "expected_input": blayer.get("expected_input")})
        warnings.append("city_massing DEFERRED — run scripts/unreal/fetch_osm_context.py --run")

    rlayer = ctx.layer_by_name(man, "city_roads")
    if os.path.exists(rpath):
        transformer = _transformer()
        feats = sorted(cb.geojson_features(rpath), key=lambda f: (f["properties"] or {}).get("osm_id", 0))
        for f in feats:
            enu = [_lonlat_to_enu(transformer, c[0], c[1]) for c in f["geometry"]["coordinates"]]
            emit(f"ctx_road_{(f['properties'] or {}).get('osm_id')}", ribbon(enu, ctx.WATER_ELEV_M, ROAD_WIDTH_M),
                 "city_roads", "none", ["context", "OSM", "ODbL", "approximate", "use:reference"])
    else:
        deferred.append({"layer": "city_roads", "reason": "no OSM road input",
                         "expected_input": rlayer.get("expected_input")})

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
    return generic


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
