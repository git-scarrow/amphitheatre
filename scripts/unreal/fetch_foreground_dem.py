#!/usr/bin/env python3
"""Reproducible USGS 3DEP foreground-terrain fetch for the CivicBowl scene.

Open data only (USGS 3D Elevation Program, public domain). Pulls a 1 m DEM clip
over the Foreground_HiFi AOI — the corridor from the seating/stage NNW across the
treatment cell / lawn / waterfront edge to Little Traverse Bay — so the foreground
ground surface beyond the ~244 m project DEM has real, georeferenced relief.

Why 3DEP and not the project DEM: ``unreal_export/terrain/*`` only covers an
~244 m square around the bowl. The bay shore is ~1.2 km NNW, so the foreground
needs elevation past the project tile. 3DEP returns NAVD88 **metres**, which is
exactly the CivicBowl local-z (local z = NAVD88 ft x 0.3048 = NAVD88 m), so it
stitches in on the same vertical datum with no offset.

The DEM is requested in **EPSG:6494** (imageSR=6494) so every pixel centre has a
known EPSG:6494 (x,y) ft -> direct ``civicbowl_common.ft_xy_to_enu`` with no
per-pixel reprojection; elevation (m) is the ENU z directly.

By default this prints the request + expected paths WITHOUT touching the network
(documents the acquisition path in no-egress environments). ``--run`` downloads.

    python scripts/unreal/fetch_foreground_dem.py            # show request + paths
    python scripts/unreal/fetch_foreground_dem.py --run      # download -> data/context/dem/

Output (consumed by gen_context.py fg_terrain layer; public domain — keep credit):
    data/context/dem/foreground_3dep.tif            (float32 NAVD88 m, EPSG:6494)
    data/context/dem/foreground_3dep.provenance.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import civicbowl_common as cb  # noqa: E402

# USGS 3DEP dynamic elevation ImageServer (returns elevation in metres, NAVD88).
SERVICE = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage"
ATTRIBUTION = "U.S. Geological Survey, 3D Elevation Program (3DEP), public domain"
HTTP_HEADERS = {"User-Agent": "amphitheatre-civicbowl-context/0.1 (Petoskey Pit; sscarrow@gmail.com)"}

# Foreground_HiFi AOI (lon/lat WGS84) — bowl + NNW bay-view corridor to the shore.
AOI_LONLAT = {"west": -84.9665, "south": 45.3715, "east": -84.9515, "north": 45.3855}
TARGET_RES_M = 1.0   # native 3DEP 1 m


def aoi_6494():
    """AOI bbox in EPSG:6494 ft + a ~1 m pixel grid size."""
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:4326", "EPSG:6494", always_xy=True)
    xs, ys = [], []
    for lon in (AOI_LONLAT["west"], AOI_LONLAT["east"]):
        for lat in (AOI_LONLAT["south"], AOI_LONLAT["north"]):
            x, y = t.transform(lon, lat)
            xs.append(x); ys.append(y)
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    w_m = (xmax - xmin) * cb.FT_TO_M
    h_m = (ymax - ymin) * cb.FT_TO_M
    nx = max(1, round(w_m / TARGET_RES_M))
    ny = max(1, round(h_m / TARGET_RES_M))
    return (xmin, ymin, xmax, ymax), (nx, ny), (w_m, h_m)


def export_params(bbox_ft, size):
    xmin, ymin, xmax, ymax = bbox_ft
    nx, ny = size
    return {
        "bbox": f"{xmin},{ymin},{xmax},{ymax}",
        "bboxSR": "6494", "imageSR": "6494",
        "size": f"{nx},{ny}",
        "format": "tiff", "pixelType": "F32",
        "interpolation": "RSP_BilinearInterpolation",
        "f": "image",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--run", action="store_true", help="actually hit the 3DEP service (needs HTTPS egress)")
    args = ap.parse_args()
    root = cb.repo_root(args.repo)
    outdir = os.path.join(root, "data", "context", "dem")
    tif = os.path.join(outdir, "foreground_3dep.tif")
    prov = os.path.join(outdir, "foreground_3dep.provenance.json")

    bbox_ft, size, (w_m, h_m) = aoi_6494()
    params = export_params(bbox_ft, size)

    print("== USGS 3DEP foreground-DEM fetch (public domain) ==")
    print(f"AOI lon/lat   : {AOI_LONLAT}")
    print(f"AOI size      : {w_m:.0f} m (E-W) x {h_m:.0f} m (N-S)  @ {TARGET_RES_M:g} m -> {size[0]}x{size[1]} px")
    print(f"service       : {SERVICE}")
    print(f"bbox (EPSG6494 ft): {params['bbox']}")
    print(f"dem ->        : {tif}")

    if not args.run:
        print("\n(interface mode — no network call. Re-run with --run to download.)")
        print("Absent this file, gen_context.py records the fg_terrain layer as DEFERRED.")
        return 0

    import urllib.parse
    import urllib.request
    os.makedirs(outdir, exist_ok=True)
    url = SERVICE + "?" + urllib.parse.urlencode(params)
    print("\n[fetch] GET 3DEP exportImage …")
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = resp.read()
    with open(tif, "wb") as fh:
        fh.write(data)

    stats = None
    try:
        import numpy as np
        import rasterio
        with rasterio.open(tif) as ds:
            a = ds.read(1)
            v = a[np.isfinite(a)]
            stats = {"shape": list(a.shape), "crs": str(ds.crs),
                     "elev_m_min": float(v.min()), "elev_m_max": float(v.max()),
                     "elev_m_mean": round(float(v.mean()), 2),
                     "bounds": list(ds.bounds)}
    except Exception as exc:
        print(f"[fetch] (rasterio verify skipped: {exc.__class__.__name__})")

    provenance = {
        "source": "USGS 3DEP Elevation ImageServer (exportImage)", "attribution": ATTRIBUTION,
        "service": SERVICE, "request_params": params,
        "aoi_lonlat": AOI_LONLAT, "target_res_m": TARGET_RES_M,
        "vertical_datum": "NAVD88", "elevation_units": "metres",
        "spatial_crs": "EPSG:6494 (NAD83(2011) Michigan, intl ft)",
        "z_note": "elevation metres == CivicBowl local-z directly (local z = NAVD88 ft x 0.3048 = NAVD88 m)",
        "bytes": len(data), "raster": stats,
    }
    with open(prov, "w") as fh:
        json.dump(provenance, fh, indent=1, sort_keys=True)
    print(f"[fetch] wrote {len(data)} bytes -> {tif}")
    if stats:
        print(f"[fetch] raster {stats['shape']} {stats['crs']}  "
              f"elev[m] {stats['elev_m_min']:.1f}..{stats['elev_m_max']:.1f}")
    print("[fetch] now run: python scripts/unreal/gen_context.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
