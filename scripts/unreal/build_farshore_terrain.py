#!/usr/bin/env python3
"""Mesh the opposite (N/NW) shore of Little Traverse Bay from the far-shore 3DEP DEM.

OFFLINE (no Unreal). Reuses the SAME coordinate contract + DEM→mesh code as
``gen_context.py`` (``_load_dem`` / ``_dem_mesh_enu`` / the ENU→UE bake matrix), so
the far-shore terrain lands in the identical EPSG:6494-ft → local-ENU-m → UE frame as
every other context mesh, with no per-vertex reprojection and no datum offset.

It produces ONE static mesh, ``ctx_farshore_terrain.obj`` — the real Harbor Springs /
Harbor Point headland + bluffs — to REPLACE the flat ``ctx_distant_horizon_band``
proxy in the bay-view / sunset backdrop.

Land clip: the fetched DEM tile also covers open bay / Lake Michigan water (3DEP
returns ~lake level there). Cells at or below ``WATER_ELEV_M + WATER_MARGIN_M`` are
masked to NaN so only land that rises above the water is meshed — a data-driven
shoreline with no OSM dependency. A ``min_north_local_m`` floor keeps the mesh well
north of the water plane / audited terrain so it can never overlap them.

    python scripts/unreal/build_farshore_terrain.py            # show plan (no write)
    python scripts/unreal/build_farshore_terrain.py --run      # write the OBJ

Input : data/context/dem/farshore_3dep.tif   (from fetch_farshore_dem.py --run)
Output: build/unreal_scene/meshes/ctx_farshore_terrain.obj
        build/unreal_scene/meshes/ctx_farshore_terrain.stats.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import civicbowl_common as cb   # noqa: E402
import context_common as ctx    # noqa: E402
import gen_context as gc        # noqa: E402  (reuse _load_dem / _dem_mesh_enu / UE bake)

import numpy as np  # noqa: E402

FAR_DEM_REL = "data/context/dem/farshore_3dep.tif"
OUT_REL = "build/unreal_scene/meshes/ctx_farshore_terrain.obj"

# Cells at/below this elevation are water (bay / Lake Michigan) -> dropped. Water
# datum is 176.62 m; a small margin removes the flat lake surface + wave-noise edge
# without eating the genuine low shoreline.
WATER_MARGIN_M = 1.5
# Floor so the meshed land stays north of the bay water plane (far edge 3500 m) and
# never overlaps the audited project / foreground terrain. The real far shoreline is
# ~3.8-4 km north, so this only ever trims open water, never land.
MIN_NORTH_LOCAL_M = 3000.0
DECIMATE_STRIDE = 2      # 10 m DEM -> ~20 m mesh; plenty for a 5 km-distant backdrop


def build(root: str, write: bool) -> dict:
    dem_path = os.path.join(root, FAR_DEM_REL)
    if not os.path.exists(dem_path):
        raise SystemExit(f"[farshore] missing DEM {dem_path}\n"
                         "  run: python scripts/unreal/fetch_farshore_dem.py --run")
    arr, tr = gc._load_dem(dem_path)              # Z[m] (NaN voids), EPSG:6494 affine

    water_cut = ctx.WATER_ELEV_M + WATER_MARGIN_M
    arr_land = arr.copy()
    arr_land[arr_land <= water_cut] = np.nan       # drop bay / lake water cells

    n_total = int(np.isfinite(arr).sum())
    n_land = int(np.isfinite(arr_land).sum())

    mesh, extent = gc._dem_mesh_enu(arr_land, tr, DECIMATE_STRIDE, MIN_NORTH_LOCAL_M, keep=None)
    if mesh is None:
        raise SystemExit("[farshore] no mesh produced (all cells clipped?) — check AOI / water cut")

    emin, emax, nmin, nmax, ztop = extent
    stats = {
        "dem": FAR_DEM_REL,
        "water_cut_m": round(water_cut, 3),
        "min_north_local_m": MIN_NORTH_LOCAL_M,
        "decimate_stride": DECIMATE_STRIDE,
        "cells_total_finite": n_total,
        "cells_land_kept": n_land,
        "land_fraction": round(n_land / max(1, n_total), 3),
        "vertices": int(len(mesh.vertices)),
        "triangles": int(len(mesh.faces)),
        "extent_enu_m": {"emin": round(emin, 1), "emax": round(emax, 1),
                          "nmin": round(nmin, 1), "nmax": round(nmax, 1), "ztop": round(ztop, 1)},
        "ztop_above_water_m": round(ztop - ctx.WATER_ELEV_M, 1),
        "water_elev_m": round(ctx.WATER_ELEV_M, 3),
        "note": "real USGS 3DEP terrain (public domain); replaces flat ctx_distant_horizon_band",
    }

    print("== build far-shore terrain mesh ==")
    print(f"DEM            : {dem_path}")
    print(f"water cut      : z <= {water_cut:.2f} m dropped  (water datum {ctx.WATER_ELEV_M:.2f} m)")
    print(f"land cells     : {n_land}/{n_total}  ({stats['land_fraction']*100:.0f}%)  stride {DECIMATE_STRIDE}")
    print(f"mesh           : {stats['vertices']} verts / {stats['triangles']} tris")
    print(f"extent ENU m   : E[{emin:.0f}..{emax:.0f}] N[{nmin:.0f}..{nmax:.0f}] ztop {ztop:.1f} "
          f"(= {stats['ztop_above_water_m']:.0f} m above water)")

    if write:
        out = os.path.join(root, OUT_REL)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        mesh.export(out, file_type="obj")
        with open(out.replace(".obj", ".stats.json"), "w") as fh:
            json.dump(stats, fh, indent=1, sort_keys=True)
        print(f"[farshore] wrote {out}")
        print(f"[farshore] import to UE: /Game/Meshes/CivicBowl/ctx_farshore_terrain")
    else:
        print("\n(plan mode — no write. Re-run with --run to export the OBJ.)")
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--run", action="store_true", help="write the OBJ (default: plan only)")
    args = ap.parse_args()
    root = cb.repo_root(args.repo)
    build(root, args.run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
