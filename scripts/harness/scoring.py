"""MultiObjectiveScorer: weighted sum over all evaluators.

Weights from spec. Score is 0–100 range (approx). Used for ranking, not as
a definitive judgment — the hard-constraint check is the gate.
"""
from __future__ import annotations


WEIGHTS = {
    "sightlines": 1.5,
    "ada": 1.5,
    "drainage": 1.5,
    "earthwork": 1.5,
    "retaining_wall_avoidance": 1.5,
    "landform_fit": 1.5,
    "bay_view": 1.5,
    "upper_sunset": 1.2,
    "glare_avoidance": 1.2,
    "capacity": 1.0,      # C_formal (quality-banded)
    "terrace": 0.5,       # L_terrace (upper contours as landscape)
    "stage_presence": 1.0,
    "symmetry_penalty": 0.3,
}

PENALTIES = {
    "cut_fill_cy": 0.1,        # per 1000 CY gross
    "haul_effort": 0.1,        # per 100k CY-ft
    "retaining_wall": 2.0,
    "drainage_loss": 0.5,      # per 10% storage loss
    "canopy_conflict": 0.3,
    "overbuild": 0.5,
}


class MultiObjectiveScorer:
    def __init__(self, custom_weights: dict | None = None,
                 custom_penalties: dict | None = None):
        self.weights = {**WEIGHTS, **(custom_weights or {})}
        self.penalties = {**PENALTIES, **(custom_penalties or {})}

    def score(self, metrics: dict) -> dict:
        breakdown = {}
        total = 0.0
        w_total = sum(self.weights.values())

        sl = metrics.get("sightlines", {})
        ada = metrics.get("ada", {})
        dr = metrics.get("drainage", {})
        ew = metrics.get("earthwork", {})
        sun = metrics.get("solar", {})
        aes = metrics.get("aesthetic", {})
        cap = metrics.get("capacity", {})

        def add(key, raw_score, weight):
            s = raw_score * weight
            breakdown[key] = {"raw": round(raw_score, 3), "weighted": round(s, 3)}
            return s

        # Sightlines: 1 if all pass, else fraction passing
        pass_frac = (sl.get("pass_count", 0) /
                     max(1, sl.get("pass_count", 0) + sl.get("fail_count", 0)))
        total += add("sightlines", pass_frac, self.weights["sightlines"])

        # ADA: 1=improved, 0.7=unchanged, 0=worsened
        ada_score = {"improved": 1.0, "unchanged": 0.7, "worsened": 0.0}.get(
            ada.get("delta", "unchanged"), 0.7
        )
        total += add("ada", ada_score, self.weights["ada"])

        # Drainage: function_preserved = 1.0; partial loss = partial score
        dr_ok = 1.0 if dr.get("cell_function_preserved", True) else 0.2
        total += add("drainage", dr_ok, self.weights["drainage"])

        # Earthwork: favour low gross CY (normalised to ~1000 CY = good, 5000 = bad)
        gross = ew.get("gross_cy", 0.0)
        ew_score = max(0.0, 1.0 - gross / 2000.0)
        total += add("earthwork", ew_score, self.weights["earthwork"])

        # Retaining wall avoidance
        wall_score = 0.0 if ew.get("wall_trigger", False) else 1.0
        total += add("retaining_wall_avoidance", wall_score, self.weights["retaining_wall_avoidance"])

        # Landform fit
        lf = aes.get("landform_fit", 0.5)
        total += add("landform_fit", lf, self.weights["landform_fit"])

        # Bay view
        bv = aes.get("bay_view_score", 0.5)
        total += add("bay_view", bv, self.weights["bay_view"])

        # Upper sunset score
        us = sun.get("upper_crescent_score", 0.0)
        total += add("upper_sunset", us, self.weights["upper_sunset"])

        # Glare avoidance: 1=low glare, 0=high glare
        glare_map = {"low": 1.0, "medium": 0.5, "high": 0.0}
        ga = glare_map.get(sun.get("glare_penalty", "low"), 1.0)
        total += add("glare_avoidance", ga, self.weights["glare_avoidance"])

        # Capacity — quality-banded C_formal relative to baseline
        base_cf = cap.get("baseline_c_formal", 1545)
        curr_cf = cap.get("c_formal", cap.get("compact", base_cf))
        cap_score = min(1.0, curr_cf / max(base_cf, 1))
        total += add("capacity", cap_score, self.weights["capacity"])

        # Terrace / lawn value: upper-contour seats beyond the formal bowl
        # (marginal + rim rows converted to landscape terraces)
        terrace = cap.get("terrace_seats", 0)
        terrace_score = min(1.0, terrace / 300.0)
        total += add("terrace", terrace_score, self.weights.get("terrace", 0.5))

        # Stage presence
        sp = aes.get("stage_presence", 0.6)
        total += add("stage_presence", sp, self.weights["stage_presence"])

        # Symmetry penalty (low weight — landscape wants asymmetry)
        # Give full score if not symmetric (no penalty)
        total += add("symmetry_penalty", 1.0, self.weights["symmetry_penalty"])

        # Normalise to 0–100
        normalised = (total / w_total) * 100.0

        # Hard penalties applied after normalisation
        pen_total = 0.0
        pen_breakdown = {}

        gross = ew.get("gross_cy", 0)
        p = gross / 1000.0 * self.penalties["cut_fill_cy"]
        pen_total += p; pen_breakdown["cut_fill"] = round(p, 2)

        haul = ew.get("haul_effort_cy_ft", 0)
        p = haul / 100000.0 * self.penalties["haul_effort"]
        pen_total += p; pen_breakdown["haul"] = round(p, 2)

        if ew.get("wall_trigger"):
            p = self.penalties["retaining_wall"]
            pen_total += p; pen_breakdown["retaining_wall"] = round(p, 2)

        dr_loss = abs(min(0, dr.get("storage_100yr_change_pct", 0)))
        p = (dr_loss / 10.0) * self.penalties["drainage_loss"]
        pen_total += p; pen_breakdown["drainage_loss"] = round(p, 2)

        ob = aes.get("overbuild_penalty", 0)
        p = ob * self.penalties["overbuild"]
        pen_total += p; pen_breakdown["overbuild"] = round(p, 2)

        final_score = max(0.0, normalised - pen_total * 10.0)

        return {
            "total": round(final_score, 1),
            "normalised_pre_penalty": round(normalised, 1),
            "penalty_total": round(pen_total, 2),
            "breakdown": breakdown,
            "penalties": pen_breakdown,
        }

    def verdict(self, score: dict, hard_constraint_result: dict) -> str:
        if not hard_constraint_result.get("valid", False):
            return "reject"
        t = score.get("total", 0)
        if t >= 70:
            return "keep_for_refinement"
        elif t >= 50:
            return "conditional"
        return "revise"
