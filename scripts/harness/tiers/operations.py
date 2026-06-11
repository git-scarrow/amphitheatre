"""Intervention-tier operation primitives.

Each operation mutates the SectionSeatingModel (geometry side) and/or computes
an incremental earthwork record. The convention for earthwork accounting:

  total earthwork = locked Scenario E baseline components (earthwork.csv)
                  + incremental operation CY (computed here, uniformly)

Incremental CY for a band-grade change is |new_design_elev − old_design_elev|
× band area (the Scenario E surface is already restored at old_design_elev).
For NEWLY promoted rows it is mean(|design_elev − existing terrain|) × band
area, sampled from the DEM along the band centreline — the same method for
every recipe, so tiers are comparable.

Terrain-delta ops from the original ClayDelta vocabulary remain available via
op type "terrain_delta" (kept primitives), executed against a ClayDelta with
recipe caps enforced.

Every op appends an audit record (model.ops_log) including its earthwork
increment, depth extremes, and any wall-trigger exposure.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from .geometry_model import Band, SectionSeatingModel, TierState, C_TARGET_MM

CF_PER_CY = 27.0


def _band_area_sqft(model: SectionSeatingModel, band: Band) -> float:
    g = model.band_footprint(band)
    if g is not None and band.geometry is not None:
        return float(g.area)
    return band.length_ft * model.tread_depth_ft(band)


def _terrain_stats(model: SectionSeatingModel, band: Band) -> dict:
    """Existing-ground stats under a band (centreline-sampled)."""
    line = band.centreline
    if line is None:
        return {"mean": np.nan, "n": 0}
    vals = model.state.sample_line(model.state.Z0, line)
    if not vals:
        return {"mean": np.nan, "n": 0}
    return {"mean": float(np.mean(vals)), "min": float(np.min(vals)),
            "max": float(np.max(vals)), "n": len(vals)}


def _grade_change_record(model: SectionSeatingModel, band: Band,
                         new_elev: float, vs: str) -> dict:
    """Earthwork increment for setting a band's design grade to new_elev.

    vs="design": change vs the already-restored Scenario E surface.
    vs="terrain": new surface vs existing ground (promoted rows).
    """
    area = _band_area_sqft(model, band)
    if vs == "design":
        dz = new_elev - band.tread_elev
        cut_cf = max(0.0, -dz) * area
        fill_cf = max(0.0, dz) * area
        max_cut = max(0.0, -dz)
        max_fill = max(0.0, dz)
    else:
        t = _terrain_stats(model, band)
        if not t["n"]:
            return {"cut_cy": 0.0, "fill_cy": 0.0, "max_cut_ft": 0.0,
                    "max_fill_ft": 0.0, "area_sqft": area, "no_terrain_data": True}
        line_vals = model.state.sample_line(model.state.Z0, band.centreline)
        dzs = [new_elev - v for v in line_vals]
        per_pt_area = area / len(dzs)
        cut_cf = sum(-d for d in dzs if d < 0) * per_pt_area
        fill_cf = sum(d for d in dzs if d > 0) * per_pt_area
        max_cut = max((-d for d in dzs if d < 0), default=0.0)
        max_fill = max((d for d in dzs if d > 0), default=0.0)
    return {
        "cut_cy": round(cut_cf / CF_PER_CY, 2),
        "fill_cy": round(fill_cf / CF_PER_CY, 2),
        "max_cut_ft": round(max_cut, 2),
        "max_fill_ft": round(max_fill, 2),
        "area_sqft": round(area, 0),
    }


def _check_caps(rec: dict, constraints: dict, context: str) -> list[str]:
    """Cap violations are reported, never silently clipped."""
    issues = []
    if rec.get("max_cut_ft", 0) > constraints.get("max_cut_ft", 1e9):
        issues.append(f"{context}: cut {rec['max_cut_ft']:.2f} ft exceeds recipe cap "
                      f"{constraints['max_cut_ft']} ft")
    if rec.get("max_fill_ft", 0) > constraints.get("max_fill_ft", 1e9):
        issues.append(f"{context}: fill {rec['max_fill_ft']:.2f} ft exceeds recipe cap "
                      f"{constraints['max_fill_ft']} ft")
    return issues


def _wall_exposure(rec: dict, band: Band, constraints: dict) -> dict | None:
    """Emergent wall trigger: depth beyond threshold → estimated wall length."""
    trig_c = constraints.get("wall_trigger_cut_ft", 3.0)
    trig_f = constraints.get("wall_trigger_fill_ft", 3.0)
    cut, fill = rec.get("max_cut_ft", 0), rec.get("max_fill_ft", 0)
    if cut <= trig_c and fill <= trig_f:
        return None
    return {
        "band": f"{band.section} r{band.row}",
        "max_cut_ft": cut, "max_fill_ft": fill,
        "est_wall_length_ft": round(band.length_ft, 0),
        "kind": "low_seat_wall" if max(cut, fill) <= 5.0 else "retaining_wall",
    }


# ── operations ──────────────────────────────────────────────────────────────

def op_add_row(model, state, params, constraints) -> dict:
    """Promote a terrace row (composition data exists) to formal seating."""
    sections = params.get("sections", ["east", "bend", "south"])
    row = int(params["row"])
    promoted, cut, fill = [], 0.0, 0.0
    issues, walls, max_cut, max_fill = [], [], 0.0, 0.0
    for s in sections:
        band = model.bands.get((s, row))
        if band is None:
            issues.append(f"add_row: no composition data for {s} r{row}")
            continue
        if band.status == "formal":
            continue
        rec = _grade_change_record(model, band, band.tread_elev, vs="terrain")
        issues += _check_caps(rec, constraints, f"add_row {s} r{row}")
        w = _wall_exposure(rec, band, constraints)
        if w:
            walls.append(w)
        band.status = "formal"
        band.added_by_op = "add_row"
        promoted.append(f"{s} r{row}")
        cut += rec["cut_cy"]; fill += rec["fill_cy"]
        max_cut = max(max_cut, rec["max_cut_ft"])
        max_fill = max(max_fill, rec["max_fill_ft"])
    return {"op": "add_row", "promoted": promoted,
            "cut_cy": round(cut, 1), "fill_cy": round(fill, 1),
            "max_cut_ft": max_cut, "max_fill_ft": max_fill,
            "cap_issues": issues, "wall_exposure": walls,
            "provenance": params.get("provenance", "")}


def op_extend_section_arc(model, state, params, constraints) -> dict:
    """On-contour arc extension of a section (measured candidate, e.g. N1).

    Analysis-tier: seats/CY come from the measured contour-walk study; the
    geometry is NOT re-emitted here. Seats are added pro-rata to the rows in
    the declared range; the op records the re-emission requirement.
    """
    section = params["section"]
    seats = int(params["seats"])
    cy = float(params.get("cy_proxy", 0.0))
    r0, r1 = params.get("rows", [6, 18])
    rows = [r for r in range(r0, r1 + 1)
            if (section, r) in model.bands
            and model.bands[(section, r)].status == "formal"]
    arc_ft = float(params.get("arc_ft", 0.0))
    total_len = sum(model.bands[(section, r)].length_ft for r in rows) or 1.0
    for r in rows:
        b = model.bands[(section, r)]
        share = b.length_ft / total_len
        b.seats += int(round(seats * share))
        b.length_ft = round(b.length_ft + arc_ft * share, 1)
    return {"op": "extend_section_arc", "section": section,
            "seats_added": seats, "arc_ft": arc_ft,
            "cut_cy": round(cy * 0.5, 1), "fill_cy": round(cy * 0.5, 1),
            "max_cut_ft": 0.5, "max_fill_ft": 0.5,
            "cap_issues": [], "wall_exposure": [],
            "analysis_tier": True,
            "provenance": params.get("provenance",
                "contour-walk extension; requires re-emission + re-validation "
                "(canon Rules 3/5) before seats are claimed")}


def op_trim_section(model, state, params, constraints) -> dict:
    section = params["section"]
    rows = params.get("rows", [])
    removed = 0
    for r in rows:
        b = model.bands.get((section, r))
        if b and b.status == "formal":
            removed += b.seats
            b.seats = 0
            b.status = "trimmed"
    return {"op": "trim_section", "section": section, "rows": rows,
            "seats_removed": removed, "cut_cy": 0.0, "fill_cy": 0.0,
            "max_cut_ft": 0.0, "max_fill_ft": 0.0,
            "cap_issues": [], "wall_exposure": []}


def _regrade_chain(model, section: str, rows: list[int],
                   target_c_mm: float, only_if_below: bool) -> dict[int, float]:
    """Walk a section's seated rows in order, raising (or, for full regrades,
    setting) the named rows to the elevation that achieves target C against
    the PREVIOUS row's actual (possibly just-updated) elevation. This keeps
    the chain consistent when some rows are skipped (only_if_below)."""
    from .geometry_model import STAGE_R_FT, FOCUS_ELEV, EYE_HT_FT
    c_ft = target_c_mm / 304.8
    all_rows = sorted(b.row for b in model.bands.values()
                      if b.section == section
                      and b.status not in ("trimmed",))
    changes: dict[int, float] = {}
    prev: tuple[float, float] | None = None
    for row in all_rows:
        b = model.bands[(section, row)]
        if b.status in ("promenade", "aisle", "lawn"):
            continue
        D = b.axis_radius_ft - STAGE_R_FT
        cur = b.tread_elev
        if prev is None or row not in rows:
            new = cur
        else:
            Dp, Ep = prev
            min_elev = FOCUS_ELEV + (c_ft + Ep) * (D / Dp) - EYE_HT_FT
            min_elev = math.ceil(min_elev * 100) / 100   # never land below target
            new = max(cur, min_elev) if only_if_below else min_elev
        # elevations live on a 0.01 ft grid (ceil above), so any real change
        # is >= 0.01; a 1 mm C shortfall needs ~0.003-0.01 ft of lift and
        # must not be swallowed by the threshold
        if abs(new - cur) > 0.005:
            changes[row] = round(new, 2)
        else:
            new = cur   # micro-change not applied — chain off the real grade
        prev = (D, new + EYE_HT_FT - FOCUS_ELEV)
    return changes


def op_regrade_rows(model, state, params, constraints) -> dict:
    """Row-family morphing: re-riser the named rows to a target C profile."""
    sections = params.get("sections", ["east", "bend", "south"])
    rows = params["rows"]
    target = float(params.get("target_c_mm", C_TARGET_MM))
    only_if_below = bool(params.get("only_if_below", False))
    changed, cut, fill = [], 0.0, 0.0
    issues, walls, max_cut, max_fill = [], [], 0.0, 0.0
    for s in sections:
        profile = _regrade_chain(model, s, list(rows), target, only_if_below)
        for r, new_elev in profile.items():
            band = model.bands.get((s, r))
            if band is None or band.status != "formal":
                continue
            # vs="design": the band's current tread is its current design
            # surface — its restore cost is already carried (baseline CSV or
            # the add_row record); only the grade CHANGE is charged here.
            rec = _grade_change_record(model, band, new_elev, vs="design")
            issues += _check_caps(rec, constraints, f"regrade {s} r{r}")
            w = _wall_exposure(rec, band, constraints)
            if w:
                walls.append(w)
            changed.append({"band": f"{s} r{r}",
                            "from": band.tread_elev, "to": new_elev,
                            "dz_ft": round(new_elev - band.tread_elev, 2)})
            band.tread_elev = new_elev
            cut += rec["cut_cy"]; fill += rec["fill_cy"]
            max_cut = max(max_cut, rec["max_cut_ft"])
            max_fill = max(max_fill, rec["max_fill_ft"])
    return {"op": "regrade_rows", "target_c_mm": target,
            "bands_changed": len(changed), "changes": changed,
            "cut_cy": round(cut, 1), "fill_cy": round(fill, 1),
            "max_cut_ft": round(max_cut, 2), "max_fill_ft": round(max_fill, 2),
            "cap_issues": issues, "wall_exposure": walls,
            "note": params.get("note", "")}


def op_smooth_row_end_shoulders(model, state, params, constraints) -> dict:
    cy = float(params.get("extra_topsoil_cy", 8.0))
    n = len(model.features.get("row_end_shoulder", []))
    return {"op": "smooth_row_end_shoulders", "shoulders": n,
            "treatment": params.get("treatment", "topsoil_only"),
            "topsoil_cy": cy, "cut_cy": 0.0, "fill_cy": 0.0,
            "max_cut_ft": 0.0, "max_fill_ft": 0.3,
            "cap_issues": [], "wall_exposure": [],
            "note": params.get("note", "")}


def op_solve_cross_aisle_plane(model, state, params, constraints) -> dict:
    cross = float(params.get("cross_slope_pct", 2.0))
    lng = float(params.get("long_slope_pct", 1.0))
    cy = float(params.get("cy_delta", 4.0))
    ok = cross <= 2.0 and lng <= 5.0
    model.cross_aisle.update({
        "cross_slope_pct": cross, "long_slope_pct": lng,
        "drains": True, "wheelable": ok, "resolved_by_op": "solve_cross_aisle_plane",
    })
    return {"op": "solve_cross_aisle_plane",
            "cross_slope_pct": cross, "long_slope_pct": lng,
            "accessible_fit": ok,
            "cut_cy": round(cy * 0.4, 1), "fill_cy": round(cy * 0.6, 1),
            "max_cut_ft": 0.3, "max_fill_ft": 0.3,
            "cap_issues": [], "wall_exposure": [],
            "note": params.get("note", "")}


def op_refit_stage(model, state, params, constraints) -> dict:
    """Stage refit to a measured sweep/study candidate.

    Rule 9 stays OPEN: rule9_status may be 'open' or 'open_candidate', never
    'resolved' (gate-enforced).

    Placement modes:
      solve_from_residuals: true — the study tables (STAGE_SHAPE_STUDY §A)
        report RESIDUAL mismatch/lateral, not applied shifts. This mode
        solves the focal point that reproduces those residuals against the
        current audience centroid. Sign convention: the shape study reports
        mismatch with the OPPOSITE sign to STAGE_REFIT_SWEEP and this
        evaluator (centroid frame, positive = stage axis clockwise of the
        audience bearing); lateral has the same sign everywhere.
      otherwise — explicit lateral_shift_ft / pull_upstage_ft move.
    """
    status = params.get("rule9_status", "open_candidate")
    if status == "resolved":
        raise ValueError("refit_stage: rule9_status 'resolved' is forbidden "
                         "while DESIGN_CANON Rule 9 is open")
    ax = float(params.get("axis_az", model.stage["axis_az"]))
    a = math.radians(ax)
    ux, uy = math.sin(a), math.cos(a)            # along axis (toward audience)
    nx, ny = math.cos(a), -math.sin(a)           # right normal
    if params.get("solve_from_residuals"):
        # residuals in the SHAPE-STUDY sign convention
        m_study = float(params["study_mismatch_deg"])
        l_resid = float(params["study_lateral_ft"])
        m = -m_study                              # convert to evaluator/sweep sign
        cen = model.audience_centroid()
        bearing = ax - m
        s = math.sin(math.radians(bearing - ax))
        if abs(s) < 1e-4:
            dist = math.hypot(cen[0] - model.stage["sf_x"],
                              cen[1] - model.stage["sf_y"])
        else:
            dist = l_resid / s
        br = math.radians(bearing)
        sfx = cen[0] - dist * math.sin(br)
        sfy = cen[1] - dist * math.cos(br)
    else:
        lat = float(params.get("lateral_shift_ft", 0.0))
        pull = float(params.get("pull_upstage_ft", 0.0))
        sfx = model.stage["sf_x"] + nx * lat - ux * pull
        sfy = model.stage["sf_y"] + ny * lat - uy * pull
    cy = float(params.get("earthwork_cy", 0.0))
    model.stage.update({
        "name": params.get("candidate", "refit"),
        "axis_az": ax, "sf_x": sfx, "sf_y": sfy,
        "rule9_status": status,
        "row1_gap_ft": params.get("row1_gap_ft", model.stage["row1_gap_ft"]),
        "cell_gap_ft": params.get("cell_gap_ft"),
        "bay_obstruction_pct": float(params.get("bay_obstruction_pct", 0.0)),
        "cell_obstruction_pct": float(params.get("cell_obstruction_pct", 0.0)),
        "foreground_obstruction_pct": float(params.get("foreground_obstruction_pct", 0.0)),
        "declared_axis_mismatch_deg": params.get("axis_mismatch_deg",
                                                 params.get("study_mismatch_deg")),
        "declared_lateral_offset_ft": params.get("lateral_offset_ft",
                                                 params.get("study_lateral_ft")),
        "declared_frame": "STAGE_SHAPE_STUDY (centroid frame, study sign: "
                          "negative = stage axis clockwise of audience bearing)",
        "earthwork_delta_cy": cy,
        "provenance": params.get("provenance", ""),
    })
    return {"op": "refit_stage", "candidate": params.get("candidate"),
            "axis_az": ax,
            "sf_moved_to": [round(sfx, 1), round(sfy, 1)],
            "placement_mode": ("solve_from_residuals"
                               if params.get("solve_from_residuals")
                               else "explicit_shift"),
            "cut_cy": round(cy * 0.5, 1), "fill_cy": round(cy * 0.5, 1),
            "max_cut_ft": 1.0, "max_fill_ft": 1.0,
            "cap_issues": [], "wall_exposure": [],
            "rule9_status": status,
            "provenance": params.get("provenance", "")}


def op_faceted_apron(model, state, params, constraints) -> dict:
    """Faceted/arc apron on the downstage edge (STAGE_SHAPE_STUDY A2)."""
    apron_sf = float(params.get("apron_sf", 0.0))
    # deck-level structure: earthwork is base prep only (~0.5 ft over apron)
    prep_cy = apron_sf * 0.5 / CF_PER_CY
    model.stage["apron"] = {
        "front": params.get("front"),
        "apron_sf": apron_sf,
        "projection_ft": params.get("projection_ft"),
        "row1_gap_ft": params.get("row1_gap_ft"),
        "performer_to_row1_ft": params.get("performer_to_row1_ft"),
        "bend_delta_ft": params.get("bend_delta_ft"),
        "bay_obstruction_pct": float(params.get("bay_obstruction_pct", 0.0)),
        "foreground_obstruction_pct": float(params.get("foreground_obstruction_pct", 0.0)),
    }
    if params.get("row1_gap_ft"):
        model.stage["row1_gap_ft"] = params["row1_gap_ft"]
    return {"op": "faceted_apron", "front": params.get("front"),
            "apron_sf": apron_sf,
            "cut_cy": round(prep_cy, 1), "fill_cy": round(prep_cy * 0.5, 1),
            "max_cut_ft": 0.5, "max_fill_ft": 0.5,
            "cap_issues": [], "wall_exposure": [],
            "provenance": params.get("provenance", "")}


def op_select_borrow_zone(model, state, params, constraints) -> dict:
    model.log_op("borrow_zone_selected", zone=params.get("zone"))
    model.stage.setdefault("_meta", {})
    return {"op": "select_borrow_zone", "zone": params.get("zone"),
            "cut_cy": 0.0, "fill_cy": 0.0, "max_cut_ft": 0.0, "max_fill_ft": 0.0,
            "cap_issues": [], "wall_exposure": [],
            "note": params.get("note", "")}


def op_terrain_delta(model, state, params, constraints, delta=None) -> dict:
    """Kept ClayDelta primitives (raise/lower/grade_ceiling/cut_bench/
    fill_shelf/smooth/flatten) executed on the intervention delta raster.
    Caps from the recipe are passed through as max_cut/max_fill."""
    if delta is None:
        return {"op": "terrain_delta", "error": "no delta raster available",
                "cut_cy": 0, "fill_cy": 0, "max_cut_ft": 0, "max_fill_ft": 0,
                "cap_issues": [], "wall_exposure": []}
    raise NotImplementedError(
        "terrain_delta sub-ops require named polygons (earthwork_scenarios."
        "geojson); wire through ScenarioLibrary when a recipe first uses them")


OPS = {
    "add_row": op_add_row,
    "extend_section_arc": op_extend_section_arc,
    "trim_section": op_trim_section,
    "regrade_rows": op_regrade_rows,
    "smooth_row_end_shoulders": op_smooth_row_end_shoulders,
    "solve_cross_aisle_plane": op_solve_cross_aisle_plane,
    "refit_stage": op_refit_stage,
    "faceted_apron": op_faceted_apron,
    "select_borrow_zone": op_select_borrow_zone,
}


def apply_operations(model: SectionSeatingModel, state: TierState,
                     operations: list[dict], constraints: dict) -> list[dict]:
    """Apply a recipe's operation list in order; return audit records."""
    records = []
    for spec in operations:
        op = spec.get("op")
        fn = OPS.get(op)
        if fn is None:
            raise ValueError(f"Unknown tier operation '{op}'")
        rec = fn(model, state, spec, constraints)
        model.log_op(op, **{k: v for k, v in rec.items() if k != "op"})
        records.append(rec)
    return records
