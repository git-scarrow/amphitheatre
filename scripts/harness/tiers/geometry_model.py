"""SectionSeatingModel: mutable three-section seating/stage geometry model.

The geometry counterpart to ClayDelta. Loaded from the LOCKED Scenario E
artifacts (read-only inputs):

  analysis/scenarioE_civic/geometry.geojson    validated tread polygons,
      cross-aisle, ADA ramps + landings, swales, shoulders, stage surfaces,
      construction envelope
  design_extended_bays/composition_table.csv   per (row, section): elev,
      axis radius, length, seats, cross-angle, C_mm, sees_bay
  design_extended_bays/seating_bays.geojson    bay centrelines rows 1-25
  analysis/scenarioE_civic/earthwork.csv       per-component CY (500.8 total)

There is NO shared arc centre and NO constant-radius fan: east / bend / south
are contour-fitted families. Operations mutate band status / tread elevation /
seats and append to an audit trail; the locked input files are never written.

Planning grade. NAVD88 intl ft, EPSG:6494.
"""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
import yaml
from rasterio.features import rasterize
from shapely.geometry import shape

SECTIONS = ("east", "bend", "south")
FORMAL_STOP_ROW = 18
PROMENADE_ROW = 5
AISLE_ROWS = (9, 10)

# Sightline solver constants (same model that produced composition_table C_mm)
STAGE_R_FT = 50.0
FOCUS_ELEV = 612.5
EYE_HT_FT = 3.94
C_TARGET_MM = 90.0

# Inherited stage (design_open_low geometry reused by Scenario E; Rule 9 OPEN)
INHERITED_STAGE = {
    "name": "inherited_az150",
    "axis_az": 150.0,
    "sf_x": 19533100.2,
    "sf_y": 750742.9,
    "elev_navd88": 612.5,
    "width_ft": 70.0,
    "depth_ft": 34.0,
    "rule9_status": "open",
    # measured row-1 gaps per family (analysis/in_situ_normalization
    # STAGE_SHAPE_STUDY.md, P_inherited)
    "row1_gap_ft": {"east": 17.3, "bend": 20.6, "south": 2.2},
    "apron": None,
    "bay_obstruction_pct": 0.0,
    "cell_obstruction_pct": 0.0,
    "earthwork_delta_cy": 0.0,
    "provenance": "design_open_low stage reused by Scenario E (Rule 9 OPEN)",
}


@dataclass
class Band:
    """One (section, row) seating band."""
    section: str
    row: int
    zone: str                 # forecourt | civic
    status: str               # formal | promenade | aisle | terrace | lawn | trimmed
    tread_elev: float         # design tread elevation (mutable)
    base_elev: float          # locked Scenario E / composition elevation
    axis_radius_ft: float
    length_ft: float
    seats: int                # current seats (mutable)
    base_seats: int
    cross_angle_deg: float
    comp_c_mm: float | None   # authoritative composition C (cross-check only)
    sees_bay: bool
    geometry: Any = None      # shapely polygon (tread) or buffered centreline
    centreline: Any = None    # shapely LineString from seating_bays
    geometry_source: str = ""
    added_by_op: str | None = None   # None = part of the locked baseline


@dataclass
class TierState:
    """Light terrain/context state for tier evaluation.

    Deliberately does NOT load design_open_low/_ctx.pkl: no arc centre, no
    fan mask. Only the DEM, the harness config constants, and the treatment
    cell polygon (a physical object, not seating geometry).
    """
    root: Path
    cfg: dict
    Z0: np.ndarray
    transform: Any
    ny: int
    nx: int
    nodata: float = -9999.0
    stage_features: list = field(default_factory=list)  # for treatment cell only

    @classmethod
    def load(cls, config_path: str | Path = "harness_config.yaml") -> "TierState":
        root = Path(config_path).resolve().parent
        with open(config_path) as fh:
            cfg = yaml.safe_load(fh)
        ds = rasterio.open(root / cfg["terrain"]["dem"])
        Z = ds.read(1).astype(np.float64)
        nd = ds.nodata or cfg["terrain"]["nodata"]
        Z[Z == nd] = np.nan
        # The treatment cell polygon lives in design_open_low/stage_floor.geojson.
        # The CELL is a physical drainage object; consuming its polygon is not a
        # design_open_low seating-geometry regression (gate checks seating only).
        feats = []
        sf = root / cfg["design"]["stage_floor"]
        if sf.exists():
            feats = json.load(open(sf))["features"]
        return cls(root=root, cfg=cfg, Z0=Z, transform=ds.transform,
                   ny=ds.height, nx=ds.width, nodata=nd, stage_features=feats)

    def stage_feature(self, name: str):
        for f in self.stage_features:
            if f["properties"].get("name") == name:
                return shape(f["geometry"])
        return None

    def rasterize_geom(self, geom) -> np.ndarray:
        if geom is None:
            return np.zeros((self.ny, self.nx), bool)
        return rasterize([(geom, 1)], out_shape=(self.ny, self.nx),
                         transform=self.transform, fill=0,
                         all_touched=True).astype(bool)

    def elev_at(self, dem: np.ndarray, x: float, y: float) -> float:
        from rasterio.transform import rowcol
        r, c = rowcol(self.transform, x, y)
        if 0 <= r < self.ny and 0 <= c < self.nx:
            v = dem[r, c]
            return float(v) if np.isfinite(v) else np.nan
        return np.nan

    def sample_line(self, dem: np.ndarray, line, step_ft: float = 3.0) -> list[float]:
        n = max(2, int(line.length / step_ft))
        vals = []
        for i in range(n + 1):
            p = line.interpolate(i / n, normalized=True)
            v = self.elev_at(dem, p.x, p.y)
            if np.isfinite(v):
                vals.append(v)
        return vals


class SectionSeatingModel:
    def __init__(self, state: TierState,
                 treads_path: str | Path,
                 composition_path: str | Path,
                 bays_path: str | Path,
                 earthwork_path: str | Path):
        self.state = state
        self.sources = {
            "treads": str(treads_path),
            "composition": str(composition_path),
            "bays": str(bays_path),
            "earthwork": str(earthwork_path),
        }
        self.bands: dict[tuple[str, int], Band] = {}
        self.features: dict[str, list[dict]] = {}   # role -> scenario E features
        self.baseline_earthwork: dict[str, dict] = {}
        self.stage: dict = dict(INHERITED_STAGE)
        self.ops_log: list[dict] = []
        self.cross_aisle: dict = {}
        self._load(treads_path, composition_path, bays_path, earthwork_path)

    # ── loading ────────────────────────────────────────────────────────────

    def _load(self, treads_path, composition_path, bays_path, earthwork_path):
        comp: dict[tuple[str, int], dict] = {}
        for r in csv.DictReader(open(composition_path)):
            key = (r["section"], int(r["row"]))
            comp[key] = {
                "zone": r["zone"],
                "elev": float(r["elev"]),
                "axis_radius_ft": float(r["axis_radius_ft"]),
                "length_ft": float(r["length_ft"]),
                "seats": int(r["seats"]),
                "cross_angle_deg": float(r["cross_angle_deg"]),
                "c_mm": float(r["C_mm"]) if r["C_mm"].strip() else None,
                "sees_bay": r["sees_bay"].strip().lower() == "true",
            }

        cl: dict[tuple[str, int], Any] = {}
        for f in json.load(open(bays_path))["features"]:
            p = f["properties"]
            cl[(p["section"], int(p["row"]))] = shape(f["geometry"])

        geo = json.load(open(treads_path))
        tread_geo: dict[tuple[str, int], Any] = {}
        for f in geo["features"]:
            p = f["properties"]
            role = p.get("role", "")
            self.features.setdefault(role, []).append(f)
            if role == "formal_restored_tread":
                tread_geo[(p["section"], int(p["row"]))] = {
                    "geom": shape(f["geometry"]),
                    "seats_kept": int(p.get("seats_kept", 0)),
                }

        # cross-aisle as-built fit
        for f in self.features.get("cross_aisle", []):
            p = f["properties"]
            self.cross_aisle = {
                "rows": p.get("nearest_row_ids", list(AISLE_ROWS)),
                "cross_slope_pct": p.get("cross_slope_pct", 2.0),
                "long_slope_pct": p.get("long_slope_pct", 1.0),
                "drains": p.get("drains", True),
                "wheelable": p.get("wheelable", True),
                "displaced_seats": p.get("displaced_seats", 169),
                "resolved_by_op": None,
            }

        for r in csv.DictReader(open(earthwork_path)):
            self.baseline_earthwork[r["component"]] = {
                "cut_cy": float(r["cut_cy"]),
                "fill_cy": float(r["fill_cy"]),
                "gross_cy": float(r["gross_cy"]),
                "topsoil_cy": float(r["topsoil_cy"]) if r.get("topsoil_cy", "").strip() else 0.0,
            }

        for (section, row), c in sorted(comp.items()):
            if row == PROMENADE_ROW:
                status = "promenade"
            elif row in AISLE_ROWS:
                status = "aisle"
            elif row <= FORMAL_STOP_ROW:
                status = "formal"
            else:
                status = "terrace"
            tg = tread_geo.get((section, row))
            seats = tg["seats_kept"] if tg else (0 if status in ("promenade", "aisle") else c["seats"])
            if status == "terrace":
                seats = c["seats"]   # terrace seats exist as informal capacity
            geom = tg["geom"] if tg else None
            line = cl.get((section, row))
            src = "scenarioE_tread" if tg else "composition_centreline"
            self.bands[(section, row)] = Band(
                section=section, row=row, zone=c["zone"], status=status,
                tread_elev=c["elev"], base_elev=c["elev"],
                axis_radius_ft=c["axis_radius_ft"], length_ft=c["length_ft"],
                seats=seats, base_seats=seats,
                cross_angle_deg=c["cross_angle_deg"],
                comp_c_mm=c["c_mm"], sees_bay=c["sees_bay"],
                geometry=geom, centreline=line, geometry_source=src,
            )

    # ── geometry helpers ───────────────────────────────────────────────────

    def band_footprint(self, band: Band):
        """Tread polygon if validated, else centreline buffered to tread depth."""
        if band.geometry is not None:
            return band.geometry
        if band.centreline is None:
            return None
        depth = self.tread_depth_ft(band)
        return band.centreline.buffer(depth / 2.0, cap_style=2)

    def tread_depth_ft(self, band: Band) -> float:
        prev = self.bands.get((band.section, band.row - 1))
        nxt = self.bands.get((band.section, band.row + 1))
        if prev is not None:
            return max(2.0, band.axis_radius_ft - prev.axis_radius_ft)
        if nxt is not None:
            return max(2.0, nxt.axis_radius_ft - band.axis_radius_ft)
        return 4.0

    def band_position(self, band: Band):
        g = band.geometry if band.geometry is not None else band.centreline
        if g is None:
            return None
        c = g.centroid
        return (c.x, c.y)

    # ── audience frame (no shared arc centre — seat-weighted, from stage) ──

    def seated_bands(self, statuses=("formal",)) -> list[Band]:
        return [b for b in self.bands.values()
                if b.status in statuses and b.seats > 0]

    def audience_centroid(self, statuses=("formal",)) -> tuple[float, float] | None:
        pts, wts = [], []
        for b in self.seated_bands(statuses):
            pos = self.band_position(b)
            if pos is None:
                continue
            pts.append(pos)
            wts.append(b.seats)
        if not pts:
            return None
        w = np.array(wts, float)
        xy = np.array(pts, float)
        cx, cy = (xy * w[:, None]).sum(axis=0) / w.sum()
        return float(cx), float(cy)

    def stage_alignment(self) -> dict:
        """Angular mismatch + lateral offset of the audience mass vs stage axis."""
        cen = self.audience_centroid()
        if cen is None:
            return {"axis_mismatch_deg": None, "lateral_offset_ft": None}
        sfx, sfy = self.stage["sf_x"], self.stage["sf_y"]
        ax = self.stage["axis_az"]
        dx, dy = cen[0] - sfx, cen[1] - sfy
        bearing = math.degrees(math.atan2(dx, dy)) % 360.0
        mismatch = ((ax - bearing + 180.0) % 360.0) - 180.0
        dist = math.hypot(dx, dy)
        lateral = dist * math.sin(math.radians(bearing - ax))
        return {
            "audience_centroid": [round(cen[0], 1), round(cen[1], 1)],
            "centroid_bearing_deg": round(bearing, 1),
            "stage_axis_deg": ax,
            "axis_mismatch_deg": round(mismatch, 1),
            "lateral_offset_ft": round(lateral, 1),
            "sf_to_centroid_ft": round(dist, 1),
            "rule9_status": self.stage.get("rule9_status", "open"),
            "stage_name": self.stage.get("name"),
        }

    # ── sightlines: per-section radial C solver ───────────────────────────
    #
    # Same model that produced composition_table C_mm (verified: east row 4
    # reproduces 207 mm exactly): D = axis_radius - 50, E = tread + 3.94
    # - 612.5, C = E·(Dp/D) − Ep against the previous SEATED row (promenade /
    # aisle gaps enlarge C exactly as in the composition table).

    def compute_c_values(self) -> dict[tuple[str, int], float | None]:
        out: dict[tuple[str, int], float | None] = {}
        for section in SECTIONS:
            rows = sorted(b.row for b in self.bands.values()
                          if b.section == section and b.status not in ("trimmed",))
            prev: Band | None = None
            for row in rows:
                b = self.bands[(section, row)]
                if b.status in ("promenade", "aisle", "lawn"):
                    out[(section, row)] = None
                    continue
                if prev is None:
                    out[(section, row)] = None   # row 1: no upstream head
                else:
                    D = b.axis_radius_ft - STAGE_R_FT
                    Dp = prev.axis_radius_ft - STAGE_R_FT
                    E = b.tread_elev + EYE_HT_FT - FOCUS_ELEV
                    Ep = prev.tread_elev + EYE_HT_FT - FOCUS_ELEV
                    c_ft = E * (Dp / D) - Ep
                    out[(section, row)] = round(c_ft * 304.8, 1)
                prev = b
        return out

    def ideal_tread_profile(self, section: str, target_c_mm: float,
                            rows: list[int] | None = None) -> dict[int, float]:
        """Solve the minimum tread elevations that achieve target C for every
        seated row in a section (the 'reference geometry' profile).

        Never lowers row 1 below its current tread (the floor pocket is fixed
        by the event floor / drainage datum).
        """
        c_ft = target_c_mm / 304.8
        all_rows = sorted(b.row for b in self.bands.values()
                          if b.section == section and b.status not in ("trimmed",))
        if rows is None:
            rows = all_rows
        profile: dict[int, float] = {}
        prev: tuple[float, float] | None = None   # (D, E)
        for row in all_rows:
            b = self.bands[(section, row)]
            if b.status in ("promenade", "aisle", "lawn"):
                continue
            D = b.axis_radius_ft - STAGE_R_FT
            if prev is None:
                elev = b.tread_elev
            else:
                Dp, Ep = prev
                E_req = (c_ft + Ep) * (D / Dp)
                elev = FOCUS_ELEV + E_req - EYE_HT_FT
                if row not in rows:
                    elev = b.tread_elev   # untouched row keeps its grade
            profile[row] = round(elev, 2)
            prev = (D, profile[row] + EYE_HT_FT - FOCUS_ELEV)
        return {r: e for r, e in profile.items() if r in rows}

    # ── summaries ──────────────────────────────────────────────────────────

    def section_stats(self) -> dict:
        out = {}
        for s in SECTIONS:
            bands = [b for b in self.bands.values()
                     if b.section == s and b.status == "formal"]
            out[s] = {
                "formal_rows": len(bands),
                "formal_seats": sum(b.seats for b in bands),
                "arc_ft": round(sum(b.length_ft for b in bands), 0),
            }
        seats = [v["formal_seats"] for v in out.values()]
        out["balance_ratio_seats"] = round(min(seats) / max(seats), 2) if max(seats) else 0
        arcs = [v["arc_ft"] for v in out.values() if isinstance(v, dict)] if False else \
               [out[s]["arc_ft"] for s in SECTIONS]
        out["balance_ratio_arc"] = round(min(arcs) / max(arcs), 2) if max(arcs) else 0
        return out

    def log_op(self, op: str, **kw):
        self.ops_log.append({"op": op, **kw})
