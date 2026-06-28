#!/usr/bin/env python3
"""Before/after visuals for the terrace terrain-overflow audit.

Produces, from the same framing:
  analysis/terrain_audit/overflow_plan_before_after.png
      plan view of the bowl, cells where rendered terrain protrudes above a
      designed flat plate (retained-ground overflow), pre-fix vs post-fix.
  analysis/terrain_audit/section_before_after.png
      a radial cross-section through the seating treads: existing ground,
      pre-fix proposed grade (green fringe bumps), post-fix proposed grade
      (clean flat plates + risers), with the design plate elevations marked.

These stand in for matched-camera Unreal captures (the Landscape renders the
post-fix proposed heightfield); a live UE capture is a follow-up that needs the
editor running.  CRS EPSG:6494, NAVD88 intl ft.
"""
import json
import os

import numpy as np
import rasterio
from rasterio.features import rasterize
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import in_situ_common as C

OUT = os.path.join(C.REPO, "analysis", "terrain_audit")
TOL = 0.10


def load(fn):
    ds = rasterio.open(fn)
    return ds, ds.read(1).astype("float64")


def main():
    dsP, prop_after = load(os.path.join(C.REPO, "dem", "proposed_grade_1ft.tif"))
    before_fn = os.path.join(C.REPO, "dem", "proposed_grade_1ft.before.tif")
    _, prop_before = load(before_fn) if os.path.exists(before_fn) else (dsP, prop_after)
    _, existing = load(C.DEM_DESIGN)
    T = dsP.transform
    nd = dsP.nodata
    valid = prop_after != nd

    rows = json.load(open(os.path.join(C.REPO, "unreal_export", "geo",
                                       "seating_rows.geojson")))["features"]
    plate_elevs = sorted({round(float(f["properties"]["proposed_elev_navd88_ft"]), 2)
                          for f in rows} | {round(C.AISLE_ELEV, 2)})

    def designed(v):
        o = np.zeros(v.shape, bool)
        for e in plate_elevs:
            o |= np.abs(v - e) <= TOL
        return o

    # ---- plate-elevation raster over tread footprints (all_touched) ----
    plate = np.full(prop_after.shape, np.nan)
    foot = np.zeros(prop_after.shape, bool)
    for f in rows:
        m = rasterize([(f["geometry"], 1)], out_shape=prop_after.shape,
                      transform=T, fill=0, all_touched=True).astype(bool) & valid
        plate[m] = float(f["properties"]["proposed_elev_navd88_ft"])
        foot |= m

    def overflow(grade):
        d = grade - plate
        return foot & (d > TOL) & ~designed(grade)

    ov_b = overflow(prop_before)
    ov_a = overflow(prop_after)

    # crop to bowl bbox for legibility
    ys, xs = np.nonzero(foot)
    r0, r1, c0, c1 = ys.min() - 8, ys.max() + 8, xs.min() - 8, xs.max() + 8
    sl = (slice(r0, r1), slice(c0, c1))

    # ===== figure 1: plan overflow maps =====
    fig, axs = plt.subplots(1, 2, figsize=(13, 6.2))
    base = np.where(valid, prop_after, np.nan)[sl]
    for ax, ov, ttl, n in [
        (axs[0], ov_b, "BEFORE — all_touched=False burn", int(ov_b.sum())),
        (axs[1], ov_a, "AFTER — all_touched=True burn", int(ov_a.sum()))]:
        ax.imshow(base, cmap="Greys", alpha=0.85)
        fp = np.where(foot[sl], 0.25, np.nan)
        ax.imshow(fp, cmap="Blues", vmin=0, vmax=1, alpha=0.35)
        delta = np.where(ov[sl], (prop_before - plate)[sl] if ov is ov_b
                         else (prop_after - plate)[sl], np.nan)
        im = ax.imshow(delta, cmap="Reds", vmin=0, vmax=1.5)
        ax.set_title(f"{ttl}\nretained-ground overflow cells = {n}", fontsize=11)
        ax.set_xticks([]); ax.set_yticks([])
    cax = fig.add_axes([0.92, 0.15, 0.015, 0.7])
    fig.colorbar(im, cax=cax, label="terrain above flat plate (ft)")
    fig.suptitle("Green existing terrain overflowing the flat seating terraces "
                 "(blue = tread footprints)", fontsize=12)
    fig.subplots_adjust(left=0.02, right=0.9, top=0.9, bottom=0.04, wspace=0.04)
    p1 = os.path.join(OUT, "overflow_plan_before_after.png")
    fig.savefig(p1, dpi=130); plt.close(fig)

    # ===== figure 2: radial cross-section through the EAST section treads =====
    east = [f for f in rows if f["properties"]["section"] == "east"]
    cents = []
    for f in east:
        ring = f["geometry"]["coordinates"][0]
        a = np.array(ring)
        cents.append((a[:, 0].mean(), a[:, 1].mean(),
                      float(f["properties"]["proposed_elev_navd88_ft"]),
                      f["properties"]["row"]))
    cents.sort(key=lambda t: t[2])  # by elevation = up the rake
    p_lo = np.array(cents[0][:2]); p_hi = np.array(cents[-1][:2])
    d = p_hi - p_lo
    L = np.hypot(*d)
    u = d / L
    # extend a bit past both ends
    s = np.linspace(-6, L + 6, int(L) + 24)
    xs_t = p_lo[0] + u[0] * s
    ys_t = p_lo[1] + u[1] * s
    rr, cc = rasterio.transform.rowcol(T, xs_t, ys_t)
    rr = np.clip(rr, 0, prop_after.shape[0] - 1)
    cc = np.clip(cc, 0, prop_after.shape[1] - 1)
    z_ex = existing[rr, cc]
    z_b = prop_before[rr, cc]
    z_a = prop_after[rr, cc]

    fig, ax = plt.subplots(figsize=(12, 5.2))
    ax.plot(s, z_ex, color="#6b8e23", lw=1.6, label="existing ground (green terrain)")
    ax.plot(s, z_b, color="#cc3333", lw=1.4, ls="--",
            label="proposed grade BEFORE (fringe overflow)")
    ax.plot(s, z_a, color="#1f4fcc", lw=1.8,
            label="proposed grade AFTER (flat plates + risers)")
    # mark plate elevations of the rows the transect passes
    for cx, cy, el, rw in cents:
        ax.axhline(el, color="0.8", lw=0.6, zorder=0)
    # shade overflow band where before > after (ground that had to be cut)
    over = z_b - z_a
    ax.fill_between(s, z_a, z_b, where=over > TOL, color="#cc3333", alpha=0.25,
                    label="cut (overflow removed)")
    ax.set_xlabel("distance up the rake, east section (ft)")
    ax.set_ylabel("elevation NAVD88 (ft)")
    ax.set_title("Cross-section through the east seating treads — terrain cut to "
                 "the flat plates")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.25)
    p2 = os.path.join(OUT, "section_before_after.png")
    fig.tight_layout(); fig.savefig(p2, dpi=130); plt.close(fig)

    print("wrote", os.path.relpath(p1, C.REPO))
    print("wrote", os.path.relpath(p2, C.REPO))
    print(f"overflow cells before={int(ov_b.sum())} after={int(ov_a.sum())}")


if __name__ == "__main__":
    main()
