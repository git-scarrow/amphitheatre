#!/usr/bin/env python3
"""Shared constants + figure geometry for the human-scale reference layer.

CALIBRATED SCHEMATIC HUMAN SCALE — not decorative entourage. Every visible
human figure (web viewer, boards) is generated from
vectors_geojson/human_scale_refs.geojson; nothing is hand-drawn. Heights are
exact in data units (ft); figure SHAPES are schematic silhouettes.

Height provenance (documented, not invented):

  standing 5.00 ft (60 in)  ≈ 5th-percentile US adult female stature
  standing 5.75 ft (69 in)  ≈ mean US adult male stature (CDC/NHANES)
  standing 6.25 ft (75 in)  ≈ 95th-percentile US adult male stature
  seated eye 3.94 ft (1200 mm) = THE repo sightline standard — the same
      EYE_SEATED_FT used by every C-value computation
      (scripts/in_situ_common.py); seated vertex = eye + 0.33 ft (~4 in)
  wheelchair eye 3.90 ft = centre of the 43-51 in occupied-adult-wheelchair
      eye-height range (US Access Board anthropometrics); vertex = eye + 0.33

Both board renderers and the audit gate import this module so the drawn
figures and the gate share one definition of "to scale".
"""
import math

import in_situ_common as C

REFS_PATH = "vectors_geojson/human_scale_refs.geojson"

STANDING_HEIGHTS_FT = (5.0, 5.75, 6.25)
SEATED_EYE_FT = C.EYE_SEATED_FT                 # 3.94 — C-value standard
SEATED_HEIGHT_FT = round(SEATED_EYE_FT + 0.33, 2)   # vertex ≈ eye + 4 in
WHEELCHAIR_EYE_FT = 3.90
WHEELCHAIR_HEIGHT_FT = round(WHEELCHAIR_EYE_FT + 0.33, 2)

HEIGHT_SOURCE = {
    "standing": "CDC/NHANES adult stature percentiles (5th F / mean M / 95th M)",
    "seated": "scripts/in_situ_common.py EYE_SEATED_FT=3.94 (1200 mm C-value "
              "standard); vertex = eye + 0.33 ft",
    "wheelchair": "US Access Board occupied-wheelchair eye height 43-51 in; "
                  "midpoint 3.90 ft; vertex = eye + 0.33 ft",
}

# every feature in the source layer must carry these
REQUIRED_HUMAN_FIELDS = (
    "ref_id", "type", "posture", "role", "height_ft", "view_context",
    "ground_elev_navd88", "ground_elev_source", "anchor", "scope",
    "geometry_anchor_source", "height_source", "blocks_bay_view",
)
REQUIRED_DIM_FIELDS = (
    "ref_id", "type", "length_ft", "label", "ground_elev_navd88",
    "geometry_anchor_source", "scope",
)

# placement ids the package is incomplete without (goal contract)
REQUIRED_PLACEMENTS = (
    "stage_front_performer", "center_stage",
    "row1_center_seated", "row1_center_standing",
    "row1_east_pocket", "row1_south_pocket",
    "row5_promenade",
    "cross_aisle_wheelchair", "cross_aisle_companion",
    "row18_upper_seated", "row18_upper_standing",
    "ada_landing_routeB_wheelchair", "ada_landing_routeA_standing",
    "lawn_overflow_edge", "treatment_cell_edge",
    "dim_stage_front_to_row1", "dim_pocket_east", "dim_pocket_south",
    "dim_scale_50ft",
)
# placements where a wheelchair/mobility ref is mandatory (ADA-critical)
ADA_CRITICAL_WHEELCHAIR = ("cross_aisle_wheelchair",
                           "ada_landing_routeB_wheelchair")


def _head_arc(cx, cz, r, a0, a1, n=10):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n),
             cz + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def figure_outline(posture, height_ft):
    """Closed 2-D silhouette for section drawings, as (dx, dz) vertices.

    dz runs from 0 (ground/tread) to EXACTLY height_ft at the head apex; dx
    is centred on 0. Board renderers translate these to (station, elev) and
    record the drawn vertical extent, which the audit gate compares to
    height_ft — so the figure cannot silently drift off scale.
    """
    h = float(height_ft)
    if posture == "standing":
        r = 0.085 * h                       # head radius
        shoulder_z, hip_w, shoulder_w = h - 2.05 * r, 0.10 * h, 0.135 * h
        pts = [(-hip_w * 0.6, 0.0), (-hip_w, 0.45 * h),
               (-shoulder_w, shoulder_z)]
        pts += _head_arc(0.0, h - r, r, math.pi, 0.0)   # over the top: apex z=h
        pts += [(shoulder_w, shoulder_z), (hip_w, 0.45 * h),
                (hip_w * 0.6, 0.0)]
        return pts
    if posture in ("seated", "wheelchair"):
        # side profile facing -x (toward the stage in our sections)
        r = 0.105 * h
        seat_z, knee_x, back_x = 0.32 * h, -0.42 * h, 0.16 * h
        pts = [(knee_x, 0.0), (knee_x - 0.05 * h, seat_z),
               (-0.10 * h, seat_z + 0.02 * h),
               (-0.12 * h, h - 2.0 * r)]
        pts += _head_arc(-0.02 * h, h - r, r, math.pi, 0.0)  # apex exactly at h
        pts += [(back_x, h - 2.2 * r), (back_x, seat_z), (knee_x + 0.16 * h, 0.0)]
        return pts
    raise ValueError(f"unknown posture {posture!r}")


def wheel_outline(n=24):
    """Wheelchair drive wheel: circle r=0.95 ft, axle 0.95 ft above ground.
    Drawn as a separate open ring behind the seated silhouette."""
    return [(0.30 + 0.95 * math.cos(2 * math.pi * i / n),
             0.95 + 0.95 * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]


def outline_extent_ft(pts):
    zs = [p[1] for p in pts]
    return max(zs) - min(zs)


# section-figure colours shared by every board renderer
FIG_FILL = {"standing": "#9c5b33", "seated": "#6d597a", "wheelchair": "#355070"}
PLAN_MARK = {"standing": ("o", "#9c5b33"), "seated": ("s", "#6d597a"),
             "wheelchair": ("D", "#355070")}

# refs snapped to their band's bend-axis station in section drawings
# (ref_id -> (bend row, along-axis stagger ft)); the cross-aisle pair sits
# where the level 622.01 band crosses the axis (rows 9/10, 117.1-121.4)
_SECTION_SNAP = {
    "row1_center_seated": (1, -1.2), "row1_center_standing": (1, 1.6),
    "row5_promenade": (5, 0.0),
    "row18_upper_seated": (18, -1.2), "row18_upper_standing": (18, 1.6),
}
_AISLE_STATION = {"cross_aisle_wheelchair": 118.6, "cross_aisle_companion": 120.6}


def section_station(ref_id, xy, comp):
    """Bend-axis station (ft from the axis origin) where a ref is drawn in
    a true-scale section, or None if the ref is plan-only (too far off the
    cut plane). Band-anchored refs snap to their band's axis radius; the
    cross-aisle pair sits on the level 622.01 band; near-axis refs project."""
    if ref_id in _SECTION_SNAP:
        row, off = _SECTION_SNAP[ref_id]
        return float(comp[(row, "bend")]["axis_radius_ft"]) + off
    if ref_id in _AISLE_STATION:
        return _AISLE_STATION[ref_id]
    if ref_id.startswith("ada_landing"):
        return None                       # plan-only (lateral switchbacks)
    ux, uy = C.U(C.AX_AZ)
    s = (xy[0] - C.FX) * ux + (xy[1] - C.FY) * uy
    lat = (xy[0] - C.FX) * uy - (xy[1] - C.FY) * ux
    return s if abs(lat) <= 25.0 else None


def draw_section_figure(ax, props, station, board, zorder=9):
    """Draw one to-scale figure on an equal-aspect section axes and return
    the audit record (drawn extent measured from the actual vertices)."""
    h, g = props["height_ft"], props["ground_elev_navd88"]
    pts = [(station + dx, g + dz)
           for dx, dz in figure_outline(props["posture"], h)]
    xs, zs = zip(*pts)
    ax.fill(xs, zs, color=FIG_FILL[props["posture"]], lw=0.4,
            ec="#2b2b28", alpha=0.95, zorder=zorder)
    if props["posture"] == "wheelchair":
        wx, wz = zip(*[(station + dx, g + dz) for dx, dz in wheel_outline()])
        ax.plot(wx, wz, color=FIG_FILL["wheelchair"], lw=0.7, zorder=zorder)
    if props.get("eye_height_ft") is not None:
        ax.plot([station - 1.3, station + 1.3],
                [g + props["eye_height_ft"]] * 2,
                color="#c0392b", lw=0.6, zorder=zorder + 1)
    return {"board": board, "ref_id": props["ref_id"],
            "posture": props["posture"], "height_ft": h,
            "drawn_height_ft": round(max(zs) - min(zs), 3),
            "station_ft": round(station, 1),
            "ground_elev_navd88": g}
