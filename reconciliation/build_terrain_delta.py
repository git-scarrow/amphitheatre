#!/usr/bin/env python3
"""Regenerate reconciliation/terrain_delta.tif = proposed_grade (after) - (before).

The delta raster is git-ignored (project convention: rasters are regenerable). This
script reproduces it from the two proposed-grade rasters that `build_proposed_grade.py`
emits (run it once with all_touched=True -> proposed_grade_1ft.tif, and once with the
pre-fix all_touched=False -> proposed_grade_1ft.before.tif). Net volume must tie to the
grading manifest (+52.9 CY fill at the time of the judge commit).
"""
import os
import numpy as np
import rasterio

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AFTER  = os.path.join(BASE, "dem", "proposed_grade_1ft.tif")
BEFORE = os.path.join(BASE, "dem", "proposed_grade_1ft.before.tif")
OUT    = os.path.join(BASE, "reconciliation", "terrain_delta.tif")

a = rasterio.open(AFTER);  after  = a.read(1); nd = a.nodata
b = rasterio.open(BEFORE); before = b.read(1)
valid = np.isfinite(after) & np.isfinite(before) & (after != nd) & (before != nd)
delta = np.where(valid, after - before, np.nan)
d = delta[valid & (np.abs(delta) > 0.001)]
cy_fill = float(d[d > 0].sum()) / 27.0
cy_cut  = float(-d[d < 0].sum()) / 27.0
print(f"changed cells: {int((np.abs(delta) > 0.001).sum())}  "
      f"FILL {cy_fill:.1f} CY  CUT {cy_cut:.1f} CY  NET {cy_fill - cy_cut:+.1f} CY")

prof = a.profile.copy(); prof.update(dtype="float32", count=1, nodata=-9999.0)
with rasterio.open(OUT, "w", **prof) as dst:
    dst.write(np.where(valid, delta, -9999.0).astype("float32"), 1)
print(f"wrote {os.path.relpath(OUT, BASE)}")
