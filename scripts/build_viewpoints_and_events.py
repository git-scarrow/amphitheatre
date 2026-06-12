#!/usr/bin/env python3
"""Viewpoints + event-mode overlays for the three-section civic bowl.

  vectors_geojson/in_situ_viewpoints.geojson  six camera stations (camera
      point, look target xy+elev, eye height, azimuth/distance, render file);
      the REQUIRED mid_row_audience_to_bay sits on the BEND (southeast)
      section row 8 and looks over the low stage to Little Traverse Bay
  vectors_geojson/event_modes.geojson         six schematic NONBINDING modes

Camera elevations sample dem/dem_design_1ft.tif when present; otherwise
terrain-dependent cameras fall back to documented estimates from tracked
values (composition elevations, ramp drops, basin spill) and say so in
`camera_elev_source`. EPSG:6494, NAVD88 intl ft.
"""
import json
import math
import os

import numpy as np
from shapely.geometry import shape, LineString
from shapely.ops import unary_union

import in_situ_common as C
from build_in_situ_geometry import rounded


def dem_sampler():
    if not os.path.exists(C.DEM_DESIGN):
        return None
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


def load_vec(name):
    with open(os.path.join(C.VEC_DIR, name)) as fh:
        return json.load(fh)["features"]


def main():
    layers = C.verify_against_design()
    comp = layers["comp"]
    elev = dem_sampler()

    treads = load_vec("terrace_treads.geojson")
    zfeats = load_vec("bowl_zones.geojson")
    zones = {}
    for f in zfeats:
        zones.setdefault(f["properties"]["zone"], []).append(f)

    def tread(sec, row):
        return next(f for f in treads
                    if f["properties"]["section"] == sec
                    and f["properties"]["row"] == row)

    stage_union = unary_union([shape(zones[z][0]["geometry"])
                               for z in ("stage_core", "stage_shoulder_left",
                                         "stage_shoulder_right")])
    stage_c = stage_union.centroid
    cell_c = shape(zones["treatment_cell_landscape"][0]["geometry"]).centroid
    aisle_c = shape(zones["cross_aisle"][0]["geometry"]).centroid
    orch_c = shape(zones["orchestra_event_floor"][0]["geometry"]).centroid
    pour = json.load(open(os.path.join(C.REPO, "pour_point.geojson")))["features"][0]
    pour_xy = pour["geometry"]["coordinates"]
    spill = pour["properties"]["spill_elev_ft_navd88"]

    def centroid_of(sec, row):
        c = shape(tread(sec, row)["geometry"]).centroid
        return c.x, c.y

    def comp_elev(sec, row):
        return float(comp[(row, sec)]["elev"])

    def ground(x, y, fallback, what):
        if elev is not None:
            v = elev(x, y)
            if v is not None:
                return round(v, 2), "dem_design_1ft.tif"
        return round(fallback, 2), f"fallback_estimate ({what}; DEM missing or nodata)"

    vps = []

    def vp(name, cam_xy, cam_ground, ground_src, eye_ft, tgt_xy, tgt_elev,
           required, desc, note=""):
        az = math.degrees(math.atan2(tgt_xy[0] - cam_xy[0],
                                     tgt_xy[1] - cam_xy[1])) % 360.0
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
            {"type": "Point",
             "coordinates": [round(cam_xy[0], 2), round(cam_xy[1], 2)]},
        ))

    # 1 — upper rim above the bend section, down to the stage
    bx, by = centroid_of("bend", 18)
    dx, dy = bx - stage_c.x, by - stage_c.y
    n = math.hypot(dx, dy)
    rim_xy = (bx + dx / n * 20.0, by + dy / n * 20.0)
    rim_g, rim_src = ground(*rim_xy,
                            fallback=comp_elev("bend", 18) + 0.30 * 20.0,
                            what="bend row-18 tread + 30% rake")
    vp("upper_rim_down_to_stage", rim_xy, rim_g, rim_src, C.EYE_STANDING_FT,
       (stage_c.x, stage_c.y), C.FOCUS_ELEV + 2.0, True,
       "standing above the bend (southeast) section's last row: three "
       "terrain-fitted seating families step down to the low stage, bay beyond",
       note="camera 20 ft behind the bend row-18 band on existing slope")

    # 2 — REQUIRED: bend-section mid-row toward stage AND bay
    cam_xy = centroid_of("bend", 8)
    bay_xy = C.polar(660.0, C.BAY_VIEW_AZ, stage_c.x, stage_c.y)
    vp("mid_row_audience_to_bay", cam_xy, comp_elev("bend", 8),
       "composition tread elev (design surface)", C.EYE_SEATED_FT,
       bay_xy, C.BAY_PLANE, True,
       "seated mid-bowl on the bend (southeast) section: performer below, "
       "dry treatment cell as scenic foreground, Little Traverse Bay + sky "
       "as the backdrop",
       note="the governing view — stage must stay low/open; no upstage shell; "
            "stage axis refit is OPEN (Rule 9) and must preserve this corridor")

    # 3 — stage looking back to the three sections
    aud_xy = centroid_of("bend", 12)
    vp("stage_looking_back_to_audience", (stage_c.x, stage_c.y), C.FOCUS_ELEV,
       "stage deck (design surface)", C.EYE_STANDING_FT,
       aud_xy, comp_elev("bend", 12) + C.EYE_SEATED_FT, False,
       "performer's view: east, bend and south families each curve with their "
       "own terrain — not one fan — rising ~15 ft around the floor")

    # 4 — ADA arrival to the cross-aisle (REBUILT network; the legacy
    # ada_ramp zones were REJECTED 2026-06-12 — quarantined in
    # vectors_geojson/legacy_ada_rejected.geojson). Camera sits ~40 ft back
    # along the rebuilt arrival route from its cross-aisle end.
    with open(os.path.join(C.REPO, "vectors_geojson",
                           "ada_route.geojson")) as fh:
        ada_fc = json.load(fh)
    arr = next(f for f in ada_fc["features"]
               if f["properties"].get("name") == "route_arrival_to_cross_aisle")
    arr_line = shape(arr["geometry"])
    cam_pt = arr_line.interpolate(max(arr_line.length - 40.0, 0.0))
    ada_g, ada_src = ground(cam_pt.x, cam_pt.y, fallback=C.AISLE_ELEV + 3.0,
                            what="rebuilt arrival route, 40 ft before the "
                                 "cross-aisle end")
    vp("ada_arrival_to_cross_aisle", (cam_pt.x, cam_pt.y), ada_g, ada_src,
       C.EYE_STANDING_FT, (aisle_c.x, aisle_c.y), C.AISLE_ELEV + 2.0, False,
       "arriving on the rebuilt accessible route (concept, pending civil "
       "detailing): the rows-9/10 cross-aisle — level, wheelable, with the "
       "mid-bowl view pause — opens below")

    # 5 — outside the bowl, from the park edge
    park_g, park_src = ground(pour_xy[0], pour_xy[1], fallback=spill,
                              what="basin spill elevation at pour point")
    vp("outside_bowl_from_park_edge", tuple(pour_xy), park_g, park_src,
       C.EYE_STANDING_FT, (stage_c.x, stage_c.y), C.FOCUS_ELEV + 2.0, False,
       "from the NE rim / park edge: the bowl reads as landscape; the "
       "contour-fitted bands disappear into the slope")

    # 6 — event floor toward the treatment cell
    vp("event_floor_to_treatment_cell", (orch_c.x, orch_c.y), C.FOCUS_ELEV,
       "event floor (design surface)", C.EYE_STANDING_FT,
       (cell_c.x, cell_c.y), C.TREATMENT_BOTTOM + 1.0, False,
       "standing on the orchestra floor: past the stage shoulder to the dry "
       "bioretention meadow — ephemeral water only, never a pool")

    C.dump(C.fc(vps), os.path.join(C.VEC_DIR, "in_situ_viewpoints.geojson"))

    # ── event modes (schematic, nonbinding) ─────────────────────────────────
    tread_union = unary_union([shape(f["geometry"]) for f in treads]).simplify(0.5)
    orchestra = shape(zones["orchestra_event_floor"][0]["geometry"])
    stage_poly = shape(zones["stage_core"][0]["geometry"])
    front_rows = unary_union([shape(tread(s, r)["geometry"])
                              for s in C.SECTIONS for r in (1, 2)]).simplify(0.5)
    shoulders = unary_union([shape(f["geometry"])
                             for f in zones["row_end_shoulder"]]).simplify(0.5)

    # downstage edge: stage-polygon side nearest the seating mass
    seat_c = tread_union.centroid
    ring = list(stage_poly.exterior.coords)
    seg = min((LineString([ring[i], ring[i + 1]]) for i in range(len(ring) - 1)),
              key=lambda s: s.centroid.distance(seat_c))

    modes = []

    def ev(mode, name, geom, **props):
        modes.append(C.feat(dict(mode=mode, name=name, schematic=True,
                                 nonbinding=True, **props), geom))

    ev("empty_park_day", "park_terraces_passive", rounded(tread_union),
       use="open park terraces — sitting, lunch, reading; no programme",
       temporary_structures="none")
    ev("empty_park_day", "floor_open_lawn", rounded(orchestra),
       use="open floor; informal play", temporary_structures="none")

    ev("small_civic_ceremony", "ceremony_stage", rounded(stage_poly),
       use="speakers / colour guard", attendance_hint="50-250",
       temporary_structures="lectern, flags")
    ev("small_civic_ceremony", "ceremony_seating", rounded(front_rows),
       use="front two rows of all three sections + orchestra folding chairs",
       temporary_structures="folding chairs on the orchestra floor")

    ev("movie_night", "temporary_screen_line", rounded(seg),
       use="inflatable screen across the stage, rigged after sunset, struck "
           "the same night",
       temporary_structures="inflatable screen + projector",
       note="night-only: never a permanent view obstruction in the bay corridor")
    ev("movie_night", "blanket_seating", rounded(tread_union),
       use="blanket seating on terraces + orchestra", attendance_hint="300-800",
       temporary_structures="projector table")

    ev("amplified_concert", "concert_stage_and_pa", rounded(stage_poly),
       use="amplified performance; PA on stage wings",
       temporary_structures="line arrays on stage corners, FOH mix on the "
                            "cross-aisle (bend section)",
       note="sound aimed up-fan (SE) away from the bay; curfew per ordinance")
    for sec in ("east", "south"):
        c = shape(tread(sec, 6)["geometry"]).centroid
        ev("amplified_concert", f"delay_speaker_{sec}",
           {"type": "Point", "coordinates": [round(c.x, 2), round(c.y, 2)]},
           use="delay/fill speaker on portable stand",
           temporary_structures="speaker stand")

    ev("festival_spillover", "spillover_shoulders_and_lawn", rounded(shoulders),
       use="overflow blanket ground on the row-end shoulders (landscape, "
           "no grading)",
       temporary_structures="none")
    rim = json.load(open(os.path.join(C.REPO, "basin_footprint.geojson")))
    rim_band = shape(rim["features"][0]["geometry"]).exterior.buffer(12.0)
    ev("festival_spillover", "vendor_line_rim", rounded(rim_band.simplify(0.5)),
       use="vendor stalls along the rim arrival edge",
       temporary_structures="pop-up tents")

    ev("winter_offseason", "winter_passive_bowl", rounded(tread_union),
       use="passive winter landscape — terraces hold snow lines; furnishings "
           "removed",
       temporary_structures="none",
       note="stage deck cleared and snow-shed; treatment cell dormant meadow")

    C.dump(C.fc(modes, extra={"nonbinding": True}),
           os.path.join(C.VEC_DIR, "event_modes.geojson"))


if __name__ == "__main__":
    main()
