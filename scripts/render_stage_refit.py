"""Render stage refit sweep visualisations.

Produces four panels in analysis/stage_refit/:
  plan_alignment.png     — hillshade plan: current stage, top candidate, audience centroid,
                           design axis (150°) vs audience axis (124°), per-section centroids
  sweep_matrix.png       — grid heat-map: angular mismatch and min-C for all candidates
  sightline_sensitivity.png — min C vs candidate (ranked by mismatch)
  fan_diagram.png        — polar fan: section bearings and angular extents from each candidate SF
"""
from __future__ import annotations
import csv, json, math, os, sys
from pathlib import Path

import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.colors import Normalize, LinearSegmentedColormap
from matplotlib.cm import ScalarMappable
from matplotlib.patches import FancyArrowPatch
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = Path(__file__).parent.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT / "scripts"))
from harness.project import ProjectState

STATE = ProjectState.load("harness_config.yaml")
TF = STATE.transform; Z = STATE.Z0

OUT = ROOT / "analysis" / "stage_refit"
OUT.mkdir(parents=True, exist_ok=True)

# ── constants ─────────────────────────────────────────────────────────────────
FX, FY        = 19533075.2, 750786.21
SF_ORIG       = (19533100.2, 750742.91)
AX_AZ_ORIG    = 150.0
AUD_CX, AUD_CY = 19533143.2, 750713.5
TOTAL_SEATS   = 1283
TRUE_AUD_AZ   = 124.4   # bearing from SF to audience centroid
FAN_HALF      = 55.0
C_GATE_MM     = 90.0

# ── geometry ──────────────────────────────────────────────────────────────────
GJ  = json.loads((ROOT / "analysis/scenarioE_civic/geometry.geojson").read_text())
CANDS = list(csv.DictReader(open(OUT / "stage_refit_candidates.csv")))

# ── helpers ───────────────────────────────────────────────────────────────────
def to_px(x, y):
    col = (x - TF.c) / TF.a
    row = (y - TF.f) / TF.e
    return col, row

def arc_pt(R, az_deg):
    a = math.radians(az_deg)
    return FX + math.sin(a) * R, FY + math.cos(a) * R

def make_stage_verts(sfx, sfy, ax_az, width=70, depth=34):
    fwd   = np.array([math.sin(math.radians(ax_az)), math.cos(math.radians(ax_az))])
    right = np.array([math.sin(math.radians(ax_az + 90)), math.cos(math.radians(ax_az + 90))])
    fl = np.array([sfx, sfy]) - right * (width / 2)
    fr = np.array([sfx, sfy]) + right * (width / 2)
    br = fr - fwd * depth
    bl = fl - fwd * depth
    return np.array([fl, fr, br, bl, fl])

def bearing_ray(sfx, sfy, az_deg, length=200):
    a = math.radians(az_deg)
    return [(sfx, sfy), (sfx + math.sin(a) * length, sfy + math.cos(a) * length)]

def px_ray(sfx, sfy, az_deg, length=200):
    pts = bearing_ray(sfx, sfy, az_deg, length)
    return [to_px(*p) for p in pts]

# ── hillshade base ─────────────────────────────────────────────────────────────
gy, gx = np.gradient(np.where(np.isfinite(Z), Z, np.nan))
shade = np.clip(0.5 - (gx + gy) * 0.7, 0, 1)

# ── per-section data ──────────────────────────────────────────────────────────
SEC_CENTS = {
    "east":  (19533190.47, 750766.44, 365),
    "bend":  (19533165.66, 750702.75, 419),
    "south": (19533089.68, 750683.74, 499),
}
SEC_COL = {"east": "#e67e22", "bend": "#27ae60", "south": "#8e44ad"}

# ── tread polygons grouped by section ─────────────────────────────────────────
sec_polys = {"east": [], "bend": [], "south": []}
for f in GJ["features"]:
    if f["properties"].get("role") != "formal_restored_tread":
        continue
    row = int(f["properties"]["row"])
    sec = f["properties"]["section"]
    seats = int(f["properties"].get("seats_kept", 0))
    if row <= 18 and seats > 0 and sec in sec_polys:
        sec_polys[sec].append(shape(f["geometry"]))

stage_poly_orig_shp = next(
    shape(f["geometry"]) for f in GJ["features"]
    if f["properties"].get("role") == "stage_surface"
    and f["properties"].get("name") == "stage"
)

# candidates ranked by score for top-8 label
def score_c(c):
    return (abs(float(c["ang_mismatch"])) / 26.0
            + 0.5 * abs(float(c["lat_off_aud"])) / 30.0
            + abs(float(c["bay_view_delta"])) / 26.0)

feasible = [c for c in CANDS
            if c["all_c_pass"] == "True"
            and "ADA" not in c["ada_swale"]
            and c["bay_blocked"] == "False"]
feasible.sort(key=score_c)
best = feasible[0] if feasible else None

# ── view bbox ─────────────────────────────────────────────────────────────────
all_shapes = [s for polys in sec_polys.values() for s in polys] + [stage_poly_orig_shp]
b = unary_union(all_shapes).bounds   # (minx, miny, maxx, maxy)
margin = 50
c0, r0 = to_px(b[0] - margin, b[3] + margin)
c1, r1 = to_px(b[2] + margin, b[1] - margin)
c0, c1 = int(min(c0,c1)), int(max(c0,c1))
r0, r1 = int(min(r0,r1)), int(max(r0,r1))

# ════════════════════════════════════════════════════════════════════════════
# Figure 1 — Plan alignment
# ════════════════════════════════════════════════════════════════════════════
fig1, ax1 = plt.subplots(figsize=(13, 12))
ax1.imshow(shade, cmap="gray", alpha=0.6)

# Tread sections
sec_alpha = {"east": 0.55, "bend": 0.55, "south": 0.55}
for sec, polys in sec_polys.items():
    col = SEC_COL[sec]
    for poly in polys:
        xs, ys = poly.exterior.xy
        cc = [to_px(x, y)[0] for x, y in zip(xs, ys)]
        rr = [to_px(x, y)[1] for x, y in zip(xs, ys)]
        ax1.fill(cc, rr, color=col, alpha=sec_alpha[sec], ec="white", lw=0.2)

# Current stage (solid grey fill + thick border)
vs_orig = make_stage_verts(SF_ORIG[0], SF_ORIG[1], AX_AZ_ORIG)
px_orig = [to_px(x, y) for x, y in vs_orig]
ax1.fill([p[0] for p in px_orig], [p[1] for p in px_orig],
         color="#636363", alpha=0.85, ec="#1a1a1a", lw=1.8, zorder=5, label="Current stage (az 150°)")

# Best candidate stage (outlined only, dashed)
if best:
    bsfx, bsfy = float(best["sfx"]), float(best["sfy"])
    baz = float(best["ax_az"])
    vs_best = make_stage_verts(bsfx, bsfy, baz)
    px_best = [to_px(x, y) for x, y in vs_best]
    ax1.fill([p[0] for p in px_best], [p[1] for p in px_best],
             color="#e74c3c", alpha=0.25, ec="#e74c3c", lw=2.0, ls="--", zorder=5,
             label=f"Best candidate ({best['id']}, az {baz:.0f}°, lat {float(best['lat_offset']):+.0f} ft)")

# ── Axis rays ──────────────────────────────────────────────────────────────
ray_len = 130
# Design axis 150° from current SF
r = px_ray(SF_ORIG[0], SF_ORIG[1], AX_AZ_ORIG, ray_len)
ax1.annotate("", xy=r[1], xytext=r[0],
             arrowprops=dict(arrowstyle="-|>", color="#636363", lw=2.0),
             zorder=8)
ax1.text(r[1][0] + 2, r[1][1] + 2, f"design axis\n150°", fontsize=8,
         color="#444", ha="left", va="top", zorder=9)

# True audience axis from current SF (124°)
r2 = px_ray(SF_ORIG[0], SF_ORIG[1], TRUE_AUD_AZ, ray_len)
ax1.annotate("", xy=r2[1], xytext=r2[0],
             arrowprops=dict(arrowstyle="-|>", color="#c0392b", lw=2.0),
             zorder=8)
ax1.text(r2[1][0] + 2, r2[1][1] + 2, f"audience axis\n{TRUE_AUD_AZ:.0f}°", fontsize=8,
         color="#c0392b", ha="left", va="top", zorder=9)

# Best candidate axis from its SF
if best:
    r3 = px_ray(bsfx, bsfy, baz, ray_len)
    ax1.annotate("", xy=r3[1], xytext=r3[0],
                 arrowprops=dict(arrowstyle="-|>", color="#e74c3c", lw=1.4, ls="dashed"),
                 zorder=8)

# Bay view axis arrow from arc centre (330° direction)
bv_start = to_px(FX, FY)
bv_end   = to_px(*arc_pt(160, 330))
ax1.annotate("", xy=bv_end, xytext=bv_start,
             arrowprops=dict(arrowstyle="-|>", color="#2980b9", lw=1.8, ls=(0,(3,2))),
             zorder=8)
ax1.text(bv_end[0] + 2, bv_end[1] - 4, "bay view\n330°", fontsize=8,
         color="#2980b9", ha="left", va="bottom", zorder=9)

# ── Points ─────────────────────────────────────────────────────────────────
# Arc centre F
fpx = to_px(FX, FY)
ax1.plot(*fpx, "k+", ms=10, mew=2, zorder=10)
ax1.text(fpx[0] + 3, fpx[1] - 3, "arc ctr F", fontsize=8, color="k", zorder=11)

# Current SF
sfpx = to_px(SF_ORIG[0], SF_ORIG[1])
ax1.plot(*sfpx, "s", color="#636363", ms=8, zorder=10)
ax1.text(sfpx[0] + 3, sfpx[1] - 3, "SF (current)", fontsize=8, color="#444", zorder=11)

# Best SF
if best:
    bpx = to_px(bsfx, bsfy)
    ax1.plot(*bpx, "s", color="#e74c3c", ms=8, zorder=10)
    ax1.text(bpx[0] + 3, bpx[1] - 3, f"SF ({best['id']})", fontsize=8, color="#e74c3c", zorder=11)

# Audience centroid star
apx = to_px(AUD_CX, AUD_CY)
ax1.plot(*apx, "*", color="gold", ms=16, mec="#333", mew=1, zorder=10,
         label=f"Seat-weighted audience centroid ({TOTAL_SEATS} seats)")
ax1.text(apx[0] + 3, apx[1] - 3, "audience\ncentroid", fontsize=8, color="#333", zorder=11)

# Per-section centroids
for sec, (cx, cy, s) in SEC_CENTS.items():
    px = to_px(cx, cy)
    ax1.plot(*px, "o", color=SEC_COL[sec], ms=10, mec="w", mew=1.2, zorder=10)
    ax1.text(px[0] + 3, px[1] - 3, f"{sec}\n({s})", fontsize=8,
             color=SEC_COL[sec], fontweight="bold", zorder=11)

# ── ±55° fan arcs from current SF (dashed grey) ───────────────────────────
for side in [-1, 1]:
    az = AX_AZ_ORIG + side * FAN_HALF
    r_fan = px_ray(SF_ORIG[0], SF_ORIG[1], az, 200)
    ax1.plot([p[0] for p in r_fan], [p[1] for p in r_fan],
             color="#999", lw=1.0, ls=":", zorder=4)

# ── Mismatch arc (between 124° and 150° rays) ─────────────────────────────
# Draw a circular arc segment at radius ~60 px from SF to show the 26° gap
arc_r_px = 55
center_px = sfpx
angles_deg = np.linspace(TRUE_AUD_AZ, AX_AZ_ORIG, 30)
arc_xs = [center_px[0] + arc_r_px * math.sin(math.radians(a)) for a in angles_deg]
arc_ys = [center_px[1] - arc_r_px * math.cos(math.radians(a)) for a in angles_deg]
ax1.plot(arc_xs, arc_ys, color="#c0392b", lw=2.0, zorder=9)
mid_az = (TRUE_AUD_AZ + AX_AZ_ORIG) / 2
mid_px = (center_px[0] + (arc_r_px + 8) * math.sin(math.radians(mid_az)),
          center_px[1] - (arc_r_px + 8) * math.cos(math.radians(mid_az)))
ax1.text(mid_px[0], mid_px[1], "26°\nmismatch", fontsize=8, color="#c0392b",
         ha="center", va="center", zorder=9,
         bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8, ec="none"))

ax1.set_xlim(c0, c1); ax1.set_ylim(r1, r0)
ax1.set_xticks([]); ax1.set_yticks([])
ax1.set_title(
    "Stage alignment audit — Scenario E validated seating\n"
    "Grey: current stage (az 150°) · Red dashed: best refit candidate · "
    "★: seat-weighted centroid · Sections: east/bend/south",
    fontsize=11
)
best_label = (f"Best candidate: {best['id']}  |  mismatch {float(best['ang_mismatch']):+.0f}°  "
              f"|  C_min {float(best['min_c_mm']):.0f} mm  |  bay Δ {float(best['bay_view_delta']):+.0f}°  "
              f"|  EW Δ {float(best['earthwork_delta_cy'])} CY"
              if best else "no feasible candidates")
ax1.text(0.02, 0.02, best_label, transform=ax1.transAxes,
         fontsize=9, va="bottom", ha="left",
         bbox=dict(boxstyle="round,pad=0.4", fc="white", alpha=0.92, ec="#999"))
handles, labels = ax1.get_legend_handles_labels()
extra = [mpatches.Patch(color=SEC_COL[s], label=f"Section: {s} ({SEC_CENTS[s][2]} seats)")
         for s in ["east", "bend", "south"]]
ax1.legend(handles=handles + extra, loc="upper right", fontsize=9, framealpha=0.92)
fig1.tight_layout()
fig1.savefig(OUT / "plan_alignment.png", dpi=140, bbox_inches="tight")
plt.close(fig1)
print("wrote plan_alignment.png")

# ════════════════════════════════════════════════════════════════════════════
# Figure 2 — Sweep matrix heat-map (ang_mismatch + C_min)
# ════════════════════════════════════════════════════════════════════════════
YAW_RANGE   = sorted({int(float(c["ax_az"])) for c in CANDS})
LAT_OFFSETS = sorted({float(c["lat_offset"]) for c in CANDS})
lookup = {(float(c["ax_az"]), float(c["lat_offset"])): c for c in CANDS}

mismatch_grid = np.full((len(YAW_RANGE), len(LAT_OFFSETS)), np.nan)
cmin_grid     = np.full((len(YAW_RANGE), len(LAT_OFFSETS)), np.nan)
feasible_mask = np.zeros((len(YAW_RANGE), len(LAT_OFFSETS)), dtype=bool)

for i, ax_az in enumerate(YAW_RANGE):
    for j, lat in enumerate(LAT_OFFSETS):
        c = lookup.get((float(ax_az), lat))
        if c:
            mismatch_grid[i, j] = float(c["ang_mismatch"])
            cmin_grid[i, j]     = float(c["min_c_mm"])
            ok = (c["all_c_pass"] == "True"
                  and "ADA" not in c["ada_swale"]
                  and c["bay_blocked"] == "False")
            feasible_mask[i, j] = ok

fig2, axes = plt.subplots(1, 2, figsize=(14, 6))

# Panel A: angular mismatch
cm_div = LinearSegmentedColormap.from_list("rdgy", ["#c0392b", "#ffffff", "#2c3e50"])
im1 = axes[0].imshow(mismatch_grid, cmap=cm_div, vmin=-30, vmax=30, aspect="auto")
axes[0].set_xticks(range(len(LAT_OFFSETS)))
axes[0].set_xticklabels([f"{l:+.0f} ft" for l in LAT_OFFSETS], fontsize=9)
axes[0].set_yticks(range(len(YAW_RANGE)))
axes[0].set_yticklabels([f"{a}°" for a in YAW_RANGE], fontsize=9)
axes[0].set_xlabel("Lateral focal-point shift (ft)", fontsize=10)
axes[0].set_ylabel("Stage axis AX_AZ (°)", fontsize=10)
axes[0].set_title("Angular mismatch: stage axis − audience bearing\n(white = aligned, red = stage too CW, blue = too CCW)", fontsize=10)
for i in range(len(YAW_RANGE)):
    for j in range(len(LAT_OFFSETS)):
        v = mismatch_grid[i, j]
        if not np.isnan(v):
            ok = feasible_mask[i, j]
            sym = "✓" if ok else "✗"
            col = "white" if abs(v) > 15 else "black"
            axes[0].text(j, i, f"{v:+.0f}°\n{sym}", ha="center", va="center",
                        fontsize=7.5, color=col, fontweight="bold" if ok else "normal")
plt.colorbar(im1, ax=axes[0], label="Mismatch (°)", shrink=0.8)

# Panel B: min C_mm
cm_seq = LinearSegmentedColormap.from_list("ryg", ["#e74c3c", "#f39c12", "#27ae60"])
vmin_c, vmax_c = 85, 175
im2 = axes[1].imshow(cmin_grid, cmap=cm_seq, vmin=vmin_c, vmax=vmax_c, aspect="auto")
axes[1].set_xticks(range(len(LAT_OFFSETS)))
axes[1].set_xticklabels([f"{l:+.0f} ft" for l in LAT_OFFSETS], fontsize=9)
axes[1].set_yticks(range(len(YAW_RANGE)))
axes[1].set_yticklabels([f"{a}°" for a in YAW_RANGE], fontsize=9)
axes[1].set_xlabel("Lateral focal-point shift (ft)", fontsize=10)
axes[1].set_title("Min sightline C (mm) — bend section rows 1-18\n(green ≥ 90 mm = pass gate)", fontsize=10)
for i in range(len(YAW_RANGE)):
    for j in range(len(LAT_OFFSETS)):
        v = cmin_grid[i, j]
        if not np.isnan(v):
            pass_c = v >= C_GATE_MM
            col = "white" if v < 100 else "black"
            axes[1].text(j, i, f"{v:.0f}", ha="center", va="center",
                        fontsize=8.5, color=col, fontweight="bold" if pass_c else "normal")
plt.colorbar(im2, ax=axes[1], label="Min C (mm)", shrink=0.8)

fig2.suptitle("Stage Refit Sweep — angular mismatch and sightline matrix\n"
              "✓ = feasible (C ≥ 90 mm, no ADA conflict, bay not blocked)", fontsize=11)
fig2.tight_layout()
fig2.savefig(OUT / "sweep_matrix.png", dpi=140, bbox_inches="tight")
plt.close(fig2)
print("wrote sweep_matrix.png")

# ════════════════════════════════════════════════════════════════════════════
# Figure 3 — Sightline sensitivity: min-C vs ranked candidate
# ════════════════════════════════════════════════════════════════════════════
feasible_sorted = sorted(feasible, key=score_c)
ids   = [c["id"] for c in feasible_sorted]
c_mm  = [float(c["min_c_mm"]) for c in feasible_sorted]
miss  = [float(c["ang_mismatch"]) for c in feasible_sorted]
bay_d = [float(c["bay_view_delta"]) for c in feasible_sorted]

fig3, ax3a = plt.subplots(figsize=(14, 5))
xs = range(len(feasible_sorted))
bars = ax3a.bar(xs, c_mm, color=[("#27ae60" if v >= C_GATE_MM else "#e74c3c") for v in c_mm],
                alpha=0.8, width=0.7)
ax3a.axhline(C_GATE_MM, color="black", lw=1.5, ls="--", label=f"Gate: {C_GATE_MM:.0f} mm")
ax3a.axhline(90, color="black", lw=1.0, ls="--")

# Mark top-8 with labels
for i, (cid, v) in enumerate(zip(ids, c_mm)):
    if i < 8:
        ax3a.text(i, v + 1.5, cid.replace("az", "").replace("_lat", "\n"), fontsize=6.5,
                  ha="center", va="bottom", rotation=0, color="#333")

# Overlay mismatch magnitude as line (secondary axis)
ax3b = ax3a.twinx()
ax3b.plot(xs, [abs(m) for m in miss], "o-", color="#c0392b", ms=4, lw=1.2, alpha=0.8,
          label="|mismatch|°")
ax3b.set_ylabel("|Angular mismatch| (°)", fontsize=10, color="#c0392b")
ax3b.tick_params(axis="y", colors="#c0392b")
ax3b.set_ylim(0, 60)

ax3a.set_xlim(-0.5, len(feasible_sorted) - 0.5)
ax3a.set_ylim(80, max(c_mm) + 15)
ax3a.set_xticks(range(0, len(ids), 5))
ax3a.set_xticklabels([ids[i] for i in range(0, len(ids), 5)], rotation=35, ha="right", fontsize=8)
ax3a.set_ylabel("Min C (mm, bend section)", fontsize=10)
ax3a.set_xlabel("Candidate (ranked by composite score — left = best)", fontsize=10)
ax3a.set_title("Sightline sensitivity: min C across all feasible candidates\n"
               "Green bars pass the 90 mm gate. Red line = |angular mismatch| (right axis).",
               fontsize=11)
lines_a, labels_a = ax3a.get_legend_handles_labels()
lines_b, labels_b = ax3b.get_legend_handles_labels()
ax3a.legend(lines_a + lines_b, labels_a + labels_b, loc="upper left", fontsize=9)
fig3.tight_layout()
fig3.savefig(OUT / "sightline_sensitivity.png", dpi=140, bbox_inches="tight")
plt.close(fig3)
print("wrote sightline_sensitivity.png")

# ════════════════════════════════════════════════════════════════════════════
# Figure 4 — Fan diagram: section bearings relative to stage axis
# ════════════════════════════════════════════════════════════════════════════
# Show the angular positions of each section centroid relative to axis for
# baseline, best candidate, and a pure-yaw-124 candidate.
fig4, axes4 = plt.subplots(1, 3, figsize=(15, 6), subplot_kw={"projection": "polar"})

compare_cases = [
    ("Baseline\naz 150°, lat 0 ft", SF_ORIG[0], SF_ORIG[1], 150.0, "#636363"),
    (f"Best: {best['id']}" if best else "—",
     float(best["sfx"]) if best else SF_ORIG[0],
     float(best["sfy"]) if best else SF_ORIG[1],
     float(best["ax_az"]) if best else 150.0,
     "#e74c3c"),
    ("Path A: pure yaw\naz 124°, lat 0 ft",
     *arc_pt(50, 124), 124.0, "#8e44ad"),
]

for ax_pol, (title, sfx, sfy, ax_az, col) in zip(axes4, compare_cases):
    # 0° = top = stage axis direction
    for sec, (cx, cy, s) in SEC_CENTS.items():
        raw_b = math.degrees(math.atan2(cx - sfx, cy - sfy)) % 360
        # relative offset from axis (signed, degrees CCW = negative)
        off = ((raw_b - ax_az) + 180) % 360 - 180
        theta = math.radians(off)
        dist  = math.hypot(cx - sfx, cy - sfy)
        # Plot as a radial line + dot
        ax_pol.plot([0, theta], [0, dist], color=SEC_COL[sec], lw=2.5, alpha=0.85)
        ax_pol.plot(theta, dist, "o", color=SEC_COL[sec], ms=10 + s / 80,
                    label=f"{sec} ({s}), {off:+.0f}°")

    # Audience centroid
    raw_b_aud = math.degrees(math.atan2(AUD_CX - sfx, AUD_CY - sfy)) % 360
    off_aud   = ((raw_b_aud - ax_az) + 180) % 360 - 180
    d_aud     = math.hypot(AUD_CX - sfx, AUD_CY - sfy)
    ax_pol.plot(math.radians(off_aud), d_aud, "*", color="gold", ms=18, mec="#333", mew=1.2,
                label=f"centroid ({off_aud:+.1f}°)", zorder=5)

    # ±55° fan lines
    for side_deg in [-55, 55]:
        ax_pol.axvline(math.radians(side_deg), color="#aaa", lw=1.0, ls=":")
    ax_pol.axvline(0, color=col, lw=2.0, ls="-", alpha=0.5)

    # Polar setup — clamp to ±90° (enough to see the east section at 75°)
    ax_pol.set_thetamin(-90); ax_pol.set_thetamax(90)
    ax_pol.set_theta_zero_location("N")
    ax_pol.set_theta_direction(-1)
    ax_pol.set_rmax(220)
    ax_pol.set_rticks([80, 120, 160, 200])
    ax_pol.set_rlabel_position(80)
    ax_pol.set_xlabel(f"axis = {ax_az:.0f}°", labelpad=14, fontsize=9, color=col)
    ax_pol.set_title(title, pad=18, fontsize=10)
    ax_pol.legend(loc="lower right", fontsize=8, framealpha=0.9,
                  bbox_to_anchor=(1.4, -0.05))
    ax_pol.tick_params(labelsize=8)
    # Custom angular labels
    ax_pol.set_xticks([math.radians(a) for a in range(-90, 91, 15)])
    ax_pol.set_xticklabels([f"{a:+.0f}°" for a in range(-90, 91, 15)], fontsize=7)

    # Annotate ±FAN_HALF
    for side_deg in [-55, 55]:
        ax_pol.text(math.radians(side_deg), 215, f"±{FAN_HALF:.0f}°",
                    ha="center", va="bottom", fontsize=8, color="#888")

fig4.suptitle("Section fan diagram — angular offset from stage axis\n"
              "★ = seat-weighted centroid  |  dotted lines = ±55° FAN_HALF  "
              "|  radial distance = ft from focal point",
              fontsize=11, y=1.02)
fig4.tight_layout()
fig4.savefig(OUT / "fan_diagram.png", dpi=140, bbox_inches="tight")
plt.close(fig4)
print("wrote fan_diagram.png")

print(f"\nAll images written to {OUT}")
