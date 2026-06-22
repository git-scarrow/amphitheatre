#!/usr/bin/env python3
"""Shared contract for the CivicBowl UE 5.8 read-only scene toolchain.

Single source of truth for:
  - where the *tracked* source artifacts live (parameterized by --repo / $AMPHI_REPO),
  - the EPSG:6494 international-feet -> local-ENU-metre frame transform (and the
    metre -> Unreal-centimetre scale), matching ``data/unreal_handoff_manifest.json``,
  - ``SCENE_SPEC``: the canonical scene inventory (groups, source layers, expected
    counts) that both the generator and the verifier agree on,
  - small loaders for the manifests + GeoJSON.

This module is pure stdlib (no shapely/trimesh/unreal) so it imports anywhere — the
offline generator and verifier import it on a laptop; the in-editor ``ue_civicbowl.py``
imports only the cheap constants/spec from it.

Nothing here mutates design truth. The scene is a *read-only viewer* assembled from the
gated handoff package (``unreal_export/`` + ``data/unreal_handoff_manifest.json``). The
Python/QGIS gates + ``data/speckle_publish_ledger.json`` remain the sole acceptance
authority; Unreal is never a source of truth.
"""
from __future__ import annotations

import hashlib
import json
import os

# ── repo location (parameterized; no hard-coded host path) ───────────────────
def repo_root(explicit: str | None = None) -> str:
    """Resolve the amphitheatre repo root: --repo > $AMPHI_REPO > two levels up."""
    if explicit:
        return os.path.abspath(explicit)
    env = os.environ.get("AMPHI_REPO")
    if env:
        return os.path.abspath(env)
    # scripts/unreal/civicbowl_common.py -> repo root is two dirs up
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── coordinate frame (mirrors data/unreal_handoff_manifest.json "crs") ───────
# EPSG:6494 NAD83(2011)/Michigan Central, INTERNATIONAL feet; vertical NAVD88 ft.
ORIGIN_X_FT = 19533067.7
ORIGIN_Y_FT = 750799.2
FT_TO_M = 0.3048
# Local frame: ENU, Z-up, metres. x=east, y=north, z = NAVD88 ft * 0.3048.
# Unreal works in centimetres; meshes are authored in metres and placed at this scale.
UE_SCALE = 100.0  # metres -> Unreal cm

MAP_PACKAGE = "/Game/Maps/CivicBowl"
MESH_PACKAGE_DIR = "/Game/Meshes/CivicBowl"
# Non-WP (no World Partition / OFPA) template — actors persist INLINE in the .umap.
# Using the WP/OpenWorld template loses headless-spawned actors on reload (host doc §8).
LEVEL_TEMPLATE = "/Engine/Maps/Templates/Template_Default"


def ft_xy_to_enu(x_ft: float, y_ft: float) -> tuple[float, float]:
    """EPSG:6494 international feet -> local ENU metres (x=east, y=north)."""
    return ((x_ft - ORIGIN_X_FT) * FT_TO_M, (y_ft - ORIGIN_Y_FT) * FT_TO_M)


def ft_z_to_m(navd88_ft: float) -> float:
    """NAVD88 international feet -> local metres (z-up)."""
    return navd88_ft * FT_TO_M


# ── ENU (right-handed) -> Unreal (left-handed) frame mapping ─────────────────
# ENU is right-handed: x=East, y=North, z=Up. Unreal world is LEFT-handed, Z-up.
# Mapping a right-handed coordinate component-wise into a left-handed frame
# (the old UE_X=East, UE_Y=North) leaves the data right-handed inside a
# left-handed renderer -> the scene is MIRROR-imaged vs true geography.
#
# The fix is a handedness-flipping (determinant = -1) axis map. We use the
# conventional Unreal geospatial mapping:
#       UE_X = North   UE_Y = East   UE_Z = Up
# An East<->North swap has determinant -1, so it converts right-handed ENU into
# Unreal's left-handed frame WITHOUT reflecting the geometry. Bearing is then
# azimuth(cw-from-North) = atan2(UE_Y, UE_X) = atan2(East, North), i.e. the
# scene's compass matches the real site. Z (elevation) is untouched.
ENU_TO_UE_LINEAR = (
    (0.0, 1.0, 0.0),   # UE_X = North  (= ENU y)
    (1.0, 0.0, 0.0),   # UE_Y = East   (= ENU x)
    (0.0, 0.0, 1.0),   # UE_Z = Up     (= ENU z)
)


def enu_to_ue(e: float, n: float, u: float) -> tuple[float, float, float]:
    """ENU metres (East, North, Up) -> Unreal-frame metres (X=North, Y=East, Z=Up)."""
    return (n, e, u)


def det3(m=ENU_TO_UE_LINEAR) -> float:
    """Determinant of a 3x3 (stdlib). For ENU_TO_UE_LINEAR this is -1.0 — the
    handedness flip that guarantees the UE scene is not mirror-imaged."""
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


# ── canonical scene inventory (the contract the verifier checks) ─────────────
# Each group: which gated source produces it, the geometry kind, and the Outliner
# folder. "expected" is the count the generated plan / loaded scene must report.
# included=True groups are built in v0; included=False are documented TODOs.
SCENE_SPEC = {
    "terrain": {
        "folder": "Reference/Terrain",
        "kind": "mesh",
        "source": "unreal_export/terrain/terrain_{existing,proposed}.{obj,glb}",
        "expected": 2,
        "included": True,
    },
    "seating": {
        "folder": "Accepted_ReadOnly/Seating",
        "kind": "polygon",
        "source": "unreal_export/geo/seating_rows.geojson",
        "expected": 45,
        "included": True,
    },
    "stage": {
        "folder": "Proposal_Editable/Stage",
        "kind": "polygon",
        "source": "unreal_export/geo/stage_floor.geojson (zone_stage_* polygons)",
        "expected": 3,
        "included": True,
    },
    "treatment_cell": {
        "folder": "Concept_Landscape/TreatmentCell",
        "kind": "polygon",
        "source": "unreal_export/geo/stage_floor.geojson (zone_treatment_cell_landscape)",
        "expected": 1,
        "included": True,
    },
    "event_floor": {
        "folder": "Concept_Landscape/EventFloor",
        "kind": "polygon",
        "source": "unreal_export/geo/stage_floor.geojson (zone_orchestra_event_floor)",
        "expected": 1,
        "included": True,
    },
    "bay_view_axis": {
        "folder": "Reference/BayView",
        "kind": "line+point",
        "source": "unreal_export/geo/stage_floor.geojson (lineage_* features)",
        "expected": 2,
        "included": True,
    },
    "ada_routes": {
        "folder": "Concept_ADA/Routes",
        "kind": "line",
        "source": "unreal_export/geo/ada_route.geojson (LineString features)",
        "expected": 8,
        "included": True,
    },
    "ada_landings": {
        "folder": "Concept_ADA/Landings",
        "kind": "point",
        "source": "unreal_export/geo/ada_route.geojson (Point features)",
        "expected": 31,
        "included": True,
    },
    "cameras": {
        "folder": "Cameras",
        "kind": "camera",
        "source": "unreal_export/manifests/camera_manifest.json",
        "expected": 7,
        "included": True,
    },
    # ── documented TODOs (geometry not in the gated geo/ package yet) ────────
    "human_scale": {
        "folder": "Reference/HumanScale",
        "kind": "point",
        "source": "vectors_geojson/human_scale_refs.geojson "
        "— NOT yet exported to unreal_export/geo/",
        "expected": None,
        "included": False,
    },
}

# Required input files for the included groups (relative to repo root).
REQUIRED_INPUTS = [
    "unreal_export/geo/seating_rows.geojson",
    "unreal_export/geo/stage_floor.geojson",
    "unreal_export/geo/ada_route.geojson",
    "unreal_export/terrain/terrain_proposed.obj",
    "unreal_export/terrain/terrain_existing.glb",
    "unreal_export/manifests/actor_manifest.json",
    "unreal_export/manifests/camera_manifest.json",
    "unreal_export/manifests/material_manifest.json",
    "data/unreal_handoff_manifest.json",
]


def included_groups() -> dict:
    return {k: v for k, v in SCENE_SPEC.items() if v["included"]}


def expected_actor_total() -> int:
    """Total non-camera actors expected in v0 (terrain + footprints + markers)."""
    return sum(
        g["expected"]
        for k, g in included_groups().items()
        if k != "cameras" and g["expected"] is not None
    )


# ── loaders ──────────────────────────────────────────────────────────────────
def load_json(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)


def geojson_features(path: str) -> list[dict]:
    return load_json(path).get("features", [])


def sha256_12(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def feature_id(feat: dict) -> str | None:
    return (feat.get("properties") or {}).get("feature_id") or feat.get("id")


def missing_inputs(root: str) -> list[str]:
    return [p for p in REQUIRED_INPUTS if not os.path.exists(os.path.join(root, p))]


def actor_index(root: str) -> dict:
    """Map source_feature_id -> actor record from the gated actor_manifest."""
    am = load_json(os.path.join(root, "unreal_export/manifests/actor_manifest.json"))
    return {a.get("source_feature_id"): a for a in am.get("actors", [])}
