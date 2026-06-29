#!/usr/bin/env python3
"""Shared definitions for the terrain-operation ledger ("agentic clay").

This module is the single source of truth for:

  * the op_id naming scheme,
  * the surface-class taxonomy (existing/no-touch, cut, fill, cap, tread,
    riser, drainage, ada, stage),
  * the construction-material vocabulary (timber/precast caps, gravel-fines
    treads, planted risers, gravel drainage, stabilized ADA, low open stage),
  * the debug-view colour palette keyed to surface class, and
  * the pure-geometry helpers (circle fit, radial band extraction,
    point-in-polygon) used to turn the Open Civic Bowl row centrelines into
    explicit engineered terrace surfaces.

Design intent
-------------
Every *visible* earthform in the Unreal scene must trace to one operation in
``design/terrain_ops.current.json``.  The visible terrain is therefore not
sculpted in Unreal and is not a single span that the seats sit on top of (the
old "grass over the seats" failure) -- it is generated, surface by surface,
from auditable operations defined here.

Dependencies: stdlib + numpy only.  No rasterio / shapely / geopandas, so the
generator and validator run on a fresh checkout where the LiDAR DEM and the
GIS stack are absent (mirrors the repo's existing missing-data tolerance).

CRS EPSG:6494 (intl ft), datum NAVD88 Geoid12A intl ft.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESIGN_SRC = os.path.join(REPO, "design_open_low")
DESIGN_DIR = os.path.join(REPO, "design")
GEO_OUT = os.path.join(REPO, "unreal_export", "geo", "terrace_ops")
MANIFEST_DIR = os.path.join(REPO, "unreal_export", "manifests")

CRS = "EPSG:6494"
DATUM = "NAVD88 Geoid12A intl ft"
SCHEMA = "amphitheatre/terrain-ops/0.2"

# ---------------------------------------------------------------------------
# Accepted Open Civic Bowl invariants (hard constraints, asserted by the
# validator -- never silently relaxed).
# ---------------------------------------------------------------------------
INVARIANTS = {
    "design": "open_civic_bowl",
    "rows": 16,
    "fan_half_angle_deg": 55.0,          # +/-55 deg  -> 110 deg total arc
    "fan_total_angle_deg": 110.0,
    "audience_face_az_deg": 330.0,        # NNW toward Little Traverse Bay
    "stage_forward": True,
    "low_open_bay_facing": True,
    "default_retaining_walls": False,
    # a riser taller than this would read as an engineered wall, not a planted
    # seeded slope; the bowl is explicitly wall-free by default.
    "wall_trigger_ft": 2.0,
}

# Radial section of one row terrace, inner (down-slope, toward stage) -> outer
# (up-slope, back of row).  Widths in feet; they sum to the ~3 ft row pitch.
# This is the engineered cross-section that replaces "bare graded slope":
#   riser face | foot tread | seat cap | drainage edge | terrain transition
BAND_PLAN = [
    ("riser",      0.50),   # near-vertical planted/seeded face up from row below
    ("tread",      1.40),   # walkable compacted gravel-fines foot tread
    ("cap",        0.60),   # timber / light-precast seat cap at back of tread
    ("drainage",   0.30),   # gravel drainage strip at the up-slope edge
    ("transition", 0.20),   # graded feather tying the plate back to existing grade
]
DEFAULT_PITCH_FT = 3.0
DRAINAGE_DROP_FT = 0.30     # drainage strip sits this far below the tread plate
ADA_PATH_WIDTH_FT = 5.0     # stabilized accessible path full width

# ---------------------------------------------------------------------------
# Surface taxonomy: surface_class -> debug colour + the construction material
# that communicates *how* the surface is built (criterion 7).
# ---------------------------------------------------------------------------
SURFACE_CLASSES = {
    # class            debug_color  material_key        material label
    "existing_no_touch": ("#9e9e9e", "existing_ground",  "Existing ground - no touch (LiDAR)"),
    "cut":               ("#2166ac", "graded_cut",       "Cut to design plate"),
    "fill":              ("#b2182b", "graded_fill",      "Engineered fill to design plate"),
    "cap":               ("#5d4037", "timber_precast_cap", "Seat cap - timber / light precast"),
    "tread":             ("#cdbfa6", "gravel_fines_tread", "Foot tread - compacted gravel fines"),
    "riser":             ("#7cb342", "planted_riser",    "Riser face - planted / seeded slope"),
    "drainage":          ("#26a69a", "gravel_drainage",  "Drainage strip - open gravel"),
    "ada":               ("#1565c0", "stabilized_ada",   "ADA route - stabilized aggregate"),
    "stage":             ("#a1887f", "stage_open_low",   "Stage / floor - low open deck"),
}

# Surface classes whose footprint terrain material must NOT draw over.  These
# are the constructed wear surfaces; only ``transition`` (and bare ground) is
# where engineered grade is allowed to meet existing terrain.
CLIPPED_CLASSES = ("cap", "tread", "riser", "drainage", "ada", "stage")

# Small vertical lift (ft) applied to constructed surfaces in Unreal so the
# clipped terrain can never z-fight up through a plate even at grazing camera
# angles.  Belt-and-suspenders on top of the geometric clip mask + the
# all_touched=True raster flattening already in build_proposed_grade.py.
RENDER_LIFT_FT = 0.02


def material_table() -> dict:
    """material_key -> {label, debug_color, surface_class}."""
    out = {}
    for sclass, (color, mkey, label) in SURFACE_CLASSES.items():
        out[mkey] = {"label": label, "debug_color": color, "surface_class": sclass}
    return out


def debug_palette() -> dict:
    """surface_class -> hex colour for the op_id / surface debug view."""
    return {s: c for s, (c, _m, _l) in SURFACE_CLASSES.items()}


# ---------------------------------------------------------------------------
# GeoJSON IO (stdlib json; geometry kept as plain coordinate lists).
# ---------------------------------------------------------------------------
def load_geojson(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)


def feature_collection(features: list) -> dict:
    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": f"urn:ogc:def:crs:EPSG::6494"}},
        "features": features,
    }


def polygon_feature(ring: np.ndarray, props: dict) -> dict:
    coords = [[round(float(x), 2), round(float(y), 2)] for x, y in ring]
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    return {"type": "Feature", "properties": props,
            "geometry": {"type": "Polygon", "coordinates": [coords]}}


# ---------------------------------------------------------------------------
# Geometry helpers (pure numpy).
# ---------------------------------------------------------------------------
def fit_circle(xy: np.ndarray) -> tuple:
    """Kasa algebraic circle fit. Returns (cx, cy, R)."""
    x, y = xy[:, 0], xy[:, 1]
    A = np.column_stack([2 * x, 2 * y, np.ones_like(x)])
    b = x * x + y * y
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy, c = sol
    R = math.sqrt(max(c + cx * cx + cy * cy, 0.0))
    return float(cx), float(cy), float(R)


def bowl_center(rows: list) -> tuple:
    """Common concentric centre of the row arcs (mean of per-row fits)."""
    cs = []
    for f in rows:
        xy = np.asarray(f["geometry"]["coordinates"], dtype=float)
        if len(xy) >= 3:
            cx, cy, _ = fit_circle(xy)
            cs.append((cx, cy))
    cs = np.asarray(cs)
    return float(cs[:, 0].mean()), float(cs[:, 1].mean())


def arc_at_radius(arc_xy: np.ndarray, center: tuple, radius: float) -> np.ndarray:
    """Re-project an arc polyline to a new radius about ``center``."""
    c = np.asarray(center, dtype=float)
    v = arc_xy - c
    r = np.hypot(v[:, 0], v[:, 1])
    u = v / r[:, None]
    return c + u * radius


def band_polygon(arc_xy: np.ndarray, center: tuple,
                 r_inner: float, r_outer: float) -> np.ndarray:
    """Annular band between two radii as a closed ring (inner fwd, outer rev)."""
    inner = arc_at_radius(arc_xy, center, r_inner)
    outer = arc_at_radius(arc_xy, center, r_outer)
    return np.vstack([inner, outer[::-1]])


def buffer_line(line_xy: np.ndarray, width_ft: float) -> np.ndarray:
    """Flat rectangular buffer of a 2-point (or polyline) line, full width."""
    pts = np.asarray(line_xy, dtype=float)
    left, right = [], []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        d = b - a
        n = np.array([-d[1], d[0]])
        nn = np.hypot(*n)
        n = n / nn if nn else np.array([0.0, 0.0])
        left.append(pts[i] + n * width_ft / 2.0)
        right.append(pts[i] - n * width_ft / 2.0)
    return np.vstack([np.asarray(left), np.asarray(right)[::-1]])


def point_in_ring(pt, ring) -> bool:
    """Ray-cast point-in-polygon for a single ring (list/array of xy)."""
    x, y = float(pt[0]), float(pt[1])
    ring = np.asarray(ring, dtype=float)
    n = len(ring)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and \
           (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def ring_contains_ring(outer_ring, inner_ring, sample=None) -> bool:
    """True if every vertex of inner_ring lies inside outer_ring."""
    pts = np.asarray(inner_ring, dtype=float)
    if sample and len(pts) > sample:
        idx = np.linspace(0, len(pts) - 1, sample).astype(int)
        pts = pts[idx]
    return all(point_in_ring(p, outer_ring) for p in pts)


def az_deg(center: tuple, pt) -> float:
    """Compass azimuth (deg, 0=N, CW) from center to point."""
    dx = float(pt[0]) - center[0]
    dy = float(pt[1]) - center[1]
    return (math.degrees(math.atan2(dx, dy))) % 360.0
