#!/usr/bin/env python3
"""In-editor assembler + verifier for the CivicBowl *context + horizon* layer.

Runs INSIDE Unreal Engine 5.8 on gentoo (MCP Python tool or headless commandlet):

    UnrealEditor-Cmd <Project>.uproject -run=pythonscript \
        -script="scripts/unreal/ue_context.py assemble --plan <build>/context_plan.json"

It consumes ``context_plan.json`` (from ``gen_context.py``) and adds the context
scenery to the SAME ``/Game/Maps/CivicBowl`` level — but ONLY under the
``Context/`` Outliner root. It never touches the audited design actors:

  assemble  import ctx_*.obj, spawn one StaticMeshActor per context entry into
            ``Context/<layer>`` (folders + tags), spawn the sunset CineCamera and
            a DirectionalLight per CALCULATED sun event, save meshes + level inline.
  verify    load the level, count ``Context/`` actors vs the plan, and confirm the
            audited design folders are still populated (context did not harm them).

``--dry-run`` walks the plan and prints the op sequence WITHOUT importing ``unreal``.

Read-only / non-contaminating discipline (host doc + civicbowl_common):
  - idempotent: only actors under ``Context/`` are cleared before rebuild, so a
    context re-assemble never disturbs the design actors (and a design
    re-assemble — which clears only its SCENE_SPEC roots — never disturbs these).
  - commandlet-safe spawns: spawn_actor_from_class + set_static_mesh (NOT
    spawn_actor_from_object, which SIGSEGVs headless).
  - meshes authored in metres; actors take scale x100; saved inline (NON-WP level).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import civicbowl_common as cb   # noqa: E402
import context_common as ctx    # noqa: E402


def load_plan(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)


def default_plan_path(repo: str | None) -> str:
    return os.path.join(cb.repo_root(repo), "build", "unreal_scene", ctx.CONTEXT_PLAN)


# ── dry-run (no engine) ──────────────────────────────────────────────────────
def dry_run(plan_path: str) -> int:
    p = load_plan(plan_path)
    base = os.path.dirname(plan_path)
    meshes = sorted({a["mesh"] for a in p["actors"] if a["mesh"]})
    print(f"[dry-run] plan        : {plan_path}")
    print(f"[dry-run] map_package : {p['map_package']}  (context root {p['context_root']}/)")
    print(f"[dry-run] design roots untouched: {p['design_roots']}")
    print(f"[dry-run] 1. clear prior actors under {p['context_root']}/ only")
    print(f"[dry-run] 2. import {len(meshes)} context meshes into {p['mesh_package_dir']}:")
    for m in meshes:
        print(f"            {'ok ' if os.path.exists(os.path.join(base, m)) else 'MISS'} {m}")
    import collections
    by_group = collections.Counter(a["group"] for a in p["actors"])
    print(f"[dry-run] 3. spawn {len(p['actors'])} context actors (scale x{int(cb.UE_SCALE)}):")
    for g, n in sorted(by_group.items()):
        print(f"            {n:3d}  {g}")
    print(f"[dry-run] 4. spawn {len(p['cameras'])} review camera(s)")
    print(f"[dry-run] 5. spawn {len(p['lights'])} DirectionalLight(s) (CALCULATED sun az/el):")
    for L in p["lights"]:
        print(f"            {L['name']}: az={L['azimuth_deg']} el={L['elevation_apparent_deg']} ({L['local_time']})")
    if p.get("deferred"):
        print(f"[dry-run] deferred (not built): {', '.join(d['layer'] for d in p['deferred'])}")
    miss = [m for m in meshes if not os.path.exists(os.path.join(base, m))]
    return 1 if miss else 0


# ── engine helpers ───────────────────────────────────────────────────────────
def _ue():
    import unreal  # noqa
    return unreal


def _import_mesh(unreal, abs_obj, dest):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", abs_obj)
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return f"{dest}/{os.path.splitext(os.path.basename(abs_obj))[0]}"


def _spawn_static(unreal, eas, mesh_asset, location, scale, label, folder, tags):
    loc = unreal.Vector(location[0], location[1], location[2])
    actor = eas.spawn_actor_from_class(unreal.StaticMeshActor, loc, unreal.Rotator(0, 0, 0))
    actor.static_mesh_component.set_static_mesh(mesh_asset)
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    actor.set_editor_property("tags", [unreal.Name(t) for t in tags if t])
    return actor


def assemble(plan_path: str) -> int:
    unreal = _ue()
    ctx.assert_disjoint_from_design()
    p = load_plan(plan_path)
    base = os.path.dirname(plan_path)
    eal = unreal.EditorAssetLibrary
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

    # Require the audited design map to already exist — context augments it.
    if not eal.does_asset_exist(p["map_package"]):
        unreal.log_error(f"[context] {p['map_package']} missing — run ue_civicbowl.py assemble first")
        return 2
    les.load_level(p["map_package"])

    # idempotent: clear ONLY the Context/ root (never the design actors)
    root = p["context_root"] + "/"
    cleared = 0
    for a in eas.get_all_level_actors():
        fp = str(a.get_folder_path())
        if fp == p["context_root"] or fp.startswith(root):
            eas.destroy_actor(a); cleared += 1
    unreal.log(f"[context] cleared {cleared} prior actor(s) under {p['context_root']}/")

    # import context meshes
    rels = sorted({a["mesh"] for a in p["actors"] if a["mesh"]})
    asset_path = {rel: _import_mesh(unreal, os.path.join(base, rel), p["mesh_package_dir"]) for rel in rels}

    # context static actors (geometry baked in metres -> scale x100, at origin)
    for a in p["actors"]:
        if a["mesh"]:
            _spawn_static(unreal, eas, eal.load_asset(asset_path[a["mesh"]]),
                          (0, 0, 0), a["scale"], a["name"], a["group"], a["tags"])

    # review camera(s)
    for c in p["cameras"]:
        pos = [v * cb.UE_SCALE for v in c["position_m"]]
        cam = eas.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(*pos))
        if c.get("look_at_m"):
            tgt = [v * cb.UE_SCALE for v in c["look_at_m"]]
            cam.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(
                unreal.Vector(*pos), unreal.Vector(*tgt)), False)
        cam.set_actor_label(c["name"])
        cam.set_folder_path(c["group"])
        cam.set_editor_property("tags", [unreal.Name(t) for t in c["tags"] if t])

    # CALCULATED sun: one DirectionalLight per event. Light travels FROM the sun,
    # so forward = -to_sun. First event visible; the rest spawned hidden (toggle).
    for i, L in enumerate(p["lights"]):
        light = eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 100000))
        ts = L["to_sun_unit_ue"]
        fwd = unreal.Vector(-ts[0], -ts[1], -ts[2])
        light.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(
            unreal.Vector(0, 0, 0), fwd * 1000.0), False)
        light.set_actor_label(L["name"])
        light.set_folder_path(L["group"])
        light.set_editor_property("tags", [unreal.Name(t) for t in L["tags"] if t])
        if i > 0:
            light.set_actor_hidden_in_game(True)
            try:
                light.set_is_temporarily_hidden_in_editor(True)
            except Exception:
                pass

    for ap in asset_path.values():
        eal.save_asset(ap)
    les.save_current_level()
    eal.save_asset(p["map_package"])
    unreal.log(f"[context] assembled under {p['context_root']}/: {len(p['actors'])} actors + "
               f"{len(p['cameras'])} camera(s) + {len(p['lights'])} sun light(s)")
    return 0


def verify(plan_path: str | None, repo: str | None) -> int:
    unreal = _ue()
    eal = unreal.EditorAssetLibrary
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    p = load_plan(plan_path or default_plan_path(repo))

    if not (eal.does_asset_exist(p["map_package"]) and les.load_level(p["map_package"])):
        print("MISSING: map not present / failed to load — run ue_civicbowl.py assemble first.")
        return 2
    actors = eas.get_all_level_actors()
    import collections
    by_folder = collections.Counter(str(a.get_folder_path()) for a in actors)

    # context present?
    ctx_groups = collections.Counter(a["group"] for a in p["actors"])
    print("context inventory (Context/ root):")
    ok = True
    for g, exp in sorted(ctx_groups.items()):
        found = by_folder.get(g, 0)
        if found < exp:
            ok = False
        print(f"   {'OK' if found >= exp else 'MISSING':9s} {g:34s} expected>={exp:>2} found {found:>2}")
    # cameras + lights folders
    for extra in {c["group"] for c in p["cameras"]} | {L["group"] for L in p["lights"]}:
        print(f"   present {by_folder.get(extra, 0):>2}  {extra}")

    # design folders still populated (context did not harm the audited inventory)
    print("audited design folders still present:")
    for key, g in cb.included_groups().items():
        if g["expected"] in (None, 0):
            continue
        found = by_folder.get(g["folder"], 0)
        mark = "OK" if found == g["expected"] else "CHANGED"
        if found != g["expected"]:
            ok = False
        print(f"   {mark:9s} {key:14s} expected {g['expected']:>3} found {found:>3}")
    print(f"VERDICT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 3


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["assemble", "verify"])
    ap.add_argument("--plan", default=None)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    plan = args.plan or default_plan_path(args.repo)
    if args.command == "assemble" and args.dry_run:
        return dry_run(plan)
    if args.command == "assemble":
        return assemble(plan)
    if args.command == "verify" and args.dry_run:
        print("[dry-run] verify needs a live editor; it loads the map and counts Context/ actors.")
        return 0
    return verify(plan, args.repo)


if __name__ == "__main__":
    raise SystemExit(main())
