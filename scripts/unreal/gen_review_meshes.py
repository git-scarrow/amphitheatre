#!/usr/bin/env python3
"""Stage CivicBowl review meshes + a deterministic scene plan from tracked sources.

OFFLINE (no Unreal). Reads the gated handoff package (``unreal_export/`` +
``data/unreal_handoff_manifest.json``), transforms each feature from EPSG:6494
international feet into the local-ENU-metre frame, writes one OBJ mesh per actor
(plus one shared point-marker mesh and the two terrain meshes), and emits
``scene_plan.json`` — the complete, deterministic spec the in-editor assembler
(``ue_civicbowl.py``) consumes.

What it builds (v0 — see civicbowl_common.SCENE_SPEC):
  terrain (2)  seating (45)  stage slabs (5)  bay-view axis+focal (2)
  ADA route ribbons (8)  ADA landing markers (31)  cameras (7, plan only)
TODO groups (geometry not yet in unreal_export/geo/): treatment cell, event floor,
human-scale refs — recorded in the plan as deferred, not built.

Determinism: output is sorted by feature id and carries source sha256(12) for
provenance but no timestamps, so ``gen`` + diff is a reproducibility check.

Usage:
    python scripts/unreal/gen_review_meshes.py            # -> build/unreal_scene/
    python scripts/unreal/gen_review_meshes.py --out DIR --repo /path/to/amphitheatre
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

import civicbowl_common as cb

try:
    import numpy as np
    import shapely.geometry as sg
    import trimesh
except Exception as exc:  # pragma: no cover - dependency guard
    print(f"[gen] missing geometry dep ({exc.__class__.__name__}: {exc}).\n"
          "      Install into the repo venv: shapely trimesh numpy mapbox_earcut",
          file=sys.stderr)
    raise

SLAB_THICKNESS_M = 0.15      # crude visible thickness for footprint slabs
RIBBON_WIDTH_M = 1.2         # ADA ribbon width (visual proxy, not a code width)
MARKER_SIZE_M = 0.6          # shared cube marker edge for point actors

# ENU(right-handed) -> UE(left-handed) as a 4x4 (X=North, Y=East, Z=Up). The
# determinant is -1, so trimesh flips triangle winding on apply_transform and
# normals stay outward. Baking this into the meshes (and into marker anchors +
# camera coords) makes the UE scene geographically faithful, not mirror-imaged.
UE_MAT = np.array([[r[0], r[1], r[2], 0.0] for r in cb.ENU_TO_UE_LINEAR] + [[0, 0, 0, 1.0]], float)


def _to_ue(mesh):
    """Apply the ENU->UE handedness-correct map to a baked (ENU) mesh, in place."""
    mesh.apply_transform(UE_MAT)
    return mesh


# ── geometry helpers (all in local ENU metres) ──────────────────────────────
def _enu_ring(coords) -> list[tuple[float, float]]:
    return [cb.ft_xy_to_enu(x, y) for x, y in [(c[0], c[1]) for c in coords]]


def _polygon_xy(geom: dict):
    """Yield shapely Polygons (exterior only, ENU metres) for Polygon/MultiPolygon."""
    t = geom["type"]
    if t == "Polygon":
        yield sg.Polygon(_enu_ring(geom["coordinates"][0]))
    elif t == "MultiPolygon":
        for poly in geom["coordinates"]:
            yield sg.Polygon(_enu_ring(poly[0]))


def slab_mesh(geom: dict, z_top_m: float):
    """Extrude polygon footprint(s) into a thin slab whose TOP sits at z_top_m."""
    parts = []
    for poly in _polygon_xy(geom):
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            continue
        m = trimesh.creation.extrude_polygon(poly, height=SLAB_THICKNESS_M)
        m.apply_translation((0.0, 0.0, z_top_m - SLAB_THICKNESS_M))
        parts.append(m)
    if not parts:
        return None
    return _to_ue(trimesh.util.concatenate(parts))


def ribbon_mesh(geom: dict, z_m: float):
    """Buffer a LineString into a flat ribbon slab at z_m (ENU metres)."""
    coords = geom["coordinates"]
    line = sg.LineString(_enu_ring(coords))
    poly = line.buffer(RIBBON_WIDTH_M / 2.0, cap_style=2, join_style=2)
    if poly.is_empty:
        return None
    m = trimesh.creation.extrude_polygon(poly, height=SLAB_THICKNESS_M)
    m.apply_translation((0.0, 0.0, z_m - SLAB_THICKNESS_M))
    return _to_ue(m)


def marker_mesh():
    return trimesh.creation.box(extents=(MARKER_SIZE_M, MARKER_SIZE_M, MARKER_SIZE_M))


def feature_z_m(feat: dict, actor: dict | None) -> float | None:
    """Resolve a *real* actor z (metres) from elevation props or a non-zero anchor.

    Returns None when no real elevation exists (e.g. ADA route lines and the
    bay-view axis carry anchor z == 0 in the manifest) — the caller then drapes
    the actor onto a data-derived datum rather than dropping it to sea level.
    """
    props = feat.get("properties") or {}
    for key in ("proposed_elev_navd88_ft", "elev_navd88_ft", "z_navd88_ft"):
        if props.get(key) is not None:
            return cb.ft_z_to_m(float(props[key]))
    if actor and actor.get("anchor_local_m") and abs(float(actor["anchor_local_m"][2])) > 1.0:
        return float(actor["anchor_local_m"][2])  # already metres
    return None


def _material_for(actor: dict | None, props: dict, default: str) -> dict:
    """Material record (id + color + flags) from the manifest actor; else a default."""
    mid = (actor or {}).get("material_id") or default
    return {"id": mid}


# ── per-layer builders ───────────────────────────────────────────────────────
def build(root: str, out: str) -> dict:
    mesh_dir = os.path.join(out, "meshes")
    os.makedirs(mesh_dir, exist_ok=True)
    aidx = cb.actor_index(root)
    mats = cb.load_json(os.path.join(root, "unreal_export/manifests/material_manifest.json"))["materials"]

    def color(mid):  # presentation only; applied later (materials are a follow-on)
        m = mats.get(mid, {})
        return {"color": m.get("color"), "hatch": m.get("hatch"), "must_label": m.get("must_label", False)}

    actors: list[dict] = []
    warnings: list[str] = []

    # ── elevation datums for actors the manifest leaves at z==0 ──────────────
    # ADA route lines + the bay-view axis/focal carry anchor z==0; drape them on
    # real, data-derived elevations instead of NAVD88 0 ft (sea level).
    ada_feats = cb.geojson_features(os.path.join(root, "unreal_export/geo/ada_route.geojson"))
    landing_z: dict[str, list[float]] = {}
    for f in ada_feats:
        if f["geometry"]["type"] != "Point":
            continue
        fid = cb.feature_id(f) or ""
        z = feature_z_m(f, aidx.get(fid))
        if z is not None and "_landing_" in fid:
            landing_z.setdefault(fid.rsplit("_landing_", 1)[0], []).append(z)
    stage_zs = [cb.ft_z_to_m(float((f["properties"] or {}).get("elev_navd88_ft")))
                for f in cb.geojson_features(os.path.join(root, "unreal_export/geo/stage_floor.geojson"))
                if f["geometry"]["type"] in ("Polygon", "MultiPolygon")
                and (f["properties"] or {}).get("elev_navd88_ft") is not None]
    stage_datum = sum(stage_zs) / len(stage_zs) if stage_zs else 186.0

    def route_z(fid: str) -> float:
        zs = landing_z.get(fid)
        if zs:
            return sum(zs) / len(zs)
        warnings.append(f"ada {fid}: no landings, draped on stage datum {stage_datum:.1f}m")
        return stage_datum

    def emit_mesh(name: str, mesh, group: str, mid: str, val: str, prov: bool,
                  tags: list[str], src: dict, anchor=None):
        rel = f"meshes/{name}.obj"
        if mesh is not None:
            mesh.export(os.path.join(out, rel), file_type="obj")
        actors.append({
            "name": name,
            "group": group,
            "mesh": rel if mesh is not None else None,
            "place_at_anchor": anchor,            # [x,y,z] metres, for marker actors
            "scale": cb.UE_SCALE,
            "material": {"id": mid, **color(mid)},
            "validation_state": val,
            "provisional": prov,
            "tags": sorted(set(tags)),
            "source": src,
        })

    # 1) seating (45 polygons) ------------------------------------------------
    sp = "unreal_export/geo/seating_rows.geojson"
    for feat in sorted(cb.geojson_features(os.path.join(root, sp)), key=cb.feature_id):
        fid = cb.feature_id(feat); a = aidx.get(fid)
        z = feature_z_m(feat, a)
        if z is None:
            z = stage_datum; warnings.append(f"seating {fid}: z draped on datum")
        m = slab_mesh(feat["geometry"], z)
        mid = (a or {}).get("material_id", "row_unknown")
        emit_mesh(f"Seating_{fid}", m, cb.SCENE_SPEC["seating"]["folder"], mid,
                  (a or {}).get("validation_state", "unknown"), bool((a or {}).get("provisional")),
                  ["acceptance:accepted_readonly", "PLANNING-GRADE", f"material:{mid}",
                   f"row:{(feat['properties'] or {}).get('row')}"],
                  {"file": sp, "feature_id": fid, "sha12": cb.sha256_12(os.path.join(root, sp))})

    # 2) stage slabs + 3) bay-view axis/focal (from stage_floor.geojson) ------
    stp = "unreal_export/geo/stage_floor.geojson"
    sha = cb.sha256_12(os.path.join(root, stp))
    for feat in sorted(cb.geojson_features(os.path.join(root, stp)), key=lambda f: cb.feature_id(f) or ""):
        fid = cb.feature_id(feat); a = aidx.get(fid); gt = feat["geometry"]["type"]
        props = feat.get("properties") or {}
        z = feature_z_m(feat, a)
        if z is None:  # bay-view axis/focal carry no elevation -> stage datum
            z = stage_datum; warnings.append(f"stage/{fid}: z draped on stage datum")
        if gt in ("Polygon", "MultiPolygon"):
            # stage_floor.geojson holds 3 stage zones + the treatment cell + the
            # event floor; route each to its own folder/material from the manifest.
            mid = (a or {}).get("material_id") or ("stage_provisional" if props.get("rule9_status") == "open"
                                                   or props.get("provisional") else "stage")
            val = (a or {}).get("validation_state") or ("provisional" if props.get("provisional") else "stage")
            prov = bool((a or {}).get("provisional", props.get("provisional", True)))
            if mid == "treatment_cell_concept" or "treatment_cell" in (fid or ""):
                group, accept, name = cb.SCENE_SPEC["treatment_cell"]["folder"], "concept", f"TreatmentCell_{fid}"
            elif mid == "event_floor_concept" or "event_floor" in (fid or "") or "orchestra" in (fid or ""):
                group, accept, name = cb.SCENE_SPEC["event_floor"]["folder"], "concept", f"EventFloor_{fid}"
            else:
                group, accept, name = cb.SCENE_SPEC["stage"]["folder"], "proposal_editable", f"Stage_{fid}"
            tags = [f"acceptance:{accept}", "PLANNING-GRADE", f"material:{mid}"]
            if mid == "stage_provisional" or props.get("rule9_status") == "open":
                tags += ["Rule-9-OPEN", "must_label"]
            if accept == "concept":
                tags += ["concept_tier", "must_label"]
            emit_mesh(name, slab_mesh(feat["geometry"], z), group, mid, val, prov, tags,
                      {"file": stp, "feature_id": fid, "sha12": sha})
        elif gt == "LineString":  # bay-view axis (reference)
            mid = (a or {}).get("material_id", "bay_view_axis")
            emit_mesh(f"Ref_{fid}", ribbon_mesh(feat["geometry"], z),
                      cb.SCENE_SPEC["bay_view_axis"]["folder"], mid,
                      (a or {}).get("validation_state", "reference_axis"), False,
                      ["acceptance:reference", f"material:{mid}", "reference_only"],
                      {"file": stp, "feature_id": fid, "sha12": sha})
        elif gt == "Point":  # focal point (reference)
            mid = (a or {}).get("material_id", "bay_view_axis")
            x, y = cb.ft_xy_to_enu(*feat["geometry"]["coordinates"][:2])
            emit_mesh(f"Ref_{fid}", None, cb.SCENE_SPEC["bay_view_axis"]["folder"], mid,
                      (a or {}).get("validation_state", "reference_axis"), False,
                      ["acceptance:reference", f"material:{mid}", "reference_only", "marker"],
                      {"file": stp, "feature_id": fid, "sha12": sha}, anchor=list(cb.enu_to_ue(x, y, z)))

    # 4) ADA routes (8 lines) + landings (31 points) --------------------------
    adp = "unreal_export/geo/ada_route.geojson"
    sha = cb.sha256_12(os.path.join(root, adp))
    for feat in sorted(cb.geojson_features(os.path.join(root, adp)), key=lambda f: cb.feature_id(f) or ""):
        fid = cb.feature_id(feat); a = aidx.get(fid); gt = feat["geometry"]["type"]
        mid = (a or {}).get("material_id", "ada_preferred" if gt == "LineString" else "ada_landing")
        if gt == "LineString":
            z = route_z(fid)  # routes carry no z; drape on their landings' mean
            emit_mesh(f"ADA_{fid}", ribbon_mesh(feat["geometry"], z),
                      cb.SCENE_SPEC["ada_routes"]["folder"], mid,
                      (a or {}).get("validation_state", "route_concept_pending_civil"), True,
                      ["acceptance:concept", "PLANNING-GRADE", f"material:{mid}",
                       "concept_pending_civil", "must_label"],
                      {"file": adp, "feature_id": fid, "sha12": sha})
        elif gt == "Point":
            z = feature_z_m(feat, a)
            if z is None:
                z = route_z(fid.rsplit("_landing_", 1)[0])
            x, y = cb.ft_xy_to_enu(*feat["geometry"]["coordinates"][:2])
            emit_mesh(f"ADANode_{fid}", None, cb.SCENE_SPEC["ada_landings"]["folder"], mid,
                      (a or {}).get("validation_state", "landing_concept"), True,
                      ["acceptance:concept", f"material:{mid}", "concept_pending_civil", "marker"],
                      {"file": adp, "feature_id": fid, "sha12": sha}, anchor=list(cb.enu_to_ue(x, y, z)))

    # shared marker mesh (placed at each point actor's anchor in-editor) -------
    marker_mesh().export(os.path.join(mesh_dir, "_marker_unit.obj"), file_type="obj")

    # terrain (import the gated meshes; convert glb->obj, copy obj) ------------
    terrain = []
    tdir = os.path.join(root, "unreal_export/terrain")
    # proposed: already OBJ
    # proposed: load OBJ, apply the ENU->UE handedness map (NOT a raw copy, or it
    # would stay mirrored vs the transformed actors), re-export.
    pr = trimesh.load(os.path.join(tdir, "terrain_proposed.obj"), force="mesh")
    _to_ue(pr).export(os.path.join(mesh_dir, "terrain_proposed.obj"), file_type="obj")
    terrain.append({"name": "Terrain_Proposed", "mesh": "meshes/terrain_proposed.obj",
                    "group": cb.SCENE_SPEC["terrain"]["folder"], "scale": cb.UE_SCALE,
                    "tags": ["acceptance:reference", "terrain:proposed"]})
    # existing: convert glb -> obj, apply the same map
    ex = trimesh.load(os.path.join(tdir, "terrain_existing.glb"), force="mesh")
    _to_ue(ex).export(os.path.join(mesh_dir, "terrain_existing.obj"), file_type="obj")
    terrain.append({"name": "Terrain_Existing", "mesh": "meshes/terrain_existing.obj",
                    "group": cb.SCENE_SPEC["terrain"]["folder"], "scale": cb.UE_SCALE,
                    "tags": ["acceptance:reference", "terrain:existing"]})

    # cameras (plan only; spawned in-editor) ----------------------------------
    cams = cb.load_json(os.path.join(root, "unreal_export/manifests/camera_manifest.json")).get("cameras", [])
    cameras = []
    for c in cams:
        pos = c.get("position_local_m")
        tgt = c.get("look_target_local_m")
        cameras.append({
            "name": c.get("camera_name"),
            "group": cb.SCENE_SPEC["cameras"]["folder"],
            "position_m": list(cb.enu_to_ue(*pos)) if pos else None,
            "look_at_m": list(cb.enu_to_ue(*tgt)) if tgt else None,
            "fov": c.get("fov_deg"),
            "scale": cb.UE_SCALE,
            "tags": sorted({f"slot:{c.get('requested_slot')}", "camera",
                            f"fov:{c.get('fov_deg')}", f"az:{c.get('look_azimuth_deg')}"}),
            "source": {"file": "unreal_export/manifests/camera_manifest.json",
                       "feature_id": c.get("source_feature_id")},
        })

    plan = {
        "schema": "civicbowl-scene-plan/0.1",
        "map_package": cb.MAP_PACKAGE,
        "mesh_package_dir": cb.MESH_PACKAGE_DIR,
        "level_template": cb.LEVEL_TEMPLATE,
        "frame": {"origin_epsg6494_ft": [cb.ORIGIN_X_FT, cb.ORIGIN_Y_FT],
                  "ft_to_m": cb.FT_TO_M, "ue_scale_m_to_cm": cb.UE_SCALE,
                  "enu_to_ue": "UE_X=North, UE_Y=East, UE_Z=Up (det -1, handedness-correct)",
                  "note": "meshes/markers/cameras are baked in the UE frame via the "
                          "handedness-flipping ENU->UE map; actors placed at origin, "
                          "markers/cameras at their UE coords, all at ue_scale."},
        "terrain": terrain,
        "actors": actors,
        "cameras": cameras,
        "deferred_groups": {k: v["source"] for k, v in cb.SCENE_SPEC.items() if not v["included"]},
        "warnings": warnings,
    }
    with open(os.path.join(out, "scene_plan.json"), "w") as fh:
        json.dump(plan, fh, indent=1, sort_keys=True)
    shutil.copy2(os.path.join(root, "unreal_export/manifests/material_manifest.json"),
                 os.path.join(out, "material_manifest.json"))
    return plan


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=None, help="amphitheatre repo root (default: $AMPHI_REPO or inferred)")
    ap.add_argument("--out", default=None, help="output dir (default: <repo>/build/unreal_scene)")
    args = ap.parse_args()

    root = cb.repo_root(args.repo)
    out = os.path.abspath(args.out) if args.out else os.path.join(root, "build", "unreal_scene")

    miss = cb.missing_inputs(root)
    if miss:
        print(f"[gen] MISSING required inputs under {root}:", file=sys.stderr)
        for m in miss:
            print(f"        {m}", file=sys.stderr)
        return 2

    os.makedirs(out, exist_ok=True)
    plan = build(root, out)

    n_actors = len(plan["actors"])
    placed = n_actors + len(plan["terrain"])  # non-camera placed objects
    n_meshes = sum(1 for a in plan["actors"] if a["mesh"]) + len(plan["terrain"])
    print(f"[gen] repo   : {root}")
    print(f"[gen] out    : {out}")
    print(f"[gen] actors : {n_actors}  (footprint meshes + markers)")
    print(f"[gen] terrain: {len(plan['terrain'])}   cameras: {len(plan['cameras'])}")
    print(f"[gen] meshes written: {n_meshes} obj + 1 shared marker")
    print(f"[gen] placed non-camera objects (actors+terrain): {placed}  "
          f"expected (SCENE_SPEC): {cb.expected_actor_total()}  "
          f"{'OK' if placed == cb.expected_actor_total() else 'MISMATCH'}")
    if plan["warnings"]:
        print(f"[gen] warnings: {len(plan['warnings'])} (see scene_plan.json)")
    print(f"[gen] wrote scene_plan.json  (deferred groups: {', '.join(plan['deferred_groups']) or 'none'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
