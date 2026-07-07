#!/usr/bin/env python3
"""Render the context-reclassification diagnostic overlay (plan view).

Re-renders the bay-view scene in analysis space with the three diagnostic
classes made visible and FALSE building primitives replaced by vegetation
proxies:

    verified_building (corridor occluder)  solid slate, labelled
    verified_building (other)              faint grey footprint
    tree_canopy (vegetation proxy)         green hatched — drawn as foliage,
                                           NOT a building block
    unknown_vertical_obstruction           magenta (none present)

Two panels: (L) full context extent, (R) zoom on the bay-view corridor where
the obstruction factor is decided.  Reads context_reclassification.geojson.

This is the analysis-grade re-render (deterministic, no live editor).  A live
UE viewport re-capture from the same camera is a one-command follow-up once the
editor is up:  python scripts/unreal/open_and_frame_civicbowl.py + capture.
"""
import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly, Wedge, Patch

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "analysis", "context_reclassification")

COL = {
    "occluder": "#2f3b52",      # verified building used for obstruction
    "building": "#c9ccd4",      # verified building, not an occluder
    "tree": "#3f9b46",          # vegetation proxy
    "unknown": "#d11fa3",       # unknown vertical obstruction
    "corridor": "#6fa8dc",
    "focal": "#e8a02d",
}


def az_xy(focal, az_deg, r):
    rad = math.radians(az_deg)
    return focal[0] + r * math.sin(rad), focal[1] + r * math.cos(rad)


def draw(ax, feats, focal, corridor, zoom=None, label_occluders=False):
    # bay corridor wedge (matplotlib Wedge uses math angles ccw from +x;
    # convert compass az -> math angle: theta = 90 - az)
    a0, a1 = corridor
    t_lo, t_hi = 90.0 - a1, 90.0 - a0
    reach = 200 if zoom else 1300
    ax.add_patch(Wedge(focal, reach, t_lo, t_hi, color=COL["corridor"],
                       alpha=0.13, zorder=0, label="_corridor"))
    for line_az in (corridor[0], 330.0, corridor[1]):
        x, y = az_xy(focal, line_az, reach)
        ax.plot([focal[0], x], [focal[1], y], color=COL["corridor"],
                lw=0.8, ls="--", alpha=0.6, zorder=1)

    occ = []
    for f in feats:
        g = f["geometry"]
        p = f["properties"]
        cls = p["classification"]
        if g is None:
            continue
        ring = g["coordinates"][0]
        if cls == "tree_canopy":
            ax.add_patch(MplPoly(ring, closed=True, facecolor=COL["tree"],
                                 edgecolor="#1d5e22", alpha=0.45, hatch="xx",
                                 lw=1.2, zorder=4))
        elif cls == "unknown_vertical_obstruction":
            ax.add_patch(MplPoly(ring, closed=True, facecolor=COL["unknown"],
                                 edgecolor="k", alpha=0.7, zorder=5))
        else:  # verified_building
            if p.get("used_for_obstruction"):
                ax.add_patch(MplPoly(ring, closed=True, facecolor=COL["occluder"],
                                     edgecolor="k", lw=0.6, zorder=3))
                occ.append((ring, p))
            else:
                ax.add_patch(MplPoly(ring, closed=True, facecolor=COL["building"],
                                     edgecolor="#9aa0ab", lw=0.3, alpha=0.85,
                                     zorder=2))
    if label_occluders:
        for ring, p in occ:
            cx = sum(x for x, _ in ring[:-1]) / (len(ring) - 1)
            cy = sum(y for _, y in ring[:-1]) / (len(ring) - 1)
            nm = p.get("name") or p["id"]
            ax.annotate(nm, (cx, cy), fontsize=6.5, ha="center", va="bottom",
                        color="k", zorder=6,
                        xytext=(0, 4), textcoords="offset points")

    ax.plot(*focal, marker="*", ms=16, color=COL["focal"],
            markeredgecolor="k", zorder=7, label="_focal")
    ax.set_aspect("equal")
    ax.set_xlabel("East (m, ENU rel origin)")
    ax.set_ylabel("North (m)")
    if zoom:
        ax.set_xlim(focal[0] - zoom, focal[0] + zoom)
        ax.set_ylim(focal[1] - 40, focal[1] + zoom)


def main():
    ov = json.load(open(os.path.join(OUT, "context_reclassification.geojson")))
    feats = ov["features"]
    focal = ov["focal_enu_m"]
    corridor = ov["bay_corridor_deg"]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 8))
    draw(axL, feats, focal, corridor, zoom=None, label_occluders=False)
    axL.set_title("Full context extent — 890 footprints by class", fontsize=11)
    draw(axR, feats, focal, corridor, zoom=170, label_occluders=True)
    axR.set_title("Bay-view corridor (318-342) — occluders + vegetation proxy",
                  fontsize=11)

    n = {c: sum(1 for f in feats
                if f["properties"]["classification"] == c)
         for c in ("verified_building", "tree_canopy",
                   "unknown_vertical_obstruction")}
    n_occ = sum(1 for f in feats
                if f["properties"].get("used_for_obstruction"))
    legend = [
        Patch(fc=COL["occluder"], ec="k",
              label=f"verified_building · bay occluder ({n_occ})"),
        Patch(fc=COL["building"], ec="#9aa0ab",
              label=f"verified_building · other ({n['verified_building'] - n_occ})"),
        Patch(fc=COL["tree"], ec="#1d5e22", hatch="xx", alpha=0.6,
              label=f"tree_canopy · vegetation proxy ({n['tree_canopy']})"),
        Patch(fc=COL["unknown"], ec="k",
              label=f"unknown_vertical_obstruction ({n['unknown_vertical_obstruction']})"),
        Patch(fc=COL["corridor"], alpha=0.3, label="bay-view corridor 318-342"),
        plt.Line2D([], [], marker="*", ms=12, color=COL["focal"],
                   ls="", markeredgecolor="k", label="focal seating eye"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=3, fontsize=9,
               frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Civic Bowl context massing — reclassified by source & confidence\n"
                 "Buildings only from footprint sources; height-only clusters -> "
                 "tree/unknown.  0 buildings reclassified; bay-view occluder set "
                 "unchanged.", fontsize=12)
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    out_png = os.path.join(OUT, "reclassification_plan.png")
    fig.savefig(out_png, dpi=130, bbox_inches="tight")
    print(f"  wrote {os.path.relpath(out_png, REPO)}")


if __name__ == "__main__":
    main()
