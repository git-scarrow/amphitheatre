"""ADAEngine: accessible route slope and landing analysis."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
from shapely.geometry import LineString, Point, shape

if TYPE_CHECKING:
    from .project import ProjectState
    from .clay import ClayDelta


class ADAEngine:
    def __init__(self, state: "ProjectState"):
        self.state = state
        ada_cfg = state.cfg["ada"]
        self.max_running_pct = ada_cfg["running_slope_pct"]
        self.target_cross_pct = ada_cfg["cross_slope_target_pct"]
        self.landing_min_ft = ada_cfg["landing_min_length_ft"]

    def _sample_line_profile(self, dem: np.ndarray, line: LineString,
                             n_pts: int = 20) -> list[tuple[float, float]]:
        """Sample elevation along a LineString. Returns [(dist, elev)]."""
        total = line.length
        pts = []
        for i in range(n_pts + 1):
            t = i / n_pts
            p = line.interpolate(t * total)
            elev = self.state.elev_at(dem, p.x, p.y)
            pts.append((t * total, elev))
        return pts

    def _running_slope(self, profile: list[tuple[float, float]]) -> float:
        """Max running slope along a profile (percent)."""
        slopes = []
        for i in range(1, len(profile)):
            d = profile[i][0] - profile[i - 1][0]
            dz = profile[i][1] - profile[i - 1][1]
            if d > 0.01:
                slopes.append(abs(dz / d) * 100)
        return max(slopes) if slopes else 0.0

    def assess_route(self, dem: np.ndarray, route_feat: dict) -> dict:
        """Assess one ADA route feature."""
        pr = route_feat["properties"]
        geom = shape(route_feat["geometry"])
        name = pr.get("name", "unnamed")
        rtype = pr.get("type", "unknown")

        if not isinstance(geom, LineString):
            return {"name": name, "status": "skipped", "reason": "non-LineString"}

        profile = self._sample_line_profile(dem, geom)
        valid = [(d, e) for d, e in profile if np.isfinite(e)]
        if len(valid) < 2:
            return {"name": name, "status": "no_data"}

        max_running = self._running_slope(valid)
        design_running = pr.get("design_running_slope_pct", self.max_running_pct)
        total_drop = abs(valid[-1][1] - valid[0][1])
        total_len = valid[-1][0]
        avg_running = (total_drop / total_len * 100) if total_len > 0 else 0.0

        return {
            "name": name,
            "type": rtype,
            "design_drop_ft": pr.get("total_drop_ft", round(total_drop, 2)),
            "measured_drop_ft": round(total_drop, 2),
            "max_running_slope_pct": round(max_running, 1),
            "avg_running_slope_pct": round(avg_running, 1),
            "design_running_slope_pct": design_running,
            "running_slope_ok": max_running <= self.max_running_pct + 0.1,
            "cross_slope_target_pct": self.target_cross_pct,
            "cross_slope_note": "schematic — cross-slope requires survey; target ≤2%",
        }

    def compute_routes(self, proposed_dem: np.ndarray) -> dict:
        """Assess all ADA routes against proposed terrain."""
        results = []
        for feat in self.state.ada_features:
            pr = feat["properties"]
            rtype = pr.get("type", "")
            if rtype == "switchback_ramp":
                r = self.assess_route(proposed_dem, feat)
                results.append(r)

        summary = {
            "routes_assessed": len(results),
            "all_running_ok": all(r.get("running_slope_ok", True) for r in results),
            "max_running_slope_pct": max(
                (r.get("max_running_slope_pct", 0) for r in results), default=0.0
            ),
            "routes": results,
        }
        return summary

    def delta_vs_baseline(self, proposed_dem: np.ndarray) -> str:
        """Return 'improved', 'unchanged', or 'worsened' vs baseline.

        Policy: if baseline already fails (route slopes >> 8.33%), only flag
        'worsened' if the proposed terrain substantially degrades the already-
        failing route (>10% increase).  Earthwork that does not fix a pre-existing
        ramp access problem should not be penalised for minor perturbations.
        """
        results = self.compute_routes(proposed_dem)
        baseline_results = self.compute_routes(self.state.Z0)
        curr_max = results.get("max_running_slope_pct", 0.0)
        base_max = baseline_results.get("max_running_slope_pct", 0.0)
        base_ok = baseline_results.get("all_running_ok", True)

        if curr_max < base_max - 0.5:
            return "improved"

        if base_ok:
            # Baseline passes — any degradation beyond noise is a real failure.
            if curr_max > base_max + 0.5:
                return "worsened"
        else:
            # Baseline already fails — only flag substantial degradation.
            if curr_max > base_max + 10.0:
                return "worsened"

        return "unchanged"
