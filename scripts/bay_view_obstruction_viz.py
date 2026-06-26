#!/usr/bin/env python3
"""Visual outputs for the bay-view obstruction analysis.

Reads analysis/bay_view_obstruction/ outputs and produces:
  heatmap_row_x_az.png  — row × azimuth obstruction heatmap
  profile_by_section.png — per-section clear% profile across rows
  plan_fan_diagram.png  — plan-view fan diagram showing blocked vs clear azimuths

Run after bay_view_obstruction.py.
"""
import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import in_situ_common as C

# Worktree-aware REPO override (same logic as bay_view_obstruction.py)
def _main_repo_root():
    import subprocess
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        common = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=here, text=True, stderr=subprocess.DEVNULL
        ).strip()
        git_dir = common if os.path.isabs(common) else os.path.normpath(os.path.join(here, common))
        main = os.path.normpath(os.path.join(git_dir, ".."))
        if os.path.exists(os.path.join(main, "dem", "dem_design_1ft.tif")):
            return main
    except Exception:
        pass
    return here

_repo = _main_repo_root()
if _repo != C.REPO:
    C.REPO = _repo

OUT_DIR = os.path.join(C.REPO, "analysis", "bay_view_obstruction")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np


def load_data():
    csv_path = os.path.join(OUT_DIR, "per_row_obstruction.csv")
    hm_path = os.path.join(OUT_DIR, "heatmap_row_x_az.csv")

    summaries = []
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            summaries.append(row)

    hm_rows = []
    with open(hm_path) as f:
        for row in csv.DictReader(f):
            hm_rows.append(row)

    return summaries, hm_rows


def make_heatmap(summaries, hm_rows):
    """Blocked% heatmap: rows on Y axis, azimuth on X axis."""
    # Build ordered band list (all three sections, row-ordered within each)
    band_keys = [s["band_key"] for s in summaries]

    # Build az list
    azimuths = sorted(set(float(r["az"]) for r in hm_rows))

    # Build matrix: bands × azimuths
    hm_dict = {}
    for r in hm_rows:
        hm_dict[(r["band_key"], float(r["az"]))] = float(r["blocked_pct"])

    mat = np.zeros((len(band_keys), len(azimuths)))
    for i, bk in enumerate(band_keys):
        for j, az in enumerate(azimuths):
            mat[i, j] = hm_dict.get((bk, az), 100.0)

    # Section dividers
    n_east = sum(1 for s in summaries if s["section"] == "east")
    n_bend = sum(1 for s in summaries if s["section"] == "bend")

    fig, ax = plt.subplots(figsize=(14, 9))
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "bay_obstruct",
        [(0.0, "#2ecc71"), (0.4, "#f1c40f"), (0.8, "#e67e22"), (1.0, "#c0392b")],
    )
    im = ax.imshow(
        mat, aspect="auto", origin="upper",
        extent=[azimuths[0] - 1, azimuths[-1] + 1, len(band_keys) - 0.5, -0.5],
        cmap=cmap, vmin=0, vmax=100,
    )
    plt.colorbar(im, ax=ax, label="Terrain-blocked % of bay-corridor rays")

    # Y-axis labels
    ax.set_yticks(range(len(band_keys)))
    ax.set_yticklabels(band_keys, fontsize=7)

    # Section dividers
    ax.axhline(n_east - 0.5, color="white", linewidth=1.5)
    ax.axhline(n_east + n_bend - 0.5, color="white", linewidth=1.5)

    # Bay corridor shading
    ax.axvspan(318, 342, alpha=0.12, color="cyan", label="Bay corridor 318-342°")

    # Vertical guide: bay axis
    ax.axvline(330, color="cyan", linewidth=0.8, linestyle="--")

    ax.set_xlabel("Azimuth (°, True North = 0)")
    ax.set_ylabel("Tread band (section + row)")
    ax.set_title(
        "Bay-view obstruction heatmap — Petoskey Civic Bowl\n"
        "Blocked % per row × azimuth  |  obstruction source: terrain_rim (DEM bare-earth)\n"
        "Stage confirmed non-obstructor (faces az 150°; bay at 330°)  ·  Trees excluded (bare-earth DEM)"
    )
    ax.legend(loc="upper left", fontsize=8)

    # Section labels on right
    for label, offset in [("EAST", n_east / 2), ("BEND", n_east + n_bend / 2), ("SOUTH", n_east + n_bend + (len(band_keys) - n_east - n_bend) / 2)]:
        ax.text(362, offset - 0.5, label, va="center", ha="left", fontsize=8,
                color="white", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc="0.3", ec="none"))

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "heatmap_row_x_az.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {os.path.relpath(out, C.REPO)}")


def make_profile(summaries):
    """Clear% by row for each section."""
    sections = ["east", "bend", "south"]
    colors = {"east": "#3498db", "bend": "#9b59b6", "south": "#e67e22"}

    fig, ax = plt.subplots(figsize=(10, 6))

    for sec in sections:
        rows_data = [(int(s["row"]), float(s["clear_pct_mean"]))
                     for s in summaries if s["section"] == sec]
        rows_data.sort()
        rows, clears = zip(*rows_data)
        ax.plot(rows, clears, "o-", color=colors[sec], label=sec.capitalize(), linewidth=1.8, markersize=5)

    # Thresholds
    ax.axhline(80, color="green", linewidth=0.8, linestyle="--", alpha=0.7, label="Acceptable ≥80%")
    ax.axhline(40, color="orange", linewidth=0.8, linestyle="--", alpha=0.7, label="Marginal ≥40%")

    # Cross-aisle zone
    ax.axvspan(8.5, 10.5, alpha=0.12, color="gray", label="Cross-aisle rows 9-10")
    ax.axvspan(4.5, 5.5, alpha=0.08, color="gray")

    ax.set_xlabel("Row number")
    ax.set_ylabel("Bay-corridor rays clear (%)")
    ax.set_title(
        "Bay-view clear % by row — Petoskey Civic Bowl\n"
        "Obstruction source: terrain_rim (DEM bare-earth)  ·  Bay corridor az 318-342°"
    )
    ax.set_ylim(-5, 105)
    ax.set_xticks(sorted({int(s["row"]) for s in summaries}))
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "profile_by_section.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {os.path.relpath(out, C.REPO)}")


def make_plan_fans(summaries, hm_rows):
    """Plan-view polar fan diagrams for three representative rows."""
    # Pick rows that represent blocked / marginal / acceptable
    rep_bands = [
        ("east r4",  "Row 4 east — BLOCKED (0% clear, eye 618 ft)"),
        ("bend r8",  "Row 8 bend — MARGINAL (69% clear, eye 623 ft)"),
        ("east r11", "Row 11 east — ACCEPTABLE (97% clear, eye 627 ft)"),
    ]

    hm_by_band = {}
    for r in hm_rows:
        hm_by_band.setdefault(r["band_key"], {})[float(r["az"])] = float(r["blocked_pct"])

    fig, axes = plt.subplots(1, 3, figsize=(15, 5),
                             subplot_kw={"projection": "polar"})

    for ax, (band_key, title) in zip(axes, rep_bands):
        az_blocked = hm_by_band.get(band_key, {})
        for az, blocked_pct in sorted(az_blocked.items()):
            az_rad = math.radians(90 - az)   # convert compass → math angle
            color = "#c0392b" if blocked_pct > 50 else (
                "#f1c40f" if blocked_pct > 10 else "#2ecc71"
            )
            ax.plot([az_rad, az_rad], [0, 1], color=color, linewidth=2, alpha=0.8)

        # Corridor band
        for az_c in np.arange(318, 343, 0.5):
            ax.plot([math.radians(90 - az_c), math.radians(90 - az_c)],
                    [0.95, 1.05], color="cyan", linewidth=1.5, alpha=0.4)

        # Bay axis
        ax.plot([math.radians(90 - 330), math.radians(90 - 330)],
                [0, 1.1], color="cyan", linewidth=1.0, linestyle="--")

        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_rticks([])
        ax.set_thetalim(math.radians(90 - 360), math.radians(90 - 280))
        ax.set_title(title, fontsize=8, pad=10, wrap=True)

    fig.suptitle(
        "Plan-view fan: green=clear, yellow=partial, red=blocked  |  Cyan=bay corridor 318-342°",
        fontsize=9,
    )
    plt.tight_layout()
    out = os.path.join(OUT_DIR, "plan_fan_diagram.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {os.path.relpath(out, C.REPO)}")


def main():
    summaries, hm_rows = load_data()
    print(f"Generating visualizations for {len(summaries)} tread bands...")
    make_heatmap(summaries, hm_rows)
    make_profile(summaries)
    make_plan_fans(summaries, hm_rows)
    print("Done.")


if __name__ == "__main__":
    main()
