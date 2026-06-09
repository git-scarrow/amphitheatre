"""EarthworkEngine: volumes, haul, yield, slope, wall-trigger."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
from shapely.geometry import shape
from rasterio.features import rasterize

if TYPE_CHECKING:
    from .project import ProjectState
    from .clay import ClayDelta

CF_PER_CY = 27.0


class EarthworkEngine:
    def __init__(self, state: "ProjectState"):
        self.state = state
        ew = state.cfg["earthwork"]
        self.tol = ew["lod_tolerance_ft"]
        self.yield_cases = {
            "conservative": ew["yield_conservative"],
            "neutral": ew["yield_neutral"],
            "optimistic": ew["yield_optimistic"],
        }
        self.pref_slope_h = ew["preferred_landscape_slope_h"]
        self.accept_slope_h = ew["acceptable_planted_slope_h"]
        self.caution_slope_h = ew["caution_slope_h"]
        self.max_tieout = ew["max_tieout_dist_ft"]

    def volumes(self, delta: "ClayDelta") -> dict:
        d = delta.delta()
        valid = np.isfinite(self.state.Z0)
        lod = valid & (np.abs(d) > self.tol)
        cut_cf = float(-d[lod & (d < 0)].sum())
        fill_cf = float(d[lod & (d > 0)].sum())
        cut_cy = cut_cf / CF_PER_CY
        fill_cy = fill_cf / CF_PER_CY
        gross_cy = cut_cy + fill_cy
        net_cy = fill_cy - cut_cy
        lod_sqft = int(lod.sum())
        max_cut = float(-d[lod & (d < 0)].min()) if (lod & (d < 0)).any() else 0.0
        max_fill = float(d[lod & (d > 0)].max()) if (lod & (d > 0)).any() else 0.0

        # yield scenarios
        yield_balance = {}
        for name, yf in self.yield_cases.items():
            available_fill = cut_cy * yf
            yield_balance[name] = {
                "yield_factor": yf,
                "available_fill_cy": round(available_fill, 1),
                "shortfall_cy": round(max(0.0, fill_cy - available_fill), 1),
                "surplus_cy": round(max(0.0, available_fill - fill_cy), 1),
                "balanced": fill_cy <= available_fill + 1.0,
            }

        return {
            "cut_cy": round(cut_cy, 1),
            "fill_cy": round(fill_cy, 1),
            "net_cy": round(net_cy, 1),
            "gross_cy": round(gross_cy, 1),
            "max_cut_ft": round(max_cut, 2),
            "max_fill_ft": round(max_fill, 2),
            "lod_sqft": lod_sqft,
            "lod_ac": round(lod_sqft / 43560.0, 3),
            "yield_balance": yield_balance,
        }

    def zone_volumes(self, delta: "ClayDelta", zones: dict) -> dict:
        """Per-zone cut/fill breakdown. zones = {name: shapely_geom or mask}."""
        d = delta.delta()
        Z0 = self.state.Z0
        out = {}
        covered = np.zeros((self.state.ny, self.state.nx), bool)
        for name, zone in zones.items():
            if isinstance(zone, np.ndarray):
                mask = zone & np.isfinite(Z0)
            else:
                mask = self.state.rasterize_geom(zone) & np.isfinite(Z0)
            lod = mask & (np.abs(d) > self.tol)
            cut = float(-d[lod & (d < 0)].sum()) / CF_PER_CY
            fill = float(d[lod & (d > 0)].sum()) / CF_PER_CY
            out[name] = {"cut_cy": round(cut, 1), "fill_cy": round(fill, 1),
                         "net_cy": round(fill - cut, 1)}
            covered |= mask
        return out

    def haul_estimate(self, delta: "ClayDelta",
                      borrow_geom=None, fill_geom=None) -> dict:
        """Estimate average haul distance between borrow and fill polygons.
        If polygons are None, uses centroid of cut vs fill pixels."""
        d = delta.delta()
        Z0 = self.state.Z0
        valid = np.isfinite(Z0)
        lod = valid & (np.abs(d) > self.tol)

        cut_mask = lod & (d < 0)
        fill_mask = lod & (d > 0)

        # Centroids
        def centroid_of_mask(m):
            if not m.any():
                return None
            ys, xs = np.where(m)
            T = self.state.transform
            x_coords = T.c + (xs + 0.5) * T.a
            y_coords = T.f + (ys + 0.5) * T.e
            return float(np.mean(x_coords)), float(np.mean(y_coords))

        if borrow_geom is not None:
            bg = shape(borrow_geom) if isinstance(borrow_geom, dict) else borrow_geom
            cut_centroid = (bg.centroid.x, bg.centroid.y)
        else:
            cut_centroid = centroid_of_mask(cut_mask)

        if fill_geom is not None:
            fg = shape(fill_geom) if isinstance(fill_geom, dict) else fill_geom
            fill_centroid = (fg.centroid.x, fg.centroid.y)
        else:
            fill_centroid = centroid_of_mask(fill_mask)

        if cut_centroid is None or fill_centroid is None:
            return {"avg_haul_ft": 0.0, "haul_effort_cy_ft": 0.0}

        dist = math.hypot(fill_centroid[0] - cut_centroid[0],
                          fill_centroid[1] - cut_centroid[1])

        v = self.volumes(delta)
        haul_effort = (v["cut_cy"] + v["fill_cy"]) / 2 * dist

        return {
            "avg_haul_ft": round(dist, 0),
            "haul_effort_cy_ft": round(haul_effort, 0),
        }

    def slope_improvement(self, delta: "ClayDelta") -> dict:
        """Compare max terrain slope before/after within LOD zone."""
        from .terrain import TerrainEngine
        te = TerrainEngine(self.state)
        lod = te.lod_mask(delta)

        if not lod.any():
            return {"slope_improved": False,
                    "max_slope_before_pct": 0.0, "max_slope_after_pct": 0.0}

        s0 = te.slope_pct(self.state.Z0)
        Zp = delta.proposed(self.state)
        sp = te.slope_pct(Zp)

        m0 = float(np.nanmax(s0[lod & np.isfinite(s0)])) if (lod & np.isfinite(s0)).any() else 0.0
        mp = float(np.nanmax(sp[lod & np.isfinite(sp)])) if (lod & np.isfinite(sp)).any() else 0.0
        return {
            "slope_improved": mp < m0,
            "max_slope_before_pct": round(m0, 1),
            "max_slope_after_pct": round(mp, 1),
        }

    def wall_trigger(self, delta: "ClayDelta") -> dict:
        """Check if cut/fill depth would require retaining walls.

        Triggered by depth, not inherited terrain steepness. Existing steep
        ground is not a wall trigger — a 0.8 ft shallow bench into a steep bank
        does not require a wall. The trigger is: does the PROPOSED DELTA create
        an unsupported face that couldn't stand at the default 3:1 slope?

        Rule: triggered if max_cut_ft > 3.0 OR max_fill_ft > 3.0 OR if the
        fill embankment depth exceeds what the tieout distance can accommodate.
        """
        v = self.volumes(delta)
        cfg = self.state.cfg["earthwork"]

        # Use delta depth (not terrain slope) as the wall trigger criterion.
        # 3:1 embankment/cut: at D_MAX=30 ft apron, max stable height = 30/3 = 10 ft.
        # For planning grade, flag at >3 ft cut or fill as a caution.
        cut_wall = v["max_cut_ft"] > 3.0
        fill_wall = v["max_fill_ft"] > 3.0

        # Also check slope of the DELTA itself (not existing terrain)
        d = delta.delta()
        from .terrain import TerrainEngine
        te = TerrainEngine(self.state)
        lod = te.lod_mask(delta)
        if lod.any():
            dy, dx = np.gradient(np.where(lod, d, 0.0), 1.0, 1.0)
            delta_slope = np.sqrt(dx**2 + dy**2) * 100.0
            max_delta_slope = float(np.nanmax(delta_slope[lod]))
        else:
            max_delta_slope = 0.0

        # Delta slope > 200% means a very abrupt cut/fill face (near-vertical in the delta)
        delta_wall = max_delta_slope > 200.0

        triggered = cut_wall or fill_wall or delta_wall

        return {
            "wall_trigger": triggered,
            "max_cut_ft": v["max_cut_ft"],
            "max_fill_ft": v["max_fill_ft"],
            "max_delta_slope_pct": round(max_delta_slope, 1),
            "note": "trigger if cut/fill > 3 ft depth or delta face > 200% slope",
        }

    def topsoil_estimate(self, delta: "ClayDelta",
                         topsoil_depth_ft: float = 0.5,
                         shrink_factor: float = 1.0) -> dict:
        """Estimate topsoil stripping volume over the limit-of-disturbance.

        V_topsoil = A_lod * t  (separate from structural cut/fill)

        Topsoil is NOT counted as usable structural fill (shrink_factor
        applies only for reuse in landscape restoration, not compaction).
        Planning default: t = 0.5 ft (6 in).
        """
        d = delta.delta()
        valid = np.isfinite(self.state.Z0)
        lod = valid & (np.abs(d) > self.tol)
        lod_sqft = int(lod.sum())
        vol_cf = lod_sqft * topsoil_depth_ft
        vol_cy = vol_cf / CF_PER_CY
        return {
            "topsoil_depth_ft": topsoil_depth_ft,
            "topsoil_lod_sqft": lod_sqft,
            "topsoil_vol_cy": round(vol_cy, 1),
            "topsoil_note": (
                "Separate from structural cut/fill. "
                "Reusable for lawn restoration but not compacted terrace fill."
            ),
        }

    def shrink_swell(self, delta: "ClayDelta",
                     shrink_factor: float | None = None) -> dict:
        """Report usable compacted fill after shrink/swell correction.

        V_usable_fill = V_cut * K
        Planning defaults: sandy/granular 0.90, mixed 0.85, clayey 0.80.
        Harness uses neutral yield (0.95) as K unless overridden.
        """
        if shrink_factor is None:
            shrink_factor = self.yield_cases.get("neutral", 0.95)
        v = self.volumes(delta)
        usable = v["cut_cy"] * shrink_factor
        shortfall = max(0.0, v["fill_cy"] - usable)
        surplus   = max(0.0, usable - v["fill_cy"])
        return {
            "shrink_factor_K": shrink_factor,
            "cut_cy": v["cut_cy"],
            "usable_compacted_fill_cy": round(usable, 1),
            "fill_demand_cy": v["fill_cy"],
            "shortfall_cy": round(shortfall, 1),
            "surplus_cy": round(surplus, 1),
            "balanced": shortfall < 1.0,
        }

    def full_report(self, delta: "ClayDelta",
                    borrow_geom=None, fill_geom=None, zones: dict | None = None) -> dict:
        v = self.volumes(delta)
        h = self.haul_estimate(delta, borrow_geom, fill_geom)
        w = self.wall_trigger(delta)
        si = self.slope_improvement(delta)
        ts = self.topsoil_estimate(delta)
        ss = self.shrink_swell(delta)
        out = {**v, **h, **w, **si,
               "topsoil": ts,
               "shrink_swell": ss}
        if zones:
            out["zone_volumes"] = self.zone_volumes(delta, zones)
        return out
