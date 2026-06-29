#!/usr/bin/env python3
"""Generate the terrain-operation ledger for the Open Civic Bowl.

Returns the Unreal amphitheatre to the agentic-clay architecture: the visible
ground is decomposed, surface by surface, into auditable *operations*.  Every
earthform, terrace, tread, riser, ADA path, drainage strip and stage surface
gets an ``op_id`` and traces back to the accepted Open Civic Bowl design.

Inputs   design_open_low/seating_rows.geojson   (16-row open fan, +/-55 deg)
         design_open_low/stage_floor.geojson     (stage, shoulders, forecourt, cell)
         design_open_low/ada_route.geojson        (accessible routes + cross-aisle)

Outputs  design/terrain_ops.proposal.json         (the ledger -- PROPOSAL tier)
         unreal_export/geo/terrace_ops/*.geojson   (explicit op geometry layers)
         unreal_export/manifests/terrace_material_manifest.json

The proposal does NOT become accepted here.  Run scripts/validate_terrain_ops.py
to gate it; on PASS that promotes it to design/terrain_ops.current.json.

Scope note: this re-bases the auditable terrain-ops architecture on the Open
Civic Bowl 16-row open fan, which the task names as the accepted design to
preserve.  (The 45-tread Scenario E bowl currently imported into the live UE
scene is a separate seating-capacity study; see docs/TERRAIN_OPS_LEDGER.md.)

stdlib + numpy only.  EPSG:6494, NAVD88 intl ft.
"""
from __future__ import annotations

import json
import os

import numpy as np

import terrace_ops_common as T


def _row_annuli(rows, radii):
    """For each row index, the [inner, outer] radius it owns (neighbour mids)."""
    n = len(rows)
    ann = []
    for i in range(n):
        if i == 0:
            pitch = radii[1] - radii[0] if n > 1 else T.DEFAULT_PITCH_FT
            inner = radii[0] - pitch / 2.0
        else:
            inner = (radii[i - 1] + radii[i]) / 2.0
        if i == n - 1:
            pitch = radii[i] - radii[i - 1] if n > 1 else T.DEFAULT_PITCH_FT
            outer = radii[i] + pitch / 2.0
        else:
            outer = (radii[i] + radii[i + 1]) / 2.0
        ann.append((inner, outer))
    return ann


def build():
    rows = T.load_geojson(os.path.join(T.DESIGN_SRC, "seating_rows.geojson"))["features"]
    rows = sorted(rows, key=lambda f: f["properties"]["row"])
    stage = T.load_geojson(os.path.join(T.DESIGN_SRC, "stage_floor.geojson"))["features"]
    ada = T.load_geojson(os.path.join(T.DESIGN_SRC, "ada_route.geojson"))["features"]

    center = T.bowl_center(rows)
    radii = [float(f["properties"]["radius_ft"]) for f in rows]
    annuli = _row_annuli(rows, radii)
    plan_total = sum(w for _, w in T.BAND_PLAN)

    ops = []
    layers = {k: [] for k in
              ("seat_caps", "tread_surfaces", "riser_faces", "drainage_bands",
               "terrain_transitions", "ada_paths", "stage_floor", "clip_mask",
               "grade_p_current")}

    # ---- per-row engineered terrace operations --------------------------
    bowl_outline_inner = None
    bowl_outline_outer = None
    for i, f in enumerate(rows):
        p = f["properties"]
        rn = int(p["row"])
        arc = np.asarray(f["geometry"]["coordinates"], dtype=float)
        a_inner, a_outer = annuli[i]
        pitch_i = a_outer - a_inner
        tread_elev = float(p["tread_elev_navd88"])
        terrain_elev = float(p.get("terrain_elev_navd88", tread_elev))
        rise = float(p.get("row_rise_ft", 0.0))
        cutfill = float(p.get("cut_fill_ft", 0.0))

        if i == 0:
            bowl_outline_inner = T.arc_at_radius(arc, center, a_inner)
        if i == len(rows) - 1:
            bowl_outline_outer = T.arc_at_radius(arc, center, a_outer)

        cursor = a_inner
        sub = {}
        for name, w in T.BAND_PLAN:
            wi = w * pitch_i / plan_total
            r0, r1 = cursor, cursor + wi
            sub[name] = (r0, r1)
            cursor = r1

        prov = {"source": "design_open_low/seating_rows.geojson",
                "feature_row": rn,
                "validation_read": {
                    "meets_C_proposed": bool(p.get("meets_C_proposed")),
                    "meets_C_on_terrain": bool(p.get("meets_C_on_terrain")),
                    "C_value_proposed_mm": p.get("C_value_proposed_mm"),
                    "cut_fill_ft": cutfill}}

        def emit(name, sclass, r0, r1, layer, elev_lo, elev_hi, extra=None):
            opid = f"op.row{rn:02d}.{name}"
            color, mkey, _ = T.SURFACE_CLASSES[sclass]
            poly = T.band_polygon(arc, center, r0, r1)
            props = {"op_id": opid, "kind": name, "surface_class": sclass,
                     "row": rn, "material": mkey, "debug_color": color,
                     "elev_lo_navd88": round(elev_lo, 2),
                     "elev_hi_navd88": round(elev_hi, 2),
                     "r_inner_ft": round(r0, 2), "r_outer_ft": round(r1, 2),
                     "status": "proposal"}
            if extra:
                props.update(extra)
            layers[layer].append(T.polygon_feature(poly, props))
            ops.append({
                "op_id": opid, "kind": name, "surface_class": sclass, "row": rn,
                "parent": f"op.row{rn:02d}", "material": mkey,
                "geometry_ref": f"unreal_export/geo/terrace_ops/{layer}.geojson#{opid}",
                "elev_lo_navd88": round(elev_lo, 2), "elev_hi_navd88": round(elev_hi, 2),
                "debug_color": color, "provenance": prov, "status": "proposal"})

        # riser (inner, climbs from row below to this tread)
        emit("riser", "riser", *sub["riser"], "riser_faces",
             tread_elev - rise, tread_elev, {"riser_height_ft": round(rise, 2)})
        # foot tread (walkable plate)
        emit("tread", "tread", *sub["tread"], "tread_surfaces",
             tread_elev, tread_elev)
        # seat cap (back of tread)
        emit("cap", "cap", *sub["cap"], "seat_caps",
             tread_elev, tread_elev,
             {"seats_compact_18in": p.get("seats_compact_18in"),
              "seats_generous_22in": p.get("seats_generous_22in")})
        # drainage edge (up-slope gravel strip, below tread)
        emit("drainage", "drainage", *sub["drainage"], "drainage_bands",
             tread_elev - T.DRAINAGE_DROP_FT, tread_elev,
             {"drainage_drop_ft": T.DRAINAGE_DROP_FT})
        # terrain transition (feather plate -> existing grade); cut/fill by sign
        tclass = ("fill" if cutfill > 0.05 else
                  "cut" if cutfill < -0.05 else "existing_no_touch")
        emit("transition", tclass, *sub["transition"], "terrain_transitions",
             min(tread_elev, terrain_elev), max(tread_elev, terrain_elev),
             {"cut_fill_ft": round(cutfill, 2), "ties_to_existing": True})

        # terrain clip mask (riser..drainage = all constructed wear surfaces).
        # Terrain material is suppressed here so existing ground cannot draw
        # over the seat caps / treads -- the core fix.
        clip_r0 = sub["riser"][0]
        clip_r1 = sub["drainage"][1]
        clip_poly = T.band_polygon(arc, center, clip_r0, clip_r1)
        clip_id = f"op.row{rn:02d}.clip"
        layers["clip_mask"].append(T.polygon_feature(clip_poly, {
            "op_id": clip_id, "kind": "clip_mask", "surface_class": "clip",
            "row": rn, "suppress_terrain_draw": True,
            "r_inner_ft": round(clip_r0, 2), "r_outer_ft": round(clip_r1, 2),
            "covers": [f"op.row{rn:02d}.{n}" for n in
                       ("riser", "tread", "cap", "drainage")],
            "status": "proposal"}))
        ops.append({
            "op_id": clip_id, "kind": "clip_mask", "surface_class": "clip",
            "row": rn, "parent": f"op.row{rn:02d}",
            "geometry_ref": f"unreal_export/geo/terrace_ops/clip_mask.geojson#{clip_id}",
            "suppress_terrain_draw": True,
            "covers": [f"op.row{rn:02d}.{n}" for n in
                       ("riser", "tread", "cap", "drainage")],
            "status": "proposal"})

    # ---- accepted grade P_current (bowl terrace footprint outline) ------
    if bowl_outline_inner is not None and bowl_outline_outer is not None:
        ring = np.vstack([bowl_outline_inner, bowl_outline_outer[::-1]])
        layers["grade_p_current"].append(T.polygon_feature(ring, {
            "op_id": "op.grade.p_current", "kind": "accepted_grade",
            "surface_class": "fill", "material": "graded_fill",
            "debug_color": T.SURFACE_CLASSES["fill"][0],
            "raster_ref": "dem/proposed_grade_1ft.tif",
            "note": "Accepted after-state grade across the terraced bowl "
                    "footprint; raster authority dem/proposed_grade_1ft.tif "
                    "(build_proposed_grade.py, all_touched=True).",
            "status": "proposal"}))
    ops.append({
        "op_id": "op.grade.p_current", "kind": "accepted_grade",
        "surface_class": "fill", "parent": None,
        "geometry_ref": "unreal_export/geo/terrace_ops/grade_p_current.geojson#op.grade.p_current",
        "raster_ref": "dem/proposed_grade_1ft.tif",
        "provenance": {"source": "dem/proposed_grade_1ft.tif",
                       "method": "build_proposed_grade.py all_touched=True"},
        "status": "proposal"})
    # existing / no-touch terrain (everything outside the clip masks)
    ops.append({
        "op_id": "op.grade.existing", "kind": "existing_grade",
        "surface_class": "existing_no_touch", "parent": None,
        "geometry_ref": "unreal_export/terrain/terrain_existing.obj",
        "note": "Existing LiDAR ground. Visible only outside the row clip "
                "masks, ADA paths and stage footprints. Never sculpted in UE.",
        "status": "proposal"})

    # ---- stage / floor operations ---------------------------------------
    stage_map = {
        "stage": ("op.stage.deck", "Stage core deck"),
        "stage_shoulder_left": ("op.stage.shoulder_left", "Stage shoulder L"),
        "stage_shoulder_right": ("op.stage.shoulder_right", "Stage shoulder R"),
        "event_floor_forecourt": ("op.floor.forecourt", "Orchestra forecourt floor"),
    }
    for f in stage:
        nm = f["properties"].get("name")
        if nm in stage_map and f["geometry"]["type"] == "Polygon":
            opid, label = stage_map[nm]
            ring = np.asarray(f["geometry"]["coordinates"][0], dtype=float)
            color, mkey, _ = T.SURFACE_CLASSES["stage"]
            elev = float(f["properties"].get("elev_navd88")
                         or f["properties"].get("grade_elev_navd88") or 612.5)
            props = {"op_id": opid, "kind": "stage", "surface_class": "stage",
                     "material": mkey, "debug_color": color,
                     "elev_navd88": round(elev, 2), "label": label,
                     "suppress_terrain_draw": True, "status": "proposal"}
            layers["stage_floor"].append(T.polygon_feature(ring, props))
            ops.append({"op_id": opid, "kind": "stage", "surface_class": "stage",
                        "material": mkey, "parent": None,
                        "geometry_ref": "unreal_export/geo/terrace_ops/stage_floor.geojson#" + opid,
                        "elev_navd88": round(elev, 2),
                        "provenance": {"source": "design_open_low/stage_floor.geojson",
                                       "feature": nm},
                        "suppress_terrain_draw": True, "status": "proposal"})
        elif nm == "treatment_wet_cell" and f["geometry"]["type"] == "Polygon":
            ring = np.asarray(f["geometry"]["coordinates"][0], dtype=float)
            props = {"op_id": "op.cell.treatment", "kind": "cut",
                     "surface_class": "cut", "material": "graded_cut",
                     "debug_color": T.SURFACE_CLASSES["cut"][0],
                     "bottom_navd88": f["properties"].get("bottom_navd88"),
                     "tier": "concept", "suppress_terrain_draw": False,
                     "note": "Stormwater treatment cell, down-only shaping; "
                             "landscape basin, terrain may read here.",
                     "status": "proposal"}
            layers["stage_floor"].append(T.polygon_feature(ring, props))
            ops.append({"op_id": "op.cell.treatment", "kind": "cut",
                        "surface_class": "cut", "material": "graded_cut",
                        "parent": None, "tier": "concept",
                        "geometry_ref": "unreal_export/geo/terrace_ops/stage_floor.geojson#op.cell.treatment",
                        "provenance": {"source": "design_open_low/stage_floor.geojson",
                                       "feature": nm},
                        "suppress_terrain_draw": False, "status": "proposal"})

    # ---- ADA operations -------------------------------------------------
    ada_ids = {
        "accessible_route_A_floor": "op.ada.route_a_floor",
        "accessible_route_B_mid_row9": "op.ada.route_b_mid",
        "mid_cross_aisle": "op.ada.cross_aisle_row9",
    }
    for f in ada:
        nm = f["properties"].get("name")
        opid = ada_ids.get(nm, f"op.ada.{nm}")
        line = np.asarray(f["geometry"]["coordinates"], dtype=float)
        poly = T.buffer_line(line, T.ADA_PATH_WIDTH_FT)
        color, mkey, _ = T.SURFACE_CLASSES["ada"]
        props = {"op_id": opid, "kind": "ada", "surface_class": "ada",
                 "material": mkey, "debug_color": color,
                 "ada_type": f["properties"].get("type"),
                 "running_slope_pct": f["properties"].get("design_running_slope_pct"),
                 "cross_slope_target_pct": f["properties"].get("cross_slope_target_pct"),
                 "suppress_terrain_draw": True, "status": "proposal"}
        layers["ada_paths"].append(T.polygon_feature(poly, props))
        ops.append({"op_id": opid, "kind": "ada", "surface_class": "ada",
                    "material": mkey, "parent": None,
                    "geometry_ref": "unreal_export/geo/terrace_ops/ada_paths.geojson#" + opid,
                    "provenance": {"source": "design_open_low/ada_route.geojson",
                                   "feature": nm},
                    "suppress_terrain_draw": True, "status": "proposal"})

    # ---- write geometry layers ------------------------------------------
    os.makedirs(T.GEO_OUT, exist_ok=True)
    for name, feats in layers.items():
        with open(os.path.join(T.GEO_OUT, f"{name}.geojson"), "w") as fh:
            json.dump(T.feature_collection(feats), fh, indent=1)

    # ---- material manifest (construction logic + clip policy) -----------
    os.makedirs(T.MANIFEST_DIR, exist_ok=True)
    mat_manifest = {
        "schema": "amphitheatre/terrace-material-manifest/0.2",
        "principle": "Materials communicate HOW each surface is built, not "
                     "merely how it is coloured. Keyed to the terrain-op ledger.",
        "render_lift_ft": T.RENDER_LIFT_FT,
        "clip_policy": {
            "clipped_surface_classes": list(T.CLIPPED_CLASSES),
            "rule": "Terrain (existing/no-touch + graded) material MUST NOT "
                    "draw over any clipped surface. Enforced by (1) the "
                    "per-row clip_mask cutouts, (2) the all_touched=True raster "
                    "flattening in build_proposed_grade.py, and (3) a "
                    f"{T.RENDER_LIFT_FT} ft render lift on constructed surfaces.",
        },
        "materials": T.material_table(),
        "debug_palette_by_surface_class": T.debug_palette(),
    }
    with open(os.path.join(T.MANIFEST_DIR, "terrace_material_manifest.json"), "w") as fh:
        json.dump(mat_manifest, fh, indent=1)

    # ---- the ledger (PROPOSAL) ------------------------------------------
    by_class = {}
    for o in ops:
        by_class[o["surface_class"]] = by_class.get(o["surface_class"], 0) + 1
    ledger = {
        "schema": T.SCHEMA,
        "status": "proposal",
        "design": "open_civic_bowl",
        "crs": T.CRS, "datum": T.DATUM,
        "bowl_center_epsg6494": [round(center[0], 2), round(center[1], 2)],
        "invariants": T.INVARIANTS,
        "sources": {
            "seating_rows": "design_open_low/seating_rows.geojson",
            "stage_floor": "design_open_low/stage_floor.geojson",
            "ada_route": "design_open_low/ada_route.geojson",
            "accepted_grade_raster": "dem/proposed_grade_1ft.tif",
        },
        "surface_classes": {s: {"debug_color": c, "material": m, "label": l}
                            for s, (c, m, l) in T.SURFACE_CLASSES.items()},
        "op_count": len(ops),
        "op_count_by_surface_class": by_class,
        "row_op_template": [n for n, _ in T.BAND_PLAN] + ["clip"],
        "ops": ops,
        "validation": {"state": "PENDING",
                       "note": "Run scripts/validate_terrain_ops.py to gate and "
                               "promote to design/terrain_ops.current.json."},
        "provenance_note": "Generated by scripts/build_terrain_ops.py from the "
                           "accepted Open Civic Bowl design. Visible terrain is "
                           "generated from these operations, not sculpted in UE.",
    }
    os.makedirs(T.DESIGN_DIR, exist_ok=True)
    out = os.path.join(T.DESIGN_DIR, "terrain_ops.proposal.json")
    with open(out, "w") as fh:
        json.dump(ledger, fh, indent=1)

    print(f"  bowl center (EPSG:6494): {center[0]:.2f}, {center[1]:.2f}")
    print(f"  rows: {len(rows)}  ops: {len(ops)}")
    print(f"  by surface class: {by_class}")
    print(f"  wrote {os.path.relpath(out, T.REPO)} (PROPOSAL)")
    print(f"  wrote {len(layers)} geometry layers -> unreal_export/geo/terrace_ops/")
    print("  wrote unreal_export/manifests/terrace_material_manifest.json")
    print("  NEXT: python scripts/validate_terrain_ops.py")


if __name__ == "__main__":
    build()
