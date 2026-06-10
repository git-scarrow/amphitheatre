#!/usr/bin/env python3
"""Shared constants + helpers for the in-situ design package.

Source of truth is the tracked Open Civic Bowl geometry in design_open_low/
(seating_rows.geojson, stage_floor.geojson, ada_route.geojson). The constants
below restate the generator parameters of scripts/design_open_low.py;
verify_against_design() cross-checks them against the tracked GeoJSON and
raises on any drift, so the in-situ package can never silently diverge from
the design of record.

Planning-grade. NAVD88 (Geoid12A) intl ft. CRS EPSG:6494.
"""
import json
import math
import os

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── canonical Open Civic Bowl parameters (design_open_low.py) ───────────────
CX, CY = 19533067.7, 750799.2          # base point
AX_AZ = 150.0                          # seating centreline azimuth (from arc centre)
FACE_AZ = (AX_AZ + 180.0) % 360.0      # audience faces 330° (NNW: bay + evening sun)
F_T = 15.0                             # arc centre offset from base point
STAGE_R = 50.0                         # stage front / sightline focus, ft up-centreline
R_INNER, R_OUTER, TREAD = 85.0, 130.0, 3.0
FAN_HALF = 55.0                        # ±55° → 110° total fan
N_ROWS = 16
FOCUS_ELEV = 612.5                     # event floor / stage NAVD88 ft
TREATMENT_BOTTOM = 609.1               # dry/ephemeral treatment-cell bottom
EYE_SEATED_FT = 3.94
EYE_STANDING_FT = 5.2

DEM_DESIGN = os.path.join(REPO, "dem", "dem_design_1ft.tif")
DESIGN_DIR = os.path.join(REPO, "design_open_low")
VEC_DIR = os.path.join(REPO, "vectors_geojson")

CRS6494 = {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::6494"}}


def U(az_deg):
    a = math.radians(az_deg)
    return math.sin(a), math.cos(a)


_UX, _UY = U(AX_AZ)
FX, FY = CX + _UX * F_T, CY + _UY * F_T                  # seating arc centre
SFX, SFY = FX + _UX * STAGE_R, FY + _UY * STAGE_R        # stage front / focus


def polar(R, az_deg, ox=FX, oy=FY):
    e, n = U(az_deg)
    return ox + e * R, oy + n * R


def arc_coords(R, fan_half=FAN_HALF, n=81, az0=AX_AZ):
    return [
        [round(polar(R, az)[0], 2), round(polar(R, az)[1], 2)]
        for az in np.linspace(az0 - fan_half, az0 + fan_half, n)
    ]


def annular_sector(r_in, r_out, fan_half=FAN_HALF, n=81, az0=AX_AZ):
    """Closed polygon ring: outer arc forward, inner arc reversed."""
    outer = arc_coords(r_out, fan_half, n, az0)
    inner = arc_coords(r_in, fan_half, n, az0)
    return outer + inner[::-1] + [outer[0]]


def fc(features, extra=None):
    out = {"type": "FeatureCollection", "crs": CRS6494, "features": features}
    if extra:
        out.update(extra)
    return out


def feat(props, geom):
    return {"type": "Feature", "properties": props, "geometry": geom}


def load_design(name):
    with open(os.path.join(DESIGN_DIR, name)) as fh:
        return json.load(fh)


def dump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=1)
    print(f"  wrote {os.path.relpath(path, REPO)}")


def verify_against_design():
    """Cross-check the restated constants against the tracked design layers."""
    rows = load_design("seating_rows.geojson")["features"]
    assert len(rows) == N_ROWS, f"expected {N_ROWS} rows, found {len(rows)}"
    radii = [f["properties"]["radius_ft"] for f in rows]
    assert abs(radii[0] - R_INNER) < 0.01 and abs(radii[-1] - R_OUTER) < 0.01, (
        f"row radii {radii[0]}..{radii[-1]} != {R_INNER}..{R_OUTER}"
    )
    assert abs(rows[0]["properties"]["dist_to_stage_ft"] - (R_INNER - STAGE_R)) < 0.11, (
        "row-1 distance to stage front drifted from 35 ft"
    )
    # arc endpoints/midpoint of row 1 must sit on the restated centre/azimuths
    coords = rows[0]["geometry"]["coordinates"]
    for az, pt in ((AX_AZ - FAN_HALF, coords[0]),
                   (AX_AZ, coords[len(coords) // 2]),
                   (AX_AZ + FAN_HALF, coords[-1])):
        ex, ey = polar(radii[0], az)
        err = math.hypot(pt[0] - ex, pt[1] - ey)
        assert err < 0.05, f"row-1 arc point at az {az} off by {err:.3f} ft"
    floor = load_design("stage_floor.geojson")["features"]
    focus = next(f for f in floor if f["properties"]["name"] == "focal_point_stage_front")
    px, py = focus["geometry"]["coordinates"]
    assert math.hypot(px - SFX, py - SFY) < 0.05, "stage front drifted from constants"
    assert abs(focus["properties"]["audience_face_az_deg"] - FACE_AZ) < 0.01
    assert abs(focus["properties"]["elev_navd88"] - FOCUS_ELEV) < 0.01
    cell = next(f for f in floor if f["properties"]["name"] == "treatment_wet_cell")
    assert abs(cell["properties"]["bottom_navd88"] - TREATMENT_BOTTOM) < 0.01
    return {"rows": rows, "floor": floor}


if __name__ == "__main__":
    verify_against_design()
    print(f"OK — constants match design_open_low/ (fan ±{FAN_HALF:.0f}°, "
          f"{N_ROWS} rows R{R_INNER:.0f}–{R_OUTER:.0f}, audience faces {FACE_AZ:.0f}°)")
