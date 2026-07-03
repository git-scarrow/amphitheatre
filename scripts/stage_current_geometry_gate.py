#!/usr/bin/env python3
"""Current-adopted-geometry stage-footprint clearance gate (RED issue resolution).

Advisory. Focuses ONLY on the current adopted geometry (P_opt core + five_facet_apron +
translated lateral shoulders) vs Scenario E row-1 treads. Classifies edges, tests the ≥12 ft
pocket gate on the governed (occupied deck) edge, quantifies the east-shoulder conflict and the
orchestra overlap, and — if needed — emits a revised shoulder footprint that clears row 1 by ≥12 ft.

Outputs -> analysis/stage_pad_redteam/:
  stage_current_geometry_gate.csv
  stage_current_geometry_gate.png
  repair_candidate_shoulders_trimmed.geojson  (CANDIDATE — optional shoulder trim, not adopted)
Run:  python scripts/stage_current_geometry_gate.py
"""
import csv
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly, Patch
from shapely.affinity import translate
from shapely.geometry import shape, mapping
from shapely.ops import unary_union, nearest_points

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "analysis", "stage_pad_redteam")
SECTIONS = ["east", "bend", "south"]
GATE = 12.0  # ≥12 ft in-situ row-1 pocket gate (DESIGN_CANON Rule 9, P_opt)


def load(p):
    return json.load(open(os.path.join(REPO, p)))


# ── current adopted geometry ─────────────────────────────────────────────────
geE = load("analysis/scenarioE_civic/geometry.geojson")
inh = [f for f in geE["features"] if f["properties"].get("role") == "stage_surface"]
inh_polys = sorted((shape(f["geometry"]) for f in inh), key=lambda g: g.area, reverse=True)
inh_core, inh_sh = inh_polys[0], inh_polys[1:]
adf = load("analysis/in_situ_normalization/adopted_stage_footprint.geojson")
off = adf["features"][0]["properties"]["lateral_offset_from_inherited_ft"]
core = translate(inh_core, xoff=off[0], yoff=off[1])
deck = shape(adf["features"][0]["geometry"])          # core ∪ five-facet apron (OCCUPIED)
apron = deck.difference(core).buffer(0)
shoulders = [translate(g, xoff=off[0], yoff=off[1]) for g in inh_sh]   # LATERAL, non-occupied
full = unary_union([deck] + shoulders)

treads = load("vectors_geojson/terrace_treads.geojson")["features"]
def row_geom(sec, r):
    gs = [shape(f["geometry"]) for f in treads
          if f["properties"]["section"] == sec and f["properties"]["row"] == r]
    return unary_union(gs) if gs else None
def row_seats(sec, r):
    return int(sum(f["properties"].get("seats_kept", 0) for f in treads
                   if f["properties"]["section"] == sec and f["properties"]["row"] == r))
row1 = {s: row_geom(s, 1) for s in SECTIONS}
row1_all = unary_union([g for g in row1.values() if g])
orchestra = {f["properties"]["name"]: shape(f["geometry"])
             for f in load("vectors_geojson/bowl_zones.geojson")["features"]
             }["orchestra_event_floor"]

# label each shoulder by the section whose row-1 it is nearest
def nearest_section(g):
    return min(SECTIONS, key=lambda s: g.distance(row1[s]))
sh_label = {i: nearest_section(g) for i, g in enumerate(shoulders)}

# ── measurements ─────────────────────────────────────────────────────────────
def mind(a, b):
    return round(a.distance(b), 2)

rows = []
for s in SECTIONS:
    r1 = row1[s]
    # shoulder nearest this section (if any)
    shs = [shoulders[i] for i in sh_label if sh_label[i] == s]
    sh_u = unary_union(shs) if shs else None
    sh_gap = mind(sh_u, r1) if sh_u else None
    sh_ovl = round(sh_u.intersection(r1).area, 1) if sh_u else 0.0
    rows.append(dict(
        section=s,
        core_to_row1_ft=mind(core, r1),
        occupied_deck_to_row1_ft=mind(deck, r1),          # GOVERNED edge
        full_footprint_to_row1_ft=mind(full, r1),
        shoulder_to_row1_ft=sh_gap,
        shoulder_row1_overlap_sf=sh_ovl,
        orchestra_overlap_sf=round(deck.intersection(orchestra).area, 1) if s == "east" else "",
        row1_seats=row_seats(s, 1),
        gate_pass_governed=bool(mind(deck, r1) >= GATE),
    ))

gov_min = min(r["occupied_deck_to_row1_ft"] for r in rows)
orch_overlap = round(deck.intersection(orchestra).area, 1)
full_overlap = round(full.intersection(orchestra).area, 1)

# ── seat impact of the east shoulder (length fraction of row-1 within the shoulder) ──
seat_loss = {}
for i, g in enumerate(shoulders):
    s = sh_label[i]
    r1 = row1[s]
    inter = g.intersection(r1)
    frac = (inter.area / r1.area) if (not inter.is_empty and r1.area) else 0.0
    seat_loss[s] = round(frac * row_seats(s, 1), 1)

# ── revised shoulders: clip anything inside the 12-ft row-1 pocket ───────────
buf = row1_all.buffer(GATE)
revised_sh = [g.difference(buf).buffer(0) for g in shoulders]
revised_full = unary_union([deck] + [g for g in revised_sh if not g.is_empty])
area_removed = round(sum(g.area for g in shoulders) - sum(g.area for g in revised_sh), 1)
revised_min = round(min(unary_union(revised_sh).distance(row1[s]) for s in SECTIONS
                        if not unary_union(revised_sh).is_empty), 2) if any(
                        not g.is_empty for g in revised_sh) else None

needs_revision = any((r["shoulder_row1_overlap_sf"] or 0) > 0.5 or
                     (r["shoulder_to_row1_ft"] is not None and r["shoulder_to_row1_ft"] < GATE)
                     for r in rows)

# ── write CSV ────────────────────────────────────────────────────────────────
with open(os.path.join(OUT, "stage_current_geometry_gate.csv"), "w", newline="") as fh:
    cols = ["section", "core_to_row1_ft", "occupied_deck_to_row1_ft",
            "full_footprint_to_row1_ft", "shoulder_to_row1_ft", "shoulder_row1_overlap_sf",
            "orchestra_overlap_sf", "row1_seats", "gate_pass_governed"]
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

# ── solid-pad-to-612.5 upper-bound CY: pre-trim (adopted) vs trimmed candidate ──
import rasterio
from rasterio.features import rasterize
with rasterio.open(os.path.join(REPO, "dem", "dem_design_1ft.tif")) as ds:
    DEM = ds.read(1).astype(float); TF = ds.transform; SHP = ds.shape; NDV = ds.nodata
    CELL = abs(TF.a * TF.e)
def padcy(geom, target=612.5):
    m = rasterize([(mapping(geom), 1)], out_shape=SHP, transform=TF, fill=0,
                  all_touched=False).astype(bool)
    if NDV is not None:
        m &= (DEM != NDV)
    z = DEM[m]
    return round(float(np.clip(target - z, 0, None).sum()) * CELL / 27.0, 1), round(z.size * CELL, 1)
pretrim_cy, pretrim_area = padcy(full)                    # = the adopted 330.2 CY / 3386 sf
cand_cy, cand_area = padcy(revised_full)
cand_orch = round(revised_full.intersection(orchestra).area, 1)

# ── write repair CANDIDATE footprint (NOT adopted; trim deferred to Phase B) ──
feats = [{"type": "Feature", "properties": {"name": "stage_core_70x34", "class": "performance_core"},
          "geometry": mapping(core)},
         {"type": "Feature", "properties": {"name": "five_facet_apron", "class": "occupied_deck"},
          "geometry": mapping(apron)}]
for i, g in enumerate(revised_sh):
    if g.is_empty:
        continue
    feats.append({"type": "Feature",
                  "properties": {"name": f"shoulder_{sh_label[i]}_trimmed",
                                 "class": "lateral_nonoccupied",
                                 "clipped_to_clear_row1_by_ft": GATE},
                  "geometry": mapping(g)})
json.dump({"type": "FeatureCollection",
           "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::6494"}},
           "properties": {"status": "repair_candidate — NOT adopted (optional shoulder trim; "
                          "occupied deck already passes the gate, so no required change)",
                          "note": "lateral shoulders clipped out of the 12-ft row-1 pocket; "
                          "deck (core+apron) unchanged",
                          "shoulder_area_removed_sf": area_removed,
                          "candidate_full_footprint_area_sf": cand_area,
                          "adopted_pretrim_full_footprint_area_sf": pretrim_area,
                          "candidate_solid_pad_612p5_cy": cand_cy,
                          "adopted_pretrim_solid_pad_612p5_cy": pretrim_cy,
                          "candidate_orchestra_overlap_sf": cand_orch,
                          "adopted_pretrim_orchestra_overlap_full_sf": full_overlap,
                          "revised_shoulder_min_clear_ft": revised_min},
           "features": feats},
          open(os.path.join(OUT, "repair_candidate_shoulders_trimmed.geojson"), "w"), indent=1)
print(f"CANDIDATE(trim): area {cand_area} sf (−{pretrim_area-cand_area:.0f}), "
      f"solid-pad CY {cand_cy} (adopted pre-trim {pretrim_cy}), orchestra∩ {cand_orch} sf")

# ── console ──────────────────────────────────────────────────────────────────
print("edge -> row1 min clearance (ft), governed edge = occupied deck (core+apron):")
for r in rows:
    print(f"  {r['section']:5s} core {r['core_to_row1_ft']:5.1f}  deck {r['occupied_deck_to_row1_ft']:5.1f}"
          f"  full {r['full_footprint_to_row1_ft']:5.1f}  shoulder_gap {r['shoulder_to_row1_ft']}"
          f"  sh∩row1 {r['shoulder_row1_overlap_sf']}sf")
print(f"GOVERNED (deck) min = {gov_min} ft -> gate {'PASS' if gov_min>=GATE else 'FAIL'} (≥{GATE})")
print(f"orchestra overlap: deck {orch_overlap} sf | full(+shoulders) {full_overlap} sf")
print(f"seat loss if shoulders clip row1: {seat_loss}")
print(f"revised shoulders: removed {area_removed} sf, new min clear {revised_min} ft; needs_revision={needs_revision}")

# ── PNG: current vs revised, edge classes + orchestra ────────────────────────
ox, oy = full.centroid.x, full.centroid.y
def T(g):
    return translate(g, xoff=-ox, yoff=-oy)
fig, axes = plt.subplots(1, 2, figsize=(15, 8), sharex=True, sharey=True)

def draw(ax, g, **kw):
    g = T(g)
    for p in (g.geoms if g.geom_type.startswith("Multi") else [g]):
        if p.is_empty:
            continue
        ax.add_patch(MplPoly(np.array(p.exterior.coords), **kw))

for ax, title, sh_set, ft in ((axes[0], "CURRENT adopted footprint", shoulders, full),
                               (axes[1], f"REVISED (shoulders clipped from 12-ft pocket; −{area_removed} sf)",
                                revised_sh, revised_full)):
    draw(ax, orchestra, facecolor="#f4e6c8", edgecolor="#c9a24b", lw=1.0, alpha=0.7, zorder=1)
    for s, col in (("east", "#3a7ca5"), ("bend", "#3a7ca5"), ("south", "#3a7ca5")):
        draw(ax, row1[s], facecolor=col, edgecolor="#12405c", lw=1.0, alpha=0.9, zorder=3)
        draw(ax, row_geom(s, 2), facecolor="#a9cbe0", edgecolor="#5a86a0", lw=0.8, alpha=0.8, zorder=2)
    for g in sh_set:
        draw(ax, g, facecolor="#b8b0a0", edgecolor="#6b6355", lw=1.0, alpha=0.9, zorder=4)
    draw(ax, apron, facecolor="#d98b5f", edgecolor="#8a4b2a", lw=1.0, alpha=0.95, zorder=5)
    draw(ax, core, facecolor="#c25d3a", edgecolor="#7a3116", lw=1.3, alpha=0.95, zorder=5)
    # governed clearance leaders (deck -> row1)
    for s in SECTIONS:
        p1, p2 = nearest_points(deck, row1[s])
        ax.plot([p1.x - ox, p2.x - ox], [p1.y - oy, p2.y - oy], "-", color="#111", lw=1.2, zorder=6)
        ax.annotate(f"{s} {deck.distance(row1[s]):.0f}ft", ((p1.x + p2.x) / 2 - ox, (p1.y + p2.y) / 2 - oy),
                    fontsize=8, color="#902", fontweight="bold", zorder=7)
    ax.set_title(title, fontsize=10)
    ax.set_aspect("equal")
    ax.grid(True, ls=":", alpha=0.4)

leg = [Patch(fc="#c25d3a", label="performance core"),
       Patch(fc="#d98b5f", label="occupied deck (apron) — GOVERNED"),
       Patch(fc="#b8b0a0", label="lateral shoulder (non-occupied)"),
       Patch(fc="#3a7ca5", label="row 1"), Patch(fc="#a9cbe0", label="row 2"),
       Patch(fc="#f4e6c8", label="orchestra_event_floor (stale zone)")]
axes[0].legend(handles=leg, loc="upper left", fontsize=8, framealpha=0.9)
fig.suptitle(f"Current stage footprint vs row 1 — governed deck gap min {gov_min} ft "
             f"({'PASS' if gov_min>=GATE else 'FAIL'} ≥12); east shoulder ∩ row1 resolved by clip",
             fontsize=12)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "stage_current_geometry_gate.png"), dpi=140)
print("wrote gate csv/png + repair_candidate_shoulders_trimmed.geojson")
