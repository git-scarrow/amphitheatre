"""ClayDelta: mutable cut/fill raster sitting on top of the immutable LiDAR ground.

P(x,y) = E_0(x,y) + Δ(x,y)

Positive Δ = fill. Negative Δ = cut.
All operations are bounded and stackable: apply multiple ops to build up a scenario.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from rasterio.features import rasterize
from scipy.ndimage import gaussian_filter
from shapely.geometry import shape

if TYPE_CHECKING:
    from .project import ProjectState


class ClayDelta:
    def __init__(self, ny: int, nx: int):
        self.ny = ny
        self.nx = nx
        self._delta = np.zeros((ny, nx), dtype=np.float64)
        self._ops: list[dict] = []  # audit trail

    @classmethod
    def zeros(cls, state: "ProjectState") -> "ClayDelta":
        return cls(state.ny, state.nx)

    @classmethod
    def load(cls, path: str | Path, state: "ProjectState") -> "ClayDelta":
        import rasterio
        with rasterio.open(path) as ds:
            d = ds.read(1).astype(np.float64)
            d[d == (ds.nodata or -9999.0)] = 0.0
        obj = cls(state.ny, state.nx)
        obj._delta = d
        return obj

    def proposed(self, state: "ProjectState") -> np.ndarray:
        """Return P = E0 + Δ. E0 NaN cells remain NaN."""
        P = state.Z0 + self._delta
        P[~np.isfinite(state.Z0)] = np.nan
        return P

    def delta(self) -> np.ndarray:
        return self._delta.copy()

    def _mask_for_geom(self, geom, state: "ProjectState") -> np.ndarray:
        return rasterize(
            [(geom, 1)], out_shape=(self.ny, self.nx),
            transform=state.transform, fill=0, all_touched=True,
        ).astype(bool)

    def _clip_to_limits(self, mask: np.ndarray, min_delta: float, max_delta: float):
        d = self._delta[mask]
        np.clip(d, min_delta, max_delta, out=d)
        self._delta[mask] = d

    # --- operations ---

    def raise_patch(self, state: "ProjectState", polygon_or_geom,
                    amount_ft: float, max_fill_ft: float = 5.0):
        """Add fill within polygon. amount_ft > 0."""
        geom = shape(polygon_or_geom) if isinstance(polygon_or_geom, dict) else polygon_or_geom
        mask = self._mask_for_geom(geom, state) & np.isfinite(state.Z0)
        self._delta[mask] += min(amount_ft, max_fill_ft)
        self._ops.append({"op": "raise_patch", "amount_ft": amount_ft, "max_fill_ft": max_fill_ft})

    def lower_patch(self, state: "ProjectState", polygon_or_geom,
                    amount_ft: float, max_cut_ft: float = 5.0):
        """Remove material within polygon. amount_ft > 0 (will become negative delta)."""
        geom = shape(polygon_or_geom) if isinstance(polygon_or_geom, dict) else polygon_or_geom
        mask = self._mask_for_geom(geom, state) & np.isfinite(state.Z0)
        self._delta[mask] -= min(amount_ft, max_cut_ft)
        self._ops.append({"op": "lower_patch", "amount_ft": amount_ft, "max_cut_ft": max_cut_ft})

    def smooth_patch(self, state: "ProjectState", polygon_or_geom, sigma_ft: float = 5.0):
        """Gaussian smooth delta within polygon to soften edges."""
        geom = shape(polygon_or_geom) if isinstance(polygon_or_geom, dict) else polygon_or_geom
        mask = self._mask_for_geom(geom, state) & np.isfinite(state.Z0)
        d_local = np.where(mask, self._delta, 0.0)
        d_smooth = gaussian_filter(d_local, sigma=sigma_ft)
        self._delta[mask] = d_smooth[mask]
        self._ops.append({"op": "smooth_patch", "sigma_ft": sigma_ft})

    def flatten_pad(self, state: "ProjectState", polygon_or_geom, target_elev_navd88: float):
        """Force absolute elevation within polygon. May cut or fill as needed."""
        geom = shape(polygon_or_geom) if isinstance(polygon_or_geom, dict) else polygon_or_geom
        mask = self._mask_for_geom(geom, state) & np.isfinite(state.Z0)
        self._delta[mask] = target_elev_navd88 - state.Z0[mask]
        self._ops.append({"op": "flatten_pad", "target_elev": target_elev_navd88})

    def terrace_plane(self, state: "ProjectState", polygon_or_geom,
                      base_elev_navd88: float | None = None,
                      cross_slope_pct: float = 2.0,
                      longitudinal_slope_pct: float = 0.5):
        """Set proposed surface to a gently draining planar terrace shelf.

        P(x,y) = base_elev + g_n*(n - n_ref) + g_s*(s - s_ref)

        Orientation (fixed, derived from arc geometry):
          anchor          = polygon centroid
          longitudinal (s) = tangent to the arc at the centroid (along-row)
          cross-slope  (n) = radial direction from arc centre (across-row,
                             positive = outward / uphill)
          g_n = cross_slope_pct / 100
          g_s = longitudinal_slope_pct / 100

        base_elev_navd88:
          If None or omitted, uses the DEM median within the polygon
          (dem_median_on_polygon).  Pass a float to fix the base elevation.
        """
        geom = shape(polygon_or_geom) if isinstance(polygon_or_geom, dict) else polygon_or_geom
        mask = self._mask_for_geom(geom, state) & np.isfinite(state.Z0)

        tf = state.transform
        cx_arc, cy_arc = state.arc_centre()
        centroid = geom.centroid
        cx_ref, cy_ref = centroid.x, centroid.y

        # Auto-derive base elevation from DEM median inside polygon
        base_elev_method = "fixed"
        if base_elev_navd88 is None:
            z_vals = state.Z0[mask]
            z_vals = z_vals[np.isfinite(z_vals)]
            base_elev_navd88 = float(np.median(z_vals)) if len(z_vals) > 0 else 0.0
            base_elev_method = "dem_median_on_polygon"

        # Coordinate grids for masked cells
        rows_i, cols_i = np.where(mask)
        x_cells = tf.c + (cols_i + 0.5) * tf.a
        y_cells = tf.f + (rows_i + 0.5) * tf.e

        # n = radial (across-row, positive = outward from arc centre = uphill)
        R_cells = np.hypot(x_cells - cx_arc, y_cells - cy_arc)
        R_ref   = np.hypot(cx_ref  - cx_arc, cy_ref  - cy_arc)
        n = R_cells - R_ref

        # s = tangential (along-row, CW from north)
        r_ref = R_ref + 1e-9
        tx = +(cy_ref - cy_arc) / r_ref
        ty = -(cx_ref - cx_arc) / r_ref
        s = (x_cells - cx_ref) * tx + (y_cells - cy_ref) * ty

        g_n = cross_slope_pct / 100.0
        g_s = longitudinal_slope_pct / 100.0
        P = base_elev_navd88 + g_n * n + g_s * s

        self._delta[mask] = P - state.Z0[mask]
        self._ops.append({
            "op": "terrace_plane",
            "base_elev": round(base_elev_navd88, 3),
            "base_elev_method": base_elev_method,
            "anchor": "centroid",
            "longitudinal_axis": "arc_tangent_at_centroid",
            "cross_axis": "radial_from_arc_centre",
            "cross_slope_pct": cross_slope_pct,
            "longitudinal_slope_pct": longitudinal_slope_pct,
        })

    def grade_ceiling(self, state: "ProjectState", polygon_or_geom,
                      target_elev_navd88: float, max_cut_ft: float = 2.0):
        """Cut-only version of flatten_pad: lower terrain to target where above it,
        capped at max_cut_ft. Never fills. Used for per-row slope regularization.
        """
        geom = shape(polygon_or_geom) if isinstance(polygon_or_geom, dict) else polygon_or_geom
        mask = self._mask_for_geom(geom, state) & np.isfinite(state.Z0)
        proposed = state.Z0[mask] + self._delta[mask]
        excess = proposed - target_elev_navd88          # positive = needs cut
        additional_cut = np.clip(excess, 0.0, max_cut_ft)
        self._delta[mask] -= additional_cut
        self._ops.append({"op": "grade_ceiling", "target_elev": target_elev_navd88,
                          "max_cut_ft": max_cut_ft})

    def cut_bench(self, state: "ProjectState", polygon_or_geom,
                  target_cut_ft: float, max_cut_ft: float = 2.0):
        """Cut down from existing grade within polygon (negative delta)."""
        geom = shape(polygon_or_geom) if isinstance(polygon_or_geom, dict) else polygon_or_geom
        mask = self._mask_for_geom(geom, state) & np.isfinite(state.Z0)
        cut = min(abs(target_cut_ft), abs(max_cut_ft))
        self._delta[mask] = np.minimum(self._delta[mask], -cut)
        self._ops.append({"op": "cut_bench", "target_cut_ft": target_cut_ft, "max_cut_ft": max_cut_ft})

    def fill_shelf(self, state: "ProjectState", polygon_or_geom,
                   target_fill_ft: float | str, max_fill_ft: float = 1.25):
        """Fill shelf within polygon (positive delta). target_fill_ft may be 'auto_balance'."""
        geom = shape(polygon_or_geom) if isinstance(polygon_or_geom, dict) else polygon_or_geom
        mask = self._mask_for_geom(geom, state) & np.isfinite(state.Z0)
        if target_fill_ft == "auto_balance":
            # Will be resolved by balance_to_zero
            fill = max_fill_ft * 0.5
        else:
            fill = min(float(target_fill_ft), max_fill_ft)
        self._delta[mask] = np.maximum(self._delta[mask], fill)
        self._ops.append({"op": "fill_shelf", "target_fill_ft": str(target_fill_ft), "max_fill_ft": max_fill_ft})

    def balance_to_zero(self, state: "ProjectState",
                        borrow_geom, fill_geom,
                        yield_factor: float = 0.95,
                        max_fill_ft: float = 1.25,
                        max_cut_ft: float = 2.0):
        """Scale fill_geom delta so borrow_CY * yield ≈ fill_CY.
        Call after cut_bench / fill_shelf to auto-size the fill."""
        bg = shape(borrow_geom) if isinstance(borrow_geom, dict) else borrow_geom
        fg = shape(fill_geom) if isinstance(fill_geom, dict) else fill_geom
        bm = self._mask_for_geom(bg, state) & np.isfinite(state.Z0)
        fm = self._mask_for_geom(fg, state) & np.isfinite(state.Z0)

        cut_cf = float(-self._delta[bm & (self._delta < 0)].sum())
        if cut_cf <= 0 or not fm.any():
            return

        target_fill_cf = cut_cf * yield_factor
        fill_area = fm.sum()
        target_fill_ft = min(target_fill_cf / fill_area, max_fill_ft) if fill_area > 0 else 0.0
        self._delta[fm] = np.maximum(self._delta[fm], target_fill_ft)
        self._ops.append({
            "op": "balance_to_zero",
            "yield_factor": yield_factor,
            "derived_fill_ft": round(target_fill_ft, 3),
        })

    def apply_scenario_action(self, state: "ProjectState", action: dict,
                              scenario_features: dict):
        """Dispatch a single action dict from a proposal to the right operation.
        scenario_features maps name -> shapely geometry."""
        op = action.get("op") or action.get("type") or list(action.keys())[0]
        params = action.get(op, action)

        geom_name = params.get("polygon") or params.get("geom")
        geom = scenario_features.get(geom_name)
        if geom is None:
            raise ValueError(f"No geometry found for '{geom_name}'. "
                             f"Available: {list(scenario_features)}")

        if op == "grade_ceiling":
            self.grade_ceiling(state, geom, params["target_elev"],
                               params.get("max_cut_ft", 2.0))
        elif op == "terrace_plane":
            self.terrace_plane(state, geom, params["base_elev"],
                               params.get("cross_slope_pct", 2.0),
                               params.get("longitudinal_slope_pct", 0.5))
        elif op == "raise_patch":
            self.raise_patch(state, geom, params["amount_ft"],
                             params.get("max_fill_ft", 5.0))
        elif op == "lower_patch":
            self.lower_patch(state, geom, params["amount_ft"],
                             params.get("max_cut_ft", 5.0))
        elif op == "smooth_patch":
            self.smooth_patch(state, geom, params.get("sigma_ft", 5.0))
        elif op == "flatten_pad":
            self.flatten_pad(state, geom, params["target_elev"])
        elif op == "cut_bench":
            self.cut_bench(state, geom,
                           params.get("target_cut_ft", params.get("preferred_cut_ft", 0.8)),
                           params.get("max_cut_ft", 2.0))
        elif op == "fill_shelf":
            self.fill_shelf(state, geom,
                            params.get("target_fill_ft", params.get("preferred_fill_ft", "auto_balance")),
                            params.get("max_fill_ft", 1.25))
        elif op == "balance_to_zero":
            borrow = scenario_features.get(params["borrow_polygon"])
            fill = scenario_features.get(params["fill_polygon"])
            if borrow is None or fill is None:
                raise ValueError("balance_to_zero requires borrow_polygon and fill_polygon keys")
            self.balance_to_zero(state, borrow, fill,
                                 params.get("yield_factor", 0.95),
                                 params.get("max_fill_ft", 1.25),
                                 params.get("max_cut_ft", 2.0))
        elif op == "preserve":
            pass  # no-op; preserved zones are enforced at evaluator level
        else:
            raise ValueError(f"Unknown op: {op}")

    def save(self, path: str | Path, state: "ProjectState"):
        import rasterio
        prof = {
            "driver": "GTiff",
            "dtype": "float32",
            "width": self.nx,
            "height": self.ny,
            "count": 1,
            "crs": rasterio.open(state.root / state.cfg["terrain"]["dem"]).crs,
            "transform": state.transform,
            "nodata": -9999.0,
            "compress": "lzw",
        }
        out = np.where(np.isfinite(state.Z0), self._delta, -9999.0).astype("float32")
        with rasterio.open(path, "w", **prof) as dst:
            dst.write(out, 1)
