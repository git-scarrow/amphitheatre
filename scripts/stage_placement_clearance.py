#!/usr/bin/env python3
"""Stage placement / row-1 clearance diagnostic (RED issue addendum).

Advisory. Changes no canon. Resolves the 35-ft vs measured-clearance contradiction by
measuring every stage-edge-to-row clearance by segment against the CURRENT adopted geometry
(Scenario E three-section treads + adopted P_opt footprint), and renders a plan-view diagnostic.

Outputs -> analysis/stage_pad_redteam/:
  stage_placement_clearance.csv
  stage_placement_clearance.png
Run:  python scripts/stage_placement_clearance.py
"""
import csv
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly
from shapely.affinity import translate
from shapely.geometry import shape, mapping, LineString, Point
from shapely.ops import unary_union, nearest_points

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "analysis", "stage_pad_redteam")
SECTIONS = ["east", "bend", "south"]
CANON_35 = 35.0  # retired design_open_low single-fan uniform stage-front->row-1


def load(p):
    return json.load(open(os.path.join(REPO, p)))


# ── current adopted geometry ─────────────────────────────────────────────────
geE = load("analysis/scenarioE_civic/geometry.geojson")
inh = [f for f in geE["features"] if f["properties"].get("role") == "stage_surface"]
inh_polys = sorted((shape(f["geometry"]) for f in inh), key=lambda g: g.area, reverse=True)
inh_core, inh_sh = inh_polys[0], inh_polys[1:]
adf = load("analysis/in_situ_normalization/adopted_stage_footprint.geojson")
props = adf["features"][0]["properties"]
deck = shape(adf["features"][0]["geometry"])          # core + five-facet apron
off = props["lateral_offset_from_inherited_ft"]
core = translate(inh_core, xoff=off[0], yoff=off[1])
apron = deck.difference(core).buffer(0)
sh_l = translate(inh_sh[0], xoff=off[0], yoff=off[1])
sh_r = translate(inh_sh[1], xoff=off[0], yoff=off[1])
footprint = unary_union([core, apron, sh_l, sh_r])

treads = load("vectors_geojson/terrace_treads.geojson")["features"]
def row_geom(sec, r):
    gs = [shape(f["geometry"]) for f in treads
          if f["properties"]["section"] == sec and f["properties"]["row"] == r]
    return unary_union(gs) if gs else None
def row_elev(sec, r):
    for f in treads:
        if f["properties"]["section"] == sec and f["properties"]["row"] == r:
            return f["properties"].get("tread_elev_navd88")
    return None

bz = {f["properties"]["name"]: shape(f["geometry"])
      for f in load("vectors_geojson/bowl_zones.geojson")["features"]}
orchestra = bz["orchestra_event_floor"]

# ── clearance table: each stage edge -> each row, by segment ─────────────────
edges = {"core_front(canon meas.)": core, "deck_front(core+apron)": deck,
         "full_footprint(+shoulders)": footprint}
rows_csv = []
for sec in SECTIONS:
    for r in (1, 2):
        rg = row_geom(sec, r)
        if rg is None:
            continue
        rec = {"section": sec, "row": r, "row_tread_elev_navd88": row_elev(sec, r)}
        for lbl, g in edges.items():
            rec[f"clear_{lbl}_ft"] = round(g.distance(rg), 1)
        rec["shortfall_vs_35ft_core_ft"] = round(CANON_35 - rec["clear_core_front(canon meas.)_ft"], 1)
        rows_csv.append(rec)

orch_overlap = round(footprint.intersection(orchestra).area, 1)
with open(os.path.join(OUT, "stage_placement_clearance.csv"), "w", newline="") as fh:
    cols = ["section", "row", "row_tread_elev_navd88",
            "clear_core_front(canon meas.)_ft", "clear_deck_front(core+apron)_ft",
            "clear_full_footprint(+shoulders)_ft", "shortfall_vs_35ft_core_ft"]
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(rows_csv)

# ── console reconciliation ───────────────────────────────────────────────────
print("core_front -> row1 by section (should reproduce canon 12.0/32.7/21.9):")
for sec in SECTIONS:
    r1 = [x for x in rows_csv if x["section"] == sec and x["row"] == 1][0]
    print(f"  {sec:5s} core {r1['clear_core_front(canon meas.)_ft']:5.1f}  "
          f"deck(+apron) {r1['clear_deck_front(core+apron)_ft']:5.1f}  "
          f"row1_elev {r1['row_tread_elev_navd88']}")
print(f"stage footprint ∩ orchestra_event_floor = {orch_overlap} sf")
print(f"design_open_low row1 elev (retired) = 613.54 ; Scenario E row1 = "
      f"{row_elev('bend',1)} ; row3 = {row_elev('bend',3)}")

# ── plan-view diagnostic PNG ─────────────────────────────────────────────────
ox, oy = footprint.centroid.x, footprint.centroid.y
def xy(g):
    g = translate(g, xoff=-ox, yoff=-oy)
    return g
fig, ax = plt.subplots(figsize=(9, 9))

def draw(g, **kw):
    g = xy(g)
    polys = g.geoms if g.geom_type.startswith("Multi") else [g]
    for p in polys:
        ax.add_patch(MplPoly(np.array(p.exterior.coords), **kw))

# zones
draw(orchestra, facecolor="#f4e6c8", edgecolor="#c9a24b", lw=1.2, alpha=0.7, zorder=1)
for sec in SECTIONS:
    for r, col in ((1, "#3a7ca5"), (2, "#8bb8d0")):
        rg = row_geom(sec, r)
        if rg:
            draw(rg, facecolor=col, edgecolor="#1d4e6b", lw=1.0, alpha=0.85, zorder=3)
draw(sh_l, facecolor="#b8b0a0", edgecolor="#6b6355", lw=1.0, alpha=0.9, zorder=2)
draw(sh_r, facecolor="#b8b0a0", edgecolor="#6b6355", lw=1.0, alpha=0.9, zorder=2)
draw(apron, facecolor="#d98b5f", edgecolor="#8a4b2a", lw=1.0, alpha=0.95, zorder=4)
draw(core, facecolor="#c25d3a", edgecolor="#7a3116", lw=1.4, alpha=0.95, zorder=4)

# P_opt marker = core-front centre
cf = xy(core)
# downstage normal: direction core-centroid -> bend row1 centroid
r1b = row_geom("bend", 1)
dvec = np.array([r1b.centroid.x - core.centroid.x, r1b.centroid.y - core.centroid.y])
dvec = dvec / np.linalg.norm(dvec)
pcx, pcy = core.centroid.x - ox, core.centroid.y - oy
ax.plot(pcx, pcy, "k*", ms=16, zorder=6)
ax.annotate("P_opt (adopted core centre)", (pcx, pcy), textcoords="offset points",
            xytext=(6, 8), fontsize=9, fontweight="bold")

# 35-ft rule locus: DOWNSTAGE FRONT EDGE only, offset 35 ft toward the audience.
# front edge = the core exterior edge whose midpoint is nearest bend row-1.
cc = list(core.exterior.coords)[:-1]
best = None
for i in range(len(cc)):
    a, b = cc[i], cc[(i + 1) % len(cc)]
    mid = Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    d = mid.distance(r1b)
    if best is None or d < best[0]:
        best = (d, a, b)
front_edge = LineString([best[1], best[2]])
locus = translate(front_edge, xoff=dvec[0] * CANON_35, yoff=dvec[1] * CANON_35)
lx = xy(locus)
ax.plot(*np.array(lx.coords).T, "--", color="#b02020", lw=2.2, zorder=5,
        label="35-ft rule locus (front edge +35 ft)")
# thin ties from the actual front edge to the locus (show the 35-ft span)
fe = xy(front_edge)
lc = np.array(lx.coords); fc = np.array(fe.coords)
for j in (0, 1):
    ax.plot([fc[j][0], lc[j][0]], [fc[j][1], lc[j][1]], ":", color="#b02020", lw=1.0, zorder=5)

# clearance leaders core-front -> row1
for sec in SECTIONS:
    rg = row_geom(sec, 1)
    p1, p2 = nearest_points(core, rg)
    ax.plot([p1.x - ox, p2.x - ox], [p1.y - oy, p2.y - oy], "-", color="#222", lw=1.3, zorder=6)
    d = core.distance(rg)
    mx, my = (p1.x + p2.x) / 2 - ox, (p1.y + p2.y) / 2 - oy
    ax.annotate(f"{sec} {d:.0f}ft", (mx, my), fontsize=9, color="#a00",
                fontweight="bold", zorder=7)

ax.set_aspect("equal")
ax.set_title("Stage placement vs row-1 clearance (current adopted P_opt / Scenario E)\n"
             "core-front gaps 12/33/22 ft — 35-ft rule (dashed) is retired single-fan geometry",
             fontsize=11)
ax.set_xlabel("ft (local, origin at footprint centroid)")
# legend proxies
from matplotlib.patches import Patch
leg = [Patch(fc="#c25d3a", label="stage core 70x34"),
       Patch(fc="#d98b5f", label="five-facet apron"),
       Patch(fc="#b8b0a0", label="shoulders"),
       Patch(fc="#3a7ca5", label="row 1 (forecourt)"),
       Patch(fc="#8bb8d0", label="row 2"),
       Patch(fc="#f4e6c8", label="orchestra_event_floor"),
       plt.Line2D([0], [0], ls="--", color="#b02020", label="35-ft rule locus (retired)")]
ax.legend(handles=leg, loc="upper left", fontsize=8, framealpha=0.9)
ax.grid(True, ls=":", alpha=0.4)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "stage_placement_clearance.png"), dpi=140)
print("wrote stage_placement_clearance.csv + .png")
