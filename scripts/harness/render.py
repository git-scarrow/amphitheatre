"""Renderer: plan view, cut/fill map, and centreline section for harness variants.

Visual style mirrors design_corner_bays — DEM terrain background, contour overlay,
seating geometry coloured by role, stage star + face arrow.

Three outputs per variant (all written into the variant directory):
  plan.png       — plan view: terrain + contours + cut/fill alpha overlay + all design objects
  cutfill.png    — zoomed cut/fill heatmap with contours and LOD boundary
  section.png    — centreline section: existing vs proposed terrain, row treads, C-value callouts

Also used standalone:
  python -m scripts.harness.render --baseline     (writes to design_open_low/)
  python -m scripts.harness.render --variant V0001
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
import rasterio

if TYPE_CHECKING:
    from .project import ProjectState
    from .clay import ClayDelta

# ── colour palette (matches corner_bays convention) ──────────────────────────
ROW_COLOR = "#1f77b4"         # seating rows
STAGE_COLOR = "navy"
ADA_COLOR = "#9467bd"
BORROW_COLOR = "#d62728"      # red = cut/borrow
FILL_COLOR = "#2ca02c"        # green = fill
NOTOUCH_COLOR = "#ff7f0e"     # orange = no-touch

WINDOW_FT = 220               # plan/section crop half-width around bowl centre

# ── helpers ──────────────────────────────────────────────────────────────────

def _U(az_deg: float):
    a = math.radians(az_deg)
    return math.sin(a), math.cos(a)


def _crop(Z: np.ndarray, T, cx: float, cy: float, win: float):
    """Return cropped subarray and its extent [x0,x1,y0,y1]."""
    c0 = max(0, int((cx - win - T.c) / T.a))
    c1 = min(Z.shape[1], int((cx + win - T.c) / T.a))
    r1 = max(0, int((cy - win - T.f) / T.e))   # T.e is negative
    r0 = min(Z.shape[0], int((cy + win - T.f) / T.e))
    if r0 > r1:
        r0, r1 = r1, r0
    sub = Z[r0:r1, c0:c1]
    ext = [T.c + c0 * T.a, T.c + c1 * T.a,
           T.f + r1 * T.e, T.f + r0 * T.e]
    return sub, ext


def _contour_levels(z_finite, step=1.0):
    lo = math.floor(np.nanmin(z_finite) / step) * step
    hi = math.ceil(np.nanmax(z_finite) / step) * step
    return np.arange(lo, hi + step, step)


def _draw_geojson_lines(ax, features, color, lw=1.6, label=None, section=None):
    """Plot all LineString features, optionally filtering by properties['name'] section."""
    plotted = False
    for f in features:
        if section and f.get("properties", {}).get("section") != section:
            continue
        g = f.get("geometry", {})
        if g.get("type") == "LineString":
            coords = g["coordinates"]
            xs = [c[0] for c in coords]
            ys = [c[1] for c in coords]
            kw = {"color": color, "lw": lw}
            if not plotted and label:
                kw["label"] = label
                plotted = True
            ax.plot(xs, ys, **kw)


def _draw_geojson_poly(ax, features, facecolor="none", edgecolor="gray", lw=1.0,
                        alpha=0.35, filter_name=None, label=None):
    from shapely.geometry import shape
    import matplotlib.patches as mpatches
    from matplotlib.path import Path as MPath
    plotted = False
    for f in features:
        if filter_name and f.get("properties", {}).get("name") != filter_name:
            continue
        g = f.get("geometry", {})
        if g.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        try:
            geom = shape(g)
        except Exception:
            continue
        if geom.geom_type == "Polygon":
            polys = [geom]
        else:
            polys = list(geom.geoms)
        for poly in polys:
            xs, ys = poly.exterior.xy
            kw = dict(facecolor=facecolor, edgecolor=edgecolor, lw=lw, alpha=alpha)
            if not plotted and label:
                kw["label"] = label
                plotted = True
            ax.fill(xs, ys, **kw)
            ax.plot(xs, ys, color=edgecolor, lw=lw)


# ── main render functions ─────────────────────────────────────────────────────

def plan_view(state: "ProjectState", delta: "ClayDelta",
              out_path: str | Path,
              metrics: dict | None = None,
              score: dict | None = None,
              scenario_geojson_features: list | None = None) -> Path:
    """Plan view: terrain + contours + cut/fill overlay + all design objects."""
    import json

    out_path = Path(out_path)
    p = state.params()
    FX, FY = state.arc_centre()
    SFx, SFy = state.stage_focus()
    face_az = p["FACE_AZ"]

    # Proposed DEM
    Zp = delta.proposed(state)
    Z0 = state.Z0
    D = delta.delta()  # cut/fill

    # Crop to window
    sub_p, ext = _crop(Zp, state.transform, FX, FY, WINDOW_FT)
    sub_0, _ = _crop(Z0, state.transform, FX, FY, WINDOW_FT)
    sub_d, _ = _crop(D, state.transform, FX, FY, WINDOW_FT)

    fig, ax = plt.subplots(figsize=(9, 9))

    # Terrain background (existing DEM for stable reference)
    vmin, vmax = np.nanpercentile(sub_0[np.isfinite(sub_0)], [2, 98])
    ax.imshow(sub_0, extent=ext, origin="upper", cmap="terrain",
              vmin=vmin, vmax=vmax, alpha=0.75)

    # Contours
    xg = np.linspace(ext[0], ext[1], sub_0.shape[1])
    yg = np.linspace(ext[3], ext[2], sub_0.shape[0])[::-1]
    finite_vals = sub_0[np.isfinite(sub_0)]
    if len(finite_vals) > 0:
        lev1 = _contour_levels(finite_vals, step=1.0)
        lev5 = _contour_levels(finite_vals, step=5.0)
        cs = ax.contour(xg, yg, sub_0, levels=lev1,
                        colors="k", linewidths=0.25, alpha=0.30)
        cs5 = ax.contour(xg, yg, sub_0, levels=lev5,
                         colors="k", linewidths=0.55, alpha=0.50)
        ax.clabel(cs5, fontsize=5, fmt="%d", inline=True)

    # Cut/fill overlay (only where |delta| > 0.05 ft)
    lod_tol = state.cfg["earthwork"]["lod_tolerance_ft"]
    d_plot = np.where(np.abs(sub_d) > lod_tol, sub_d, np.nan)
    d_finite = d_plot[np.isfinite(d_plot)]
    max_abs = max(0.1, float(np.abs(d_finite).max())) if len(d_finite) > 0 else 0.1
    norm_cf = mcolors.TwoSlopeNorm(vmin=-max_abs, vcenter=0, vmax=max_abs)
    cf_img = ax.imshow(d_plot, extent=ext, origin="upper",
                       cmap="RdBu_r", norm=norm_cf, alpha=0.45)
    plt.colorbar(cf_img, ax=ax, fraction=0.025, pad=0.01,
                 label="Cut (−) / Fill (+)  ft")

    # Scenario polygons (borrow / fill / no-touch)
    if scenario_geojson_features:
        role_style = {
            "borrow":    (BORROW_COLOR, "Borrow zone"),
            "fill":      (FILL_COLOR,   "Fill zone"),
            "no_touch":  (NOTOUCH_COLOR,"No-touch"),
            "haul_corridor": ("#8c564b", "Haul corridor"),
        }
        plotted_roles: set = set()
        for feat in scenario_geojson_features:
            role = feat.get("properties", {}).get("role", "")
            if role not in role_style:
                continue
            color, role_label = role_style[role]
            label = role_label if role not in plotted_roles else None
            plotted_roles.add(role)
            _draw_geojson_poly(ax, [feat], facecolor=color, edgecolor=color,
                               lw=1.2, alpha=0.18, label=label)

    # Seating rows (from geojson)
    row_feats = state.stage_features  # includes all stage_floor features
    try:
        rows_geojson = json.load(open(state.root / state.cfg["design"]["seating_rows"]))
        _draw_geojson_lines(ax, rows_geojson["features"],
                            color=ROW_COLOR, lw=1.6, label="Seating rows")
    except Exception:
        pass

    # Stage polygon
    stage_feat = [f for f in state.stage_features
                  if f["properties"].get("name") in ("stage", "stage_shoulder_left", "stage_shoulder_right")]
    _draw_geojson_poly(ax, stage_feat, facecolor=STAGE_COLOR, edgecolor=STAGE_COLOR,
                       lw=1.5, alpha=0.55)

    # Forecourt
    fore_feat = [f for f in state.stage_features
                 if f["properties"].get("name") == "event_floor_forecourt"]
    _draw_geojson_poly(ax, fore_feat, facecolor="lightyellow", edgecolor="goldenrod",
                       lw=1.0, alpha=0.30)

    # ADA routes
    try:
        _draw_geojson_lines(ax, state.ada_features, color=ADA_COLOR, lw=1.4, label="ADA routes")
    except Exception:
        pass

    # Treatment cell
    tc_feat = [f for f in state.stage_features
               if f["properties"].get("name") == "treatment_wet_cell"]
    _draw_geojson_poly(ax, tc_feat, facecolor="steelblue", edgecolor="steelblue",
                       lw=1.2, alpha=0.20, label="Treatment cell")

    # Stage star + face arrow
    ax.plot(SFx, SFy, "k*", ms=16, zorder=10)
    ux, uy = _U(face_az)
    ax.annotate("", xy=(SFx + ux * 80, SFy + uy * 80), xytext=(SFx, SFy),
                arrowprops=dict(arrowstyle="->", color="navy", lw=2.0))
    ax.annotate(f"{int(face_az)}°", xy=(SFx + ux * 90, SFy + uy * 90),
                fontsize=8, color="navy", ha="center")

    ax.set_aspect("equal")
    ax.set_xlabel("EPSG:6494 X (ft)")
    ax.set_ylabel("Y (ft)")

    # Title
    title_parts = ["Proposed plan — cut/fill overlay"]
    if metrics:
        ew = metrics.get("earthwork", {})
        sl = metrics.get("sightlines", {})
        title_parts.append(
            f"Cut {ew.get('cut_cy', 0):.0f} / Fill {ew.get('fill_cy', 0):.0f} CY  "
            f"· {sl.get('pass_count', 0)}/{sl.get('pass_count', 0) + sl.get('fail_count', 0)} rows ≥90mm"
        )
    if score:
        title_parts.append(f"Score {score.get('total', 0):.1f}/100  {score.get('verdict', '')}")

    ax.set_title("\n".join(title_parts), fontsize=10)
    ax.legend(loc="upper right", fontsize=7, framealpha=0.7)

    plt.tight_layout()
    plt.savefig(out_path, dpi=130)
    plt.close()
    return out_path


def cutfill_map(state: "ProjectState", delta: "ClayDelta",
                out_path: str | Path,
                metrics: dict | None = None) -> Path:
    """Zoomed cut/fill heatmap with 0.5-ft contours and LOD boundary."""
    out_path = Path(out_path)
    FX, FY = state.arc_centre()
    Z0 = state.Z0
    D = delta.delta()
    lod_tol = state.cfg["earthwork"]["lod_tolerance_ft"]

    win = 160  # tighter crop than plan view
    sub_z, ext = _crop(Z0, state.transform, FX, FY, win)
    sub_d, _ = _crop(D, state.transform, FX, FY, win)

    fig, ax = plt.subplots(figsize=(8, 8))

    # Cut/fill heatmap
    d_plot = np.where(np.abs(sub_d) > lod_tol, sub_d, np.nan)
    max_abs = max(0.1, float(np.nanmax(np.abs(d_plot[np.isfinite(d_plot)])) if np.isfinite(d_plot).any() else 0.1))
    norm_cf = mcolors.TwoSlopeNorm(vmin=-max_abs, vcenter=0, vmax=max_abs)
    im = ax.imshow(sub_d, extent=ext, origin="upper", cmap="RdBu_r",
                   norm=norm_cf, alpha=0.85)
    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.01,
                 label="Cut (−) / Fill (+)  ft")

    # Terrain contours at 0.5 ft
    xg = np.linspace(ext[0], ext[1], sub_z.shape[1])
    yg = np.linspace(ext[3], ext[2], sub_z.shape[0])[::-1]
    finite_z = sub_z[np.isfinite(sub_z)]
    if len(finite_z) > 0:
        lev = np.arange(math.floor(np.nanmin(finite_z)*2)/2,
                        math.ceil(np.nanmax(finite_z)*2)/2 + 0.5, 0.5)
        cs = ax.contour(xg, yg, sub_z, levels=lev,
                        colors="k", linewidths=0.4, alpha=0.45)
        ax.clabel(cs, fontsize=5, fmt="%.1f", inline=True)

    # LOD boundary
    sub_lod = (np.abs(sub_d) > lod_tol).astype(float)
    ax.contour(xg[:sub_lod.shape[1]], yg[:sub_lod.shape[0]], sub_lod,
               levels=[0.5], colors="yellow", linewidths=1.2, linestyles="--")

    # Seating rows outline
    try:
        import json
        rows_geojson = json.load(open(state.root / state.cfg["design"]["seating_rows"]))
        _draw_geojson_lines(ax, rows_geojson["features"],
                            color="white", lw=1.0, label="Rows")
    except Exception:
        pass

    ax.set_aspect("equal")
    ax.set_xlabel("EPSG:6494 X (ft)")
    ax.set_ylabel("Y (ft)")

    title = "Cut / Fill map  (red = cut, blue = fill, dashed = LOD boundary)"
    if metrics:
        ew = metrics.get("earthwork", {})
        title += (f"\nGross {ew.get('gross_cy', 0):.0f} CY  |  "
                  f"max cut {ew.get('max_cut_ft', 0):.2f} ft  "
                  f"max fill {ew.get('max_fill_ft', 0):.2f} ft")
    ax.set_title(title, fontsize=10)
    ax.legend(loc="upper right", fontsize=7, framealpha=0.7)

    plt.tight_layout()
    plt.savefig(out_path, dpi=130)
    plt.close()
    return out_path


def section_view(state: "ProjectState", delta: "ClayDelta",
                 out_path: str | Path,
                 metrics: dict | None = None) -> Path:
    """Centreline section: existing (dashed) vs proposed (solid) terrain + row treads + C callouts."""
    out_path = Path(out_path)
    p = state.params()
    FX, FY = state.arc_centre()
    SFx, SFy = state.stage_focus()
    ax_az = p["AX_AZ"]
    focus_elev = p["FOCUS_ELEV"]
    eye_ht = p["EYE_HT"]
    stage_r = p["STAGE_R"]
    R_inner = p["R_INNER"]
    R_outer = p["R_OUTER"]

    Zp = delta.proposed(state)
    Z0 = state.Z0

    # Sample centreline from -20 ft (upstage) to R_outer + 30 ft (behind last row)
    r_start = -20.0
    r_end = R_outer + 30.0
    n_pts = 300
    rs = np.linspace(r_start, r_end, n_pts)
    ux, uy = _U(ax_az)

    z0_line = []
    zp_line = []
    for r in rs:
        x = FX + ux * r
        y = FY + uy * r
        z0_line.append(state.elev_at(Z0, x, y))
        zp_line.append(state.elev_at(Zp, x, y))

    z0_line = np.array(z0_line)
    zp_line = np.array(zp_line)

    # Convert radius from arc centre to dist from stage
    dist = rs - stage_r

    # Get sightline rows from metrics if available
    sl_rows = (metrics or {}).get("sightline_rows", [])

    fig, axes = plt.subplots(2, 1, figsize=(12, 8),
                              gridspec_kw={"height_ratios": [3, 1]})
    ax_sec, ax_cv = axes

    # ── upper: section profile ────────────────────────────────────────────────
    ax_sec.plot(dist, z0_line, color="gray", lw=1.2, ls="--",
                label="Existing terrain", alpha=0.8)
    ax_sec.plot(dist, zp_line, color="#1f77b4", lw=1.8,
                label="Proposed terrain", alpha=0.9)

    # Stage datum line
    ax_sec.axhline(focus_elev, color="goldenrod", lw=0.8, ls=":",
                   alpha=0.7, label=f"Stage datum {focus_elev:.1f} ft")

    # Row treads
    for row in sl_rows:
        r_dist = row.get("dist_to_stage_ft", 0)
        tread = row.get("tread_elev", None)
        terr = row.get("terrain_elev", None)
        if tread is None:
            continue
        # Tread horizontal mark
        half_w = 1.0  # ±1 ft either side for visual tread
        ax_sec.plot([r_dist - half_w, r_dist + half_w], [tread, tread],
                    color="crimson", lw=2.0, solid_capstyle="butt")
        # Fill wedge if tread > terrain
        if terr is not None and tread > terr + 0.02:
            ax_sec.fill_between([r_dist - half_w, r_dist + half_w],
                                [terr, terr], [tread, tread],
                                color="salmon", alpha=0.5, lw=0)

    # Row labels every 4 rows
    for row in sl_rows[::4]:
        r_dist = row.get("dist_to_stage_ft", 0)
        tread = row.get("tread_elev")
        if tread:
            ax_sec.annotate(f"R{row['row']}", (r_dist, tread + 0.4),
                            fontsize=6, ha="center", color="crimson")

    # Eye-level sightline from last row to stage
    if sl_rows:
        last = sl_rows[-1]
        r_d = last.get("dist_to_stage_ft", 0)
        eye_z = last.get("tread_elev", focus_elev) + eye_ht
        ax_sec.plot([0, r_d], [focus_elev, eye_z],
                    color="limegreen", lw=0.9, ls=(0, (3, 3)),
                    alpha=0.6, label="Sightline (row 16→stage)")

    ax_sec.set_xlim(dist[0], dist[-1])
    ax_sec.set_ylabel("Elevation NAVD88 (ft)")
    ax_sec.set_title("Centreline section — existing (dashed) vs proposed (solid); row treads (red)", fontsize=10)
    ax_sec.legend(fontsize=7, loc="upper left", framealpha=0.7)
    ax_sec.axvline(0, color="k", lw=0.7, ls="--", alpha=0.4)
    ax_sec.annotate("stage front", (0, focus_elev - 0.5), fontsize=7, color="goldenrod")
    ax_sec.grid(axis="y", lw=0.3, alpha=0.4)

    # ── lower: C-value per row ────────────────────────────────────────────────
    c_rows = [r for r in sl_rows if r.get("C_value_mm") is not None]
    if c_rows:
        dists_c = [r["dist_to_stage_ft"] for r in c_rows]
        c_vals = [r["C_value_mm"] for r in c_rows]
        colors_c = ["#2ca02c" if v >= 90 else "#d62728" for v in c_vals]
        ax_cv.bar(dists_c, c_vals, width=2.2, color=colors_c, alpha=0.8)
        ax_cv.axhline(90, color="k", lw=1.0, ls="--", alpha=0.6, label="90 mm target")
        ax_cv.set_xlabel("Distance from stage (ft)")
        ax_cv.set_ylabel("C-value (mm)")
        ax_cv.set_title("Sightline C-value per row  (green ≥90 mm, red = fail)", fontsize=9)
        ax_cv.legend(fontsize=7, framealpha=0.7)
        ax_cv.set_xlim(dist[0], dist[-1])
        ax_cv.grid(axis="y", lw=0.3, alpha=0.4)
    else:
        ax_cv.axis("off")
        ax_cv.text(0.5, 0.5, "No sightline data", ha="center", va="center",
                   transform=ax_cv.transAxes, color="gray")

    if metrics:
        ew = metrics.get("earthwork", {})
        sl = metrics.get("sightlines", {})
        fig.suptitle(
            f"Cut {ew.get('cut_cy', 0):.0f} / Fill {ew.get('fill_cy', 0):.0f} CY  ·  "
            f"Sightlines {sl.get('pass_count', 0)}/{sl.get('pass_count', 0) + sl.get('fail_count', 0)} pass  ·  "
            f"Min C {sl.get('min_C_mm', '—')} mm",
            fontsize=9, y=1.01,
        )

    plt.tight_layout()
    plt.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close()
    return out_path


def render_variant(state: "ProjectState", delta: "ClayDelta",
                   out_dir: str | Path,
                   metrics: dict | None = None,
                   score: dict | None = None) -> list[Path]:
    """Generate all three images for a variant. Returns list of written paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True)

    # Load scenario features for plan overlay
    try:
        import json
        sc_path = state.root / "earthwork_scenarios.geojson"
        sc_feats = json.load(open(sc_path))["features"] if sc_path.exists() else []
    except Exception:
        sc_feats = []

    written = []
    written.append(plan_view(state, delta, out_dir / "plan.png",
                              metrics=metrics, score=score,
                              scenario_geojson_features=sc_feats))
    written.append(cutfill_map(state, delta, out_dir / "cutfill.png", metrics=metrics))
    written.append(section_view(state, delta, out_dir / "section.png", metrics=metrics))
    return written


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import os

    _HERE = Path(__file__).parent.parent
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))

    from harness.project import ProjectState
    from harness.clay import ClayDelta
    from harness.evaluators import EvaluatorSuite
    from harness.scoring import MultiObjectiveScorer

    parser = argparse.ArgumentParser(description="Harness renderer")
    parser.add_argument("--baseline", action="store_true",
                        help="Render baseline (delta=0) to design_open_low/")
    parser.add_argument("--variant", help="Render a saved variant, e.g. V0001")
    parser.add_argument("--out", help="Output directory override")
    parser.add_argument("--config", default="harness_config.yaml")
    args = parser.parse_args()

    os.chdir(Path(args.config).parent)

    state = ProjectState.load(args.config)
    suite = EvaluatorSuite(state)
    scorer = MultiObjectiveScorer()

    if args.baseline:
        delta = ClayDelta.zeros(state)
        metrics = suite.run_all(delta, bowl_axis_az=330.0)
        score = scorer.score(metrics)
        out_dir = Path(args.out) if args.out else state.root / "design_open_low"
        paths = render_variant(state, delta, out_dir, metrics=metrics, score=score)
        for p in paths:
            print(f"  wrote {p}")

    elif args.variant:
        from harness.variants import VariantManager
        import yaml
        vm = VariantManager(state.root / "variants")
        v = vm.load(args.variant)
        # Reload delta from tif
        vdir = state.root / "variants" / args.variant
        delta = ClayDelta.load(vdir / "delta.tif", state)
        out_dir = Path(args.out) if args.out else vdir
        metrics = v["metrics"]
        score = v["score"]
        paths = render_variant(state, delta, out_dir, metrics=metrics, score=score)
        for p in paths:
            print(f"  wrote {p}")

    else:
        parser.print_help()
