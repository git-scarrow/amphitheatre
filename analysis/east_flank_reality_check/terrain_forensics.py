"""
Terrain forensics — east flank reality check.
Petoskey Pit, Petoskey MI.  EPSG:6494 NAVD88 intl ft.

Runs all slope-artifact tests defined in slope_artifact_tests.md and
produces figures in figures/ and tables in outputs/.

Usage:
    cd /home/sam/projects/amphitheatre
    source .venv/bin/activate
    python analysis/east_flank_reality_check/terrain_forensics.py
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.ticker import MultipleLocator
import rasterio
from rasterio.transform import rowcol
from scipy.ndimage import gaussian_filter, label as ndlabel
from scipy.interpolate import RegularGridInterpolator
import csv
import os
import warnings
warnings.filterwarnings("ignore")

# ── paths ──────────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
DEM_PATH = os.path.join(HERE, "../../dem/dem_design_1ft.tif")
FIG_DIR  = os.path.join(HERE, "figures")
OUT_DIR  = os.path.join(HERE, "outputs")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

# ── load DEM ───────────────────────────────────────────────────────────────
with rasterio.open(DEM_PATH) as src:
    dem = src.read(1).astype(float)
    dem[dem == src.nodata] = np.nan
    transform = src.transform
    crs = src.crs
    nrows, ncols = dem.shape

cell_x = transform.a   # ft / pixel (positive)
cell_y = -transform.e  # ft / pixel (positive)
cell = (cell_x + cell_y) / 2.0  # ≈1 ft

def world_to_idx(x, y):
    """World coords → (row, col) float indices."""
    r = (y - transform.f) / transform.e
    c = (x - transform.c) / transform.a
    return r, c

def idx_to_world(r, c):
    x = transform.c + c * transform.a
    y = transform.f + r * transform.e
    return x, y

def sample_elev(r, c):
    """Bilinear sample; returns nan outside bounds."""
    r0, c0 = int(np.floor(r)), int(np.floor(c))
    if r0 < 0 or c0 < 0 or r0 >= nrows-1 or c0 >= ncols-1:
        return np.nan
    dr, dc = r - r0, c - c0
    return (dem[r0,c0]*(1-dr)*(1-dc) + dem[r0+1,c0]*dr*(1-dc) +
            dem[r0,c0+1]*(1-dr)*dc + dem[r0+1,c0+1]*dr*dc)

# ── stage / bowl focus ─────────────────────────────────────────────────────
# From design_open_low.py: seating arc center CX,CY=19533067.7,750799.2;
# arc axis AX_AZ=150°; F_T=15 ft along axis → FX=CX+sin(150)*15, FY=CY+cos(150)*15
# FX = 19533067.7 + 0.5*15 = 19533075.2
# FY = 750799.2  + (-0.866)*15 = 750786.2
# This is the correct center for all seating arc radii (R=85–130 ft).
CX = 19533075.2   # EPSG:6494 easting (ft) — seating arc center
CY = 750786.2     # EPSG:6494 northing (ft)

# ── multi-axis profiles ────────────────────────────────────────────────────
def transect(cx, cy, azimuth_deg, r_start=0, r_end=200, step=1.0):
    """Sample DEM along a radial from (cx,cy) in the given azimuth.
    Returns arrays: station_ft, elev_ft."""
    az_rad = np.radians(azimuth_deg)
    dx = np.sin(az_rad)
    dy = np.cos(az_rad)
    stations = np.arange(r_start, r_end + step, step)
    elevs = []
    for s in stations:
        wx = cx + s * dx
        wy = cy + s * dy
        ri, ci = world_to_idx(wx, wy)
        elevs.append(sample_elev(ri, ci))
    return stations, np.array(elevs)

print("Computing transect profiles…")
profiles = {
    "S  (az 180)": transect(CX, CY, 180),
    "SE (az 135)": transect(CX, CY, 135),
    "E  (az  90)": transect(CX, CY,  90),
}
# Parallel offsets every 10 ft along the east profile
for offset_ft in [-20, -10, 10, 20]:
    label = f"E+{offset_ft:+d}ft offset"
    # offset is perpendicular to east (az 0 = north, so perp = az 0 or 180)
    cx_off = CX                    # keep easting
    cy_off = CY + offset_ft        # shift northing
    profiles[label] = transect(cx_off, cy_off, 90)

# ── slope from elevation profile ──────────────────────────────────────────
def profile_slope_deg(stations, elevs):
    """Local slope in degrees between adjacent 1-ft stations."""
    ds = np.diff(stations)
    dz = np.diff(elevs)
    with np.errstate(invalid="ignore"):
        slope_deg = np.degrees(np.arctan(np.abs(dz) / ds))
    # pad so len == len(stations)
    return np.concatenate([[slope_deg[0]], slope_deg])

# ── multi-scale slope rasters ─────────────────────────────────────────────
print("Computing multi-scale slope rasters…")

def slope_from_dem(d, cell_size=1.0):
    """Slope in degrees from a DEM array using central difference."""
    dz_dy, dz_dx = np.gradient(d, cell_size)
    return np.degrees(np.arctan(np.sqrt(dz_dx**2 + dz_dy**2)))

slope_1ft  = slope_from_dem(dem, cell)
slope_3ft  = slope_from_dem(gaussian_filter(dem, sigma=1.5), cell)
slope_5ft  = slope_from_dem(gaussian_filter(dem, sigma=2.5), cell)
slope_10ft = slope_from_dem(gaussian_filter(dem, sigma=5.0), cell)

# ── extract zone statistics ─────────────────────────────────────────────
def zone_mask(cx, cy, az_lo, az_hi, r_lo, r_hi):
    """Boolean mask for cells within an azimuth/radius band."""
    rows, cols = np.mgrid[0:nrows, 0:ncols]
    wx, wy = idx_to_world(rows, cols)
    dx = wx - cx; dy = wy - cy
    dist = np.sqrt(dx**2 + dy**2)
    az = np.degrees(np.arctan2(dx, dy)) % 360  # CW from north
    return (dist >= r_lo) & (dist <= r_hi) & (az >= az_lo) & (az <= az_hi)

zones = {
    "S_wall":    (165, 195, 85, 150),
    "SE_corner": (120, 165, 85, 150),
    "E_flank":   ( 75, 120, 85, 150),
    "upper_E_rim":(75, 120, 130, 170),
    "upper_S_rim":(150, 195, 130, 170),
}

scale_names = ["1ft_raw", "3ft_smooth", "5ft_smooth", "10ft_smooth"]
slope_maps  = [slope_1ft, slope_3ft, slope_5ft, slope_10ft]

print("Computing zone statistics…")
stats_rows = []
for zname, (az_lo, az_hi, r_lo, r_hi) in zones.items():
    mask = zone_mask(CX, CY, az_lo, az_hi, r_lo, r_hi)
    for sname, smap in zip(scale_names, slope_maps):
        vals = smap[mask & ~np.isnan(dem)]
        if len(vals) == 0:
            continue
        gt25 = np.sum(vals > 25) * (cell**2)  # sq ft
        gt30 = np.sum(vals > 30) * (cell**2)
        stats_rows.append({
            "zone": zname, "scale": sname,
            "n_cells": len(vals),
            "median_deg": round(float(np.median(vals)), 2),
            "mean_deg":   round(float(np.mean(vals)), 2),
            "p90_deg":    round(float(np.percentile(vals, 90)), 2),
            "p95_deg":    round(float(np.percentile(vals, 95)), 2),
            "max_deg":    round(float(np.max(vals)), 2),
            "area_gt25_sqft": round(gt25, 1),
            "area_gt30_sqft": round(gt30, 1),
        })

with open(os.path.join(OUT_DIR, "slope_stats_by_zone.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=stats_rows[0].keys())
    w.writeheader(); w.writerows(stats_rows)
print(f"  → outputs/slope_stats_by_zone.csv ({len(stats_rows)} rows)")

# ── connected-component analysis ──────────────────────────────────────────
print("Running connected-component analysis…")
cc_rows = []
for thresh_deg in [25, 30]:
    for sname, smap in zip(scale_names, slope_maps):
        binary = (smap > thresh_deg) & ~np.isnan(dem)
        labeled, n = ndlabel(binary)
        for comp_id in range(1, n+1):
            comp_mask = labeled == comp_id
            area_sqft = np.sum(comp_mask) * (cell**2)
            if area_sqft < 4:
                continue  # ignore 1-2 pixel specks
            rows_idx, cols_idx = np.where(comp_mask)
            cen_r, cen_c = np.mean(rows_idx), np.mean(cols_idx)
            cen_x, cen_y = idx_to_world(cen_r, cen_c)
            dx, dy = cen_x - CX, cen_y - CY
            dist = np.sqrt(dx**2 + dy**2)
            az = np.degrees(np.arctan2(dx, dy)) % 360
            # bounding box in cells
            h = rows_idx.max() - rows_idx.min() + 1
            w = cols_idx.max() - cols_idx.min() + 1
            aspect = max(h, w) / max(1, min(h, w))
            cc_rows.append({
                "threshold_deg": thresh_deg,
                "scale": sname,
                "comp_id": comp_id,
                "area_sqft": round(area_sqft, 1),
                "aspect_ratio": round(aspect, 2),
                "centroid_dist_ft": round(float(dist), 1),
                "centroid_az_deg": round(float(az), 1),
                "bbox_h": h, "bbox_w": w,
            })

cc_rows.sort(key=lambda r: -r["area_sqft"])
with open(os.path.join(OUT_DIR, "connected_components.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cc_rows[0].keys() if cc_rows else [])
    if cc_rows:
        w.writeheader(); w.writerows(cc_rows)
print(f"  → outputs/connected_components.csv ({len(cc_rows)} rows)")

# ── profile table ──────────────────────────────────────────────────────────
print("Writing profile table…")
profile_rows = []
for pname, (stations, elevs) in profiles.items():
    slopes = profile_slope_deg(stations, elevs)
    for s, e, sl in zip(stations, elevs, slopes):
        profile_rows.append({
            "profile": pname,
            "station_ft": round(float(s), 1),
            "elev_ft": round(float(e), 3) if not np.isnan(e) else "",
            "slope_deg": round(float(sl), 2) if not np.isnan(sl) else "",
        })
with open(os.path.join(OUT_DIR, "profile_table.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["profile","station_ft","elev_ft","slope_deg"])
    w.writeheader(); w.writerows(profile_rows)
print(f"  → outputs/profile_table.csv")

# ═══════════════════════════════════════════════════════════════════════════
# FIGURES
# ═══════════════════════════════════════════════════════════════════════════

# ── Figure 1: S/SE/E profile comparison ────────────────────────────────────
print("Figure 1: S/SE/E profile comparison…")
fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=False)
ax_elev, ax_slope = axes

main_profiles = ["S  (az 180)", "SE (az 135)", "E  (az  90)"]
colors = ["#c0392b", "#e67e22", "#2980b9"]
for pname, col in zip(main_profiles, colors):
    stations, elevs = profiles[pname]
    slopes = profile_slope_deg(stations, elevs)
    ax_elev.plot(stations, elevs, color=col, lw=1.5, label=pname.strip())
    ax_slope.plot(stations, slopes, color=col, lw=1.2, alpha=0.85, label=pname.strip())

ax_elev.axvspan(85, 130, alpha=0.08, color="green", label="Seating band R85–130")
ax_slope.axvspan(85, 130, alpha=0.08, color="green")
ax_slope.axhline(18, ls="--", color="gray", lw=0.8, label="18° (S/SE bowl-wall reference)")
ax_slope.axhline(25, ls=":", color="orange", lw=1.0, label="25° threshold")
ax_slope.axhline(30, ls=":", color="red",    lw=1.0, label="30° threshold")

ax_elev.set_ylabel("Elevation (NAVD88 intl ft)")
ax_elev.set_title("Petoskey Pit — S / SE / E transect elevation profiles")
ax_elev.legend(fontsize=8); ax_elev.grid(alpha=0.3)
ax_slope.set_xlabel("Station from bowl center (ft)")
ax_slope.set_ylabel("Local slope (°)")
ax_slope.set_title("Profile local slope — 1-ft DEM (artifact-prone; compare to smoothed)")
ax_slope.legend(fontsize=8); ax_slope.grid(alpha=0.3)
ax_slope.set_ylim(0, 55)

plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "s_se_e_profile_comparison.png"), dpi=150)
plt.close()

# ── Figure 2: Multi-scale slope comparison on east profile ─────────────────
print("Figure 2: East multi-scale slope…")
stations, elevs = profiles["E  (az  90)"]
fig, ax = plt.subplots(figsize=(12, 5))
scale_cols = ["#e74c3c", "#e67e22", "#2ecc71", "#2980b9"]
scale_sigmas = [0, 1.5, 2.5, 5.0]
scale_labels = ["1-ft raw", "3-ft (σ=1.5)", "5-ft (σ=2.5)", "10-ft (σ=5.0)"]

for sigma, scol, slabel in zip(scale_sigmas, scale_cols, scale_labels):
    if sigma == 0:
        sm_dem = dem
    else:
        sm_dem = gaussian_filter(dem, sigma=sigma)
    # sample along east transect
    az_rad = np.radians(90)
    slopes_sm = []
    for s in stations:
        wx = CX + s * np.sin(az_rad)
        wy = CY + s * np.cos(az_rad)
        ri, ci = world_to_idx(wx, wy)
        # finite difference using adjacent cells
        ri0, ci0 = int(ri), int(ci)
        if ri0 < 1 or ci0 < 1 or ri0 >= nrows-1 or ci0 >= ncols-1:
            slopes_sm.append(np.nan)
            continue
        dzdx = (sm_dem[ri0, ci0+1] - sm_dem[ri0, ci0-1]) / (2*cell)
        dzdy = (sm_dem[ri0-1, ci0] - sm_dem[ri0+1, ci0]) / (2*cell)
        slopes_sm.append(np.degrees(np.arctan(np.sqrt(dzdx**2 + dzdy**2))))
    ax.plot(stations, slopes_sm, color=scol, lw=1.5, alpha=0.85, label=slabel)

ax.axvspan(85, 130, alpha=0.08, color="green", label="Seating band R85–130")
ax.axhline(18, ls="--", color="gray",   lw=0.8, label="18° bowl-wall reference")
ax.axhline(25, ls=":",  color="orange", lw=1.0, label="25° threshold")
ax.axhline(30, ls=":",  color="red",    lw=1.0, label="30° threshold (artifact candidate)")
ax.set_xlabel("Station from bowl center (ft)")
ax.set_ylabel("Slope (°)")
ax.set_title("East transect (az 90°) — slope at 4 smoothing scales\n"
             "If >30° signal disappears at 3–5 ft smoothing → NOT a real escarpment")
ax.legend(fontsize=8); ax.grid(alpha=0.3); ax.set_ylim(0, 50)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "multiscale_slope_east.png"), dpi=150)
plt.close()

# ── Figure 3: Connected components map (30° threshold, 1-ft raw) ───────────
print("Figure 3: Connected components map…")
# crop to a local window around the bowl
ri_c, ci_c = world_to_idx(CX, CY)
pad = 180  # ft
ri0 = max(0, int(ri_c) - pad)
ri1 = min(nrows, int(ri_c) + pad)
ci0 = max(0, int(ci_c) - pad)
ci1 = min(ncols, int(ci_c) + pad)
dem_crop   = dem[ri0:ri1, ci0:ci1]
slp_crop   = slope_1ft[ri0:ri1, ci0:ci1]
slp3_crop  = slope_3ft[ri0:ri1, ci0:ci1]

fig, axes = plt.subplots(1, 2, figsize=(14, 7))
for ax, smap, title_suffix in zip(axes,
                                  [slp_crop, slp3_crop],
                                  ["1-ft raw", "3-ft smoothed"]):
    gt30 = (smap > 30) & ~np.isnan(dem_crop)
    gt25 = (smap > 25) & (smap <= 30) & ~np.isnan(dem_crop)
    extent = [ci0*cell, ci1*cell, -ri1*cell, -ri0*cell]
    ax.imshow(dem_crop, cmap="terrain", aspect="equal",
              vmin=np.nanpercentile(dem_crop, 5), vmax=np.nanpercentile(dem_crop, 99),
              extent=[ci0, ci1, ri1, ri0])
    # overlay slope zones
    ax.imshow(np.where(gt25, 1, np.nan), cmap="Oranges", alpha=0.5, aspect="equal",
              vmin=0, vmax=2, extent=[ci0, ci1, ri1, ri0])
    ax.imshow(np.where(gt30, 1, np.nan), cmap="Reds", alpha=0.7, aspect="equal",
              vmin=0, vmax=2, extent=[ci0, ci1, ri1, ri0])
    # mark bowl center
    ax.plot(ci_c, ri_c, "b+", ms=12, mew=2, label="Bowl center")
    ax.set_title(f">25° (orange) and >30° (red) cells — {title_suffix}", fontsize=9)
    ax.set_xlabel("Column index"); ax.set_ylabel("Row index")
    ax.legend(fontsize=7)

plt.suptitle("Petoskey Pit — slope threshold map: does >30° persist after smoothing?",
             fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "connected_components_map.png"), dpi=150)
plt.close()

# ── Figure 4: Parallel east-offset profiles ───────────────────────────────
print("Figure 4: Parallel offset profiles…")
fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
ax_e, ax_s = axes
offset_keys = [k for k in profiles if "offset" in k or k == "E  (az  90)"]
cmap = plt.get_cmap("cool", len(offset_keys))
for i, pk in enumerate(sorted(offset_keys)):
    st, el = profiles[pk]
    sl = profile_slope_deg(st, el)
    c = cmap(i)
    ax_e.plot(st, el, color=c, lw=1.2, label=pk.strip(), alpha=0.8)
    ax_s.plot(st, sl, color=c, lw=1.2, alpha=0.8)

ax_e.axvspan(85, 130, alpha=0.07, color="green")
ax_s.axvspan(85, 130, alpha=0.07, color="green")
ax_s.axhline(25, ls=":", color="orange", lw=0.9)
ax_s.axhline(30, ls=":", color="red",    lw=0.9)
ax_e.set_ylabel("Elevation (ft)"); ax_e.legend(fontsize=7, ncol=2); ax_e.grid(alpha=0.3)
ax_s.set_ylabel("Slope (°)");      ax_s.grid(alpha=0.3); ax_s.set_ylim(0, 50)
ax_s.set_xlabel("Station (ft)")
ax_e.set_title("East transect + parallel offsets: elevation")
ax_s.set_title("East transect + parallel offsets: slope (1-ft raw)")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "east_parallel_profiles.png"), dpi=150)
plt.close()

# ── Figure 5: Site orientation diagram ────────────────────────────────────
print("Figure 5: Site orientation diagram…")
fig, ax = plt.subplots(figsize=(8, 8))
ax.imshow(dem_crop, cmap="terrain", aspect="equal",
          vmin=np.nanpercentile(dem_crop, 5), vmax=np.nanpercentile(dem_crop, 99),
          extent=[ci0, ci1, ri1, ri0], alpha=0.7)

def draw_arrow(cx, cy, az_deg, length, label_txt, color):
    az_rad = np.radians(az_deg)
    # convert world to pixel
    ri_s, ci_s = world_to_idx(cx, cy)
    dci = length * np.sin(az_rad)
    dri = -length * np.cos(az_rad)  # row increases downward
    ax.annotate("", xy=(ci_s+dci, ri_s+dri), xytext=(ci_s, ri_s),
                arrowprops=dict(arrowstyle="->", color=color, lw=2.0))
    ax.text(ci_s + dci*1.15, ri_s + dri*1.15, label_txt,
            ha="center", va="center", fontsize=8, color=color,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7))

draw_arrow(CX, CY,   0, 90, "Lake St (N)", "#2980b9")
draw_arrow(CX, CY, 180, 90, "Mitchell St (S)", "#2980b9")
draw_arrow(CX, CY,  90, 90, "Petoskey St (E)", "#c0392b")
draw_arrow(CX, CY, 270, 90, "Bayfront Park (W)", "#27ae60")
draw_arrow(CX, CY, 330, 75, "Bay view (NNW)", "#8e44ad")

ax.plot(ci_c, ri_c, "k*", ms=14, label="Bowl center")
ax.set_title("Petoskey Pit — corrected site orientation\n"
             "East = Petoskey Street; North = Lake St; South = Mitchell St; West = Bayfront Park",
             fontsize=9)
ax.set_xlabel("Column index (≈ft east)"); ax.set_ylabel("Row index (≈ft south)")
ax.legend(fontsize=7)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "site_orientation_diagram.png"), dpi=150)
plt.close()

# ── Figure 6: Zone slope statistics summary bar chart ─────────────────────
print("Figure 6: Zone statistics summary…")
import io, sys

# Load stats CSV back
rows_loaded = []
with open(os.path.join(OUT_DIR, "slope_stats_by_zone.csv")) as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows_loaded.append(row)

zones_list = list(zones.keys())
scale_list_short = ["1ft", "3ft", "5ft", "10ft"]
scale_full = ["1ft_raw", "3ft_smooth", "5ft_smooth", "10ft_smooth"]

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
ax_p90, ax_gt30 = axes

x = np.arange(len(zones_list))
width = 0.2
bar_cols = ["#e74c3c", "#e67e22", "#2ecc71", "#2980b9"]

for i, (sf, sl, bc) in enumerate(zip(scale_full, scale_list_short, bar_cols)):
    p90_vals = []
    gt30_vals = []
    for zn in zones_list:
        matching = [r for r in rows_loaded if r["zone"]==zn and r["scale"]==sf]
        if matching:
            p90_vals.append(float(matching[0]["p90_deg"]))
            gt30_vals.append(float(matching[0]["area_gt30_sqft"]))
        else:
            p90_vals.append(0); gt30_vals.append(0)
    ax_p90.bar(x + i*width, p90_vals, width, label=sl, color=bc, alpha=0.8)
    ax_gt30.bar(x + i*width, gt30_vals, width, label=sl, color=bc, alpha=0.8)

ax_p90.axhline(25, ls=":", color="orange", lw=1.0, label="25° line")
ax_p90.axhline(30, ls=":", color="red",    lw=1.0, label="30° line")
ax_p90.set_xticks(x + width*1.5); ax_p90.set_xticklabels(zones_list, rotation=20, ha="right", fontsize=8)
ax_p90.set_ylabel("p90 slope (°)"); ax_p90.set_title("p90 slope by zone and scale"); ax_p90.legend(fontsize=8)

ax_gt30.set_xticks(x + width*1.5); ax_gt30.set_xticklabels(zones_list, rotation=20, ha="right", fontsize=8)
ax_gt30.set_ylabel("Area >30° (sq ft)"); ax_gt30.set_title("Area >30° by zone and scale"); ax_gt30.legend(fontsize=8)

plt.suptitle("Slope statistics by zone — key: does E_flank match S_wall/SE_corner, or is it different?",
             fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "zone_slope_statistics.png"), dpi=150)
plt.close()

# ── Summary printout ────────────────────────────────────────────────────────
print("\n" + "="*70)
print("TERRAIN FORENSICS SUMMARY — Petoskey Pit East Flank")
print("="*70)

# Compare E_flank vs S_wall at 1-ft raw
def get_stat(zone, scale, stat):
    for r in rows_loaded:
        if r["zone"] == zone and r["scale"] == scale:
            return float(r[stat])
    return float("nan")

print("\nZone comparison — 1-ft raw slope (artifact-prone):")
print(f"{'Zone':<15} {'median':>7} {'p90':>7} {'p95':>7} {'max':>7} {'>30 sqft':>10}")
for z in zones_list:
    print(f"{z:<15} {get_stat(z,'1ft_raw','median_deg'):>7.1f} "
          f"{get_stat(z,'1ft_raw','p90_deg'):>7.1f} "
          f"{get_stat(z,'1ft_raw','p95_deg'):>7.1f} "
          f"{get_stat(z,'1ft_raw','max_deg'):>7.1f} "
          f"{get_stat(z,'1ft_raw','area_gt30_sqft'):>10.0f}")

print("\nZone comparison — 3-ft smoothed (more reliable):")
print(f"{'Zone':<15} {'median':>7} {'p90':>7} {'p95':>7} {'max':>7} {'>30 sqft':>10}")
for z in zones_list:
    print(f"{z:<15} {get_stat(z,'3ft_smooth','median_deg'):>7.1f} "
          f"{get_stat(z,'3ft_smooth','p90_deg'):>7.1f} "
          f"{get_stat(z,'3ft_smooth','p95_deg'):>7.1f} "
          f"{get_stat(z,'3ft_smooth','max_deg'):>7.1f} "
          f"{get_stat(z,'3ft_smooth','area_gt30_sqft'):>10.0f}")

print("\n10-ft smoothed (most reliable for design-intent slope):")
print(f"{'Zone':<15} {'median':>7} {'p90':>7} {'p95':>7} {'max':>7} {'>30 sqft':>10}")
for z in zones_list:
    print(f"{z:<15} {get_stat(z,'10ft_smooth','median_deg'):>7.1f} "
          f"{get_stat(z,'10ft_smooth','p90_deg'):>7.1f} "
          f"{get_stat(z,'10ft_smooth','p95_deg'):>7.1f} "
          f"{get_stat(z,'10ft_smooth','max_deg'):>7.1f} "
          f"{get_stat(z,'10ft_smooth','area_gt30_sqft'):>10.0f}")

# Key question
e_p90_1ft   = get_stat("E_flank",   "1ft_raw",    "p90_deg")
e_p90_3ft   = get_stat("E_flank",   "3ft_smooth", "p90_deg")
e_p90_10ft  = get_stat("E_flank",   "10ft_smooth","p90_deg")
e_gt30_1ft  = get_stat("E_flank",   "1ft_raw",    "area_gt30_sqft")
e_gt30_3ft  = get_stat("E_flank",   "3ft_smooth", "area_gt30_sqft")
s_p90_1ft   = get_stat("S_wall",    "1ft_raw",    "p90_deg")
s_p90_10ft  = get_stat("S_wall",    "10ft_smooth","p90_deg")

print("\n" + "-"*70)
print("VERDICT:")
print(f"  E_flank p90:  1-ft {e_p90_1ft:.1f}°  |  3-ft {e_p90_3ft:.1f}°  |  10-ft {e_p90_10ft:.1f}°")
print(f"  S_wall  p90:  1-ft {s_p90_1ft:.1f}°  |  10-ft {s_p90_10ft:.1f}°")
print(f"  E_flank area>30°: 1-ft {e_gt30_1ft:.0f} sqft  |  3-ft {e_gt30_3ft:.0f} sqft")

if e_p90_10ft > 22:
    print("\n  E flank p90 at 10-ft scale exceeds 22° → E flank is bowl-wall grade.")
    print("  The 'gentle east' framing is INCORRECT. E matches S/SE character.")
elif e_p90_10ft < 15:
    print("\n  E flank p90 at 10-ft scale < 15° → E flank IS gentler than S/SE wall.")
    print("  'Gentle east' may be accurate — but still doesn't mean no seating potential.")
else:
    print("\n  E flank p90 at 10-ft scale in intermediate range. Character uncertain.")
    print("  Field survey needed before design commitment.")

if e_gt30_3ft < 100:
    print(f"\n  Area >30° at 3-ft smooth = {e_gt30_3ft:.0f} sqft — likely artifact.")
    print("  No escarpment at design-relevant scale confirmed by 3-ft smoothing.")
else:
    print(f"\n  Area >30° at 3-ft smooth = {e_gt30_3ft:.0f} sqft — may be a real feature.")
    print("  Multi-scale analysis and field survey still needed to confirm.")

print("\nFigures written to:", FIG_DIR)
print("Tables written to:", OUT_DIR)
print("Done.")
