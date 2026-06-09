"""SolarEvaluator: sunset visibility scoring and glare analysis.

The solar layer is deterministic — the agent may move terrain and design
objects, but cannot move the sun. Optimizing glare requires rotating the bowl
or accepting terrain-limited horizon, not faking the sun position.

Seasonal envelope of interest: 296–306° (late May – late July sunset band).
Key rule: bowl axis ~315–325° puts sunset left-of-centre for audience,
avoiding performer glare while enriching upper rows.
"""
from __future__ import annotations

import math
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .project import ProjectState

# Import existing solar.py (../solar.py relative to harness/)
_SOLAR_PATH = Path(__file__).parent.parent
if str(_SOLAR_PATH) not in sys.path:
    sys.path.insert(0, str(_SOLAR_PATH))
from solar import sun_position  # noqa: E402


class SolarEvaluator:
    def __init__(self, state: "ProjectState"):
        self.state = state
        site = state.cfg["site"]
        self.lat = site["lat"]
        self.lon = site["lon"]
        self.utc_offset = site["utc_offset_hours"]
        solar_cfg = state.cfg["solar"]
        self.az_min = solar_cfg["sunset_envelope_az_min"]
        self.az_max = solar_cfg["sunset_envelope_az_max"]
        self.glare_high = solar_cfg["glare_high_deg"]
        self.glare_medium = solar_cfg["glare_medium_deg"]

    def sunset_azimuths(self) -> dict[str, float]:
        """Compute approximate sunset azimuth for each sample date (hour=21 EDT)."""
        dates = self.state.cfg["solar"]["sample_dates"]
        year = 2025
        results = {}
        for d in dates:
            dt = datetime(year, d["month"], d["day"], 21, 0, 0)
            az, alt, _ = sun_position(dt, self.lat, self.lon, self.utc_offset)
            results[d["label"]] = round(az, 1)
        return results

    def _horizon_elevation(self, proposed_dem: np.ndarray,
                            observer_x: float, observer_y: float, observer_z: float,
                            az_deg: float, max_range_ft: float = 500.0,
                            step_ft: float = 10.0) -> float:
        """Ray-cast horizon elevation angle (degrees) along az_deg from observer."""
        a = math.radians(az_deg)
        dx_unit = math.sin(a)
        dy_unit = math.cos(a)
        max_angle = -90.0
        r = step_ft
        while r <= max_range_ft:
            tx = observer_x + dx_unit * r
            ty = observer_y + dy_unit * r
            tz = self.state.elev_at(proposed_dem, tx, ty)
            if np.isfinite(tz):
                angle = math.degrees(math.atan2(tz - observer_z, r))
                max_angle = max(max_angle, angle)
            r += step_ft
        return max_angle

    def score_observer(self, proposed_dem: np.ndarray,
                        obs_x: float, obs_y: float, obs_eye_z: float,
                        bowl_axis_az: float) -> dict:
        """Score solar value for one observer point."""
        results = {}
        in_envelope = 0
        total_dates = 0

        for label, sunset_az in self.sunset_azimuths().items():
            # Horizon at that azimuth
            horizon_alt = self._horizon_elevation(proposed_dem, obs_x, obs_y, obs_eye_z,
                                                   sunset_az)
            # Sun altitude at nominal sunset time
            dt = self._sample_datetime(label)
            sun_az, sun_alt, _ = sun_position(dt, self.lat, self.lon, self.utc_offset)

            visible = sun_alt > horizon_alt + 0.5  # sun above terrain horizon
            in_envelope_date = self.az_min <= sunset_az <= self.az_max
            if in_envelope_date:
                total_dates += 1
                if visible:
                    in_envelope += 1
            results[label] = {
                "sunset_az": sunset_az,
                "horizon_alt_deg": round(horizon_alt, 1),
                "sun_alt_deg": round(sun_alt, 1),
                "visible": visible,
                "in_envelope": in_envelope_date,
            }

        envelope_score = in_envelope / total_dates if total_dates > 0 else 0.0

        # Glare: distance between bowl axis and sunset envelope centre
        envelope_centre = (self.az_min + self.az_max) / 2
        az_offset = abs(bowl_axis_az - envelope_centre) % 360
        if az_offset > 180:
            az_offset = 360 - az_offset

        if az_offset < self.glare_high:
            glare = "high"
        elif az_offset < self.glare_medium:
            glare = "medium"
        else:
            glare = "low"

        return {
            "envelope_score": round(envelope_score, 2),
            "glare_penalty": glare,
            "az_offset_to_envelope": round(az_offset, 1),
            "dates": results,
        }

    def _sample_datetime(self, label: str) -> datetime:
        dates = {d["label"]: d for d in self.state.cfg["solar"]["sample_dates"]}
        d = dates.get(label, {"month": 6, "day": 21})
        return datetime(2025, d["month"], d["day"], 21, 0, 0)

    def score_upper_crescent(self, proposed_dem: np.ndarray,
                              bowl_axis_az: float) -> dict:
        """Score upper rows (rows 12–16) for sunset value."""
        p = self.state.params()
        FX, FY = self.state.arc_centre()
        ax = p["AX_AZ"]
        fh = p["FAN_HALF"]
        R_outer = p["R_OUTER"]
        eye_ht = p["EYE_HT"]

        # Observer points: mid-arc of upper rows, biased left (west) toward sunset
        observer_pts = []
        for R in [R_outer - 9, R_outer - 6, R_outer - 3, R_outer]:
            # West flank of upper rows (left side as audience faces bowl)
            for az_off in [fh * 0.5, fh * 0.75]:
                a = math.radians(ax - az_off)  # west = left of audience-facing
                x = FX + math.sin(a) * R
                y = FY + math.cos(a) * R
                z = self.state.elev_at(proposed_dem, x, y)
                if np.isfinite(z):
                    observer_pts.append((x, y, z + eye_ht))

        if not observer_pts:
            return {"upper_crescent_score": 0.0, "sample_count": 0}

        scores = [self.score_observer(proposed_dem, x, y, z, bowl_axis_az)
                  for x, y, z in observer_pts]
        avg_score = float(np.mean([s["envelope_score"] for s in scores]))
        glare_vals = {"low": 0, "medium": 1, "high": 2}
        avg_glare_val = float(np.mean([glare_vals[s["glare_penalty"]] for s in scores]))
        glare = ["low", "medium", "high"][round(avg_glare_val)]

        return {
            "upper_crescent_score": round(avg_score, 2),
            "glare_penalty": glare,
            "sample_count": len(observer_pts),
            "detail": scores[:2],  # first two for report
        }

    def glare_penalty_score(self, bowl_axis_az: float) -> float:
        """Penalty 0–1 (0=no penalty, 1=high glare) for performer glare."""
        envelope_centre = (self.az_min + self.az_max) / 2
        az_offset = abs(bowl_axis_az - envelope_centre) % 360
        if az_offset > 180:
            az_offset = 360 - az_offset
        if az_offset < self.glare_high:
            return 1.0
        elif az_offset < self.glare_medium:
            return 0.5
        return 0.0
