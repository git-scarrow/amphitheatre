#!/usr/bin/env python3
"""Fetch + clip USGS 3DEP 1 m DEMs for the comparator sites.

Reads only the needed window from the cloud-hosted USGS GeoTIFF via GDAL
/vsicurl/ range requests (no full-tile download), writes a native-CRS clip to
data/comparators/<slug>/dem/dem_clip_1m.tif, and records full provenance
(source URL, CRS, resolution, nodata, window bounds, stats) to
data/comparators/<slug>/dem/provenance.json.

Reproduce:  .venv/bin/python scripts/comparators/fetch_comparator_dem.py
"""
import json
import os
import sys

import numpy as np
import pyproj
import rasterio
from rasterio.windows import from_bounds

sys.path.insert(0, os.path.dirname(__file__))
from sites import SITES

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))


def fetch_site(slug, site):
    url = site["dem_product"]["url"]
    lon, lat = site["center_lonlat"]
    half = site["clip_half_m"]
    out_dir = os.path.join(ROOT, "data", "comparators", slug, "dem")
    os.makedirs(out_dir, exist_ok=True)
    out_tif = os.path.join(out_dir, "dem_clip_1m.tif")

    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open("/vsicurl/" + url) as src:
            to_native = pyproj.Transformer.from_crs("EPSG:4326", src.crs,
                                                    always_xy=True)
            cx, cy = to_native.transform(lon, lat)
            bounds = (cx - half, cy - half, cx + half, cy + half)
            win = from_bounds(*bounds, transform=src.transform)
            win = win.round_offsets().round_lengths()
            data = src.read(1, window=win)
            transform = src.window_transform(win)
            nodata = src.nodata
            profile = {
                "driver": "GTiff", "dtype": "float32", "count": 1,
                "height": data.shape[0], "width": data.shape[1],
                "crs": src.crs, "transform": transform, "nodata": nodata,
                "compress": "deflate", "predictor": 3, "tiled": True,
            }
            crs_str = src.crs.to_string()
            res = src.res

    valid = data[data != nodata] if nodata is not None else data
    if valid.size == 0:
        raise RuntimeError(f"{slug}: clip window contains no valid DEM cells")

    with rasterio.open(out_tif, "w", **profile) as dst:
        dst.write(data.astype("float32"), 1)

    prov = {
        "site": site["name"],
        "slug": slug,
        "source_url": url,
        "dem_product": site["dem_product"],
        "access_method": "GDAL /vsicurl/ windowed read (this script)",
        "fetched_on": site.get("fetched_on", "2026-06-12"),
        "native_crs": crs_str,
        "native_resolution_m": [res[0], res[1]],
        "vertical": "NAVD88 meters (USGS 3DEP standard for 1 m DEM products)",
        "center_lonlat_wgs84": [lon, lat],
        "center_native_xy": [cx, cy],
        "clip_bounds_native": list(bounds),
        "clip_shape_px": [int(data.shape[0]), int(data.shape[1])],
        "elev_min_m": float(valid.min()),
        "elev_max_m": float(valid.max()),
        "nodata": nodata,
        "units_policy": ("clip kept in native meters; all derived metrics "
                         "convert to feet explicitly (suffix _ft)"),
    }
    with open(os.path.join(out_dir, "provenance.json"), "w") as f:
        json.dump(prov, f, indent=1)
    print(f"{slug}: {data.shape} px, CRS {crs_str}, res {res}, "
          f"z [{valid.min():.1f}, {valid.max():.1f}] m -> {out_tif}")


def main():
    for slug, site in SITES.items():
        fetch_site(slug, site)


if __name__ == "__main__":
    main()
