"""
Validate suspect DEM cells in the eastern seating rim against raw LiDAR returns.

Suspect zone: outer seating rows (R=115-130 ft from arc centre, full fan arc),
where the harness was seeing terrain values suggesting 30°+ slopes that may be
DEM artifacts (classification error, rim-break, vegetation bleed-through).

For each 1-ft DEM cell in the suspect zone the script:
  1. Computes the local slope from the DEM.
  2. Queries the .laz point cloud for returns within that cell's footprint.
  3. Reports: return count, classification breakdown, raw Z spread, DEM Z,
     and a SUSPECT flag when ground-classified returns don't support the DEM.

Outputs
-------
  - Console table of all cells with slope > SLOPE_FLAG_DEG
  - suspect_cells.csv  — machine-readable flagged cells
  - dem_validation.png — hillshade + slope overlay + flagged cells scatter

Usage
-----
  cd /home/sam/projects/amphitheatre
  source .venv/bin/activate
  python3 scripts/validate_dem_lidar.py
"""
from __future__ import annotations

import csv
import math
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import rasterio
from rasterio.transform import rowcol
from scipy.ndimage import generic_filter
import laspy

# ── configuration ────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
DEM_PATH     = PROJECT_ROOT / "dem/dem_design_1ft.tif"
LAZ_PATHS    = sorted((PROJECT_ROOT / "data").glob("*.laz"))

# Arc centre in EPSG:6494 (NAD83/Michigan Central, international feet)
CX = 19533067.7
CY = 750799.2

AX_AZ    = 150.0   # bowl axis azimuth (toward stage from seating)
FAN_HALF = 55.0    # half-fan width, degrees

R_SUSPECT_INNER = 110.0   # ft — start checking here
R_SUSPECT_OUTER = 135.0   # ft — extend slightly beyond outermost row band

# Flag cells whose DEM-derived slope exceeds this (degrees)
SLOPE_FLAG_DEG = 25.0

# Flag cells where DEM Z exceeds the median ground return Z by more than this
HEIGHT_EXCESS_FT = 1.0

OUT_CSV = PROJECT_ROOT / "suspect_cells.csv"
OUT_PNG = PROJECT_ROOT / "dem_validation.png"

# ── helpers ──────────────────────────────────────────────────────────────────

def polar_from_centre(X: np.ndarray, Y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (radius_ft, azimuth_deg_from_north_clockwise) for each (X,Y)."""
    dx = X - CX
    dy = Y - CY
    R = np.hypot(dx, dy)
    az = np.degrees(np.arctan2(dx, dy)) % 360.0   # clockwise from N
    return R, az

def in_fan(R: np.ndarray, az: np.ndarray) -> np.ndarray:
    """Boolean mask: within the seating fan and suspect radial band."""
    az_diff = (az - AX_AZ + 180) % 360 - 180      # signed diff to axis
    return (
        (R >= R_SUSPECT_INNER) & (R <= R_SUSPECT_OUTER) &
        (np.abs(az_diff) <= FAN_HALF)
    )

def slope_degrees(Z: np.ndarray, res: float = 1.0) -> np.ndarray:
    """Compute per-cell slope in degrees from a 2-D elevation array."""
    dy, dx = np.gradient(np.where(np.isfinite(Z), Z, np.nan), res, res)
    return np.degrees(np.arctan(np.hypot(dx, dy)))

# ── 1. load DEM and identify suspect cells ───────────────────────────────────

print("Loading DEM…")
with rasterio.open(DEM_PATH) as ds:
    Z   = ds.read(1).astype(np.float64)
    nodata = ds.nodata or -9999.0
    Z[Z == nodata] = np.nan
    tf  = ds.transform
    ny, nx = Z.shape
    res = tf.a                          # pixel size in ft (assumed square)
    crs = ds.crs

# Build coordinate grids (cell centres)
cols = np.arange(nx)
rows = np.arange(ny)
Xc = tf.c + (cols + 0.5) * tf.a       # easting
Yc = tf.f + (rows + 0.5) * tf.e       # northing (tf.e is negative)
Xgrid, Ygrid = np.meshgrid(Xc, Yc)

R_grid, AZ_grid = polar_from_centre(Xgrid, Ygrid)
fan_mask = in_fan(R_grid, AZ_grid) & np.isfinite(Z)

slope = slope_degrees(Z, res)

# Suspect by slope alone
slope_flag  = fan_mask & (slope > SLOPE_FLAG_DEG)
flagged_rows, flagged_cols = np.where(slope_flag)

print(f"  DEM size : {ny}×{nx} px  ({ny*nx:,} cells)")
print(f"  Fan+band : {fan_mask.sum():,} cells")
print(f"  Slope>{SLOPE_FLAG_DEG:.0f}°: {slope_flag.sum():,} cells")

# ── 2. load LAZ returns inside the bounding box of the suspect zone ──────────

# Compute bounding box of suspect region
if slope_flag.any():
    fx = Xgrid[slope_flag]
    fy = Ygrid[slope_flag]
    xmin, xmax = fx.min() - 2, fx.max() + 2
    ymin, ymax = fy.min() - 2, fy.max() + 2
else:
    # fall back to full fan+band bbox
    fx = Xgrid[fan_mask]; fy = Ygrid[fan_mask]
    xmin, xmax = fx.min() - 2, fx.max() + 2
    ymin, ymax = fy.min() - 2, fy.max() + 2

print(f"\nLoading LiDAR returns in bbox X=[{xmin:.0f},{xmax:.0f}] Y=[{ymin:.0f},{ymax:.0f}]…")
if not LAZ_PATHS:
    print("  ERROR: no .laz files found in data/"); sys.exit(1)

all_px = []; all_py = []; all_pz = []; all_cls = []

for laz_path in LAZ_PATHS:
    print(f"  reading {laz_path.name}…")
    with laspy.open(laz_path) as f:
        lf = f.read()
    # LiDAR coordinates are stored as integers; apply scale+offset
    px = np.array(lf.x, dtype=np.float64)
    py = np.array(lf.y, dtype=np.float64)
    pz = np.array(lf.z, dtype=np.float64)
    cls = np.array(lf.classification, dtype=np.uint8)

    keep = (px >= xmin) & (px <= xmax) & (py >= ymin) & (py <= ymax)
    all_px.append(px[keep]); all_py.append(py[keep])
    all_pz.append(pz[keep]); all_cls.append(cls[keep])
    print(f"    {keep.sum():,} returns in bbox  (total in file: {len(px):,})")

px = np.concatenate(all_px)
py = np.concatenate(all_py)
pz = np.concatenate(all_pz)
cls = np.concatenate(all_cls)
print(f"  Total returns loaded: {len(px):,}")

# ── 3. per-cell analysis ─────────────────────────────────────────────────────

# Build a lookup: bin LiDAR returns to 1-ft DEM cells
def xy_to_rc(x, y):
    """Convert map coordinates to (row, col) indices in the DEM grid."""
    c = ((x - tf.c) / tf.a - 0.5).astype(int)
    r = ((y - tf.f) / tf.e - 0.5).astype(int)
    valid = (r >= 0) & (r < ny) & (c >= 0) & (c < nx)
    return r, c, valid

pt_rows, pt_cols, pt_valid = xy_to_rc(px, py)
px, py, pz, cls = px[pt_valid], py[pt_valid], pz[pt_valid], cls[pt_valid]
pt_rows, pt_cols = pt_rows[pt_valid], pt_cols[pt_valid]

# Build per-cell lists using a dict keyed by (row, col)
from collections import defaultdict
cell_returns = defaultdict(list)   # (r,c) -> list of (z, classification)
for i in range(len(px)):
    cell_returns[(pt_rows[i], pt_cols[i])].append((pz[i], cls[i]))

print(f"  Returns mapped to {len(cell_returns):,} DEM cells")

# ── 4. evaluate flagged cells ─────────────────────────────────────────────────

CLASS_NAMES = {
    0: "never_classified", 1: "unclassified", 2: "ground", 3: "low_veg",
    4: "medium_veg", 5: "high_veg", 6: "building", 7: "noise",
    9: "water", 18: "high_noise",
}

results = []
print(f"\n{'':─<100}")
header = (f"{'row':>5} {'col':>5} {'X':>12} {'Y':>12} {'R':>7} {'az':>6} "
          f"{'Z_dem':>7} {'slope°':>7} {'n_ret':>6} {'n_gnd':>6} "
          f"{'gnd_med':>8} {'gnd_max':>8} {'excess':>7} {'flag'}")
print(header)
print(f"{'':─<100}")

for ri, ci in zip(flagged_rows, flagged_cols):
    x = float(Xgrid[ri, ci])
    y = float(Ygrid[ri, ci])
    z_dem = float(Z[ri, ci])
    sl = float(slope[ri, ci])
    r_ft = float(R_grid[ri, ci])
    az = float(AZ_grid[ri, ci])

    returns = cell_returns.get((ri, ci), [])
    n_ret = len(returns)
    ground = [z for z, c in returns if c == 2]
    n_gnd = len(ground)

    gnd_med = float(np.median(ground)) if ground else float("nan")
    gnd_max = float(np.max(ground))    if ground else float("nan")
    excess  = z_dem - gnd_max          if ground else float("nan")

    # Flag conditions
    flags = []
    if n_ret == 0:
        flags.append("NO_RETURNS")
    elif n_gnd == 0:
        flags.append("NO_GROUND")
    if math.isfinite(excess) and excess > HEIGHT_EXCESS_FT:
        flags.append(f"DEM_HIGH+{excess:.1f}ft")
    if n_gnd > 0 and n_gnd / n_ret < 0.2 and n_ret >= 3:
        flags.append(f"LOW_GND_RATIO({n_gnd}/{n_ret})")

    flag_str = "|".join(flags) if flags else "ok"

    row_out = {
        "dem_row": ri, "dem_col": ci, "X": round(x, 1), "Y": round(y, 1),
        "R_ft": round(r_ft, 1), "az_deg": round(az, 1),
        "Z_dem": round(z_dem, 2), "slope_deg": round(sl, 1),
        "n_returns": n_ret, "n_ground": n_gnd,
        "ground_median_Z": round(gnd_med, 2) if math.isfinite(gnd_med) else "",
        "ground_max_Z": round(gnd_max, 2)    if math.isfinite(gnd_max) else "",
        "dem_minus_gnd_max": round(excess, 2) if math.isfinite(excess) else "",
        "flags": flag_str,
    }
    results.append(row_out)

    print(f"{ri:>5} {ci:>5} {x:>12.1f} {y:>12.1f} {r_ft:>7.1f} {az:>6.1f} "
          f"{z_dem:>7.2f} {sl:>7.1f} {n_ret:>6} {n_gnd:>6} "
          f"{gnd_med:>8.2f} {gnd_max:>8.2f} {excess:>7.2f}  {flag_str}")

# ── 5. summary counts ─────────────────────────────────────────────────────────

n_no_returns = sum(1 for r in results if "NO_RETURNS" in r["flags"])
n_no_ground  = sum(1 for r in results if "NO_GROUND"  in r["flags"])
n_dem_high   = sum(1 for r in results if "DEM_HIGH"   in r["flags"])
n_ok         = sum(1 for r in results if r["flags"] == "ok")

print(f"\n{'':─<100}")
print(f"SUMMARY  ({len(results)} cells above {SLOPE_FLAG_DEG}° slope in suspect zone)")
print(f"  ok (ground returns support DEM) : {n_ok}")
print(f"  NO_RETURNS (nothing in .laz)    : {n_no_returns}")
print(f"  NO_GROUND  (no class-2 returns) : {n_no_ground}")
print(f"  DEM_HIGH   (DEM > max gnd +{HEIGHT_EXCESS_FT:.1f}ft): {n_dem_high}")

# ── 6. write CSV ──────────────────────────────────────────────────────────────

with open(OUT_CSV, "w", newline="") as fh:
    if results:
        writer = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
print(f"\nCSV written → {OUT_CSV.relative_to(PROJECT_ROOT)}")

# ── 7. plot ───────────────────────────────────────────────────────────────────

print("Rendering validation map…")

# crop DEM to suspect bbox
r0 = max(0, int((ymax - tf.f) / tf.e))
r1 = min(ny, int((ymin - tf.f) / tf.e) + 1)
c0 = max(0, int((xmin - tf.c) / tf.a))
c1 = min(nx, int((xmax - tf.c) / tf.a) + 1)
Zc = Z[r0:r1, c0:c1]
Sc = slope[r0:r1, c0:c1]

fig, axes = plt.subplots(1, 2, figsize=(16, 8))
fig.suptitle("DEM validation — suspect eastern rim cells", fontsize=13, fontweight="bold")

extent = [
    tf.c + c0 * tf.a, tf.c + c1 * tf.a,
    tf.f + r1 * tf.e, tf.f + r0 * tf.e,
]

# left: DEM hillshade with slope overlay
ax = axes[0]
ax.set_title("Slope (°) — suspect zone")
im = ax.imshow(Sc, extent=extent, origin="upper",
               cmap="RdYlGn_r", vmin=0, vmax=40, interpolation="nearest")
plt.colorbar(im, ax=ax, label="slope (°)", shrink=0.8)

# overlay flagged cell locations
if results:
    xs_ok  = [r["X"] for r in results if r["flags"] == "ok"]
    ys_ok  = [r["Y"] for r in results if r["flags"] == "ok"]
    xs_bad = [r["X"] for r in results if r["flags"] != "ok"]
    ys_bad = [r["Y"] for r in results if r["flags"] != "ok"]
    if xs_ok:
        ax.scatter(xs_ok, ys_ok, s=12, c="lime", marker="o", label="slope>25° / gnd ok", zorder=5)
    if xs_bad:
        ax.scatter(xs_bad, ys_bad, s=30, c="red", marker="x", linewidths=1.5,
                   label="SUSPECT (no gnd / DEM high)", zorder=6)
    ax.legend(fontsize=8, loc="upper left")

ax.set_xlabel("Easting (ft, EPSG:6494)")
ax.set_ylabel("Northing (ft)")
ax.plot(CX, CY, "b*", ms=12, label="arc centre")

# right: DEM elevation
ax2 = axes[1]
ax2.set_title("DEM elevation (ft NAVD88)")
im2 = ax2.imshow(Zc, extent=extent, origin="upper",
                 cmap="terrain", interpolation="nearest")
plt.colorbar(im2, ax=ax2, label="elev (ft)", shrink=0.8)
if results:
    if xs_bad:
        ax2.scatter(xs_bad, ys_bad, s=30, c="red", marker="x",
                    linewidths=1.5, label="SUSPECT", zorder=6)
ax2.plot(CX, CY, "b*", ms=12)
ax2.set_xlabel("Easting (ft, EPSG:6494)")

plt.tight_layout()
plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
plt.close()
print(f"Map written  → {OUT_PNG.relative_to(PROJECT_ROOT)}")
