#!/usr/bin/env python3
"""Open + frame the /Game/Maps/CivicBowl review scene — a viewport/visibility aid.

WHY THIS EXISTS
---------------
The CivicBowl scene is geographically faithful: vertical coordinates are *absolute
NAVD88 elevation* (site grade ~600-620 ft -> ~183-189 m), with no vertical datum
subtraction (only the horizontal origin (CX,CY) is removed — see
``civicbowl_common.ft_z_to_m`` / ``ft_xy_to_enu``). In Unreal centimetres the whole
model therefore sits ~18,700 cm (≈187 m) ABOVE the world origin / Template_Default
floor, while horizontally it straddles the origin (±~120 m). A freshly-opened editor
viewport starts near the origin looking horizontally, so the operator sees only the
template grid + sky and the model is far overhead, out of frame.

This is a *framing* problem, not a spawn/geometry problem (all SCENE_SPEC actors are
present and correctly placed). This script points the camera at the model and leaves
durable review cameras so the scene is visible "without manual hunting". It NEVER
moves an actor, edits geometry, or touches design canon — it only loads the map,
reads bounds, sets the viewport camera, and adds non-SCENE_SPEC review cameras.

WHAT IT DOES
------------
  1. loads /Game/Maps/CivicBowl (idempotent — reuses the open level if already loaded),
  2. selects every SCENE_SPEC actor (terrain, seating, stage, human-scale, …),
  3. computes their combined world bounds and points the live editor viewport at
     the centre, down the bay-view sightline, framing the whole amphitheatre,
  4. (re)creates two NAMED review cameras in the ``Review`` Outliner folder:
       - ``ReviewCam_Overview``  — elevated 3/4 aerial framing all bounds,
       - ``ReviewCam_SeatedEye`` — seated-eye height on the upper seating rake,
         looking down toward the stage and the bay beyond,
  5. saves the level (so the cameras persist) and prints + writes a JSON report of
     combined bounds, per-folder actor counts, and the camera locations.

The ``Review`` folder is deliberately OUTSIDE every SCENE_SPEC folder, so
``ue_civicbowl.py verify`` (which counts by SCENE_SPEC folder name) stays green and
``assemble`` (which only clears its own managed top-level folders) never touches the
review cameras.

HOW TO RUN
----------
Inside the LIVE editor on gentoo (the Moonlight GUI session) — Output Log → console
mode ``Python``, or Tools → Execute Python Script:

    py "<repo>/scripts/unreal/open_and_frame_civicbowl.py"

Headless (commandlet) also works for the report + camera bake (the live-viewport
framing step is simply skipped when no editor viewport exists):

    UnrealEditor-Cmd <Project>.uproject -run=pythonscript \
        -script="<repo>/scripts/unreal/open_and_frame_civicbowl.py"
"""
from __future__ import annotations

import json
import math
import os
import sys

# This runs inside UE's Python (cwd is usually the project, not the repo); make our
# sibling shared-contract module importable regardless of cwd.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import civicbowl_common as cb  # noqa: E402

# ── review-camera contract (kept out of SCENE_SPEC so verify/assemble ignore it) ──
REVIEW_FOLDER = "Review"
OVERVIEW_CAM = "ReviewCam_Overview"
SEATED_CAM = "ReviewCam_SeatedEye"
# Seated eye height: 3.94 ft (EYE_SEATED_FT, the C-value sightline standard used by
# the human-scale layer) -> metres -> Unreal cm.
EYE_SEATED_CM = 3.94 * cb.FT_TO_M * cb.UE_SCALE  # ≈ 120.1 cm
OVERVIEW_FOV = 55.0
SEATED_FOV = 50.0
# Bay-view sightline azimuth (NNW, from civicbowl_common / README): seating looks
# over the stage toward the bay along ~330°. The establishing overview sits "behind
# the audience" at the reciprocal bearing (~150°, SSE) and looks down the axis.
BAY_VIEW_AZIMUTH_DEG = 330.0


def _report_path() -> str:
    """Best-effort durable location for the JSON report (repo build dir if present)."""
    try:
        root = cb.repo_root(None)
        out = os.path.join(root, "build", "unreal_scene")
        if os.path.isdir(out):
            return os.path.join(out, "frame_report.json")
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), "civicbowl_frame_report.json")


# ── geometry helpers (pure; no engine) ───────────────────────────────────────
def _azimuth_dir(azimuth_deg: float, tilt_deg: float):
    """Unit vector (UE X=North, Y=East, Z=Up) at a compass azimuth, tilted up by
    ``tilt_deg`` above the horizon. Used to place a camera 'behind' a target."""
    az = math.radians(azimuth_deg)
    tl = math.radians(tilt_deg)
    horiz = math.cos(tl)
    return (math.cos(az) * horiz, math.sin(az) * horiz, math.sin(tl))


def _frame_distance(extent_x: float, extent_y: float, fov_deg: float, margin: float):
    """Camera standoff (cm) so a box of these half-extents fits the FOV horizontally."""
    half_diag = math.hypot(extent_x, extent_y)
    return half_diag / math.tan(math.radians(fov_deg) * 0.5) * margin


# ── engine section (only runs when `unreal` is importable) ───────────────────
def run() -> int:
    import unreal  # noqa

    eal = unreal.EditorAssetLibrary
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

    map_pkg = cb.MAP_PACKAGE
    if not eal.does_asset_exist(map_pkg):
        unreal.log_error(f"[frame] map missing: {map_pkg} — run ue_civicbowl.py assemble first")
        return 2
    les.load_level(map_pkg)
    unreal.log(f"[frame] map loaded: {map_pkg}")

    # SCENE_SPEC folders (the real model) vs our review folder.
    spec_folders = {g["folder"] for g in cb.included_groups().values()}
    geom_folders = {g["folder"] for k, g in cb.included_groups().items() if k != "cameras"}

    actors = eas.get_all_level_actors()
    by_folder = {}
    spec_actors = []     # everything in a SCENE_SPEC folder (for selection)
    geom_actors = []     # non-camera SCENE_SPEC actors (for bounds + reps)
    seating_actors, stage_actors = [], []
    for a in actors:
        fp = str(a.get_folder_path())
        by_folder[fp] = by_folder.get(fp, 0) + 1
        if fp in spec_folders:
            spec_actors.append(a)
        if fp in geom_folders:
            geom_actors.append(a)
            if fp == cb.SCENE_SPEC["seating"]["folder"]:
                seating_actors.append(a)
            elif fp == cb.SCENE_SPEC["stage"]["folder"]:
                stage_actors.append(a)

    if not geom_actors:
        unreal.log_error("[frame] no SCENE_SPEC actors found — is the map assembled?")
        return 3

    # combined world bounds over the real model (origin ± box extent per actor).
    INF = float("inf")
    gmin = [INF, INF, INF]
    gmax = [-INF, -INF, -INF]

    def _accum(actor):
        origin, extent = actor.get_actor_bounds(False)
        for i, (o, e) in enumerate(((origin.x, extent.x), (origin.y, extent.y), (origin.z, extent.z))):
            gmin[i] = min(gmin[i], o - e)
            gmax[i] = max(gmax[i], o + e)

    for a in geom_actors:
        _accum(a)

    center = unreal.Vector((gmin[0] + gmax[0]) / 2.0,
                           (gmin[1] + gmax[1]) / 2.0,
                           (gmin[2] + gmax[2]) / 2.0)
    half = (max((gmax[0] - gmin[0]) / 2.0, 1.0),
            max((gmax[1] - gmin[1]) / 2.0, 1.0),
            max((gmax[2] - gmin[2]) / 2.0, 1.0))

    def _centroid(group_actors, fallback):
        if not group_actors:
            return fallback
        sx = sy = sz = 0.0
        for a in group_actors:
            o, _ = a.get_actor_bounds(False)
            sx += o.x; sy += o.y; sz += o.z
        n = float(len(group_actors))
        return unreal.Vector(sx / n, sy / n, sz / n)

    stage_center = _centroid(stage_actors, center)

    # ── overview camera: stand off "behind the audience" (reciprocal of the
    #    bay-view azimuth), tilted ~32° down, far enough to frame the bounds. ──
    back_az = (BAY_VIEW_AZIMUTH_DEG + 180.0) % 360.0   # ~150° SSE
    d = _frame_distance(half[0], half[1], OVERVIEW_FOV, margin=1.18)
    dx, dy, dz = _azimuth_dir(back_az, tilt_deg=32.0)
    over_loc = unreal.Vector(center.x + dx * d, center.y + dy * d, center.z + dz * d)
    over_rot = unreal.MathLibrary.find_look_at_rotation(over_loc, center)

    # ── seated-eye camera: pick the upper seating actor (farthest from the stage)
    #    + eye height, looking at the stage centre (and the bay beyond). ──
    if seating_actors:
        def _dist_to_stage(a):
            o, _ = a.get_actor_bounds(False)
            return (o.x - stage_center.x) ** 2 + (o.y - stage_center.y) ** 2
        upper = max(seating_actors, key=_dist_to_stage)
        so, sext = upper.get_actor_bounds(False)
        seat_loc = unreal.Vector(so.x, so.y, so.z + sext.z + EYE_SEATED_CM)
    else:
        seat_loc = unreal.Vector(center.x - half[0], center.y, center.z + EYE_SEATED_CM)
    seat_rot = unreal.MathLibrary.find_look_at_rotation(seat_loc, stage_center)

    # ── (re)create the review cameras idempotently (clear prior Review/ actors) ──
    cleared = 0
    for a in list(actors):
        if str(a.get_folder_path()) == REVIEW_FOLDER:
            eas.destroy_actor(a); cleared += 1

    def _spawn_cam(name, loc, rot, fov, tags):
        cam = eas.spawn_actor_from_class(unreal.CameraActor, loc, rot)
        cam.set_actor_label(name)
        cam.set_folder_path(REVIEW_FOLDER)
        try:
            cam.camera_component.set_field_of_view(fov)
        except Exception:
            pass
        cam.set_editor_property("tags", [unreal.Name(t) for t in tags if t])
        return cam

    _spawn_cam(OVERVIEW_CAM, over_loc, over_rot, OVERVIEW_FOV,
               ["review", "viewport_aid", "frames:all", f"fov:{int(OVERVIEW_FOV)}"])
    _spawn_cam(SEATED_CAM, seat_loc, seat_rot, SEATED_FOV,
               ["review", "viewport_aid", "human_scale", "posture:seated",
                "eye_ft:3.94", f"fov:{int(SEATED_FOV)}"])
    unreal.log(f"[frame] review cameras: cleared {cleared} prior, spawned 2 in '{REVIEW_FOLDER}'")

    # ── select the real model + point the live viewport at it (GUI only) ──
    try:
        eas.set_selected_level_actors(spec_actors)
    except Exception as exc:
        unreal.log_warning(f"[frame] select skipped: {exc}")

    viewport_framed = False
    try:
        ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        ues.set_level_viewport_camera_info(over_loc, over_rot)
        viewport_framed = True
    except Exception:
        try:  # deprecated fallback for older API surface
            unreal.EditorLevelLibrary.set_level_viewport_camera_info(over_loc, over_rot)
            viewport_framed = True
        except Exception as exc:
            unreal.log_warning(f"[frame] live-viewport framing unavailable (headless?): {exc}")

    # ── persist + report ──
    les.save_current_level()
    eal.save_asset(map_pkg)

    report = {
        "map": map_pkg,
        "viewport_framed": viewport_framed,
        "actor_total": len(actors),
        "scene_spec_actors": len(spec_actors),
        "combined_bounds_cm": {
            "min": [round(v, 1) for v in gmin],
            "max": [round(v, 1) for v in gmax],
            "center": [round(center.x, 1), round(center.y, 1), round(center.z, 1)],
            "size": [round(gmax[i] - gmin[i], 1) for i in range(3)],
            "note": "UE cm; axes X=North, Y=East, Z=Up. Z carries absolute NAVD88 elevation.",
        },
        "by_folder": dict(sorted(by_folder.items())),
        "cameras": {
            OVERVIEW_CAM: {
                "location_cm": [round(over_loc.x, 1), round(over_loc.y, 1), round(over_loc.z, 1)],
                "look_at_cm": [round(center.x, 1), round(center.y, 1), round(center.z, 1)],
                "fov": OVERVIEW_FOV,
                "azimuth_deg": round(back_az, 1),
            },
            SEATED_CAM: {
                "location_cm": [round(seat_loc.x, 1), round(seat_loc.y, 1), round(seat_loc.z, 1)],
                "look_at_cm": [round(stage_center.x, 1), round(stage_center.y, 1), round(stage_center.z, 1)],
                "fov": SEATED_FOV,
                "eye_height_cm": round(EYE_SEATED_CM, 1),
            },
        },
    }
    txt = json.dumps(report, indent=2)
    unreal.log("[frame] REPORT\n" + txt)
    try:
        rp = _report_path()
        with open(rp, "w") as fh:
            fh.write(txt + "\n")
        unreal.log(f"[frame] report written: {rp}")
    except Exception as exc:
        unreal.log_warning(f"[frame] report not written: {exc}")

    unreal.log("[frame] DONE — pilot 'ReviewCam_Overview' (whole bowl) or "
               "'ReviewCam_SeatedEye' (seated sightline) from the Review folder.")
    return 0


def main() -> int:
    try:
        import unreal  # noqa: F401
    except Exception:
        print("[frame] this script must run inside Unreal Engine "
              "(py <path>, or UnrealEditor-Cmd -run=pythonscript). "
              "Bounds/camera math is engine-driven; nothing to do off-engine.")
        return 0
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
