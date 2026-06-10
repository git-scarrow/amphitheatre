#!/usr/bin/env python3
"""In-situ geometry for the Open Civic Bowl.

Converts the tracked design_open_low/ layers into visible in-situ geometry:

  vectors_geojson/terrace_treads.geojson   16 annular tread polygons (turf terraces)
  vectors_geojson/terrace_edges.geojson    low seat-edge / terrace-edge arcs + riser heights
  vectors_geojson/bowl_zones.geojson       stage core, lateral shoulders, forecourt,
                                           ADA corridors, cross-aisle overlay,
                                           treatment-cell landscape, untouched slope
  vectors_geojson/{seating_rows,stage_floor,ada_route}.geojson  verbatim copies

The stage is a LOW OPEN DECK with lateral floor-level shoulders only — no back
wall, no upstage shell, no fly tower (the bay + sky are the backdrop). The
treatment cell is DRY/EPHEMERAL bioretention, never permanent water. Those
intent flags are written onto the features so scripts/audit_in_situ_package.py
can enforce them.

Planning-grade. NAVD88 intl ft. EPSG:6494. Run from repo root.
"""
import os
import shutil

from shapely.geometry import shape, mapping, LineString
from shapely.ops import unary_union

import in_situ_common as C


def rounded(geom, nd=2):
    """mapping() with coordinates rounded to nd decimals."""

    def rec(x):
        if isinstance(x, (list, tuple)):
            return [rec(v) for v in x]
        return round(x, nd)

    m = mapping(geom)
    return {"type": m["type"], "coordinates": rec(m["coordinates"])}


def main():
    layers = C.verify_against_design()
    rows, floor = layers["rows"], layers["floor"]
    by_name = {f["properties"]["name"]: f for f in floor}

    # ── terrace treads: each row arc widened to its 3.0 ft tread band ──────
    treads, edges, tread_shapes = [], [], []
    prev_tread = C.FOCUS_ELEV
    for f in rows:
        p = f["properties"]
        R = p["radius_ft"]
        ring = C.annular_sector(R, R + C.TREAD)
        props = dict(p)
        props.update(
            zone="terrace_tread",
            surface="turf",
            tread_inner_radius_ft=R,
            tread_outer_radius_ft=round(R + C.TREAD, 2),
            tread_depth_ft=C.TREAD,
        )
        treads.append(C.feat(props, {"type": "Polygon", "coordinates": [ring]}))
        tread_shapes.append(shape(treads[-1]["geometry"]))
        riser = round(p["tread_elev_navd88"] - prev_tread, 2)
        edges.append(
            C.feat(
                {
                    "row": p["row"],
                    "name": f"terrace_edge_row{p['row']:02d}",
                    "edge_type": "low_seat_edge",
                    "radius_ft": R,
                    "riser_ft": riser,
                    "top_elev_navd88": p["tread_elev_navd88"],
                    "material": "timber-or-stone low seat edge (≤1.5 ft)",
                    "retaining_wall": False,
                    "note": "front edge of tread; doubles as informal bench seating",
                },
                {"type": "LineString", "coordinates": C.arc_coords(R)},
            )
        )
        prev_tread = p["tread_elev_navd88"]
    C.dump(C.fc(treads), os.path.join(C.VEC_DIR, "terrace_treads.geojson"))
    C.dump(C.fc(edges), os.path.join(C.VEC_DIR, "terrace_edges.geojson"))

    # ── bowl zones ──────────────────────────────────────────────────────────
    open_stage_flags = dict(
        enclosure="none",
        upstage_shell=False,
        back_wall=False,
        fly_tower=False,
        open_to_bay_side=True,
    )
    zones = []

    def add_zone(name, geom, **props):
        zones.append(C.feat(dict(zone=name, name=name, **props), geom))

    stage = by_name["stage"]
    add_zone(
        "stage_core",
        stage["geometry"],
        elev_navd88=C.FOCUS_ELEV,
        surface="hardscape deck",
        max_structure_height_ft=4.0,
        note="70x34 ft low open stage at event-floor grade; bay + sky are the backdrop",
        **open_stage_flags,
    )
    for side in ("left", "right"):
        sh = by_name[f"stage_shoulder_{side}"]
        add_zone(
            f"stage_shoulder_{side}",
            sh["geometry"],
            elev_navd88=C.FOCUS_ELEV,
            surface="hardscape deck",
            max_structure_height_ft=4.0,
            note="lateral floor-level shoulder (band-shell projection logic, not an enclosing wall)",
            **open_stage_flags,
        )
    add_zone(
        "event_floor_forecourt",
        by_name["event_floor_forecourt"]["geometry"],
        elev_navd88=C.FOCUS_ELEV,
        surface="stabilized turf / accessible event floor",
        note="orchestra apron between stage front and row 1 (~35 ft); floor-level accessible seating",
    )
    cell = by_name["treatment_wet_cell"]
    add_zone(
        "treatment_cell_landscape",
        cell["geometry"],
        bottom_navd88=C.TREATMENT_BOTTOM,
        hydrology="dry_ephemeral_bioretention",
        permanent_water=False,
        planting="wet-tolerant meadow / bioretention mix",
        note=(
            "dry bioretention cell beyond the stage; ponds only shallowly and "
            "transiently after large storms — never a standing pool"
        ),
    )

    ada = C.load_design("ada_route.geojson")["features"]
    ada_shapes = []
    for f in ada:
        p = f["properties"]
        line = shape(f["geometry"])
        width = 6.0 if p["type"] == "switchback_ramp" else C.TREAD
        corr = line.buffer(width / 2.0, cap_style="flat", join_style="round")
        ada_shapes.append(corr)
        is_aisle = p["name"] == "mid_cross_aisle"
        add_zone(
            "cross_aisle" if is_aisle else "ada_route",
            rounded(corr),
            source_route=p["name"],
            corridor_width_ft=width,
            overlay=is_aisle,  # the aisle band rides on the row tread it follows
            # DESIGN_CANON Rules 6/7: name the actual generator; never claim a
            # seam discovery. This band is a buffer of the design route line.
            geometry_source="design_route_buffer (design_open_low ada_route.geojson)",
            seam_derived=False,
            cost_status="concept",  # Rule 3: schematic corridor, not cost-proxy
            note=(
                "level cross-aisle / wheelchair dispersion band (overlay on its row tread)"
                if is_aisle
                else f"{p['name']} corridor, schematic {width:.0f} ft width about the route line"
            ),
        )

    # untouched slope: study envelope minus every intervention footprint
    footprints = unary_union(
        tread_shapes
        + ada_shapes
        + [
            shape(by_name[n]["geometry"])
            for n in (
                "stage",
                "stage_shoulder_left",
                "stage_shoulder_right",
                "event_floor_forecourt",
                "treatment_wet_cell",
            )
        ]
    )
    envelope = footprints.buffer(40.0).simplify(0.5)
    untouched = envelope.difference(footprints.buffer(0.1)).simplify(0.25)
    add_zone(
        "untouched_slope",
        rounded(untouched),
        surface="existing slope vegetation",
        earthwork="none",
        note="existing grade preserved — no work; 40 ft study envelope minus all footprints",
    )
    C.dump(C.fc(zones), os.path.join(C.VEC_DIR, "bowl_zones.geojson"))

    # ── verbatim copies of the governing design layers ─────────────────────
    os.makedirs(C.VEC_DIR, exist_ok=True)
    for name in ("seating_rows.geojson", "stage_floor.geojson", "ada_route.geojson"):
        shutil.copy2(os.path.join(C.DESIGN_DIR, name), os.path.join(C.VEC_DIR, name))
        print(f"  copied design_open_low/{name} -> vectors_geojson/{name}")


if __name__ == "__main__":
    main()
