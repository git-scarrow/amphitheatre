"""EvaluatorSuite: run all evaluators and apply hard constraints."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .project import ProjectState
    from .clay import ClayDelta

from .earthwork import EarthworkEngine
from .sightlines import SightlineEngine
from .ada import ADAEngine
from .drainage import DrainageEngine
from .solar_eval import SolarEvaluator
from .aesthetic import AestheticEvaluator
from .terrain import TerrainEngine


class EvaluatorSuite:
    def __init__(self, state: "ProjectState"):
        self.state = state
        self.earthwork = EarthworkEngine(state)
        self.sightlines = SightlineEngine(state)
        self.ada = ADAEngine(state)
        self.drainage = DrainageEngine(state)
        self.solar = SolarEvaluator(state)
        self.aesthetic = AestheticEvaluator(state)
        self.terrain = TerrainEngine(state)

    def run_all(self, delta: "ClayDelta",
                bowl_axis_az: float | None = None,
                borrow_geom=None, fill_geom=None,
                zones: dict | None = None) -> dict:
        """Run all evaluators; return merged metrics dict."""
        if bowl_axis_az is None:
            bowl_axis_az = self.state.cfg["axes"]["face_az"]

        Zp = delta.proposed(self.state)

        # Earthwork
        ew = self.earthwork.full_report(delta, borrow_geom, fill_geom, zones)

        # Sightlines
        sl_rows = self.sightlines.compute_rows(Zp)
        sl = self.sightlines.summary(sl_rows)
        sl["delta_vs_baseline"] = self.sightlines.delta_vs_baseline(sl_rows)

        # ADA
        ada = self.ada.compute_routes(Zp)
        ada["delta"] = self.ada.delta_vs_baseline(Zp)

        # Drainage
        dr = self.drainage.compute(Zp)
        dr["delta"] = self.drainage.delta_vs_baseline(Zp)

        # Solar
        sun = self.solar.score_upper_crescent(Zp, bowl_axis_az)
        sun["glare_penalty_score"] = self.solar.glare_penalty_score(bowl_axis_az)
        sun["sunset_azimuths"] = self.solar.sunset_azimuths()

        # Aesthetic
        aes = self.aesthetic.compute(delta, ew)

        # Capacity — quality-banded (formal/soft/marginal/terrace) from sightline C-values
        p = self.state.params()
        fan_half = p["FAN_HALF"]
        seat_w_g = 1.83; aisle = 0.18
        import math

        cap_cfg = self.state.cfg.get("capacity_bands", {})
        C_FORMAL   = cap_cfg.get("formal_c_min_mm",   90)
        C_SOFT     = cap_cfg.get("soft_c_min_mm",     60)
        C_MARGINAL = cap_cfg.get("marginal_c_min_mm", 30)
        ALPHA      = cap_cfg.get("alpha_soft",         0.5)
        BETA       = cap_cfg.get("beta_marginal",      0.15)

        formal_seats = soft_seats = marginal_seats = terrace_seats = 0
        for r in sl_rows:
            seats_r = max(0, int(r["R"] * math.radians(2 * fan_half) * (1 - aisle) // seat_w_g))
            in_formal = r.get("in_formal_zone", True)
            if in_formal:
                # Formal zone: use harness-computed C (reflects proposed delta)
                c_raw = r.get("C_value_mm")
                c_mm = float(c_raw) if c_raw is not None else None
            else:
                # Terrace zone: use composition_table C (accounts for cross-angle
                # effects the arc-median model cannot capture in the outer rows)
                comp = r.get("composition_c_mm")
                c_mm = float(comp) if comp is not None else r.get("C_value_mm")
                c_mm = float(c_mm) if c_mm is not None else None

            if c_mm is None or c_mm >= C_FORMAL:
                formal_seats += seats_r
            elif c_mm >= C_SOFT:
                soft_seats += seats_r
            elif c_mm >= C_MARGINAL:
                marginal_seats += seats_r
            else:
                terrace_seats += seats_r   # rim / lawn zone

        c_formal = formal_seats + ALPHA * soft_seats + BETA * marginal_seats
        baseline_cap = self.state.ctx.get("cap", {})

        return {
            "earthwork": ew,
            "sightlines": sl,
            "sightline_rows": sl_rows,
            "ada": ada,
            "drainage": dr,
            "solar": sun,
            "aesthetic": aes,
            "capacity": {
                "formal_seats":    formal_seats,
                "soft_seats":      soft_seats,
                "marginal_seats":  marginal_seats,
                "terrace_seats":   terrace_seats,
                "c_formal":        round(c_formal, 1),
                "baseline_c_formal": baseline_cap.get("c_formal", 1545),
                # legacy fields kept for report compatibility
                "compact":  formal_seats + soft_seats + marginal_seats,
                "generous": formal_seats + soft_seats,
                "baseline_compact": baseline_cap.get("compact", 1797),
                "baseline_generous": baseline_cap.get("generous", 1472),
                "delta_compact":  (formal_seats + soft_seats + marginal_seats)
                                  - baseline_cap.get("compact", 1797),
                "delta_generous": (formal_seats + soft_seats)
                                  - baseline_cap.get("generous", 1472),
            },
            "bowl_axis_az": bowl_axis_az,
        }

    def hard_constraints(self, metrics: dict) -> dict:
        """Return {valid: bool, failures: list[str]}.
        A single hard-constraint failure archives the variant as invalid.
        """
        failures = []

        # 1. All sightlines must pass
        sl = metrics.get("sightlines", {})
        if not sl.get("all_pass", True):
            n_fail = sl.get("fail_count", 0)
            failures.append(f"sightlines: {n_fail} row(s) fail 90 mm C-value")

        # 2. Drainage: treatment cell function must be preserved
        dr = metrics.get("drainage", {})
        if not dr.get("cell_function_preserved", True):
            chg = dr.get("storage_100yr_change_pct", 0)
            failures.append(
                f"drainage: treatment cell storage reduced by {abs(chg):.1f}% "
                f"or floor freeboard < 1 ft (freeboard={dr.get('event_floor_freeboard_ft', 0):.2f} ft)"
            )

        # 3. No retaining wall trigger
        ew = metrics.get("earthwork", {})
        if ew.get("wall_trigger", False):
            failures.append(
                f"retaining_wall: wall trigger tripped "
                f"(max_cut={ew.get('max_cut_ft', 0):.1f} ft, "
                f"max_fill={ew.get('max_fill_ft', 0):.1f} ft, "
                f"max_slope={ew.get('max_slope_pct', 0):.0f}%)"
            )

        # 4. Net earthwork balance under neutral yield
        yb = ew.get("yield_balance", {}).get("neutral", {})
        if not yb.get("balanced", True):
            shortfall = yb.get("shortfall_cy", 0)
            failures.append(
                f"earthwork_balance: neutral yield case fails by {shortfall:.0f} CY shortfall"
            )

        # 5. ADA must not be worsened
        ada = metrics.get("ada", {})
        if ada.get("delta") == "worsened":
            failures.append("ADA: accessible routes worsened vs baseline")

        # 6. Bay view must not be blocked
        aes = metrics.get("aesthetic", {})
        bv = aes.get("bay_view_score", 1.0)
        if bv < 0.3:
            failures.append(f"bay_view: score {bv:.2f} < 0.30 — upstage view blocked")

        return {"valid": len(failures) == 0, "failures": failures}

    def no_touch_violations(self, delta: "ClayDelta") -> list[str]:
        """Check if delta modifies any no-touch zones."""
        violations = []
        d = delta.delta()
        tol = self.state.cfg["earthwork"]["lod_tolerance_ft"]

        # Treatment cell core
        g = self.state.stage_feature("treatment_wet_cell")
        if g is not None:
            mask = self.state.rasterize_geom(g)
            if np.abs(d[mask]).max() > tol:
                violations.append("treatment_cell_core modified")

        # Seating rows on natural grade
        fan_mask = self.state.fan_mask()
        p = self.state.params()
        # Only flag if fill > REGRADE threshold (1.5 ft) across >20% of seats
        big_fill = fan_mask & (d > 1.5)
        if big_fill.sum() > fan_mask.sum() * 0.2:
            violations.append("seating_rake: substantial fill (>1.5 ft) over >20% of fan")

        return violations
