"""TierEvaluator: ONE evaluator for every intervention-tier scenario.

Every scenario — including Scenario_E_baseline — is measured by this class
with identical code paths, and the evaluator fingerprints itself (SHA-256 of
the tiers package sources) into every result so the same-evaluator gate can
prove it. Differences between scenarios come ONLY from the recipe operations.

Earthwork convention (uniform across tiers):
  total = locked Scenario E components (earthwork.csv, identical in every
          scenario) + incremental operation CY computed by operations.py.

C-value model (uniform): per-section radial solver, D = axis_radius − 50 ft,
eye 3.94 ft, focus 612.5 — the same model that produced the composition-table
C_mm (cross-checked in the output). Planning grade.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
from shapely.geometry import shape

from .geometry_model import (SectionSeatingModel, TierState, SECTIONS,
                             C_TARGET_MM)

EVALUATOR_VERSION = "tiers-1.0"


def evaluator_fingerprint() -> str:
    h = hashlib.sha256()
    pkg = Path(__file__).parent
    for name in ("geometry_model.py", "operations.py", "evaluator.py"):
        h.update((pkg / name).read_bytes())
    return h.hexdigest()[:16]


class TierEvaluator:
    def __init__(self, state: TierState):
        self.state = state
        cb = state.cfg.get("capacity_bands", {})
        self.c_formal = cb.get("formal_c_min_mm", 90)
        self.c_soft = cb.get("soft_c_min_mm", 60)
        self.c_marginal = cb.get("marginal_c_min_mm", 30)
        self.alpha = cb.get("alpha_soft", 0.5)
        self.beta = cb.get("beta_marginal", 0.15)
        self.fingerprint = evaluator_fingerprint()

    # ── capacity & sightlines ──────────────────────────────────────────────

    def capacity(self, model: SectionSeatingModel) -> dict:
        c_vals = model.compute_c_values()
        bands = {"formal": 0, "soft": 0, "marginal": 0, "sub_marginal": 0}
        per_section = {s: dict(bands) for s in SECTIONS}
        terrace_seats = 0
        c_dist, c_weights = [], []
        baseline_fail, promoted_below = [], []
        for b in model.bands.values():
            if b.status == "terrace":
                terrace_seats += b.seats
                continue
            if b.status != "formal" or b.seats <= 0:
                continue
            c = c_vals.get((b.section, b.row))
            if c is not None:
                c_dist.append(c)
                c_weights.append(b.seats)
            if c is None or c >= self.c_formal:
                k = "formal"
            elif c >= self.c_soft:
                k = "soft"
            elif c >= self.c_marginal:
                k = "marginal"
            else:
                k = "sub_marginal"
            if k != "formal":
                entry = {"band": f"{b.section} r{b.row}", "c_mm": c, "seats": b.seats}
                # A baseline-validated formal row dropping below 90 mm is a
                # REGRESSION (hard check); a newly promoted row landing soft
                # is a quality finding already carried by the banding.
                (promoted_below if b.added_by_op else baseline_fail).append(entry)
            bands[k] += b.seats
            per_section[b.section][k] += b.seats

        qa = bands["formal"] + self.alpha * bands["soft"] + self.beta * bands["marginal"]
        c_arr = np.array(c_dist, float)
        w_arr = np.array(c_weights, float)

        def wq(q):
            if not len(c_arr):
                return None
            idx = np.argsort(c_arr)
            cw = np.cumsum(w_arr[idx]) / w_arr.sum()
            return round(float(c_arr[idx][np.searchsorted(cw, q)]), 0)

        # cross-check vs composition table (baseline only meaningful)
        diffs = [abs(c_vals[(b.section, b.row)] - b.comp_c_mm)
                 for b in model.bands.values()
                 if b.comp_c_mm is not None
                 and c_vals.get((b.section, b.row)) is not None]
        return {
            "seats_by_band": bands,
            "per_section": per_section,
            "terrace_informal_seats": terrace_seats,
            "quality_adjusted_seats": round(qa, 1),
            "formal_band_a_seats": bands["formal"],
            "sightline_distribution_mm": {
                "min": round(float(c_arr.min()), 0) if len(c_arr) else None,
                "p25": wq(0.25), "median": wq(0.5), "p75": wq(0.75),
                "max": round(float(c_arr.max()), 0) if len(c_arr) else None,
            },
            "baseline_formal_rows_below_90mm": baseline_fail,
            "promoted_rows_below_90mm": promoted_below,
            "sightlines_formal_ok": len(baseline_fail) == 0,
            # fully_formal: EVERY formal-status band (baseline AND promoted)
            # meets 90 mm. A scenario can pass the regression check yet not
            # be fully formal — the report flags it.
            "fully_formal": len(baseline_fail) == 0 and len(promoted_below) == 0,
            "c_model": "per-section radial solver (stage_r 50, eye 3.94, focus 612.5)",
            "c_model_vs_composition_mean_abs_mm": round(float(np.mean(diffs)), 1) if diffs else None,
        }

    # ── stage ──────────────────────────────────────────────────────────────

    def stage_metrics(self, model: SectionSeatingModel) -> dict:
        align = model.stage_alignment()
        st = model.stage
        return {
            **align,
            # Frame naming: both this evaluator and the studies measure the
            # SAME quantity (stage axis vs seat-weighted audience-centroid
            # bearing). Signs differ: evaluator/STAGE_REFIT_SWEEP use
            # positive = stage axis clockwise of audience bearing;
            # STAGE_SHAPE_STUDY reports the same value negated. Lateral has
            # the same sign everywhere (negative = audience left of axis).
            "mismatch_centroid_frame_deg": align.get("axis_mismatch_deg"),
            "lateral_offset_centroid_frame_ft": align.get("lateral_offset_ft"),
            "frame_note": "computed = centroid frame, sweep sign; "
                          "declared = STAGE_SHAPE_STUDY residuals, study sign "
                          "(= -computed)",
            "declared_axis_mismatch_deg": st.get("declared_axis_mismatch_deg"),
            "declared_lateral_offset_ft": st.get("declared_lateral_offset_ft"),
            "declared_frame": st.get("declared_frame"),
            "row1_gap_ft": st.get("row1_gap_ft"),
            "row1_gap_min_ft": round(min(st.get("row1_gap_ft", {"x": 0}).values()), 1),
            "cell_gap_ft": st.get("cell_gap_ft"),
            "apron": st.get("apron"),
            "stage_earthwork_cy": st.get("earthwork_delta_cy", 0.0),
            "provenance": st.get("provenance", ""),
        }

    def performer_distances(self, model: SectionSeatingModel) -> dict:
        sfx, sfy = model.stage["sf_x"], model.stage["sf_y"]
        d, w = [], []
        for b in model.seated_bands():
            pos = model.band_position(b)
            if pos is None:
                continue
            d.append(math.hypot(pos[0] - sfx, pos[1] - sfy))
            w.append(b.seats)
        if not d:
            return {}
        d_arr, w_arr = np.array(d), np.array(w, float)
        idx = np.argsort(d_arr)
        cw = np.cumsum(w_arr[idx]) / w_arr.sum()

        def q(p):
            return round(float(d_arr[idx][np.searchsorted(cw, p)]), 1)

        frac_within = lambda r: round(float(w_arr[d_arr <= r].sum() / w_arr.sum()), 3)
        return {
            "min_ft": round(float(d_arr.min()), 1),
            "p25_ft": q(0.25), "median_ft": q(0.5), "p90_ft": q(0.9),
            "max_ft": round(float(d_arr.max()), 1),
            "seat_frac_within_100ft": frac_within(100),
            "seat_frac_within_150ft": frac_within(150),
            "seat_frac_within_200ft": frac_within(200),
        }

    def acoustic_proxy(self, perf: dict) -> dict:
        """Distance-banded speech-intelligibility proxy (declared formula):
        score = 1.0·f(≤100ft) + 0.7·f(100-150) + 0.4·f(150-200) + 0.2·f(>200)
        Unamplified-speech bands; planning proxy only."""
        if not perf:
            return {"score": None}
        f100 = perf["seat_frac_within_100ft"]
        f150 = perf["seat_frac_within_150ft"] - f100
        f200 = perf["seat_frac_within_200ft"] - f100 - f150
        fout = 1.0 - perf["seat_frac_within_200ft"]
        score = 1.0 * f100 + 0.7 * f150 + 0.4 * f200 + 0.2 * fout
        return {"score": round(score, 3),
                "formula": "1.0*(<=100ft)+0.7*(100-150)+0.4*(150-200)+0.2*(>200), seat-weighted"}

    # ── access ─────────────────────────────────────────────────────────────

    def ada_metrics(self, model: SectionSeatingModel) -> dict:
        routes = []
        for f in model.features.get("ada_ramp", []):
            p = f["properties"]
            routes.append({
                "name": p.get("name", "ramp"),
                "running_slope_pct": p.get("running_slope_pct"),
                "running_ok": bool(p.get("running_ok", False)),
                "landings": p.get("landings"),
            })
        ca = model.cross_aisle
        cross_ok = (ca.get("cross_slope_pct", 99) <= 2.0
                    and ca.get("wheelable", False))
        all_ok = all(r["running_ok"] for r in routes) and cross_ok
        return {
            "routes": routes,
            "routes_assessed": len(routes),
            "all_running_ok": all(r["running_ok"] for r in routes),
            "cross_aisle": ca,
            "cross_aisle_ok": cross_ok,
            "ada_ok": all_ok,
            "note": "designed switchback surfaces (Scenario E validated); "
                    "cross-slope remains survey-gated",
        }

    # ── earthwork ──────────────────────────────────────────────────────────

    def earthwork(self, model: SectionSeatingModel, op_records: list[dict]) -> dict:
        base = model.baseline_earthwork.get("TOTAL",
                                            {"cut_cy": 0, "fill_cy": 0,
                                             "gross_cy": 0, "topsoil_cy": 0})
        inc_cut = sum(r.get("cut_cy", 0) for r in op_records)
        inc_fill = sum(r.get("fill_cy", 0) for r in op_records)
        inc_topsoil = sum(r.get("topsoil_cy", 0) for r in op_records)
        max_cut = max([r.get("max_cut_ft", 0) for r in op_records], default=0.0)
        max_fill = max([r.get("max_fill_ft", 0) for r in op_records], default=0.0)
        # baseline max fill on any restored tread: 2.83 ft (SCENARIO_E_CIVIC.md)
        return {
            "baseline_components": model.baseline_earthwork,
            "baseline_cut_cy": base["cut_cy"],
            "baseline_fill_cy": base["fill_cy"],
            "baseline_gross_cy": base["gross_cy"],
            "baseline_topsoil_cy": base["topsoil_cy"],
            "incremental_cut_cy": round(inc_cut, 1),
            "incremental_fill_cy": round(inc_fill, 1),
            "incremental_gross_cy": round(inc_cut + inc_fill, 1),
            "incremental_topsoil_cy": round(inc_topsoil, 1),
            "total_cut_cy": round(base["cut_cy"] + inc_cut, 1),
            "total_fill_cy": round(base["fill_cy"] + inc_fill, 1),
            "total_gross_cy": round(base["gross_cy"] + inc_cut + inc_fill, 1),
            "total_net_cy": round((base["fill_cy"] + inc_fill)
                                  - (base["cut_cy"] + inc_cut), 1),
            "max_incremental_cut_ft": round(max_cut, 2),
            "max_incremental_fill_ft": round(max_fill, 2),
            "max_overall_fill_ft": round(max(max_fill, 2.83), 2),
            "max_overall_cut_ft": round(max_cut, 2),
            "baseline_max_tread_fill_ft": 2.83,
        }

    def disturbed_area(self, model: SectionSeatingModel,
                       op_records: list[dict]) -> dict:
        env = model.features.get("construction_envelope", [])
        base_sqft = sum(shape(f["geometry"]).area for f in env)
        new_sqft = 0.0
        for b in model.bands.values():
            if b.added_by_op:
                g = model.band_footprint(b)
                if g is not None:
                    new_sqft += g.area
        apron = (model.stage.get("apron") or {}).get("apron_sf", 0.0)
        total = base_sqft + new_sqft + apron
        return {
            "baseline_envelope_sqft": round(base_sqft, 0),
            "new_disturbance_sqft": round(new_sqft + apron, 0),
            "total_sqft": round(total, 0),
            "total_ac": round(total / 43560.0, 3),
        }

    # ── drainage / obstruction ─────────────────────────────────────────────

    def drainage(self, model: SectionSeatingModel) -> dict:
        tc = self.state.cfg["treatment_cell"]
        cell = self.state.stage_feature("treatment_wet_cell")
        swales = [shape(f["geometry"]) for f in model.features.get("drainage_swale", [])]
        conflicts = []
        for b in model.bands.values():
            if not b.added_by_op:
                continue
            g = model.band_footprint(b)
            if g is None:
                continue
            if cell is not None and g.intersects(cell):
                conflicts.append(f"{b.section} r{b.row} intersects treatment cell")
            for i, sw in enumerate(swales):
                if g.intersects(sw):
                    conflicts.append(f"{b.section} r{b.row} intersects swale {i}")
        freeboard = round(tc["event_floor_min_navd88"] - tc["wsel_100yr"], 2)
        ok = len(conflicts) == 0 and freeboard >= 1.0
        return {
            "cell_present": cell is not None,
            "event_floor_freeboard_ft": freeboard,
            "freeboard_ok": freeboard >= 1.0,
            "swales": len(swales),
            "swales_fall_to_pour_point": True,   # Scenario E validated; ops do not regrade swales
            "conflicts": conflicts,
            "drainage_ok": ok,
        }

    def obstruction(self, model: SectionSeatingModel) -> dict:
        st = model.stage
        bay = float(st.get("bay_obstruction_pct", 0.0))
        cell = float(st.get("cell_obstruction_pct", 0.0))
        fg = float(st.get("foreground_obstruction_pct", 0.0))
        apron = st.get("apron") or {}
        bay = max(bay, float(apron.get("bay_obstruction_pct", 0.0)))
        fg = max(fg, float(apron.get("foreground_obstruction_pct", 0.0)))
        grade = "none" if bay <= 2.0 else ("minor" if bay <= 10.0 else "flagged")
        return {
            "bay_obstruction_pct": bay,
            "cell_obstruction_pct": cell,
            "foreground_sky_obstruction_pct": fg,
            "grade": grade,
            "bay_view_ok": bay <= 10.0,
            "rule": "stage judged by incremental obstruction vs NW rim "
                    "silhouette, never height (visual-envelope rule); "
                    "<=2% none / <=10% minor / above flagged",
        }

    # ── operations & walls ─────────────────────────────────────────────────

    def operations_score(self, model: SectionSeatingModel,
                         ada: dict, ew: dict, op_records: list[dict]) -> dict:
        checks = {
            "cross_aisle_wheelable": bool(model.cross_aisle.get("wheelable")),
            "two_ada_routes_pass": ada.get("all_running_ok", False)
                                   and ada.get("routes_assessed", 0) >= 2,
            "promenade_present": any(b.status == "promenade"
                                     for b in model.bands.values()),
            "shoulders_treated": any(r.get("op") == "smooth_row_end_shoulders"
                                     for r in op_records)
                                 or bool(model.features.get("row_end_shoulder")),
            "row1_gaps_gte_12ft": min(model.stage.get(
                "row1_gap_ft", {"x": 0.0}).values()) >= 12.0,
            "borrow_declared_if_needed": (
                ew["incremental_gross_cy"] < 50.0
                or any(r.get("op") == "select_borrow_zone" for r in op_records)),
        }
        return {"checks": checks,
                "score": round(sum(checks.values()) / len(checks), 2)}

    def wall_triggers(self, op_records: list[dict], constraints: dict) -> dict:
        walls = [w for r in op_records for w in r.get("wall_exposure", [])]
        cap_issues = [c for r in op_records for c in r.get("cap_issues", [])]
        return {
            "wall_trigger": len(walls) > 0,
            "wall_count": len(walls),
            "walls": walls,
            "est_total_wall_length_ft": round(sum(w["est_wall_length_ft"]
                                                  for w in walls), 0),
            "cap_violations": cap_issues,
            "thresholds": {
                "cut_ft": constraints.get("wall_trigger_cut_ft", 3.0),
                "fill_ft": constraints.get("wall_trigger_fill_ft", 3.0),
            },
            "doctrine": "walls are an emergent OUTPUT of depth, never an input zone",
        }

    # ── composite ──────────────────────────────────────────────────────────

    def score(self, m: dict, weights: dict, baseline_qa: float | None) -> dict:
        cap = m["capacity"]
        qa = cap["quality_adjusted_seats"]
        comp = {}
        comp["capacity"] = min(1.5, qa / baseline_qa) if baseline_qa else 1.0
        total_seated = max(1, sum(cap["seats_by_band"].values()))
        comp["sightlines"] = cap["seats_by_band"]["formal"] / total_seated
        comp["section_balance"] = m["section_balance"]["balance_ratio_seats"]
        sm = m["stage"]
        mis = abs(sm.get("axis_mismatch_deg") or 0.0)
        lat = abs(sm.get("lateral_offset_ft") or 0.0)
        comp["stage_fit"] = round((max(0.0, 1 - mis / 30.0)
                                   + max(0.0, 1 - lat / 30.0)) / 2, 3)
        comp["ada"] = 1.0 if m["ada"]["ada_ok"] else 0.0
        comp["drainage"] = 1.0 if m["drainage"]["drainage_ok"] else 0.2
        comp["bay_view"] = {"none": 1.0, "minor": 0.7,
                            "flagged": 0.3}[m["obstruction"]["grade"]]
        comp["acoustic"] = m["acoustic"]["score"] or 0.0
        comp["operations"] = m["operations"]["score"]
        comp["earthwork_economy"] = max(
            0.0, 1.0 - m["earthwork"]["incremental_gross_cy"] / 2000.0)
        comp["wall_avoidance"] = 0.0 if m["walls"]["wall_trigger"] else 1.0

        w_total = sum(weights.values())
        total = sum(comp[k] * weights[k] for k in comp) / w_total * 100.0
        return {"total": round(total, 1),
                "components": {k: round(v, 3) for k, v in comp.items()},
                "weights": weights}

    # ── validation status ──────────────────────────────────────────────────

    @staticmethod
    def validation_status(recipe, op_records: list[dict]) -> dict:
        """validated | analysis-tier | reference-only, with reasons."""
        if recipe.tier_class == "idealized":
            return {"status": "reference-only",
                    "reasons": ["dominated reference case — not a live design "
                                "path; exists to anchor the top of the Pareto "
                                "chart"]}
        if not op_records:
            return {"status": "validated",
                    "reasons": ["Scenario E as accepted (seating/ADA/drainage "
                                "canon-ACCEPTED); stage Rule 9 open"]}
        reasons = []
        ops = {r.get("op") for r in op_records}
        if "add_row" in ops or "extend_section_arc" in ops:
            reasons.append("N1/N2 seat additions require re-emission + "
                           "Scenario E re-validation (canon Rules 3/5)")
        if "refit_stage" in ops or "faceted_apron" in ops:
            reasons.append("P_opt / apron are tested candidates only — "
                           "Rule 9 remains OPEN")
        if "regrade_rows" in ops:
            reasons.append("regraded treads need re-emission on the real "
                           "surface before seats are claimed")
        return {"status": "analysis-tier",
                "reasons": reasons or ["operations not yet re-validated"]}

    # ── entry point ────────────────────────────────────────────────────────

    def evaluate(self, model: SectionSeatingModel, recipe,
                 op_records: list[dict],
                 baseline_qa: float | None = None) -> dict:
        cap = self.capacity(model)
        stage = self.stage_metrics(model)
        perf = self.performer_distances(model)
        acoustic = self.acoustic_proxy(perf)
        ada = self.ada_metrics(model)
        ew = self.earthwork(model, op_records)
        dist = self.disturbed_area(model, op_records)
        dr = self.drainage(model)
        obs = self.obstruction(model)
        walls = self.wall_triggers(op_records, recipe.constraints)
        ops = self.operations_score(model, ada, ew, op_records)

        m = {
            "scenario": recipe.name,
            "tier_class": recipe.tier_class,
            "intent": recipe.intent.strip(),
            "validation_status": self.validation_status(recipe, op_records),
            "evaluator": {"version": EVALUATOR_VERSION,
                          "fingerprint": self.fingerprint},
            "geometry_provenance": model.sources,
            "capacity": cap,
            "section_balance": model.section_stats(),
            "stage": stage,
            "performer_to_seat_ft": perf,
            "acoustic": acoustic,
            "ada": ada,
            "earthwork": ew,
            "disturbed_area": dist,
            "drainage": dr,
            "obstruction": obs,
            "operations": ops,
            "walls": walls,
            "op_records": op_records,
            "hard_checks": {
                "sightlines_formal_ok": cap["sightlines_formal_ok"],
                "ada_ok": ada["ada_ok"],
                "drainage_ok": dr["drainage_ok"],
                "bay_view_ok": obs["bay_view_ok"],
                "no_wall_trigger": not walls["wall_trigger"],
            },
        }
        m["score"] = self.score(m, recipe.scoring_weights, baseline_qa)
        return m
