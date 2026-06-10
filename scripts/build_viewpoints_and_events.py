#!/usr/bin/env python3
"""Viewpoints + event-mode overlays for the in-situ package.

  vectors_geojson/in_situ_viewpoints.geojson  six named camera stations with
      camera point, look target (xy + elev), eye height, look azimuth/distance,
      and intended render filename (renders/<name>.png)
  vectors_geojson/event_modes.geojson         six schematic, NONBINDING event
      overlays (empty park day, small civic ceremony, movie night, amplified
      concert, festival spillover, winter/off-season)

Camera elevations sample dem/dem_design_1ft.tif when it is present; when the
DEM is absent (fresh checkout — rasters are gitignored) terrain-dependent
cameras fall back to documented estimates from tracked values and say so in
`camera_elev_source`. Design-surface cameras (treads, stage, floor) never
need the DEM.

EPSG:6494, NAVD88 intl ft. Run after build_in_situ_geometry.py.
"""
import json
import math
import os

from shapely.geometry import shape, Point
from shapely.ops import unary_union

import in_situ_common as C
from build_in_situ_geometry import rounded

BAY_PLANE = 579.45  # measured Little Traverse Bay water plane (EPT)


def dem_sampler():
    if not os.path.exists(C.DEM_DESIGN):
        return None
    import numpy as np
    import rasterio
    from rasterio.transform import rowcol

    ds = rasterio.open(C.DEM_DESIGN)
    A = ds.read(1).astype(float)
    A[A == ds.nodata] = np.nan
    T = ds.transform

    def elev(x, y):
        r, c = rowcol(T, x, y)
        if 0 <= r < A.shape[0] and 0 <= c < A.shape[1]:
            v = A[r, c]
            return None if not np.isfinite(v) else float(v)
        return None

    return elev


def main():
    layers = C.verify_against_design()
    rows = {f["properties"]["row"]: f["properties"] for f in layers["rows"]}
    floor = {f["properties"]["name"]: f for f in layers["floor"]}
    elev = dem_sampler()

    cell = shape(floor["treatment_wet_cell"]["geometry"])
    cell_c = cell.centroid
    pour = json.load(open(os.path.join(C.REPO, "pour_point.geojson")))["features"][0]
    pour_xy = pour["geometry"]["coordinates"]
    spill = pour["properties"]["spill_elev_ft_navd88"]

    # stage centre: between downstage (R=50) and upstage (R=16) edges on axis
    stage_cx, stage_cy = C.polar(C.STAGE_R - 17.0, C.AX_AZ)
    mid_row = 8
    mid_R = rows[mid_row]["radius_ft"]
    mid_tread = rows[mid_row]["tread_elev_navd88"]
    top_tread = rows[C.N_ROWS]["tread_elev_navd88"]
    aisle_row = 9
    aisle_R = rows[aisle_row]["radius_ft"]
    aisle_tread = rows[aisle_row]["tread_elev_navd88"]

    def ground(x, y, fallback, what):
        """DEM sample with documented fallback."""
        if elev is not None:
            v = elev(x, y)
            if v is not None:
                return round(v, 2), "dem_design_1ft.tif"
        return round(fallback, 2), f"fallback_estimate ({what}; DEM missing or nodata)"

    vps = []

    def vp(name, cam_xy, cam_ground, ground_src, eye_ft, tgt_xy, tgt_elev,
           required, desc, note=""):
        az = (math.degrees(math.atan2(tgt_xy[0] - cam_xy[0],
                                      tgt_xy[1] - cam_xy[1]))) % 360.0
        dist = math.hypot(tgt_xy[0] - cam_xy[0], tgt_xy[1] - cam_xy[1])
        vps.append(C.feat(
            {
                "name": name,
                "description": desc,
                "camera_elev_navd88": round(cam_ground + eye_ft, 2),
                "camera_ground_elev_navd88": cam_ground,
                "camera_elev_source": ground_src,
                "eye_height_ft": eye_ft,
                "look_target_x": round(tgt_xy[0], 2),
                "look_target_y": round(tgt_xy[1], 2),
                "look_target_elev_navd88": round(tgt_elev, 2),
                "look_azimuth_deg": round(az, 1),
                "look_distance_ft": round(dist, 1),
                "fov_deg_suggested": 60,
                "render_file": f"renders/{name}.png",
                "required": required,
                "note": note,
                "datum": "NAVD88 Geoid12A intl ft",
            },
            {"type": "Point", "coordinates": [round(cam_xy[0], 2), round(cam_xy[1], 2)]},
        ))

    # 1 — upper rim looking down to the stage
    rim_xy = C.polar(150.0, C.AX_AZ)
    rim_g, rim_src = ground(*rim_xy, fallback=top_tread + 0.30 * (150.0 - (C.R_OUTER + C.TREAD)),
                            what="top tread + 30% natural rake")
    vp("upper_rim_down_to_stage", rim_xy, rim_g, rim_src, C.EYE_STANDING_FT,
       (stage_cx, stage_cy), C.FOCUS_ELEV + 2.0, True,
       "standing above the last row on the centreline, the whole 110-degree fan and "
       "low stage below, bay beyond",
       note="camera 17 ft behind the top tread on existing slope")

    # 2 — REQUIRED: mid-row audience toward stage AND bay
    cam_xy = C.polar(mid_R + 1.0, C.AX_AZ)
    bay_xy = C.polar(660.0, C.FACE_AZ, C.SFX, C.SFY)
    vp("mid_row_audience_to_bay", cam_xy, mid_tread, "tread_elev (design surface)",
       C.EYE_SEATED_FT, bay_xy, BAY_PLANE, True,
       "seated at row 8 centre: performer at 71 ft, dry treatment cell as scenic "
       "foreground, Little Traverse Bay + sky as the backdrop",
       note="the governing view — stage must stay low/open; no upstage shell")

    # 3 — stage looking back to audience
    aud_xy = C.polar(mid_R, C.AX_AZ)
    vp("stage_looking_back_to_audience", (stage_cx, stage_cy), C.FOCUS_ELEV,
       "stage deck (design surface)", C.EYE_STANDING_FT,
       aud_xy, mid_tread + C.EYE_SEATED_FT, False,
       "performer's view: 16 turf terraces rising ~15 ft on the natural rake, "
       "framed by the lateral shoulders")

    # 4 — ADA arrival to the cross-aisle
    ada_top = C.polar(C.R_OUTER + 25.0, C.AX_AZ + C.FAN_HALF)
    ada_g, ada_src = ground(*ada_top, fallback=aisle_tread + 4.0,
                            what="cross-aisle tread + ramp drop")
    aisle_mid = C.polar(aisle_R, C.AX_AZ + C.FAN_HALF / 2)
    vp("ada_arrival_to_cross_aisle", ada_top, ada_g, ada_src, C.EYE_STANDING_FT,
       aisle_mid, aisle_tread + 2.0, False,
       "arriving on accessible Route B: the level cross-aisle and wheelchair "
       "dispersion band at row 9, bowl opening beyond")

    # 5 — outside the bowl, from the park edge
    park_g, park_src = ground(pour_xy[0], pour_xy[1], fallback=spill,
                              what="basin spill elevation at pour point")
    vp("outside_bowl_from_park_edge", tuple(pour_xy), park_g, park_src,
       C.EYE_STANDING_FT, (stage_cx, stage_cy), C.FOCUS_ELEV + 2.0, False,
       "from the NE rim / park edge: the bowl reads as landscape, terraces "
       "almost invisible until the rim line")

    # 6 — event floor toward the treatment cell
    floor_xy = C.polar(C.STAGE_R + 17.0, C.AX_AZ)
    vp("event_floor_to_treatment_cell", floor_xy, C.FOCUS_ELEV,
       "event floor (design surface)", C.EYE_STANDING_FT,
       (cell_c.x, cell_c.y), C.TREATMENT_BOTTOM + 1.0, False,
       "standing on the forecourt: past the stage shoulder to the dry "
       "bioretention meadow — ephemeral water only, never a pool")

    C.dump(C.fc(vps), os.path.join(C.VEC_DIR, "in_situ_viewpoints.geojson"))

    # ── event modes (schematic, nonbinding) ─────────────────────────────────
    treads = json.load(open(os.path.join(C.VEC_DIR, "terrace_treads.geojson")))["features"]
    tread_union = unary_union([shape(f["geometry"]) for f in treads]).simplify(0.5)
    forecourt = shape(floor["event_floor_forecourt"]["geometry"])
    stage_poly = shape(floor["stage"]["geometry"])

    modes = []

    def ev(mode, name, geom, **props):
        modes.append(C.feat(dict(mode=mode, name=name, schematic=True,
                                 nonbinding=True, **props), geom))

    ev("empty_park_day", "park_terraces_passive",
       rounded(tread_union),
       use="open park terraces — sitting, lunch, reading; no programme",
       temporary_structures="none")
    ev("empty_park_day", "floor_open_lawn", rounded(forecourt),
       use="open floor; informal play", temporary_structures="none")

    ev("small_civic_ceremony", "ceremony_stage", rounded(stage_poly),
       use="speakers / colour guard", attendance_hint="50-250",
       temporary_structures="lectern, flags")
    ev("small_civic_ceremony", "ceremony_seating",
       rounded(unary_union([shape(f["geometry"]) for f in treads[:4]]).simplify(0.5)),
       use="front four rows + forecourt folding chairs",
       temporary_structures="folding chairs on forecourt")

    screen = [[round(v, 2) for v in C.polar(C.STAGE_R - C.TREAD, lat_az)]
              for lat_az in (C.AX_AZ - 14, C.AX_AZ + 14)]
    ev("movie_night", "temporary_screen_line",
       {"type": "LineString", "coordinates": screen},
       use="inflatable screen across the stage, rigged after sunset, struck same night",
       temporary_structures="inflatable screen + projector",
       note="night-only: never a permanent view obstruction in the bay corridor")
    ev("movie_night", "blanket_seating", rounded(tread_union),
       use="blanket seating on terraces + forecourt", attendance_hint="300-800",
       temporary_structures="projector table")

    pa = [C.polar(rows[6]["radius_ft"], C.AX_AZ - C.FAN_HALF),
          C.polar(rows[6]["radius_ft"], C.AX_AZ + C.FAN_HALF)]
    ev("amplified_concert", "concert_stage_and_pa", rounded(stage_poly),
       use="amplified performance; PA on stage wings",
       temporary_structures="line arrays on stage corners, FOH mix at row 8 centre",
       note="sound aimed up-fan (SSE) away from the bay; curfew per ordinance")
    for i, p in enumerate(pa):
        ev("amplified_concert", f"delay_speaker_{i + 1}",
           {"type": "Point", "coordinates": [round(p[0], 2), round(p[1], 2)]},
           use="delay/fill speaker on portable stand", temporary_structures="speaker stand")

    ev("festival_spillover", "spillover_upper_slope",
       rounded(shape({"type": "Polygon",
                      "coordinates": [C.annular_sector(C.R_OUTER + C.TREAD, 160.0)]})),
       use="overflow blanket ground on the upper slope (no grading — existing rake)",
       temporary_structures="none")
    ev("festival_spillover", "vendor_line_rim",
       rounded(shape({"type": "Polygon",
                      "coordinates": [C.annular_sector(165.0, 180.0, fan_half=40.0)]})),
       use="vendor stalls along the rim arrival edge", temporary_structures="pop-up tents")

    ev("winter_offseason", "winter_passive_bowl", rounded(tread_union),
       use="passive winter landscape — terraces hold snow lines; furnishings removed",
       temporary_structures="none",
       note="stage deck cleared and snow-shed; treatment cell dormant meadow")

    C.dump(C.fc(modes, extra={"nonbinding": True}),
           os.path.join(C.VEC_DIR, "event_modes.geojson"))


if __name__ == "__main__":
    main()
