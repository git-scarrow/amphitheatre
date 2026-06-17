#!/usr/bin/env python3
"""Build a minimal Unreal handoff package for the Petoskey Pit civic bowl.

This is an EXPORT/VIEWER layer. It is read-only on the authoritative GIS/design
repo and never mutates governing geometry. It converts the CURRENT accepted
design (Scenario E three-section civic bowl, as expressed by the in-situ
package) and the planning DEMs into clean, Unreal-importable assets, with full
provenance back to each source file + feature id.

Authoritative sources (see truth_package/data_inventory.md):
  vectors_geojson/terrace_treads.geojson .......... 45 seating treads (rows)
  vectors_geojson/bowl_zones.geojson .............. stage / event floor / cell
  design_open_low/stage_floor.geojson ............. bay-view axis + focal point
  vectors_geojson/ada_route.geojson ............... ADA route concept (A/B)
  analysis/tier_emission/Scenario_E_baseline_reemit/validation.json
                                                    sightline C, seat bands, ADA
  vectors_geojson/in_situ_viewpoints.geojson ...... 6 canonical cameras
  dem/dem_design_1ft.tif, dem/proposed_grade_1ft.tif, dem/cut_fill_1ft.tif

Outputs (under unreal_export/, regenerable):
  geo/seating_rows.geojson         tread polygons (mesh actors), cut/fill sampled
  geo/seating_row_splines.geojson  row centreline arcs (spline actors)
  geo/stage_floor.geojson          stage/forecourt/treatment/bay-axis actors
  geo/ada_route.geojson            route/path actors + landings, slope metadata
  tables/sightline_table.csv       per-row C / band / status (read from source)
  terrain/*.glb, *.obj             ENU Z-up metre meshes (existing + proposed)
  terrain/*.r16, *.png             16-bit heightfields for Unreal Landscape
  terrain/*.heightfield.json       NAVD88 ft / EPSG:6494 provenance sidecars
  manifests/actor_manifest.json/.csv   every actor -> source file + feature id
  manifests/material_manifest.json     styles keyed to VALIDATION STATE (read)
  manifests/camera_manifest.json       human-scale cameras (authoritative + derived)
  manifests/provenance.json            origin, CRS, datum, sha256, warnings block

Coordinate contract (single frame for ALL 3D geometry):
  local ENU, Z-up, METRES; origin = canon EPSG:6494 (19533067.7, 750799.2) intl ft;
  x = east, y = north, z = NAVD88 ft * 0.3048. Fully reversible (see README_UNREAL.md).
  GeoJSON exports stay in EPSG:6494 intl ft (gate-valid, round-trippable);
  the actor manifest bridges EPSG:6494 anchors <-> local metre anchors.

Nothing here recomputes a validated quantity. Seat counts, C-values, ADA slopes,
and the planning-grade warnings are read verbatim from the source tables; the
companion verify_unreal_export.py asserts they are not weakened or replaced.
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime as _dt
import hashlib
import json
import math
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── governing constants (single source: scripts/in_situ_common.py) ──────────
sys.path.insert(0, os.path.join(REPO, "scripts"))
try:
    import in_situ_common as C  # noqa: E402

    ORIGIN_X, ORIGIN_Y = C.CX, C.CY
    BAY_VIEW_AZ = C.BAY_VIEW_AZ
    BAY_PLANE = C.BAY_PLANE
    _CONST_SOURCE = "scripts/in_situ_common.py"
except Exception as exc:  # fresh checkout without that module's deps
    ORIGIN_X, ORIGIN_Y = 19533067.7, 750799.2
    BAY_VIEW_AZ, BAY_PLANE = 330.0, 579.45
    _CONST_SOURCE = f"fallback constants (in_situ_common import failed: {exc})"

FT2M = 0.3048  # exact: EPSG:6494 is INTERNATIONAL feet (see docs/datum_note.md)
C_BAR_MM = 90.0  # civic sightline bar (formal-seat threshold), from canon

SRC = {
    "treads": "vectors_geojson/terrace_treads.geojson",
    "zones": "vectors_geojson/bowl_zones.geojson",
    "stage_lineage": "design_open_low/stage_floor.geojson",
    "ada_route": "vectors_geojson/ada_route.geojson",
    "viewpoints": "vectors_geojson/in_situ_viewpoints.geojson",
    "validation": "analysis/tier_emission/Scenario_E_baseline_reemit/validation.json",
    "design_state": "truth_package/design_state.current.json",
    "dem_existing": "dem/dem_design_1ft.tif",
    "dem_proposed": "dem/proposed_grade_1ft.tif",
    "dem_cutfill": "dem/cut_fill_1ft.tif",
    "data_inventory": "truth_package/data_inventory.md",
}

OUT = "unreal_export"


# ── small utilities ─────────────────────────────────────────────────────────
def p(rel: str) -> str:
    return os.path.join(REPO, rel)


def opath(rel: str) -> str:
    return os.path.join(REPO, OUT, rel)


def ensure_dir(rel: str) -> str:
    d = opath(rel)
    os.makedirs(d, exist_ok=True)
    return d


def sha12(rel: str):
    path = p(rel)
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def jload(rel: str):
    with open(p(rel)) as fh:
        return json.load(fh)


def jwrite(rel: str, obj) -> str:
    path = opath(rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return path


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", REPO, "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


CRS6494 = {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::6494"}}


def to_local_m(x: float, y: float, z_ft: float):
    """EPSG:6494 intl ft -> local ENU metres, Z-up, about the canon origin."""
    return [
        round((x - ORIGIN_X) * FT2M, 4),
        round((y - ORIGIN_Y) * FT2M, 4),
        round(z_ft * FT2M, 4),
    ]


def ring_centroid(ring):
    """Area centroid of a ring, computed about its first vertex to avoid the
    float cancellation that ruins shoelace sums on ~1.9e7 ft eastings."""
    ox, oy = ring[0][0], ring[0][1]
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        ax, ay = x0 - ox, y0 - oy
        bx, by = x1 - ox, y1 - oy
        cross = ax * by - bx * ay
        a += cross
        cx += (ax + bx) * cross
        cy += (ay + by) * cross
    if abs(a) < 1e-9:
        return [ox, oy]
    a *= 0.5
    return [cx / (6 * a) + ox, cy / (6 * a) + oy]


def outer_ring(geom):
    if geom["type"] == "Polygon":
        return geom["coordinates"][0]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"][0][0]
    if geom["type"] == "LineString":
        return geom["coordinates"]
    if geom["type"] == "Point":
        return [geom["coordinates"]]
    return []


# ── actor registry (provenance bridge) ──────────────────────────────────────
ACTORS = []  # list of dict rows for the actor manifest


def register_actor(*, name, actor_class, source_file, source_feature_id,
                   anchor_xyz_epsg6494_ft, z_navd88_ft, material_id,
                   validation_state, provisional=False, note=""):
    ax, ay = anchor_xyz_epsg6494_ft
    ACTORS.append({
        "actor_name": name,
        "actor_class": actor_class,
        "source_file": source_file,
        "source_sha256_12": sha12(source_file),
        "source_feature_id": source_feature_id,
        "anchor_epsg6494_ft": [round(ax, 2), round(ay, 2)],
        "anchor_local_m": to_local_m(ax, ay, z_navd88_ft or 0.0),
        "z_navd88_ft": None if z_navd88_ft is None else round(z_navd88_ft, 2),
        "material_id": material_id,
        "validation_state": validation_state,
        "provisional": bool(provisional),
        "note": note,
    })


# ── 1. seating rows (from terrace_treads + cut/fill raster sampling) ─────────
def sample_cutfill(geom):
    """Mean / min / max of dem/cut_fill_1ft.tif inside a tread polygon.

    cut_fill = proposed - existing (ft): positive = fill, negative = cut.
    Returns (mean, min, max, n_cells) or (None, None, None, 0) when the raster
    is absent or no valid cell falls inside the footprint.
    """
    rel = SRC["dem_cutfill"]
    if not os.path.exists(p(rel)):
        return None, None, None, 0
    import numpy as np
    import rasterio
    from rasterio.mask import mask as rio_mask

    try:
        with rasterio.open(p(rel)) as r:
            arr, _ = rio_mask(r, [geom], crop=True, filled=False, all_touched=True)
            nod = r.nodata
    except Exception:
        return None, None, None, 0
    band = arr[0]
    data = band.compressed() if hasattr(band, "compressed") else band.ravel()
    data = np.asarray(data, dtype="float64")
    if nod is not None:
        data = data[data != nod]
    data = data[np.isfinite(data)]
    if data.size == 0:
        return None, None, None, 0
    return (round(float(data.mean()), 2), round(float(data.min()), 2),
            round(float(data.max()), 2), int(data.size))


def band_status_lookup(validation):
    """section rN -> (band_a_seats, pass_frac, status, fail_reasons)."""
    out = {}
    for b in validation.get("per_band", []):
        out[b["band"]] = {
            "band_a_seats": b.get("band_a"),
            "pass_frac": b.get("pass_frac"),
            "status": b.get("status"),
            "fail_reasons": b.get("fail_reasons", []),
        }
    return out


def build_seating(validation):
    treads = jload(SRC["treads"])
    bands = band_status_lookup(validation)
    c_rows = validation.get("c_rows", {})

    row_feats, spline_feats = [], []
    seat_total = 0
    for i, f in enumerate(treads["features"]):
        pr = f["properties"]
        geom = f["geometry"]
        section, row = pr.get("section"), pr.get("row")
        band_key = f"{section} r{row}"
        fid = f"tread_{section}_r{row}"
        seats = pr.get("seats_kept") or 0
        seat_total += seats
        c_mm = c_rows.get(band_key, pr.get("C_mm"))
        binfo = bands.get(band_key, {})
        status = binfo.get("status", "unknown")
        # verdict: read-only interpretation of the SOURCE C against the canon bar.
        if c_mm is None:
            verdict = "front_row_no_obstruction"
        elif c_mm >= C_BAR_MM:
            verdict = "PASS"
        else:
            verdict = "WARN"

        cf_mean, cf_min, cf_max, cf_n = sample_cutfill(geom)

        ring = outer_ring(geom)
        cen = ring_centroid(ring)
        elev = pr.get("tread_elev_navd88")
        material_id = f"row_{status}"

        props = {
            "feature_id": fid,
            "source_file": SRC["treads"],
            "source_index": i,
            "row": row,
            "section": section,
            "section_family": pr.get("section_family"),
            "zone": pr.get("zone"),
            "axis_radius_ft": pr.get("axis_radius_ft"),
            "proposed_elev_navd88_ft": elev,
            "seats_kept": seats,
            "C_mm": c_mm,
            "C_bar_mm": C_BAR_MM,
            "sightline_verdict": verdict,
            "band_status": status,
            "band_a_seats": binfo.get("band_a_seats"),
            "pass_frac": binfo.get("pass_frac"),
            "fail_reasons": binfo.get("fail_reasons", []),
            "sees_bay": pr.get("sees_bay"),
            "surface": pr.get("surface"),
            "cross_angle_deg": pr.get("cross_angle_deg"),
            "cutfill_mean_ft": cf_mean,
            "cutfill_min_ft": cf_min,
            "cutfill_max_ft": cf_max,
            "cutfill_cells": cf_n,
            "cutfill_sign": "positive=fill, negative=cut",
            "cutfill_source": SRC["dem_cutfill"],
            "geometry_source": pr.get("geometry_source"),
            "datum": pr.get("datum"),
            "material_id": material_id,
            "unreal_anchor_local_m": to_local_m(cen[0], cen[1], elev or 0.0),
            "provenance": "derived from terrace_treads.geojson (read-only); "
                          "C_mm and band_status from validation.json; "
                          "cutfill sampled from cut_fill_1ft.tif",
        }
        row_feats.append({"type": "Feature", "geometry": geom, "properties": props})

        # spline actor: tread axis arc (use the polygon's longest edge chain as
        # the row centreline proxy -> the outer ring minus the closing point).
        spline_props = dict(props)
        spline_props["actor_kind"] = "row_spline"
        spline_feats.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": ring[:-1] if ring[-1] == ring[0] else ring},
            "properties": spline_props,
        })

        register_actor(
            name=f"Row_{section}_{row:02d}",
            actor_class="spline_mesh",
            source_file=SRC["treads"],
            source_feature_id=fid,
            anchor_xyz_epsg6494_ft=cen,
            z_navd88_ft=elev,
            material_id=material_id,
            validation_state=verdict if verdict != "front_row_no_obstruction" else status,
            note=f"{seats} seats; band {status}; C={c_mm}mm",
        )

    fc = {"type": "FeatureCollection", "crs": CRS6494,
          "name": "seating_rows", "features": row_feats}
    splines = {"type": "FeatureCollection", "crs": CRS6494,
               "name": "seating_row_splines", "features": spline_feats}
    jwrite("geo/seating_rows.geojson", fc)
    jwrite("geo/seating_row_splines.geojson", splines)
    return {"n_rows": len(row_feats), "seat_total": seat_total}


# ── 2. stage floor complex (from bowl_zones + stage lineage) ────────────────
STAGE_ZONES = {
    "stage_core": ("stage", True),
    "stage_shoulder_left": ("stage_shoulder", True),
    "stage_shoulder_right": ("stage_shoulder", True),
    "orchestra_event_floor": ("forecourt_event_floor", False),
    "treatment_cell_landscape": ("treatment_cell", False),
}


def build_stage():
    zones = jload(SRC["zones"])
    lineage = jload(SRC["stage_lineage"])
    feats = []

    for i, f in enumerate(zones["features"]):
        pr = f["properties"]
        z = pr.get("zone")
        if z not in STAGE_ZONES:
            continue
        role, is_stage = STAGE_ZONES[z]
        name = pr.get("name", z)
        fid = f"zone_{name}"
        rule9 = pr.get("rule9_status")
        provisional = bool(is_stage and rule9 == "open")
        concept = z in ("orchestra_event_floor", "treatment_cell_landscape")
        elev = pr.get("elev_navd88") or pr.get("grade_elev_navd88")
        material_id = ("stage_provisional" if provisional else
                       "treatment_cell_concept" if z == "treatment_cell_landscape" else
                       "event_floor_concept" if z == "orchestra_event_floor" else
                       "stage")
        cen = ring_centroid(outer_ring(f["geometry"]))
        props = {
            "feature_id": fid,
            "source_file": SRC["zones"],
            "source_index": i,
            "role": role,
            "zone": z,
            "name": name,
            "elev_navd88_ft": elev,
            "rule9_status": rule9,
            "provisional": provisional,
            "concept_tier": concept,
            "blocks_bay_view": pr.get("blocks_bay_view"),
            "open_to_bay_side": pr.get("open_to_bay_side"),
            "max_structure_height_ft": pr.get("max_structure_height_ft"),
            "geometry_source": pr.get("geometry_source"),
            "surface": pr.get("surface"),
            "material_id": material_id,
            "note": pr.get("note") or pr.get("rule9_note") or "",
            "unreal_anchor_local_m": to_local_m(cen[0], cen[1], elev or 0.0),
            "provenance": "derived from bowl_zones.geojson (read-only)",
        }
        feats.append({"type": "Feature", "geometry": f["geometry"], "properties": props})
        register_actor(
            name="Stage_" + name if is_stage else name.title().replace("_", ""),
            actor_class="mesh",
            source_file=SRC["zones"],
            source_feature_id=fid,
            anchor_xyz_epsg6494_ft=cen,
            z_navd88_ft=elev,
            material_id=material_id,
            validation_state=("provisional" if provisional else
                              "concept" if concept else "source_of_truth"),
            provisional=provisional,
            note=("Rule 9 OPEN - stage deck PROVISIONAL" if provisional else
                  "concept-tier illustrative" if concept else ""),
        )

    # bay-view axis + focal point from the inherited stage lineage
    for i, f in enumerate(lineage["features"]):
        pr = f["properties"]
        nm = pr.get("name", "")
        if nm not in ("bay_view_axis", "focal_point_stage_front"):
            continue
        fid = f"lineage_{nm}"
        ring = outer_ring(f["geometry"])
        cen = ring_centroid(ring) if len(ring) > 2 else ring[0]
        props = {
            "feature_id": fid,
            "source_file": SRC["stage_lineage"],
            "source_index": i,
            "role": nm,
            "name": nm,
            "az_deg": pr.get("az_deg", BAY_VIEW_AZ if nm == "bay_view_axis" else None),
            "note": pr.get("note", ""),
            "material_id": "bay_view_axis",
            "lineage": "inherited design_open_low stage lineage",
            "provenance": "derived from design_open_low/stage_floor.geojson (read-only)",
        }
        feats.append({"type": "Feature", "geometry": f["geometry"], "properties": props})
        register_actor(
            name="BayViewAxis" if nm == "bay_view_axis" else "FocalPointStageFront",
            actor_class="spline" if f["geometry"]["type"] == "LineString" else "point",
            source_file=SRC["stage_lineage"],
            source_feature_id=fid,
            anchor_xyz_epsg6494_ft=cen,
            z_navd88_ft=None,
            material_id="bay_view_axis",
            validation_state="reference_axis",
            note=f"bay-view azimuth {BAY_VIEW_AZ} deg",
        )

    fc = {"type": "FeatureCollection", "crs": CRS6494,
          "name": "stage_floor", "features": feats}
    jwrite("geo/stage_floor.geojson", fc)
    return {"n_stage_features": len(feats)}


# ── 3. ADA route (from ada_route + validation cross-check) ──────────────────
def build_ada(validation):
    ada = jload(SRC["ada_route"])
    val_ada = {a["name"]: a for a in validation.get("ada", [])}
    feats = []
    n_routes = n_nodes = 0
    for i, f in enumerate(ada["features"]):
        pr = f["properties"]
        geom = f["geometry"]
        nm = pr.get("name", f"ada_{i}")
        fid = f"ada_{nm}"
        gtype = geom["type"]
        cross = val_ada.get(pr.get("route") or nm, {})
        if gtype == "LineString":
            n_routes += 1
            preferred = pr.get("preferred", False)
            material_id = "ada_preferred" if preferred else (
                "ada_service" if pr.get("class") == "service" else "ada_alternative")
            props = {
                "feature_id": fid,
                "source_file": SRC["ada_route"],
                "source_index": i,
                "kind": "route",
                "name": nm,
                "from": pr.get("from"),
                "to": pr.get("to"),
                "route_class": pr.get("class"),
                "role": pr.get("role"),
                "status": pr.get("status"),  # carried VERBATIM, never strengthened
                "preferred": preferred,
                "alternatives": pr.get("alternatives", []),
                "length_ft": pr.get("length_ft"),
                "drop_ft": pr.get("drop_ft"),
                "design_grade_pct": pr.get("design_grade_pct"),
                "profile": pr.get("profile"),
                "landings_marked": pr.get("landings_marked"),
                "smoothness_before": pr.get("smoothness_before"),
                "smoothness_after": pr.get("smoothness_after"),
                "validation_running_slope_pct": cross.get("running_slope_pct"),
                "validation_flights": cross.get("flights"),
                "validation_landings": cross.get("landings"),
                "validation_running_ok": cross.get("running_ok"),
                "grading_required": pr.get("grading_required"),
                "material_id": material_id,
                "provenance": "derived from ada_route.geojson (read-only); "
                              "running-slope/flights/landings cross-checked "
                              "against validation.json ada[]",
            }
            cen = ring_centroid(geom["coordinates"]) if len(geom["coordinates"]) > 2 \
                else geom["coordinates"][0]
            register_actor(
                name="ADA_" + nm,
                actor_class="spline",
                source_file=SRC["ada_route"],
                source_feature_id=fid,
                anchor_xyz_epsg6494_ft=geom["coordinates"][0],
                z_navd88_ft=pr.get("elev_navd88"),
                material_id=material_id,
                validation_state="route_concept_pending_civil",
                note=pr.get("status", ""),
            )
        elif gtype == "Point":
            n_nodes += 1
            material_id = "ada_landing"
            props = {
                "feature_id": fid,
                "source_file": SRC["ada_route"],
                "source_index": i,
                "kind": pr.get("kind", "node"),
                "name": nm,
                "elev_navd88_ft": pr.get("elev_navd88"),
                "crossing": pr.get("crossing"),
                "design_grade_pct": pr.get("design_grade_pct"),
                "note": pr.get("note", ""),
                "material_id": material_id,
                "unreal_anchor_local_m": to_local_m(
                    geom["coordinates"][0], geom["coordinates"][1],
                    pr.get("elev_navd88") or 0.0),
                "provenance": "derived from ada_route.geojson (read-only)",
            }
            register_actor(
                name="ADANode_" + nm,
                actor_class="point",
                source_file=SRC["ada_route"],
                source_feature_id=fid,
                anchor_xyz_epsg6494_ft=geom["coordinates"][:2],
                z_navd88_ft=pr.get("elev_navd88"),
                material_id=material_id,
                validation_state="landing_concept",
                note=pr.get("kind", "node"),
            )
        else:
            continue
        feats.append({"type": "Feature", "geometry": geom, "properties": props})

    fc = {"type": "FeatureCollection", "crs": CRS6494,
          "name": "ada_route", "features": feats}
    jwrite("geo/ada_route.geojson", fc)
    return {"n_routes": n_routes, "n_nodes": n_nodes}


# ── 4. sightline_table.csv (read straight from validation.json) ─────────────
def build_sightline_table(validation):
    c_rows = validation.get("c_rows", {})
    elevs = validation.get("measured_rows_1_18", {})
    bands = band_status_lookup(validation)
    treads = {f'{f["properties"]["section"]} r{f["properties"]["row"]}': f["properties"]
              for f in jload(SRC["treads"])["features"]}

    cols = ["band", "section", "row", "tread_elev_navd88_ft", "C_mm", "C_bar_mm",
            "seats_kept", "band_a_seats", "pass_frac", "band_status", "sees_bay",
            "sightline_verdict", "fail_reasons", "source"]
    rows = []

    def sort_key(k):
        sec, r = k.split(" r")
        order = {"east": 0, "bend": 1, "south": 2}
        return (order.get(sec, 9), int(r))

    for band_key in sorted(c_rows, key=sort_key):
        sec, r = band_key.split(" r")
        c = c_rows[band_key]
        tp = treads.get(band_key, {})
        binfo = bands.get(band_key, {})
        if c is None:
            verdict = "front_row_no_obstruction"
        elif c >= C_BAR_MM:
            verdict = "PASS"
        else:
            verdict = "WARN"
        rows.append({
            "band": band_key,
            "section": sec,
            "row": int(r),
            "tread_elev_navd88_ft": elevs.get(band_key, tp.get("tread_elev_navd88")),
            "C_mm": c,
            "C_bar_mm": C_BAR_MM,
            "seats_kept": tp.get("seats_kept"),
            "band_a_seats": binfo.get("band_a_seats"),
            "pass_frac": binfo.get("pass_frac"),
            "band_status": binfo.get("status"),
            "sees_bay": tp.get("sees_bay"),
            "sightline_verdict": verdict,
            "fail_reasons": ";".join(binfo.get("fail_reasons", [])),
            "source": "validation.json c_rows/per_band/measured_rows_1_18",
        })

    path = opath("tables/sightline_table.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    warns = [r["band"] for r in rows if r["sightline_verdict"] == "WARN"]
    return {"n_rows": len(rows), "warn_rows": warns,
            "banded_total_a": validation.get("banded", {}).get("A")}


# ── 5. terrain meshes + heightfields ────────────────────────────────────────
def _read_filled(rel, step):
    import numpy as np
    import rasterio
    from rasterio.fill import fillnodata
    with rasterio.open(p(rel)) as r:
        full = r.read(1).astype("float64")
        nod = r.nodata
        res_ft = r.res[0]
        x0, ytop = r.bounds.left, r.bounds.top
    void = (full == nod) if nod is not None else np.zeros(full.shape, bool)
    if void.any():
        full = fillnodata(full, mask=~void, max_search_distance=400)
    if nod is not None:
        full = np.where(full == nod, np.nan, full)
    arr = full[::step, ::step]
    void_d = void[::step, ::step]
    return arr, void_d, res_ft * step, x0, ytop


def build_terrain_mesh(rel, step, name):
    """ENU Z-up metre mesh. Returns stats dict; writes GLB (+OBJ for proposed)."""
    import numpy as np
    import trimesh

    arr, void_d, res_ft, x0, ytop = _read_filled(rel, step)
    ny, nx = arr.shape
    res_m = res_ft * FT2M
    # vertex grid: local metres, x east, y north (rows run north->south)
    xs = (np.arange(nx) * res_ft + x0 - ORIGIN_X) * FT2M
    ys = (ytop - np.arange(ny) * res_ft - ORIGIN_Y) * FT2M
    X, Y = np.meshgrid(xs, ys)
    Z = arr * FT2M
    verts = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])

    def vid(i, j):
        return i * nx + j

    faces = []
    finite = np.isfinite(arr)
    for i in range(ny - 1):
        for j in range(nx - 1):
            if not (finite[i, j] and finite[i, j + 1]
                    and finite[i + 1, j] and finite[i + 1, j + 1]):
                continue
            a, b = vid(i, j), vid(i, j + 1)
            c, d = vid(i + 1, j), vid(i + 1, j + 1)
            faces.append([a, c, b])
            faces.append([b, c, d])
    faces = np.asarray(faces, dtype=np.int64)
    # zero-out non-finite vertices so trimesh doesn't choke on NaN
    verts = np.where(np.isfinite(verts), verts, 0.0)

    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    ensure_dir("terrain")
    glb = opath(f"terrain/terrain_{name}.glb")
    with open(glb, "wb") as fh:
        fh.write(trimesh.exchange.gltf.export_glb(trimesh.Scene(mesh)))
    obj_path = None
    if name == "proposed":
        obj_path = opath(f"terrain/terrain_{name}.obj")
        with open(obj_path, "w") as fh:
            fh.write(trimesh.exchange.obj.export_obj(mesh, include_normals=False))
    zmin = float(np.nanmin(arr))
    zmax = float(np.nanmax(arr))
    return {
        "name": name, "source": rel, "sha256_12": sha12(rel),
        "grid": [int(nx), int(ny)], "step_px": step,
        "res_ft": round(res_ft, 3), "res_m": round(res_m, 4),
        "verts": int(verts.shape[0]), "faces": int(faces.shape[0]),
        "void_frac": round(float(void_d.mean()), 4),
        "z_navd88_ft": [round(zmin, 2), round(zmax, 2)],
        "glb": os.path.relpath(glb, p(OUT)),
        "obj": os.path.relpath(obj_path, p(OUT)) if obj_path else None,
        "frame": "local ENU metres, Z-up; x=east y=north z=NAVD88ft*0.3048; "
                 f"origin EPSG:6494 ({ORIGIN_X}, {ORIGIN_Y}) intl ft",
    }


def build_heightfield(rel, name):
    """Full-res 16-bit heightfield for Unreal Landscape import (.r16 + .png).

    Unreal Landscape RAW import expects 16-bit unsigned, row-major. We record
    the exact NAVD88 ft range and the per-unit Z scale so the landscape Z can be
    reconstructed: navd88_ft = zmin_ft + raw/65535 * (zmax_ft - zmin_ft).
    """
    import numpy as np
    from PIL import Image
    arr, void_d, res_ft, x0, ytop = _read_filled(rel, 1)
    ny, nx = arr.shape
    finite = np.isfinite(arr)
    zmin = float(arr[finite].min())
    zmax = float(arr[finite].max())
    span = max(zmax - zmin, 1e-6)
    q = np.zeros(arr.shape, dtype="float64")
    q[finite] = (arr[finite] - zmin) / span * 65535.0
    q = np.clip(np.round(q), 0, 65535).astype("<u2")
    ensure_dir("terrain")
    r16 = opath(f"terrain/heightfield_{name}.r16")
    q.tofile(r16)
    png = opath(f"terrain/heightfield_{name}.png")
    # 'I;16' is native-endian 16-bit; q is little-endian uint16 (LE host assumed,
    # as is the .r16). frombytes avoids the deprecated fromarray(mode=) path.
    Image.frombytes("I;16", (nx, ny), q.tobytes()).save(png)
    res_m = res_ft * FT2M
    meta = {
        "name": name,
        "source": rel,
        "sha256_12": sha12(rel),
        "format": "16-bit unsigned, little-endian, row-major (N->S rows, W->E cols)",
        "grid": [int(nx), int(ny)],
        "res_ft": round(res_ft, 3),
        "res_m": round(res_m, 4),
        "z_navd88_ft": {"min": round(zmin, 3), "max": round(zmax, 3),
                        "span": round(span, 3)},
        "reconstruct_navd88_ft": "zmin + raw/65535 * span",
        "unreal_landscape": {
            "size_px": [int(nx), int(ny)],
            "xy_scale_cm_per_px": round(res_m * 100.0, 4),
            "z_scale_note": ("Unreal Z 'scale' 100 maps the full 0..65535 raw to "
                             "512 m. To honour NAVD88 ft, set landscape Z scale = "
                             f"{round(span * FT2M * 100.0 / 512.0, 6)} (so 65535 -> "
                             f"{round(span * FT2M, 3)} m span), Z offset = "
                             f"{round(zmin * FT2M * 100.0, 1)} cm."),
        },
        "void_frac": round(float(void_d.mean()), 4),
        "datum": "NAVD88 (Geoid12A), international feet",
        "horizontal_crs": "EPSG:6494 NAD83(2011)/Michigan Central, intl ft",
        "nw_corner_epsg6494_ft": [round(x0, 2), round(ytop, 2)],
        "nw_corner_local_m": to_local_m(x0, ytop, zmin),
        "files": {"raw": os.path.basename(r16), "png": os.path.basename(png)},
        "WARNING": "planning-grade (2015 USGS LiDAR + supplement) - not a survey",
    }
    jwrite(f"terrain/heightfield_{name}.heightfield.json", meta)
    return meta


# ── 6. camera manifest (authoritative viewpoints + derived row eyes) ────────
REQUESTED_VIEWS = ["stage", "row1", "row9", "upper_row", "ada_route", "rim"]

# map canonical viewpoint names -> requested vantage slots
VIEW_MAP = {
    "stage_looking_back_to_audience": "stage",
    "mid_row_audience_to_bay": "row9",
    "upper_rim_down_to_stage": "upper_row",
    "ada_arrival_to_cross_aisle": "ada_route",
    "outside_bowl_from_park_edge": "rim",
    "event_floor_to_treatment_cell": "stage",
}


def build_cameras():
    vps = jload(SRC["viewpoints"])
    cams = []
    covered = set()
    for i, f in enumerate(vps["features"]):
        pr = f["properties"]
        nm = pr["name"]
        slot = VIEW_MAP.get(nm)
        if slot:
            covered.add(slot)
        x, y = f["geometry"]["coordinates"][:2]
        eye = pr.get("camera_elev_navd88")
        tx, ty = pr.get("look_target_x"), pr.get("look_target_y")
        tgt_local = (to_local_m(tx, ty, pr.get("look_target_elev_navd88") or 0.0)
                     if tx is not None else None)
        cams.append({
            "camera_name": "Cam_" + nm,
            "requested_slot": slot,
            "source_file": SRC["viewpoints"],
            "source_feature_id": nm,
            "position_local_m": to_local_m(x, y, eye or 0.0),
            "position_epsg6494_ft": [round(x, 2), round(y, 2)],
            "eye_elev_navd88_ft": eye,
            "eye_height_ft": pr.get("eye_height_ft"),
            "look_azimuth_deg": pr.get("look_azimuth_deg"),
            "look_target_local_m": tgt_local,
            "fov_deg": pr.get("fov_deg_suggested"),
            "description": pr.get("description"),
            "derived": False,
            "provenance": "in_situ_viewpoints.geojson (authoritative camera)",
        })

    # derive any missing requested slots (row1) from tread geometry + eye height
    treads = {f'{f["properties"]["section"]} r{f["properties"]["row"]}': f
              for f in jload(SRC["treads"])["features"]}
    derive = {"row1": "bend r1"}
    EYE_FT = 3.94  # seated eye, matches mid_row viewpoint
    for slot, band_key in derive.items():
        if slot in covered:
            continue
        f = treads.get(band_key)
        if not f:
            continue
        cen = ring_centroid(outer_ring(f["geometry"]))
        elev = f["properties"].get("tread_elev_navd88") or 0.0
        cams.append({
            "camera_name": f"Cam_{slot}_{band_key.replace(' ', '_')}",
            "requested_slot": slot,
            "source_file": SRC["treads"],
            "source_feature_id": f'tread_{band_key.replace(" ", "_r").replace("_r", "_")}',
            "position_local_m": to_local_m(cen[0], cen[1], elev + EYE_FT),
            "position_epsg6494_ft": [round(cen[0], 2), round(cen[1], 2)],
            "eye_elev_navd88_ft": round(elev + EYE_FT, 2),
            "eye_height_ft": EYE_FT,
            "look_azimuth_deg": BAY_VIEW_AZ,
            "look_target_local_m": None,
            "fov_deg": 50,
            "description": f"seated eye at {band_key} looking toward the bay axis",
            "derived": True,
            "provenance": "DERIVED from terrace_treads.geojson centroid + "
                          f"{EYE_FT} ft seated eye (no authoritative viewpoint "
                          "for this slot)",
        })
        covered.add(slot)

    manifest = {
        "schema": "unreal-handoff/camera-manifest/0.1",
        "frame": "positions in local ENU metres, Z-up; azimuth deg clockwise "
                 "from north; bay-view axis = {} deg".format(BAY_VIEW_AZ),
        "requested_slots": REQUESTED_VIEWS,
        "slots_covered": sorted(covered),
        "slots_uncovered": [s for s in REQUESTED_VIEWS if s not in covered],
        "cameras": cams,
    }
    jwrite("manifests/camera_manifest.json", manifest)
    return {"n_cameras": len(cams), "covered": sorted(covered),
            "uncovered": [s for s in REQUESTED_VIEWS if s not in covered]}


# ── 7. material manifest (styles keyed to validation state, read-only) ──────
def build_material_manifest():
    mats = {
        "row_formal": {"label": "Seating row - formal (C >= 90 mm)",
                       "color": "#2e7d32", "keyed_to": "band_status=formal"},
        "row_partial": {"label": "Seating row - partial band",
                        "color": "#f9a825", "keyed_to": "band_status=partial"},
        "row_warn": {"label": "Seating row - sightline WARN (C < 90 mm)",
                     "color": "#ef6c00", "keyed_to": "sightline_verdict=WARN"},
        "row_unknown": {"label": "Seating row - status unknown",
                        "color": "#9e9e9e", "keyed_to": "band_status=unknown"},
        "stage": {"label": "Stage deck", "color": "#37474f",
                  "keyed_to": "zone=stage_core/shoulder"},
        "stage_provisional": {
            "label": "Stage deck - PROVISIONAL (DESIGN_CANON Rule 9 OPEN)",
            "color": "#c62828", "hatch": "diagonal",
            "keyed_to": "rule9_status=open", "must_label": True},
        "event_floor_concept": {"label": "Orchestra / event floor - concept tier",
                                "color": "#bcaaa4", "keyed_to": "concept_tier=true"},
        "treatment_cell_concept": {"label": "Treatment cell - concept tier",
                                   "color": "#4fc3f7", "keyed_to": "concept_tier=true"},
        "bay_view_axis": {"label": f"Bay-view axis ({BAY_VIEW_AZ} deg)",
                          "color": "#01579b", "keyed_to": "reference_axis"},
        "ada_preferred": {"label": "ADA route - preferred concept",
                          "color": "#1565c0", "keyed_to": "preferred=true"},
        "ada_alternative": {"label": "ADA route - alternative concept",
                            "color": "#7e57c2", "keyed_to": "preferred=false"},
        "ada_service": {"label": "ADA service route", "color": "#8d6e63",
                        "keyed_to": "class=service"},
        "ada_landing": {"label": "ADA landing / node", "color": "#90caf9",
                        "keyed_to": "kind=landing"},
        "cutfill_diverging": {
            "label": "Cut/fill overlay (blue=cut, red=fill, white=balanced)",
            "ramp": {"cut_-10ft": "#2166ac", "balanced_0": "#f7f7f7",
                     "fill_+10ft": "#b2182b"},
            "keyed_to": "cutfill_mean_ft (from cut_fill_1ft.tif)"},
        "terrain_existing": {"label": "Existing ground (LiDAR, planning-grade)",
                             "color": "#cfd8dc"},
        "terrain_proposed": {"label": "Proposed grade (planning-grade)",
                             "color": "#d7ccc8"},
    }
    validation_states = {
        "PASS": "#2e7d32", "WARN": "#ef6c00", "FAIL": "#c62828",
        "UNKNOWN": "#9e9e9e", "provisional": "#c62828",
        "concept": "#bcaaa4", "source_of_truth": "#2e7d32",
    }
    manifest = {
        "schema": "unreal-handoff/material-manifest/0.1",
        "note": "Materials are PRESENTATION ONLY. Each is keyed to a validation "
                "attribute READ from the source tables; none re-computes or "
                "overrides a validated state. Provisional/concept tiers MUST "
                "remain visually marked (see must_label).",
        "materials": mats,
        "validation_state_palette": validation_states,
    }
    jwrite("manifests/material_manifest.json", manifest)
    return {"n_materials": len(mats)}


# ── 8. actor manifest + provenance ──────────────────────────────────────────
def write_actor_manifest():
    manifest = {
        "schema": "unreal-handoff/actor-manifest/0.1",
        "note": "Every Unreal actor traces to a source file + feature id. "
                "anchor_local_m is the ENU metre position; anchor_epsg6494_ft is "
                "the georeferenced position for round-trip back to GIS.",
        "frame": "local ENU metres, Z-up; origin EPSG:6494 "
                 f"({ORIGIN_X}, {ORIGIN_Y}) intl ft; ft->m {FT2M}",
        "n_actors": len(ACTORS),
        "actors": ACTORS,
    }
    jwrite("manifests/actor_manifest.json", manifest)
    # flat CSV
    path = opath("manifests/actor_manifest.csv")
    cols = ["actor_name", "actor_class", "source_file", "source_feature_id",
            "source_sha256_12", "anchor_epsg6494_ft_x", "anchor_epsg6494_ft_y",
            "anchor_local_m_x", "anchor_local_m_y", "anchor_local_m_z",
            "z_navd88_ft", "material_id", "validation_state", "provisional", "note"]
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for a in ACTORS:
            w.writerow([
                a["actor_name"], a["actor_class"], a["source_file"],
                a["source_feature_id"], a["source_sha256_12"],
                a["anchor_epsg6494_ft"][0], a["anchor_epsg6494_ft"][1],
                a["anchor_local_m"][0], a["anchor_local_m"][1], a["anchor_local_m"][2],
                a["z_navd88_ft"], a["material_id"], a["validation_state"],
                a["provisional"], a["note"],
            ])
    return {"n_actors": len(ACTORS)}


def write_provenance(stats):
    ds = jload(SRC["design_state"])
    warnings = ds.get("warnings", [])
    sources = {}
    for k, rel in SRC.items():
        sources[k] = {"path": rel, "sha256_12": sha12(rel),
                      "exists": os.path.exists(p(rel))}
    prov = {
        "schema": "unreal-handoff/provenance/0.1",
        "generated": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "generator": "scripts/build_unreal_export.py",
        "git_commit": git_commit(),
        "constants_source": _CONST_SOURCE,
        "authoritative_boundary": (
            "The GIS/design repo is the SINGLE source of truth. This package is "
            "a viewer/export layer. Unreal is NOT source of truth. Any geometry "
            "edited in Unreal must return as a proposal GeoJSON in EPSG:6494 and "
            "pass the existing Python/QGIS gates (scripts/audit_in_situ_package.py "
            "et al.) before it can become design truth."),
        "crs": {
            "horizontal": "EPSG:6494 NAD83(2011)/Michigan Central, INTERNATIONAL feet",
            "vertical": "NAVD88 (Geoid12A), international feet",
            "local_origin_epsg6494_ft": [ORIGIN_X, ORIGIN_Y],
            "ft_to_m": FT2M,
            "local_frame": "ENU, Z-up, metres; x=east y=north z=NAVD88ft*0.3048",
            "reverse_transform": "X_epsg6494_ft = x_local_m/0.3048 + origin_x; "
                                 "Y_epsg6494_ft = y_local_m/0.3048 + origin_y; "
                                 "navd88_ft = z_local_m/0.3048",
        },
        "bay_view_az_deg": BAY_VIEW_AZ,
        "bay_plane_navd88_ft": BAY_PLANE,
        "warnings": warnings,  # carried VERBATIM from design_state.current.json
        "warnings_source": SRC["design_state"],
        "sources": sources,
        "build_stats": stats,
        "regenerate": "python scripts/build_unreal_export.py",
        "verify": "python scripts/verify_unreal_export.py",
    }
    jwrite("manifests/provenance.json", prov)
    return {"n_warnings": len(warnings)}


# ── orchestration ───────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mesh-step", type=int, default=2,
                    help="DEM decimation for terrain meshes (px; default 2 = 2 ft)")
    ap.add_argument("--no-terrain", action="store_true",
                    help="skip terrain meshes/heightfields (geometry/tables only)")
    args = ap.parse_args()

    missing = [k for k in ("treads", "zones", "ada_route", "validation",
                           "viewpoints", "stage_lineage", "design_state")
               if not os.path.exists(p(SRC[k]))]
    if missing:
        print("FATAL: missing authoritative sources:",
              ", ".join(SRC[k] for k in missing), file=sys.stderr)
        return 2

    os.makedirs(p(OUT), exist_ok=True)
    validation = jload(SRC["validation"])
    stats = {}

    print("[1/8] seating rows + splines ...")
    stats["seating"] = build_seating(validation)
    print("      ", stats["seating"])

    print("[2/8] stage / forecourt / treatment / bay-axis ...")
    stats["stage"] = build_stage()
    print("      ", stats["stage"])

    print("[3/8] ADA route + landings ...")
    stats["ada"] = build_ada(validation)
    print("      ", stats["ada"])

    print("[4/8] sightline_table.csv ...")
    stats["sightline"] = build_sightline_table(validation)
    print("      ", stats["sightline"])

    if args.no_terrain:
        print("[5/8] terrain ... SKIPPED (--no-terrain)")
        stats["terrain"] = {"skipped": True}
    elif any(not os.path.exists(p(SRC[k]))
             for k in ("dem_existing", "dem_proposed")):
        print("[5/8] terrain ... SKIPPED (DEM rasters absent)")
        stats["terrain"] = {"skipped": "dem_absent"}
    else:
        print(f"[5/8] terrain meshes (step={args.mesh_step}) + heightfields ...")
        terr = {"meshes": [], "heightfields": []}
        terr["meshes"].append(build_terrain_mesh(SRC["dem_existing"], args.mesh_step, "existing"))
        terr["meshes"].append(build_terrain_mesh(SRC["dem_proposed"], args.mesh_step, "proposed"))
        terr["heightfields"].append(build_heightfield(SRC["dem_existing"], "existing"))
        terr["heightfields"].append(build_heightfield(SRC["dem_proposed"], "proposed"))
        stats["terrain"] = terr
        for m in terr["meshes"]:
            print(f"       mesh {m['name']}: {m['verts']} verts {m['faces']} faces "
                  f"z {m['z_navd88_ft']} ft")

    print("[6/8] camera manifest ...")
    stats["cameras"] = build_cameras()
    print("      ", stats["cameras"])

    print("[7/8] material manifest ...")
    stats["materials"] = build_material_manifest()

    print("[8/8] actor manifest + provenance ...")
    stats["actors"] = write_actor_manifest()
    stats["provenance"] = write_provenance(stats)
    print("      ", stats["actors"], stats["provenance"])

    print(f"\nDONE -> {OUT}/  ({len(ACTORS)} actors)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
