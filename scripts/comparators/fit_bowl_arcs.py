#!/usr/bin/env python3
"""Fit circular arcs to DEM elevation contours inside each comparator's
seating wedge — same Kåsa circle-fit approach the Petoskey package uses for
its treads — so radii / arc lengths / fan angles are MEASURED from terrain,
not assumed from the stage-front anchor.

For each site: take contours at row-1+2ft, mid-bowl, and top-2ft elevations
(from the centerline profile breaks), keep vertices inside the digitized fan
sector (padded ±15°) and within a sane radius band, fit a circle to the
mid contour, then report:
  * fitted arc center (vs stage-front anchor)
  * radius at each of the three contours (distance from fitted center)
  * angular extent of the mid contour about the fitted center = measured fan

Output: data/comparators/<slug>/derived/arc_fit.json
Reproduce:  .venv/bin/python scripts/comparators/fit_bowl_arcs.py
"""
import json
import math
import os
import sys

import numpy as np
import rasterio

sys.path.insert(0, os.path.dirname(__file__))
from sites import SITES, US_FT_PER_M

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))


def contour_points(z, transform, level, nodata):
    """Marching-squares-free contour: cells whose 4-neighbour crossings
    bracket the level; returns cell-center coords (1 m accuracy is fine)."""
    zz = np.where(z == nodata, np.nan, z) if nodata is not None else z
    pts = []
    above = zz > level
    for axis in (0, 1):
        diff = above.astype(int)
        cross = np.diff(diff, axis=axis) != 0
        idx = np.argwhere(cross)
        for r, c in idx:
            rr, cc = (r + 0.5, c) if axis == 0 else (r, c + 0.5)
            x = transform.c + (cc + 0.5) * transform.a
            y = transform.f + (rr + 0.5) * transform.e
            pts.append((x, y))
    return np.array(pts) if pts else np.empty((0, 2))


def kasa_fit(xy):
    x, y = xy[:, 0], xy[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    b = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = float(sol[0]), float(sol[1])
    r = float(math.sqrt(max(sol[2] + cx ** 2 + cy ** 2, 0.0)))
    rmse = float(np.sqrt(np.mean((np.hypot(x - cx, y - cy) - r) ** 2)))
    return cx, cy, r, rmse


def in_sector(pts, cx, cy, az0, az1, rmin, rmax):
    d = pts - np.array([cx, cy])
    r = np.hypot(d[:, 0], d[:, 1])
    az = (np.degrees(np.arctan2(d[:, 0], d[:, 1]))) % 360
    span = (az1 - az0) % 360
    rel = (az - az0) % 360
    keep = (rel <= span) & (r >= rmin) & (r <= rmax)
    return pts[keep], az[keep], r[keep]


def process(slug):
    sd = os.path.join(ROOT, "data", "comparators", slug)
    cfg = json.load(open(os.path.join(sd, "site_config.json")))
    with rasterio.open(os.path.join(sd, "dem", "dem_clip_1m.tif")) as src:
        z = src.read(1)
        tf = src.transform
        nod = src.nodata

    import csv
    s, zft = [], []
    with open(os.path.join(sd, "derived", "centerline_section.csv")) as f:
        for row in csv.DictReader(f):
            if row["z_ft_navd88"]:
                s.append(float(row["s_ft"]))
                zft.append(float(row["z_ft_navd88"]))
    s, zft = np.array(s), np.array(zft)
    b = cfg["breaks_ft"]
    z_row1 = np.interp(b["row1_s"], s, zft)
    z_top = np.interp(b["seating_top_s"], s, zft)
    z_mid = (z_row1 + z_top) / 2

    ux, uy = cfg["arc_center_xy"]
    fan = cfg["fan_deg"]
    az0 = (fan["start_az"] - 15) % 360
    az1 = (fan["end_az"] + 15) % 360

    # expected radius of each contour from the centerline profile (first
    # crossing inside the seating zone) — bands keep out same-elevation
    # terrain elsewhere in the clip (e.g. SB creek floor north of the bowl)
    zone = (s >= b["row1_s"] * 0.5) & (s <= b["rim_crest_s"])
    sz, zzf = s[zone], zft[zone]

    def r_expected(level_ft):
        above = zzf >= level_ft
        idx = np.argmax(above) if above.any() else None
        if idx is None or idx == 0:
            return None
        return float(np.interp(level_ft, zzf[idx-1:idx+1], sz[idx-1:idx+1]))

    levels = {"row1": z_row1 + 2.0, "mid": z_mid, "top": z_top - 2.0}
    pts_m = {}
    for name, lev_ft in levels.items():
        r_exp_ft = r_expected(lev_ft)
        if r_exp_ft is None:
            pts_m[name] = np.empty((0, 2))
            continue
        rmin = r_exp_ft / US_FT_PER_M * 0.6
        rmax = r_exp_ft / US_FT_PER_M * 1.6
        pts = contour_points(z, tf, lev_ft / US_FT_PER_M, nod)
        kept, _, _ = in_sector(pts, ux, uy, az0, az1, rmin, rmax)
        pts_m[name] = kept

    if len(pts_m["mid"]) < 20:
        raise RuntimeError(f"{slug}: too few mid-contour points")
    # An unconstrained Kåsa fit drifts on <180° arcs flanked by natural
    # slope (verified: centers landed uphill, giving r(row1) > r(top)).
    # The spoke/ring QA overlays show the terraces visually concentric
    # about the stage-front anchor at both sites, so we CONSTRAIN the
    # center to the anchor and measure radii/extents about it.
    cx, cy = ux, uy
    free = kasa_fit(pts_m["mid"])
    d = pts_m["mid"] - np.array([cx, cy])
    center_az = (cfg["audience_facing_azimuth_deg"] + 180.0) % 360.0
    rel = ((np.degrees(np.arctan2(d[:, 0], d[:, 1])) - center_az + 180.0)
           % 360.0) - 180.0   # wrap-safe, centered on bowl axis
    lo, hi = np.percentile(rel, [2, 98])
    fan_meas = hi - lo
    rr_mid = np.hypot(d[:, 0], d[:, 1])
    rmse = float(np.sqrt(np.mean((rr_mid - np.median(rr_mid)) ** 2)))

    out = {"center_xy": [cx, cy],
           "center_basis": "CONSTRAINED to stage-front anchor (inferred); "
                           "unconstrained fit rejected — see script comment",
           "unconstrained_fit_center_xy": [free[0], free[1]],
           "unconstrained_fit_rmse_m": free[3],
           "mid_contour_radial_rmse_m": rmse,
           "fan_angle_measured_deg": round(float(fan_meas), 1),
           "fan_basis": "angular extent (2-98 pct) of mid-bowl contour about "
                        "stage-front anchor",
           "contour_levels_ft": {k: round(float(v), 1)
                                 for k, v in levels.items()},
           "radii_ft": {}}
    for name in ("row1", "mid", "top"):
        if len(pts_m[name]) >= 10:
            dd = pts_m[name] - np.array([cx, cy])
            rr = np.hypot(dd[:, 0], dd[:, 1])
            out["radii_ft"][name] = {
                "median": round(float(np.median(rr)) * US_FT_PER_M, 1),
                "p10_p90": [round(float(np.percentile(rr, 10)) * US_FT_PER_M, 1),
                            round(float(np.percentile(rr, 90)) * US_FT_PER_M, 1)],
                "n_pts": int(len(rr))}
    with open(os.path.join(sd, "derived", "arc_fit.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(f"{slug}: fan {out['fan_angle_measured_deg']}°, "
          f"r(row1) {out['radii_ft'].get('row1',{}).get('median')} ft, "
          f"r(mid) {out['radii_ft'].get('mid',{}).get('median')} ft, "
          f"r(top) {out['radii_ft'].get('top',{}).get('median')} ft, "
          f"radial rmse {rmse:.1f} m")


def main():
    for slug in SITES:
        process(slug)


if __name__ == "__main__":
    main()
