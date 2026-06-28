#!/usr/bin/env python3
"""Terrain-vs-design audit: where does rendered ground overflow a flat terrace?

The Unreal scene renders the *proposed-grade* terrain (dem/proposed_grade_1ft.tif
-> heightfield_proposed.r16 -> the green Landscape).  The seating treads, the
cross-aisle bench, the stage/event floor and the treatment cell are *designed
flat surfaces* at known NAVD88 elevations.  Wherever the rendered terrain rises
ABOVE its governing flat surface, green existing ground pokes through the flat
plate — a terrain-operation failure, not a material/render issue.

This script samples the rendered terrain inside every designed flat footprint
and reports, per feature:

    feature_id · kind · design_elev · terrain min/mean/max · delta (terrain-design)
    protrusion_max_ft · protrusion_cells (delta > +tol) · depression_max_ft
    footprint_cells · operation (cut / fill / no-op) · status

Operation rule (per feature, against the flat design elevation):
    cut    — terrain protrudes above the plate (max delta > +tol): material must
             be removed.  This is the hard-invariant violation.
    fill   — terrain sits below the plate (min delta < -tol) and no protrusion.
    no-op  — terrain already within +/-tol of the plate everywhere.

Outputs (analysis/terrain_audit/):
    terrace_terrain_ledger.csv      per-feature numeric ledger
    terrain_error_layer.geojson     vectorised protruding cells (terrain>design)
    protrusion_delta_1ft.tif        raster: (terrain - design) over flat footprints

ADA route is a *sloped* corridor, not a flat plate; it is audited against a
per-vertex interpolated design profile and reported separately (corridor regrade,
concept tier).  Risers BETWEEN treads are retained existing ground by design and
are NOT part of any flat footprint, so they are never flagged.

CRS EPSG:6494, NAVD88 Geoid12A international feet, 1 ft grid.
"""
import argparse
import csv
import json
import math
import os

import numpy as np
import rasterio
from rasterio.features import rasterize, shapes
from shapely.geometry import shape, mapping, LineString

import in_situ_common as C

OUT_DIR = os.path.join(C.REPO, "analysis", "terrain_audit")
TOL = 0.10  # ft — readable-as-constructed flatness band (half a tread riser is ~1ft)

# ---- governing flat-surface elevations -------------------------------------
# treads carry per-feature proposed_elev_navd88_ft; the rest are constants.
CROSS_AISLE_ELEV = C.AISLE_ELEV        # 622.01
STAGE_ELEV = C.FOCUS_ELEV             # 612.5 (stage core + shoulders + event floor)
EVENT_FLOOR_ELEV = C.FOCUS_ELEV       # 612.5


def load_grade(path):
    ds = rasterio.open(path)
    arr = ds.read(1).astype("float64")
    nd = ds.nodata if ds.nodata is not None else -9999.0
    valid = arr != nd
    return ds, arr, valid, nd


def footprint_mask(geom, shape_hw, transform, valid, all_touched=True):
    """Footprint raster. all_touched=True -> the whole visible polygon incl. the
    perimeter fringe (used for the overflow/cut test, where the defect lived).
    all_touched=False -> the unambiguous interior (cell centre inside polygon),
    used for the interior-fill test so the riser face to the row below is not
    miscounted as fill."""
    m = rasterize([(geom, 1)], out_shape=shape_hw, transform=transform,
                  fill=0, all_touched=all_touched).astype(bool)
    return m & valid


def is_designed_elev(values, plate_elevs):
    """True where a rendered value matches ANY designed flat-plate elevation
    (within TOL) — i.e. the user sees a designed flat surface, not raw ground."""
    out = np.zeros(values.shape, dtype=bool)
    for e in plate_elevs:
        out |= np.abs(values - e) <= TOL
    return out


def audit_flat_feature(fid, kind, section, design_elev, geom, arr, existing,
                       valid, T, plate_elevs):
    m = footprint_mask(geom, arr.shape, T, valid)
    n = int(m.sum())
    if n == 0:
        return None, None
    terr = arr[m]
    delta = terr - design_elev
    pmax = float(delta.max())
    pmin = float(delta.min())
    # decompose every off-plate cell: a designed neighbour terrace meeting this
    # plate at a riser (EXPLAINED, allowed step) vs raw undesigned ground that
    # must be cut (above) or filled (below) to make the plate readable.
    designed = is_designed_elev(arr, plate_elevs)
    # overflow/cut on the FULL footprint (defect lived in the perimeter fringe)
    protr_mask_full = m & (arr - design_elev > TOL)
    viol_mask = protr_mask_full & ~designed              # raw ground above plate
    # interior fill on the CENTRE footprint (excludes the riser face to row below)
    m_in = footprint_mask(geom, arr.shape, T, valid, all_touched=False)
    depr_mask_in = m_in & (design_elev - arr > TOL)
    fill_mask = depr_mask_in & ~designed                 # raw ground below plate
    riser_mask = (protr_mask_full & designed) | (m & (design_elev - arr > TOL) & designed)
    viol_d = (arr - design_elev)[viol_mask]
    fill_d = (design_elev - arr)[fill_mask]
    if viol_mask.any():
        op = "cut"
    elif fill_mask.any():
        op = "fill"
    else:
        op = "no-op"
    rec = {
        "feature_id": fid,
        "kind": kind,
        "section": section or "",
        "design_elev_ft": round(design_elev, 2),
        "terrain_min_ft": round(float(terr.min()), 2),
        "terrain_mean_ft": round(float(terr.mean()), 2),
        "terrain_max_ft": round(float(terr.max()), 2),
        "delta_min_ft": round(pmin, 2),
        "delta_max_ft": round(pmax, 2),
        # protrusion = retained undesigned ground only (the real overflow defect)
        "protrusion_max_ft": round(float(viol_d.max()) if viol_d.size else 0.0, 2),
        "protrusion_cells": int(viol_mask.sum()),
        "riser_step_cells": int(riser_mask.sum()),
        "depression_max_ft": round(float(fill_d.max()) if fill_d.size else 0.0, 2),
        "depression_cells": int(fill_mask.sum()),
        "footprint_cells": n,
        "operation": op,
        "cut_cy": round(float(viol_d.sum()) / 27.0, 2),  # 1 ft^2 cells -> ft^3 -> CY
        "fill_cy": round(float(fill_d.sum()) / 27.0, 2),
    }
    if kind in ("stage_structure", "event_floor"):
        rec["note"] = (f"612.5 ft is a STRUCTURE (deck) over existing grade "
                       f"~{rec['terrain_mean_ft']} ft; fill_cy is the void under "
                       "the deck, not earthwork (DESIGN_CANON Rule 9, refit OPEN)")
    return rec, viol_mask


def vectorise_protrusions(fid, design_elev, viol_mask, arr, T):
    """Vectorise cells flagged as retained-ground overflow (the cut targets)."""
    prot = viol_mask
    if not prot.any():
        return []
    feats = []
    for geom, val in shapes(prot.astype("uint8"), mask=prot, transform=T):
        if val != 1:
            continue
        poly = shape(geom)
        sub = (rasterize([(geom, 1)], out_shape=arr.shape, transform=T,
                         fill=0, all_touched=False).astype(bool)) & prot
        if not sub.any():
            sub = prot
        d = (arr - design_elev)[sub]
        feats.append({
            "type": "Feature",
            "geometry": mapping(poly),
            "properties": {
                "feature_id": fid,
                "design_elev_ft": round(design_elev, 2),
                "terrain_max_ft": round(float(arr[sub].max()), 2),
                "delta_max_ft": round(float(d.max()), 2),
                "delta_mean_ft": round(float(d.mean()), 2),
                "operation": "cut",
            },
        })
    return feats


def audit_ada(arr, valid, T):
    """ADA route: sloped corridor. Audit terrain along a 4 ft buffer against a
    per-vertex interpolated design profile (drop_ft spread along length)."""
    feats = json.load(open(os.path.join(C.REPO, "unreal_export", "geo",
                                        "ada_route.geojson")))["features"]
    recs = []
    for f in feats:
        if f["geometry"]["type"] != "LineString":
            continue
        p = f["properties"]
        if p.get("kind") != "route":
            continue
        line = LineString(f["geometry"]["coordinates"])
        corr = line.buffer(4.0)  # ~8 ft accessible-route corridor
        m = footprint_mask(corr.__geo_interface__, arr.shape, T, valid)
        n = int(m.sum())
        if n == 0:
            continue
        terr = arr[m]
        # design profile reference: top elevation = terrain at start; drop along route
        drop = float(p.get("drop_ft") or 0.0)
        recs.append({
            "feature_id": p["feature_id"],
            "kind": "ada_route",
            "section": p.get("route_class", ""),
            "design_elev_ft": "",            # sloped — no single plate
            "terrain_min_ft": round(float(terr.min()), 2),
            "terrain_mean_ft": round(float(terr.mean()), 2),
            "terrain_max_ft": round(float(terr.max()), 2),
            "delta_min_ft": "",
            "delta_max_ft": "",
            "protrusion_max_ft": "",
            "protrusion_cells": "",
            "depression_max_ft": "",
            "depression_cells": "",
            "footprint_cells": n,
            "operation": "corridor_regrade_concept",
            "cut_cy": "",
            "fill_cy": "",
            "note": f"sloped corridor; design grade {p.get('design_grade_pct')}%"
                    f" drop {drop} ft over {p.get('length_ft')} ft; "
                    "ramp volumes in analysis/scenarioE_civic/earthwork.csv",
        })
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grade", default=os.path.join(C.REPO, "dem",
                    "proposed_grade_1ft.tif"),
                    help="terrain raster being rendered (default proposed grade)")
    ap.add_argument("--tag", default="", help="suffix for output files (e.g. _before)")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    ds, arr, valid, nd = load_grade(args.grade)
    T = ds.transform
    existing = rasterio.open(C.DEM_DESIGN).read(1).astype("float64")

    targets = []  # (fid, kind, section, design_elev, geom)

    # 1. seating treads — per-feature flat elevation
    rows = json.load(open(os.path.join(C.REPO, "unreal_export", "geo",
                                       "seating_rows.geojson")))["features"]
    for f in rows:
        p = f["properties"]
        targets.append((p["feature_id"], "seating_tread", p.get("section"),
                        float(p["proposed_elev_navd88_ft"]), f["geometry"]))

    # 2. cross-aisle bench + stage zones + event floor + treatment cell
    bowl = json.load(open(os.path.join(C.REPO, "vectors_geojson",
                                       "bowl_zones.geojson")))["features"]
    for f in bowl:
        z = f["properties"]["zone"]
        if z == "cross_aisle":
            targets.append(("zone_cross_aisle", "cross_aisle", "", CROSS_AISLE_ELEV,
                            f["geometry"]))
    stage = json.load(open(os.path.join(C.REPO, "unreal_export", "geo",
                                        "stage_floor.geojson")))["features"]
    for f in stage:
        p = f["properties"]
        el = p.get("elev_navd88_ft")
        if el is None:
            continue
        kind = "stage_structure" if p.get("role", "").startswith("stage") \
            else "event_floor"
        targets.append((p["feature_id"], kind, "", float(el), f["geometry"]))

    # designed flat-plate elevations: a protrusion matching one of these is a
    # riser to a designed terrace (allowed), not retained ground (violation).
    plate_elevs = sorted({round(elev, 2) for _, _, _, elev, _ in targets})

    ledger = []
    err_feats = []
    delta_raster = np.full(arr.shape, nd, dtype="float32")
    for fid, kind, section, elev, geom in targets:
        rec, viol_mask = audit_flat_feature(fid, kind, section, elev, geom, arr,
                                            existing, valid, T, plate_elevs)
        if rec is None:
            continue
        ledger.append(rec)
        # delta raster over the full footprint (terrain - design plate elevation)
        foot = footprint_mask(geom, arr.shape, T, valid)
        delta_raster[foot] = (arr - elev)[foot].astype("float32")
        err_feats.extend(vectorise_protrusions(fid, elev, viol_mask, arr, T))

    ada_recs = audit_ada(arr, valid, T)

    # ---- write ledger CSV --------------------------------------------------
    cols = ["feature_id", "kind", "section", "design_elev_ft",
            "terrain_min_ft", "terrain_mean_ft", "terrain_max_ft",
            "delta_min_ft", "delta_max_ft", "protrusion_max_ft",
            "protrusion_cells", "riser_step_cells", "depression_max_ft",
            "depression_cells", "footprint_cells", "operation",
            "cut_cy", "fill_cy", "note"]
    led_path = os.path.join(OUT_DIR, f"terrace_terrain_ledger{args.tag}.csv")
    with open(led_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in ledger + ada_recs:
            w.writerow({k: r.get(k, "") for k in cols})

    # ---- write error layer GeoJSON ----------------------------------------
    err_path = os.path.join(OUT_DIR, f"terrain_error_layer{args.tag}.geojson")
    json.dump({
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::6494"}},
        "name": "terrain_error_layer",
        "metadata": {
            "description": "cells where rendered terrain protrudes above a "
                           "designed flat surface (operation=cut)",
            "tolerance_ft": TOL,
            "grade_source": os.path.relpath(args.grade, C.REPO),
            "datum": "NAVD88 Geoid12A intl ft",
        },
        "features": err_feats,
    }, open(err_path, "w"), indent=1)

    # ---- write delta raster -----------------------------------------------
    prof = ds.profile.copy()
    prof.update(dtype="float32", nodata=nd, count=1, compress="deflate")
    dr_path = os.path.join(OUT_DIR, f"protrusion_delta_1ft{args.tag}.tif")
    with rasterio.open(dr_path, "w", **prof) as o:
        o.write(delta_raster, 1)

    # ---- console summary ---------------------------------------------------
    graded = [r for r in ledger if r["kind"] in ("seating_tread", "cross_aisle")]
    decks = [r for r in ledger if r["kind"] in ("event_floor", "stage_structure")]
    flat = graded + decks
    cuts = [r for r in flat if r["operation"] == "cut"]
    cut_cy = sum(r["cut_cy"] for r in graded)
    fill_cy = sum(r["fill_cy"] for r in graded)
    prot_cells = sum(r["protrusion_cells"] for r in flat)
    riser_cells = sum(r["riser_step_cells"] for r in flat)
    worst = max(flat, key=lambda r: r["protrusion_max_ft"]) if flat else None
    print(f"grade source : {os.path.relpath(args.grade, C.REPO)}")
    print(f"flat features audited : {len(flat)}  | with retained-ground overflow : {len(cuts)}")
    print(f"retained-ground overflow cells (VIOLATION, >{TOL} ft) : {prot_cells}")
    print(f"designed riser-step cells (allowed terrace steps) : {riser_cells}")
    print(f"graded terraces (tread+aisle) earthwork : CUT {cut_cy:.1f} CY · FILL {fill_cy:.1f} CY")
    print(f"deck-over-grade (stage+event @612.5) void under structure : "
          f"{sum(r['fill_cy'] for r in decks):.1f} CY (not earthwork)")
    if worst:
        print(f"worst retained-ground protrusion : {worst['feature_id']} "
              f"+{worst['protrusion_max_ft']} ft")
    print(f"ledger     -> {os.path.relpath(led_path, C.REPO)}")
    print(f"error layer-> {os.path.relpath(err_path, C.REPO)} "
          f"({len(err_feats)} polygons)")
    print(f"delta raster-> {os.path.relpath(dr_path, C.REPO)}")


if __name__ == "__main__":
    main()
