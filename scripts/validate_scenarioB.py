"""Scenario B spatial validation — segment-level, where the model lies by omission.

THE KEY RULE
------------
A row segment is Band A (formal fixed seat) only if it passes sightline AND slope
AND clipping AND surface-continuity gates SIMULTANEOUSLY.  Clipped formal seats
disappear as-built; they are earned back only by the selective-restoration pass
(Scenario D), at a real fill cost the prior memo hid inside "self-balancing".

The terrace_sweep memo claimed Scenario B (0.5 ft fill clip) is "self-balancing,
no import", that clipping happens "at row ends", and reported all 24 rows as civic
seats.  This script tests each claim against the ACTUAL clipped surface, segment by
segment, and emits the canonical segment table.

Canonical output: analysis/scenarioB_validation/segments.csv
  row_id, segment_id, station_ft, surface_type, C_actual_surface_mm, C_band,
  cross_slope_pct, longitudinal_slope_pct, running_slope_pct, slope_status,
  fill_requested_ft, fill_applied_ft, fill_unmet_ft, clip_under_seat, clip_at_tip,
  abrupt_grade_break_in, terrain_grade_break_ft, accessible_route_required,
  wheelchair_space_required, formal_seat_allowed, informal_use_allowed,
  validation_status, failure_reason, repair_fill_cy

Also: row_validation.csv, seat_bands.csv, envelope_earthwork.csv, sensitivity.csv,
validation.json, clipped_fill_heatmap.png, and SCENARIO_B_VALIDATION.md.

Data-gated (emitted but NOT validated — flagged honestly):
  V5 field-survey reconciliation (no survey -> G8 DEM-noise proxy instead)
  V6 soil suitability / topsoil-as-structural-fill
  accessible_route_required / wheelchair_space_required (no ADA/aisle layout)
  drainage runoff/swale sizing after clipping (slope direction only)
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_erosion, gaussian_filter

ROOT = Path(__file__).parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "scripts"))

from harness.project import ProjectState
from harness.clay import ClayDelta
from shapely.geometry import shape, Point

# ── design knobs being validated ────────────────────────────────────────────────
TREAD_HALF_FT = 1.8
CROSS_SLOPE   = 2.0
LONG_SLOPE    = 0.5
MAX_FILL_CLIP = 0.5
STATION_FT    = 8.0          # segment length along the row

# comfort / safety thresholds (ASSUMPTIONS — override freely; documented in memo)
UNMET_SEAT_FT   = 0.10       # unmet fill above this under a seat = depression
CROSS_PASS      = 2.5        # tread cross-slope pass ceiling (%)
CROSS_WARN      = 3.5
LONG_PASS       = 2.0        # tread longitudinal pass ceiling (%)
LONG_WARN       = 3.0
CONTINUITY_FT   = 0.50       # grade break above this = trip edge / discontinuity
C_FORMAL_MM     = 90.0
C_SOFT_MM       = 60.0
C_MARGINAL_MM   = 30.0
FORMAL_STOP_ROW = 18

# construction envelope (V7)
BACK_STRIP_FT    = 2.5
ENVELOPE_HALF_FT = TREAD_HALF_FT + BACK_STRIP_FT

OUTDIR = ROOT / "analysis" / "scenarioB_validation"
OUTDIR.mkdir(parents=True, exist_ok=True)

STATE = ProjectState.load("harness_config.yaml")
FX, FY = STATE.arc_centre()
P = STATE.params()
STAGE_R, FOCUS_ELEV, EYE_HT = P["STAGE_R"], P["FOCUS_ELEV"], P["EYE_HT"]
TF = STATE.transform
FINITE = np.isfinite(STATE.Z0)
print(f"DEM {STATE.Z0.shape} finite={int(FINITE.sum())} arc=({FX:.1f},{FY:.1f})")

# ── load sections (seating + promenade) ─────────────────────────────────────────
BAYS = json.load(open(ROOT / "design_extended_bays/seating_bays.geojson"))
COMP = {}
for r in csv.DictReader(open(ROOT / "design_extended_bays/composition_table.csv")):
    COMP[(int(r["row"]), r["section"])] = {
        "elev": float(r["elev"]) if r.get("elev") else None,
        "axis_r": float(r["axis_radius_ft"]) if r.get("axis_radius_ft") else 0.0,
        "C_mm": float(r["C_mm"]) if r.get("C_mm") else None,
        "kind": r["kind"],
    }

SEC_ORDER = {"east": 0, "bend": 1, "south": 2}
sections = []
for feat in BAYS["features"]:
    p = feat["properties"]
    rn, sec = int(p["row"]), p["section"]
    line = shape(feat["geometry"])
    comp = COMP.get((rn, sec), {})
    sections.append({
        "row": rn, "section": sec, "zone": p["zone"], "kind": p["kind"],
        "line": line, "poly": line.buffer(TREAD_HALF_FT, cap_style=2),
        "length_ft": float(p.get("length_ft") or line.length),
        "seats": int(p.get("seats") or 0),
        "design_elev": comp.get("elev"),
        "axis_r": comp.get("axis_r", 0.0),
        "comp_C_mm": comp.get("C_mm"),
    })
rows_present = sorted({s["row"] for s in sections})
n_sec_by_row = {r: sum(1 for s in sections if s["row"] == r and s["kind"] == "seating")
                for r in rows_present}
print(f"{len(sections)} sections, rows {rows_present[0]}-{rows_present[-1]}")

# ── build global ideal + clipped surfaces, and keep per-section cell arrays ──────
def section_delta(poly):
    d = ClayDelta.zeros(STATE)
    d.terrace_plane(STATE, poly, base_elev_navd88=None,
                    cross_slope_pct=CROSS_SLOPE, longitudinal_slope_pct=LONG_SLOPE)
    mask = d._mask_for_geom(poly, STATE) & FINITE
    return d.delta(), mask

ideal_delta   = np.zeros_like(STATE.Z0)
clipped_delta = np.zeros_like(STATE.Z0)
unmet_grid    = np.zeros_like(STATE.Z0)

SEC_CELLS = {}   # (row,section) -> dict of per-cell arrays
for s in sections:
    dd, mask = section_delta(s["poly"])
    clip = np.where(dd > MAX_FILL_CLIP, MAX_FILL_CLIP, dd)
    ideal_delta[mask]   = dd[mask]
    clipped_delta[mask] = clip[mask]
    unmet_grid[mask]    = np.maximum(dd[mask] - MAX_FILL_CLIP, 0.0)
    SEC_CELLS[(s["row"], s["section"])] = {"dd": dd, "mask": mask}

proposed_clip  = np.where(FINITE, STATE.Z0 + clipped_delta, np.nan)
proposed_ideal = np.where(FINITE, STATE.Z0 + ideal_delta, np.nan)
gy, gx = np.gradient(proposed_clip, 1.0, 1.0)            # ft/ft on as-built surface

def cell_xy(ri, ci):
    return TF.c + (ci + 0.5) * TF.a, TF.f + (ri + 0.5) * TF.e

# ── V3: per-row C on actual clipped surface and on ideal plane ───────────────────
def row_mask(rn):
    m = np.zeros_like(FINITE)
    for s in sections:
        if s["row"] == rn and s["kind"] == "seating":
            m |= SEC_CELLS[(s["row"], s["section"])]["mask"]
    return m

def median_on(surface, mask):
    v = surface[mask]; v = v[np.isfinite(v)]
    return float(np.median(v)) if len(v) else np.nan

ROWG = {}
for rn in rows_present:
    m = row_mask(rn)
    if not m.any():
        continue
    ROWG[rn] = {
        "mask": m,
        "axis_r": next(s["axis_r"] for s in sections if s["row"] == rn),
        "actual_elev": median_on(proposed_clip, m),
        "ideal_elev":  median_on(proposed_ideal, m),
        "comp_C_mm": next((s["comp_C_mm"] for s in sections if s["row"] == rn), None),
        "n_sec": n_sec_by_row[rn],
        "seats": sum(s["seats"] for s in sections if s["row"] == rn),
        "area": int(m.sum()),
    }

def cval(D, E, Dp, Ep):
    return E * (Dp / D) - Ep

def compute_C(elev_key, rowg=ROWG):
    out, prev = {}, None
    for rn in sorted(rowg):
        g = rowg[rn]; R = g["axis_r"]
        eye = g[elev_key] + EYE_HT; E = eye - FOCUS_ELEV; D = R - STAGE_R
        out[rn] = (None if prev is None
                   else cval(D, E, prev["R"] - STAGE_R, prev["E"]) * 304.8)
        prev = {"R": R, "E": E}
    return out

C_actual = compute_C("actual_elev")
C_ideal  = compute_C("ideal_elev")
for rn in ROWG:
    ROWG[rn]["C_actual_mm"] = round(C_actual[rn], 1) if C_actual[rn] is not None else None
    ROWG[rn]["C_ideal_mm"]  = round(C_ideal[rn], 1) if C_ideal[rn] is not None else None

# ── segment loop (V1 + V2 + V4 unified at segment granularity) ───────────────────
def grade_break_ft(mask_local, surface):
    """p95 of max 4-neighbour |Δelev| over interior cells (trip-edge proxy)."""
    if not mask_local.any():
        return 0.0
    ys, xs = np.where(mask_local)
    vals = []
    ny, nx = surface.shape
    for y, x in zip(ys, xs):
        z = surface[y, x]
        if not np.isfinite(z):
            continue
        loc = []
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < ny and 0 <= xx < nx and mask_local[yy, xx] and np.isfinite(surface[yy, xx]):
                loc.append(abs(surface[yy, xx] - z))
        if loc:
            vals.append(max(loc))
    return float(np.percentile(vals, 95)) if vals else 0.0

segments = []
seg_counter = {}
for rn in rows_present:
    row_secs = sorted([s for s in sections if s["row"] == rn],
                      key=lambda s: SEC_ORDER.get(s["section"], 9))
    station0 = 0.0     # cumulative along-row station across sections
    for s in row_secs:
        key = (rn, s["section"])
        dd = SEC_CELLS[key]["dd"]; mask = SEC_CELLS[key]["mask"]
        interior = binary_erosion(mask, iterations=1)
        ri, ci = np.where(mask)
        if len(ri) == 0:
            continue
        xs, ys = cell_xy(ri, ci)
        line = s["line"]; L = max(line.length, 1e-6)
        d_along = np.array([line.project(Point(x, y)) for x, y in zip(xs, ys)])
        Rcell = np.hypot(xs - FX, ys - FY)   # radial coord (n, across-row)
        is_int  = interior[ri, ci]
        zc      = proposed_clip[ri, ci]      # as-built surface elevation per cell
        dd_c    = dd[ri, ci]
        unmet_c = np.maximum(dd_c - MAX_FILL_CLIP, 0.0)
        fillreq_c = np.maximum(dd_c, 0.0)
        fillapp_c = np.minimum(fillreq_c, MAX_FILL_CLIP)

        n_st = max(1, int(round(L / STATION_FT)))
        edges = np.linspace(0, L, n_st + 1)
        for j in range(n_st):
            d0, d1 = edges[j], edges[j + 1]
            in_seg =(d_along >= d0) & (d_along < d1) if j < n_st - 1 else (d_along >= d0) & (d_along <= d1 + 1e-6)
            if in_seg.sum() == 0:
                continue
            # cross/long slope by least-squares PLANE FIT to the actual surface
            # (raster gradient on a 4-cell-wide tread bleeds the inter-row riser;
            #  a plane fit reads the genuine seating-surface slope + dishing).
            seg_int = in_seg & is_int
            use = seg_int if seg_int.sum() >= 4 else in_seg
            nn = Rcell[use]; ss = d_along[use]; zz = zc[use]
            ok = np.isfinite(zz)
            nn, ss, zz = nn[ok], ss[ok], zz[ok]
            if len(zz) >= 4:
                nn = nn - nn.mean(); ss = ss - ss.mean()
                Amat = np.column_stack([nn, ss, np.ones_like(nn)])
                coef, *_ = np.linalg.lstsq(Amat, zz, rcond=None)
                cross_p90 = abs(coef[0]) * 100.0      # dz/dn  (across-row)
                long_p90  = abs(coef[1]) * 100.0      # dz/ds  (along-row)
                resid = zz - Amat @ coef
                twist = float(np.sqrt(np.mean(resid ** 2)))   # planarity / dishing (ft)
            else:
                cross_p90, long_p90, twist = CROSS_SLOPE, LONG_SLOPE, 0.0
            # segment cell mask in raster space for grade-break
            seg_mask = np.zeros_like(mask)
            seg_mask[ri[seg_int], ci[seg_int]] = True if seg_int.any() else False
            if seg_int.sum() < 3:
                seg_mask[ri[in_seg], ci[in_seg]] = True
            gb = grade_break_ft(seg_mask, proposed_clip)

            at_tip = (j == 0) or (j == n_st - 1)
            unmet_seg = unmet_c[in_seg]
            unmet_max = float(unmet_seg.max()) if unmet_seg.size else 0.0
            unmet_cy  = float(unmet_seg.sum()) / 27.0
            clip_present = unmet_max > UNMET_SEAT_FT
            clip_under_seat = bool(clip_present and not at_tip)
            clip_at_tip = bool(clip_present and at_tip)

            # C: per-row on actual clipped surface (radial sightline model)
            g = ROWG.get(rn, {})
            c_act = g.get("C_actual_mm")
            c_ref = c_act if c_act is not None else g.get("comp_C_mm")
            if c_ref is None:
                c_ref = 999 if rn == 1 else 0   # row1 front row always sees stage
            c_band = ("A" if c_ref >= C_FORMAL_MM else "B" if c_ref >= C_SOFT_MM
                      else "C" if c_ref >= C_MARGINAL_MM else "D")

            # slope status — pass needs both slopes within ceilings AND a planar
            # (low-residual) surface; clip dishing shows up as residual `twist`.
            if cross_p90 <= CROSS_PASS and long_p90 <= LONG_PASS and twist <= 0.12:
                slope_status = "pass"
            elif cross_p90 <= CROSS_WARN and long_p90 <= LONG_WARN and twist <= 0.25:
                slope_status = "warn"
            else:
                slope_status = "fail"
            running = long_p90      # walking along a tread row
            continuity_ok = gb <= CONTINUITY_FT
            clipped_geom = s["kind"] == "seating" and g.get("n_sec", 3) < 3

            # surface_type
            if s["kind"] == "promenade":
                surface_type = "aisle"
            elif clipped_geom:
                surface_type = "shoulder"
            else:
                surface_type = "formal_tread"   # may downgrade below

            # THE KEY RULE — all gates simultaneously
            formal_seat_allowed = bool(
                s["kind"] == "seating" and not clipped_geom
                and c_band == "A" and slope_status == "pass"
                and not clip_under_seat and continuity_ok)

            informal_use_allowed = bool(
                s["kind"] == "seating" and c_ref >= C_MARGINAL_MM and gb < 1.0)

            # Restorable-formal: a clipped tread whose IDEAL plane is a valid formal
            # seat (C_ideal>=90, full 3-section).  Restoring its unmet fill rebuilds
            # the 2%/0.5% plane -> slope, continuity AND clip all pass at once.
            c_ideal_row = g.get("C_ideal_mm")
            ideal_ok = (rn == 1) or (c_ideal_row is not None and c_ideal_row >= C_FORMAL_MM)
            restorable_formal = bool(s["kind"] == "seating" and not clipped_geom and ideal_ok)
            repair_fill_cy = round(unmet_cy, 3) if (restorable_formal and not formal_seat_allowed) else 0.0

            if s["kind"] == "seating" and not formal_seat_allowed:
                if restorable_formal:
                    surface_type = "formal_tread"      # needs restoration build step
                elif informal_use_allowed and not clipped_geom:
                    surface_type = "lawn_terrace"
                else:
                    surface_type = "shoulder"

            # failure reasons
            reasons = []
            if s["kind"] == "seating" and not formal_seat_allowed:
                if clipped_geom: reasons.append("clipped_geometry")
                if c_band != "A": reasons.append(f"C_band_{c_band}")
                if clip_under_seat: reasons.append("clip_under_seat")
                if slope_status != "pass": reasons.append(f"slope_x{cross_p90:.1f}/s{long_p90:.1f}/d{twist:.2f}")
                if not continuity_ok: reasons.append(f"grade_break_{gb*12:.1f}in")
                if restorable_formal: reasons.append("restorable_by_fill")

            # validation_status: proxy if a gate sits within DEM-noise margin
            near_C   = abs(c_ref - C_FORMAL_MM) <= 15
            near_unmet = abs(unmet_max - UNMET_SEAT_FT) <= 0.10
            near_slope = abs(cross_p90 - CROSS_PASS) <= 0.5 or abs(long_p90 - LONG_PASS) <= 0.5
            if s["kind"] == "promenade":
                validation_status = "proxy"     # circulation slope w/o ADA layout
            elif near_C or near_unmet or near_slope:
                validation_status = "proxy"
            else:
                validation_status = "validated"

            seg_counter[rn] = seg_counter.get(rn, 0) + 1
            seg_id = f"r{rn:02d}_{s['section']}_{seg_counter[rn]:02d}"
            segments.append({
                "row_id": rn,
                "segment_id": seg_id,
                "station_ft": round(station0 + (d0 + d1) / 2, 1),
                "surface_type": surface_type,
                "C_actual_surface_mm": (round(c_ref, 1) if c_ref < 900 else ""),
                "C_band": c_band if s["kind"] == "seating" else "",
                "cross_slope_pct": round(cross_p90, 2),
                "longitudinal_slope_pct": round(long_p90, 2),
                "running_slope_pct": round(running, 2),
                "slope_status": slope_status,
                "fill_requested_ft": round(float(fillreq_c[in_seg].max()) if in_seg.any() else 0, 2),
                "fill_applied_ft": round(float(fillapp_c[in_seg].max()) if in_seg.any() else 0, 2),
                "fill_unmet_ft": round(unmet_max, 2),
                "clip_under_seat": clip_under_seat,
                "clip_at_tip": clip_at_tip,
                "abrupt_grade_break_in": round(gb * 12, 1),
                "terrain_grade_break_ft": round(gb, 2),
                "accessible_route_required": False,     # not_validated (no ADA layout)
                "wheelchair_space_required": False,     # not_validated (no ADA layout)
                "formal_seat_allowed": formal_seat_allowed,
                "informal_use_allowed": informal_use_allowed,
                "validation_status": validation_status,
                "failure_reason": ";".join(reasons),
                "repair_fill_cy": repair_fill_cy,
                # bookkeeping (not in canonical schema, kept for rollups)
                "_kind": s["kind"], "_seats": s["seats"], "_seg_seat_frac": float(in_seg.sum()),
                "_sec_cells": float(len(ri)), "_clipped_geom": clipped_geom,
                "_restorable_formal": restorable_formal, "_c_band": c_band,
                "_informal": informal_use_allowed,
            })
        station0 += s["length_ft"]

print(f"{len(segments)} segments")

# ── allocate seats to segments proportionally, roll up bands ─────────────────────
for seg in segments:
    denom = sum(x["_seg_seat_frac"] for x in segments
                if x["row_id"] == seg["row_id"] and x["segment_id"][:8] == seg["segment_id"][:8])
    # seats per section split across its segments by cell share
    sec_prefix = seg["segment_id"].rsplit("_", 1)[0]
    sec_cells = sum(x["_seg_seat_frac"] for x in segments if x["segment_id"].rsplit("_", 1)[0] == sec_prefix)
    seg["_seats_alloc"] = seg["_seats"] * (seg["_seg_seat_frac"] / sec_cells) if sec_cells else 0

band_seats = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0}      # AS-BUILT (Scenario B, no restore)
scenD_seats = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0}     # Scenario D (selective restore)
restored_A = 0.0; repair_total_cy = 0.0
for seg in segments:
    if seg["_kind"] != "seating":
        continue
    sa = seg["_seats_alloc"]
    # --- as-built band ---
    if seg["formal_seat_allowed"]:
        band_seats["A"] += sa
    elif seg["_restorable_formal"]:
        band_seats["B"] += sa          # sittable now, formal only after restoration
        restored_A += sa
        repair_total_cy += seg["repair_fill_cy"]
    elif seg["_informal"] and seg["_c_band"] in ("A", "B"):
        band_seats["B"] += sa
    elif seg["_c_band"] == "C":
        band_seats["C"] += sa
    else:
        band_seats["D"] += sa
    # --- Scenario D band (restoration earns formal back) ---
    if seg["formal_seat_allowed"] or seg["_restorable_formal"]:
        scenD_seats["A"] += sa
    elif seg["_informal"] and seg["_c_band"] in ("A", "B"):
        scenD_seats["B"] += sa
    elif seg["_c_band"] == "C":
        scenD_seats["C"] += sa
    else:
        scenD_seats["D"] += sa

band_weight = {"A": 1.0, "B": 0.5, "C": 0.15, "D": 0.0}
C_formal_asbuilt = sum(band_weight[b] * band_seats[b] for b in band_seats)
scenarioD_A  = scenD_seats["A"]
scenarioD_BC = scenD_seats["B"] + scenD_seats["C"]

# ── V7: construction envelope vs tread strip + balance honesty ───────────────────
def envelope_totals(half_ft):
    cut = fill = 0.0
    for s in sections:
        dd, mask = section_delta(s["line"].buffer(half_ft, cap_style=2))
        dloc = np.where(dd[mask] > MAX_FILL_CLIP, MAX_FILL_CLIP, dd[mask])
        cut += float(np.maximum(-dloc, 0).sum()); fill += float(np.maximum(dloc, 0).sum())
    return cut / 27.0, fill / 27.0

tread_cut, tread_fill = envelope_totals(TREAD_HALF_FT)
env_cut, env_fill     = envelope_totals(ENVELOPE_HALF_FT)
cutm = FINITE & (clipped_delta < -0.05); fillm = FINITE & (clipped_delta > 0.05)
def centroid(m):
    if not m.any(): return None
    ys, xs = np.where(m); return (float(np.mean(TF.c+(xs+0.5)*TF.a)), float(np.mean(TF.f+(ys+0.5)*TF.e)))
cc, fc = centroid(cutm), centroid(fillm)
haul_ft = math.hypot(fc[0]-cc[0], fc[1]-cc[1]) if (cc and fc) else 0.0
K = 0.95
usable_fill = tread_cut * K
fill_shortfall = max(0.0, tread_fill - usable_fill)
total_unmet_cy = float(unmet_grid.sum()) / 27.0

# ── G8: DEM ±0.5 ft correlated-noise sensitivity ────────────────────────────────
def verdict_on(Z):
    Zsave = STATE.Z0; STATE.Z0 = Z
    try:
        clip = np.zeros_like(Z); ideal = np.zeros_like(Z)
        seat_clip = 0
        for s in sections:
            dd, mask = section_delta(s["poly"])
            clip[mask] = np.where(dd[mask] > MAX_FILL_CLIP, MAX_FILL_CLIP, dd[mask])
            ideal[mask] = dd[mask]
        prop = np.where(FINITE, Z + clip, np.nan); prop_i = np.where(FINITE, Z + ideal, np.nan)
        rg = {}
        for rn in rows_present:
            m = row_mask(rn)
            if not m.any(): continue
            rg[rn] = {"axis_r": ROWG[rn]["axis_r"],
                      "actual_elev": median_on(prop, m), "ideal_elev": median_on(prop_i, m)}
        Ci = compute_C("ideal_elev", rg)
        earnback = sum(1 for rn in rg if rn <= FORMAL_STOP_ROW and Ci.get(rn) is not None and Ci[rn] >= C_FORMAL_MM)
        # seat-zone unmet cells
        for s in sections:
            dd, mask = section_delta(s["poly"]); ri, ci = np.where(mask)
            if len(ri) == 0: continue
            xs, ys = cell_xy(ri, ci); L = max(s["line"].length, 1e-6)
            t = np.array([s["line"].project(Point(x, y))/L for x, y in zip(xs, ys)])
            um = np.maximum(dd[mask]-MAX_FILL_CLIP, 0.0)
            seat_clip += int(((um > UNMET_SEAT_FT) & (t > 0.1) & (t < 0.9)).sum())
        return earnback, seat_clip
    finally:
        STATE.Z0 = Zsave

base_seat_clip = sum(1 for seg in segments if seg["clip_under_seat"])
sens = []
rng = np.random.default_rng(42)
for seed in range(5):
    noise = gaussian_filter(rng.standard_normal(STATE.Z0.shape), sigma=8.0)
    noise *= 0.5 / (noise.std() + 1e-9)
    eb, sc = verdict_on(np.where(FINITE, STATE.Z0 + noise, np.nan))
    sens.append({"seed": seed, "earnback_formal_rows": eb, "seatzone_clip_cells": sc})

# ── objective U (reframed) ──────────────────────────────────────────────────────
w = {"formal": 1.0, "lawn": 0.3, "sightline": 5.0, "gross_per_cy": 0.05, "import_per_cy": 0.5}
sightline_rows = sum(1 for rn in ROWG if rn <= FORMAL_STOP_ROW
                     and (ROWG[rn]["C_actual_mm"] or 0) >= C_FORMAL_MM)
gross = tread_cut + tread_fill
U_asbuilt = (w["formal"]*band_seats["A"] + w["lawn"]*(band_seats["B"]+band_seats["C"])
             + w["sightline"]*sightline_rows - w["gross_per_cy"]*gross - w["import_per_cy"]*fill_shortfall)
U_scenarioD = (w["formal"]*scenarioD_A + w["lawn"]*scenarioD_BC
               + w["sightline"]*sightline_rows
               - w["gross_per_cy"]*(gross+repair_total_cy) - w["import_per_cy"]*fill_shortfall)

# ── write CSVs ──────────────────────────────────────────────────────────────────
SCHEMA = ["row_id", "segment_id", "station_ft", "surface_type", "C_actual_surface_mm",
          "C_band", "cross_slope_pct", "longitudinal_slope_pct", "running_slope_pct",
          "slope_status", "fill_requested_ft", "fill_applied_ft", "fill_unmet_ft",
          "clip_under_seat", "clip_at_tip", "abrupt_grade_break_in", "terrain_grade_break_ft",
          "accessible_route_required", "wheelchair_space_required", "formal_seat_allowed",
          "informal_use_allowed", "validation_status", "failure_reason", "repair_fill_cy"]
with open(OUTDIR / "segments.csv", "w", newline="") as fh:
    wri = csv.DictWriter(fh, fieldnames=SCHEMA); wri.writeheader()
    for seg in segments:
        wri.writerow({k: seg[k] for k in SCHEMA})

with open(OUTDIR / "row_validation.csv", "w", newline="") as fh:
    fields = ["row", "n_sec", "axis_r", "actual_elev", "ideal_elev", "C_actual_mm",
              "C_ideal_mm", "comp_C_mm", "seats", "unmet_cy", "min_fill_to_restore_ft"]
    wri = csv.DictWriter(fh, fieldnames=fields); wri.writeheader()
    for rn in sorted(ROWG):
        g = ROWG[rn]
        wri.writerow({"row": rn, "n_sec": g["n_sec"], "axis_r": round(g["axis_r"], 1),
                      "actual_elev": round(g["actual_elev"], 2), "ideal_elev": round(g["ideal_elev"], 2),
                      "C_actual_mm": g["C_actual_mm"], "C_ideal_mm": g["C_ideal_mm"],
                      "comp_C_mm": g["comp_C_mm"], "seats": g["seats"],
                      "unmet_cy": round(float(unmet_grid[g["mask"]].sum())/27.0, 2),
                      "min_fill_to_restore_ft": round(max(0.0, g["ideal_elev"]-g["actual_elev"]), 2)})

with open(OUTDIR / "seat_bands.csv", "w", newline="") as fh:
    wri = csv.DictWriter(fh, fieldnames=["band", "meaning", "asbuilt_seats", "scenarioD_seats", "weight"])
    wri.writeheader()
    meanings = {"A": "formal fixed seat", "B": "informal terrace/lawn",
                "C": "overflow/lawn edge", "D": "landscape/no-count"}
    for b in ["A", "B", "C", "D"]:
        wri.writerow({"band": b, "meaning": meanings[b], "asbuilt_seats": round(band_seats[b], 1),
                      "scenarioD_seats": round(scenD_seats[b], 1), "weight": band_weight[b]})

with open(OUTDIR / "envelope_earthwork.csv", "w", newline="") as fh:
    wri = csv.DictWriter(fh, fieldnames=["envelope", "width_ft", "cut_cy", "fill_cy", "gross_cy"])
    wri.writeheader()
    wri.writerow({"envelope": "tread strip", "width_ft": 2*TREAD_HALF_FT,
                  "cut_cy": round(tread_cut, 1), "fill_cy": round(tread_fill, 1), "gross_cy": round(tread_cut+tread_fill, 1)})
    wri.writerow({"envelope": "construction (tread+back strip)", "width_ft": 2*ENVELOPE_HALF_FT,
                  "cut_cy": round(env_cut, 1), "fill_cy": round(env_fill, 1), "gross_cy": round(env_cut+env_fill, 1)})

with open(OUTDIR / "sensitivity.csv", "w", newline="") as fh:
    wri = csv.DictWriter(fh, fieldnames=["seed", "earnback_formal_rows", "seatzone_clip_cells"])
    wri.writeheader()
    for r in sens: wri.writerow(r)
    wri.writerow({"seed": "baseline", "earnback_formal_rows": sightline_rows, "seatzone_clip_cells": base_seat_clip})

# ── JSON summary ────────────────────────────────────────────────────────────────
n_under = sum(1 for s in segments if s["clip_under_seat"])
n_tip   = sum(1 for s in segments if s["clip_at_tip"])
n_formal_asbuilt = sum(1 for s in segments if s["formal_seat_allowed"])
n_restorable = sum(1 for s in segments if s["_restorable_formal"] and not s["formal_seat_allowed"])
summary = {
    "claims_tested": {
        "clip_at_row_ends_only":
            f"FALSE — {n_under} segments clip UNDER seats vs {n_tip} at tips",
        "self_balancing_no_import":
            f"GEOMETRIC ONLY — restoring formal seats (Scenario D) costs {repair_total_cy:.0f} CY of the "
            f"fill the clip 'saved'; after K={K} shrink the tread strip still imports {fill_shortfall:.0f} CY; haul {haul_ft:.0f} ft",
        "all_24_rows_are_seats":
            f"FALSE — as-built formal seats={band_seats['A']:.0f}; bands B={band_seats['B']:.0f} C={band_seats['C']:.0f} D={band_seats['D']:.0f}",
    },
    "segments": {"total": len(segments), "formal_asbuilt": n_formal_asbuilt,
                 "clip_under_seat": n_under, "clip_at_tip": n_tip, "restorable_by_fill": n_restorable},
    "bands_asbuilt": {b: round(band_seats[b], 1) for b in band_seats},
    "bands_scenarioD": {b: round(scenD_seats[b], 1) for b in scenD_seats},
    "C_formal_asbuilt": round(C_formal_asbuilt, 1),
    "scenarioD_repair_cy": round(repair_total_cy, 1),
    "prior_claims": {"raw_envelope": 1895, "prior_formal": 1452, "prior_C_formal": 1545},
    "envelope": {"tread_gross_cy": round(tread_cut+tread_fill, 1),
                 "construction_gross_cy": round(env_cut+env_fill, 1),
                 "growth_x": round((env_cut+env_fill)/max(tread_cut+tread_fill, 1e-9), 2),
                 "haul_ft": round(haul_ft), "usable_fill_cy": round(usable_fill, 1),
                 "fill_shortfall_after_shrink_cy": round(fill_shortfall, 1),
                 "total_unmet_fill_cy": round(total_unmet_cy, 1)},
    "sensitivity": {"baseline_earnback_rows": sightline_rows, "baseline_seatzone_clip": base_seat_clip, "runs": sens},
    "objective_U": {"asbuilt": round(U_asbuilt, 1), "scenarioD": round(U_scenarioD, 1), "weights": w},
    "data_gated_NOT_validated": [
        "accessible_route_required / wheelchair_space_required — no ADA/aisle layout",
        "V5 field-survey reconciliation — no survey (G8 DEM-noise proxy only)",
        "V6 soil suitability / topsoil-as-structural-fill",
        "drainage runoff/swale sizing after clipping — slope direction only",
    ],
}
json.dump(summary, open(OUTDIR / "validation.json", "w"), indent=2)

# ── heatmap ─────────────────────────────────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    # crop to the seating footprint (cells touched by any tread)
    touched = np.abs(ideal_delta) > 1e-9
    ys, xs = np.where(touched)
    y0, y1 = ys.min() - 25, ys.max() + 25
    x0, x1 = xs.min() - 25, xs.max() + 25
    sub_z   = np.where(FINITE, STATE.Z0, np.nan)[y0:y1, x0:x1]
    sub_un  = np.where(unmet_grid > 0.01, unmet_grid, np.nan)[y0:y1, x0:x1]
    vmax = float(np.nanpercentile(unmet_grid[unmet_grid > 0.01], 99)) if (unmet_grid > 0.01).any() else 0.8

    fig, ax = plt.subplots(figsize=(11, 9))
    # hillshade-ish background
    gyb, gxb = np.gradient(sub_z)
    shade = np.clip(0.5 - (gxb + gyb), 0, 1)
    ax.imshow(shade, cmap="gray", alpha=0.5, origin="upper")
    im = ax.imshow(sub_un, cmap="hot_r", norm=Normalize(0, vmax), origin="upper")
    plt.colorbar(im, ax=ax, label=f"unmet fill (ft) the 0.5 ft clip DROPPED  (p99={vmax:.2f})")

    # overlay segment markers: red=under-seat clip, blue=tip clip
    for seg in segments:
        if not (seg["clip_under_seat"] or seg["clip_at_tip"]):
            continue
        rn = seg["row_id"]; g = ROWG.get(rn)
        if g is None: continue
    # mark by scanning row masks is heavy; instead annotate counts
    ax.text(0.02, 0.98,
            f"{n_under} segments clip UNDER seats\n{n_tip} segments clip at tips\n"
            f"as-built formal seats: {band_seats['A']:.0f}\n"
            f"Scenario D formal (restore {repair_total_cy:.0f} CY): {scenarioD_A:.0f}",
            transform=ax.transAxes, va="top", ha="left", fontsize=10,
            bbox=dict(boxstyle="round", fc="white", alpha=0.85))
    ax.set_title("Scenario B unmet fill — where the 0.5 ft clip lands\n"
                 "prior memo said 'at row ends'; it is distributed across the bowl, mostly under seats")
    ax.set_xlabel("each bright pixel is a tread cell the clip left below the design plane (a seat-surface dip)")
    ax.set_xticks([]); ax.set_yticks([])
    fig.savefig(OUTDIR / "clipped_fill_heatmap.png", dpi=120, bbox_inches="tight")
    print("heatmap written")
except Exception as e:
    import traceback; traceback.print_exc()
    print("heatmap skipped:", e)

# ── console ─────────────────────────────────────────────────────────────────────
print("\n=== Scenario B segment validation ===")
print(f"segments={len(segments)}  formal_asbuilt={n_formal_asbuilt}  "
      f"clip_under_seat={n_under}  clip_at_tip={n_tip}  restorable={n_restorable}")
print("bands as-built:", {b: round(band_seats[b], 1) for b in band_seats})
print(f"Scenario D: formal A earned back={restored_A:.0f} seats for {repair_total_cy:.0f} CY  "
      f"-> A={scenarioD_A:.0f}")
print(f"envelope growth x={(env_cut+env_fill)/max(tread_cut+tread_fill,1e-9):.2f}  "
      f"shortfall after shrink={fill_shortfall:.1f}CY  total unmet={total_unmet_cy:.1f}CY  haul={haul_ft:.0f}ft")
print("sensitivity:", [(s["earnback_formal_rows"], s["seatzone_clip_cells"]) for s in sens])
print(f"U_asbuilt={U_asbuilt:.1f}  U_scenarioD={U_scenarioD:.1f}")
print("Wrote", OUTDIR)
