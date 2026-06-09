"""TerrainEngine: apply delta, compute slopes, extract profiles."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
from scipy.ndimage import uniform_filter

if TYPE_CHECKING:
    from .project import ProjectState
    from .clay import ClayDelta


class TerrainEngine:
    def __init__(self, state: "ProjectState"):
        self.state = state

    def proposed(self, delta: "ClayDelta") -> np.ndarray:
        return delta.proposed(self.state)

    def slope_pct(self, dem: np.ndarray) -> np.ndarray:
        """Slope in percent (rise/run * 100). Uses 1 ft pixel spacing."""
        dy, dx = np.gradient(dem, 1.0, 1.0, edge_order=1)
        slope = np.sqrt(dx**2 + dy**2) * 100.0
        slope[~np.isfinite(dem)] = np.nan
        return slope

    def slope_stats(self, dem: np.ndarray, mask: np.ndarray | None = None) -> dict:
        s = self.slope_pct(dem)
        if mask is not None:
            s = s[mask & np.isfinite(s)]
        else:
            s = s[np.isfinite(s)]
        if s.size == 0:
            return {"mean_slope_pct": np.nan, "max_slope_pct": np.nan, "p95_slope_pct": np.nan}
        return {
            "mean_slope_pct": float(np.mean(s)),
            "max_slope_pct": float(np.max(s)),
            "p95_slope_pct": float(np.percentile(s, 95)),
        }

    def sample_arc_row(self, dem: np.ndarray, R: float, n: int = 41) -> dict:
        """Sample elevations along a row arc; return stats."""
        p = self.state.params()
        ax, fh = p["AX_AZ"], p["FAN_HALF"]
        FX, FY = self.state.arc_centre()
        vals = []
        for az in np.linspace(ax - fh, ax + fh, n):
            a = math.radians(az)
            x = FX + math.sin(a) * R
            y = FY + math.cos(a) * R
            v = self.state.elev_at(dem, x, y)
            if np.isfinite(v):
                vals.append(v)
        return {
            "median": float(np.median(vals)) if vals else np.nan,
            "min": float(np.min(vals)) if vals else np.nan,
            "max": float(np.max(vals)) if vals else np.nan,
            "n": len(vals),
        }

    def cut_fill_raster(self, delta: "ClayDelta") -> np.ndarray:
        """Return raw delta (Zp - Z0). Positive = fill, negative = cut."""
        return delta.delta()

    def lod_mask(self, delta: "ClayDelta", tol: float | None = None) -> np.ndarray:
        """Limit-of-disturbance: pixels where |delta| > tolerance."""
        tol = tol or self.state.cfg["earthwork"]["lod_tolerance_ft"]
        return (np.abs(delta.delta()) > tol) & np.isfinite(self.state.Z0)
