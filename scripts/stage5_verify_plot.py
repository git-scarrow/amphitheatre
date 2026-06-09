#!/usr/bin/env python3
"""Stage 5 verification + cut/fill plot + SE steep-wall geotech check."""
import json
from pathlib import Path
import numpy as np, rasterio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

ROOT = str(Path(__file__).parent.parent)
gp = rasterio.open(f"{ROOT}/stage5/grade_proposed.tif").read(1)
cf = rasterio.open(f"{ROOT}/stage5/cut_fill_map.tif").read(1)
exr = rasterio.open(f"{ROOT}/dem/dem_design_1ft.tif")
ex = exr.read(1); ex = np.where(ex == exr.nodata, np.nan, ex)   # mask nodata
gp = np.where(gp == -9999, np.nan, gp); cf = np.where(cf == -9999, np.nan, cf)

# --- sanity ---
print("VERIFY")
print("  proposed z min/max:", round(np.nanmin(gp), 2), round(np.nanmax(gp), 2))
print("  cut/fill min/max ft:", round(np.nanmin(cf), 2), round(np.nanmax(cf), 2))
print("  real holes (proposed NaN where existing valid):",
      int((np.isnan(gp) & np.isfinite(ex)).sum()))

# --- slope of proposed surface (only where 3x3 neighborhood is fully valid) ---
gy, gx = np.gradient(np.where(np.isfinite(gp), gp, np.nan), 1.0)
slope = np.hypot(gx, gy) * 100.0
slope[~np.isfinite(ex)] = np.nan      # drop nodata-edge artifacts
print("  proposed slope p50/p95/p99 %:",
      *[round(float(np.nanpercentile(slope, q)), 1) for q in (50, 95, 99)])

# --- retaining / deep-cut accounting (geotech flag) ---
dcut6 = (cf < -6) & np.isfinite(cf)
print("  cut >6 ft: %d px = %.3f ac; >10 ft: %d px; deepest %.1f ft"
      % (dcut6.sum(), dcut6.sum()/43560.0, int(((cf<-10)&np.isfinite(cf)).sum()),
         float(np.nanmin(cf))))

# --- SE steep-wall geotech check: behind upper seating (az ~150 from focus) ---
import pickle
ctx = pickle.load(open(f"{ROOT}/stage4/_ctx.pkl", "rb"))
F = ctx["F"]; ds = rasterio.open(f"{ROOT}/dem/dem_design_1ft.tif")
xs = ds.transform.c + (np.arange(ds.width)+0.5)*ds.transform.a
ys = ds.transform.f + (np.arange(ds.height)+0.5)*ds.transform.e
XX, YY = np.meshgrid(xs, ys)
RAD = np.hypot(XX-F[0], YY-F[1]); AZ = (np.degrees(np.arctan2(XX-F[0], YY-F[1]))) % 360
se = (np.abs(((AZ-150+180) % 360)-180) <= 30) & (RAD >= 160) & (RAD <= 230)
print("  SE upper-wall existing slope p50/p90/max %:",
      *[round(float(np.nanpercentile(slope[se & np.isfinite(slope)], q)), 1)
        for q in (50, 90, 100)])
se_prop_max = float(np.nanpercentile(slope[se & np.isfinite(slope)], 98))
print("  SE proposed slope p98 %:", round(se_prop_max, 1),
      "(3:1=33%, 2:1=50%)")

# --- plot: cut/fill map ---
fig, ax = plt.subplots(1, 2, figsize=(15, 7.2))
hs = ax[0]
hs.imshow(ex, cmap="gray", extent=[xs[0], xs[-1], ys[-1], ys[0]])
norm = TwoSlopeNorm(vmin=np.nanmin(cf), vcenter=0, vmax=np.nanmax(cf))
im = hs.imshow(np.where(np.abs(cf) > 0.05, cf, np.nan), cmap="RdBu",
               norm=norm, extent=[xs[0], xs[-1], ys[-1], ys[0]], alpha=0.85)
hs.plot(F[0], F[1], "k*", ms=14)
hs.set_title("Cut (red) / Fill (blue), ft  —  proposed minus existing")
hs.set_xlabel("Easting (US ft)"); hs.set_ylabel("Northing (US ft)")
fig.colorbar(im, ax=hs, shrink=0.7, label="Δz (ft): + fill / - cut")

ax[1].imshow(gp, cmap="terrain", extent=[xs[0], xs[-1], ys[-1], ys[0]])
ax[1].plot(F[0], F[1], "k*", ms=14)
ax[1].set_title("Proposed finished grade (NAVD88 ft)")
ax[1].set_xlabel("Easting (US ft)")
for a in ax:
    a.set_xlim(F[0]-260, F[0]+260); a.set_ylim(F[1]-260, F[1]+260)
fig.tight_layout()
fig.savefig(f"{ROOT}/stage5/cut_fill_map.png", dpi=130)
print("Wrote cut_fill_map.png")

json.dump(dict(prop_z=[round(float(np.nanmin(gp)),2), round(float(np.nanmax(gp)),2)],
               cf_ft=[round(float(np.nanmin(cf)),2), round(float(np.nanmax(cf)),2)],
               slope_pct={"p50":round(float(np.nanpercentile(slope,50)),1),
                          "p95":round(float(np.nanpercentile(slope,95)),1),
                          "max":round(float(np.nanmax(slope)),1)},
               se_wall_existing_pct={"p50":round(float(np.nanpercentile(slope[se&np.isfinite(slope)],50)),1),
                          "p90":round(float(np.nanpercentile(slope[se&np.isfinite(slope)],90)),1),
                          "max":round(float(np.nanmax(slope[se&np.isfinite(slope)])),1)}),
          open(f"{ROOT}/stage5/_verify.json","w"), indent=2)
