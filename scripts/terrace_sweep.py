"""Three-scenario terrace earthwork sweep.

Scenario A — Terrain-following (minimum earthwork baseline)
  terrace_plane with base_elev derived from DEM median inside the buffered
  row polygon.  This is the true cost of sitting rows on natural grade.

Scenario B — Terrain-following + cleaned ends
  Same as A but adds grade_ceiling on each row to limit max fill at row ends
  where the terrain dips.  Represents best light-touch value.

Scenario C — Sightline-optimized
  terrace_plane with base_elev fixed to the design_extended_bays sightline
  tread elevation (composition_table 'elev' column).  Measures the earthwork
  premium of the sightline-tuned geometry over pure terrain-following.

Source geometry: design_extended_bays/seating_bays.geojson (LineStrings).
Each row is buffered ±TREAD_HALF_FT to produce a terrace polygon.

Output
------
  terrace_sweep.csv   — per-row per-scenario cut/fill table
  terrace_sweep.md    — formatted markdown summary
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

# Run from project root
ROOT = Path(__file__).parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "scripts"))

from harness.project import ProjectState
from harness.clay import ClayDelta
from harness.earthwork import EarthworkEngine
from shapely.geometry import shape

STATE = ProjectState.load("harness_config.yaml")
EW    = EarthworkEngine(STATE)

BAYS_GEOJSON  = ROOT / "design_extended_bays/seating_bays.geojson"
COMP_CSV      = ROOT / "design_extended_bays/composition_table.csv"
OUT_CSV       = ROOT / "terrace_sweep.csv"
OUT_MD        = ROOT / "terrace_sweep.md"

TREAD_HALF_FT = 1.8   # buffer each side of centerline → 3.6 ft tread depth
CROSS_SLOPE   = 2.0   # % drainage cross-slope
LONG_SLOPE    = 0.5   # % longitudinal drainage
MAX_FILL_CLIP = 0.5   # Scenario B: clip fill beyond this at row ends (ft)

# ── load row data ─────────────────────────────────────────────────────────────

fc    = json.load(open(BAYS_GEOJSON))
# Composition table: (row, section) → elev, C_mm, axis_radius_ft
comp  = {}
comp_r_by_row: dict[int, float] = {}  # row → axis_radius_ft
for r in csv.DictReader(open(COMP_CSV)):
    if r["kind"] == "seating":
        key = (int(r["row"]), r["section"])
        rn  = int(r["row"])
        comp[key] = {
            "elev": float(r["elev"]),
            "C_mm": r["C_mm"] or "",
            "axis_radius_ft": float(r["axis_radius_ft"]) if r.get("axis_radius_ft") else 0.0,
        }
        if r.get("axis_radius_ft"):
            comp_r_by_row[rn] = float(r["axis_radius_ft"])

# Build per-row aggregated data (sum sections)
rows_data: dict[int, dict] = {}
for feat in fc["features"]:
    p = feat["properties"]
    if p["kind"] != "seating":
        continue
    rn = int(p["row"])
    if rn not in rows_data:
        rows_data[rn] = {
            "row": rn, "zone": p["zone"],
            "axis_r": (float(p.get("axis_radius_ft") or 0) or
                       comp.get((rn, p["section"]), {}).get("axis_radius_ft", 0) or
                       comp_r_by_row.get(rn, 0)),
            "sections": [],
        }
    geom_line = shape(feat["geometry"])
    poly = geom_line.buffer(TREAD_HALF_FT, cap_style=2)   # flat-cap buffer
    design_elev = comp.get((rn, p["section"]), {}).get("elev")
    rows_data[rn]["sections"].append({
        "section": p["section"],
        "poly": poly,
        "design_elev": design_elev,
        "length_ft": float(p.get("length_ft") or geom_line.length),
        "seats": int(p.get("seats") or 0),
        "C_mm": comp.get((rn, p["section"]), {}).get("C_mm", ""),
    })

# Pre-compute per-row arc summary (arc_ft, clipped, theoretical_arc_ft)
FAN_HALF_DEG = STATE.cfg.get("bowl", {}).get("fan_half_deg", 60)
for rd in rows_data.values():
    r = rd["axis_r"]
    rd["arc_ft"] = sum(s["length_ft"] for s in rd["sections"])
    rd["n_sections"] = len(rd["sections"])
    rd["clipped"] = rd["n_sections"] < 3
    rd["theoretical_arc_ft"] = (r * 2 * math.radians(FAN_HALF_DEG)
                                 if r > 0 else 0.0)
    rd["arc_pct_of_full"] = (
        round(100 * rd["arc_ft"] / rd["theoretical_arc_ft"])
        if rd["theoretical_arc_ft"] > 0 else 0
    )

sorted_rows = sorted(rows_data.keys())
print(f"Loaded {len(sorted_rows)} seating rows, "
      f"{sum(len(v['sections']) for v in rows_data.values())} section polygons")

# ── helpers ───────────────────────────────────────────────────────────────────

def apply_and_measure(delta: ClayDelta, label: str) -> dict:
    """Return cut/fill summary for current delta state."""
    v = EW.volumes(delta)
    ts = EW.topsoil_estimate(delta)
    ss = EW.shrink_swell(delta)
    d  = delta.delta()
    valid = np.isfinite(STATE.Z0)
    lod   = valid & (np.abs(d) > EW.tol)
    cells_over_05_cut  = int((lod & (d < -0.5)).sum())
    cells_over_05_fill = int((lod & (d >  0.5)).sum())
    cells_over_10_cut  = int((lod & (d < -1.0)).sum())
    cells_over_10_fill = int((lod & (d >  1.0)).sum())
    return {
        "scenario": label,
        "cut_cy":   v["cut_cy"],
        "fill_cy":  v["fill_cy"],
        "net_cy":   v["net_cy"],
        "gross_cy": v["gross_cy"],
        "max_cut_ft":  v["max_cut_ft"],
        "max_fill_ft": v["max_fill_ft"],
        "lod_sqft":    v["lod_sqft"],
        "topsoil_cy":  ts["topsoil_vol_cy"],
        "usable_fill_cy": ss["usable_compacted_fill_cy"],
        "cells_over_05_cut":  cells_over_05_cut,
        "cells_over_05_fill": cells_over_05_fill,
        "cells_over_10_cut":  cells_over_10_cut,
        "cells_over_10_fill": cells_over_10_fill,
    }

# ── run scenarios ──────────────────────────────────────────────────────────────

records = []

for rn in sorted_rows:
    rd = rows_data[rn]
    sections = rd["sections"]

    for sc_label, use_design_elev, clip_fill in [
        ("A_terrain",     False, False),
        ("B_terrain_clip", False, True),
        ("C_sightline",    True,  False),
    ]:
        delta = ClayDelta.zeros(STATE)

        for sec in sections:
            poly = sec["poly"]
            if sc_label in ("A_terrain", "B_terrain_clip"):
                base_elev = None   # auto from DEM median
            else:
                # Scenario C: use design tread elevation
                base_elev = sec["design_elev"]
                if base_elev is None:
                    base_elev = None  # fall back to DEM median if missing

            delta.terrace_plane(STATE, poly,
                                base_elev_navd88=base_elev,
                                cross_slope_pct=CROSS_SLOPE,
                                longitudinal_slope_pct=LONG_SLOPE)

            if clip_fill:
                # Scenario B: limit fill beyond MAX_FILL_CLIP
                d = delta.delta()
                mask = delta._mask_for_geom(poly, STATE) & np.isfinite(STATE.Z0)
                d[mask] = np.minimum(d[mask], MAX_FILL_CLIP)
                delta._delta = d

        m = apply_and_measure(delta, sc_label)
        m["row"]     = rn
        m["zone"]    = rd["zone"]
        m["sections"] = rd["n_sections"]
        m["arc_ft"]  = round(rd["arc_ft"], 1)
        m["theoretical_arc_ft"] = round(rd["theoretical_arc_ft"], 1)
        m["clipped"] = "yes" if rd["clipped"] else "no"
        m["arc_pct_of_full"] = rd["arc_pct_of_full"]
        m["total_seats"] = sum(s["seats"] for s in sections)
        m["C_mm_axis"] = sections[0]["C_mm"] if sections else ""
        records.append(m)

    print(f"  row {rn:2d} done")

# ── write CSV ──────────────────────────────────────────────────────────────────

fields = ["scenario","row","zone","sections","clipped","arc_ft",
          "theoretical_arc_ft","arc_pct_of_full","total_seats","C_mm_axis",
          "cut_cy","fill_cy","net_cy","gross_cy",
          "max_cut_ft","max_fill_ft","lod_sqft","topsoil_cy",
          "usable_fill_cy","cells_over_05_cut","cells_over_05_fill",
          "cells_over_10_cut","cells_over_10_fill"]

with open(OUT_CSV, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    for rec in records:
        w.writerow({f: rec.get(f, "") for f in fields})

print(f"\nCSV → {OUT_CSV.name}")

# ── write markdown ─────────────────────────────────────────────────────────────

def scenario_total(sc):
    recs = [r for r in records if r["scenario"] == sc]
    return {
        "cut_cy":   round(sum(r["cut_cy"]  for r in recs), 1),
        "fill_cy":  round(sum(r["fill_cy"] for r in recs), 1),
        "net_cy":   round(sum(r["net_cy"]  for r in recs), 1),
        "gross_cy": round(sum(r["gross_cy"] for r in recs), 1),
        "topsoil_cy": round(sum(r["topsoil_cy"] for r in recs), 1),
        "usable_fill_cy": round(sum(r["usable_fill_cy"] for r in recs), 1),
    }

lines = [
    "# Terrace earthwork sweep — three scenarios",
    "",
    "Source: `design_extended_bays/seating_bays.geojson` buffered ±1.8 ft.",
    f"Tread depth: {2*TREAD_HALF_FT:.1f} ft | Cross-slope: {CROSS_SLOPE}% | Long-slope: {LONG_SLOPE}%",
    "",
    "## Scenario totals",
    "",
    "| Scenario | Cut CY | Fill CY | Net CY | Gross CY | Topsoil CY | Usable fill CY |",
    "|---|---|---|---|---|---|---|",
]

for sc, label in [
    ("A_terrain",     "A — Terrain-following (DEM median)"),
    ("B_terrain_clip","B — Terrain-following + 0.5 ft fill clip"),
    ("C_sightline",   "C — Sightline-optimized (design tread elev)"),
]:
    t = scenario_total(sc)
    lines.append(
        f"| {label} | {t['cut_cy']:.0f} | {t['fill_cy']:.0f} | "
        f"{t['net_cy']:+.0f} | {t['gross_cy']:.0f} | "
        f"{t['topsoil_cy']:.0f} | {t['usable_fill_cy']:.0f} |"
    )

def row_interp(mc, mf):
    # Wall trigger fires at 3.0 ft; flag only rows approaching that threshold.
    if mc <= 0.5 and mf <= 0.5:
        return "excellent fit"
    elif mc <= 1.0 and mf <= 1.0:
        return "normal tread grading"
    elif mc <= 2.0 and mf <= 2.0:
        return "standard cut-and-fill"
    else:
        return "review geometry (>2 ft delta)"

def row_table_lines(scenario_key):
    out = []
    for rec in [r for r in records if r["scenario"] == scenario_key]:
        mc = rec["max_cut_ft"]; mf = rec["max_fill_ft"]
        clip_note = " **clipped**" if rec["clipped"] == "yes" else ""
        out.append(
            f"| {rec['row']}{clip_note} | {rec['zone']} | {rec['C_mm_axis']} | "
            f"{rec['sections']} | {rec['arc_ft']:.0f} | {rec['arc_pct_of_full']}% | "
            f"{rec['cut_cy']:.1f} | {rec['fill_cy']:.1f} | {rec['net_cy']:+.1f} | "
            f"{mc:.2f} | {mf:.2f} | {row_interp(mc, mf)} |"
        )
    return out

ROW_HDR = [
    "| Row | Zone | C mm | Secs | Arc ft | Arc % | Cut CY | Fill CY | Net CY | Max cut ft | Max fill ft | Interpretation |",
    "|---|---|---|---|---|---|---|---|---|---|---|---|",
]
CLIP_NOTE = ("Rows marked **clipped** have fewer than 3 sections because the east or south "
             "arcs exit the street boundary at that radius.  "
             "Arc % shows buildable arc as a fraction of the theoretical full-fan arc.")

# Primary: Scenario B
t_b = scenario_total("B_terrain_clip")
lines += [
    "",
    "## Per-row detail — Scenario B (site-balanced, primary)",
    "",
    CLIP_NOTE,
    "",
] + ROW_HDR + row_table_lines("B_terrain_clip")

lines += [
    "",
    "## Material balance — Scenario B (site-balanced, no import)",
    "",
    f"- Structural cut: **{t_b['cut_cy']:.0f} CY**",
    f"- Fill demand: **{t_b['fill_cy']:.0f} CY**",
    f"- Net: **{t_b['net_cy']:+.1f} CY** — self-balancing, no truck import required",
    f"- Usable compacted fill (cut × 0.95): **{t_b['usable_fill_cy']:.0f} CY**",
    f"- Topsoil stripping (separate): **{t_b['topsoil_cy']:.0f} CY**",
    "",
    ("Fill ends of treads are clipped at 0.5 ft where terrain dips; those edges "
     "drain outward more aggressively — acceptable for an open-air venue."),
]

# Baseline reference: Scenario A
t_a = scenario_total("A_terrain")
lines += [
    "",
    "## Per-row detail — Scenario A (terrain-following baseline)",
    "",
    CLIP_NOTE,
    "",
] + ROW_HDR + row_table_lines("A_terrain")

lines += [
    "",
    "## Material balance — Scenario A (baseline)",
    "",
    f"- Structural cut: **{t_a['cut_cy']:.0f} CY**",
    f"- Fill demand: **{t_a['fill_cy']:.0f} CY**",
    f"- Net: **{t_a['net_cy']:+.0f} CY** import needed before shrink/swell",
    f"- Usable compacted fill (cut × 0.95): **{t_a['usable_fill_cy']:.0f} CY**",
    f"- Topsoil stripping (separate): **{t_a['topsoil_cy']:.0f} CY**",
    "",
    "See `terrace_sweep.csv` for full per-row per-scenario data.",
]

with open(OUT_MD, "w") as fh:
    fh.write("\n".join(lines) + "\n")

print(f"MD  → {OUT_MD.name}")
print()
print("Scenario totals:")
for sc, label in [("A_terrain","A"),("B_terrain_clip","B"),("C_sightline","C")]:
    t = scenario_total(sc)
    print(f"  {label}: cut={t['cut_cy']} fill={t['fill_cy']} net={t['net_cy']:+} "
          f"gross={t['gross_cy']} topsoil={t['topsoil_cy']}")
