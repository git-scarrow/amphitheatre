#!/usr/bin/env python3
"""Normalized bowl-section overlay: Petoskey design vs the three measured
comparators, on one axis.

Why this exists: the combined 4-panel board (render_comparator_board.py)
needs the Petoskey raster dem/proposed_grade_1ft.tif, which is gitignored and
regenerable only from the source LAZ tiles + the PDAL CLI. This figure needs
NO raster — comparators come from their committed centerline_section.csv
(measured, 3DEP 1 m) and Petoskey from repo canon numbers in
data/comparators/petoskey_metrics.json (basis: canon, NOT measured here).

Both axes are normalized to the stage front: x = distance from stage front
(ft), y = elevation above the stage-front floor (ft). That is the only frame
in which four venues of different absolute datum are comparable.

Reproduce:  .venv/bin/python scripts/comparators/render_section_overlay.py
"""
import csv
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
COMP = os.path.join(ROOT, "data", "comparators")

STYLE = {
    "charlevoix_odmark_pavilion": ("#0072B2", "Odmark Pavilion, Charlevoix MI"),
    "meijer_gardens_amphitheater": ("#009E73", "Meijer Gardens, Grand Rapids MI"),
    "santa_barbara_bowl": ("#D55E00", "Santa Barbara Bowl, CA"),
}


def load_profile(slug):
    s, z = [], []
    with open(os.path.join(COMP, slug, "derived",
                           "centerline_section.csv")) as f:
        for row in csv.DictReader(f):
            if row["z_ft_navd88"]:
                s.append(float(row["s_ft"]))
                z.append(float(row["z_ft_navd88"]))
    return np.array(s), np.array(z)


def main():
    comp = json.load(open(os.path.join(COMP, "comparison.json")))
    fig, ax = plt.subplots(figsize=(13, 7))

    for slug, (color, label) in STYLE.items():
        s, z = load_profile(slug)
        m = comp[slug]
        s_row1 = m["stage_front_to_row1_ft"]["value"]
        s_top = m["upper_row_distance_ft"]["value"]
        z0 = float(np.interp(2.0, s, z))
        keep = (s >= -5) & (s <= max(s_top * 1.6, 130))
        ax.plot(s[keep], z[keep] - z0, lw=2.0, color=color,
                label=f"{label} — measured 3DEP 1 m")
        for sv, mk in ((s_row1, "o"), (s_top, "s")):
            ax.plot(sv, float(np.interp(sv, s, z)) - z0, mk, color=color,
                    ms=8, mec="k", mew=0.8, zorder=5)

    # Petoskey: canon design geometry, not a DEM trace. Straight rake between
    # the canonical row-1 and top-of-seating points.
    p = comp["petoskey"]
    p_row1 = 35.0                       # stage front -> row 1 (canon, ft)
    p_rise = p["rise_row1_to_top_ft"]["value"]
    p_top = p["upper_row_distance_ft"]["value"]
    ax.plot([0, p_row1, p_top], [0, 0, p_rise], lw=2.6, color="#111111",
            ls="--", label="Petoskey Pit civic bowl — DESIGN CANON (not measured)")
    ax.plot(p_row1, 0, "o", color="#111111", ms=9, mec="w", mew=1.0, zorder=6)
    ax.plot(p_top, p_rise, "s", color="#111111", ms=9, mec="w", mew=1.0,
            zorder=6)

    ax.axhline(0, color="k", lw=0.6, alpha=0.4)
    ax.axvline(0, color="r", lw=0.9, ls=":", alpha=0.7)
    ax.annotate("stage front", (0, -1.5), color="red", fontsize=9,
                rotation=90, va="top", ha="right")
    ax.set_xlabel("distance from stage front along bowl axis (ft)")
    ax.set_ylabel("elevation above stage-front floor (ft)")
    ax.set_title("Bowl sections, normalized to the stage front\n"
                 "circle = row 1 / front of seating   ·   square = top of seating",
                 fontsize=12)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9, loc="upper left")
    ax.set_xlim(-8, 235)
    fig.text(0.5, 0.005,
             "Comparators MEASURED from USGS 3DEP 1 m bare-earth DEM. "
             "Petoskey trace is DESIGN CANON (idealized straight rake), not a "
             "surveyed or DEM-measured profile — do not read it as as-built.",
             ha="center", fontsize=8, style="italic")
    out = os.path.join(ROOT, "boards", "bowl_section_overlay.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out, dpi=140, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    main()
