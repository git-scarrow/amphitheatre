#!/usr/bin/env python3
"""Bake per-operation OBJ meshes for the terrain-op ledger (offline, no UE).

Each accepted operation in design/terrain_ops.current.json becomes ONE small
OBJ mesh named by its op_id, so the Unreal scene imports an actor per op and
can be coloured / materialled / clipped per op (criteria 3, 6, 7).

Frame: local ENU Z-up metres with East pre-negated to cancel UE's OBJ-importer
Y flip -- identical to scripts/unreal/gen_review_meshes.py
(civicbowl_common.enu_to_ue_mesh).  Origin EPSG:6494 (19533067.7, 750799.2) ft.

Surfaces:
  cap / tread / ada / stage  -> flat slab at the op elevation
  drainage                   -> flat slab at the channel bottom
  riser                      -> vertical face along the down-slope edge
  transition                 -> strip sloped from plate elev to existing grade

stdlib + numpy only (gen_review_meshes needs shapely+trimesh, absent here).
Outputs  unreal_export/terrain/terrace_ops/<op_id>.obj
         unreal_export/terrain/terrace_ops/mesh_manifest.json
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

import terrace_ops_common as T

ORIGIN_X_FT, ORIGIN_Y_FT, FT_TO_M = 19533067.7, 750799.2, 0.3048
MESH_OUT = os.path.join(T.REPO, "unreal_export", "terrain", "terrace_ops")


def enu_mesh(x_ft, y_ft, z_ft):
    """EPSG:6494 ft + NAVD88 ft -> UE mesh frame metres (n, -e, u)."""
    e = (x_ft - ORIGIN_X_FT) * FT_TO_M
    n = (y_ft - ORIGIN_Y_FT) * FT_TO_M
    return (n, -e, z_ft * FT_TO_M)


def _split_band(ring):
    """Band ring [inner... , outer-reversed...] -> aligned (inner, outer) arrays."""
    pts = np.asarray(ring[:-1] if ring[0] == ring[-1] else ring, dtype=float)
    h = len(pts) // 2
    inner = pts[:h]
    outer = pts[h:][::-1]
    m = min(len(inner), len(outer))
    return inner[:m], outer[:m]


def _obj(verts, faces, name):
    lines = [f"o {name}", f"g {name}"]
    for v in verts:
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}")
    for a, b, c in faces:
        lines.append(f"f {a+1} {b+1} {c+1}")
    return "\n".join(lines) + "\n"


def slab_band(ring, z_inner_ft, z_outer_ft):
    """Triangulated strip between the inner and outer arcs (per-vertex z lerp)."""
    inner, outer = _split_band(ring)
    verts, faces = [], []
    for i in range(len(inner)):
        verts.append(enu_mesh(inner[i, 0], inner[i, 1], z_inner_ft))
    for i in range(len(outer)):
        verts.append(enu_mesh(outer[i, 0], outer[i, 1], z_outer_ft))
    n = len(inner)
    for i in range(n - 1):
        a, b = i, i + 1            # inner
        c, d = n + i, n + i + 1    # outer
        faces.append((a, c, d))
        faces.append((a, d, b))
    return verts, faces


def riser_wall(ring, z_bot_ft, z_top_ft):
    """Vertical wall along the inner (down-slope) arc of a riser band."""
    inner, _ = _split_band(ring)
    verts, faces = [], []
    for i in range(len(inner)):
        verts.append(enu_mesh(inner[i, 0], inner[i, 1], z_bot_ft))
    for i in range(len(inner)):
        verts.append(enu_mesh(inner[i, 0], inner[i, 1], z_top_ft))
    n = len(inner)
    for i in range(n - 1):
        a, b = i, i + 1
        c, d = n + i, n + i + 1
        faces.append((a, c, d))
        faces.append((a, d, b))
    return verts, faces


def fan_poly(ring, z_ft):
    """Fan-triangulate an arbitrary flat polygon from its centroid."""
    pts = np.asarray(ring[:-1] if ring[0] == ring[-1] else ring, dtype=float)
    cen = pts.mean(axis=0)
    verts = [enu_mesh(cen[0], cen[1], z_ft)]
    for p in pts:
        verts.append(enu_mesh(p[0], p[1], z_ft))
    faces = []
    n = len(pts)
    for i in range(n):
        faces.append((0, 1 + i, 1 + (i + 1) % n))
    return verts, faces


def build():
    ledger_path = os.path.join(T.DESIGN_DIR, "terrain_ops.current.json")
    if not os.path.exists(ledger_path):
        print("FAIL: no accepted ledger. Run build_terrain_ops.py + "
              "validate_terrain_ops.py first.")
        return 1
    ledger = T.load_geojson(ledger_path)

    # index every surface feature by op_id across the geometry layers
    feat = {}
    layer_of = {}
    for ln in ("seat_caps", "tread_surfaces", "riser_faces", "drainage_bands",
               "terrain_transitions", "ada_paths", "stage_floor"):
        for f in T.load_geojson(os.path.join(T.GEO_OUT, f"{ln}.geojson"))["features"]:
            oid = f["properties"]["op_id"]
            feat[oid] = f
            layer_of[oid] = ln

    os.makedirs(MESH_OUT, exist_ok=True)
    manifest = {"schema": "amphitheatre/terrace-mesh-manifest/0.1",
                "frame": "ENU Z-up metres, East pre-negated (enu_to_ue_mesh)",
                "origin_epsg6494_ft": [ORIGIN_X_FT, ORIGIN_Y_FT],
                "ft_to_m": FT_TO_M, "meshes": []}
    written = 0
    for o in ledger["ops"]:
        oid = o["op_id"]
        f = feat.get(oid)
        if f is None:
            continue
        p = f["properties"]
        ring = f["geometry"]["coordinates"][0]
        kind = p.get("kind")
        elo = p.get("elev_lo_navd88")
        ehi = p.get("elev_hi_navd88")
        ez = p.get("elev_navd88")
        if kind == "riser":
            verts, faces = riser_wall(ring, elo, ehi)
        elif kind == "transition":
            verts, faces = slab_band(ring, ehi, elo)   # inner=plate, outer=existing
        elif kind in ("cap", "tread", "drainage"):
            z = elo if kind == "drainage" else ehi
            verts, faces = slab_band(ring, z, z)
        elif kind in ("ada", "stage", "cut"):
            z = ez if ez is not None else (ehi if ehi is not None else 612.5)
            verts, faces = fan_poly(ring, z)
        else:
            continue
        path = os.path.join(MESH_OUT, f"{oid}.obj")
        with open(path, "w") as fh:
            fh.write(_obj(verts, faces, oid))
        manifest["meshes"].append({
            "op_id": oid, "obj": os.path.relpath(path, T.REPO),
            "surface_class": o.get("surface_class"),
            "material": o.get("material"),
            "debug_color": o.get("debug_color"),
            "suppress_terrain_draw": o.get("suppress_terrain_draw", False),
            "render_lift_ft": T.RENDER_LIFT_FT,
            "verts": len(verts), "faces": len(faces)})
        written += 1

    with open(os.path.join(MESH_OUT, "mesh_manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)

    # headless well-formedness check
    bad = [m for m in manifest["meshes"] if m["verts"] < 3 or m["faces"] < 1]
    print(f"  wrote {written} op meshes -> {os.path.relpath(MESH_OUT, T.REPO)}/")
    print(f"  mesh_manifest.json: {len(manifest['meshes'])} entries, "
          f"malformed: {len(bad)}")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(build())
