#!/usr/bin/env python3
"""In-editor assembler + verifier for the /Game/Maps/CivicBowl review scene.

Runs INSIDE Unreal Engine 5.8 on gentoo — either executed by the Unreal MCP
server's Python tool, or headless via:

    UnrealEditor-Cmd <Project>.uproject -run=pythonscript \
        -script="scripts/unreal/ue_civicbowl.py assemble --plan <build>/scene_plan.json"

It consumes the deterministic ``scene_plan.json`` produced by
``gen_review_meshes.py`` (no job-tmp, no manual clicks). Two subcommands:

  assemble  duplicate a NON-WP Basic level -> /Game/Maps/CivicBowl, import the
            staged meshes, spawn one actor per plan entry (folders + tags),
            spawn the cameras, then save the meshes + the level INLINE.
  verify    load /Game/Maps/CivicBowl and report the actor/folder inventory,
            comparing it to the canonical SCENE_SPEC.

``--dry-run`` walks the plan and prints the exact operation sequence WITHOUT
importing ``unreal`` — so the plan-driving logic is checkable off-engine.

Read-only discipline: this assembles a *viewer* scene from the gated handoff
package. It never writes back to vectors_geojson/, dem/, the validation outputs,
Speckle, or data/speckle_publish_ledger.json. Anything edited in Unreal must
return as a proposal GeoJSON in EPSG:6494 through the repo gates.

Key gotchas baked in (host doc gentoo_unreal_host_setup.md §8):
  - Use the NON-WP Template_Default level; WP/OpenWorld loses headless-spawned
    actors on reload. Actors are stored inline in the .umap.
  - save_assets(level) does NOT save imported meshes — save each mesh asset too.
  - Meshes are authored in metres; UE works in cm, so actors take scale x100.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Import the cheap shared constants/spec. This file may run inside UE's Python
# (cwd not the repo), so add our own dir to sys.path defensively.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import civicbowl_common as cb  # noqa: E402


def load_plan(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)


def default_plan_path(repo: str | None) -> str:
    return os.path.join(cb.repo_root(repo), "build", "unreal_scene", "scene_plan.json")


# ── dry-run: print the op sequence from the plan (no engine) ─────────────────
def dry_run(plan: str) -> int:
    p = load_plan(plan)
    base = os.path.dirname(plan)
    print(f"[dry-run] plan        : {plan}")
    print(f"[dry-run] map_package : {p['map_package']}  (template {p['level_template']})")
    print(f"[dry-run] mesh dir    : {p['mesh_package_dir']}")
    meshes = sorted({a["mesh"] for a in p["actors"] if a["mesh"]} |
                    {t["mesh"] for t in p["terrain"]} | {"meshes/_marker_unit.obj"})
    print(f"[dry-run] 1. duplicate {p['level_template']} -> {p['map_package']}; load level")
    print(f"[dry-run] 2. import {len(meshes)} unique meshes into {p['mesh_package_dir']}:")
    for m in meshes:
        exists = os.path.exists(os.path.join(base, m))
        print(f"            {'ok ' if exists else 'MISS'} {m}")
    print(f"[dry-run] 3. spawn {len(p['terrain'])} terrain + {len(p['actors'])} actors (scale x{int(cb.UE_SCALE)}):")
    import collections
    by_group = collections.Counter(a["group"] for a in p["actors"])
    for g, n in sorted(by_group.items()):
        print(f"            {n:3d}  {g}")
    markers = sum(1 for a in p["actors"] if a.get("place_at_anchor"))
    print(f"            ({markers} placed at anchor via shared marker mesh)")
    print(f"[dry-run] 4. spawn {len(p['cameras'])} cameras into {cb.SCENE_SPEC['cameras']['folder']}")
    print(f"[dry-run] 5. save each imported mesh asset + save level INLINE")
    if p.get("deferred_groups"):
        print(f"[dry-run] deferred (not built): {', '.join(p['deferred_groups'])}")
    miss = [m for m in meshes if not os.path.exists(os.path.join(base, m))]
    return 1 if miss else 0


# ── engine helpers (only used when `unreal` is importable) ───────────────────
def _ue():
    import unreal  # noqa
    return unreal


def _import_mesh(unreal, abs_obj: str, dest: str):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", abs_obj)
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    stem = os.path.splitext(os.path.basename(abs_obj))[0]
    return f"{dest}/{stem}"


def _spawn_static(unreal, eas, mesh_asset, location, scale, label, folder, tags):
    loc = unreal.Vector(location[0], location[1], location[2])
    actor = eas.spawn_actor_from_object(mesh_asset, loc, unreal.Rotator(0, 0, 0))
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    actor.set_editor_property("tags", [unreal.Name(t) for t in tags if t])
    return actor


def assemble(plan_path: str, force: bool) -> int:
    unreal = _ue()
    p = load_plan(plan_path)
    base = os.path.dirname(plan_path)
    eal = unreal.EditorAssetLibrary
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

    # 1. NON-WP level (actors persist inline). Duplicate the Basic template.
    if eal.does_asset_exist(p["map_package"]):
        if force:
            eal.delete_asset(p["map_package"])
        else:
            unreal.log_warning(f"{p['map_package']} exists; pass --force to recreate")
    if not eal.does_asset_exist(p["map_package"]):
        eal.duplicate_asset(p["level_template"], p["map_package"])
    les.load_level(p["map_package"])

    # 2. import all unique meshes (relative paths -> abs under the plan dir)
    rels = sorted({a["mesh"] for a in p["actors"] if a["mesh"]} |
                  {t["mesh"] for t in p["terrain"]} | {"meshes/_marker_unit.obj"})
    asset_path = {}
    for rel in rels:
        asset_path[rel] = _import_mesh(unreal, os.path.join(base, rel), p["mesh_package_dir"])
    marker_asset = eal.load_asset(asset_path["meshes/_marker_unit.obj"])

    # 3. terrain + footprint actors at origin (geometry baked in metres, scale x100);
    #    point actors placed at their ENU anchor with the shared marker mesh.
    for t in p["terrain"]:
        _spawn_static(unreal, eas, eal.load_asset(asset_path[t["mesh"]]),
                      (0, 0, 0), t["scale"], t["name"], t["group"], t.get("tags", []))
    for a in p["actors"]:
        if a["mesh"]:
            _spawn_static(unreal, eas, eal.load_asset(asset_path[a["mesh"]]),
                          (0, 0, 0), a["scale"], a["name"], a["group"], a["tags"])
        elif a.get("place_at_anchor"):
            x, y, z = (v * cb.UE_SCALE for v in a["place_at_anchor"])
            _spawn_static(unreal, eas, marker_asset, (x, y, z), a["scale"],
                          a["name"], a["group"], a["tags"])

    # 4. cameras
    for c in p["cameras"]:
        pos = [v * cb.UE_SCALE for v in c["position_m"]]
        cam = eas.spawn_actor_from_class(unreal.CineCameraActor,
                                         unreal.Vector(pos[0], pos[1], pos[2]))
        if c.get("look_at_m"):
            tgt = [v * cb.UE_SCALE for v in c["look_at_m"]]
            rot = unreal.MathLibrary.find_look_at_rotation(
                unreal.Vector(*pos), unreal.Vector(*tgt))
            cam.set_actor_rotation(rot, False)
        cam.set_actor_label(c["name"])
        cam.set_folder_path(c["group"])
        cam.set_editor_property("tags", [unreal.Name(t) for t in c["tags"] if t])

    # 5. save the imported meshes AND the level (inline) — both are required
    for ap in asset_path.values():
        eal.save_asset(ap)
    les.save_current_level()
    eal.save_asset(p["map_package"])
    unreal.log(f"[civicbowl] assembled + saved {p['map_package']}: "
               f"{len(p['terrain'])} terrain + {len(p['actors'])} actors + {len(p['cameras'])} cameras")
    return 0


def verify(plan_path: str | None, repo: str | None) -> int:
    unreal = _ue()
    eal = unreal.EditorAssetLibrary
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    map_pkg = cb.MAP_PACKAGE
    reload_ok = eal.does_asset_exist(map_pkg) and les.load_level(map_pkg)
    print(f"project map : {map_pkg}")
    print(f"reload_ok   : {bool(reload_ok)}")
    if not reload_ok:
        print("MISSING: map not present / failed to load — run `assemble` first.")
        return 2

    actors = eas.get_all_level_actors()
    import collections
    by_folder = collections.Counter(str(a.get_folder_path()) for a in actors)
    print("inventory by folder:")
    for f, n in sorted(by_folder.items()):
        print(f"   {n:3d}  {f}")

    # compare to the canonical spec
    ok = True
    print("group checks (SCENE_SPEC, included groups):")
    for key, g in cb.included_groups().items():
        if g["expected"] is None:
            continue
        found = by_folder.get(g["folder"], 0)
        mark = "OK" if found == g["expected"] else "MISMATCH"
        if found != g["expected"]:
            ok = False
        print(f"   {mark:9s} {key:14s} expected {g['expected']:>3} found {found:>3}  ({g['folder']})")
    print(f"VERDICT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 3


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["assemble", "verify"])
    ap.add_argument("--plan", default=None, help="scene_plan.json (default: <repo>/build/unreal_scene/)")
    ap.add_argument("--repo", default=None, help="amphitheatre repo root (for default plan path)")
    ap.add_argument("--force", action="store_true", help="assemble: recreate the map if it exists")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the op sequence from the plan without importing `unreal`")
    args = ap.parse_args()

    plan = args.plan or default_plan_path(args.repo)
    if args.command == "assemble" and args.dry_run:
        return dry_run(plan)
    if args.command == "assemble":
        return assemble(plan, args.force)
    if args.command == "verify" and args.dry_run:
        print("[dry-run] verify needs a live editor; it loads the map and counts actors.")
        return 0
    return verify(plan, args.repo)


if __name__ == "__main__":
    raise SystemExit(main())
