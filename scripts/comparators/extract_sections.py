#!/usr/bin/env python3
"""Extract true-scale centerline sections + radial fan scans from each
comparator DEM clip.

Per site:
  * centerline profile through the stage-front center along the bowl axis
    (axis from site_config.json — derived from the OSM stage rectangle
    orientation + seating side; labeled inferred), sampled every 0.5 m,
    output CSV (meters AND feet columns, never mixed) + QA plot.
  * radial elevation scan around the arc center (2 deg steps) used to
    measure the seating fan angle from terrain rather than eyeball.

Outputs in data/comparators/<slug>/derived/.
Reproduce:  .venv/bin/python scripts/comparators/extract_sections.py
"""
import csv
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio

sys.path.insert(0, os.path.dirname(__file__))
from sites import SITES, US_FT_PER_M

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))


def bilinear(z, transform, x, y, nodata):
    col = (x - transform.c) / transform.a - 0.5
    row = (y - transform.f) / transform.e - 0.5
    c0, r0 = int(math.floor(col)), int(math.floor(row))
    if c0 < 0 or r0 < 0 or c0+1 >= z.shape[1] or r0+1 >= z.shape[0]:
        return np.nan
    q = z[r0:r0+2, c0:c0+2].astype(float)
    if nodata is not None and (q == nodata).any():
        return np.nan
    fc, fr = col - c0, row - r0
    return (q[0, 0]*(1-fc)*(1-fr) + q[0, 1]*fc*(1-fr)
            + q[1, 0]*(1-fc)*fr + q[1, 1]*fc*fr)


def sample_ray(z, transform, nodata, x0, y0, az_deg, s0, s1, step=0.5):
    az = math.radians(az_deg)
    dx, dy = math.sin(az), math.cos(az)
    ss = np.arange(s0, s1 + 1e-9, step)
    zz = np.array([bilinear(z, transform, x0 + s*dx, y0 + s*dy, nodata)
                   for s in ss])
    return ss, zz


def process(slug):
    site = SITES[slug]
    sd = os.path.join(ROOT, "data", "comparators", slug)
    dd = os.path.join(sd, "derived")
    os.makedirs(dd, exist_ok=True)
    with open(os.path.join(sd, "site_config.json")) as f:
        cfg = json.load(f)
    with rasterio.open(os.path.join(sd, "dem", "dem_clip_1m.tif")) as src:
        z = src.read(1)
        tf = src.transform
        nod = src.nodata

    ax_az = cfg["audience_facing_azimuth_deg"]          # audience -> stage
    ux, uy = cfg["arc_center_xy"]                       # stage-front center
    away = (ax_az + 180.0) % 360.0                      # stage -> audience

    # centerline: negative s = behind stage front (stage side), positive =
    # into the audience
    ss, zz = sample_ray(z, tf, nod, ux, uy, away,
                        -cfg["profile_back_m"], cfg["profile_out_m"])
    with open(os.path.join(dd, "centerline_section.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["s_m", "s_ft", "z_m_navd88", "z_ft_navd88"])
        for s, zv in zip(ss, zz):
            w.writerow([f"{s:.2f}", f"{s*US_FT_PER_M:.2f}",
                        f"{zv:.3f}" if np.isfinite(zv) else "",
                        f"{zv*US_FT_PER_M:.3f}" if np.isfinite(zv) else ""])

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(ss*US_FT_PER_M, zz*US_FT_PER_M, lw=1.2, color="k")
    ax.axvline(0, color="red", lw=0.8, ls="--", label="arc center (stage front)")
    ax.set_xlabel("distance along axis from stage front (ft; + = into audience)")
    ax.set_ylabel("elev NAVD88 (ft)")
    ax.set_title(f"{site['name']} — centerline section "
                 f"az {away:.1f}° (true scale source data)")
    ax.grid(alpha=0.3); ax.legend()
    ax.set_aspect(5)
    fig.savefig(os.path.join(dd, "centerline_section_qa.png"),
                dpi=130, bbox_inches="tight")
    plt.close(fig)

    # radial fan scan: rise across the seating annulus per azimuth
    r0, r1 = cfg["fan_scan_r_m"]
    rows = []
    for theta in np.arange(0, 360, 2.0):
        rs, rz = sample_ray(z, tf, nod, ux, uy, theta, r0, r1)
        good = np.isfinite(rz)
        if good.sum() < 5:
            rows.append((theta, np.nan, np.nan))
            continue
        rise = np.nanmax(rz[good]) - np.nanmin(rz[good])
        # monotonicity score: fraction of steps rising away from center
        d = np.diff(rz[good])
        mono = (d > -0.05).mean()
        rows.append((theta, rise, mono))
    with open(os.path.join(dd, "fan_scan.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["azimuth_deg", "rise_m", "monotonic_frac"])
        for r in rows:
            w.writerow([f"{r[0]:.0f}",
                        f"{r[1]:.3f}" if np.isfinite(r[1]) else "",
                        f"{r[2]:.3f}" if np.isfinite(r[2]) else ""])

    th = np.array([r[0] for r in rows])
    ri = np.array([r[1] for r in rows])
    mo = np.array([r[2] for r in rows])
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(th, ri*US_FT_PER_M, label="rise across annulus (ft)")
    ax.plot(th, mo*10, label="monotonic frac x10", alpha=0.6)
    ax.axvline(away % 360, color="red", ls="--", lw=0.8, label="centerline az")
    ax.set_xlabel("azimuth from arc center (deg)")
    ax.set_title(f"{site['name']} — radial fan scan r=[{r0},{r1}] m")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.savefig(os.path.join(dd, "fan_scan_qa.png"), dpi=130,
                bbox_inches="tight")
    plt.close(fig)
    zmin = np.nanmin(zz); zmax = np.nanmax(zz)
    print(f"{slug}: section z [{zmin*US_FT_PER_M:.1f}, {zmax*US_FT_PER_M:.1f}] ft, "
          f"rise {(zmax-zmin)*US_FT_PER_M:.1f} ft over axis; outputs in {dd}")


def main():
    for slug in SITES:
        process(slug)


if __name__ == "__main__":
    main()
