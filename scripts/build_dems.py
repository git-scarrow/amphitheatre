#!/usr/bin/env python3
"""
Stage 1 — build clean ground DEMs from USGS LiDAR for the Petoskey Pit AOI.

Reproducible driver: composes a PDAL pipeline (merge two tiles -> ground class 2
-> crop to AOI+margin -> writers.gdal IDW) and runs it for both resolutions.

CRS: EPSG:6494  NAD83(2011) / Michigan Central (INTERNATIONAL feet).  <-- note: intl ft, not US survey ft
Vertical: NAVD88 (Geoid12A), international feet (from LAZ header).

Run inside the project venv (only used for orchestration; PDAL is the system CLI).
"""
import json, subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEM = ROOT / "dem"
DEM.mkdir(exist_ok=True)

TILES = [
    DATA / "USGS_LPC_MI_13County_2015_C16_532749.laz",
    DATA / "USGS_LPC_MI_13County_2015_C16_532751.laz",
]

# AOI center (EPSG:6494, intl ft) = reprojected prior EPT-request centroid.
CE, CN = 19533022.70, 750785.65

# (label, filename, resolution_ft, half_extent_ft)
JOBS = [
    ("design",  DEM / "dem_design_1ft.tif",   1.0, 400.0),
    ("context", DEM / "dem_context_2p5ft.tif", 2.5, 800.0),
]

MARGIN = 30.0  # ft: crop a little beyond the grid so edge cells have neighbours for IDW

def pipeline(out_path, res, half):
    emin, emax = CE - half, CE + half
    nmin, nmax = CN - half, CN + half
    crop_bounds = f"([{emin-MARGIN},{emax+MARGIN}],[{nmin-MARGIN},{nmax+MARGIN}])"
    return {
        "pipeline": [
            *[str(t) for t in TILES],
            {"type": "filters.merge"},
            # ground only (ASPRS class 2); this also excludes noise (7), water (9), etc.
            {"type": "filters.range", "limits": "Classification[2:2]"},
            {"type": "filters.crop", "bounds": crop_bounds},
            {
                "type": "writers.gdal",
                "filename": str(out_path),
                "resolution": res,
                "output_type": "idw",
                "window_size": 3,          # fill small holes from neighbouring cells
                "gdaldriver": "GTiff",
                "data_type": "float32",
                "nodata": -9999.0,
                "bounds": f"([{emin},{emax}],[{nmin},{nmax}])",
                "gdalopts": "COMPRESS=DEFLATE,TILED=YES",
                "override_srs": "EPSG:6494",
            },
        ]
    }

def main():
    for label, out, res, half in JOBS:
        pj = pipeline(out, res, half)
        pf = ROOT / "scripts" / f"pipeline_{label}.json"
        pf.write_text(json.dumps(pj, indent=2))
        print(f"[{label}] {res} ft -> {out.name}  (AOI {2*half:.0f}x{2*half:.0f} ft)")
        r = subprocess.run(["pdal", "pipeline", str(pf)], capture_output=True, text=True)
        if r.returncode != 0:
            print("PDAL FAILED:\n", r.stderr, file=sys.stderr)
            sys.exit(1)
        print(f"  OK  pipeline={pf.name}")
    print("done")

if __name__ == "__main__":
    main()
