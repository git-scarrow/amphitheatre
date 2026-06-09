"""AestheticEvaluator: measurable proxies for civic/landscape quality.

Aesthetic judgment becomes computable. No vague taste — only proxies.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
from shapely.geometry import shape

if TYPE_CHECKING:
    from .project import ProjectState
    from .clay import ClayDelta


class AestheticEvaluator:
    def __init__(self, state: "ProjectState"):
        self.state = state

    def landform_fit(self, delta: "ClayDelta") -> float:
        """Fraction of row treads within ±0.2 ft of natural grade (no engineered fill needed).
        1.0 = all rows on natural grade. Lower = more forcing.
        """
        rows = self.state.rows_tbl
        Zp = delta.proposed(self.state)
        on_grade = sum(
            1 for r in rows
            if abs(self.state.sample_arc_median(Zp, r["R"]) - r.get("terr", 0)) < 0.25
        )
        return round(on_grade / len(rows), 2) if rows else 0.0

    def row_arc_contour_match(self) -> float:
        """How well do row arcs follow natural contour curvature.
        Proxy: stddev of terrain elevation across each row arc (lower = more level arc).
        We use the baseline terrain only — this doesn't change with delta.
        """
        rows = self.state.rows_tbl
        scores = []
        for r in rows:
            p = self.state.params()
            ax, fh = p["AX_AZ"], p["FAN_HALF"]
            FX, FY = self.state.arc_centre()
            vals = []
            for az in np.linspace(ax - fh, ax + fh, 21):
                a = math.radians(az)
                x = FX + math.sin(a) * r["R"]
                y = FY + math.cos(a) * r["R"]
                v = self.state.elev_at(self.state.Z0, x, y)
                if np.isfinite(v):
                    vals.append(v)
            if vals:
                scores.append(float(np.std(vals)))
        # Normalise: stddev < 0.5 ft = good (score 1), > 3 ft = poor (score 0)
        if not scores:
            return 0.0
        mean_std = float(np.mean(scores))
        return round(max(0.0, 1.0 - mean_std / 3.0), 2)

    def stage_presence(self) -> float:
        """Stage frontage as fraction of row-1 arc length.
        0.64 = target (~64%). Score normalised to 1.0 at target."""
        p = self.state.params()
        row1_arc = p["R_INNER"] * math.radians(2 * p["FAN_HALF"])
        stage_front = self.state.cfg["stage"]["width_ft"] + 2 * 17.0  # ~104 ft
        ratio = stage_front / row1_arc
        return round(min(1.0, ratio / 0.64), 2)

    def bay_view_score(self, proposed_dem: np.ndarray) -> float:
        """Score based on whether the upstage (bay-facing) side stays open and low.
        Check: median elevation of DEM directly behind stage stays <= event_floor + 3 ft.
        """
        p = self.state.params()
        FX, FY = self.state.arc_centre()
        ax = p["AX_AZ"]
        stage_r = self.state.cfg["stage"]["stage_r_ft"]
        floor_elev = self.state.cfg["stage"]["elevation_navd88"]

        # Sample a zone upstage of the stage (behind stage in audience view = NNW)
        upstage_elvs = []
        for r in [stage_r + 10, stage_r + 20, stage_r + 30]:
            for az_off in np.linspace(-20, 20, 9):
                a = math.radians(ax + az_off)
                x = FX + math.sin(a) * r
                y = FY + math.cos(a) * r
                v = self.state.elev_at(proposed_dem, x, y)
                if np.isfinite(v):
                    upstage_elvs.append(v)

        if not upstage_elvs:
            return 0.5

        max_upstage = float(np.percentile(upstage_elvs, 90))
        # Score: 1.0 if upstage < floor + 3 ft, 0 if upstage > floor + 10 ft
        excess = max_upstage - (floor_elev + 3.0)
        return round(max(0.0, min(1.0, 1.0 - excess / 7.0)), 2)

    def open_air_score(self, proposed_dem: np.ndarray) -> float:
        """Check that no tall structure obstructs the upstage horizon.
        Proxy for 'not an enclosed room' — delegates to bay_view_score."""
        return self.bay_view_score(proposed_dem)

    def overbuild_penalty(self, earthwork_metrics: dict) -> float:
        """Penalty for over-engineering. 0=lean, 1=extremely over-built."""
        gross_cy = earthwork_metrics.get("gross_cy", 0)
        wall = earthwork_metrics.get("wall_trigger", False)
        # ~100 CY gross = minimal; ~1000 CY = concerning; > 2000 CY = overbuild
        cy_penalty = min(1.0, gross_cy / 2000.0)
        wall_penalty = 1.0 if wall else 0.0
        return round((cy_penalty + wall_penalty) / 2, 2)

    def compute(self, delta: "ClayDelta", earthwork_metrics: dict) -> dict:
        Zp = delta.proposed(self.state)
        return {
            "landform_fit": self.landform_fit(delta),
            "row_arc_contour_match": self.row_arc_contour_match(),
            "stage_presence": self.stage_presence(),
            "bay_view_score": self.bay_view_score(Zp),
            "open_air_score": self.open_air_score(Zp),
            "overbuild_penalty": self.overbuild_penalty(earthwork_metrics),
        }
