"""Tier emission + validation — modest_normalization and ambitious_shaped_bowl
(SEATING SCOPE), emitted as real geometry and validated under canon Rules 3/4/5.

WHY THIS SCRIPT EXISTS
----------------------
The intervention-tier harness (scripts/run_intervention_tiers.py) evaluated the
tier recipes ANALYSIS-TIER: seats and CY from band-area accounting and contour-
walk proxies, never from an emitted surface. Scenario B taught that analysis-tier
seat claims can collapse on emission (1,452 → 217). This script re-emits each
tier the way Scenario E itself was emitted (scripts/scenarioE_civic.py), then
validates Rule 4's gates per 8-ft segment on the ACTUAL surface, the way
Scenario B was validated (scripts/validate_scenarioB.py).

STAGE DECOUPLING (deliberate scope cut)
---------------------------------------
ambitious_shaped_bowl's refit_stage (P_opt) and faceted_apron ops are NOT
emitted here. They carry zero seats in the tier decomposition and are gated
behind DESIGN_CANON Rule 9, which is OPEN. This script validates the SEATING
claims only; the emitted scenario is "ambitious_shaped_bowl (seating scope,
inherited stage)". Stage candidates re-enter when Rule 9 closes.

METHOD NOTES (calibration decisions, made explicit)
---------------------------------------------------
* Two-phase emission: rows 1-18 are emitted first (DEM-median planes, exactly
  as Scenario E). Regrade chains are then solved against the MEASURED emitted
  previous-row elevations — not the composition table — because that is what
  "re-emission on the real surface" means. Promoted/regraded rows are emitted
  at the solved elevations.
* C is measured STATION-MATCHED on centrelines: per 8-ft segment, this row's
  proposed-surface elevation at the segment centre vs the previous seated
  row's proposed-surface elevation at the nearest centreline point, with D
  from the composition axis radii. Whole-band medians are NOT used — bands of
  different arc length have different along-row extents and the 0.5 %
  longitudinal term biases their medians against each other by up to ±20 mm C.
* Adjacent tread masks overlap at 1-ft raster edges (all_touched rasterize);
  the later-emitted row owns the shared cells. Grade-break continuity is
  therefore measured only on cells still lying on the segment's own fitted
  plane (|resid| <= 0.30 ft): the inter-row riser is the DESIGN, not a trip
  edge. Plane-fit slope/planarity uses interior-eroded cells as in
  validate_scenarioB.py.
* N1 extension paths are emitted by the same contour walk as the study
  (recorded points), then gated by the extended-bays emission standards:
  z-resid p90 <= 0.25 ft vs raw DEM, crossing angle p90 <= 10°, MIN bay
  length 25 ft, adjacent clearance >= 3 ft, seat-splay 45° (study gate) with
  the 28° composition gate reported as the strict bound.
* Incremental earthwork is the raster diff (tier delta − baseline delta) with
  DISJOINT component attribution (extension > promoted > regraded > baseline
  treads > other).

Outputs -> analysis/tier_emission/<tier>/ {geometry.geojson, segments.csv,
validation.json} + analysis/tier_emission/_baseline_reconciliation.json

Planning grade. EPSG:6494, NAVD88 intl ft.
"""
from __future__ import annotations

import csv, json, math, os, sys
from pathlib import Path

import numpy as np
import rasterio as _rio
from scipy.ndimage import binary_erosion, gaussian_filter
from shapely.geometry import shape, LineString, Point, mapping
from shapely.ops import unary_union

ROOT = Path(__file__).parent.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT / "scripts"))

from harness.project import ProjectState
from harness.clay import ClayDelta
from harness.earthwork import EarthworkEngine

OUT_BASE = ROOT / "analysis" / "tier_emission"
OUT_BASE.mkdir(parents=True, exist_ok=True)

STATE = ProjectState.load("harness_config.yaml")
EW = EarthworkEngine(STATE)
FX, FY = STATE.arc_centre(); TF = STATE.transform
FINITE = np.isfinite(STATE.Z0)

# ── design constants (identical to scenarioE_civic.py / tier geometry model) ────
TREAD_HALF = 1.8
CROSS_SLOPE, LONG_SLOPE = 2.0, 0.5
STAGE_R, FOCUS_ELEV, EYE_HT = 50.0, 612.5, 3.94
C_FORMAL_MM = 90.0
PROMENADE_ROW = 5; AISLE_ROWS = (9, 10); FORMAL_STOP_ROW = 18
ADA_MAX_PCT = STATE.cfg["ada"]["running_slope_pct"]
MAX_RISE_PER_FLIGHT = 2.5
ADA_CROSS_PCT = float(STATE.cfg["ada"].get("cross_slope_target_pct", 2.0))
DRAIN_MIN_PCT = 0.5

# Rule 4 segment gates (validate_scenarioB.py thresholds; longitudinal per Rule 4)
STATION_FT = 8.0
CROSS_PASS, LONG_PASS, TWIST_PASS = 2.5, 1.0, 0.12
CONTINUITY_FT = 0.50
OWNED_RESID_FT = 0.30      # cells beyond this off the fitted plane belong to a
                           # neighbouring tread (by-design riser), not this one

# extended-bays emission gates (design_extended_bays.py standards) for N1
GATE_RESID_P90 = 0.25; GATE_CROSS_ANG = 10.0; GATE_CLEAR = 3.0
MIN_BAY_LEN = 25.0
SEAT_W_G = 1.83; AISLE_LOSS = 0.18
SPLAY_GATE_DEG = 45.0          # the study's gate (declared "generous")
SPLAY_STRICT_DEG = 28.0        # civic_bowl composition gate (strict bound)
MIN_WALL_SLOPE = 0.15; STREET_SETBACK = 15.0
Y_LAKE, Y_MITCHELL, X_PETOSKEY = 750943.1, 750593.6, 19533270.8
SF_X, SF_Y = 19533100.2, 750742.9       # inherited stage front centre (Rule 9 OPEN)

# ── locked inputs ────────────────────────────────────────────────────────────────
BAYS = json.load(open(ROOT / "design_extended_bays/seating_bays.geojson"))
COMP = {}
for r in csv.DictReader(open(ROOT / "design_extended_bays/composition_table.csv")):
    COMP[(r["section"], int(r["row"]))] = {
        "elev": float(r["elev"]), "axis_r": float(r["axis_radius_ft"]),
        "length_ft": float(r["length_ft"]), "seats": int(r["seats"]),
        "zone": r["zone"], "kind": r["kind"],
        "c_mm": float(r["C_mm"]) if r["C_mm"].strip() else None,
    }
LINES = {}
for f in BAYS["features"]:
    p = f["properties"]
    LINES[(p["section"], int(p["row"]))] = shape(f["geometry"])
ADA_SRC = json.load(open(ROOT / "design_open_low/ada_route.geojson"))
STG = json.load(open(ROOT / "design_open_low/stage_floor.geojson"))
_cell = next(shape(f["geometry"]) for f in STG["features"]
             if f["properties"].get("name") == "treatment_wet_cell")
DTx, DTy = _cell.centroid.x, _cell.centroid.y
PP_spill = json.load(open(ROOT / "pour_point.geojson"))["features"][0][
    "properties"]["spill_elev_ft_navd88"]
LOCKED_EW = {r["component"]: r for r in
             csv.DictReader(open(ROOT / "analysis/scenarioE_civic/earthwork.csv"))}
LOCKED_TOTAL_CY = float(LOCKED_EW["TOTAL"]["gross_cy"])

SECTIONS = ("east", "bend", "south")


def bearing(dx, dy): return math.degrees(math.atan2(dx, dy)) % 360.0
def ang_diff(a, b): return ((a - b + 180.0) % 360.0) - 180.0
def U(az): a = math.radians(az); return math.sin(a), math.cos(a)
def arc_pt(R, az): e, n = U(az); return FX + e * R, FY + n * R


def seated_rows(section):
    rows = sorted(r for (s, r) in COMP if s == section and COMP[(s, r)]["kind"] == "seating")
    return [r for r in rows if r != PROMENADE_ROW and r not in AISLE_ROWS]


def sample_centreline(surface, line, step_ft=3.0):
    n = max(2, int(line.length / step_ft))
    vals = []
    for i in range(n + 1):
        p = line.interpolate(i / n, normalized=True)
        v = STATE.elev_at(surface, p.x, p.y)
        if np.isfinite(v):
            vals.append(v)
    return vals


# ── Scenario E baseline ops (ports of scenarioE_civic.py emitters) ──────────────
def accessible_cross_aisle(delta, band_poly, rows, elev_bend):
    i, j = rows
    mid = (elev_bend[i] + elev_bend[j]) / 2.0
    R_ref = (COMP[("bend", i)]["axis_r"] + COMP[("bend", j)]["axis_r"]) / 2.0
    mask = delta._mask_for_geom(band_poly, STATE) & FINITE
    ri, ci = np.where(mask)
    x = TF.c + (ci + 0.5) * TF.a; y = TF.f + (ri + 0.5) * TF.e
    n = np.hypot(x - FX, y - FY) - R_ref
    cx, cy = x.mean(), y.mean()
    rc = math.hypot(cx - FX, cy - FY) + 1e-9
    tgx, tgy = (cy - FY) / rc, -(cx - FX) / rc
    s = (x - cx) * tgx + (y - cy) * tgy
    gx, gl = ADA_CROSS_PCT / 100.0, 1.0 / 100.0
    e = mid + gx * n + gl * (s - s.min())
    delta._delta[ri, ci] = e - STATE.Z0[ri, ci]
    coef, *_ = np.linalg.lstsq(np.column_stack([n, s, np.ones_like(n)]), e, rcond=None)
    x_slope, l_slope = abs(coef[0]) * 100.0, abs(coef[1]) * 100.0
    ponds = (x_slope < DRAIN_MIN_PCT) and (l_slope < DRAIN_MIN_PCT)
    return mask, dict(datum=round(float(e.mean()), 2),
                      cross_slope_pct=round(x_slope, 2), long_slope_pct=round(l_slope, 2),
                      drains=bool(not ponds),
                      wheelable=bool(x_slope <= ADA_CROSS_PCT + 0.25))


def emit_switchback(delta, name, line, drop_ft):
    a = np.array(line.coords[0]); b = np.array(line.coords[-1])
    axis = b - a; straight = float(np.hypot(*axis))
    axis_u = axis / (straight + 1e-9); perp = np.array([-axis_u[1], axis_u[0]])
    n_flights = max(1, math.ceil(drop_ft / MAX_RISE_PER_FLIGHT))
    rise_per = drop_ft / n_flights
    run_per = rise_per / (ADA_MAX_PCT / 100.0)
    half_w = run_per / 2.0; advance = straight / max(n_flights, 1)
    pts, elev = [], []
    z0 = STATE.elev_at(STATE.Z0, *a)
    top_elev = z0 if np.isfinite(z0) else PP_spill + drop_ft
    cur = a.copy(); e = top_elev
    for i in range(n_flights):
        side = 1 if i % 2 == 0 else -1
        pts.append(cur + perp * (-side * half_w)); elev.append(e)
        e -= rise_per
        cur = cur + perp * (side * half_w) + axis_u * advance
        pts.append(cur); elev.append(e)
    corridor = LineString([tuple(p) for p in pts]).buffer(2.5, cap_style=2)
    mask = delta._mask_for_geom(corridor, STATE) & FINITE
    ri, ci = np.where(mask)
    if len(ri):
        xs = TF.c + (ci + 0.5) * TF.a; ys = TF.f + (ri + 0.5) * TF.e
        pa = np.array(pts); ea = np.array(elev)
        for k in range(len(ri)):
            d2 = (pa[:, 0] - xs[k]) ** 2 + (pa[:, 1] - ys[k]) ** 2
            delta._delta[ri[k], ci[k]] = ea[int(np.argmin(d2))] - STATE.Z0[ri[k], ci[k]]
    return corridor, {"name": name, "flights": n_flights,
                      "running_slope_pct": ADA_MAX_PCT,
                      "landings": n_flights - 1 + 2, "running_ok": True}


def emit_swale(delta, name, az, tread_mask, R0=150.0, R_end=22.0):
    p0 = arc_pt(R0, az); p1 = arc_pt(R_end, az)
    poly = LineString([p0, p1]).buffer(2.0, cap_style=2)
    z_start = float(STATE.elev_at(STATE.Z0, *p0)); z_end = float(STATE.elev_at(STATE.Z0, *p1))
    smask = delta._mask_for_geom(poly, STATE) & FINITE
    conflict_cells = int((smask & tread_mask).sum())
    delta._delta[smask] = np.minimum(delta._delta[smask], -1.5)
    d_start = math.hypot(p0[0] - DTx, p0[1] - DTy); d_end = math.hypot(p1[0] - DTx, p1[1] - DTy)
    falls = (z_end <= z_start) and (d_end < d_start)
    return poly, {"name": name, "az_deg": round(az, 1),
                  "falls_toward_cell": bool(falls),
                  "tread_conflict_cells": conflict_cells,
                  "valid": bool(falls and conflict_cells == 0)}


# ── N1 east contour-walk extension (port of normalize_sections.walk, with
#    points + per-point gate values RECORDED so the geometry can be emitted) ─────
_Zs = gaussian_filter(np.nan_to_num(STATE.Z0, nan=float(np.nanmedian(STATE.Z0))), 3.0)
_gy, _gx = np.gradient(_Zs)


def _sample(arr, x, y):
    r, c = _rio.transform.rowcol(TF, x, y)
    if 0 <= r < arr.shape[0] and 0 <= c < arr.shape[1]:
        return float(arr[r, c])
    return None


def contour_walk(x, y, E, az_dir):
    """Walk the E contour; record points + per-point splay. Same gates and
    parameters as the N1 study walk (normalize_sections.py)."""
    pts, splays = [], []
    L, step = 0.0, 3.0
    stop = "250 ft cap"
    for _ in range(120):
        z, dzx, dzy = _sample(_Zs, x, y), _sample(_gx, x, y), _sample(_gy, x, y)
        if z is None:
            stop = "DEM edge"; break
        slope = math.hypot(dzx, -dzy)
        if slope < MIN_WALL_SLOPE:
            stop = f"wall flattens (slope {slope:.2f})"; break
        downhill = bearing(-dzx, dzy)
        to_stage = bearing(SF_X - x, SF_Y - y)
        splay = abs(ang_diff(downhill, to_stage))
        if splay > SPLAY_GATE_DEG:
            stop = f"seat splay gate ({splay:.0f}°)"; break
        tx, ty = dzy, dzx          # contour tangent (perp to world fall vector)
        n = math.hypot(tx, ty)
        tx, ty = tx / n, ty / n
        ex, ey = U(az_dir)
        if tx * ex + ty * ey < 0:
            tx, ty = -tx, -ty
        x2, y2 = x + tx * step, y + ty * step
        z2, d2x, d2y = _sample(_Zs, x2, y2), _sample(_gx, x2, y2), _sample(_gy, x2, y2)
        if z2 is None:
            stop = "DEM edge"; break
        g2 = max(math.hypot(d2x, -d2y), 1e-6)
        x2 += (E - z2) * d2x / g2 ** 2
        y2 += (E - z2) * (-d2y) / g2 ** 2
        if X_PETOSKEY - STREET_SETBACK <= x2:
            stop = "Petoskey St setback"; break
        if Y_LAKE - STREET_SETBACK <= y2:
            stop = "E Lake St setback"; break
        zc = _sample(_Zs, x2, y2)
        if zc is None or abs(zc - E) > 0.5:
            stop = "contour lost"; break
        x, y, L = x2, y2, L + step
        pts.append((x, y)); splays.append(splay)
    return pts, splays, L, stop


def build_extension_bands(design_elev_fn):
    """Emit N1 extension centrelines off the east cap end of rows 6-18,
    then apply the extended-bays emission gates (incl. MIN_BAY_LEN — the march
    rejects stub bays < 25 ft, so a stub extension cannot be claimed either)."""
    out = []
    for row in [r for r in seated_rows("east") if 6 <= r <= 18]:
        line = LINES[("east", row)]
        cs = list(line.coords)
        e0, e1 = cs[0], cs[-1]
        az0 = bearing(e0[0] - FX, e0[1] - FY); az1 = bearing(e1[0] - FX, e1[1] - FY)
        end, seg = ((e0, (cs[1], cs[0])) if az0 < az1 else (e1, (cs[-2], cs[-1])))
        az_dir = bearing(seg[1][0] - seg[0][0], seg[1][1] - seg[0][1])
        E_contour = COMP[("east", row)]["elev"]          # contour the walk follows
        pts, splays, L, stop = contour_walk(end[0], end[1], E_contour, az_dir)
        rec = {"row": row, "walk_ft": round(L, 0), "stop": stop,
               "design_elev": design_elev_fn(row)}
        if len(pts) < 3:
            rec.update({"emitted": False, "reason": "walk shorter than 9 ft",
                        "seats_45": 0, "seats_28": 0})
            out.append(rec); continue
        ext_line = LineString(pts)
        raw = [STATE.elev_at(STATE.Z0, x, y) for x, y in pts]
        raw = np.array([v for v in raw if np.isfinite(v)])
        med = float(np.median(raw)) if len(raw) else np.nan
        z_resid_p90 = float(np.percentile(np.abs(raw - med), 90)) if len(raw) else 99.0
        cross_angs = []
        for k in range(1, len(pts)):
            tx, ty = pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]
            tn = math.hypot(tx, ty)
            dzx, dzy = _sample(_gx, *pts[k]), _sample(_gy, *pts[k])
            if dzx is None or tn < 1e-9:
                continue
            cdx, cdy = dzy, dzx
            cn = math.hypot(cdx, cdy)
            if cn < 1e-9:
                continue
            dot = abs((tx * cdx + ty * cdy) / (tn * cn))
            cross_angs.append(math.degrees(math.acos(min(1.0, dot))))
        cross_p90 = float(np.percentile(cross_angs, 90)) if cross_angs else 99.0
        L28 = 0.0
        for k, sp in enumerate(splays):
            if sp > SPLAY_STRICT_DEG:
                break
            L28 = (k + 1) * 3.0
        gates = {
            "gate_resid_ok": z_resid_p90 <= GATE_RESID_P90,
            "gate_cross_ok": cross_p90 <= GATE_CROSS_ANG,
            "gate_min_len_ok": L >= MIN_BAY_LEN,
        }
        gates_ok = all(gates.values())
        rec.update({
            "emitted": bool(gates_ok), "z_resid_p90": round(z_resid_p90, 2),
            "cross_ang_p90": round(cross_p90, 1), **gates,
            "len_45_ft": round(L, 1), "len_28_ft": round(L28, 1),
            "seats_45": int(L * (1 - AISLE_LOSS) // SEAT_W_G) if gates_ok else 0,
            "seats_28": int(L28 * (1 - AISLE_LOSS) // SEAT_W_G) if gates_ok else 0,
            "line": ext_line if gates_ok else None,
        })
        out.append(rec)
    emitted = [r for r in out if r.get("line") is not None]
    for a, b in zip(emitted, emitted[1:]):
        d = a["line"].distance(b["line"])
        a["clearance_to_next_ft"] = round(d, 2)
        if d < GATE_CLEAR:
            a["emitted"] = False; a["reason"] = f"clearance {d:.2f} < {GATE_CLEAR}"
            a["seats_45"] = a["seats_28"] = 0
    return out


# ── scenario assembly (two-phase: emit rows 1-18, MEASURE, solve, emit ops) ─────
def measured_chain_solve(delta, regrade_passes, promote_rows):
    """Solve regrade/promotion elevations against the MEASURED emitted surface.

    Walks each section's seated rows in order. Rows already emitted (1-18)
    contribute their measured centreline-median elevation; promoted rows enter
    at their composition elevation. Returns {(sec,row): solved_elev} for every
    row whose grade must change (lift vs measured/composition), plus the
    measured medians for reporting."""
    proposed = delta.proposed(STATE)
    measured = {}
    for sec in SECTIONS:
        for row in seated_rows(sec):
            if row <= FORMAL_STOP_ROW and (sec, row) in LINES:
                vals = sample_centreline(proposed, LINES[(sec, row)])
                measured[(sec, row)] = float(np.median(vals)) if vals else COMP[(sec, row)]["elev"]
    cur = dict(measured)
    for sec in SECTIONS:
        for row in promote_rows:
            if (sec, row) in COMP:
                cur[(sec, row)] = COMP[(sec, row)]["elev"]
    changes = {}
    max_row = max([FORMAL_STOP_ROW] + list(promote_rows))
    for rows, target_c_mm, only_if_below in regrade_passes:
        c_ft = target_c_mm / 304.8
        for sec in SECTIONS:
            prev = None
            for row in [r for r in seated_rows(sec) if r <= max_row]:
                if (sec, row) not in cur:
                    continue
                D = COMP[(sec, row)]["axis_r"] - STAGE_R
                e_now = cur[(sec, row)]
                if prev is None or row not in rows:
                    new = e_now
                else:
                    Dp, Ep = prev
                    min_elev = FOCUS_ELEV + (c_ft + Ep) * (D / Dp) - EYE_HT
                    min_elev = math.ceil(min_elev * 100) / 100
                    new = max(e_now, min_elev) if only_if_below else min_elev
                if abs(new - e_now) > 0.005:
                    changes[(sec, row)] = round(new, 2)
                    cur[(sec, row)] = round(new, 2)
                else:
                    new = e_now
                prev = (D, new + EYE_HT - FOCUS_ELEV)
    # every promoted row must carry an explicit design elevation
    for sec in SECTIONS:
        for row in promote_rows:
            if (sec, row) in COMP and (sec, row) not in changes:
                changes[(sec, row)] = COMP[(sec, row)]["elev"]
    return changes, measured


def build_scenario(name, promote_rows, regrade_passes, with_extension):
    delta = ClayDelta.zeros(STATE)
    feats = []
    bands = {}
    tread_mask = np.zeros_like(FINITE)
    formal_rows = [r for r in range(1, FORMAL_STOP_ROW + 1)
                   if r != PROMENADE_ROW and r not in AISLE_ROWS]

    def emit_band(sec, row, line, base_elev, status, seats, part="main"):
        nonlocal tread_mask
        poly = line.buffer(TREAD_HALF, cap_style=2)
        delta.terrace_plane(STATE, poly, base_elev_navd88=base_elev,
                            cross_slope_pct=CROSS_SLOPE, longitudinal_slope_pct=LONG_SLOPE)
        m = delta._mask_for_geom(poly, STATE) & FINITE
        tread_mask |= m
        role = ("formal_restored_tread" if status == "formal"
                else "tier_promoted_tread" if part == "main" else "n1_extension_tread")
        feats.append({"type": "Feature", "geometry": mapping(poly),
                      "properties": {"role": role, "row": row, "section": sec,
                                     "part": part, "seats": seats,
                                     "design_elev": base_elev}})
        bands[(sec, row, part)] = {
            "section": sec, "row": row, "part": part, "status": status,
            "line": line, "poly": poly, "mask": m, "seats": seats,
            "axis_r": COMP[(sec, row)]["axis_r"], "design_elev": base_elev,
        }

    # phase 1: the locked Scenario E formal bowl (rows 1-18, DEM-median planes)
    for sec in SECTIONS:
        for row in formal_rows:
            if (sec, row) in LINES:
                emit_band(sec, row, LINES[(sec, row)], None, "formal",
                          COMP[(sec, row)]["seats"])

    # phase 2: solve regrades/promotions against the MEASURED surface, emit
    changes, measured = measured_chain_solve(delta, regrade_passes, promote_rows)
    regrade_log = []
    for (sec, row), new_elev in sorted(changes.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if (sec, row) not in LINES:
            continue
        is_promo = row in promote_rows
        ref = COMP[(sec, row)]["elev"] if is_promo else measured.get((sec, row), COMP[(sec, row)]["elev"])
        regrade_log.append({"band": f"{sec} r{row}",
                            "from_ref": round(ref, 2), "to": new_elev,
                            "dz_ft": round(new_elev - ref, 2),
                            "kind": "promotion" if is_promo else "regrade"})
        emit_band(sec, row, LINES[(sec, row)], new_elev,
                  "promoted" if is_promo else "formal",
                  COMP[(sec, row)]["seats"],
                  part="main")
        if not is_promo:
            bands[(sec, row, "main")]["status"] = "formal"
            bands[(sec, row, "main")]["regraded"] = True

    # phase 2b: station-level convergence. The exactly-90 chain solves C
    # against row-median elevations; at matched 8-ft stations the emitted
    # surface can land 1-3 mm short (different along-row extents, 0.01-ft
    # grid). The regrade op's contract is C >= target ON THE REAL SURFACE,
    # so iterate: measure station-C median, lift by the deficit, re-emit.
    target_rows = []        # [(sec,row,target_mm,only_if_below)] in chain order
    for rows, target, oib in regrade_passes:
        for sec in SECTIONS:
            for row in sorted(rows):
                if (sec, row, "main") in bands:
                    target_rows.append((sec, row, target, oib))
    target_rows.sort(key=lambda t: (t[1], t[0]))
    iteration_log = []
    for it in range(4):
        lifted = 0
        for sec, row, target, oib in target_rows:
            b = bands[(sec, row, "main")]
            pr = prev_seated_row(sec, row)
            if pr is None:
                continue
            proposed = delta.proposed(STATE)
            plines = [bands[k]["line"] for k in bands
                      if k[0] == sec and k[1] == pr and k[2] == "main"]
            if not plines:
                continue
            D = COMP[(sec, row)]["axis_r"] - STAGE_R
            Dp = COMP[(sec, pr)]["axis_r"] - STAGE_R
            line = b["line"]; L = max(line.length, 1e-6)
            n_st = max(1, int(round(L / STATION_FT)))
            cs = []
            for j in range(n_st):
                p = line.interpolate((j + 0.5) / n_st, normalized=True)
                z = STATE.elev_at(proposed, p.x, p.y)
                pl = plines[0]
                q = pl.interpolate(pl.project(p))
                zp = STATE.elev_at(proposed, q.x, q.y)
                if np.isfinite(z) and np.isfinite(zp):
                    cs.append(((z + EYE_HT - FOCUS_ELEV) * (Dp / D)
                               - (zp + EYE_HT - FOCUS_ELEV)) * 304.8)
            if not cs:
                continue
            # p05 criterion: the regrade op's contract is the WHOLE row at the
            # formal profile, so the lift must clear the sagging end stations
            # (row-end curvature mismatch), not just the row median. p05 rather
            # than min so a single matched-point artifact cannot drive the lift.
            med = float(np.percentile(cs, 5))
            if med >= target - 0.05:
                continue
            lift_ft = math.ceil(((target - med + 1.0) / 304.8 / (Dp / D)) * 100) / 100
            cur_elev = b["design_elev"]
            if cur_elev is None:        # median-emitted band: anchor at measurement
                vals = sample_centreline(proposed, line)
                cur_elev = float(np.median(vals))
            new_elev = round(cur_elev + lift_ft, 2)
            emit_band(sec, row, line, new_elev, b["status"], b["seats"])
            changes[(sec, row)] = new_elev
            iteration_log.append({"band": f"{sec} r{row}", "iteration": it + 1,
                                  "station_c_p05": round(med, 1),
                                  "target_c_mm": target,
                                  "lift_ft": lift_ft, "to": new_elev})
            lifted += 1
        if not lifted:
            break

    # phase 3: N1 extension (adopts the solved design elevations)
    ext_records = []
    if with_extension:
        def design_elev_fn(row):
            return changes.get(("east", row), measured.get(("east", row),
                               COMP[("east", row)]["elev"]))
        ext_records = build_extension_bands(design_elev_fn)
        for rec in ext_records:
            if not rec.get("emitted") or rec.get("line") is None:
                continue
            emit_band("east", rec["row"], rec["line"], rec["design_elev"],
                      "promoted" if rec["row"] > FORMAL_STOP_ROW else "formal",
                      rec["seats_45"], part="extension")

    # phase 4: cross-aisle (rows 9/10 reclassification, accessible_fit section)
    row_polys = {}
    for (sec, row), line in LINES.items():
        if COMP[(sec, row)]["kind"] == "seating" and 1 <= row <= FORMAL_STOP_ROW:
            row_polys.setdefault(row, []).append(line.buffer(TREAD_HALF, cap_style=2))
    retained = unary_union([p for r in row_polys if r not in AISLE_ROWS
                            for p in row_polys[r]])
    xa_poly = unary_union([p for r in AISLE_ROWS for p in row_polys[r]]).difference(retained)
    elev_bend = {r: COMP[("bend", r)]["elev"] for r in AISLE_ROWS}
    xa_mask, xa_sec = accessible_cross_aisle(delta, xa_poly, list(AISLE_ROWS), elev_bend)
    feats.append({"type": "Feature", "geometry": mapping(xa_poly),
                  "properties": {"role": "cross_aisle", **xa_sec}})

    # phase 5: ADA switchbacks
    ada_results = []
    for f in ADA_SRC["features"]:
        pr = f["properties"]
        if pr.get("type") == "switchback_ramp":
            corridor, res = emit_switchback(delta, pr["name"], shape(f["geometry"]),
                                            pr.get("total_drop_ft", 6.0))
            ada_results.append(res)
            feats.append({"type": "Feature", "geometry": mapping(corridor),
                          "properties": {"role": "ada_ramp", **res}})

    # phase 6: flank swales at azimuths derived from the EMITTED tread set
    tre_az = STATE.AZ[tread_mask]
    east_az = float(np.percentile(tre_az, 0.5)) - 5.0
    south_az = float(np.percentile(tre_az, 99.5)) + 5.0
    swale_results = []
    for nm, az in (("east_flank_swale", east_az), ("south_flank_swale", south_az)):
        poly, res = emit_swale(delta, nm, az, tread_mask)
        swale_results.append(res)
        feats.append({"type": "Feature", "geometry": mapping(poly),
                      "properties": {"role": "drainage_swale", **res}})

    cell_mask = STATE.rasterize_geom(_cell)
    cell_conflict = int((cell_mask & tread_mask).sum())

    # disjoint component masks for incremental attribution
    masks = {"n1_extension": np.zeros_like(FINITE),
             "promoted_rows": np.zeros_like(FINITE),
             "regraded_rows_11_18": np.zeros_like(FINITE),
             "treads_rows_1_18": np.zeros_like(FINITE)}
    for b in bands.values():
        if b["part"] == "extension":
            masks["n1_extension"] |= b["mask"]
        elif b["status"] == "promoted":
            masks["promoted_rows"] |= b["mask"]
        elif b.get("regraded"):
            masks["regraded_rows_11_18"] |= b["mask"]
        else:
            masks["treads_rows_1_18"] |= b["mask"]
    taken = np.zeros_like(FINITE)
    for nm in ("n1_extension", "promoted_rows", "regraded_rows_11_18", "treads_rows_1_18"):
        masks[nm] = masks[nm] & ~taken
        taken |= masks[nm]

    # re-emitted bands appended duplicate features; keep the last per band
    seen = {}
    for f in feats:
        p = f["properties"]
        seen[(p["role"], p.get("section"), p.get("row"), p.get("part"), p.get("name"))] = f
    feats = list(seen.values())

    return {
        "name": name, "delta": delta, "bands": bands, "features": feats,
        "iteration_log": iteration_log,
        "changes": {f"{k[0]} r{k[1]}": v for k, v in changes.items()},
        "measured_1_18": {f"{k[0]} r{k[1]}": round(v, 2) for k, v in measured.items()},
        "regrade_log": regrade_log, "ext_records": ext_records,
        "xa": xa_sec, "ada": ada_results, "swales": swale_results,
        "tread_mask": tread_mask, "comp_masks": masks,
        "cell_conflict_cells": cell_conflict,
        "swale_az": {"east": round(east_az, 1), "south": round(south_az, 1)},
    }


# ── validation: station-matched C + Rule 4 segment gates ────────────────────────
def prev_seated_row(sec, row):
    rows = seated_rows(sec)
    i = rows.index(row)
    return rows[i - 1] if i > 0 else None


def station_c_values(scn, proposed):
    """Per-band list of (station_ft, C_mm) measured at centreline stations on
    the emitted surface, matched to the nearest point on the previous seated
    row's centreline. Extensions use their own line vs the row in front's
    full line (main + extension if emitted)."""
    prev_lines = {}
    for (sec, row, part), b in scn["bands"].items():
        prev_lines.setdefault((sec, row), []).append(b["line"])
    out = {}
    for key, b in scn["bands"].items():
        sec, row, part = key
        pr = prev_seated_row(sec, row)
        if pr is None or (sec, pr) not in prev_lines:
            out[key] = None      # front row: no upstream head
            continue
        plines = prev_lines[(sec, pr)]
        D = COMP[(sec, row)]["axis_r"] - STAGE_R
        Dp = COMP[(sec, pr)]["axis_r"] - STAGE_R
        line = b["line"]; L = max(line.length, 1e-6)
        n_st = max(1, int(round(L / STATION_FT)))
        cs = []
        for j in range(n_st):
            t = (j + 0.5) / n_st
            p = line.interpolate(t, normalized=True)
            z = STATE.elev_at(proposed, p.x, p.y)
            pl = min(plines, key=lambda l: l.distance(p))
            q = pl.interpolate(pl.project(p))
            zp = STATE.elev_at(proposed, q.x, q.y)
            if not (np.isfinite(z) and np.isfinite(zp)):
                cs.append((round((j + 0.5) * L / n_st, 1), None))
                continue
            E = z + EYE_HT - FOCUS_ELEV
            Ep = zp + EYE_HT - FOCUS_ELEV
            cs.append((round((j + 0.5) * L / n_st, 1),
                       round((E * (Dp / D) - Ep) * 304.8, 1)))
        out[key] = cs
    return out


def validate_segments(scn, proposed, c_stations):
    segments = []
    dd = scn["delta"].delta()
    ny, nx = proposed.shape
    for key, b in sorted(scn["bands"].items(), key=lambda kv: (kv[0][1], kv[0][0])):
        sec, row, part = key
        mask = b["mask"]
        interior = binary_erosion(mask, iterations=1)
        ri, ci = np.where(mask)
        if len(ri) == 0:
            continue
        xs = TF.c + (ci + 0.5) * TF.a; ys = TF.f + (ri + 0.5) * TF.e
        line = b["line"]; L = max(line.length, 1e-6)
        d_along = np.array([line.project(Point(x, y)) for x, y in zip(xs, ys)])
        Rcell = np.hypot(xs - FX, ys - FY)
        is_int = interior[ri, ci]
        zc = proposed[ri, ci]
        cs = c_stations.get(key)
        n_st = max(1, int(round(L / STATION_FT)))
        edges = np.linspace(0, L, n_st + 1)
        for j in range(n_st):
            d0, d1 = edges[j], edges[j + 1]
            in_seg = ((d_along >= d0) & (d_along < d1) if j < n_st - 1
                      else (d_along >= d0) & (d_along <= d1 + 1e-6))
            if in_seg.sum() == 0:
                continue
            c_ref = None if cs is None else (cs[j][1] if j < len(cs) else None)
            c_ok = (cs is None) or (c_ref is not None and c_ref >= C_FORMAL_MM)
            seg_int = in_seg & is_int
            use = seg_int if seg_int.sum() >= 4 else in_seg
            nn = Rcell[use]; ss = d_along[use]; zz = zc[use]
            okm = np.isfinite(zz)
            nn, ss, zz = nn[okm], ss[okm], zz[okm]
            if len(zz) >= 4:
                nn = nn - nn.mean(); ss = ss - ss.mean()
                A = np.column_stack([nn, ss, np.ones_like(nn)])
                coef, *_ = np.linalg.lstsq(A, zz, rcond=None)
                resid = zz - A @ coef
                owned = np.abs(resid) <= OWNED_RESID_FT
                if owned.sum() >= 4 and owned.sum() < len(zz):
                    # refit on owned cells only (neighbour-row riser cells out)
                    coef, *_ = np.linalg.lstsq(A[owned], zz[owned], rcond=None)
                    resid = zz[owned] - A[owned] @ coef
                cross = abs(coef[0]) * 100.0; lng = abs(coef[1]) * 100.0
                twist = float(np.sqrt(np.mean(resid ** 2)))
            else:
                cross, lng, twist = CROSS_SLOPE, LONG_SLOPE, 0.0
                coef = None
            # grade break only on cells owned by this segment's plane
            sel = np.zeros(len(ri), bool)
            idx = np.where(use)[0][okm] if len(zz) else np.array([], int)
            if coef is not None and len(idx):
                nn2 = Rcell[idx] - Rcell[use][okm].mean()
                # recompute ownership against final plane for ALL in_seg cells
                allidx = np.where(in_seg)[0]
                nA = Rcell[allidx]; sA = d_along[allidx]; zA = zc[allidx]
                okA = np.isfinite(zA)
                nA = nA - Rcell[use][okm].mean() if False else nA - nA[okA].mean()
                sA = sA - sA[okA].mean()
                zhat = coef[0] * nA + coef[1] * sA + coef[2]
                ownA = okA & (np.abs(zA - zhat) <= OWNED_RESID_FT)
                sel[allidx[ownA]] = True
            else:
                sel[np.where(in_seg)[0]] = True
            seg_mask = np.zeros_like(mask)
            seg_mask[ri[sel], ci[sel]] = True
            gb_vals = []
            for y, x in zip(*np.where(seg_mask)):
                z = proposed[y, x]
                if not np.isfinite(z):
                    continue
                loc = [abs(proposed[y + dy, x + dx] - z)
                       for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))
                       if 0 <= y + dy < ny and 0 <= x + dx < nx
                       and seg_mask[y + dy, x + dx] and np.isfinite(proposed[y + dy, x + dx])]
                if loc:
                    gb_vals.append(max(loc))
            gb = float(np.percentile(gb_vals, 95)) if gb_vals else 0.0
            slope_ok = cross <= CROSS_PASS and lng <= LONG_PASS and twist <= TWIST_PASS
            cont_ok = gb <= CONTINUITY_FT
            formal_ok = bool(c_ok and slope_ok and cont_ok)
            d_seg = dd[ri[in_seg], ci[in_seg]]
            reasons = []
            if not c_ok: reasons.append(f"C_{c_ref}mm")
            if not slope_ok: reasons.append(f"slope_x{cross:.1f}/s{lng:.1f}/d{twist:.2f}")
            if not cont_ok: reasons.append(f"grade_break_{gb*12:.1f}in")
            segments.append({
                "band": f"{sec} r{row}" + ("" if part == "main" else f" [{part}]"),
                "row": row, "section": sec, "part": part,
                "station_ft": round((d0 + d1) / 2, 1),
                "C_actual_mm": c_ref if c_ref is not None else "",
                "cross_slope_pct": round(cross, 2),
                "long_slope_pct": round(lng, 2),
                "plane_resid_ft": round(twist, 3),
                "grade_break_in": round(gb * 12, 1),
                "max_cut_ft": round(float(np.maximum(-d_seg, 0).max()) if d_seg.size else 0, 2),
                "max_fill_ft": round(float(np.maximum(d_seg, 0).max()) if d_seg.size else 0, 2),
                "formal_seat_allowed": formal_ok,
                "failure_reason": ";".join(reasons),
                "_cells": int(in_seg.sum()),
            })
    return segments


def rollup_seats(scn, segments):
    by_band = {}
    for s in segments:
        by_band.setdefault((s["section"], s["row"], s["part"]), []).append(s)
    banded = {"A": 0.0, "other": 0.0}
    per_band = []
    for key, segs in by_band.items():
        b = scn["bands"][key]
        tot = sum(s["_cells"] for s in segs) or 1
        ok = sum(s["_cells"] for s in segs if s["formal_seat_allowed"])
        a = b["seats"] * ok / tot
        banded["A"] += a
        banded["other"] += b["seats"] - a
        per_band.append({"band": f"{key[0]} r{key[1]}" + ("" if key[2] == "main" else " [ext]"),
                         "seats": b["seats"], "band_a": round(a, 1),
                         "pass_frac": round(ok / tot, 3),
                         "status": b["status"],
                         "fail_reasons": sorted({r for s in segs if s["failure_reason"]
                                                 for r in s["failure_reason"].split(";")})})
    return banded, per_band


def depth_caps_and_walls(scn, max_cut_cap, max_fill_cap, wall_trig=3.0):
    issues, walls = [], []
    dd = scn["delta"].delta()
    changed = set(scn["changes"].keys())
    for key, b in scn["bands"].items():
        ctx = f"{key[0]} r{key[1]}{'' if key[2]=='main' else ' [ext]'}"
        if b["status"] != "promoted" and key[2] != "extension" \
           and f"{key[0]} r{key[1]}" not in changed:
            continue            # caps apply to the INCREMENTAL ops, not the locked baseline
        d = dd[b["mask"]]
        mc = float(np.maximum(-d, 0).max()) if d.size else 0.0
        mf = float(np.maximum(d, 0).max()) if d.size else 0.0
        if mc > max_cut_cap:
            issues.append(f"{ctx}: cut {mc:.2f} ft exceeds cap {max_cut_cap}")
        if mf > max_fill_cap:
            issues.append(f"{ctx}: fill {mf:.2f} ft exceeds cap {max_fill_cap}")
        if mc > wall_trig or mf > wall_trig:
            walls.append({"band": ctx, "max_cut_ft": round(mc, 2),
                          "max_fill_ft": round(mf, 2)})
    return issues, walls


def incremental_earthwork(scn, base_delta):
    diff = scn["delta"].delta() - base_delta.delta()
    diff = np.where(FINITE, diff, 0.0)
    cut = float(np.maximum(-diff, 0).sum()) / 27.0
    fill = float(np.maximum(diff, 0).sum()) / 27.0
    per_comp = {}
    named = np.zeros_like(FINITE)
    for nm, m in scn["comp_masks"].items():
        d = diff[m]
        per_comp[nm] = {"cut_cy": round(float(np.maximum(-d, 0).sum()) / 27.0, 1),
                        "fill_cy": round(float(np.maximum(d, 0).sum()) / 27.0, 1)}
        named |= m
    d = diff[~named & FINITE]
    per_comp["other_(swales/ada/aisle)"] = {
        "cut_cy": round(float(np.maximum(-d, 0).sum()) / 27.0, 1),
        "fill_cy": round(float(np.maximum(d, 0).sum()) / 27.0, 1)}
    return {"incr_cut_cy": round(cut, 1), "incr_fill_cy": round(fill, 1),
            "incr_gross_cy": round(cut + fill, 1), "per_component": per_comp}


def run_tier(scn, base, caps):
    proposed = scn["delta"].proposed(STATE)
    c_stations = station_c_values(scn, proposed)
    segments = validate_segments(scn, proposed, c_stations)
    banded, per_band = rollup_seats(scn, segments)
    cap_issues, walls = depth_caps_and_walls(scn, *caps)
    vol = EW.volumes(scn["delta"])
    incr = incremental_earthwork(scn, base["delta"]) if base is not None else None
    # row-level C summary: median of station Cs per band
    c_rows = {}
    for key, cs in c_stations.items():
        if cs is None:
            c_rows[f"{key[0]} r{key[1]}" + ("" if key[2] == "main" else " [ext]")] = None
        else:
            vals = [c for _, c in cs if c is not None]
            c_rows[f"{key[0]} r{key[1]}" + ("" if key[2] == "main" else " [ext]")] = (
                round(float(np.median(vals)), 1) if vals else None)
    promoted_med = {}
    for key, b in scn["bands"].items():
        if b["status"] == "promoted":
            v = proposed[b["mask"]]; v = v[np.isfinite(v)]
            promoted_med[key] = float(np.median(v)) if len(v) else np.nan
    sees_bay = all((v + EYE_HT) > 618.5 for v in promoted_med.values()) if promoted_med else True
    formal_c = [c for k, c in c_rows.items() if c is not None]
    hard = {
        "sightlines_formal_ok": all(c >= C_FORMAL_MM for c in formal_c),
        "ada_ok": all(r["running_ok"] for r in scn["ada"]),
        "drainage_ok": all(s["valid"] for s in scn["swales"]),
        "cross_aisle_ok": scn["xa"]["drains"] and scn["xa"]["wheelable"],
        "bay_view_ok": bool(sees_bay),
        "treatment_cell_preserved": scn["cell_conflict_cells"] == 0,
        "no_wall_trigger": len(walls) == 0,
        "caps_ok": len(cap_issues) == 0,
    }
    return {"c_rows": c_rows, "segments": segments, "banded": banded,
            "per_band": per_band, "cap_issues": cap_issues, "walls": walls,
            "volumes": vol, "incremental": incr, "hard": hard}


def write_outputs(scn, res, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    json.dump({"type": "FeatureCollection", "features": scn["features"]},
              open(outdir / "geometry.geojson", "w"))
    cols = ["band", "row", "section", "part", "station_ft", "C_actual_mm",
            "cross_slope_pct", "long_slope_pct", "plane_resid_ft",
            "grade_break_in", "max_cut_ft", "max_fill_ft",
            "formal_seat_allowed", "failure_reason"]
    with open(outdir / "segments.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for s in res["segments"]:
            w.writerow(s)
    payload = {k: v for k, v in res.items() if k != "segments"}
    payload["changes"] = scn["changes"]
    payload["regrade_log"] = scn["regrade_log"]
    payload["iteration_log"] = scn["iteration_log"]
    payload["measured_rows_1_18"] = scn["measured_1_18"]
    payload["ext_records"] = [{k: v for k, v in r.items() if k != "line"}
                              for r in scn["ext_records"]]
    payload["cross_aisle"] = scn["xa"]; payload["ada"] = scn["ada"]
    payload["swales"] = scn["swales"]; payload["swale_az"] = scn["swale_az"]
    payload["n_segments"] = len(res["segments"])
    json.dump(payload, open(outdir / "validation.json", "w"), indent=1)


# ── run ──────────────────────────────────────────────────────────────────────────
print("=== Tier emission + validation (seating scope; stage Rule 9 untouched) ===")

base = build_scenario("Scenario_E_baseline_reemit", [], [], False)
base_vol = EW.volumes(base["delta"])
base_seats = sum(b["seats"] for b in base["bands"].values())
drift_cy = base_vol["gross_cy"] - LOCKED_TOTAL_CY
print(f"baseline re-emission: {base_vol['gross_cy']} CY vs locked {LOCKED_TOTAL_CY} "
      f"(drift {drift_cy:+.1f}); formal seats nominal {base_seats}")
if abs(drift_cy) > 0.05 * LOCKED_TOTAL_CY:
    print("!! baseline drift exceeds 5% — incremental numbers below are suspect")

base_res = run_tier(base, None, caps=(2.0, 1.5))
write_outputs(base, base_res, OUT_BASE / "Scenario_E_baseline_reemit")
print(f"  baseline validated Band-A on emitted surface: {base_res['banded']['A']:.0f} "
      f"of {base_seats}")

modest = build_scenario("modest_normalization", [19],
                        [([19], 90.0, True)], False)
modest_res = run_tier(modest, base, caps=(1.25, 1.5))   # cap raised per emission finding F3/F6
write_outputs(modest, modest_res, OUT_BASE / "modest_normalization")

ambitious = build_scenario("ambitious_shaped_bowl_seating", [19, 20],
                           [(list(range(11, 19)), 100.0, True),
                            ([19, 20], 90.0, False)], True)
amb_res = run_tier(ambitious, base, caps=(3.0, 3.0))
write_outputs(ambitious, amb_res, OUT_BASE / "ambitious_shaped_bowl_seating")

for nm, scn, res in (("baseline", base, base_res),
                     ("modest", modest, modest_res),
                     ("ambitious(seating)", ambitious, amb_res)):
    inc = res["incremental"]
    print(f"\n{nm}: Band-A {res['banded']['A']:.0f}  "
          f"total {res['volumes']['gross_cy']} CY"
          + (f"  incr {inc['incr_gross_cy']} CY" if inc else "")
          + f"  hard={'PASS' if all(res['hard'].values()) else 'FAIL'}")
    for k, v in res["hard"].items():
        if not v:
            print(f"   FAIL {k}")
    for i in res["cap_issues"]:
        print(f"   CAP {i}")
    soft = {k: c for k, c in res["c_rows"].items() if c is not None and c < C_FORMAL_MM}
    if soft:
        print(f"   C<90 rows: {soft}")
    if scn["regrade_log"]:
        lifted = [r for r in scn["regrade_log"] if abs(r["dz_ft"]) > 0.005]
        print(f"   regrades/promotions emitted: {len(scn['regrade_log'])} "
              f"({len(lifted)} with grade change)")
    if nm == "ambitious(seating)":
        ext_seats = sum(r.get("seats_45", 0) for r in scn["ext_records"] if r.get("emitted"))
        ext28 = sum(r.get("seats_28", 0) for r in scn["ext_records"] if r.get("emitted"))
        print(f"   N1 extension: {ext_seats} seats emitted@45° splay "
              f"({ext28} under strict 28°); per-row:")
        for r in scn["ext_records"]:
            print(f"     r{r['row']}: walk {r['walk_ft']} ft, stop={r['stop']}, "
                  f"emitted={r.get('emitted')}, seats45={r.get('seats_45', 0)}, "
                  f"resid_p90={r.get('z_resid_p90')}, cross_p90={r.get('cross_ang_p90')}")

json.dump({"baseline_drift_cy": round(drift_cy, 1),
           "locked_total_cy": LOCKED_TOTAL_CY,
           "reemit_total_cy": base_vol["gross_cy"],
           "baseline_validated_band_a": round(base_res["banded"]["A"], 1),
           "baseline_nominal_seats": base_seats},
          open(OUT_BASE / "_baseline_reconciliation.json", "w"), indent=1)
print(f"\nwrote {OUT_BASE}")
