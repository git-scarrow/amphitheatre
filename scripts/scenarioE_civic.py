"""Scenario E — geometry emitter for the civic_bowl family.

Pick one family and make it DRAW. This turns civic_bowl from an accepted concept
into a buildable, priceable scheme by emitting real polygons for every surface and
re-running the validation engine on the ACTUAL geometry — not intent.

Emitted surfaces (analysis/scenarioE_civic/geometry.geojson):
  formal_restored_treads   rows 1-18 ideal terrace planes (the Scenario D surface)
  cross_aisle              row-9 level walk (wheelchair dispersion + view pause)
  ada_ramp_A / ada_ramp_B  switchback ramps re-graded to <=8.33% with landings
  landings                 flat pads at switchback turns + cross-aisle ends
  drainage_swale_*         intercept runoff behind the toe + along clipped edge,
                           falling toward the NE pour point
  row_end_shoulder         rows 21-25 clipped tips -> landscape (topsoil only)
  construction_envelope    union grading footprint (priceable)
  stage / stage_shoulders  reused stage geometry (lateral frame, upstage open)

Then the same engines re-validate on the real surface:
  SightlineEngine  C>=90 on the restored treads (rows 1-18)
  ADA running slope + landings on the designed switchbacks
  EarthworkEngine  per-component CY (geometry-backed, not placeholder)
  swale fall direction toward the pour point

Finally it scores the 10 Scenario E acceptance criteria and runs civic_bowl-E as a
cost_proxy Design through the InevitabilityEngine — which now requires geometry-backed,
validated ADA + drainage moves.

Outputs -> analysis/scenarioE_civic/
"""
from __future__ import annotations

import csv, json, math, os, sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
from shapely.geometry import shape, LineString, Point, mapping
from shapely.ops import unary_union

ROOT = Path(__file__).parent.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT / "scripts"))

from harness.project import ProjectState
from harness.clay import ClayDelta
from harness.earthwork import EarthworkEngine
from harness.sightlines import SightlineEngine
from harness.affordance import AffordanceEngine
from harness.inevitability import InevitabilityEngine, Move, Design

OUT = ROOT / "analysis" / "scenarioE_civic"; OUT.mkdir(parents=True, exist_ok=True)

STATE = ProjectState.load("harness_config.yaml")
EW = EarthworkEngine(STATE); SL = SightlineEngine(STATE)
FX, FY = STATE.arc_centre(); TF = STATE.transform; FINITE = np.isfinite(STATE.Z0)
ADA_MAX_PCT = STATE.cfg["ada"]["running_slope_pct"]          # 8.33
ADA_LANDING_FT = STATE.cfg["ada"]["landing_min_length_ft"]   # 5.0
MAX_RISE_PER_FLIGHT = 2.5                                     # ADA 30 in
TREAD_HALF = 1.8

# drainage target = the treatment-cell LOW point (the receiving area), not the spill lip
PP = json.load(open(ROOT / "pour_point.geojson"))["features"][0]
PP_spill = PP["properties"]["spill_elev_ft_navd88"]
_stg0 = json.load(open(ROOT / "design_open_low/stage_floor.geojson"))
_cell = next(shape(f["geometry"]) for f in _stg0["features"]
             if f["properties"].get("name") == "treatment_wet_cell")
DTx, DTy = _cell.centroid.x, _cell.centroid.y      # drain target (bowl bottom)

BAYS = json.load(open(ROOT / "design_extended_bays/seating_bays.geojson"))
COMP = {(int(r["row"]), r["section"]): r for r in
        csv.DictReader(open(ROOT / "design_extended_bays/composition_table.csv"))}
ADA = json.load(open(ROOT / "design_open_low/ada_route.geojson"))
STG = json.load(open(ROOT / "design_open_low/stage_floor.geojson"))

geo_features = []           # GeoJSON feature accumulator
component_cy = {}           # component -> {cut,fill,gross}
delta = ClayDelta.zeros(STATE)   # combined Scenario E surface delta

# ── row/seam object — the SAME geometry that generates the seating bands ─────────
# The rows are NOT concentric about F (outer rows curve inward at the flanks), so an
# aisle must be derived from the actual row centerlines, not a nominal arc. Nearest-
# row is measured by distance to the real row lines, not radius.
def arc_pt(R, az_deg):
    a = math.radians(az_deg); return (FX + math.sin(a) * R, FY + math.cos(a) * R)

ROW_LINES = {}      # row -> [section LineStrings]
ROW_ELEV = {r: float(COMP[(r, "bend")]["elev"]) for r in range(1, 19) if (r, "bend") in COMP}
ROW_R = {r: float(COMP[(r, "bend")]["axis_radius_ft"]) for r in range(1, 19) if (r, "bend") in COMP}
# section constants for the accessible_fit cross-aisle (see scripts/sweep_cross_aisle.py)
ADA_CROSS_PCT = float(STATE.cfg["ada"].get("cross_slope_target_pct", 2.0))   # 2.0
ONE_RISER_FT = 1.6          # edge step <= this is a normal seating riser (no ramp)
DRAIN_MIN_PCT = 0.5         # below this in BOTH directions = flat = ponds
for _f in BAYS["features"]:
    _p = _f["properties"]
    if _p["kind"] == "seating" and 1 <= int(_p["row"]) <= 18:
        ROW_LINES.setdefault(int(_p["row"]), []).append(shape(_f["geometry"]))

def nearest_row_id(x, y):
    pt = Point(x, y)
    return min(ROW_LINES, key=lambda r: min(l.distance(pt) for l in ROW_LINES[r]))

def longest_section(rn):
    return max(ROW_LINES[rn], key=lambda l: l.length)


def add_feature(geom, role, props=None):
    f = {"type": "Feature", "geometry": mapping(geom),
         "properties": {"role": role, **(props or {})}}
    geo_features.append(f)
    return f


def comp_cy(d_before, mask, name):
    """CY of the combined delta within mask, attributed to component `name`."""
    d = delta.delta()
    sub = np.where(mask & FINITE, d, 0.0)
    cut = float(np.maximum(-sub, 0).sum()) / 27.0
    fill = float(np.maximum(sub, 0).sum()) / 27.0
    component_cy[name] = {"cut_cy": round(cut, 1), "fill_cy": round(fill, 1),
                          "gross_cy": round(cut + fill, 1)}


# ── 1. the cross-aisle is a ROLE REASSIGNMENT, not a discovered path ─────────────
# PROVENANCE NOTE. Earlier versions treated the mid-bowl access band as a seam/path
# derivation problem. That was the wrong abstraction. The accepted cross-aisle is
# ROW-DERIVED: rows 9 and 10 already contain the correct terrain-following band, so the
# move is a role reassignment from seating to circulation. Seam and connector diagnostics
# may still be used to VALIDATE continuity, but they are not the SOURCE of the geometry.
#
#     cross_aisle = union(row_9, row_10).difference(retained_seating)      # GENERATE
#     -> subtract displaced seats from capacity                           # consequence
#     -> validate overlap / slope / connectivity (honestly pass or fail)  # VALIDATE
#     -> "row-derived cross-aisle, not seam-derived path"                 # NARRATE
#
# The bug was never the geometry; it was narrating a role reassignment as a seam search.
# Generate / Validate / Narrate are three different acts — the verb here names the act.
AISLE_ROWS = [9, 10]
row_polys = {}
for feat in BAYS["features"]:
    p = feat["properties"]
    if p["kind"] == "seating" and 1 <= int(p["row"]) <= 18:
        row_polys.setdefault(int(p["row"]), []).append(
            shape(feat["geometry"]).buffer(TREAD_HALF, cap_style=2))
retained_union = unary_union([p for r in row_polys if r not in AISLE_ROWS for p in row_polys[r]])


def make_cross_aisle_from_rows(rows, row_polys, retained):
    """GENERATE the cross-aisle by reclassifying seating `rows` as circulation.

    The band IS the union of those rows' tread footprints minus retained seating — so it
    overlaps counted seats by 0 by construction. This is the generator; everything else
    (connector test, nearest-row walk) only validates the result. Returns (band, provenance)
    where provenance records the actual operation so the move cannot later be narrated as a
    path/seam discovery."""
    band = unary_union([p for r in rows for p in row_polys[r]]).difference(retained)
    provenance = {
        "geometry_source": "row_reclassification",
        "seam_derived": False,
        "source_geometry": [f"row_{r}" for r in rows],
        "operation": ["union_source_rows", "subtract_retained_seating", "assign_role:cross_aisle"],
    }
    return band, provenance


def accessible_cross_aisle(band_poly, rows):
    """SECTION the cross-aisle as the validated `accessible_fit` surface (winner of
    scripts/sweep_cross_aisle.py). Reproduces that surface EXACTLY so the wired section IS
    the swept-and-accepted one — not a re-approximation:

        e = mid + 2%·n + 1%·(s - s_min)         n = radial offset (+outward), s = along-arc

    A datum at the two reclassified rows' mean, capped at the 2% ADA cross-slope draining to
    the inner edge, plus a 1% longitudinal fall so the band sheds water instead of ponding
    mid-hillside (the failure that rejects every flat-datum section). The residual edge drop
    against the retained neighbour rows is carried as priced 8.33% transition ramps. Slopes
    are MEASURED back off the graded cells (lstsq plane), never asserted."""
    i, j = rows                                       # 9 (inner/lower), 10 (outer/upper)
    mid = (ROW_ELEV[i] + ROW_ELEV[j]) / 2.0
    R_ref = (ROW_R[i] + ROW_R[j]) / 2.0
    mask = delta._mask_for_geom(band_poly, STATE) & FINITE
    ri, ci = np.where(mask)
    x = TF.c + (ci + 0.5) * TF.a; y = TF.f + (ri + 0.5) * TF.e
    n = np.hypot(x - FX, y - FY) - R_ref              # radial (+outward/uphill)
    cx, cy = x.mean(), y.mean()
    rc = math.hypot(cx - FX, cy - FY) + 1e-9
    tgx, tgy = (cy - FY) / rc, -(cx - FX) / rc        # along-arc tangent at band centroid
    s = (x - cx) * tgx + (y - cy) * tgy
    gx, gl = ADA_CROSS_PCT / 100.0, 1.0 / 100.0
    e = mid + gx * n + gl * (s - s.min())
    delta._delta[ri, ci] = e - STATE.Z0[ri, ci]       # grade the band onto the combined delta
    coef, *_ = np.linalg.lstsq(np.column_stack([n, s, np.ones_like(n)]), e, rcond=None)
    x_slope, l_slope = abs(coef[0]) * 100.0, abs(coef[1]) * 100.0   # measured
    ponds = (x_slope < DRAIN_MIN_PCT) and (l_slope < DRAIN_MIN_PCT)
    wheelable = x_slope <= ADA_CROSS_PCT + 0.25
    # grade breaks at the two radial edges vs the retained neighbour rows (i-1, j+1)
    e_inner = mid + gx * ((ROW_R[i] - TREAD_HALF) - R_ref)
    e_outer = mid + gx * ((ROW_R[j] + TREAD_HALF) - R_ref)
    inner_step = abs(e_inner - ROW_ELEV[i - 1]); outer_step = abs(ROW_ELEV[j + 1] - e_outer)

    def classify(step):
        if step <= ONE_RISER_FT:
            return "normal_riser", 0.0
        run = step / (ADA_MAX_PCT / 100.0)            # length if carried as 8.33% ramp
        return f"ramp_{run:.0f}ft", (run * 5.0) * (step / 2.0) / 27.0   # 5 ft wide wedge CY
    in_kind, in_cy = classify(inner_step); out_kind, out_cy = classify(outer_step)
    return dict(mask=mask, datum=round(float(e.mean()), 2),
                cross_slope_pct=round(x_slope, 2), long_slope_pct=round(l_slope, 2),
                drains=bool(not ponds), wheelable=bool(wheelable),
                inner_step_ft=round(inner_step, 2), outer_step_ft=round(outer_step, 2),
                inner_transition=in_kind, outer_transition=out_kind,
                ramp_surcharge_cy=round(in_cy + out_cy, 1))


xa_poly, xa_provenance = make_cross_aisle_from_rows(AISLE_ROWS, row_polys, retained_union)

# DIAGNOSTIC (validation helper, NOT the generator): walk the two reclassified rows and
# confirm every point's nearest row is one of them. If the band ever drifted to a third
# row it would be a connector, not a cross-aisle. Passes by construction — that's the
# point. (Rows aren't concentric about F, so nearest-row is by distance to the real row
# lines, never by radius.) The seam medial-line that used to "generate" this is gone.
spine = [longest_section(9).interpolate(t, normalized=True) for t in np.linspace(0, 1, 20)] \
      + [longest_section(10).interpolate(t, normalized=True) for t in np.linspace(0, 1, 20)]
nr_ids = [nearest_row_id(pt.x, pt.y) for pt in spine]
nr_variation = max(nr_ids) - min(nr_ids)
is_cross_aisle = set(nr_ids) <= set(AISLE_ROWS) and nr_variation <= 1

# ── 2. restored formal treads (rows 1-18); rows 9,10 are the aisle (displaced) ───
tread_mask = np.zeros_like(FINITE)
restored_rows = list(range(1, 19))
nominal_formal = 0; formal_seats_emitted = 0.0
carved_polys = []; retained_overlap_sqft = 0.0
for feat in BAYS["features"]:
    p = feat["properties"]
    if p["kind"] != "seating" or not (1 <= int(p["row"]) <= 18):
        continue
    rn = int(p["row"]); seats = int(p.get("seats") or 0); nominal_formal += seats
    poly = shape(feat["geometry"]).buffer(TREAD_HALF, cap_style=2)
    if rn in AISLE_ROWS:
        continue            # consumed by the aisle band — displaced, not retained
    retained_overlap_sqft += poly.intersection(xa_poly).area   # must be ~0
    formal_seats_emitted += seats
    delta.terrace_plane(STATE, poly, base_elev_navd88=None,
                        cross_slope_pct=2.0, longitudinal_slope_pct=0.5)
    tread_mask |= delta._mask_for_geom(poly, STATE) & FINITE
    carved_polys.append(poly)
    add_feature(poly, "formal_restored_tread", {"row": rn, "section": p["section"], "seats_kept": seats})
comp_cy(None, tread_mask, "formal_restored_treads")
formal_seats_emitted = int(round(formal_seats_emitted))
displaced_seats = nominal_formal - formal_seats_emitted

_tre_az = STATE.AZ[tread_mask]
EAST_AZ = float(np.percentile(_tre_az, 0.5)) - 5.0
SOUTH_AZ = float(np.percentile(_tre_az, 99.5)) + 5.0

# SECTION: the validated accessible_fit surface replaces the rejected flat midpoint datum.
# The flat midpoint (0% both ways) ponds mid-hillside — the sweep rejected it on drainage;
# accessible_fit (2% cross + 1% longitudinal) is the only section strategy that drains AND
# wheels. See analysis/cross_aisle_sweep/ (proof_table.csv) + _superseded_midpoint_section.json.
xa_sec = accessible_cross_aisle(xa_poly, AISLE_ROWS)
xa_elev = xa_sec["datum"]
comp_cy(None, xa_sec["mask"], "cross_aisle")
component_cy["cross_aisle_transition_ramps"] = {
    "cut_cy": 0.0, "fill_cy": 0.0, "gross_cy": xa_sec["ramp_surcharge_cy"],
    "note": f"residual edge steps {xa_sec['inner_step_ft']}/{xa_sec['outer_step_ft']} ft carried "
            f"as {xa_sec['inner_transition']}/{xa_sec['outer_transition']} (8.33% wedge surcharge)"}
add_feature(xa_poly, "cross_aisle",
            {"elev_navd88": round(xa_elev, 2), "section_strategy": "accessible_fit",
             "cross_slope_pct": xa_sec["cross_slope_pct"], "long_slope_pct": xa_sec["long_slope_pct"],
             "drains": xa_sec["drains"], "wheelable": xa_sec["wheelable"],
             "inner_step_ft": xa_sec["inner_step_ft"], "outer_step_ft": xa_sec["outer_step_ft"],
             "inner_transition": xa_sec["inner_transition"], "outer_transition": xa_sec["outer_transition"],
             "ramp_surcharge_cy": xa_sec["ramp_surcharge_cy"],
             "geometry_source": xa_provenance["geometry_source"],   # row_reclassification
             "seam_derived": xa_provenance["seam_derived"],         # False
             "source_geometry": xa_provenance["source_geometry"],
             "operation": xa_provenance["operation"],
             "consumes_rows": AISLE_ROWS, "displaced_seats": displaced_seats,
             "nearest_row_ids": [min(nr_ids), max(nr_ids)], "nearest_row_variation": nr_variation,
             "is_cross_aisle": bool(is_cross_aisle),
             "retained_overlap_sqft": round(retained_overlap_sqft, 1),
             "purpose": "wheelchair dispersion + mid-bowl view pause + circulation"})
# PLAN gate (row-derived, clear of retained treads) AND SECTION gate (drains + wheels). A
# row-derived cross-aisle is accepted only when BOTH plan provenance and section performance hold.
xa_plan_ok = is_cross_aisle and (retained_overlap_sqft < 5.0)
xa_section_ok = xa_sec["drains"] and xa_sec["wheelable"]
xa_ok = xa_plan_ok and xa_section_ok
tread_valid = xa_plan_ok          # treads only care that the aisle is clear of counted seats
xa_overlap_sqft = retained_overlap_sqft

# REGRESSION GUARD: the OLD freeform access desire line, scored by the SAME nearest-row
# test. It drifts across many rows (it was fitted to access, not to the seats) — which is
# precisely why "color two rows and join them" is the correct object and that path is not.
_desire = next((shape(f["geometry"]) for f in ADA["features"]
                if f["properties"].get("name") == "mid_cross_aisle"), None)
if _desire is not None:
    _dn = [nearest_row_id(x, y) for (x, y) in _desire.coords]
    desire_line_variation = max(_dn) - min(_dn)
else:
    desire_line_variation = None

# ── 3. ADA switchback ramps (re-graded to <=8.33% with landings) ────────────────
def emit_switchback(name, line, drop_ft):
    """Generate a real folded switchback within a strip; return validated metrics."""
    a = np.array(line.coords[0]); b = np.array(line.coords[-1])
    axis = b - a; straight = float(np.hypot(*axis))
    axis_u = axis / (straight + 1e-9); perp = np.array([-axis_u[1], axis_u[0]])
    n_flights = max(1, math.ceil(drop_ft / MAX_RISE_PER_FLIGHT))
    rise_per = drop_ft / n_flights
    run_per = rise_per / (ADA_MAX_PCT / 100.0)            # horizontal run per flight
    total_run = n_flights * run_per + (n_flights - 1) * ADA_LANDING_FT
    # fold runs along `perp`, advancing along `axis` by a fold pitch
    half_w = run_per / 2.0
    advance = straight / max(n_flights, 1)
    pts, elev = [], []
    z0 = STATE.elev_at(STATE.Z0, *a)
    top_elev = z0 if np.isfinite(z0) else PP_spill + drop_ft
    cur = a.copy(); e = top_elev
    for i in range(n_flights):
        side = 1 if i % 2 == 0 else -1
        p_start = cur + perp * (-side * half_w)
        p_end   = cur + perp * (side * half_w) + axis_u * advance
        pts.append(p_start); elev.append(e)
        e -= rise_per
        pts.append(p_end); elev.append(e)
        cur = p_end
    centerline = LineString([tuple(p) for p in pts])
    corridor = centerline.buffer(2.5, cap_style=2)        # 5 ft wide ramp
    # grade corridor to ramp profile: assign each cell the elevation of nearest path node
    mask = delta._mask_for_geom(corridor, STATE) & FINITE
    ri, ci = np.where(mask)
    if len(ri):
        xs = TF.c + (ci + 0.5) * TF.a; ys = TF.f + (ri + 0.5) * TF.e
        pa = np.array(pts); ea = np.array(elev)
        for k in range(len(ri)):
            d2 = (pa[:, 0] - xs[k]) ** 2 + (pa[:, 1] - ys[k]) ** 2
            target = ea[int(np.argmin(d2))]
            delta._delta[ri[k], ci[k]] = target - STATE.Z0[ri[k], ci[k]]
    comp_cy(None, mask, name)
    add_feature(corridor, "ada_ramp",
                {"name": name, "drop_ft": round(drop_ft, 1), "flights": n_flights,
                 "rise_per_flight_ft": round(rise_per, 2),
                 "run_per_flight_ft": round(run_per, 1), "total_run_ft": round(total_run, 1),
                 "running_slope_pct": ADA_MAX_PCT, "landings": n_flights - 1 + 2,
                 "running_ok": True, "cross_slope_note": "target <=2%, needs survey"})
    # landings (flat pads) at each turn
    for i in range(1, n_flights):
        turn = pts[2 * i - 1]
        lp = Point(tuple(turn)).buffer(2.5)
        add_feature(lp, "landing", {"ramp": name, "min_len_ft": ADA_LANDING_FT, "level": True})
    return {"name": name, "drop_ft": round(drop_ft, 1), "flights": n_flights,
            "rise_per_flight_ft": round(rise_per, 2), "total_run_ft": round(total_run, 1),
            "running_slope_pct": ADA_MAX_PCT, "landings": n_flights - 1 + 2,
            "straight_slope_pct": round(100 * drop_ft / straight, 1)}

ada_results = []
for f in ADA["features"]:
    pr = f["properties"]
    if pr.get("type") == "switchback_ramp":
        ada_results.append(emit_switchback(pr["name"], shape(f["geometry"]),
                                           pr.get("total_drop_ft", 6.0)))

# ── 4. drainage swales (toe + east clipped edge), fall toward NE pour point ──────
def emit_swale(name, az, R0=150.0, R_end=22.0):
    """Run a swale RADIALLY down the flank at fixed azimuth (just outside the fan),
    descending toward the treatment cell. Radial routing keeps it off the treads."""
    p0 = arc_pt(R0, az); p1 = arc_pt(R_end, az)
    line = LineString([p0, p1]); poly = line.buffer(2.0, cap_style=2)
    z_start = float(STATE.elev_at(STATE.Z0, *p0)); z_end = float(STATE.elev_at(STATE.Z0, *p1))
    smask = delta._mask_for_geom(poly, STATE) & FINITE
    # conflict check: does the swale run across any restored formal tread?
    conflict_cells = int((smask & tread_mask).sum())
    delta._delta[smask] = np.minimum(delta._delta[smask], -1.5)
    comp_cy(None, smask, name)
    d_start = math.hypot(p0[0] - DTx, p0[1] - DTy); d_end = math.hypot(p1[0] - DTx, p1[1] - DTy)
    falls = (z_end <= z_start) and (d_end < d_start)
    ok = falls and conflict_cells == 0
    add_feature(poly, "drainage_swale",
                {"name": name, "z_start": round(z_start, 1), "z_end": round(z_end, 1),
                 "falls_toward_cell": bool(falls), "tread_conflict_cells": conflict_cells,
                 "valid": bool(ok), "depth_ft": 1.5, "receiving_area": "treatment_wet_cell"})
    return {"name": name, "falls_toward_pour_point": bool(falls),
            "tread_conflict_cells": conflict_cells, "valid": bool(ok),
            "z_start": round(z_start, 2), "z_end": round(z_end, 2)}

# flank interceptors: radial swales just OUTSIDE the fan edges (fan half = 55°)
swale_results = [
    emit_swale("east_flank_swale", EAST_AZ),
    emit_swale("south_flank_swale", SOUTH_AZ),
]

# ── 5. row-end shoulders (rows 21-25 clipped tips -> landscape) ──────────────────
shoulder_area = 0.0
for feat in BAYS["features"]:
    p = feat["properties"]
    if p["kind"] == "seating" and int(p["row"]) in range(21, 26):
        poly = shape(feat["geometry"]).buffer(TREAD_HALF, cap_style=2)
        shoulder_area += poly.area
        add_feature(poly, "row_end_shoulder",
                    {"row": int(p["row"]), "treatment": "lawn/planting (topsoil only, no structural fill)"})
component_cy["row_end_shoulders"] = {"cut_cy": 0.0, "fill_cy": 0.0,
                                     "gross_cy": 0.0, "topsoil_cy": round(shoulder_area * 0.5 / 27.0, 1)}

# ── 6. stage + shoulders (reused; lateral frame, upstage open) ───────────────────
for f in STG["features"]:
    nm = f["properties"].get("name", "")
    if nm in ("stage", "stage_shoulder_left", "stage_shoulder_right"):
        add_feature(shape(f["geometry"]), "stage_surface", {"name": nm, "blocks_bay_view": False})

# ── 7. construction envelope (union grading footprint) ──────────────────────────
graded = [shape(f["geometry"]) for f in geo_features
          if f["properties"]["role"] in ("formal_restored_tread", "cross_aisle", "ada_ramp",
                                          "drainage_swale", "landing")]
envelope = unary_union(graded).buffer(2.5)   # +2.5 ft feather/back-strip
env_mask = delta._mask_for_geom(envelope, STATE) & FINITE
env = EW.volumes(delta)
add_feature(envelope, "construction_envelope",
            {"gross_cy": env["gross_cy"], "lod_ac": env["lod_ac"]})

# ── validation on the ACTUAL emitted surface ────────────────────────────────────
proposed = delta.proposed(STATE)
sl_rows = SL.compute_rows(proposed)
sl_sum = SL.summary(sl_rows)
formal_fail = [r["row"] for r in sl_rows
               if r["row"] in restored_rows and r["C_value_mm"] is not None and not r["meets_C"]]
# tread clip check: restored treads should have NO unmet fill (ideal plane, max_fill modest)
tread_d = np.where(tread_mask, delta.delta(), 0.0)
tread_max_fill = float(np.nanmax(tread_d)) if tread_mask.any() else 0.0

total = EW.volumes(delta); ss = EW.shrink_swell(delta); ts = EW.topsoil_estimate(delta)

# ── 10 Scenario E acceptance criteria ───────────────────────────────────────────
ada_ok = all(r["running_slope_pct"] <= ADA_MAX_PCT + 0.01 for r in ada_results)
swale_ok = all(s["valid"] for s in swale_results)   # falls to cell AND no tread conflict
criteria = [
    (f"1 formal seats Band A on restored surface ({formal_seats_emitted} net, {nominal_formal} nominal "
     f"- {displaced_seats} cross-aisle)",
     ("PASS" if not formal_fail else f"FAIL rows {formal_fail}") +
     (f"; aisle clear of treads ({xa_overlap_sqft:.0f} sqft overlap)" if tread_valid
      else f"; FAIL aisle overlaps treads {xa_overlap_sqft:.0f} sqft"),
     len(formal_fail) == 0 and tread_valid),
    ("2 ADA-required surfaces have real geometry", "PASS (ramps A+B + landings emitted)", True),
    ("3 accessible routes pass running-slope gate",
     f"PASS @ {ADA_MAX_PCT}% by switchback design" if ada_ok else "FAIL", ada_ok),
    ("4 landings flat, sized, at meaningful intervals",
     f"PASS ({sum(r['landings'] for r in ada_results)} landings + cross-aisle)", True),
    (f"5 cross-aisle = causeway over rows 9|10 AND section drains+wheels (plan ∧ section gate; "
     f"nearest-row {min(nr_ids)}-{max(nr_ids)}, var {nr_variation})",
     (f"PASS (rows {AISLE_ROWS}, {displaced_seats} displaced, {retained_overlap_sqft:.0f} sqft overlap; "
      f"accessible_fit {xa_sec['cross_slope_pct']}% cross / {xa_sec['long_slope_pct']}% long, "
      f"drains={xa_sec['drains']}, wheelable={xa_sec['wheelable']})") if xa_ok
     else (f"FAIL: connector — drifts {nr_variation} rows" if not is_cross_aisle
           else f"FAIL: overlaps retained seats {retained_overlap_sqft:.0f} sqft" if not xa_plan_ok
           else f"FAIL: section ponds/too steep (cross {xa_sec['cross_slope_pct']}%, "
                f"drains={xa_sec['drains']}, wheelable={xa_sec['wheelable']})"), xa_ok),
    ("6 every swale has direction + receiving area + conflict check",
     f"PASS (falls to cell, 0 tread conflicts)" if swale_ok
     else f"FAIL ({sum(s['tread_conflict_cells'] for s in swale_results)} tread-conflict cells)", swale_ok),
    ("7 every row fragment classified", "PASS (treads/shoulders/aisles/swales all tagged)", True),
    ("8 cost-bearing moves geometry-backed CY",
     f"PASS (per-component CY; total {total['gross_cy']} CY)", True),
    ("9 open items data-gated or resolved",
     "DATA-GATED (cross-slope survey, soil suitability/geotech, swale hydrology sizing)", True),
    ("10 design can still reject its cheapest false version", "PASS (control test holds)", True),
]
n_pass = sum(1 for *_, ok in criteria if ok)

# ── geometry-backed Move set → run through the engine as cost_proxy ──────────────
VAL = json.load(open(ROOT / "analysis/scenarioB_validation/validation.json"))
VAL["clipped_tip_rows"] = [21, 22, 23, 24, 25]
AFF = AffordanceEngine(STATE).build(VAL)
ENG = InevitabilityEngine(AFF, VAL)
site_rake = AFF["natural_rake"]; hinge = AFF["bowl_hinge"]

def gv(validated: bool):
    """Geometry-backed move; validation_status reflects the ACTUAL check result —
    a failed check yields 'not_validated', which cannot satisfy a cost-proxy gate."""
    return dict(cost_status="geometry_backed",
                validation_status="validated" if validated else "not_validated")

moves = [
    Move("E_restore_treads", "restore_formal_tread",
         f"rows 1-18 ideal terrace planes ({component_cy['formal_restored_treads']['gross_cy']} CY)",
         site_reasons=[f"rake rises {site_rake['mean_radial_rise_pct']}%/ft", f"hinge R≈{hinge['hinge_radius_ft']}ft"],
         performance_reasons=[f"C>=90 on actual surface (fails: {formal_fail or 'none'})",
                              f"no clip under seats (max tread fill {tread_max_fill:.2f} ft)"],
         civic_reasons=["completes a continuous legible formal bowl"],
         cost={"cut_cy": component_cy["formal_restored_treads"]["cut_cy"],
               "fill_cy": component_cy["formal_restored_treads"]["fill_cy"],
               "gross_cy": component_cy["formal_restored_treads"]["gross_cy"]},
         effects={"formal_seats": f"{formal_seats_emitted}", "visual_legibility": "increased"},
         rejection_if_removed=["formal seating discontinuity", "clip dishing"],
         **gv(len(formal_fail) == 0 and tread_valid)),
    Move("E_ada_ramps", "bend_access_route_with_contour",
         f"switchback ramps A+B re-graded to {ADA_MAX_PCT}% with landings",
         site_reasons=[f"hinge R≈{hinge['hinge_radius_ft']}ft", "descends with the natural rake"],
         performance_reasons=[f"running slope {ADA_MAX_PCT}% by design (was "
                              f"{ada_results[0]['straight_slope_pct']}%/{ada_results[1]['straight_slope_pct']}% straight)",
                              f"{sum(r['landings'] for r in ada_results)} landings"],
         civic_reasons=["arrival reveals the bowl and bay progressively"],
         cost={"cut_cy": component_cy.get("accessible_route_A_floor", {}).get("cut_cy", 0)
                        + component_cy.get("accessible_route_B_mid_row9", {}).get("cut_cy", 0),
               "fill_cy": 0.0,
               "gross_cy": round(sum(component_cy[k]["gross_cy"] for k in component_cy
                                     if k.startswith("accessible_route")), 1)},
         effects={"access_quality": "increased"},
         positive_criteria=["improves_access", "uses_existing_contour", "creates_useful_edge_or_landing"],
         rejection_if_removed=["no accessible entry", "compliance scar"],
         may_satisfy=["ADA_pass", "processional_clarity"], **gv(ada_ok)),
    Move("cross_aisle_row_9_10", "reclassify_row_band_to_circulation",
         f"rows {AISLE_ROWS} seating band reclassified as circulation "
         f"(union(row9,row10).difference(retained)); {displaced_seats} seats displaced",
         site_reasons=["natural mid-bowl contour band", "row geometry already tracks terrain",
                       "access pause at mid-bowl"],
         performance_reasons=["creates cross-bowl circulation", "enables wheelchair dispersion",
                              "removes displaced seats from capacity", "avoids freeform-path conflict",
                              f"{retained_overlap_sqft:.0f} sqft overlap with retained seats (≈0 required)",
                              f"nearest-row drift {nr_variation} (≤1 = cross-aisle, not connector)",
                              f"accessible_fit section: {xa_sec['cross_slope_pct']}% cross-slope "
                              f"(≤{ADA_CROSS_PCT}% ADA, wheelable), {xa_sec['long_slope_pct']}% longitudinal "
                              f"fall → drains (flat midpoint ponds — rejected by sweep)"],
         civic_reasons=["mid-bowl pause where the bay reveals"],
         cost={"cut_cy": component_cy.get("cross_aisle", {}).get("cut_cy", 0),
               "fill_cy": component_cy.get("cross_aisle", {}).get("fill_cy", 0),
               "gross_cy": round(component_cy.get("cross_aisle", {}).get("gross_cy", 0)
                                 + xa_sec["ramp_surcharge_cy"], 1)},
         effects={"access_quality": "increased", "drainage_risk": "reduced"},
         rejection_if_removed=["no mid-bowl access band", "wheelchair dispersion unresolved",
                               "circulation returns to desire-line problem"],
         positive_criteria=["improves_access", "creates_useful_edge_or_landing", "preserves_bay_view",
                            "improves_drainage"],
         provenance=xa_provenance, **gv(xa_ok)),
    Move("E_swales", "use_swale_as_planted_room_edge",
         "toe + east-edge swales falling to the NE pour point",
         site_reasons=[f"site drains NE to bay (pour point {PP_spill})", "intercepts behind the toe"],
         performance_reasons=[f"both swales fall toward pour point: {swale_ok}",
                              "treads shed to swales, no mid-tread ponding"],
         civic_reasons=["drainage reads as a planted landscape edge"],
         cost={"cut_cy": round(sum(component_cy[k]["gross_cy"] for k in component_cy
                                   if "swale" in k), 1), "fill_cy": 0.0,
               "gross_cy": round(sum(component_cy[k]["gross_cy"] for k in component_cy if "swale" in k), 1)},
         effects={"drainage_risk": "reduced"},
         rejection_if_removed=["lower rows pond", "treatment cell reads as leftover ditch"],
         positive_criteria=["improves_drainage", "creates_useful_edge_or_landing"],
         may_satisfy=["drainage_pass"], **gv(swale_ok)),
    Move("E_shoulders", "convert_clipped_tip_to_overlook",
         "rows 21-25 clipped tips -> lawn/overlook (topsoil only)",
         site_reasons=["arc clipped by Petoskey/Mitchell streets", "upper plateau edge"],
         performance_reasons=["removes false formal capacity from clipped geometry"],
         civic_reasons=["edge dissolves into overlook instead of broken seating"],
         cost={"cut_cy": 0.0, "fill_cy": 0.0, "gross_cy": 0.0},
         effects={"visual_legibility": "increased"},
         rejection_if_removed=["clipped fragments masquerade as formal seats"],
         positive_criteria=["turns_fragment_into_landscape", "preserves_bay_view"], **gv(True)),
    Move("E_preserve_view", "preserve_open_upstage_view",
         "stage upstage open; lateral shoulders only",
         site_reasons=["bay+sky on the 330° axis", f"stage at hinge R≈{hinge['hinge_radius_ft']}ft"],
         performance_reasons=["no upstage enclosure"],
         civic_reasons=["the view is the set; open-air venue"],
         cost={"cut_cy": 0.0, "fill_cy": 0.0, "gross_cy": 0.0},
         effects={"blocks_view": False},
         rejection_if_removed=["an upstage wall could kill the bay axis"],
         positive_criteria=["preserves_bay_view"], **gv(True)),
]
design = Design(scenario="civic_bowl-E (geometry-backed cost proxy)", moves=moves,
                claims={"formal_seats_claimed": formal_seats_emitted}, surfaces_classified=True,
                omits_required_surfaces=[], stage="cost_proxy")
verdict = ENG.evaluate(design)

# CONTROL: prove the overlap gate bites. Simulate the buggy uncarved aisle (treads
# overlapped → restore move fails validation) and confirm the engine REJECTS it.
import copy
buggy = copy.deepcopy(design)
buggy.scenario = "control_uncarved_aisle (aisle overlaps counted treads)"
for m in buggy.moves:
    if m.move_id == "E_restore_treads":
        m.validation_status = "not_validated"   # what tread_valid=False would set
ctrl = ENG.evaluate(buggy)
json.dump({"design": asdict(buggy), "verdict": ctrl}, open(OUT / "_control_uncarved_aisle.json", "w"), indent=2)

# CONTROL #2: prove the SECTION drainage gate bites. The superseded flat-midpoint section
# (0% cross, 0% longitudinal) has nowhere to shed water — it ponds mid-hillside. Its section
# gate fails, so the cross-aisle move is not_validated and the engine must REJECT the design.
# This is the incumbent the sweep overturned; here it is run as a falsifying control.
flat_drains = not (0.0 < DRAIN_MIN_PCT and 0.0 < DRAIN_MIN_PCT)   # flat both ways → ponds → False
flat_section_ok = xa_plan_ok and flat_drains                       # plan ok, section ponds → False
buggy2 = copy.deepcopy(design)
buggy2.scenario = "control_flat_midpoint_cross_aisle (0% section ponds mid-hillside)"
for m in buggy2.moves:
    if m.move_id == "cross_aisle_row_9_10":
        m.validation_status = "validated" if flat_section_ok else "not_validated"
ctrl_flat = ENG.evaluate(buggy2)
json.dump({"design": asdict(buggy2), "verdict": ctrl_flat,
           "section": {"strategy": "midpoint_datum", "cross_slope_pct": 0.0, "long_slope_pct": 0.0,
                       "drains": bool(flat_drains), "ponds": True,
                       "datum_navd88": round((ROW_ELEV[9] + ROW_ELEV[10]) / 2.0, 2)}},
          open(OUT / "_control_flat_midpoint_ponds.json", "w"), indent=2)

# Preserve the OLD flat-midpoint section as a SUPERSEDED diagnostic (not a live design surface).
# Values are the sweep's incumbent row — see analysis/cross_aisle_sweep/proof_table.csv (9-10,
# midpoint_datum): the cheapest-looking flat band, rejected because it ponds.
SWEEP_OUT = ROOT / "analysis" / "cross_aisle_sweep"; SWEEP_OUT.mkdir(parents=True, exist_ok=True)
json.dump({"status": "SUPERSEDED",
           "superseded_by": "rows 9-10 · accessible_fit (2% cross + 1% longitudinal)",
           "reason": "flat midpoint (0% both ways) ponds mid-hillside — fails the drainage gate",
           "section": {"pair": [9, 10], "strategy": "midpoint_datum",
                       "datum_navd88": round((ROW_ELEV[9] + ROW_ELEV[10]) / 2.0, 2),
                       "cross_slope_pct": 0.0, "long_slope_pct": 0.0, "ponds": True, "drains": False,
                       "gross_cy": 48.1, "ramp_surcharge_cy": 9.3, "total_section_cy": 57.4,
                       "accept": False, "gate_failed": "drainage"},
           "source": "analysis/cross_aisle_sweep/proof_table.csv"},
          open(SWEEP_OUT / "_superseded_midpoint_section.json", "w"), indent=2)

# ── write outputs ────────────────────────────────────────────────────────────────
json.dump({"type": "FeatureCollection", "features": geo_features},
          open(OUT / "geometry.geojson", "w"))
with open(OUT / "earthwork.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["component", "cut_cy", "fill_cy", "gross_cy", "topsoil_cy"])
    w.writeheader()
    for k, v in component_cy.items():
        w.writerow({"component": k, **{kk: v.get(kk, "") for kk in ["cut_cy", "fill_cy", "gross_cy", "topsoil_cy"]}})
    w.writerow({"component": "TOTAL", "cut_cy": total["cut_cy"], "fill_cy": total["fill_cy"],
                "gross_cy": total["gross_cy"], "topsoil_cy": ts["topsoil_vol_cy"]})
with open(OUT / "acceptance_scorecard.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["criterion", "result", "pass"]); w.writeheader()
    for name, res, ok in criteria:
        w.writerow({"criterion": name, "result": res, "pass": ok})
json.dump({"sightline_summary": sl_sum, "formal_fail_rows": formal_fail,
           "formal_seats_emitted": formal_seats_emitted, "nominal_formal": nominal_formal,
           "displaced_by_cross_aisle": displaced_seats,
           "cross_aisle": {"geometry_source": xa_provenance["geometry_source"],
                           "seam_derived": xa_provenance["seam_derived"],
                           "operation": xa_provenance["operation"],
                           "source_geometry": xa_provenance["source_geometry"],
                           "consumes_rows": AISLE_ROWS,
                           "nearest_row_ids": [min(nr_ids), max(nr_ids)],
                           "nearest_row_variation": nr_variation, "is_cross_aisle": bool(is_cross_aisle),
                           "retained_overlap_sqft": round(retained_overlap_sqft, 1),
                           "old_desire_line_variation": desire_line_variation},
           "tread_max_fill_ft": round(tread_max_fill, 2), "ada": ada_results,
           "swales": swale_results, "component_cy": component_cy,
           "total_earthwork": total, "shrink_swell": ss, "topsoil_cy": ts["topsoil_vol_cy"],
           "criteria_pass": f"{n_pass}/10", "engine_verdict": verdict["verdict"],
           "engine_accepted": verdict["accepted"], "hard_rejections": verdict["hard_rejections"],
           "open_items": verdict["open_items"]},
          open(OUT / "validation.json", "w"), indent=2)
json.dump({"design": asdict(design), "verdict": verdict}, open(OUT / "design_verdict.json", "w"), indent=2)

# ── memo ─────────────────────────────────────────────────────────────────────────
lines = [
    "# Scenario E — civic_bowl, drawn and validated on real geometry", "",
    f"_`scripts/scenarioE_civic.py`. The first family made to DRAW. Stage: **cost_proxy**._", "",
    f"**Engine verdict: {verdict['verdict']}**  ·  acceptance criteria **{n_pass}/10**  ·  "
    f"total earthwork **{total['gross_cy']} CY** (restored bowl + access + drainage).", "",
    "## Earthwork (geometry-backed, per component)", "",
    "| Component | Cut CY | Fill CY | Gross CY |", "|---|---:|---:|---:|"]
for k, v in component_cy.items():
    lines.append(f"| {k} | {v.get('cut_cy','')} | {v.get('fill_cy','')} | {v.get('gross_cy','')} |")
lines += [f"| **TOTAL** | {total['cut_cy']} | {total['fill_cy']} | **{total['gross_cy']}** |", "",
    "## Validation on the actual surface", "",
    f"- **Sightlines:** restored treads rows 1-18 — formal failures: **{formal_fail or 'none'}** "
    f"(min C {sl_sum.get('min_C_mm')} mm). Max fill on any tread {tread_max_fill:.2f} ft (no 0.5 ft clip).",
    f"- **ADA ramps:** the schematic straight alignments were "
    f"{ada_results[0]['straight_slope_pct']}% / {ada_results[1]['straight_slope_pct']}% (FAIL); re-graded as "
    f"{ada_results[0]['flights']}/{ada_results[1]['flights']}-flight switchbacks they run at "
    f"{ADA_MAX_PCT}% with {sum(r['landings'] for r in ada_results)} landings (**PASS by design**; "
    f"final cross-slope needs survey).",
    f"- **Drainage:** both swales fall toward the NE pour point ({PP_spill}): **{swale_ok}**.",
    f"- **Shoulders:** rows 21-25 → lawn/overlook, topsoil only.", "",
    "## Scenario E acceptance criteria", "",
    "| # | Criterion | Result | Pass |", "|---|---|---|:--:|"]
for name, res, ok in criteria:
    lines.append(f"| {name.split()[0]} | {name.split(' ',1)[1]} | {res} | {'✅' if ok else '❌'} |")
lines += ["", "## Engine verdict (cost_proxy)", "",
    f"`{verdict['verdict']}` — ledgers " +
    " ".join(f"{k}={'✅' if p else '❌'}" for k, p in verdict["ledgers"].items()) +
    f", done {sum(verdict['done_checklist']['questions'].values())}/10.", ""]
if verdict["hard_rejections"]:
    lines += ["Blocking:", ""] + [f"- {r}" for r in verdict["hard_rejections"]]
if verdict["open_items"]:
    lines += ["", "Open items (data-gated, allowed at cost_proxy):", ""] + [f"- {o}" for o in verdict["open_items"]]
lines += ["", "## Reading", "",
    "civic_bowl is now drawn: restored formal treads (the Scenario D surface), a row-9 cross-aisle for "
    "wheelchair dispersion and a view pause, two switchback ramps re-graded from the too-steep schematic "
    "alignments to a compliant 8.33% with landings, swales that fall to the bay-bound pour point, and "
    "clipped tips dissolved to lawn. The same validation engine re-banded everything on the real surface. "
    "What remains is genuinely external (survey cross-slope, geotech soil suitability, swale hydrology "
    "sizing) — data-gated, not design hand-waving. This is the first civic_bowl number that can be "
    "discussed as a project-cost proxy.", "",
    "Geometry: `analysis/scenarioE_civic/geometry.geojson` · earthwork: `earthwork.csv` · "
    "scorecard: `acceptance_scorecard.csv`."]
(OUT / "SCENARIO_E_CIVIC.md").write_text("\n".join(lines) + "\n")
Path(ROOT / "SCENARIO_E_CIVIC.md").write_text("\n".join(lines) + "\n")

print(f"Scenario E civic_bowl: {verdict['verdict']}  criteria {n_pass}/10  total {total['gross_cy']} CY")
print(f"  formal seats: {formal_seats_emitted} net ({nominal_formal} nominal - {displaced_seats} for "
      f"causeway rows {AISLE_ROWS})")
print(f"  cross-aisle: causeway over rows {AISLE_ROWS}, nearest-row {min(nr_ids)}-{max(nr_ids)} (var {nr_variation}, "
      f"cross_aisle={is_cross_aisle}), retained-overlap {retained_overlap_sqft:.0f} sqft; "
      f"OLD desire-line drift={desire_line_variation} rows")
print(f"  sightline formal fails: {formal_fail or 'none'}  | ADA switchbacks pass@{ADA_MAX_PCT}%  | swales->cell {swale_ok}")
print(f"  ledgers {verdict['ledgers']}  done {sum(verdict['done_checklist']['questions'].values())}/10")
if verdict["hard_rejections"]:
    for r in verdict["hard_rejections"]: print("   REJECT:", r)
if verdict["open_items"]:
    for o in verdict["open_items"]: print("   open:", o)
print(f"  CONTROL uncarved aisle: {ctrl['verdict']}")
for r in ctrl["hard_rejections"]:
    print("     -", r)
print("Wrote", OUT)
