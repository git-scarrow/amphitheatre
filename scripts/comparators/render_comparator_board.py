#!/usr/bin/env python3
"""Board 07 — comparator side-by-side: Petoskey civic bowl vs Santa Barbara
Bowl vs Frederik Meijer Gardens Amphitheater.

Row 1: plan diagrams, ALL AT THE SAME SCALE (600 ft windows, north up).
Row 2: centerline sections, ALL AT THE SAME SCALE, true scale (no vertical
       exaggeration), with calibrated human-scale figures from
       scripts/human_scale_common.py (same heights on all three sites).
Row 3: metric table with basis flags — M = measured (DEM/repo geometry),
       I = inferred from imagery/OSM (never presented as measured),
       P = published, C = Petoskey repo canon.

Petoskey geometry is read-only: proposed_grade_1ft.tif + vectors_geojson.
Output: boards/comparator_side_by_side.png
Reproduce:  .venv/bin/python scripts/comparators/render_comparator_board.py
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
from matplotlib.colors import LightSource
from matplotlib.patches import Polygon as MplPoly, Wedge

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.dirname(__file__))
import human_scale_common as H
import in_situ_common as C
from sites import SITES, US_FT_PER_M

ROOT = os.path.normpath(os.path.join(SCRIPTS, ".."))
PLAN_HALF_FT = 300.0          # 600 ft plan windows for every site
SEC_X = (-60, 260)            # shared section x-range (ft from stage front)
SEC_Y_SPAN = 110.0            # shared section y-span (ft)

FIG_COLORS = {"standing": "#0b6e4f", "seated": "#1d4e89"}


def draw_figure(ax, x_ft, ground_ft, posture, height_ft, scale=1.0):
    pts = H.figure_outline(posture, height_ft)
    xs = [x_ft + p[0] * scale for p in pts]
    zs = [ground_ft + p[1] * scale for p in pts]
    ax.fill(xs, zs, color=FIG_COLORS.get(posture, "k"), alpha=0.9, lw=0,
            zorder=6)


def petoskey_profile():
    """Sample the proposed grade along the seating axis (az 132) through the
    axis origin; returns s (ft from STAGE FRONT, + into audience) and z (ft).
    Stage front = 35 ft bayward of row 1 (canon); row 1 at axis radius 85."""
    fx, fy = C.FX, C.FY
    az = math.radians(C.AX_AZ)
    ux, uy = math.sin(az), math.cos(az)
    r1 = 85.0
    stage_front_s_axis = r1 - 35.0          # 50 ft from axis origin
    with rasterio.open(os.path.join(ROOT, "dem", "proposed_grade_1ft.tif")) as src:
        z = src.read(1)
        tf = src.transform
        nod = src.nodata
        ss = np.arange(-40.0, 300.0, 1.0)   # axis-radius coordinates
        zz = []
        for s in ss:
            x, y = fx + s * ux, fy + s * uy
            col = int((x - tf.c) / tf.a)
            row = int((y - tf.f) / tf.e)
            v = z[row, col] if (0 <= row < z.shape[0] and
                                0 <= col < z.shape[1]) else np.nan
            zz.append(np.nan if (nod is not None and v == nod) else float(v))
    s_from_front = ss - stage_front_s_axis
    return s_from_front, np.array(zz)


def comparator_profile(slug):
    s, z = [], []
    p = os.path.join(ROOT, "data", "comparators", slug, "derived",
                     "centerline_section.csv")
    with open(p) as f:
        for row in csv.DictReader(f):
            if row["z_ft_navd88"]:
                s.append(float(row["s_ft"]))
                z.append(float(row["z_ft_navd88"]))
    return np.array(s), np.array(z)


def hillshade_panel(ax, dem_path, center_xy, ft_per_unit, title,
                    vert_exag=2.0):
    """Render hillshade around center; returns extent in FEET relative to
    center so all plans share one scale."""
    with rasterio.open(dem_path) as src:
        z = src.read(1)
        tf = src.transform
        nod = src.nodata
    zm = np.ma.masked_equal(z, nod) if nod is not None else \
        np.ma.masked_invalid(z)
    ls = LightSource(azdeg=315, altdeg=42)
    hs = ls.hillshade(zm.filled(float(zm.mean())), vert_exag=vert_exag,
                      dx=abs(tf.a), dy=abs(tf.e))
    x0, y0 = center_xy
    # native extent -> feet relative to center
    left = (tf.c - x0) * ft_per_unit
    right = (tf.c + tf.a * z.shape[1] - x0) * ft_per_unit
    top = (tf.f - y0) * ft_per_unit
    bottom = (tf.f + tf.e * z.shape[0] - y0) * ft_per_unit
    ax.imshow(hs, extent=(left, right, bottom, top), cmap="gray",
              interpolation="bilinear")
    ax.set_xlim(-PLAN_HALF_FT, PLAN_HALF_FT)
    ax.set_ylim(-PLAN_HALF_FT, PLAN_HALF_FT)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, fontsize=11, fontweight="bold")


def draw_scalebar(ax, ox=0.0, oy=0.0):
    y = oy - PLAN_HALF_FT + 35
    x0 = ox - PLAN_HALF_FT + 30
    ax.plot([x0, x0 + 100], [y, y], color="k", lw=3, solid_capstyle="butt")
    ax.plot([x0, x0 + 50], [y + 3.5, y + 3.5], color="k", lw=3,
            solid_capstyle="butt")
    ax.annotate("100 ft", (x0 + 50, y - 10), ha="center", fontsize=8)
    ax.annotate("N", (ox + PLAN_HALF_FT - 45, oy + PLAN_HALF_FT - 60),
                fontsize=12, fontweight="bold", ha="center")
    ax.annotate("", xy=(ox + PLAN_HALF_FT - 45, oy + PLAN_HALF_FT - 25),
                xytext=(ox + PLAN_HALF_FT - 45, oy + PLAN_HALF_FT - 55),
                arrowprops=dict(arrowstyle="-|>", color="k"))


def geo_to_rel(coords, center, ft_per_unit):
    return [((c[0] - center[0]) * ft_per_unit,
             (c[1] - center[1]) * ft_per_unit) for c in coords]


def plan_comparator(ax, slug):
    sd = os.path.join(ROOT, "data", "comparators", slug)
    cfg = json.load(open(os.path.join(sd, "site_config.json")))
    arc = json.load(open(os.path.join(sd, "derived", "arc_fit.json")))
    center = cfg["arc_center_xy"]
    hillshade_panel(ax, os.path.join(sd, "dem", "dem_clip_1m.tif"),
                    center, US_FT_PER_M, SITES[slug]["name"],
                    vert_exag=2.0 if slug == "santa_barbara_bowl" else 4.0)
    fc = json.load(open(os.path.join(sd, "osm_features.geojson")))
    for ft in fc["features"]:
        if ft["properties"].get("role") == "stage_structure_footprint":
            rel = geo_to_rel(ft["geometry"]["coordinates"][0], center,
                             US_FT_PER_M)
            ax.add_patch(MplPoly(rel, closed=True, facecolor="#c0392b",
                                 edgecolor="darkred", alpha=0.75, zorder=5))
    # fan wedge (measured) + centerline
    fan = arc["fan_angle_measured_deg"]
    face = cfg["audience_facing_azimuth_deg"]
    away = (face + 180) % 360
    r_top = arc["radii_ft"]["top"]["median"]
    # matplotlib Wedge angles are CCW from +x; convert from azimuth
    a0 = 90 - (away + fan / 2)
    a1 = 90 - (away - fan / 2)
    ax.add_patch(Wedge((0, 0), r_top, a0, a1, width=None, facecolor="none",
                       edgecolor="#2980b9", lw=1.6, ls="--", zorder=4))
    az = math.radians(away)
    ax.plot([0, r_top * 1.15 * math.sin(az)],
            [0, r_top * 1.15 * math.cos(az)],
            color="#2980b9", lw=1.2, zorder=4)
    draw_scalebar(ax)


def plan_petoskey(ax):
    center = (C.FX, C.FY)
    hillshade_panel(ax, os.path.join(ROOT, "dem", "proposed_grade_1ft.tif"),
                    center, 1.0, "Petoskey Pit civic bowl (Scenario E)",
                    vert_exag=3.0)
    zones = json.load(open(os.path.join(ROOT, "vectors_geojson",
                                        "bowl_zones.geojson")))
    for f in zones["features"]:
        zn = f["properties"].get("zone")
        if zn not in ("stage_core", "stage_shoulder_left",
                      "stage_shoulder_right", "orchestra_event_floor",
                      "cross_aisle"):
            continue
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "Polygon" \
            else [p for mp in geom["coordinates"] for p in [mp[0]]]
        if geom["type"] == "Polygon":
            polys = [geom["coordinates"][0]]
        else:
            polys = [ring[0] for ring in geom["coordinates"]]
        color = "#c0392b" if zn.startswith("stage") else (
            "#d4a017" if zn == "cross_aisle" else "#7f8c8d")
        for ring in polys:
            rel = geo_to_rel(ring, center, 1.0)
            ax.add_patch(MplPoly(rel, closed=True, facecolor=color,
                                 edgecolor="none",
                                 alpha=0.75 if zn.startswith("stage") else 0.5,
                                 zorder=5))
    treads = json.load(open(os.path.join(ROOT, "vectors_geojson",
                                         "terrace_treads.geojson")))
    for f in treads["features"]:
        g = f["geometry"]
        lines = [g["coordinates"]] if g["type"] == "LineString" \
            else g["coordinates"]
        for ln in lines:
            rel = geo_to_rel(ln, center, 1.0)
            ax.plot([p[0] for p in rel], [p[1] for p in rel],
                    color="#145a32", lw=0.9, zorder=5)
    fan, face = 110.0, (C.AX_AZ + 180) % 360
    away = C.AX_AZ
    a0 = 90 - (away + fan / 2)
    a1 = 90 - (away - fan / 2)
    ax.add_patch(Wedge((0, 0), 157, a0, a1, facecolor="none",
                       edgecolor="#2980b9", lw=1.6, ls="--", zorder=4))
    az = math.radians(away)
    ax.plot([0, 185 * math.sin(az)], [0, 185 * math.cos(az)],
            color="#2980b9", lw=1.2, zorder=4)
    # bay-view arrow az 330
    azb = math.radians(330.0)
    ax.annotate("bay 330°",
                xy=(255 * math.sin(azb), 255 * math.cos(azb)),
                xytext=(120 * math.sin(azb), 120 * math.cos(azb)),
                arrowprops=dict(arrowstyle="-|>", color="#1a5276"),
                fontsize=8, color="#1a5276")
    # recenter window on the bowl (seating sits ~110 ft along az 132)
    ox = 110 * math.sin(math.radians(C.AX_AZ))
    oy = 110 * math.cos(math.radians(C.AX_AZ))
    ax.set_xlim(ox - PLAN_HALF_FT, ox + PLAN_HALF_FT)
    ax.set_ylim(oy - PLAN_HALF_FT, oy + PLAN_HALF_FT)
    draw_scalebar(ax, ox, oy)


def section_panel(ax, s, z, title, anno, datum=None):
    """True-scale section; s in ft from stage front, z absolute ft.
    Plots z relative to floor elevation so all sites share one y-range."""
    z0 = anno["floor_z"]
    ax.fill_between(s, z - z0, -12, color="#d7ccc8", lw=0)
    ax.plot(s, z - z0, color="#4e342e", lw=1.4)
    # stage deck rectangle (frontage side view: depth x ~3.5 ft deck height)
    sd, dep = anno.get("stage_h", 3.5), anno["stage_depth"]
    ax.fill_between([-dep, 0], [anno["stage_z"] - z0] * 2,
                    [anno["stage_z"] - z0 + sd] * 2,
                    color="#c0392b", alpha=0.85, zorder=5)
    for x_ft, gz, posture, h in anno["figures"]:
        draw_figure(ax, x_ft, gz - z0, posture, h)
    ax.axhline(0, color="k", lw=0.4, alpha=0.4)
    for x_ft, label, gz in anno.get("labels", []):
        ax.annotate(label, (x_ft, gz - z0 + 8), fontsize=7, ha="center",
                    color="#333")
    ax.set_xlim(*SEC_X)
    ax.set_ylim(-12, SEC_Y_SPAN - 12)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25, lw=0.4)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("ft from stage front", fontsize=8)
    ax.tick_params(labelsize=7)


def build_table(ax, comp):
    ax.axis("off")
    rows = [
        ("capacity (unlike bases — see memo)", "capacity"),
        ("stage core width (ft)", "stage_core_width_ft"),
        ("effective frontage w/ shoulders (ft)", "stage_effective_frontage_ft"),
        ("stage depth (ft)", "stage_depth_ft"),
        ("stage front → row 1 (ft)", "stage_front_to_row1_ft"),
        ("fan angle (deg)", "fan_angle_deg"),
        ("rise row 1 → top (ft)", "rise_row1_to_top_ft"),
        ("avg rake (%)", "avg_rake_pct"),
        ("local rake range (%)", "local_rake_range_pct"),
        ("upper-row distance (ft)", "upper_row_distance_ft"),
        ("rows / terraces", "row_count_est"),
    ]
    sites = ["petoskey", "meijer_gardens_amphitheater", "santa_barbara_bowl"]
    headers = ["metric", "Petoskey (design)", "Meijer Gardens", "SB Bowl"]
    flag = {"measured_dem": "M", "inferred_imagery": "I",
            "published": "P", "canon": "C"}
    cells = []
    for label, key in rows:
        line = [label]
        for sl in sites:
            v = comp[sl].get(key)
            if v is None:
                line.append("—")
                continue
            val = v["value"]
            if isinstance(val, list):
                val = f"{val[0]}–{val[1]}"
            line.append(f"{val}  [{flag[v['basis']]}]")
        cells.append(line)
    t = ax.table(cellText=cells, colLabels=headers, loc="center",
                 cellLoc="left", colWidths=[0.22, 0.27, 0.255, 0.255])
    t.auto_set_font_size(False)
    t.set_fontsize(8.5)
    t.scale(1, 1.55)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor("#cccccc")
        if r == 0:
            cell.set_facecolor("#34495e")
            cell.set_text_props(color="white", fontweight="bold")
    ax.set_title("[M] measured from DEM/repo geometry · [I] inferred from "
                 "imagery/OSM (not survey-grade) · [P] published · "
                 "[C] Petoskey canon.  Capacity bases differ: Petoskey = "
                 "geometric seat count, Meijer = lawn/event capacity (weak "
                 "cite), SB = ticketing capacity.  Petoskey 104 ft effective "
                 "frontage counts shoulders as performance surface — a "
                 "Rule 9 question the comparators cannot decide.",
                 fontsize=8, pad=4)


def main():
    comp = json.load(open(os.path.join(ROOT, "data", "comparators",
                                       "comparison.json")))
    fig = plt.figure(figsize=(22, 21))
    gs = fig.add_gridspec(3, 3, height_ratios=[1.25, 0.62, 0.78],
                          hspace=0.16, wspace=0.06)

    ax = fig.add_subplot(gs[0, 0]); plan_petoskey(ax)
    ax = fig.add_subplot(gs[0, 1]); plan_comparator(ax, "meijer_gardens_amphitheater")
    ax = fig.add_subplot(gs[0, 2]); plan_comparator(ax, "santa_barbara_bowl")

    seated = H.SEATED_HEIGHT_FT
    standing = 5.75

    # Petoskey section
    s, z = petoskey_profile()
    pz = comp["petoskey"]
    z_floor = 612.5
    figs = [(-17, 612.5, "standing", standing),
            (17, 612.5, "standing", standing),
            (38, 610.8, "seated", seated),
            (107, 633.5, "seated", seated),
            (118, 633.5, "standing", standing)]
    labels = [(-17, "stage 612.5", 616), (17, "event floor", 612.5),
              (35, "row 1", 611), (107, "row 18", 634)]
    ax = fig.add_subplot(gs[1, 0])
    section_panel(ax, s, z, "Petoskey — axis az 132 (proposed grade, true scale)",
                  {"floor_z": z_floor, "stage_z": 612.5, "stage_depth": 34,
                   "figures": figs, "labels": labels})
    ax.set_ylabel("ft above event floor", fontsize=8)

    # Meijer section
    s, z = comparator_profile("meijer_gardens_amphitheater")
    zf = comp["meijer_gardens_amphitheater"]["floor_elev_ft"]["value"]
    figs = [(-15, 811.5, "standing", standing),
            (12, np.interp(12, s, z), "seated", seated),
            (98, np.interp(98, s, z), "seated", seated),
            (110, np.interp(110, s, z), "standing", standing)]
    labels = [(-20, "stage (canopy)", 815), (10, "row 1", 811),
              (100, "lawn crest", 824.5)]
    ax = fig.add_subplot(gs[1, 1])
    section_panel(ax, s, z, "Meijer Gardens — centerline az 201 (USGS 1 m DEM)",
                  {"floor_z": zf, "stage_z": 811.5, "stage_depth": 45,
                   "figures": figs, "labels": labels})

    # SB section
    s, z = comparator_profile("santa_barbara_bowl")
    zf = comp["santa_barbara_bowl"]["floor_elev_ft"]["value"]
    figs = [(-20, 178.3, "standing", standing),
            (30, np.interp(30, s, z), "seated", seated),
            (212, np.interp(212, s, z), "seated", seated),
            (224, np.interp(224, s, z), "standing", standing)]
    labels = [(-25, "stage house", 183), (27, "row 1", 179),
              (215, "top of seating", 248)]
    ax = fig.add_subplot(gs[1, 2])
    section_panel(ax, s, z, "Santa Barbara Bowl — centerline az 276 (USGS 1 m DEM)",
                  {"floor_z": zf, "stage_z": 178.0, "stage_depth": 50,
                   "stage_h": 5.0, "figures": figs, "labels": labels})

    ax = fig.add_subplot(gs[2, :])
    build_table(ax, comp)

    fig.suptitle("Board 07 — Comparator benchmark: Petoskey civic bowl vs two "
                 "in-use bowl amphitheatres (same plan scale, true-scale "
                 "sections, calibrated human figures)",
                 fontsize=14, fontweight="bold", y=0.985)
    fig.text(0.5, 0.005,
             "Sources: USGS 3DEP 1 m DEM (CA_Montecito_2018, MI_31Co_Kent_2016)"
             " · OSM stage footprints (inferred) · Esri World Imagery "
             "(inferred) · Petoskey repo canon (EPSG:6494 ft, read-only). "
             "Figures: human_scale_common.py heights "
             f"(standing 5.75 ft, seated {H.SEATED_HEIGHT_FT} ft).",
             ha="center", fontsize=8)
    out = os.path.join(ROOT, "boards", "comparator_side_by_side.png")
    fig.savefig(out, dpi=110, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    main()
