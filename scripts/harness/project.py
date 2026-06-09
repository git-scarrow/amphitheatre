"""ProjectState: immutable terrain + design objects loaded once at startup."""
import json
import math
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
import yaml
from rasterio.transform import rowcol
from shapely.geometry import shape


@dataclass
class ProjectState:
    root: Path
    cfg: dict

    # Terrain (immutable)
    Z0: np.ndarray = field(repr=False)          # existing DEM (NY x NX)
    transform: Any = field(repr=False)           # rasterio Affine
    ny: int = 0
    nx: int = 0
    nodata: float = -9999.0

    # Design context
    ctx: dict = field(default_factory=dict)      # from _ctx.pkl
    rows_tbl: list = field(default_factory=list) # per-row geometry+sightline data
    stage_features: list = field(default_factory=list)
    ada_features: list = field(default_factory=list)
    basin_poly: Any = None                        # shapely Polygon

    # Pixel coordinate grids (derived)
    XX: np.ndarray = field(repr=False, default=None)
    YY: np.ndarray = field(repr=False, default=None)
    RAD: np.ndarray = field(repr=False, default=None)  # radius from arc centre
    AZ: np.ndarray = field(repr=False, default=None)   # bearing from arc centre

    @classmethod
    def load(cls, config_path: str | Path = "harness_config.yaml") -> "ProjectState":
        root = Path(config_path).parent
        with open(config_path) as fh:
            cfg = yaml.safe_load(fh)

        # DEM
        dem_path = root / cfg["terrain"]["dem"]
        ds = rasterio.open(dem_path)
        Z = ds.read(1).astype(np.float64)
        nd = ds.nodata or cfg["terrain"]["nodata"]
        Z[Z == nd] = np.nan
        ny, nx = ds.shape
        T = ds.transform

        # Pixel-centre coordinate grids
        cols = np.arange(nx)
        rows = np.arange(ny)
        XC = T.c + (cols + 0.5) * T.a
        YC = T.f + (rows + 0.5) * T.e
        XX, YY = np.meshgrid(XC, YC)

        # Arc centre
        ctx_path = root / cfg["design"]["baseline_ctx"]
        ctx = pickle.load(open(ctx_path, "rb"))
        FX, FY = ctx["F"]
        dx = XX - FX
        dy = YY - FY
        RAD = np.hypot(dx, dy)
        AZ = np.degrees(np.arctan2(dx, dy)) % 360.0

        # Design objects
        def load_fc(rel):
            p = root / rel
            return json.load(open(p))["features"] if p.exists() else []

        stage_feats = load_fc(cfg["design"]["stage_floor"])
        ada_feats = load_fc(cfg["design"]["ada_route"])

        basin_poly = None
        basin_path = root / cfg["design"]["basin"]
        if basin_path.exists():
            feats = json.load(open(basin_path))["features"]
            if feats:
                basin_poly = shape(feats[0]["geometry"])

        state = cls(
            root=root, cfg=cfg,
            Z0=Z, transform=T, ny=ny, nx=nx, nodata=nd,
            ctx=ctx, rows_tbl=ctx["rows"],
            stage_features=stage_feats,
            ada_features=ada_feats,
            basin_poly=basin_poly,
            XX=XX, YY=YY, RAD=RAD, AZ=AZ,
        )
        return state

    # --- conveniences ---

    def stage_feature(self, name: str):
        for f in self.stage_features:
            if f["properties"].get("name") == name:
                return shape(f["geometry"])
        return None

    def params(self) -> dict:
        return self.ctx["params"]

    def arc_centre(self):
        return self.ctx["F"]  # (FX, FY)

    def stage_focus(self):
        return self.ctx.get("SF", self.ctx["F"])

    def elev_at(self, dem: np.ndarray, x: float, y: float) -> float:
        r, c = rowcol(self.transform, x, y)
        if 0 <= r < self.ny and 0 <= c < self.nx:
            v = dem[r, c]
            return float(v) if np.isfinite(v) else np.nan
        return np.nan

    def sample_arc_median(self, dem: np.ndarray, R: float, n: int = 41) -> float:
        p = self.params()
        ax, fh = p["AX_AZ"], p["FAN_HALF"]
        FX, FY = self.arc_centre()
        vals = []
        for az in np.linspace(ax - fh, ax + fh, n):
            a = math.radians(az)
            x = FX + math.sin(a) * R
            y = FY + math.cos(a) * R
            v = self.elev_at(dem, x, y)
            if np.isfinite(v):
                vals.append(v)
        return float(np.median(vals)) if vals else np.nan

    def fan_mask(self) -> np.ndarray:
        p = self.params()
        ax, fh = p["AX_AZ"], p["FAN_HALF"]
        d = (self.AZ - ax + 180) % 360 - 180
        return (np.abs(d) <= fh) & (self.RAD >= p["R_INNER"]) & (self.RAD <= p["R_OUTER"])

    def rasterize_geom(self, geom) -> np.ndarray:
        from rasterio.features import rasterize
        if geom is None:
            return np.zeros((self.ny, self.nx), bool)
        return rasterize(
            [(geom, 1)], out_shape=(self.ny, self.nx),
            transform=self.transform, fill=0, all_touched=True,
        ).astype(bool)
