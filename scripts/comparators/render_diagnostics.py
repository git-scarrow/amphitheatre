#!/usr/bin/env python3
"""Diagnostic renders for digitization: imagery + DEM hillshade/contours with
OSM overlay, in native UTM coordinates with a labeled grid. Also reports the
stage footprint's minimum rotated rectangle (dims + long-axis azimuth).

Output: data/comparators/<slug>/diagnostic_{imagery,dem}.png
Reproduce:  .venv/bin/python scripts/comparators/render_diagnostics.py
"""
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import LightSource
from shapely.geometry import shape

sys.path.insert(0, os.path.dirname(__file__))
from sites import SITES, US_FT_PER_M

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))


def stage_rect_report(slug):
    p = os.path.join(ROOT, "data", "comparators", slug, "osm_features.geojson")
    with open(p) as f:
        fc = json.load(f)
    for ft in fc["features"]:
        if ft["properties"].get("role") == "stage_structure_footprint":
            g = shape(ft["geometry"])
            r = g.minimum_rotated_rectangle
            xs, ys = r.exterior.xy
            edges = [(math.dist((xs[i], ys[i]), (xs[i+1], ys[i+1])),
                      math.degrees(math.atan2(xs[i+1]-xs[i], ys[i+1]-ys[i])) % 180)
                     for i in range(4)]
            edges.sort()
            short, long_ = edges[0], edges[-1]
            return {
                "centroid": [g.centroid.x, g.centroid.y],
                "area_m2": g.area,
                "rect_long_m": long_[0], "rect_short_m": short[0],
                "rect_long_ft": long_[0]*US_FT_PER_M,
                "rect_short_ft": short[0]*US_FT_PER_M,
                "long_axis_azimuth_deg": long_[1],
                "polygon": ft,
            }
    return None


def render(slug):
    site_dir = os.path.join(ROOT, "data", "comparators", slug)
    with open(os.path.join(site_dir, "dem", "provenance.json")) as f:
        prov = json.load(f)
    xmin, ymin, xmax, ymax = prov["clip_bounds_native"]
    with rasterio.open(os.path.join(site_dir, "dem", "dem_clip_1m.tif")) as src:
        z = src.read(1)
        nod = src.nodata
    zm = np.ma.masked_equal(z, nod) if nod is not None else np.ma.masked_invalid(z)

    with open(os.path.join(site_dir, "osm_features.geojson")) as f:
        fc = json.load(f)

    img = plt.imread(os.path.join(site_dir, "imagery",
                                  "esri_world_imagery_0p5m.png"))
    rep = stage_rect_report(slug)

    for kind in ("imagery", "dem"):
        fig, ax = plt.subplots(figsize=(14, 14))
        if kind == "imagery":
            ax.imshow(img, extent=(xmin, xmax, ymin, ymax))
        else:
            ls = LightSource(azdeg=315, altdeg=45)
            hs = ls.hillshade(zm.filled(np.nanmean(zm)), vert_exag=2,
                              dx=1, dy=1)
            ax.imshow(hs, extent=(xmin, xmax, ymin, ymax), cmap="gray")
            step = 1.0 if (zm.max()-zm.min()) < 40 else 2.0
            cs = ax.contour(np.linspace(xmin+0.5, xmax-0.5, z.shape[1]),
                            np.linspace(ymax-0.5, ymin+0.5, z.shape[0]),
                            zm, levels=np.arange(math.floor(zm.min()),
                                                 math.ceil(zm.max()), step),
                            colors="orange", linewidths=0.4, alpha=0.8)
            ax.clabel(cs, fmt="%d", fontsize=5)
        for ft in fc["features"]:
            g = ft["geometry"]
            coords = g["coordinates"][0] if g["type"] == "Polygon" \
                else g["coordinates"]
            xs = [c[0] for c in coords]; ys = [c[1] for c in coords]
            is_stage = ft["properties"].get("role") == "stage_structure_footprint"
            hw = ft["properties"].get("highway")
            color = "red" if is_stage else ("cyan" if hw else "lime")
            lw = 2.5 if is_stage else 0.8
            ax.plot(xs, ys, color=color, lw=lw)
        cx, cy = prov["center_native_xy"]
        ax.set_xlim(cx-220, cx+220); ax.set_ylim(cy-220, cy+220)
        ax.set_xticks(np.arange(round(cx-220, -1), cx+220, 40))
        ax.set_yticks(np.arange(round(cy-220, -1), cy+220, 40))
        ax.grid(True, color="yellow" if kind == "imagery" else "blue",
                alpha=0.35, lw=0.5)
        ax.tick_params(labelsize=7)
        ax.set_title(f"{SITES[slug]['name']} — {kind} + OSM "
                     f"({prov['native_crs']}, m)", fontsize=11)
        ax.set_aspect("equal")
        out = os.path.join(site_dir, f"diagnostic_{kind}.png")
        fig.savefig(out, dpi=130, bbox_inches="tight")
        plt.close(fig)
        print("wrote", out)
    if rep:
        print(f"{slug} stage footprint (OSM, inferred): "
              f"{rep['rect_long_ft']:.0f} x {rep['rect_short_ft']:.0f} ft "
              f"(long x short), long-axis az {rep['long_axis_azimuth_deg']:.1f}/"
              f"{(rep['long_axis_azimuth_deg']+180)%360:.1f} deg, "
              f"centroid {rep['centroid'][0]:.1f},{rep['centroid'][1]:.1f}")


def main():
    for slug in SITES:
        render(slug)


if __name__ == "__main__":
    main()
