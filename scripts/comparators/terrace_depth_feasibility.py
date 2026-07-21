#!/usr/bin/env python3
"""Screen: can the Petoskey landform support Charlevoix-depth seating terraces?

The controlling identity for a level terrace cut into a uniform slope is

    riser = natural_slope x tread_depth

so "deep terraces" and "gentle risers" are the same question asked twice, and
the answer is set by the EXISTING ground, not by preference. Charlevoix gets
~10.7 ft terraces at ~1.8-2.2 ft risers because its hillside is 17.1%. This
script measures Petoskey's natural slope radially across the seating fan and
reports, at each radius, the deepest tread that still yields a chosen riser.

Terrain basis: an INDEPENDENT reference clip of USGS 3DEP 1 m
MI_13County_2015_C16 — the same LiDAR project family the Petoskey canon is
built from, fetched fresh here so this screen does not depend on the
gitignored dem/dem_design_1ft.tif. It is REFERENCE ONLY: it is not design
canon and must not be substituted for the EPSG:6494 canon surface.

SCOPE LIMIT (DESIGN_CANON discipline): this is a landform screen. It emits NO
seating geometry, revalidates NO C-values, and must not appear in a cost
table. It answers only "where is the ground gentle enough", which is the
precondition for any deeper-terrace proposal.

Reproduce:  .venv/bin/python scripts/comparators/terrace_depth_feasibility.py
"""
import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyproj
import rasterio
from rasterio.transform import rowcol
from rasterio.windows import from_bounds

FT = 3.280839895013123
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
REF = os.path.join(ROOT, "data", "comparators", "_reference",
                   "petoskey_existing_3dep")
TILE = ("https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/"
        "MI_13County_2015_C16/TIFF/USGS_1M_16_x65y503_MI_13County_2015_C16.tif")
TARGET_RISER_FT = 2.0          # a comfortable, steppable terrace riser
CHARLEVOIX_TREAD_FT = 10.7     # measured: 64 ft seated run / 6 bands
CHARLEVOIX_RAKE_PCT = 17.1     # measured from 3DEP 1 m
PETOSKEY_RAKE_PCT = 31.8       # canon
PETOSKEY_SPACING_FT = 4.63     # canon: 69.5 ft run / 15 treads


def tread_vertices():
    g = json.load(open(os.path.join(ROOT, "vectors_geojson",
                                    "terrace_treads.geojson")))
    pts, rad = [], []
    for f in g["features"]:
        acc = []

        def rec(c):
            if isinstance(c, list) and c and isinstance(c[0], (int, float)):
                acc.append(c[:2])
            elif isinstance(c, list):
                for y in c:
                    rec(y)
        rec(f["geometry"]["coordinates"])
        for p in acc:
            pts.append(p)
            rad.append(f["properties"]["axis_radius_ft"])
    return np.array(pts, float), np.array(rad, float)


def fit_centre(pts, rad):
    """Least-squares bowl centre with per-row radii held at canon values."""
    c = pts.mean(axis=0)
    for _ in range(300):
        d = pts - c
        rr = np.hypot(d[:, 0], d[:, 1])
        step = np.linalg.lstsq(-d / rr[:, None], -(rr - rad), rcond=None)[0]
        c = c + step
        if np.linalg.norm(step) < 1e-9:
            break
    d = pts - c
    rr = np.hypot(d[:, 0], d[:, 1])
    az = np.degrees(np.arctan2(d[:, 0], d[:, 1])) % 360
    return c, float(np.sqrt(((rr - rad) ** 2).mean())), float(az.min()), float(az.max())


def ensure_reference_dem(lon, lat, half_m=250.0):
    os.makedirs(REF, exist_ok=True)
    out = os.path.join(REF, "dem_clip_1m.tif")
    if os.path.exists(out):
        return out
    t = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:26916", always_xy=True)
    ux, uy = t.transform(lon, lat)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open("/vsicurl/" + TILE) as src:
            b = (ux - half_m, uy - half_m, ux + half_m, uy + half_m)
            w = from_bounds(*b, transform=src.transform)
            w = w.round_offsets().round_lengths()
            data = src.read(1, window=w)
            prof = {"driver": "GTiff", "dtype": "float32", "count": 1,
                    "height": data.shape[0], "width": data.shape[1],
                    "crs": src.crs, "transform": src.window_transform(w),
                    "nodata": src.nodata, "compress": "deflate",
                    "predictor": 3, "tiled": True}
            crs, nod = str(src.crs), src.nodata
    with rasterio.open(out, "w", **prof) as d:
        d.write(data.astype("float32"), 1)
    v = data[data != nod] if nod is not None else data
    json.dump({
        "role": "REFERENCE ONLY — existing/natural terrain screen. NOT design "
                "canon; NOT a substitute for dem/dem_design_1ft.tif (EPSG:6494).",
        "source_url": TILE, "project": "MI_13County_2015_C16",
        "lidar_acquisition": "2015 (same project family as Petoskey canon)",
        "publication_date": "2022-11-13", "native_crs": crs,
        "native_resolution_m": [1.0, 1.0], "vertical": "NAVD88 meters",
        "center_lonlat_wgs84": [lon, lat], "clip_bounds_native": list(b),
        "fetched_on": "2026-07-21",
        "elev_min_m": float(v.min()), "elev_max_m": float(v.max()),
    }, open(os.path.join(REF, "provenance.json"), "w"), indent=1)
    return out


def main():
    pts, rad = tread_vertices()
    c6494, rmse, az_lo, az_hi = fit_centre(pts, rad)
    to84 = pyproj.Transformer.from_crs("EPSG:6494", "EPSG:4326", always_xy=True)
    lon, lat = to84.transform(*pts.mean(axis=0))
    dem = ensure_reference_dem(lon, lat)

    src = rasterio.open(dem)
    z = src.read(1).astype(float)
    if src.nodata is not None:
        z[z == src.nodata] = np.nan
    gy, gx = np.gradient(z, 1.0)
    slope = np.hypot(gx, gy) * 100.0
    to16 = pyproj.Transformer.from_crs("EPSG:6494", "EPSG:26916", always_xy=True)

    def at(x6, y6):
        x, y = to16.transform(x6, y6)
        r, cc = rowcol(src.transform, x, y)
        if 0 <= r < z.shape[0] and 0 <= cc < z.shape[1]:
            e, s = z[r, cc], slope[r, cc]
            return (float(e) * FT if np.isfinite(e) else None,
                    float(s) if np.isfinite(s) else None)
        return None, None

    rs = np.arange(25, 181, 2.5)
    E, S, S25, S75 = [], [], [], []
    for r in rs:
        zs, ss = [], []
        for a in np.linspace(az_lo, az_hi, 80):
            ar = math.radians(a)
            e, s = at(c6494[0] + r * math.sin(ar), c6494[1] + r * math.cos(ar))
            if e is not None:
                zs.append(e)
            if s is not None:
                ss.append(s)
        E.append(np.median(zs)); S.append(np.median(ss))
        S25.append(np.percentile(ss, 25)); S75.append(np.percentile(ss, 75))
    E, S = np.array(E), np.array(S)
    S25, S75 = np.array(S25), np.array(S75)
    max_tread = np.where(S > 1.0, TARGET_RISER_FT / (S / 100.0), np.nan)

    bands = [(25, 72, "#4DAF4A", "flat event floor  <2%"),
             (72, 95, "#0072B2", "FORECOURT BAND  5-31%"),
             (95, 157, "#D55E00", "CIVIC CORE  31-38%"),
             (157, 180, "#999999", "above seating")]

    fig, axes = plt.subplots(2, 1, figsize=(13, 10), sharex=True,
                             gridspec_kw={"height_ratios": [1, 1.25]})
    ax = axes[0]
    ax.plot(rs, E, color="#333", lw=2)
    ax.set_ylabel("existing ground elev (ft NAVD88)")
    ax.set_title("Petoskey Pit — EXISTING ground across the seating fan "
                 "(USGS 3DEP 1 m, MI_13County_2015 — reference, not canon)",
                 fontsize=12)
    for r0, r1, col, _ in bands:
        ax.axvspan(r0, r1, color=col, alpha=0.13)
    for rr, lab in ((85, "row 1\n(r=85)"), (156.8, "top of seating\n(r=157)")):
        ax.axvline(rr, color="k", ls=":", lw=1.2)
        ax.annotate(lab, (rr, E.min() + 2), fontsize=9, ha="center")
    ax.grid(alpha=.3)

    ax = axes[1]
    ax.fill_between(rs, S25, S75, color="#D55E00", alpha=.18,
                    label="natural slope p25-p75")
    ax.plot(rs, S, color="#D55E00", lw=2.4, label="natural slope, median (%)")
    ax.axhline(CHARLEVOIX_RAKE_PCT, color="#0072B2", ls="--", lw=1.8,
               label=f"Charlevoix measured rake {CHARLEVOIX_RAKE_PCT}%")
    ax.axhline(PETOSKEY_RAKE_PCT, color="k", ls="--", lw=1.4,
               label=f"Petoskey design rake {PETOSKEY_RAKE_PCT}% (canon)")
    ax.set_ylabel("natural slope (%)", color="#D55E00"); ax.set_ylim(0, 45)
    ax2 = ax.twinx()
    ax2.plot(rs, max_tread, color="#009E73", lw=2.4,
             label=f"max tread depth at a {TARGET_RISER_FT} ft riser (ft)")
    ax2.axhline(CHARLEVOIX_TREAD_FT, color="#0072B2", ls=":", lw=1.8)
    ax2.annotate(f"Charlevoix terrace depth {CHARLEVOIX_TREAD_FT} ft",
                 (150, CHARLEVOIX_TREAD_FT + .5), color="#0072B2",
                 fontsize=9, ha="right")
    ax2.axhline(PETOSKEY_SPACING_FT, color="k", ls=":", lw=1.4)
    ax2.annotate(f"Petoskey current spacing {PETOSKEY_SPACING_FT} ft",
                 (150, PETOSKEY_SPACING_FT - .65), fontsize=9, ha="right")
    ax2.set_ylabel(f"max tread depth @ {TARGET_RISER_FT} ft riser (ft)",
                   color="#009E73"); ax2.set_ylim(0, 18)
    for r0, r1, col, _ in bands:
        ax.axvspan(r0, r1, color=col, alpha=0.13)
    ax.set_xlabel(f"radius from bowl centre (ft)  —  seating fan "
                  f"az {az_lo:.0f}-{az_hi:.0f}")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=9, loc="upper left"); ax.grid(alpha=.3)
    fig.text(0.5, 0.003,
             "riser = natural slope x tread depth. Deep terraces need gentle "
             "ground: the civic core caps out near 5.3-6.5 ft of tread at a 2 ft "
             "riser, while the forecourt band (r 75-95) reaches 7-13 ft. "
             "Screen only — no geometry emitted, no C-values revalidated.",
             ha="center", fontsize=8.5, style="italic")
    plt.tight_layout()
    out = os.path.join(ROOT, "boards", "petoskey_terrace_depth_feasibility.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.savefig(out, dpi=140, bbox_inches="tight")

    def band_area(r0, r1):
        return (az_hi - az_lo) / 360.0 * math.pi * (r1 ** 2 - r0 ** 2)

    rep = {
        "_role": "landform screen only — emits no seating geometry, "
                 "revalidates no C-values, not costable",
        "terrain_basis": "USGS 3DEP 1 m MI_13County_2015_C16 (reference clip)",
        "bowl_centre_6494": [float(c6494[0]), float(c6494[1])],
        "centre_fit_rmse_ft": round(rmse, 2),
        "seating_fan_az": [round(az_lo), round(az_hi)],
        "identity": "riser_ft = natural_slope * tread_depth_ft",
        "target_riser_ft": TARGET_RISER_FT,
        "zones": {},
        "canon_crosscheck_ft": {},
    }
    for r0, r1, _, lab in bands:
        m = (rs >= r0) & (rs <= r1)
        rep["zones"][lab] = {
            "radius_ft": [r0, r1],
            "plan_area_sf": round(band_area(r0, r1)),
            "natural_slope_pct_median": round(float(np.median(S[m])), 1),
            "natural_slope_pct_range": [round(float(S[m].min()), 1),
                                        round(float(S[m].max()), 1)],
            "max_tread_ft_at_target_riser": [
                round(float(np.nanmin(max_tread[m])), 1),
                round(float(np.nanmax(max_tread[m])), 1)],
            "riser_ft_if_charlevoix_depth": [
                round(float(S[m].min() / 100 * CHARLEVOIX_TREAD_FT), 2),
                round(float(S[m].max() / 100 * CHARLEVOIX_TREAD_FT), 2)],
        }
    for r, lab, canon in ((85, "row1_tread_elev", 610.83),
                          (156.8, "top_of_seating_elev", 633.70)):
        i = int(np.argmin(abs(rs - r)))
        rep["canon_crosscheck_ft"][lab] = {
            "existing_reference": round(float(E[i]), 2), "canon": canon,
            "diff": round(float(E[i]) - canon, 2)}
    rp = os.path.join(ROOT, "analysis", "terrace_depth_feasibility.json")
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    json.dump(rep, open(rp, "w"), indent=1)
    print("wrote", out)
    print("wrote", rp)
    for lab, v in rep["zones"].items():
        print(f"  {lab:26} slope {v['natural_slope_pct_median']:5.1f}%  "
              f"max tread @{TARGET_RISER_FT}ft riser "
              f"{v['max_tread_ft_at_target_riser']}  "
              f"riser if 10.7ft deep {v['riser_ft_if_charlevoix_depth']}")


if __name__ == "__main__":
    main()
