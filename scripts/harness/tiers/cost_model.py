"""Planning cost model: ranges only, never false precision.

Cost = earthwork (cut/fill/topsoil CY) + surface work (fine grading, aisle,
apron) + structures (walls if triggered, stage refit if performed), with
mobilization and planning contingency factors applied as ranges.

Outputs per scenario: total range, incremental-over-baseline range, and three
cost-effectiveness ratios (per Band-A seat, per quality-adjusted seat, per
score point over Scenario E) — each reported as a range.
"""
from __future__ import annotations

from pathlib import Path

import yaml


class CostModel:
    def __init__(self, assumptions_path: str | Path):
        raw = yaml.safe_load(open(assumptions_path))
        ca = raw.get("cost_assumptions", raw)
        self.unit = ca["unit_costs"]
        self.factors = ca["factors"]
        self.meta = {k: ca.get(k) for k in ("currency", "basis_year", "confidence")}
        self.path = str(assumptions_path)

    def _u(self, key: str, qty: float) -> tuple[float, float]:
        u = self.unit[key]
        return qty * u["low"], qty * u["high"]

    def _mid(self, key: str) -> float:
        u = self.unit[key]
        return (u["low"] + u["high"]) / 2.0

    def op_cost_midpoint(self, rec: dict) -> float:
        """Direct midpoint cost of one operation record — earthwork +
        op-specific structures. EXCLUDES fine grading / lawn / mobilization /
        contingency, which the scenario cost model applies at scenario level.
        For comparing operations against each other, not for totals."""
        c = (rec.get("cut_cy", 0) * self._mid("cut_per_cy")
             + rec.get("fill_cy", 0) * self._mid("fill_per_cy")
             + rec.get("topsoil_cy", 0) * self._mid("topsoil_per_cy"))
        if rec.get("op") == "faceted_apron":
            c += rec.get("apron_sf", 0) * self._mid("apron_structure_per_sf")
        if rec.get("op") == "refit_stage":
            c += self._mid("stage_refit_lump")
        for w in rec.get("wall_exposure", []):
            c += w.get("est_wall_length_ft", 0) * self._mid("low_wall_per_lf")
        return round(c, 0)

    def scenario_cost(self, metrics: dict) -> dict:
        ew = metrics["earthwork"]
        lines = {}

        def add(name, lo, hi, qty, unit):
            if qty <= 0:
                return
            lines[name] = {"qty": round(qty, 1), "unit": unit,
                           "low": round(lo, 0), "high": round(hi, 0)}

        cut = ew["total_cut_cy"]; fill = ew["total_fill_cy"]
        topsoil = ew["baseline_topsoil_cy"] + ew["incremental_topsoil_cy"]
        add("cut", *self._u("cut_per_cy", cut), cut, "CY")
        add("fill", *self._u("fill_per_cy", fill), fill, "CY")
        add("topsoil", *self._u("topsoil_per_cy", topsoil), topsoil, "CY")

        # fine grading over the disturbed seating surface
        grade_sf = metrics["disturbed_area"]["total_sqft"] * 0.5  # ~half is tread surface
        add("fine_grading", *self._u("fine_grading_per_sf", grade_sf), grade_sf, "SF")
        lawn_sf = metrics["disturbed_area"]["total_sqft"] * 0.5
        add("lawn_restore", *self._u("lawn_restore_per_sf", lawn_sf), lawn_sf, "SF")

        # ADA ramps (baseline scope, identical across tiers) — rough plan areas
        ramp_sf = 2 * 6.0 * 120.0   # two switchbacks, 6 ft wide, ~120 ft runs
        add("ada_ramps", *self._u("ada_ramp_per_sf", ramp_sf), ramp_sf, "SF")
        aisle_sf = 8.0 * 250.0      # rows-9/10 causeway
        add("cross_aisle", *self._u("cross_aisle_per_sf", aisle_sf), aisle_sf, "SF")

        apron = (metrics["stage"].get("apron") or {})
        apron_sf = float(apron.get("apron_sf") or 0.0)
        add("apron_structure", *self._u("apron_structure_per_sf", apron_sf),
            apron_sf, "SF")

        if metrics["stage"].get("stage_earthwork_cy", 0) > 0:
            u = self.unit["stage_refit_lump"]
            lines["stage_refit"] = {"qty": 1, "unit": "LS",
                                    "low": u["low"], "high": u["high"]}

        wall_lf = metrics["walls"].get("est_total_wall_length_ft", 0.0)
        add("low_walls", *self._u("low_wall_per_lf", wall_lf), wall_lf, "LF")

        sub_lo = sum(v["low"] for v in lines.values())
        sub_hi = sum(v["high"] for v in lines.values())
        mob = self.factors["mobilization_pct"]
        cont = self.factors["planning_contingency_pct"]
        tot_lo = sub_lo * (1 + mob["low"] / 100) * (1 + cont["low"] / 100)
        tot_hi = sub_hi * (1 + mob["high"] / 100) * (1 + cont["high"] / 100)

        def rng(lo, hi):
            return {"low": int(round(lo, -2)), "high": int(round(hi, -2))}

        return {
            "assumptions": self.path,
            "confidence": self.meta.get("confidence"),
            "lines": lines,
            "subtotal": rng(sub_lo, sub_hi),
            "total_range": rng(tot_lo, tot_hi),
            "note": "planning ranges only — comparison-grade, not a bid basis",
        }

    @staticmethod
    def effectiveness(cost: dict, metrics: dict,
                      baseline_cost: dict, baseline_metrics: dict) -> dict:
        """Incremental cost-effectiveness vs the Scenario E baseline (ranges)."""
        d_lo = cost["total_range"]["low"] - baseline_cost["total_range"]["low"]
        d_hi = cost["total_range"]["high"] - baseline_cost["total_range"]["high"]
        d_seats = (metrics["capacity"]["formal_band_a_seats"]
                   - baseline_metrics["capacity"]["formal_band_a_seats"])
        d_qa = (metrics["capacity"]["quality_adjusted_seats"]
                - baseline_metrics["capacity"]["quality_adjusted_seats"])
        d_score = (metrics["score"]["total"]
                   - baseline_metrics["score"]["total"])

        def ratio(dlo, dhi, denom):
            if denom is None or abs(denom) < 1e-9:
                return None
            lo, hi = sorted((dlo / denom, dhi / denom))
            return {"low": round(lo, 0), "high": round(hi, 0)}

        return {
            "incremental_cost_range": {"low": int(d_lo), "high": int(d_hi)},
            "delta_band_a_seats": d_seats,
            "delta_quality_adjusted_seats": round(d_qa, 1),
            "delta_score": round(d_score, 1),
            "cost_per_band_a_seat": ratio(d_lo, d_hi, d_seats),
            "cost_per_quality_adjusted_seat": ratio(d_lo, d_hi, d_qa),
            "cost_per_score_point": ratio(d_lo, d_hi, d_score),
        }
