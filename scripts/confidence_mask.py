"""
Build a LiDAR-support confidence mask over the full design DEM and overlay
all harness design decisions to reveal which conclusions rest on unsupported
interpolated terrain.

Confidence classes (per DEM cell)
  2 = GROUND-SUPPORTED   — at least one class-2 (ground) LiDAR return
  1 = RETURNS/NO-GROUND  — returns present but none classified as ground
  0 = ZERO-RETURN        — no LiDAR returns at all; DEM is interpolated

Outputs
-------
  dem/confidence_mask.tif     — single-band GeoTIFF (0/1/2) for harness use
  confidence_design_overlay.png — map showing confidence + design decisions
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import numpy as np
import rasterio
from rasterio.transform import from_bounds
import laspy
from shapely.geometry import shape
from rasterio.features import rasterize

# ── paths / constants ────────────────────────────────────────────────────────

ROOT     = Path(__file__).parent.parent
DEM_PATH = ROOT / "dem/dem_design_1ft.tif"
LAZ_PATHS = sorted((ROOT / "data").glob("*.laz"))
GEOJSON  = ROOT / "earthwork_scenarios.geojson"

OUT_TIF  = ROOT / "dem/confidence_mask.tif"
OUT_PNG  = ROOT / "confidence_design_overlay.png"

# Arc / bowl geometry (EPSG:6494)
CX, CY   = 19533067.7, 750799.2
AX_AZ    = 150.0        # bowl axis azimuth (toward stage)
FAN_HALF = 55.0         # half-fan width
R_ROWS   = [85 + 3*i for i in range(16)]   # row radii ft (85,88,...130)
ROW_LABELS = [f"R{i+1}" for i in range(16)]

# Variant delta files for decision-overlay
V0005_DELTA = ROOT / "variants/V0005/delta.tif"   # worst wall-trigger
V0008_DELTA = ROOT / "variants/V0008/delta.tif"   # grade_ceiling accepted

# ── 1. load DEM ───────────────────────────────────────────────────────────────

print("Loading DEM…")
with rasterio.open(DEM_PATH) as ds:
    Z    = ds.read(1).astype(np.float64)
    nd   = ds.nodata or -9999.0
    Z[Z == nd] = np.nan
    tf   = ds.transform
    crs  = ds.crs
    ny, nx = Z.shape
    res  = abs(tf.a)

# Cell-centre coordinate grids
cols = np.arange(nx); rows_i = np.arange(ny)
Xc = tf.c + (cols + 0.5) * tf.a
Yc = tf.f + (rows_i + 0.5) * tf.e
Xgrid, Ygrid = np.meshgrid(Xc, Yc)

dem_xmin = tf.c
dem_xmax = tf.c + nx * tf.a
dem_ymax = tf.f
dem_ymin = tf.f + ny * tf.e

print(f"  {ny}×{nx} px | X=[{dem_xmin:.0f},{dem_xmax:.0f}] Y=[{dem_ymin:.0f},{dem_ymax:.0f}]")

# ── 2. build confidence mask from raw LiDAR ───────────────────────────────────

# confidence: 0=no_returns, 1=returns_no_ground, 2=ground_supported
confidence = np.zeros((ny, nx), dtype=np.uint8)

def xy_to_rc(x, y):
    c = ((x - tf.c) / tf.a - 0.5).astype(int)
    r = ((y - tf.f) / tf.e - 0.5).astype(int)
    valid = (r >= 0) & (r < ny) & (c >= 0) & (c < nx)
    return r, c, valid

from pyproj import Transformer, CRS as ProjCRS

TARGET_CRS = ProjCRS.from_epsg(6494)   # NAD83(2011)/Michigan Central, int'l ft

for laz_path in LAZ_PATHS:
    print(f"Processing {laz_path.name}…")
    with laspy.open(laz_path) as f:
        lf = f.read()
    px = np.array(lf.x, dtype=np.float64)
    py = np.array(lf.y, dtype=np.float64)
    cls = np.array(lf.classification, dtype=np.uint8)

    # Reproject to EPSG:6494 if needed
    src_crs = lf.header.parse_crs()
    if src_crs is not None:
        try:
            src_epsg = ProjCRS.from_user_input(src_crs).to_epsg()
        except Exception:
            src_epsg = None
        if src_epsg and src_epsg != 6494:
            print(f"  reprojecting from EPSG:{src_epsg} → EPSG:6494…")
            tr = Transformer.from_crs(src_epsg, 6494, always_xy=True)
            px, py = tr.transform(px, py)

    # clip to DEM bbox
    keep = (px >= dem_xmin) & (px <= dem_xmax) & (py >= dem_ymin) & (py <= dem_ymax)
    px, py, cls = px[keep], py[keep], cls[keep]
    print(f"  {keep.sum():,} returns within DEM bbox")

    if len(px) == 0:
        continue

    pt_r, pt_c, valid = xy_to_rc(px, py)
    px, py, cls = px[valid], py[valid], cls[valid]
    pt_r, pt_c = pt_r[valid], pt_c[valid]

    # Mark cells that have any return
    confidence[pt_r, pt_c] = np.maximum(confidence[pt_r, pt_c], 1)

    # Upgrade to 2 where a ground return exists
    gnd = cls == 2
    if gnd.any():
        confidence[pt_r[gnd], pt_c[gnd]] = 2

# Cells outside DEM data extent stay 0 regardless
confidence[~np.isfinite(Z)] = 255   # nodata sentinel

counts = {0: (confidence == 0).sum(),
          1: (confidence == 1).sum(),
          2: (confidence == 2).sum()}
valid_cells = np.isfinite(Z).sum()
print(f"\nConfidence summary (valid DEM cells: {valid_cells:,})")
print(f"  Ground-supported  (2): {counts[2]:,}  ({100*counts[2]/valid_cells:.1f}%)")
print(f"  Returns/no-ground (1): {counts[1]:,}  ({100*counts[1]/valid_cells:.1f}%)")
print(f"  Zero-return       (0): {counts[0]:,}  ({100*counts[0]/valid_cells:.1f}%)")

# ── 3. save confidence mask GeoTIFF ──────────────────────────────────────────

prof = {
    "driver": "GTiff", "dtype": "uint8", "width": nx, "height": ny,
    "count": 1, "crs": crs, "transform": tf,
    "nodata": 255, "compress": "lzw",
}
with rasterio.open(OUT_TIF, "w", **prof) as dst:
    dst.write(confidence, 1)
print(f"Confidence mask → {OUT_TIF.relative_to(ROOT)}")

# ── 4. load variant deltas ────────────────────────────────────────────────────

def load_delta(path):
    if not path.exists():
        return np.zeros((ny, nx))
    with rasterio.open(path) as ds:
        d = ds.read(1).astype(np.float64)
        nd = ds.nodata or -9999.0
        d[d == nd] = 0.0
    return d

print("Loading variant deltas…")
d_v0005 = load_delta(V0005_DELTA)
d_v0008 = load_delta(V0008_DELTA)

# Wall-trigger cells: V0005 delta < -3.0 ft (depth that fired the trigger)
wall_cells = d_v0005 < -3.0
# Grade-ceiling affected cells: V0008 cut cells
gc_cells   = d_v0008 < -0.1

# Confidence class of those decision cells
def conf_breakdown(mask, label):
    total = mask.sum()
    if total == 0:
        print(f"  {label}: no cells")
        return
    c0 = (mask & (confidence == 0)).sum()
    c1 = (mask & (confidence == 1)).sum()
    c2 = (mask & (confidence == 2)).sum()
    print(f"  {label} ({total:,} cells): "
          f"ground-supported={c2} ({100*c2/total:.0f}%)  "
          f"no-ground={c1} ({100*c1/total:.0f}%)  "
          f"zero-return={c0} ({100*c0/total:.0f}%)")

print("\nDecision-cell confidence breakdown:")
conf_breakdown(wall_cells, "V0005 wall-trigger cells (delta<-3ft)")
conf_breakdown(gc_cells,   "V0008 grade_ceiling cells (delta<-0.1ft)")

# ── 5. geometry helpers ───────────────────────────────────────────────────────

def arc_xy(cx, cy, R, az_centre, fan_half, n=200):
    """Return (x, y) arrays for a fan arc."""
    az0 = math.radians(az_centre - fan_half)
    az1 = math.radians(az_centre + fan_half)
    angles = np.linspace(az0, az1, n)
    # azimuth is clockwise from north → x=sin, y=cos
    x = cx + R * np.sin(angles)
    y = cy + R * np.cos(angles)
    return x, y

def fan_edge(cx, cy, R_inner, R_outer, az):
    """Radial line from R_inner to R_outer at given azimuth."""
    az_r = math.radians(az)
    x = [cx + r * math.sin(az_r) for r in (R_inner, R_outer)]
    y = [cy + r * math.cos(az_r) for r in (R_inner, R_outer)]
    return x, y

# Load row-band polygons 13-16 from geojson for boundary overlay
with open(GEOJSON) as fh:
    fc = json.load(fh)

outer_bands = {}
for feat in fc["features"]:
    name = feat["properties"].get("name", "")
    if name in ("row_band_13", "row_band_14", "row_band_15", "row_band_16"):
        outer_bands[name] = shape(feat["geometry"])

# ── 6. plot ───────────────────────────────────────────────────────────────────

print("\nRendering overlay map…")

# Crop to design zone + generous buffer
buf = 20
r0_p = max(0, int((CY + R_ROWS[-1] + buf - tf.f) / tf.e))
r1_p = min(ny, int((CY - R_ROWS[-1] - buf - tf.f) / tf.e) + 1)
c0_p = max(0, int((CX - R_ROWS[-1] - buf - tf.c) / tf.a))
c1_p = min(nx, int((CX + R_ROWS[-1] + buf - tf.c) / tf.a) + 1)

Zp   = Z[r0_p:r1_p, c0_p:c1_p]
Cp   = confidence[r0_p:r1_p, c0_p:c1_p].astype(float)
Cp[Cp == 255] = np.nan

w5p  = wall_cells[r0_p:r1_p, c0_p:c1_p]
gc_p = gc_cells[r0_p:r1_p, c0_p:c1_p]

extent = [
    tf.c + c0_p * tf.a,
    tf.c + c1_p * tf.a,
    tf.f + r1_p * tf.e,
    tf.f + r0_p * tf.e,
]

fig, axes = plt.subplots(1, 2, figsize=(20, 10))
fig.suptitle(
    "LiDAR support confidence vs harness design decisions\n"
    "RED = zero LiDAR returns (interpolated DEM)  |  YELLOW = returns, no ground class  |  GREEN = ground-supported",
    fontsize=11, fontweight="bold"
)

# Confidence colour map: 0=red, 1=yellow, 2=green
from matplotlib.colors import ListedColormap, BoundaryNorm
cmap_conf = ListedColormap(["#d73027", "#fee08b", "#1a9850"])
norm_conf  = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cmap_conf.N)

for ax_i, ax in enumerate(axes):
    im = ax.imshow(Cp, extent=extent, origin="upper",
                   cmap=cmap_conf, norm=norm_conf,
                   interpolation="nearest", alpha=0.7)

    # DEM hillshade as context
    from scipy.ndimage import uniform_filter
    ls = np.gradient(np.where(np.isfinite(Zp), Zp, np.nan))
    shade = (-ls[0] - ls[1]) / 2.0
    shade = (shade - np.nanmin(shade)) / (np.nanmax(shade) - np.nanmin(shade) + 1e-9)
    ax.imshow(shade, extent=extent, origin="upper",
              cmap="gray", alpha=0.25, interpolation="bilinear")

    # Fan boundary lines
    for az_edge in (AX_AZ - FAN_HALF, AX_AZ + FAN_HALF):
        ex, ey = fan_edge(CX, CY, R_ROWS[0] - 5, R_ROWS[-1] + 10, az_edge)
        ax.plot(ex, ey, "k--", lw=0.8, alpha=0.6)

    # Row arcs (thin grey)
    for ri, R in enumerate(R_ROWS):
        ax_, ay_ = arc_xy(CX, CY, R, AX_AZ, FAN_HALF)
        lw = 1.5 if R >= 121 else 0.6   # emphasise outer rows 13-16
        ax.plot(ax_, ay_, color="black", lw=lw, alpha=0.5)
        if R >= 121:  # label rows 13-16
            mid_az = math.radians(AX_AZ)
            lx = CX + (R + 3) * math.sin(mid_az)
            ly = CY + (R + 3) * math.cos(mid_az)
            ax.text(lx, ly, f"R{ri+1}", fontsize=7, ha="center",
                    color="black", fontweight="bold")

    # Arc centre
    ax.plot(CX, CY, "b*", ms=10, zorder=8)

    if ax_i == 0:
        ax.set_title("Confidence mask + row arcs", fontsize=10)
    else:
        ax.set_title("Confidence mask + harness decisions from unsupported terrain", fontsize=10)
        # Overlay V0005 wall-trigger cells (hatched red)
        wm = np.ma.masked_where(~w5p, np.ones_like(w5p, dtype=float))
        ax.imshow(wm, extent=extent, origin="upper",
                  cmap=ListedColormap(["#ff0000"]), alpha=0.6,
                  interpolation="nearest", zorder=5)

        # Overlay V0008 grade_ceiling cells (semi-transparent blue)
        gm = np.ma.masked_where(~gc_p, np.ones_like(gc_p, dtype=float))
        ax.imshow(gm, extent=extent, origin="upper",
                  cmap=ListedColormap(["#3182bd"]), alpha=0.4,
                  interpolation="nearest", zorder=4)

        # Legend patches
        p_wall = mpatches.Patch(color="#ff0000", alpha=0.6,
                                label="V0005 wall-trigger cells (delta<−3 ft)")
        p_gc   = mpatches.Patch(color="#3182bd", alpha=0.5,
                                label="V0008 grade_ceiling cut cells")
        ax.legend(handles=[p_wall, p_gc], fontsize=8, loc="upper left")

    ax.set_xlabel("Easting (ft, EPSG:6494)", fontsize=8)
    ax.set_ylabel("Northing (ft)", fontsize=8)
    ax.tick_params(labelsize=7)

# Shared colour-bar for confidence
cbar_ax = fig.add_axes([0.45, 0.08, 0.01, 0.75])
sm = plt.cm.ScalarMappable(cmap=cmap_conf, norm=norm_conf)
sm.set_array([])
cb = fig.colorbar(sm, cax=cbar_ax, ticks=[0, 1, 2])
cb.ax.set_yticklabels(["Zero-return\n(interpolated)", "Returns /\nno ground", "Ground-\nsupported"], fontsize=7)

plt.tight_layout(rect=[0, 0.08, 1, 0.95])
plt.savefig(OUT_PNG, dpi=160, bbox_inches="tight")
plt.close()
print(f"Map → {OUT_PNG.relative_to(ROOT)}")
print("Done.")
