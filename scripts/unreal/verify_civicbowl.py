#!/usr/bin/env python3
"""Offline verifier + report for the CivicBowl scene reproducibility path.

Runs ANYWHERE (no Unreal). Reports the same shape the in-editor `ue_civicbowl.py
verify` reports, for the parts checkable off-engine:

  - project / map package path
  - required source inputs present / missing
  - expected geometry groups + counts (SCENE_SPEC), and what the built plan holds
  - whether every mesh the plan references exists on disk (plan completeness)
  - deferred groups (documented TODOs)
  - the exact on-gentoo command to (re)assemble + reload-verify via MCP

Exit non-zero if inputs are missing or the built plan is incomplete. The live
"can the map be reloaded and inspected via MCP" check is `ue_civicbowl.py verify`
(needs the editor); this command prints that command path.

Usage:
    python scripts/unreal/verify_civicbowl.py
    python scripts/unreal/verify_civicbowl.py --repo /path --plan build/unreal_scene/scene_plan.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import civicbowl_common as cb  # noqa: E402

PROJECT_HINT = "/mnt/data/UnrealProjects/PetoskeyCivicBowl/  (gentoo; parameterize on other hosts)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--plan", default=None, help="scene_plan.json (default: <repo>/build/unreal_scene/)")
    args = ap.parse_args()

    root = cb.repo_root(args.repo)
    plan_path = args.plan or os.path.join(root, "build", "unreal_scene", "scene_plan.json")
    rc = 0

    print("== CivicBowl scene — offline verification ==")
    print(f"repo         : {root}")
    print(f"UE project   : {PROJECT_HINT}")
    print(f"map package  : {cb.MAP_PACKAGE}   (level template {cb.LEVEL_TEMPLATE})")
    print(f"NOT a web endpoint — editor/MCP target only. Static web viewer is separate.")

    # 1. required inputs
    miss = cb.missing_inputs(root)
    print(f"\nrequired inputs ({len(cb.REQUIRED_INPUTS)}): {'all present' if not miss else f'{len(miss)} MISSING'}")
    for m in miss:
        print(f"   MISSING  {m}"); rc = 2

    # 2. expected groups (SCENE_SPEC)
    print("\nexpected geometry groups (SCENE_SPEC):")
    for k, g in cb.SCENE_SPEC.items():
        tag = "build" if g["included"] else "TODO "
        exp = g["expected"] if g["expected"] is not None else "?"
        print(f"   [{tag}] {k:14s} {str(exp):>3}  {g['folder']:28s} <- {g['source']}")
    print(f"   expected placed non-camera objects (built groups): {cb.expected_actor_total()}")

    # 3. built plan
    if not os.path.exists(plan_path):
        print(f"\nplan         : NOT BUILT ({plan_path})")
        print("   run: python scripts/unreal/gen_review_meshes.py")
        return rc or 1
    plan = json.load(open(plan_path))
    base = os.path.dirname(plan_path)
    import collections
    by_group = collections.Counter(a["group"] for a in plan["actors"])
    placed = len(plan["actors"]) + len(plan["terrain"])
    print(f"\nplan         : {plan_path}")
    print(f"   schema={plan.get('schema')}  actors={len(plan['actors'])}  "
          f"terrain={len(plan['terrain'])}  cameras={len(plan['cameras'])}  placed={placed}")
    for g, n in sorted(by_group.items()):
        print(f"     {n:3d}  {g}")

    # 4. plan completeness — every referenced mesh exists
    refs = [a["mesh"] for a in plan["actors"] if a["mesh"]] + [t["mesh"] for t in plan["terrain"]]
    refs.append("meshes/_marker_unit.obj")
    missing_meshes = [m for m in dict.fromkeys(refs) if not os.path.exists(os.path.join(base, m))]
    print(f"\nplan meshes  : {len(set(refs))} referenced, "
          f"{'all present' if not missing_meshes else f'{len(missing_meshes)} MISSING'}")
    for m in missing_meshes:
        print(f"   MISSING  {m}"); rc = 1

    # 5. expected-vs-built check
    print("\ngroup checks:")
    ok = True
    for key, g in cb.included_groups().items():
        if g["expected"] is None or key in ("terrain", "cameras"):
            continue
        found = by_group.get(g["folder"], 0)
        if found != g["expected"]:
            ok = False; rc = rc or 1
        print(f"   {'OK' if found == g['expected'] else 'MISMATCH':9s} {key:14s} "
              f"expected {g['expected']:>3} found {found:>3}")
    t_ok = len(plan["terrain"]) == cb.SCENE_SPEC["terrain"]["expected"]
    c_ok = len(plan["cameras"]) == cb.SCENE_SPEC["cameras"]["expected"]
    print(f"   {'OK' if t_ok else 'MISMATCH':9s} terrain        expected   2 found {len(plan['terrain']):>3}")
    print(f"   {'OK' if c_ok else 'MISMATCH':9s} cameras        expected   7 found {len(plan['cameras']):>3}")
    if not (t_ok and c_ok):
        ok = False; rc = rc or 1

    if plan.get("deferred_groups"):
        print(f"\ndeferred TODO groups: {', '.join(plan['deferred_groups'])}")
    if plan.get("warnings"):
        print(f"warnings (z fallbacks etc.): {len(plan['warnings'])}")

    print("\nlive MCP reload-verify (on gentoo, editor up):")
    print("   python scripts/unreal/ue_civicbowl.py verify")
    print(f"\nVERDICT: {'PASS (offline)' if ok and rc == 0 else 'ISSUES — see above'}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
