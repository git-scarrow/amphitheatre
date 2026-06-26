#!/usr/bin/env python3
"""In-editor assembler + verifier for the CivicBowl *context + horizon* layer.

Runs INSIDE Unreal Engine 5.8 on gentoo (MCP Python tool or headless commandlet):

    UnrealEditor-Cmd <Project>.uproject -run=pythonscript \
        -script="scripts/unreal/ue_context.py assemble --plan <build>/context_plan.json"

It consumes ``context_plan.json`` (from ``gen_context.py``) and adds context
scenery to the SAME ``/Game/Maps/CivicBowl`` level. The import is INCREMENTAL and
SAFE: it only ever creates/updates actors under the managed roots
``Context/City_LoFi/`` and ``Context/Foreground_HiFi/``. Everything else is
PRESERVED untouched — the accepted single-sun lights, the sunset review camera,
and the three accepted-as-hidden v0 proxies (``ctx_bay_water_plane``,
``ctx_shoreline_proxy``, ``ctx_distant_horizon_band``).

  plan              LIVE diff against the open level, NO writes / NO save: reports
                    create / update / preserve-hidden / would-delete / labels /
                    mesh count.
  assemble --dry-run  OFFLINE plan (no engine, no save): the same op set from the
                    plan file + the safety assertions (run this first).
  assemble          LIVE import: clears ONLY managed-root actors, imports managed
                    meshes, spawns mesh actors + TextRender labels (mesh=None +
                    label_text), force-hides the three protected proxies, saves.
  verify            load the level, count actors vs the plan, confirm audited
                    design folders are still intact.

Safety contract (host doc + civicbowl_common):
  - managed-only: only ``Context/City_LoFi`` + ``Context/Foreground_HiFi`` are
    cleared/rebuilt; the design SCENE_SPEC roots and the rest of ``Context/`` are
    never touched.
  - protected proxies are NEVER cleared or respawned, and are force-hidden
    (hidden-in-game + hidden-in-editor) on every assemble. Deleting one requires
    the explicit ``--allow-delete-protected`` opt-in.
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


# ── safe-import contract ──────────────────────────────────────────────────────
# The live import is INCREMENTAL: it only ever creates/updates actors under these
# two roots. Everything else under Context/ — the accepted hidden proxies, the
# calculated sun lights, the sunset review camera — is PRESERVED untouched, so a
# re-import can never clobber the accepted scene's lighting or un-hide a proxy.
MANAGED_ROOTS = ("Context/City_LoFi", "Context/Foreground_HiFi")

# The three crude v0 proxies are accepted as HIDDEN/non-rendering. They are never
# cleared, never respawned by this importer, and are force-hidden on every run.
# Matched by actor label OR legacy folder (resilient to either drifting).
PROTECTED_HIDDEN_NAMES = {"ctx_distant_horizon_band", "ctx_shoreline_proxy", "ctx_bay_water_plane"}
PROTECTED_HIDDEN_FOLDERS = {"Context/distant_horizon_band", "Context/bay_shoreline_ref",
                            "Context/bay_water_plane"}


def _is_managed(group: str) -> bool:
    return any(group == r or group.startswith(r + "/") for r in MANAGED_ROOTS)


def _is_protected(name: str, folder: str) -> bool:
    return name in PROTECTED_HIDDEN_NAMES or folder in PROTECTED_HIDDEN_FOLDERS


def _managed_actors(plan: dict) -> list[dict]:
    return [a for a in plan["actors"] if _is_managed(a["group"])]


def _label_actors(actors: list[dict]) -> list[dict]:
    return [a for a in actors if not a.get("mesh") and a.get("label_text")]


# ── dry-run (no engine) — the safe-import plan ───────────────────────────────
def dry_run(plan_path: str) -> int:
    """Offline plan: exactly what a live assemble WOULD do, with no engine + no save.

    Cannot see the live scene, so create-vs-update is resolved live (see `plan`);
    here we report the intended op set and assert the safety invariants hold."""
    import collections
    p = load_plan(plan_path)
    base = os.path.dirname(plan_path)

    managed = _managed_actors(p)
    labels = _label_actors(managed)
    mesh_actors = [a for a in managed if a.get("mesh")]
    meshes = sorted({a["mesh"] for a in mesh_actors})
    nonmanaged = [a for a in p["actors"] if not _is_managed(a["group"])]
    protected = [a for a in p["actors"] if _is_protected(a["name"], a["group"])]

    print(f"[plan] plan file   : {plan_path}")
    print(f"[plan] map_package : {p['map_package']}  (NOT saved in dry-run)")
    print(f"[plan] managed roots (only these are created/updated):")
    for r in MANAGED_ROOTS:
        print(f"           {r}/")

    by_group = collections.Counter(a["group"] for a in managed)
    print(f"\n[plan] CREATE/UPDATE — {len(managed)} actor(s) under managed roots:")
    for g, n in sorted(by_group.items()):
        print(f"           {n:5d}  {g}")
    print(f"[plan]   of which mesh actors : {len(mesh_actors)}  (unique meshes to import: {len(meshes)})")
    print(f"[plan]   of which LABELS      : {len(labels)}  -> TextRender actors")
    for a in labels:
        print(f"               label {a['name']:22s} text={a.get('label_text')!r}  {a['group']}")

    print(f"\n[plan] PRESERVE (never cleared, never respawned) — {len(nonmanaged)} non-managed Context actor(s):")
    pg = collections.Counter(a["group"] for a in nonmanaged)
    for g, n in sorted(pg.items()):
        flag = "  <- PROTECTED-HIDDEN" if g in PROTECTED_HIDDEN_FOLDERS else ""
        print(f"           {n:5d}  {g}{flag}")
    print(f"[plan]   + accepted sun lights ({len(p['lights'])}) and review camera(s) ({len(p['cameras'])}) "
          f"are PRESERVED (not respawned)")

    print(f"\n[plan] FORCE-HIDDEN enforcement targets ({len(protected)}):")
    for a in protected:
        print(f"           {a['name']:24s} {a['group']}")

    # deletes: only inside managed roots, only on re-import; computed live. None on first import.
    print(f"\n[plan] WOULD-DELETE: only actors already under {MANAGED_ROOTS} are cleared+rebuilt "
          f"(idempotent update); computed against the live scene by `plan`. "
          f"No non-managed actor is ever deleted.")
    if p.get("deferred"):
        print(f"[plan] deferred (not built): {', '.join(d['layer'] for d in p['deferred'])}")

    # safety assertions ------------------------------------------------------
    print("\n[plan] SAFETY CHECKS:")
    ok = True
    bad_managed_protected = [a for a in managed if _is_protected(a["name"], a["group"])]
    c1 = not bad_managed_protected
    print(f"   {'PASS' if c1 else 'FAIL'}  no protected proxy is in a managed (rebuilt) root")
    ok = ok and c1
    design_roots = set(p["design_roots"])
    c2 = all(a["group"].split("/")[0] not in design_roots for a in managed)
    print(f"   {'PASS' if c2 else 'FAIL'}  no managed actor lands in an audited design root {sorted(design_roots)}")
    ok = ok and c2
    c3 = all(_is_managed(a["group"]) for a in (mesh_actors + labels))
    print(f"   {'PASS' if c3 else 'FAIL'}  all created geometry/labels confined to City_LoFi/Foreground_HiFi")
    ok = ok and c3
    miss = [m for m in meshes if not os.path.exists(os.path.join(base, m))]
    c4 = not miss
    print(f"   {'PASS' if c4 else 'FAIL'}  all {len(meshes)} managed meshes present on disk"
          + (f" (MISSING {len(miss)})" if miss else ""))
    ok = ok and c4
    print(f"\n[plan] VERDICT: {'SAFE — no destructive edits, proxies stay hidden' if ok else 'UNSAFE — see FAIL above'}")
    return 0 if ok else 1


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


def _spawn_label(unreal, eas, text, location_cm, label, folder, tags):
    """Label as a TextRenderActor (mesh=None + label_text). Falls back to a tagged
    empty actor only if TextRenderActor is unavailable on this build."""
    loc = unreal.Vector(location_cm[0], location_cm[1], location_cm[2])
    try:
        actor = eas.spawn_actor_from_class(unreal.TextRenderActor, loc, unreal.Rotator(0, 0, 0))
        trc = actor.get_component_by_class(unreal.TextRenderComponent)
        trc.set_text(unreal.Text.from_string(text))
        for prop, val in (("world_size", 800.0),
                          ("horizontal_alignment", unreal.HorizTextAligment.EHTA_CENTER)):
            try:
                trc.set_editor_property(prop, val)
            except Exception:
                pass
        tags = list(tags) + ["label_textrender"]
    except Exception:
        actor = eas.spawn_actor_from_class(unreal.Actor, loc, unreal.Rotator(0, 0, 0))
        tags = list(tags) + ["label_fallback_no_textrender", f"text:{text}"]
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    actor.set_editor_property("tags", [unreal.Name(t) for t in tags if t])
    return actor


def _force_hidden(unreal, actor):
    """Make an actor non-rendering in game and hidden in the editor (idempotent)."""
    actor.set_actor_hidden_in_game(True)
    try:
        actor.set_is_temporarily_hidden_in_editor(True)
    except Exception:
        pass


def _scan_live(unreal, eas):
    """Map label -> actor and folder -> [labels] for the current level."""
    by_label, by_folder = {}, {}
    for a in eas.get_all_level_actors():
        lbl = a.get_actor_label()
        fp = str(a.get_folder_path())
        by_label[lbl] = a
        by_folder.setdefault(fp, []).append(lbl)
    return by_label, by_folder


def _enforce_protected_hidden(unreal, eas) -> list[str]:
    """Force the three accepted proxies hidden/non-rendering. Never creates or
    deletes them — only flips visibility on whatever already exists."""
    touched = []
    for a in eas.get_all_level_actors():
        if _is_protected(a.get_actor_label(), str(a.get_folder_path())):
            _force_hidden(unreal, a)
            touched.append(a.get_actor_label())
    return touched


def live_plan(plan_path: str) -> int:
    """In-editor PLAN (no writes, no save): diff the plan against the live scene and
    report create / update / preserve-hidden / would-delete / labels / mesh count."""
    unreal = _ue()
    p = load_plan(plan_path)
    eal = unreal.EditorAssetLibrary
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not (eal.does_asset_exist(p["map_package"]) and les.load_level(p["map_package"])):
        unreal.log_error(f"[plan] {p['map_package']} missing — run ue_civicbowl.py assemble first")
        return 2

    managed = _managed_actors(p)
    plan_names = {a["name"] for a in managed}
    by_label, by_folder = _scan_live(unreal, eas)
    live_managed = [lbl for fp, lbls in by_folder.items() if _is_managed(fp) for lbl in lbls]

    create = sorted(n for n in plan_names if n not in by_label)
    update = sorted(n for n in plan_names if n in by_label)
    would_delete = sorted(n for n in live_managed if n not in plan_names)
    labels = _label_actors(managed)

    print(f"[plan] LIVE diff against {p['map_package']} (no save):")
    print(f"   CREATE          : {len(create)}")
    print(f"   UPDATE (rebuild): {len(update)}")
    print(f"   LABELS          : {len(labels)} TextRender")
    print(f"   meshes to import: {len({a['mesh'] for a in managed if a.get('mesh')})}")
    print(f"   WOULD-DELETE (managed-root actors not in plan): {len(would_delete)}")
    for n in would_delete[:20]:
        print(f"        - {n}")

    # protected proxies: report current visibility (no change in plan mode)
    print("   PROTECTED proxies (current state, unchanged by plan):")
    for a in eas.get_all_level_actors():
        if _is_protected(a.get_actor_label(), str(a.get_folder_path())):
            hid_game = a.get_editor_property("hidden") if False else None  # avoid noisy API
            try:
                hidden_ed = a.is_temporarily_hidden_in_editor()
            except Exception:
                hidden_ed = "?"
            print(f"        {a.get_actor_label():24s} folder={a.get_folder_path()}  hidden_in_editor={hidden_ed}")

    # safety: nothing in a design root, no protected actor in managed set
    design_roots = set(p["design_roots"])
    bad = [n for n in (create + update) if by_label.get(n) and
           str(by_label[n].get_folder_path()).split("/")[0] in design_roots]
    print(f"   SAFE: managed actors in a design root = {len(bad)} (must be 0)")
    print(f"[plan] no actors created/destroyed, no save performed.")
    return 0


def assemble(plan_path: str, allow_delete_protected: bool = False) -> int:
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

    # INCREMENTAL + SAFE: clear ONLY actors under the managed roots. The accepted
    # hidden proxies, calculated sun lights, and review camera live elsewhere under
    # Context/ and are PRESERVED untouched. Protected proxies are never cleared even
    # if one somehow lands in a managed root (unless explicitly approved).
    cleared = skipped_protected = 0
    for a in eas.get_all_level_actors():
        fp = str(a.get_folder_path())
        if not _is_managed(fp):
            continue
        if _is_protected(a.get_actor_label(), fp) and not allow_delete_protected:
            skipped_protected += 1
            continue
        eas.destroy_actor(a); cleared += 1
    unreal.log(f"[context] cleared {cleared} prior actor(s) under managed roots "
               f"{MANAGED_ROOTS} (protected skipped: {skipped_protected})")

    managed = _managed_actors(p)
    mesh_actors = [a for a in managed if a.get("mesh")]
    labels = _label_actors(managed)

    # import only the managed meshes
    rels = sorted({a["mesh"] for a in mesh_actors})
    asset_path = {rel: _import_mesh(unreal, os.path.join(base, rel), p["mesh_package_dir"]) for rel in rels}

    # managed static actors (geometry baked in metres -> scale x100, at origin)
    for a in mesh_actors:
        # never (re)create a protected proxy from the plan; if present, force-hide it
        if _is_protected(a["name"], a["group"]):
            continue
        _spawn_static(unreal, eas, eal.load_asset(asset_path[a["mesh"]]),
                      (0, 0, 0), a["scale"], a["name"], a["group"], a["tags"])

    # managed labels -> TextRender (anchor is in metres -> x100 to cm)
    for a in labels:
        anchor_m = a.get("place_at_anchor") or [0, 0, 0]
        loc_cm = [v * cb.UE_SCALE for v in anchor_m]
        _spawn_label(unreal, eas, a["label_text"], loc_cm, a["name"], a["group"], a["tags"])

    # PRESERVED (not respawned): accepted sun lights (p["lights"]) + review camera
    # (p["cameras"]) + the legacy backdrop proxies. Touching them is out of scope.

    # safety net: force the three accepted proxies hidden/non-rendering, always.
    hidden = _enforce_protected_hidden(unreal, eas)
    unreal.log(f"[context] force-hidden protected proxies: {hidden}")

    for ap in asset_path.values():
        eal.save_asset(ap)
    les.save_current_level()
    eal.save_asset(p["map_package"])
    unreal.log(f"[context] assembled under managed roots: {len(mesh_actors)} mesh actor(s) + "
               f"{len(labels)} label(s); preserved sun/camera/proxies; proxies hidden={hidden}")
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
    ap.add_argument("command", choices=["assemble", "verify", "plan"],
                    help="plan = live no-save diff; assemble --dry-run = offline plan; assemble = live import")
    ap.add_argument("--plan", default=None, dest="plan_path")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-delete-protected", action="store_true",
                    help="EXPLICIT opt-in to delete the accepted hidden proxies (default: never)")
    args = ap.parse_args()
    plan = args.plan_path or default_plan_path(args.repo)
    if args.command == "assemble" and args.dry_run:
        return dry_run(plan)                       # offline plan (no engine, no save)
    if args.command == "plan":
        return live_plan(plan)                     # live diff, no save
    if args.command == "assemble":
        return assemble(plan, allow_delete_protected=args.allow_delete_protected)
    if args.command == "verify" and args.dry_run:
        print("[dry-run] verify needs a live editor; it loads the map and counts Context/ actors.")
        return 0
    return verify(plan, args.repo)


if __name__ == "__main__":
    raise SystemExit(main())
