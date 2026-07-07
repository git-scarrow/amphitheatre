#!/usr/bin/env python3
"""Human decision packet — post-emission seating-scope choice (Decision 1).

  boards/04_seating_options_comparison.png   same-scale plan triptych:
      Scenario E baseline / modest_normalization / ambitious (seating
      scope), each drawn from its EMITTED geometry
      (analysis/tier_emission/<tier>/geometry.geojson)
  boards/05_seating_options_section.png      true-scale bend-axis section
      showing what rows 19-20 add above the row-18 formal bowl
  analysis/decision_packet/decision_table.csv   compact decision table
  analysis/decision_packet/sources.json         provenance manifest

Source of truth: docs/POST_EMISSION_DECISION_MEMO.md and the emission
validation behind it (analysis/tier_emission/TIER_EMISSION_VALIDATION.md).
This script runs NO new sweeps — it reads the validation artifacts on disk
and asserts the memo's headline numbers before drawing anything.

Guardrails enforced here:
  * stage = inherited az-150 object, PROVISIONAL — Rule 9 carried_provisional
    (bundle adopted 2026-07-02, geometry NOT re-emitted): drawn
    dashed-outline-only in every panel, still the inherited object and not the
    adopted geometry
  * N1 east contour extension REJECTED on emission (0 of +149) — never drawn
  * the 1,665-seat figure is NOT validated — ambitious is quoted
    1,505 validated / +262

Deterministic output. Planning-grade. EPSG:6494, NAVD88 (Geoid12A) intl ft.
"""
import csv
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LightSource
from matplotlib.lines import Line2D

import human_scale_common as HS
import in_situ_common as C

BOARDS = os.path.join(C.REPO, "boards")
PACKET = os.path.join(C.REPO, "analysis", "decision_packet")
EMIT = os.path.join(C.REPO, "analysis", "tier_emission")

SECTION_COLORS = {"east": "#b08968", "bend": "#7fae6e", "south": "#5e8a9e"}
ROW19_COLOR = "#d35400"   # modest scope (row 19)
ROW20_COLOR = "#8e44ad"   # ambitious scope adds row 20
STAGE_COLOR = "#7b241c"

FOOT = ("PLANNING-GRADE / SCHEMATIC — not stamped engineering · EPSG:6494 · "
        "NAVD88 (Geoid12A) intl ft · source of truth: "
        "docs/POST_EMISSION_DECISION_MEMO.md + analysis/tier_emission/ "
        "(commit f6b1d96) · scripts/render_decision_packet.py")

GUARD = ("GUARDRAILS — dashed stage outline = INHERITED az-150 stage, PROVISIONAL: "
         "Rule 9 carried_provisional — bundle adopted 2026-07-02 (P_opt path-3 + "
         "path-4 wide-fan + five_facet_apron + T1_deck_only; Method B 2026-07-03), "
         "geometry NOT re-emitted so the drawn stage is still the inherited object, "
         "not resolved (re-emit + audit pending) · N1 east contour extension REJECTED on "
         "emission (0 of +149 seats survive) and is NOT drawn · 1,665 is NOT a "
         "validated seat count — ambitious is quoted 1,505 validated / +262 · "
         "increments are measured against the re-emitted baseline under the same "
         "strict per-segment validator")

# (directory, panel letter, display label)
TIERS = (
    ("Scenario_E_baseline_reemit", "A", "Scenario E baseline"),
    ("modest_normalization", "B", "modest_normalization"),
    ("ambitious_shaped_bowl_seating", "C", "ambitious (seating scope)"),
)


# ── data ─────────────────────────────────────────────────────────────────────

def load_tier(d):
    with open(os.path.join(EMIT, d, "geometry.geojson")) as fh:
        geom = json.load(fh)["features"]
    with open(os.path.join(EMIT, d, "validation.json")) as fh:
        val = json.load(fh)
    return geom, val


def headline_numbers(tiers):
    """Validated headline numbers, asserted against the controlling memo."""
    with open(os.path.join(EMIT, "_baseline_reconciliation.json")) as fh:
        recon = json.load(fh)
    base_a = tiers["Scenario_E_baseline_reemit"][1]["banded"]["A"]
    mod_a = tiers["modest_normalization"][1]["banded"]["A"]
    amb_a = tiers["ambitious_shaped_bowl_seating"][1]["banded"]["A"]
    mod_cy = tiers["modest_normalization"][1]["incremental"]["incr_gross_cy"]
    amb_cy = tiers["ambitious_shaped_bowl_seating"][1]["incremental"]["incr_gross_cy"]
    H = dict(
        base_a=int(round(base_a)), base_nom=1283,
        mod_a=int(round(mod_a)), mod_nom=1397, mod_d=int(round(mod_a - base_a)),
        amb_a=int(round(amb_a)), amb_nom=1516, amb_d=int(round(amb_a - base_a)),
        mod_cy=mod_cy, amb_cy=amb_cy,
        base_gross_cy=recon["reemit_total_cy"], base_drift=recon["baseline_drift_cy"],
    )
    # guard: refuse to draw if the on-disk artifacts drift from the memo's claims
    memo = dict(base_a=1243, mod_a=1357, mod_d=114, amb_a=1505, amb_d=262,
                mod_cy=25.3, amb_cy=47.3)
    bad = {k: (H[k], v) for k, v in memo.items() if H[k] != v}
    if bad:
        raise SystemExit(f"artifacts disagree with POST_EMISSION_DECISION_MEMO: {bad} "
                         "— re-validate before issuing a decision packet")
    return H


def load_zones():
    with open(os.path.join(C.VEC_DIR, "bowl_zones.geojson")) as fh:
        feats = json.load(fh)["features"]
    z = {}
    for f in feats:
        z.setdefault(f["properties"]["zone"], []).append(f)
    return z


def dem():
    if not os.path.exists(C.DEM_DESIGN):
        return None
    import rasterio

    ds = rasterio.open(C.DEM_DESIGN)
    A = ds.read(1).astype(float)
    A[A == ds.nodata] = np.nan
    b = ds.bounds
    return dict(dem=A, extent=(b.left, b.right, b.bottom, b.top),
                transform=ds.transform)


# ── drawing helpers ──────────────────────────────────────────────────────────

def draw_polys(ax, feats, **kw):
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path

    for f in feats:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        verts, codes = [], []
        for rings in polys:
            for ring in rings:
                verts.extend(ring)
                codes.extend([Path.MOVETO] + [Path.LINETO] * (len(ring) - 2)
                             + [Path.CLOSEPOLY])
        ax.add_patch(PathPatch(Path(verts, codes), **kw))


def draw_lines(ax, feats, **kw):
    for f in feats:
        g = f["geometry"]
        lines = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        if g["type"] in ("LineString", "MultiLineString"):
            for ln in lines:
                xs, ys = zip(*ln)
                ax.plot(xs, ys, **kw)


def bounds_of(featsets, pad=0.0):
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


def hillshade(ax, D):
    if D is None:
        ax.set_facecolor("#eeece6")
        return
    ls = LightSource(azdeg=315, altdeg=45)
    hs = ls.hillshade(np.where(np.isfinite(D["dem"]), D["dem"],
                               np.nanmedian(D["dem"])), vert_exag=2, dx=1, dy=1)
    ax.imshow(hs, cmap="gray", extent=D["extent"], origin="upper",
              alpha=0.8, zorder=0)


def tier_panel(ax, geom, zones, D, bnds):
    hillshade(ax, D)
    draw_polys(ax, zones.get("treatment_cell_landscape", []),
               facecolor="#cfe0cf", edgecolor="none", alpha=0.5, zorder=1)
    draw_polys(ax, zones.get("orchestra_event_floor", []),
               facecolor="#e3dcc8", edgecolor="none", alpha=0.5, zorder=1)
    draw_polys(ax, zones.get("promenade_hinge", []),
               facecolor="#d9cfa3", edgecolor="none", alpha=0.7, zorder=2)
    for f in geom:
        p = f["properties"]
        if p.get("role") == "formal_restored_tread":
            draw_polys(ax, [f], facecolor=SECTION_COLORS[p["section"]],
                       edgecolor="white", lw=0.2, alpha=0.9, zorder=3)
        elif p.get("role") == "tier_promoted_tread":
            fc = ROW19_COLOR if p["row"] == 19 else ROW20_COLOR
            draw_polys(ax, [f], facecolor=fc, edgecolor="white",
                       lw=0.3, alpha=0.95, zorder=4)
        elif p.get("role") == "cross_aisle":
            draw_polys(ax, [f], facecolor="#d9cfa3", edgecolor="#8a7d54",
                       lw=0.5, alpha=0.95, zorder=4)
        elif p.get("role") == "ada_ramp":
            draw_polys(ax, [f], facecolor="#9aa9b5", edgecolor="#5d6d7a",
                       lw=0.4, alpha=0.9, zorder=4)
        elif p.get("role") == "drainage_swale":
            draw_polys(ax, [f], facecolor="none", edgecolor="#2e86ab",
                       lw=0.8, ls=":", alpha=0.9, zorder=4)
    for f in zones.get("hinge_ray", []):
        draw_lines(ax, [f], color=STAGE_COLOR, lw=0.8, ls=(0, (4, 3)),
                   alpha=0.8, zorder=5)
    # stage: INHERITED object, dashed outline only — PROVISIONAL, Rule 9 carried_provisional (geometry not re-emitted)
    for z in ("stage_core", "stage_shoulder_left", "stage_shoulder_right"):
        draw_polys(ax, zones.get(z, []), facecolor="none",
                   edgecolor=STAGE_COLOR, lw=1.4, ls=(0, (5, 3)), zorder=6)
    ax.set_aspect("equal")
    ax.set_xlim(bnds[0], bnds[2])
    ax.set_ylim(bnds[1], bnds[3])
    ax.set_xticks([]); ax.set_yticks([])


def scalebar(ax, bnds):
    x0 = bnds[0] + 0.05 * (bnds[2] - bnds[0])
    y0 = bnds[1] + 0.05 * (bnds[3] - bnds[1])
    ax.plot([x0, x0 + 50], [y0, y0], color="k", lw=2, zorder=9)
    ax.text(x0 + 25, y0 + 4, "50 ft", ha="center", fontsize=6.5, zorder=9)


# ── board 04: same-scale plan triptych ───────────────────────────────────────

def board_04(tiers, H, zones, D):
    all_feats = [g for g, _ in tiers.values()]
    stage = sum((zones.get(z, []) for z in
                 ("stage_core", "stage_shoulder_left", "stage_shoulder_right")), [])
    bnds = bounds_of(all_feats + [stage], pad=28)

    fig = plt.figure(figsize=(16.5, 8.2), dpi=150)
    fig.suptitle("Board 04 — SEATING-SCOPE DECISION · the three validated options, "
                 "same scale, emitted geometry", fontsize=14, fontweight="bold")
    sub = {
        "A": (f"{H['base_a']:,} Band-A validated ({H['base_nom']:,} nominal)\n"
              f"{H['base_gross_cy']} CY gross (re-emit drift "
              f"{H['base_drift']:+.1f}) · ACCEPTED control — fallback regardless"),
        "B": (f"+{H['mod_d']} seats → {H['mod_a']:,} validated "
              f"({H['mod_nom']:,} nominal)\n+{H['mod_cy']} CY incremental · "
              "EMITTED + VALIDATED — all hard gates pass"),
        "C": (f"+{H['amb_d']} seats → {H['amb_a']:,} validated "
              f"({H['amb_nom']:,} nominal)\n+{H['amb_cy']} CY incremental · "
              "EMITTED + VALIDATED — all hard gates pass"),
    }
    for i, (d, letter, label) in enumerate(TIERS):
        ax = fig.add_axes([0.025 + i * 0.325, 0.17, 0.31, 0.70])
        tier_panel(ax, tiers[d][0], zones, D, bnds)
        scalebar(ax, bnds)
        if i == 0:
            ax.annotate("N", xy=(0.95, 0.95), xytext=(0.95, 0.86),
                        xycoords="axes fraction", ha="center", fontsize=9,
                        arrowprops=dict(arrowstyle="-|>", color="k"))
            sc = next(f for f in zones["stage_core"])
            sx = np.mean([c[0] for c in sc["geometry"]["coordinates"][0]])
            sy = np.mean([c[1] for c in sc["geometry"]["coordinates"][0]])
            ax.annotate("stage: PROVISIONAL\n(inherited az-150 — Rule 9 carried_provisional)",
                        (sx, sy), textcoords="offset points", xytext=(-8, 34),
                        fontsize=7, color=STAGE_COLOR, fontweight="bold",
                        ha="center", zorder=10)
        if letter == "C":
            ax.text(0.985, 0.015,
                    "east march stops at the az-85 cap —\n"
                    "N1 extension REJECTED on emission (0 of +149), not drawn",
                    transform=ax.transAxes, fontsize=6.5, color="#884444",
                    ha="right", va="bottom", zorder=10)
        ax.set_title(f"{letter} — {label}\n{sub[letter]}", fontsize=9)

    handles = [
        Line2D([], [], marker="s", ls="", ms=8, color=SECTION_COLORS["east"],
               label="east family (rows 1–18)"),
        Line2D([], [], marker="s", ls="", ms=8, color=SECTION_COLORS["bend"],
               label="bend (SE) family"),
        Line2D([], [], marker="s", ls="", ms=8, color=SECTION_COLORS["south"],
               label="south family"),
        Line2D([], [], marker="s", ls="", ms=8, color=ROW19_COLOR,
               label="row 19 promoted (modest + ambitious)"),
        Line2D([], [], marker="s", ls="", ms=8, color=ROW20_COLOR,
               label="row 20 promoted (ambitious only)"),
        Line2D([], [], marker="s", ls="", ms=8, color="#d9cfa3",
               label="cross-aisle / promenade hinge"),
        Line2D([], [], marker="s", ls="", ms=8, color="#9aa9b5", label="ADA ramps"),
        Line2D([], [], color="#2e86ab", ls=":", label="drainage swales"),
        Line2D([], [], color=STAGE_COLOR, ls=(0, (5, 3)),
               label="inherited stage — PROVISIONAL (Rule 9 carried_provisional)"),
        Line2D([], [], color=STAGE_COLOR, ls=(0, (4, 3)), lw=0.8,
               label="hinge ray (section transition — no single fan)"),
    ]
    fig.legend(handles=handles, fontsize=7, loc="lower center", ncol=5,
               bbox_to_anchor=(0.5, 0.075), framealpha=0.9)
    fig.text(0.5, 0.048, GUARD, ha="center", fontsize=7, color="#7b241c", wrap=True)
    fig.text(0.5, 0.012, FOOT, ha="center", fontsize=7, color="#555555")
    out = os.path.join(BOARDS, "04_seating_options_comparison.png")
    fig.savefig(out, facecolor="white")
    plt.close(fig)
    print(f"  wrote {os.path.relpath(out, C.REPO)}")


# ── board 05: true-scale bend-axis section ───────────────────────────────────

def load_human_section_refs():
    """Human-scale refs flagged for the board-05 section, from the source
    layer (vectors_geojson/human_scale_refs.geojson) — never hand-placed."""
    path = os.path.join(C.REPO, HS.REFS_PATH)
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        feats = json.load(fh)["features"]
    return [f for f in feats
            if f["properties"]["type"] == "human"
            and "board05_section" in f["properties"].get("view_context", [])]


def board_05(tiers, H, D):
    comp = C.load_composition()
    bend18 = [(float(comp[(r, "bend")]["axis_radius_ft"]),
               float(comp[(r, "bend")]["elev"])) for r in C.FORMAL_ROWS]
    promoted = {}
    for f in tiers["ambitious_shaped_bowl_seating"][0]:
        p = f["properties"]
        if p.get("role") == "tier_promoted_tread" and p["section"] == "bend":
            promoted[p["row"]] = (float(comp[(p["row"], "bend")]["axis_radius_ft"]),
                                  p["design_elev"])

    fig = plt.figure(figsize=(16.5, 7.2), dpi=150)
    fig.suptitle("Board 05 — SECTION · what rows 19–20 add "
                 "(bend-section axis az 132, TRUE SCALE 1:1)",
                 fontsize=14, fontweight="bold")

    ax = fig.add_axes([0.05, 0.40, 0.92, 0.46])
    if D is not None:
        import rasterio

        s = np.linspace(-70, 215, 580)
        xs = C.FX + np.sin(np.radians(C.AX_AZ)) * s
        ys = C.FY + np.cos(np.radians(C.AX_AZ)) * s
        rr, cc = rasterio.transform.rowcol(D["transform"], xs, ys)
        rr = np.clip(rr, 0, D["dem"].shape[0] - 1)
        cc = np.clip(cc, 0, D["dem"].shape[1] - 1)
        ax.plot(s, D["dem"][rr, cc], color="#7a6a55", lw=1.0,
                label="existing ground (DEM, az-132 axis)")
    for R, e in bend18:
        ax.plot([R - 1.8, R + 1.8], [e, e], color=SECTION_COLORS["bend"], lw=2.6)
    ax.plot([], [], color=SECTION_COLORS["bend"], lw=2.6,
            label="Scenario E formal rows 1–18 (baseline, 1,243 validated)")
    pr, pe = 101.8, float(comp[(5, "bend")]["elev"])
    ax.plot([pr - 4, pr + 4], [pe, pe], color="#d9cfa3", lw=3.4,
            label="row-5 promenade hinge")
    ax.plot([117.1 - 4, 121.4 + 4], [C.AISLE_ELEV] * 2, color="#8a7d54", lw=3.4,
            label="cross-aisle (rows 9–10) 622.01")
    R19, e19 = promoted[19]
    R20, e20 = promoted[20]
    ax.plot([R19 - 1.8, R19 + 1.8], [e19, e19], color=ROW19_COLOR, lw=3.2,
            label=f"row 19 promoted — MODEST scope (+{H['mod_d']} validated)")
    ax.plot([R20 - 1.8, R20 + 1.8], [e20, e20], color=ROW20_COLOR, lw=3.2,
            label=f"row 20 promoted — AMBITIOUS scope (+{H['amb_d']} validated, "
                  "incl. comfort regrades)")
    ax.plot([16, 50], [C.FOCUS_ELEV] * 2, color=STAGE_COLOR, lw=2.6, ls=(0, (5, 3)),
            label="inherited stage deck 612.5 — PROVISIONAL (Rule 9 carried_provisional)")
    ax.axhline(618.5, color="#1f77b4", lw=0.7, ls="--", alpha=0.7,
               label="flat NW rim silhouette 618.5 (bay-view check datum)")
    # human-scale figures from the source layer, drawn 1:1 (audited)
    hs_records = []
    for f in load_human_section_refs():
        p = dict(f["properties"])
        st = HS.section_station(p["ref_id"], f["geometry"]["coordinates"], comp)
        if st is None:
            continue
        if p["ref_id"] == "ambitious_row20_seated":
            st = R20 - 1.2          # snap to the promoted row-20 station
            p["ground_elev_navd88"] = e20
        hs_records.append(HS.draw_section_figure(ax, p, st, "05_section"))
    ax.plot([], [], marker="s", ls="", color=HS.FIG_FILL["standing"],
            label="human-scale refs, 1:1 (human_scale_refs.geojson — incl. "
                  "wheelchair on the cross-aisle, seated on row 20)")

    eye = e20 + C.EYE_SEATED_FT
    ax.annotate("", xy=(-65, 618.5), xytext=(R20, eye),
                arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=1.1, alpha=0.85))
    ax.text(-62, 623.5, f"row-20 seated eye {eye:.1f} ft ≫ 618.5 rim —\n"
                        "bay + sky backdrop preserved (validation F5)",
            fontsize=7.5, color="#1f77b4")
    ax.set_aspect("equal")
    ax.set_xlim(-70, 215)
    ax.set_ylim(604, 648)
    ax.set_xlabel("ft along bend-section axis from origin (− = NNW toward bay)",
                  fontsize=8)
    ax.set_ylabel("ft NAVD88", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=6.5, loc="upper left", ncol=2, framealpha=0.9)
    ax.grid(alpha=0.2)

    # detail inset — rows 16-20, also true scale
    axz = fig.add_axes([0.625, 0.115, 0.35, 0.24])
    for R, e in bend18:
        if R >= 145:
            axz.plot([R - 1.8, R + 1.8], [e, e], color=SECTION_COLORS["bend"], lw=3.5)
    axz.plot([R19 - 1.8, R19 + 1.8], [e19, e19], color=ROW19_COLOR, lw=4)
    axz.plot([R20 - 1.8, R20 + 1.8], [e20, e20], color=ROW20_COLOR, lw=4)
    r18R, r18e = bend18[-1]
    axz.annotate(f"riser {e19 - r18e:.1f} ft", ((r18R + R19) / 2, (r18e + e19) / 2),
                 textcoords="offset points", xytext=(-4, 9), fontsize=7,
                 ha="right", color=ROW19_COLOR)
    axz.annotate(f"riser {e20 - e19:.1f} ft", ((R19 + R20) / 2, (e19 + e20) / 2),
                 textcoords="offset points", xytext=(-4, 9), fontsize=7,
                 ha="right", color=ROW20_COLOR)
    for R, e, t, c in ((r18R, r18e, "r18", SECTION_COLORS["bend"]),
                       (R19, e19, "r19", ROW19_COLOR), (R20, e20, "r20", ROW20_COLOR)):
        axz.text(R, e - 1.0, t, ha="center", fontsize=7, color=c)
    axz.set_aspect("equal")
    axz.set_xlim(144, 174)
    axz.set_ylim(628, 640)
    axz.tick_params(labelsize=6.5)
    axz.grid(alpha=0.2)
    axz.set_title("detail: rows 16–20 (true scale) — promoted rows continue the "
                  "natural rake; max incr. depths 0.95 cut / 1.59 fill ft, "
                  "no wall trigger", fontsize=7.5)

    fig.text(0.05, 0.31,
             "What the promotions are: the same 3.6-ft treads continued up the\n"
             "already-validated rake — no new typology, no walls (max incremental\n"
             "depths 0.95 ft cut / 1.59 ft fill, well under the 3-ft trigger).\n"
             "MODEST = row 19 in all three families (+114 validated, +25.3 CY).\n"
             "AMBITIOUS = rows 19–20 plus the 100-mm comfort regrade of rows\n"
             "11–18 (+262 validated, +47.3 CY) — the regrade also heals the\n"
             "baseline's soft south r18. All elevations are the EMITTED design\n"
             "planes; the bend family is drawn — east/south carry the same\n"
             "promotions at their own curvature (no single fan).",
             fontsize=8, va="top", ha="left",
             bbox=dict(facecolor="#f4f1ea", edgecolor="#cccccc"))
    fig.text(0.5, 0.045, GUARD, ha="center", fontsize=7, color="#7b241c", wrap=True)
    fig.text(0.5, 0.012, FOOT, ha="center", fontsize=7, color="#555555")
    out = os.path.join(BOARDS, "05_seating_options_section.png")
    fig.savefig(out, facecolor="white")
    plt.close(fig)
    print(f"  wrote {os.path.relpath(out, C.REPO)}")
    return hs_records


# ── decision table + provenance ──────────────────────────────────────────────

STAGE_STATUS = ("Rule 9 carried_provisional — inherited az-150 stage drawn "
                "PROVISIONAL (geometry NOT re-emitted); bundle adopted 2026-07-02 "
                "(P_opt path-3 + path-4 wide-fan + five_facet_apron + T1_deck_only; "
                "Method B 2026-07-03), not resolved (re-emit + audit pending)")


def decision_table(H):
    os.makedirs(PACKET, exist_ok=True)
    rows = [
        ["A", "Scenario E baseline", H["base_a"], H["base_nom"], 0, 0.0,
         "ACCEPTED control (seating/ADA/drainage); re-emits at 500.8 CY, "
         "drift +0.0 vs locked earthwork.csv",
         STAGE_STATUS,
         "Fallback regardless of the decision; choose if no further "
         "earthwork is wanted"],
        ["B", "modest_normalization (seating)", H["mod_a"], H["mod_nom"],
         H["mod_d"], H["mod_cy"],
         "EMITTED + VALIDATED 2026-06-11, all hard gates pass "
         "(recipe cut cap 1.25 ft with provenance); +114 claim validated in full",
         STAGE_STATUS,
         "Cheapest validated step if any expansion is funded"],
        ["C", "ambitious_shaped_bowl (seating scope)", H["amb_a"], H["amb_nom"],
         H["amb_d"], H["amb_cy"],
         "EMITTED + VALIDATED 2026-06-11, all hard gates pass; quote +262/1,505 "
         "(NOT 1,665 — N1 east extension REJECTED on emission, 0 of +149 survive)",
         STAGE_STATUS,
         "Validated Pareto knee — recommended scope if budget allows; "
         "Pareto ordering unchanged by the CY restatement"],
    ]
    out = os.path.join(PACKET, "decision_table.csv")
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["option", "label", "band_a_validated_seats", "nominal_seats",
                    "delta_seats_vs_baseline", "incremental_earthwork_cy",
                    "validation_status", "stage_status", "recommended_posture"])
        w.writerows(rows)
    print(f"  wrote {os.path.relpath(out, C.REPO)}")


def provenance(H, hs_records=None):
    out = os.path.join(PACKET, "sources.json")
    with open(out, "w") as fh:
        json.dump({
            "human_scale": {
                "source": "vectors_geojson/human_scale_refs.geojson",
                "policy": "board-05 figures drawn 1:1 from the source layer "
                          "(vertical extent = height_ft); none hand-drawn",
                "figures": hs_records or [],
                "wheelchair_figures": [r["ref_id"] for r in hs_records or []
                                       if r["posture"] == "wheelchair"],
            },
            "controlling_memo": "docs/POST_EMISSION_DECISION_MEMO.md",
            "emission_validation": "analysis/tier_emission/TIER_EMISSION_VALIDATION.md"
                                   " (commit f6b1d96)",
            "geometry_inputs": [f"analysis/tier_emission/{d}/geometry.geojson"
                                for d, _, _ in TIERS],
            "validation_inputs": [f"analysis/tier_emission/{d}/validation.json"
                                  for d, _, _ in TIERS]
                                 + ["analysis/tier_emission/"
                                    "_baseline_reconciliation.json"],
            "context_inputs": ["vectors_geojson/bowl_zones.geojson",
                               "design_extended_bays/composition_table.csv",
                               "dem/dem_design_1ft.tif"],
            "headline_numbers_asserted": H,
            "stage_rule9_status": ("open (geometry — drawn PROVISIONAL in all "
                                   "visuals); decision carried_provisional 2026-07-02 "
                                   "(bundle P_opt path-3 + path-4 wide-fan + "
                                   "five_facet_apron + T1_deck_only; Method B "
                                   "2026-07-03) — not resolved (re-emit + audit pending)"),
            "n1_east_extension": "REJECTED on emission (0 of +149) — never drawn",
            "claim_1665": "not live — ambitious quoted 1,505 validated / +262",
            "outputs": ["docs/HUMAN_DECISION_BRIEF.md",
                        "boards/04_seating_options_comparison.png",
                        "boards/05_seating_options_section.png",
                        "analysis/decision_packet/decision_table.csv"],
            "script": "scripts/render_decision_packet.py",
        }, fh, indent=1)
    print(f"  wrote {os.path.relpath(out, C.REPO)}")


def main():
    tiers = {d: load_tier(d) for d, _, _ in TIERS}
    H = headline_numbers(tiers)
    zones = load_zones()
    D = dem()
    os.makedirs(BOARDS, exist_ok=True)
    board_04(tiers, H, zones, D)
    hs_records = board_05(tiers, H, D)
    decision_table(H)
    provenance(H, hs_records)


if __name__ == "__main__":
    main()
