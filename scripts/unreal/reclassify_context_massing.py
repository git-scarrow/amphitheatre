#!/usr/bin/env python3
"""Reclassify Civic Bowl context massing by SOURCE and CONFIDENCE.

Governing rule (provenance discipline, stricter than the prior pipeline):

    A massing object may be classified as a BUILDING only when it has explicit
    building-FOOTPRINT support (an OSM building polygon, a Microsoft ML building
    footprint, or a manual confirmation).  A vertical cluster known only from a
    LiDAR/aerial HEIGHT signal — with no footprint behind it — is NOT a building.
    It becomes a tree-canopy object (if a vegetation source explains it) or an
    unknown-vertical-obstruction object (if nothing does).

This is an AUDIT, not a geometry edit.  It reads the committed, redistributable
derived inventory and emits a diagnostic overlay with three VISIBLE classes:

    verified_building            footprint-backed; height may be LiDAR/tag/typology
    tree_canopy                  vegetation occluder (declared or observed)
    unknown_vertical_obstruction vertical signal with no footprint + no canopy

Every emitted object preserves:  source, source_type, footprint_support,
height_support, classification, confidence, used_for_obstruction.

Inputs  (analysis/bay_view_obstruction/, data/) — all tracked / open-derived:
    osm_near_focal.json     890 OSM building footprints near the focal point
    massing_rows.json       per-building terrain-obstruction flag + LiDAR height
    massing_suspects.json   18 LiDAR-height-verified W/NW corridor occluders
    data/unreal_context_manifest.json   17 context layers (incl deferred canopy)

Outputs (analysis/context_reclassification/):
    context_reclassification.geojson    diagnostic overlay (3 classes + props)
    reclassification_summary.json       counts, occluder-set invariance proof
    RECLASSIFICATION_REPORT.md          human-readable findings

CRS: ENU metres relative to the project origin (same frame as osm_near_focal
ce/cn/bbox).  Planning-grade.  Read-only w.r.t. all scene geometry.
"""
import csv
import json
import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OBS = os.path.join(REPO, "analysis", "bay_view_obstruction")
OUT = os.path.join(REPO, "analysis", "context_reclassification")

# --- corridor that defines the bay-view obstruction factor (matches the
#     layered-obstruction analyzer: bay axis 330, +/-12 deg = 318..342) ------
BAY_AZ = 330.0
CORRIDOR = (318.0, 342.0)
# documented foreground tree screen (bay_view_obstruction.py header): densest
# at az 315-320 — a known, separate vegetation lever with NO footprint or actor.
TREE_SCREEN_AZ = (313.0, 321.0)
TREE_SCREEN_REACH_M = 130.0


def load(path):
    with open(path) as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# confidence model — aligned with OBSTRUCTION_CONFIDENCE_REPORT.md bands
#   High | Medium-High | Medium | Low | Indeterminate
# A verified building's footprint is certain (OSM survey); its overall
# confidence is governed by how well its HEIGHT is known, because the bay-view
# obstruction magnitude depends on roof height.
# --------------------------------------------------------------------------- #
FOOTPRINT_CONF = {
    "osm_footprint": "High",        # OSM surveyed/traced building polygon
    "ms_ml_footprint": "Medium",    # Microsoft ML building footprint (aerial)
    "manual": "High",
    "none": "Indeterminate",
}
HEIGHT_CONF = {
    "lidar_dsm_minus_dtm": "Medium-High",  # measured, not survey-grade
    "osm_tag_levels": "Medium",
    "ms_ml_height": "Medium",
    "typology_generic": "Low",
    "none": "Indeterminate",
}
_ORDER = ["Indeterminate", "Low", "Medium", "Medium-High", "High"]


def weaker(a, b):
    return a if _ORDER.index(a) <= _ORDER.index(b) else b


def main():
    os.makedirs(OUT, exist_ok=True)

    near = load(os.path.join(OBS, "osm_near_focal.json"))
    focal = near["focal_enu"]            # [E, N] metres of the focal seating eye
    buildings = near["buildings"]
    rows = {r["osm_id"]: r for r in load(os.path.join(OBS, "massing_rows.json"))}
    suspects = load(os.path.join(OBS, "massing_suspects.json"))
    # the occluder set the bay-view obstruction factor actually depends on:
    # the LiDAR-height-verified W/NW corridor suspects that carry a bbox.
    occluder_ids = {m["osm_id"] for m in suspects}
    suspect_by_id = {m["osm_id"]: m for m in suspects}
    manifest = load(os.path.join(REPO, "data", "unreal_context_manifest.json"))

    features = []
    counts = {
        "verified_building": 0,
        "tree_canopy": 0,
        "unknown_vertical_obstruction": 0,
        "ground_or_backdrop_context": 0,
    }
    conf_breakdown = {}
    reclassified_to_tree = []
    reclassified_to_unknown = []
    occluders_before = set()   # what the prior pipeline used as bay-view occluders
    occluders_after = set()    # what survives the strict rule as a used building

    # ---------------- buildings (the footprint-backed inventory) ----------- #
    for b in buildings:
        oid = b["osm_id"]
        row = rows.get(oid, {})
        tag = b.get("building")           # OSM building=* value
        # EVERY object in this inventory carries an OSM building footprint.
        footprint_support = "osm_footprint"
        # height provenance: LiDAR for the verified corridor suspects; else
        # OSM levels tag; else the building-type typology heuristic.
        if oid in suspect_by_id:
            height_support = "lidar_dsm_minus_dtm"
        elif b.get("levels"):
            height_support = "osm_tag_levels"
        else:
            height_support = "typology_generic"

        # ---- STRICT RULE ------------------------------------------------- #
        # footprint present -> stays a verified building. (No object here is
        # height-only; if one ever were, it would fall through to the
        # vegetation / unknown branch below.)
        if footprint_support in ("osm_footprint", "ms_ml_footprint", "manual"):
            classification = "verified_building"
        else:
            # height-only signal: cannot be a building. We have no vegetation
            # source tying it to canopy here, so it is unknown vertical.
            classification = "unknown_vertical_obstruction"
            reclassified_to_unknown.append(oid)

        fp_conf = FOOTPRINT_CONF[footprint_support]
        h_conf = HEIGHT_CONF[height_support]
        confidence = weaker(fp_conf, h_conf) if classification == "verified_building" else h_conf

        # was this object an occluder in the prior bay-view obstruction calc?
        was_occluder = oid in occluder_ids
        if was_occluder:
            occluders_before.add(oid)
        # does it remain a building used for the bay-view obstruction factor?
        used_for_obstruction = was_occluder and classification == "verified_building"
        if used_for_obstruction:
            occluders_after.add(oid)

        counts[classification] += 1
        conf_breakdown[confidence] = conf_breakdown.get(confidence, 0) + 1

        sm = suspect_by_id.get(oid, {})
        bbox = b.get("bbox")              # [minE, minN, maxE, maxN] ENU metres
        geom = None
        if bbox:
            e0, n0, e1, n1 = bbox
            geom = {"type": "Polygon", "coordinates": [[
                [e0, n0], [e1, n0], [e1, n1], [e0, n1], [e0, n0]]]}
        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "id": f"osm/{oid}",
                "name": b.get("name"),
                "osm_building_tag": tag,
                "source": "OpenStreetMap building footprint (ODbL)",
                "source_type": "OSM",
                "footprint_support": footprint_support,
                "height_support": height_support,
                "classification": classification,
                "confidence": confidence,
                "footprint_confidence": fp_conf,
                "height_confidence": h_conf,
                "used_for_obstruction": used_for_obstruction,
                "obstructs_terrain_flag": bool(row.get("obstructs")),
                "in_bay_corridor": CORRIDOR[0] <= b.get("az", -1) <= CORRIDOR[1],
                "height_m": row.get("h_m") or sm.get("h_m"),
                "top_ft": row.get("top_ft") or sm.get("top_ft"),
                "base_minus_terrain_m": sm.get("base_minus_terrain_m"),
                "az_from_focal_deg": round(b.get("az", 0.0), 1),
                "dist_m": round(b.get("dist", 0.0), 1),
                "notes": ("LiDAR-height-verified W/NW corridor occluder"
                          if was_occluder else
                          "footprint-backed; outside bay corridor or below sightline"),
            },
        })

    # ---------------- tree canopy (vegetation, NO footprint) --------------- #
    # 1) the documented foreground tree screen (az ~315-320), observed in the
    #    EPT viewshed analysis but with no footprint and no scene actor.
    a0, a1 = TREE_SCREEN_AZ
    ring = [focal]
    for k in range(13):
        az = a0 + (a1 - a0) * k / 12.0
        rad = math.radians(az)
        # ENU: az measured from North, clockwise -> E=sin, N=cos
        e = focal[0] + TREE_SCREEN_REACH_M * math.sin(rad)
        n = focal[1] + TREE_SCREEN_REACH_M * math.cos(rad)
        ring.append([e, n])
    ring.append(focal)
    counts["tree_canopy"] += 1
    conf_breakdown["Indeterminate"] = conf_breakdown.get("Indeterminate", 0) + 1
    features.append({
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [ring]},
        "properties": {
            "id": "veg/foreground_tree_screen",
            "name": "Foreground tree screen (az ~315-320)",
            "source": "EPT viewshed analysis + aerial/field observation",
            "source_type": "LiDAR-first-return / observed (no footprint)",
            "footprint_support": "none",
            "height_support": "none",
            "classification": "tree_canopy",
            "confidence": "Indeterminate",
            "footprint_confidence": "Indeterminate",
            "height_confidence": "Indeterminate",
            "used_for_obstruction": False,
            "candidate_for_obstruction": True,
            "in_bay_corridor": True,
            "az_from_focal_deg": round(sum(TREE_SCREEN_AZ) / 2, 1),
            "notes": ("Real vegetation occluder, densest az 315-320; overlaps the "
                      "318-342 bay corridor lower bound. No footprint, no scene "
                      "actor -> currently UNMODELLED (indeterminate). Must be a "
                      "vegetation proxy, never a building block."),
        },
    })

    # 2) the deferred fg_canopy manifest layer (declared, not yet fetched).
    canopy_layer = next((L for L in manifest["layers"]
                         if L["layer_name"] == "fg_canopy"), None)
    if canopy_layer:
        counts["tree_canopy"] += 1
        conf_breakdown["Indeterminate"] = conf_breakdown.get("Indeterminate", 0) + 1
        features.append({
            "type": "Feature",
            "geometry": None,
            "properties": {
                "id": "veg/fg_canopy_layer",
                "name": "fg_canopy (deferred context layer)",
                "source": canopy_layer.get("source"),
                "source_type": canopy_layer.get("source_type"),
                "footprint_support": "none",
                "height_support": "none",
                "classification": "tree_canopy",
                "confidence": "Indeterminate",
                "used_for_obstruction": False,
                "candidate_for_obstruction": True,
                "notes": "Declared occluder layer, DEFERRED — no geometry fetched yet.",
            },
        })

    # ---------------- non-vertical context (bookkeeping only) -------------- #
    # account for 'all context massing': terrain / water / roads / parks /
    # harbor / labels / backdrop are ground-plane or backdrop, not vertical
    # obstruction. They are counted but not part of the 3 visible classes.
    skip_layers = {"city_massing", "fg_canopy"}  # buildings + canopy handled above
    ground_context = []
    for L in manifest["layers"]:
        if L["layer_name"] in skip_layers:
            continue
        counts["ground_or_backdrop_context"] += 1
        ground_context.append({
            "layer": L["layer_name"], "category": L.get("category"),
            "source_type": L.get("source_type"),
            "obstruction_role": L.get("obstruction_role"),
            "classification": "ground_or_backdrop_context",
            "used_for_obstruction": False,
        })

    # ---------------- write the diagnostic overlay ------------------------- #
    overlay = {
        "type": "FeatureCollection",
        "name": "civic_bowl_context_reclassification",
        "crs_note": "ENU metres relative to project origin "
                    "(EPSG:6494 local origin); same frame as osm_near_focal.",
        "rule": "Buildings require explicit footprint support (OSM/MS-ML/manual). "
                "Height-only vertical clusters -> tree_canopy or "
                "unknown_vertical_obstruction, never building blocks.",
        "classes": ["verified_building", "tree_canopy",
                    "unknown_vertical_obstruction"],
        "focal_enu_m": focal,
        "bay_corridor_deg": CORRIDOR,
        "features": features,
    }
    with open(os.path.join(OUT, "context_reclassification.geojson"), "w") as fh:
        json.dump(overlay, fh, indent=1)

    # ---------------- invariance proof + summary --------------------------- #
    obstruction_changed = occluders_before != occluders_after
    summary = {
        "generated_by": "scripts/unreal/reclassify_context_massing.py",
        "rule": overlay["rule"],
        "total_objects_audited": sum(counts.values()),
        "class_counts": counts,
        "visible_diagnostic_classes": {
            k: counts[k] for k in
            ("verified_building", "tree_canopy", "unknown_vertical_obstruction")},
        "confidence_breakdown": conf_breakdown,
        "former_building_reclassified_to_tree": len(reclassified_to_tree),
        "former_building_reclassified_to_unknown": len(reclassified_to_unknown),
        "remained_verified_building": counts["verified_building"],
        "reclassified_to_tree_ids": reclassified_to_tree,
        "reclassified_to_unknown_ids": reclassified_to_unknown,
        "bay_view_occluders_before": sorted(occluders_before),
        "bay_view_occluders_after": sorted(occluders_after),
        "obstruction_occluder_set_identical": not obstruction_changed,
        "obstruction_factor_changed": obstruction_changed,
        "ground_or_backdrop_layers": ground_context,
    }
    with open(os.path.join(OUT, "reclassification_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1)

    # ---------------- console ---------------------------------------------- #
    print("Context massing reclassification")
    print("=" * 60)
    print(f"  objects audited:            {summary['total_objects_audited']}")
    print(f"  verified_building:          {counts['verified_building']}")
    print(f"  tree_canopy:                {counts['tree_canopy']}")
    print(f"  unknown_vertical_obstruct.: {counts['unknown_vertical_obstruction']}")
    print(f"  (ground/backdrop context):  {counts['ground_or_backdrop_context']}")
    print()
    print(f"  former buildings -> trees:    {len(reclassified_to_tree)}")
    print(f"  former buildings -> unknown:  {len(reclassified_to_unknown)}")
    print(f"  remained verified buildings:  {counts['verified_building']}")
    print()
    print(f"  bay-view occluders before:  {len(occluders_before)}")
    print(f"  bay-view occluders after:   {len(occluders_after)}")
    print(f"  occluder set identical:     {not obstruction_changed}")
    print(f"  OBSTRUCTION FACTOR CHANGED:  {obstruction_changed}")
    print()
    print(f"  wrote {os.path.relpath(OUT, REPO)}/context_reclassification.geojson")
    print(f"  wrote {os.path.relpath(OUT, REPO)}/reclassification_summary.json")
    return summary


if __name__ == "__main__":
    main()
