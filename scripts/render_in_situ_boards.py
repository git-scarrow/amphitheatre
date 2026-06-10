#!/usr/bin/env python3
"""Boards + viewpoint placeholder renders — three-section civic bowl.

  renders/<viewpoint>.png            six SCHEMATIC plan-diagram placeholders
  boards/01_site_fit_board.png       plan on hillshade, sections coloured
                                     separately, cut/fill, governing metrics
  boards/02_experience_board.png     station map + placeholders + bend-axis
                                     section + per-section C-values
  boards/03_landscape_character_board.png  materials + six event-mode panels
  boards/board_sources.json          structural manifest: governing scheme +
                                     source layers (audited)

The three seating families (east / bend=SE / south) are drawn in DISTINCT
colours with their hinge rays so the boards can never read as one uniform
fan. The stage is labelled "refit OPEN (Rule 9)". Renders from tracked
vectors alone; the DEM adds hillshade/cut-fill/profile when present.
Deterministic output. EPSG:6494, NAVD88 intl ft.
"""
import json
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LightSource
from matplotlib.lines import Line2D
from matplotlib.patches import PathPatch
from matplotlib.path import Path

import in_situ_common as C

RENDERS = os.path.join(C.REPO, "renders")
BOARDS = os.path.join(C.REPO, "boards")
FOOT = ("PLANNING-GRADE / SCHEMATIC — not stamped engineering · EPSG:6494 · "
        "NAVD88 (Geoid12A) intl ft · three-section civic bowl (Scenario E) · "
        "stage refit OPEN (Rule 9) · scripts/render_in_situ_boards.py")

SECTION_COLORS = {"east": "#b08968", "bend": "#7fae6e", "south": "#5e8a9e"}
MAT_FALLBACK = "#cccccc"


def load(name):
    with open(os.path.join(C.VEC_DIR, name)) as fh:
        return json.load(fh)["features"]


def geoms_to_patch(geom, **kw):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    verts, codes = [], []
    for rings in polys:
        for ring in rings:
            verts.extend(ring)
            codes.extend([Path.MOVETO] + [Path.LINETO] * (len(ring) - 2) + [Path.CLOSEPOLY])
    return PathPatch(Path(verts, codes), **kw)


def draw_layer(ax, feats, **kw):
    for f in feats:
        g = f["geometry"]
        if g["type"] in ("Polygon", "MultiPolygon"):
            pk = {k: v for k, v in kw.items()
                  if k in ("facecolor", "edgecolor", "alpha", "lw", "ls", "zorder", "hatch")}
            ax.add_patch(geoms_to_patch(g, **pk))
        elif g["type"] in ("LineString", "MultiLineString"):
            lines = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
            for ln in lines:
                xs, ys = zip(*ln)
                ax.plot(xs, ys, **{k: v for k, v in kw.items()
                                   if k in ("color", "lw", "ls", "alpha", "zorder")})
        elif g["type"] == "Point":
            ax.plot(*g["coordinates"], "o", ms=kw.get("ms", 5),
                    color=kw.get("color", "k"), zorder=kw.get("zorder", 5))


def dem_arrays():
    if not os.path.exists(C.DEM_DESIGN):
        return None
    import rasterio

    ds = rasterio.open(C.DEM_DESIGN)
    A = ds.read(1).astype(float)
    A[A == ds.nodata] = np.nan
    b = ds.bounds
    cf = None
    cf_path = os.path.join(C.REPO, "dem", "cut_fill_1ft.tif")
    if os.path.exists(cf_path):
        d2 = rasterio.open(cf_path)
        cf = d2.read(1).astype(float)
        cf[cf == d2.nodata] = np.nan
    return dict(dem=A, cf=cf, extent=(b.left, b.right, b.bottom, b.top),
                transform=ds.transform)


def hillshade_base(ax, D):
    if D is None:
        ax.set_facecolor("#eeece6")
        ax.text(0.02, 0.02, "DEM missing — vector-only base (see dem/MISSING_DATA.md)",
                transform=ax.transAxes, fontsize=7, color="#884444", zorder=20)
        return
    ls = LightSource(azdeg=315, altdeg=45)
    hs = ls.hillshade(np.where(np.isfinite(D["dem"]), D["dem"], np.nanmedian(D["dem"])),
                      vert_exag=2, dx=1, dy=1)
    ax.imshow(hs, cmap="gray", extent=D["extent"], origin="upper",
              alpha=0.85, zorder=0)


def plan_geometry(ax, mats, treads, zones, ctx, vps=None, lw_scale=1.0,
                  section_colors=True, show_stage=True, floor_override=None):
    """Standard plan: material base, then the three families coloured
    separately, hinge rays, stage, circulation.

    show_stage=False suppresses the inherited stage. The stored zones were
    DERIVED from it, so two presentation patches remove its silhouette:
    floor_override replaces the orchestra polygon (whose hull traced the old
    stage corners), and the slope-grass backdrop is unioned with the old
    footprint (whose hole otherwise shows bare hillshade in the old stage's
    exact shape)."""
    colors = {f["properties"]["zone"]: f["properties"].get("color_hint", MAT_FALLBACK)
              for f in mats}
    base_order = ["existing_slope_grass", "event_floor", "bioretention_planting",
                  "vegetated_swales", "accessible_paths", "hardscape_stage",
                  "existing_vegetation"]
    if not show_stage:
        base_order.remove("hardscape_stage")
    alphas = {"existing_slope_grass": 0.25, "existing_vegetation": 0.35}
    for z in base_order:
        f = next((m for m in mats if m["properties"]["zone"] == z), None)
        if f:
            if z == "event_floor" and floor_override is not None:
                f = {"geometry": floor_override, "properties": f["properties"]}
            elif z == "existing_slope_grass" and not show_stage:
                from shapely.geometry import shape as _shape, mapping as _mapping
                from shapely.ops import unary_union as _uu

                old_stage = [_shape(g["geometry"]) for g in zones
                             if g["properties"]["zone"].startswith("stage")]
                f = {"geometry": _mapping(_uu([_shape(f["geometry"])] + old_stage)),
                     "properties": f["properties"]}
            draw_layer(ax, [f], facecolor=colors.get(z, MAT_FALLBACK),
                       edgecolor="none", alpha=alphas.get(z, 0.8), zorder=2)
    for f in treads:
        sec = f["properties"]["section"]
        fc = SECTION_COLORS[sec] if section_colors else "#7fae6e"
        draw_layer(ax, [f], facecolor=fc, edgecolor="white",
                   lw=0.2 * lw_scale, alpha=0.9, zorder=3)
    zmap = {}
    for f in zones:
        zmap.setdefault(f["properties"]["zone"], []).append(f)
    draw_layer(ax, zmap.get("hinge_ray", []), color="#7b241c", lw=1.0 * lw_scale,
               ls=(0, (4, 3)), zorder=6)
    if show_stage:
        for z in ("stage_core", "stage_shoulder_left", "stage_shoulder_right"):
            draw_layer(ax, zmap.get(z, []), facecolor="none",
                       edgecolor="#5a4632", lw=1.0 * lw_scale, zorder=4)
    draw_layer(ax, zmap.get("cross_aisle", []), facecolor="#d9cfa3",
               edgecolor="#8a7d54", lw=0.5, alpha=0.95, zorder=4)
    rim = [f for f in ctx if f["properties"]["kind"] == "rim_arrival_edge"]
    draw_layer(ax, rim, color="#7a4a12", lw=1.4 * lw_scale, zorder=4)
    corr = [f for f in ctx if f["properties"]["kind"] == "bay_view_corridor"]
    draw_layer(ax, corr, facecolor="#9ec9e8", edgecolor="#5588bb",
               alpha=0.18, lw=0.8, zorder=1)
    paths = [f for f in ctx if f["properties"]["kind"] in ("park_path", "service_access")]
    draw_layer(ax, paths, color="#666666", lw=0.9 * lw_scale, ls="--", zorder=3)
    if vps:
        for f in vps:
            x, y = f["geometry"]["coordinates"]
            ax.plot(x, y, "^", ms=7, color="#c0392b", mec="white", zorder=8)


def view_cone(ax, p, fov=60.0, **kw):
    x, y = p["geometry"]["coordinates"]
    pr = p["properties"]
    az, dist = pr["look_azimuth_deg"], pr["look_distance_ft"]
    L = min(dist, 180)
    for d in (-fov / 2, fov / 2):
        ex, ey = C.polar(L, az + d, x, y)
        ax.plot([x, ex], [y, ey], **kw)
    ax.annotate("", xy=(pr["look_target_x"], pr["look_target_y"]), xytext=(x, y),
                arrowprops=dict(arrowstyle="->", color=kw.get("color", "#c0392b"),
                                lw=1.2, alpha=0.9))


def fmt_axes(ax, bounds=None, pad=30):
    ax.set_aspect("equal")
    if bounds:
        ax.set_xlim(bounds[0] - pad, bounds[2] + pad)
        ax.set_ylim(bounds[1] - pad, bounds[3] + pad)
    ax.set_xticks([])
    ax.set_yticks([])


def all_bounds(featsets, pad=0):
    xs, ys = [], []

    def rec(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for v in c:
                rec(v)

    for feats in featsets:
        for f in feats:
            rec(f["geometry"]["coordinates"])
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad


def north_arrow(ax):
    ax.annotate("N", xy=(0.965, 0.945), xytext=(0.965, 0.86),
                xycoords="axes fraction", ha="center", fontsize=9,
                arrowprops=dict(arrowstyle="-|>", color="k"))


def section_legend(ax, loc="lower left"):
    handles = [Line2D([], [], marker="s", ls="", ms=9, color=SECTION_COLORS[s],
                      label=f"{s} family" + (" (southeast)" if s == "bend" else ""))
               for s in C.SECTIONS]
    handles.append(Line2D([], [], color="#7b241c", ls=(0, (4, 3)),
                          label="hinge ray (section transition)"))
    ax.legend(handles=handles, fontsize=6.5, loc=loc, framealpha=0.85)


def render_viewpoints(vps, mats, treads, zones, ctx, D):
    os.makedirs(RENDERS, exist_ok=True)
    rim = [f for f in ctx if f["properties"]["kind"] == "rim_arrival_edge"]
    for f in vps:
        p = f["properties"]
        fig, ax = plt.subplots(figsize=(8, 6), dpi=110)
        hillshade_base(ax, D)
        plan_geometry(ax, mats, treads, zones, ctx)
        x, y = f["geometry"]["coordinates"]
        view_cone(ax, f, color="#c0392b", lw=1.3)
        ax.plot(x, y, "^", ms=11, color="#c0392b", mec="white", zorder=9)
        b = all_bounds([rim])
        fmt_axes(ax, (min(b[0], x), min(b[1], y), max(b[2], x), max(b[3], y)), pad=60)
        north_arrow(ax)
        ax.set_title(f"{p['name']}  —  SCHEMATIC PLACEHOLDER (plan diagram, "
                     "not a perspective render)", fontsize=9)
        txt = (f"{p['description']}\n"
               f"camera {p['camera_elev_navd88']:.1f} ft NAVD88 "
               f"(eye +{p['eye_height_ft']:.1f} ft, {p['camera_elev_source']})\n"
               f"look az {p['look_azimuth_deg']:.0f}°, target "
               f"{p['look_target_elev_navd88']:.1f} ft @ {p['look_distance_ft']:.0f} ft, "
               f"suggested FOV {p['fov_deg_suggested']}°")
        ax.text(0.01, -0.02, txt, transform=ax.transAxes, fontsize=7,
                va="top", wrap=True)
        fig.savefig(os.path.join(RENDERS, f"{p['name']}.png"),
                    bbox_inches="tight", facecolor="white")
        plt.close(fig)
    print(f"  wrote renders/<name>.png x{len(vps)} (schematic placeholders)")


def axis_profile(ax, treads, comp, D):
    """Profile along the bend-section axis (az 132 from the axis origin)."""
    if D is not None:
        import rasterio

        s = np.linspace(-260, 215, 960)
        xs = C.FX + np.sin(math.radians(C.AX_AZ)) * s
        ys = C.FY + np.cos(math.radians(C.AX_AZ)) * s
        rr, cc = rasterio.transform.rowcol(D["transform"], xs, ys)
        rr = np.clip(rr, 0, D["dem"].shape[0] - 1)
        cc = np.clip(cc, 0, D["dem"].shape[1] - 1)
        ax.plot(s, D["dem"][rr, cc], color="#7a6a55", lw=1.0,
                label="existing ground (DEM, az 132 axis)")
    bend = sorted((f["properties"] for f in treads
                   if f["properties"]["section"] == "bend"),
                  key=lambda p: p["row"])
    for p in bend:
        R = p["axis_radius_ft"]
        ax.plot([R - 1.8, R + 1.8], [p["tread_elev_navd88"]] * 2,
                color=SECTION_COLORS["bend"], lw=2.4)
    prom_r, prom_e = 101.8, float(comp[(5, "bend")]["elev"])
    ax.plot([prom_r - 4, prom_r + 4], [prom_e] * 2, color="#d9cfa3", lw=3.2,
            label="row-5 promenade hinge")
    ax.plot([117.1 - 4, 121.4 + 4], [C.AISLE_ELEV] * 2, color="#8a7d54", lw=3.2,
            label="cross-aisle (rows 9-10) 622.01")
    ax.plot([16, 50], [C.FOCUS_ELEV] * 2, color="#5a4632", lw=3,
            label="stage deck (refit OPEN — Rule 9)")
    ax.axhline(C.TREATMENT_BOTTOM, color="#6f9b8f", lw=0.8, ls="--",
               label="treatment-cell bottom 609.1 (dry/ephemeral)")
    p8 = next(p for p in bend if p["row"] == 8)
    ax.annotate("", xy=(-255, 612.0),
                xytext=(p8["axis_radius_ft"], p8["tread_elev_navd88"] + C.EYE_SEATED_FT),
                arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=1.1, alpha=0.8))
    ax.text(-180, 630, "→ bay + sky backdrop\n(no upstage shell)", fontsize=7,
            color="#1f77b4")
    ax.set_xlabel("ft along bend-section axis from origin (− = NNW toward bay)",
                  fontsize=7)
    ax.set_ylabel("ft NAVD88", fontsize=7)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=6, loc="upper left")
    ax.grid(alpha=0.2)


def provisional_corners():
    """Corner ring of the P_opt provisional footprint, or None."""
    path = os.path.join(C.REPO, "analysis", "in_situ_normalization",
                        "stage_typology_scores.json")
    if not os.path.exists(path):
        return None, None
    st = json.load(open(path))
    sel = st["selected_placement"]
    P, az = sel["front_centre"], sel["axis_az"]
    ux, uy = C.U(az)
    wx, wy = C.U(az + 90.0)
    corners = [(P[0] + ux * u + wx * w, P[1] + uy * u + wy * w)
               for u, w in ((0, -35), (0, 35), (-34, 35), (-34, -35), (0, -35))]
    return st, corners


def provisional_floor(treads):
    """Schematic orchestra polygon derived from the PROVISIONAL footprint:
    hull(P_opt deck, row-1 bands) minus deck minus all treads — replaces the
    stored zone whose boundary traces the inherited stage."""
    from shapely.geometry import shape, Polygon, mapping
    from shapely.ops import unary_union

    st, corners = provisional_corners()
    if st is None:
        return None
    deck = Polygon(corners)
    row1 = [shape(f["geometry"]) for f in treads if f["properties"]["row"] == 1]
    allt = unary_union([shape(f["geometry"]) for f in treads])
    floor = (unary_union([deck] + row1).convex_hull
             .difference(deck.buffer(0.1))
             .difference(allt.buffer(0.1)).simplify(0.25))
    return mapping(floor)


def stage_refit_overlay(ax):
    """Provisional P_opt footprint + axis arrow, if the study exists."""
    st, corners = provisional_corners()
    if st is None:
        return None
    sel = st["selected_placement"]
    P, az = sel["front_centre"], sel["axis_az"]
    xs, ys = zip(*corners)
    ax.fill(xs, ys, facecolor="#b9a48a", alpha=0.8, zorder=8)
    ax.plot(xs, ys, color="#7b241c", lw=1.6, ls=(0, (5, 3)), zorder=9)
    ex, ey = C.polar(55, az, P[0], P[1])
    ax.annotate("", xy=(ex, ey), xytext=(P[0], P[1]),
                arrowprops=dict(arrowstyle="-|>", color="#7b241c", lw=1.4))
    ax.annotate("PROVISIONAL stage footprint\n(P_opt — Rule 9 pending;\n"
                "see STAGE_SHAPE_STUDY.md)",
                (P[0], P[1]), textcoords="offset points", xytext=(12, -30),
                fontsize=7, color="#7b241c", fontweight="bold", zorder=10)
    return st


def board_01(mats, treads, zones, ctx, vps, D):
    fig = plt.figure(figsize=(16, 10), dpi=150)
    fig.suptitle("Board 01 — SITE FIT · three-section civic bowl in the Petoskey Pit",
                 fontsize=15, fontweight="bold")
    ax = fig.add_axes([0.03, 0.07, 0.55, 0.84])
    hillshade_base(ax, D)
    study = None
    show_inherited = not os.path.exists(
        os.path.join(C.REPO, "analysis", "in_situ_normalization",
                     "stage_typology_scores.json"))
    plan_geometry(ax, mats, treads, zones, ctx, vps,
                  show_stage=show_inherited,
                  floor_override=None if show_inherited
                  else provisional_floor(treads))
    rim = [f for f in ctx if f["properties"]["kind"] == "rim_arrival_edge"]
    streets = [f for f in ctx if f["properties"]["kind"] == "street_edge"]
    draw_layer(ax, streets, color="#555555", lw=1.0, ls="-.", zorder=3)
    if not show_inherited:
        study = stage_refit_overlay(ax)
    fmt_axes(ax, all_bounds([streets or rim]), pad=20)
    north_arrow(ax)
    section_legend(ax)
    ax.set_title("plan — east / bend (SE) / south families (normalized extents "
                 "= N0, asymmetry terrain-justified); ONLY the provisional "
                 "P_opt stage footprint shown — SCHEMATIC, Rule 9 decision "
                 "pending", fontsize=8.5)

    axc = fig.add_axes([0.61, 0.47, 0.36, 0.42])
    man_path = os.path.join(C.REPO, "dem", "in_situ_grading_manifest.json")
    if D is not None and D["cf"] is not None:
        v = np.nanmax(np.abs(D["cf"]))
        im = axc.imshow(np.where(D["cf"] == 0, np.nan, D["cf"]), cmap="RdBu_r",
                        vmin=-min(v, 4), vmax=min(v, 4), extent=D["extent"],
                        origin="upper", zorder=2)
        hillshade_base(axc, D)
        fmt_axes(axc, all_bounds([rim]), pad=40)
        fig.colorbar(im, ax=axc, shrink=0.7).set_label("cut(−)/fill(+) ft", fontsize=7)
        axc.set_title("cut / fill (1 ft grid)", fontsize=9)
    else:
        axc.axis("off")
        axc.text(0.5, 0.5, "cut/fill raster unavailable\n(see dem/MISSING_DATA.md)",
                 ha="center", va="center", fontsize=10, color="#884444")

    axt = fig.add_axes([0.61, 0.07, 0.36, 0.34])
    axt.axis("off")
    man = json.load(open(man_path)) if os.path.exists(man_path) else None
    seats = sum(f["properties"]["seats_kept"] for f in treads)
    lines = [
        "GOVERNING SCHEME — Scenario E three-section civic bowl",
        "· three terrain-fitted families: east / bend (SE) / south",
        "· rows 1-4 forecourt + 5 promenade hinge + 6-18 civic",
        "· rows 9-10 reclassified as the level cross-aisle (622.01)",
        f"· {seats:,} Band-A seats (validated on the restored surface)",
        "· no retaining walls · low seat edges ≤1.5 ft · swales to NE pour point",
        "· NO single fan declared — sections have separate local curvature",
        "· normalized extents = N0: east/south arc ratio 0.74, asymmetry",
        "  justified by seat-splay + street stops (NORMALIZATION.md)",
        "· stage: Rule 9 OPEN — plan shows ONLY the provisional P_opt",
        "  footprint (residual −6.7 ft / −6.3°, row-1 gaps ≥12 ft); element",
        "  menu + deltas + Rule 9 paths: STAGE_SHAPE_STUDY.md (A–E)",
        "· Scenario E validated earthwork: 500.8 CY gross (excl. stage)",
        "· NOT Claude-Design-ready until the stage decision lands",
    ]
    if man:
        lines.append(f"· raster model: fill {man['fill_cy_total']:.0f} CY · "
                     f"cut {man['cut_cy_total']:.0f} CY (manifest)")
    else:
        lines.append("· raster volumes pending DEM rebuild (dem/MISSING_DATA.md)")
    axt.text(0, 0.95, "\n".join(lines), fontsize=9.5, va="top", family="monospace")
    fig.text(0.5, 0.015, FOOT, ha="center", fontsize=7, color="#555555")
    out = os.path.join(BOARDS, "01_site_fit_board.png")
    fig.savefig(out, facecolor="white")
    plt.close(fig)
    print(f"  wrote {os.path.relpath(out, C.REPO)}")


def board_02(mats, treads, zones, ctx, vps, comp, D):
    fig = plt.figure(figsize=(16, 10), dpi=150)
    fig.suptitle("Board 02 — HUMAN EXPERIENCE · six stations through the bowl",
                 fontsize=15, fontweight="bold")
    axm = fig.add_axes([0.03, 0.52, 0.30, 0.38])
    hillshade_base(axm, D)
    plan_geometry(axm, mats, treads, zones, ctx)
    for i, f in enumerate(vps, 1):
        x, y = f["geometry"]["coordinates"]
        view_cone(axm, f, color="#c0392b", lw=0.7, alpha=0.6)
        axm.plot(x, y, "^", ms=8, color="#c0392b", mec="white", zorder=9)
        axm.annotate(str(i), (x, y), textcoords="offset points", xytext=(6, 5),
                     fontsize=8, fontweight="bold", color="#7b241c", zorder=10)
    rim = [f for f in ctx if f["properties"]["kind"] == "rim_arrival_edge"]
    fmt_axes(axm, all_bounds([rim]), pad=70)
    north_arrow(axm)
    axm.set_title("viewpoint stations (numbered)", fontsize=9)

    pos = [(0.36, 0.55, 0.20, 0.34), (0.575, 0.55, 0.20, 0.34), (0.79, 0.55, 0.20, 0.34),
           (0.36, 0.10, 0.20, 0.34), (0.575, 0.10, 0.20, 0.34), (0.79, 0.10, 0.20, 0.34)]
    for i, f in enumerate(vps):
        p = f["properties"]
        axv = fig.add_axes(pos[i])
        img_path = os.path.join(C.REPO, p["render_file"])
        if os.path.exists(img_path):
            axv.imshow(plt.imread(img_path))
        axv.set_xticks([]); axv.set_yticks([])
        req = " (REQUIRED)" if p["required"] else ""
        axv.set_title(f"{i + 1} · {p['name']}{req}", fontsize=7.5)

    axs = fig.add_axes([0.03, 0.10, 0.30, 0.36])
    axis_profile(axs, treads, comp, D)
    axs.set_title("bend-section axis profile + row-8 bay sightline", fontsize=8)

    axb = fig.add_axes([0.03, 0.015, 0.30, 0.055])
    cmm = {}
    for f in treads:
        p = f["properties"]
        if p["C_mm"] is not None:
            cmm.setdefault(p["section"], []).append((p["row"], p["C_mm"]))
    width = 0.27
    for j, s in enumerate(C.SECTIONS):
        rows = sorted(cmm.get(s, []))
        axb.bar([r + (j - 1) * width for r, _ in rows], [v for _, v in rows],
                width=width, color=SECTION_COLORS[s])
    axb.axhline(90, color="#c0392b", lw=0.7)
    axb.tick_params(labelsize=5)
    axb.text(1.01, 0.5, "C-value mm/row by section (red = 90)",
             transform=axb.transAxes, fontsize=6, va="center")
    fig.text(0.5, 0.0, FOOT, ha="center", fontsize=7, color="#555555")
    out = os.path.join(BOARDS, "02_experience_board.png")
    fig.savefig(out, facecolor="white")
    plt.close(fig)
    print(f"  wrote {os.path.relpath(out, C.REPO)}")


def board_03(mats, treads, zones, ctx, events, D):
    fig = plt.figure(figsize=(16, 10), dpi=150)
    fig.suptitle("Board 03 — LANDSCAPE CHARACTER · materials, water, seasons",
                 fontsize=15, fontweight="bold")
    ax = fig.add_axes([0.03, 0.09, 0.42, 0.80])
    hillshade_base(ax, D)
    plan_geometry(ax, mats, treads, zones, ctx, section_colors=False)
    rim = [f for f in ctx if f["properties"]["kind"] == "rim_arrival_edge"]
    fmt_axes(ax, all_bounds([rim]), pad=60)
    north_arrow(ax)
    ax.set_title("material zones (sections unified as turf terraces here — "
                 "see board 01 for family structure)", fontsize=8)
    handles = [Line2D([], [], marker="s", ls="", ms=9,
                      color=m["properties"].get("color_hint", MAT_FALLBACK),
                      label=f"{m['properties']['zone']}"
                            f"{' (schematic)' if m['properties'].get('schematic') else ''}")
               for m in mats]
    ax.legend(handles=handles, fontsize=6.5, loc="lower left", framealpha=0.85)

    by_mode = {}
    for f in events:
        by_mode.setdefault(f["properties"]["mode"], []).append(f)
    order = ["empty_park_day", "small_civic_ceremony", "movie_night",
             "amplified_concert", "festival_spillover", "winter_offseason"]
    pos = [(0.48, 0.55, 0.155, 0.32), (0.645, 0.55, 0.155, 0.32), (0.81, 0.55, 0.155, 0.32),
           (0.48, 0.17, 0.155, 0.32), (0.645, 0.17, 0.155, 0.32), (0.81, 0.17, 0.155, 0.32)]
    for i, mode in enumerate(order):
        axe = fig.add_axes(pos[i])
        hillshade_base(axe, D)
        plan_geometry(axe, mats, treads, zones, ctx, lw_scale=0.5,
                      section_colors=False)
        draw_layer(axe, by_mode.get(mode, []), facecolor="#e67e22",
                   edgecolor="#a04000", alpha=0.45, color="#a04000",
                   lw=1.2, ms=6, zorder=7)
        fmt_axes(axe, all_bounds([rim]), pad=30)
        axe.set_title(mode.replace("_", " "), fontsize=8)

    axt = fig.add_axes([0.48, 0.025, 0.49, 0.10])
    axt.axis("off")
    axt.text(0, 1.0,
             "WATER: the treatment cell is a DRY bioretention meadow — ephemeral "
             "ponding only after large storms, never a standing pool; flank swales "
             "carry runoff to the NE pour point. The water in this design is "
             "Little Traverse Bay, ~200 m NNW, seen over the low open stage.\n"
             "EVENT OVERLAYS are schematic and NONBINDING — temporary structures "
             "only; the movie screen rigs after sunset and strikes the same night.",
             fontsize=8.5, va="top", wrap=True)
    fig.text(0.5, 0.0, FOOT, ha="center", fontsize=7, color="#555555")
    out = os.path.join(BOARDS, "03_landscape_character_board.png")
    fig.savefig(out, facecolor="white")
    plt.close(fig)
    print(f"  wrote {os.path.relpath(out, C.REPO)}")


def main():
    layers = C.verify_against_design()
    comp = layers["comp"]
    os.makedirs(BOARDS, exist_ok=True)
    mats = load("material_zones.geojson")
    treads = load("terrace_treads.geojson")
    zones = load("bowl_zones.geojson")
    ctx = load("site_context.geojson")
    vps = load("in_situ_viewpoints.geojson")
    events = load("event_modes.geojson")
    D = dem_arrays()
    render_viewpoints(vps, mats, treads, zones, ctx, D)
    board_01(mats, treads, zones, ctx, vps, D)
    board_02(mats, treads, zones, ctx, vps, comp, D)
    board_03(mats, treads, zones, ctx, events, D)
    with open(os.path.join(BOARDS, "board_sources.json"), "w") as fh:
        json.dump({
            "governing_scheme": C.GOVERNING_SCHEME,
            "seating_source": "vectors_geojson/terrace_treads.geojson "
                              "(scenarioE formal_restored_tread)",
            "sections": list(C.SECTIONS),
            "single_fan_declared": False,
            "stage_rule9_status": C.STAGE_RULE9_STATUS,
            "claude_design_ready": False,
            "stage_refit_candidate": "P_opt (analysis/in_situ_normalization/"
                                     "stage_typology_scores.json) — candidate "
                                     "only, decision pending",
            "normalization": "N0 selected (analysis/in_situ_normalization/"
                             "section_balance.json)",
            "superseded_sources_excluded": list(C.SUPERSEDED_SCHEMES),
            "boards": ["01_site_fit_board.png", "02_experience_board.png",
                       "03_landscape_character_board.png"],
        }, fh, indent=1)
    print("  wrote boards/board_sources.json")


if __name__ == "__main__":
    main()
