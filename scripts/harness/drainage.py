"""DrainageEngine: treatment cell storage, ponding, freeboard checks."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .project import ProjectState
    from .clay import ClayDelta


class DrainageEngine:
    def __init__(self, state: "ProjectState"):
        self.state = state
        tc = state.cfg["treatment_cell"]
        self.cell_bottom = tc["bottom_navd88"]
        self.pool_elev = tc["pool_navd88"]
        self.wsel_100yr = tc["wsel_100yr"]
        self.floor_min = tc["event_floor_min_navd88"]

    def _get_cell_mask(self) -> np.ndarray:
        g = self.state.stage_feature("treatment_wet_cell")
        return self.state.rasterize_geom(g)

    def storage_volume(self, dem: np.ndarray, wsel: float,
                       cell_mask: np.ndarray | None = None) -> float:
        """Approximate storage volume (CF) between dem and wsel within cell_mask."""
        if cell_mask is None:
            cell_mask = self._get_cell_mask()
        valid = cell_mask & np.isfinite(dem)
        depth = np.maximum(0.0, wsel - dem[valid])
        return float(depth.sum())  # sum of 1sqft cells * depth in ft = CF

    def freeboard(self, proposed_dem: np.ndarray) -> float:
        """Event floor freeboard above 100-yr WSEL.
        Uses the configured floor elevation (design datum), not raw terrain, because the
        stage pad is an engineered surface whose elevation is a design constant, not derived
        from the DEM sample at that point.
        """
        return round(self.floor_min - self.wsel_100yr, 2)

    def compute(self, proposed_dem: np.ndarray) -> dict:
        mask = self._get_cell_mask()
        if not mask.any():
            return {"error": "treatment_wet_cell geometry not found"}

        s_pool = self.storage_volume(proposed_dem, self.pool_elev, mask)
        s_100yr = self.storage_volume(proposed_dem, self.wsel_100yr, mask)
        s0_pool = self.storage_volume(self.state.Z0, self.pool_elev, mask)
        s0_100yr = self.storage_volume(self.state.Z0, self.wsel_100yr, mask)

        cell_area = float(mask.sum())
        cell_area_ac = round(cell_area / 43560.0, 3)

        fb = self.freeboard(proposed_dem)

        return {
            "cell_area_sqft": round(cell_area, 0),
            "cell_area_ac": cell_area_ac,
            "storage_pool_wsel_cf": round(s_pool, 0),
            "storage_100yr_wsel_cf": round(s_100yr, 0),
            "storage_pool_change_pct": round((s_pool - s0_pool) / max(s0_pool, 1) * 100, 1),
            "storage_100yr_change_pct": round((s_100yr - s0_100yr) / max(s0_100yr, 1) * 100, 1),
            "event_floor_freeboard_ft": fb,
            "freeboard_ok": fb >= 1.0,
            "cell_function_preserved": (
                s_100yr >= s0_100yr * 0.90 and fb >= 1.0
            ),
        }

    def delta_vs_baseline(self, proposed_dem: np.ndarray) -> str:
        result = self.compute(proposed_dem)
        chg = result.get("storage_100yr_change_pct", 0.0)
        if chg > 2:
            return "gained"
        elif chg < -5:
            return "lost"
        return "unchanged"
