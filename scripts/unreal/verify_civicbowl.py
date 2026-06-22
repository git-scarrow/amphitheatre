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

    # 6. orientation / handedness — computed THROUGH the ENU->UE transform
    import math
    print("\norientation (computed through the ENU->UE map):")
    det = cb.det3()
    det_ok = abs(det + 1.0) < 1e-9
    print(f"   {'OK' if det_ok else 'FAIL':9s} ENU->UE determinant = {det:+.1f} "
          f"(must be -1: right-handed ENU -> left-handed UE, i.e. NOT mirrored)")
    if not det_ok:
        ok = False; rc = rc or 1

    def ue_az(ue_x, ue_y):  # azimuth cw-from-north in the UE frame
        return (math.degrees(math.atan2(ue_y, ue_x)) + 360) % 360

    # bay-view axis: take its endpoints from source, push through the same map
    stage = cb.geojson_features(os.path.join(root, "unreal_export/geo/stage_floor.geojson"))
    axis = next((f for f in stage if cb.feature_id(f) == "lineage_bay_view_axis"), None)
    if axis:
        c0 = axis["geometry"]["coordinates"][0]; c1 = axis["geometry"]["coordinates"][-1]
        a = cb.enu_to_ue(*cb.ft_xy_to_enu(c0[0], c0[1]), 0.0)
        b = cb.enu_to_ue(*cb.ft_xy_to_enu(c1[0], c1[1]), 0.0)
        az = ue_az(b[0] - a[0], b[1] - a[1])
        bv_ok = abs(((az - 330.0 + 180) % 360) - 180) < 2.0
        if not bv_ok:
            ok = False; rc = rc or 1
        print(f"   {'OK' if bv_ok else 'FAIL':9s} bay-view axis azimuth = {az:.1f}deg (expect 330 NNW)")

    # seating must occupy the S/SE rake (azimuth 90..200 cw-from-north)
    import collections
    secs = collections.defaultdict(list)
    for f in cb.geojson_features(os.path.join(root, "unreal_export/geo/seating_rows.geojson")):
        ring = f["geometry"]["coordinates"][0]
        es = [cb.ft_xy_to_enu(p[0], p[1]) for p in ring]
        e = sum(p[0] for p in es) / len(es); n = sum(p[1] for p in es) / len(es)
        ux, uy, _ = cb.enu_to_ue(e, n, 0.0)
        secs[(f["properties"] or {}).get("section_family") or "?"].append(ue_az(ux, uy))
    for s, az in sorted(secs.items()):
        m = sum(az) / len(az)
        good = 90 <= m <= 200
        if not good:
            ok = False; rc = rc or 1
        print(f"   {'OK' if good else 'FAIL':9s} seating[{s}] mean azimuth = {m:.0f}deg (expect S/SE 90..200)")

    print("\nlive MCP reload-verify (on gentoo, editor up):")
    print("   python scripts/unreal/ue_civicbowl.py verify")
    print(f"\nVERDICT: {'PASS (offline)' if ok and rc == 0 else 'ISSUES — see above'}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
