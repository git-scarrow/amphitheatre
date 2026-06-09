#!/usr/bin/env python3
"""Stage 4 figure + seat_count.md + README.md."""
import json, math, pickle
import numpy as np
import rasterio
from rasterio.transform import rowcol
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly

ctx = pickle.load(open("stage4/_ctx.pkl", "rb"))
rows = ctx["rows"]; cap = ctx["cap"]; P = ctx["params"]; ada = ctx["ada"]
FX, FY = ctx["F"]
AX_AZ = P["AX_AZ"]; FACE_AZ = P["FACE_AZ"]; FAN = P["FAN_HALF"]
R_IN = P["R_INNER"]; R_OUT = P["R_OUTER"]; FOCUS = P["FOCUS_ELEV"]; EYE = P["EYE_HT"]
C_TGT = P["C_TARGET_FT"]

ds = rasterio.open("dem/dem_design_1ft.tif"); A = ds.read(1).astype(float); nod = ds.nodata
A[A == nod] = np.nan; T = ds.transform
def elev(x, y):
    r, c = rowcol(T, x, y)
    return np.nan if not (0 <= r < A.shape[0] and 0 <= c < A.shape[1]) else A[r, c]
def U(az): a = math.radians(az); return math.sin(a), math.cos(a)
def polar(R, az, ox=FX, oy=FY): e, n = U(az); return ox + e*R, oy + n*R

# window around the venue
pad = 60
xs = [FX]; ys = [FY]
for az in (AX_AZ-FAN, AX_AZ+FAN, FACE_AZ):
    x, y = polar(R_OUT+40, az); xs.append(x); ys.append(y)
x0, x1 = min(xs)-pad, max(xs)+pad; y0, y1 = min(ys)-pad, max(ys)+pad
r0, c0 = rowcol(T, x0, y1); r1, c1 = rowcol(T, x1, y0)
r0, r1 = max(0, r0), min(A.shape[0], r1); c0, c1 = max(0, c0), min(A.shape[1], c1)
sub = A[r0:r1, c0:c1]
extent = [ds.xy(0, c0)[0], ds.xy(0, c1)[0], ds.xy(r1, 0)[1], ds.xy(r0, 0)[1]]

# hillshade
gy, gx = np.gradient(sub)
slope = np.pi/2 - np.arctan(np.hypot(gx, gy))
asp = np.arctan2(-gx, gy)
az_l, alt_l = np.radians(315), np.radians(45)
hs = (np.sin(alt_l)*np.sin(slope) + np.cos(alt_l)*np.cos(slope)*np.cos(az_l - asp))

fig = plt.figure(figsize=(16, 9))
gs = fig.add_gridspec(2, 2, width_ratios=[1.25, 1], height_ratios=[1, 1])
axP = fig.add_subplot(gs[:, 0]); axS = fig.add_subplot(gs[0, 1]); axC = fig.add_subplot(gs[1, 1])

# ---- PLAN
axP.imshow(hs, extent=extent, cmap="gray", alpha=0.85, origin="upper", aspect="equal")
cs = axP.contour(np.linspace(extent[0], extent[1], sub.shape[1]),
                 np.linspace(extent[3], extent[2], sub.shape[0]), sub,
                 levels=np.arange(605, 660, 2), colors="#88663344", linewidths=0.5)
sf = json.load(open("stage4/stage_floor.geojson"))
for f in sf["features"]:
    g = f["geometry"]; nm = f["properties"]["name"]
    if g["type"] == "Polygon":
        col = {"stage": "#222", "event_floor_forecourt": "#d9b38c",
               "treatment_wet_cell": "#3b7fb0"}.get(nm, "#999")
        axP.add_patch(MPoly(g["coordinates"][0], closed=True, fc=col, ec="k", alpha=0.55, lw=1, zorder=4))
    elif g["type"] == "LineString":
        xs_, ys_ = zip(*g["coordinates"]); axP.plot(xs_, ys_, "--", color="#1f6f1f", lw=1.4, zorder=5)
    else:
        axP.plot(*g["coordinates"], "*", color="yellow", ms=18, mec="k", zorder=8)
sr = json.load(open("stage4/seating_rows.geojson"))
for f in sr["features"]:
    xs_, ys_ = zip(*f["geometry"]["coordinates"])
    ok = f["properties"]["meets_C_on_terrain"]
    axP.plot(xs_, ys_, "-", color=("#2c7" if ok else "#d33"), lw=1.6, zorder=6)
ar = json.load(open("stage4/ada_route.geojson"))
for f in ar["features"]:
    g = f["geometry"]
    if g["type"] == "LineString":
        xs_, ys_ = zip(*g["coordinates"])
        sty = "-" if "switchback" in f["properties"].get("type", "") else ":"
        axP.plot(xs_, ys_, sty, color="#0050ff", lw=2.2, zorder=7)
    else:
        axP.plot(*g["coordinates"], "s", color="#00bfff", ms=9, mec="k", zorder=9)
axP.plot([], [], "-", color="#2c7", label="seating: meets C on terrain")
axP.plot([], [], "-", color="#d33", label="seating: needs regrade")
axP.plot([], [], "-", color="#0050ff", label="accessible ramp")
axP.plot([], [], "s", color="#00bfff", mec="k", label="accessible (WC) seating")
axP.plot([], [], "--", color="#1f6f1f", label="bay-view axis (NNW)")
axP.plot([], [], "*", color="yellow", mec="k", label="focal point / stage")
axP.set_title("Plan — partial-fan amphitheater on the S/SE arc (DEM hillshade, 2 ft contours)", fontsize=10)
axP.set_xlabel("Easting (US ft, EPSG:6494)"); axP.set_ylabel("Northing (US ft)")
axP.legend(loc="lower left", fontsize=7.5, framealpha=0.9); axP.set_aspect("equal")
axP.annotate("← to Little Traverse Bay", xy=polar(R_OUT*0.0+40, FACE_AZ),
             xytext=polar(150, FACE_AZ), fontsize=8, color="#06c", ha="center")

# ---- SECTION along centerline (NW-SE)
ts = np.arange(-110, R_OUT+30, 1.0)
prof = [elev(*polar(t, AX_AZ)) for t in ts]
axS.plot(ts, prof, color="#7a5", lw=1.5, label="existing grade")
# stair-step treads
for i, r in enumerate(rows):
    t = r["R"]; te = r["tread_prop"]
    axS.plot([t-1.4, t+1.4], [te, te], color=("#2c7" if r["meets_terr"] else "#d33"), lw=2.5)
# stage + floor
axS.plot([-30, R_IN], [FOCUS, FOCUS], color="#d9b38c", lw=4, solid_capstyle="butt", label="event floor 612.5")
axS.add_patch(plt.Rectangle((-26, FOCUS), 12, 3.0, fc="#222", ec="k", zorder=5))
axS.text(-20, FOCUS+3.3, "stage", fontsize=7, ha="center")
# treatment pool
axS.plot([-110, -30], [609.1, 609.1], color="#3b7fb0", lw=2)
axS.fill_between([-110, -30], 609.1, 611.3, color="#3b7fb0", alpha=0.3)
axS.text(-70, 611.6, "wet/treatment cell\n609.1–611.3", fontsize=6.5, ha="center", color="#06c")
# sightline rays from a few rows to focus
for i in (0, 9, 19, len(rows)-1):
    r = rows[i]
    axS.plot([r["R"], 0], [r["eye_prop"], FOCUS], color="#bbb", lw=0.6, zorder=1)
axS.plot([0], [FOCUS], "*", color="orange", ms=12, mec="k", zorder=6)
axS.set_title("Section on centerline (az 150 SSE) — treads, sightlines, treatment cell", fontsize=9)
axS.set_xlabel("Distance from focal point (ft)  ·  NW ← → SE upslope"); axS.set_ylabel("Elev NAVD88 (ft)")
axS.legend(loc="upper left", fontsize=7); axS.grid(alpha=0.25)

# ---- C-value chart
rn = [r["row"] for r in rows[1:]]
ct = [r["C_terr"]*304.8 for r in rows[1:]]
cp = [r["C_prop"]*304.8 for r in rows[1:]]
ctc = [max(v, -60) for v in ct]                      # clamp deep negatives so they stay visible
axC.bar(rn, ctc, color=["#2c7" if v >= C_TGT*304.8 else "#d33" for v in ct], width=0.8)
axC.axhline(C_TGT*304.8, color="k", ls="--", lw=1, label=f"target {C_TGT*304.8:.0f} mm")
axC.axhline(0, color="#555", lw=0.6)
axC.set_title("Row C-value on bare terrain (red = needs regrade; neg = blocked view)", fontsize=9)
axC.set_xlabel("Row"); axC.set_ylabel("C-value (mm)"); axC.set_ylim(-70, 400)
axC.legend(fontsize=7); axC.grid(axis="y", alpha=0.25)

fig.suptitle("Petoskey Pit — Stage 4: partial-fan amphitheater geometry (planning-grade, NAVD88 intl ft)", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.97])
fig.savefig("stage4/plan_and_sections.png", dpi=130)
print("wrote stage4/plan_and_sections.png")

# ---------------------------------------------------------------- seat_count.md
nfail = sum(1 for r in rows if not r["meets_terr"])
nreg = sum(1 for r in rows if r["regrade"] or not r["meets_terr"])
tot_fill = sum(max(0, r["cutfill"]) for r in rows)
md = f"""# Stage 4 — Seat Count & Capacity

**Petoskey Pit amphitheater — partial fan on the S/SE arc.** Planning-grade.
Geometry: focal point (stage front) at NW edge of the event floor; concentric
terraced rows centered on the focus; centerline **az {AX_AZ:.0f}° (SSE)**, audience
faces **az {FACE_AZ:.0f}° (NNW, toward Little Traverse Bay & evening sun)**.

| Parameter | Value |
|---|---|
| Rows | {P['NROWS']} |
| Inner / outer radius (from focus) | {R_IN:.0f} / {R_OUT:.0f} ft |
| Fan angle | ±{FAN:.0f}° ({2*FAN:.0f}° total) |
| Tread (row) depth | {P['TREAD']:.1f} ft |
| Longitudinal aisle/vom allowance | {P['AISLE_FRAC']*100:.0f}% of arc |
| Event floor / focus elevation | {FOCUS:.1f} ft NAVD88 |

## Capacity by seat-width scenario

| Scenario | Seat width | **Total seats** | Notes |
|---|---|---|---|
| **Compact** | {P['SEAT_W_COMPACT']*12:.0f} in ({P['SEAT_W_COMPACT']:.2f} ft) | **{cap['compact']:,}** | ben/bleacher-style, dense civic events |
| **Generous** | {P['SEAT_W_GENEROUS']*12:.0f} in ({P['SEAT_W_GENEROUS']:.2f} ft) | **{cap['generous']:,}** | fixed chairs / comfortable spacing |

Seats/row scale with radius (outer rows hold ~{rows[-1]['seats_compact']} compact;
inner rows ~{rows[0]['seats_compact']}). Per-row counts are in `sightline_table.csv`
and `seating_rows.geojson`.

## Sightlines (C-value target {C_TGT*304.8:.0f} mm / {C_TGT:.2f} ft eye-over-eye)

- **Proposed graded terraces meet the {C_TGT*304.8:.0f} mm target in all {P['NROWS']} rows** (by design).
- On **bare existing terrain**, **{P['NROWS']-nfail} of {P['NROWS']} rows already clear** the target;
  **{nfail} rows fail** and are flagged for regrading: rows {', '.join(str(r['row']) for r in rows if not r['meets_terr'])}
  (the upper rows where the natural slope eases near the rim).
- Earthwork is **fill-only, ~0 cut**; total ≈ {tot_fill:.1f} ft of summed per-row fill,
  concentrated in the upper rows (max {max(r['cutfill'] for r in rows):.1f} ft at row
  {max(rows, key=lambda r: r['cutfill'])['row']}). The front {sum(1 for r in rows if abs(r['cutfill'])<0.05)} rows sit essentially on grade.

## Accessibility (see `ada_route.geojson`)

The bowl is a **closed depression** — there is **no natural ≤8.33% rim-to-floor grade**
(the rim lip runs ~16%), so accessible access requires engineered ramps:

- **Route A (primary):** NW bay-side garden → event floor, {ada['routeA_drop']} ft drop,
  {ada['routeA_runs']} switchback runs @ 8.33%, ≤2% cross — lands on **floor-level accessible seating**.
- **Route B:** SE upper garden → **mid-bowl level cross-aisle (row 15)**, {ada['routeB_drop']} ft drop,
  {ada['routeB_runs']} runs @ 8.33% — gives dispersed accessible seating at mid height.
- **6 wheelchair-space pairs** dispersed L/C/R at the **front (floor)** and **mid (row 15)** levels
  (ADA 221.2 dispersion). Companion seats assumed adjacent.

> Ramp alignments are **schematic** (corridor + run/landing counts correct; exact
> footprint to be fit in design). Cross-slope ≤2% is a design target, not yet graded.
"""
open("stage4/seat_count.md", "w").write(md)
print("wrote stage4/seat_count.md")
