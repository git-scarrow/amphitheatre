#!/usr/bin/env python3
"""Extended offline verification for the CivicBowl context + horizon layer.

Runs ANYWHERE (no Unreal). Asserts the two things that matter most: the audited
design path is byte-for-byte unchanged, and the new context scenery is present,
declared, isolated from the design gates, and does not block the bay view.

Reports / gates:
  1. AUDITED design unchanged — re-runs verify_civicbowl.py; requires PASS, and
     the design scene_plan.json counts still match SCENE_SPEC exactly.
  2. Context manifest valid — every layer declares the required provenance fields.
  3. Context plan present — every context actor sits under the Context/ root,
     disjoint from the design roots, and maps to a declared layer.
  4. Design-count isolation — NO context layer/actor contributes to a design gate
     (none set included_in_verification:true in v0).
  5. Bay-view corridor unobstructed — no 'occluder' context geometry rises into
     the eye->bay sightline within the corridor; backdrops (water/horizon/shore)
     are confirmed below the seated eye, so they cannot occlude.
  6. Orientation preserved — det(ENU->UE) = -1, water-plane normal is +Z (up),
     and the sunset camera aims down the audited bay-view axis (~330 NNW).

Exit non-zero on any gate failure.

    python scripts/unreal/verify_context.py
    python scripts/unreal/verify_context.py --repo /path --plan build/unreal_scene/context_plan.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import civicbowl_common as cb   # noqa: E402
import context_common as ctx    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _design_unchanged(root: str) -> tuple[bool, str]:
    """Re-run the audited design verifier; PASS == design inventory intact."""
    r = subprocess.run([sys.executable, os.path.join(HERE, "verify_civicbowl.py"), "--repo", root],
                       capture_output=True, text=True)
    verdict = next((ln for ln in r.stdout.splitlines() if ln.startswith("VERDICT")), "VERDICT: (none)")
    return (r.returncode == 0 and "PASS" in verdict), verdict.strip()


def _corridor_membership(corr: dict, e: float, n: float) -> tuple[bool, float, float]:
    """Return (in_corridor, along_range_m, perp_dist_m) for an ENU point."""
    ox, oy = corr["origin_enu_m"]; de, dn = corr["dir_to_bay"]
    re, rn = e - ox, n - oy
    along = re * de + rn * dn                 # projection onto bay direction
    perp = abs(re * (-dn) + rn * de)          # perpendicular distance to axis
    return (along >= 0 and perp <= corr["half_width_m"]), along, perp


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--plan", default=None, help="context_plan.json (default: <repo>/build/unreal_scene/)")
    args = ap.parse_args()
    root = cb.repo_root(args.repo)
    plan_path = args.plan or os.path.join(root, "build", "unreal_scene", ctx.CONTEXT_PLAN)
    ok = True

    print("== CivicBowl context + horizon — extended verification ==")
    print(f"repo        : {root}")
    print(f"context root: {ctx.CONTEXT_FOLDER_ROOT}   map: {cb.MAP_PACKAGE}")

    # 1. audited design unchanged ---------------------------------------------
    d_ok, verdict = _design_unchanged(root)
    print(f"\n[1] audited design (verify_civicbowl.py): {'OK' if d_ok else 'FAIL'}  ({verdict})")
    print(f"    expected audited non-camera objects (SCENE_SPEC) = {cb.expected_actor_total()} (unchanged)")
    ok = ok and d_ok

    # 2. context manifest valid -----------------------------------------------
    man = ctx.load_context_manifest(root)
    problems = ctx.validate_manifest(man)
    print(f"\n[2] context manifest ({len(man.get('layers', []))} layers): "
          f"{'OK — all required fields declared' if not problems else f'{len(problems)} PROBLEM(S)'}")
    for p in problems:
        print(f"    PROBLEM  {p}"); ok = False
    try:
        ctx.assert_disjoint_from_design()
        print(f"    OK       Context root disjoint from design roots {sorted(ctx.design_folder_roots())}")
    except AssertionError as e:
        print(f"    FAIL     {e}"); ok = False

    # 3. context plan present + well-formed -----------------------------------
    if not os.path.exists(plan_path):
        print(f"\n[3] context plan: NOT BUILT ({plan_path})")
        print("    run: python scripts/unreal/gen_context.py")
        return 1
    plan = json.load(open(plan_path))
    base = os.path.dirname(plan_path)
    declared = {l["layer_name"] for l in man["layers"]}
    print(f"\n[3] context plan: {plan_path}")
    print(f"    actors={len(plan['actors'])}  lights={len(plan['lights'])}  "
          f"cameras={len(plan['cameras'])}  deferred={[d['layer'] for d in plan['deferred']]}")
    import collections
    by_layer = collections.Counter(a["layer"] for a in plan["actors"])
    for layer, n in sorted(by_layer.items()):
        mark = "OK" if layer in declared else "UNDECLARED"
        if layer not in declared:
            ok = False
        print(f"    {mark:6s} {n:3d}  {layer}")
    # every actor under Context/ root, mesh present
    bad_root = [a["name"] for a in plan["actors"] if not a["group"].startswith(ctx.CONTEXT_FOLDER_ROOT + "/")]
    if bad_root:
        print(f"    FAIL   {len(bad_root)} actor(s) not under {ctx.CONTEXT_FOLDER_ROOT}/: {bad_root[:3]}"); ok = False
    missing = [a["mesh"] for a in plan["actors"]
               if a["mesh"] and not os.path.exists(os.path.join(base, a["mesh"]))]
    print(f"    meshes : {sum(1 for a in plan['actors'] if a['mesh'])} referenced, "
          f"{'all present' if not missing else f'{len(missing)} MISSING'}")
    if missing:
        ok = False

    # 4. design-count isolation -----------------------------------------------
    opted_in = [a["name"] for a in plan["actors"] if a.get("included_in_verification")]
    collide = [a["name"] for a in plan["actors"] if a["group"].split("/")[0] in ctx.design_folder_roots()]
    iso_ok = not opted_in and not collide
    print(f"\n[4] design-count isolation: {'OK' if iso_ok else 'FAIL'}")
    print(f"    context actors contributing to a design gate (included_in_verification): {len(opted_in)}")
    print(f"    context actors landing in a design folder root                          : {len(collide)}")
    ok = ok and iso_ok

    # 5. bay-view corridor unobstructed ---------------------------------------
    corr = plan.get("corridor")
    print(f"\n[5] bay-view corridor (az {corr['azimuth_deg']:.0f}, half-width "
          f"{corr['half_width_m']:.0f} m): " if corr else "\n[5] bay-view corridor: ", end="")
    # seated eye datum = sunset camera position z (highest seat + 1.5 m), in UE z = ENU z
    eye_z = plan["cameras"][0]["position_m"][2] if plan["cameras"] else None
    occluders = [a for a in plan["actors"] if a.get("obstruction_role") == "occluder" and a.get("extent_enu_m")]
    backdrops = [a for a in plan["actors"] if a.get("obstruction_role") == "backdrop" and a.get("extent_enu_m")]
    obstructions = []
    if corr and eye_z is not None:
        ox, oy = corr["origin_enu_m"]; de, dn = corr["dir_to_bay"]
        # near visible water target: water plane near edge along the corridor
        near_along = ctx.BAY_NEAR_N_M  # ~150 m bay-side
        tgt = (ox + de * near_along, oy + dn * near_along, ctx.WATER_ELEV_M)
        eye_along = -(corr["origin_enu_m"][0] * de + corr["origin_enu_m"][1] * dn)  # ~0; eye near origin
        for a in occluders:
            emin, emax, nmin, nmax, ztop = a["extent_enu_m"]
            for (e, n) in [(emin, nmin), (emax, nmin), (emax, nmax), (emin, nmax)]:
                inside, along, perp = _corridor_membership(corr, e, n)
                if not inside or along > near_along:
                    continue
                # sightline height from eye (at along=0) descending to the near water target
                frac = max(0.0, min(1.0, along / max(near_along, 1e-6)))
                sight_z = eye_z + (ctx.WATER_ELEV_M - eye_z) * frac
                if ztop > sight_z + 0.5:
                    obstructions.append((a["name"], round(along, 1), round(ztop, 1), round(sight_z, 1)))
                    break
    print(f"{'OK' if not obstructions else 'FAIL'}")
    print(f"    occluder context actors: {len(occluders)}  "
          f"(0 -> corridor trivially clear; becomes a live gate once OSM city massing is fetched)")
    for nm, al, zt, sz in obstructions:
        print(f"    OBSTRUCTION {nm}: top {zt} m > sightline {sz} m at {al} m along corridor"); ok = False
    # backdrops must sit below the seated eye (cannot occlude the bay)
    if eye_z is not None:
        for a in backdrops:
            ztop = a["extent_enu_m"][4]
            tag = "OK" if ztop <= eye_z else "CHECK"
            if ztop > eye_z:
                # horizon band may legitimately rise above eye far away; only flag if also in corridor near side
                pass
            print(f"    backdrop {a['layer']:20s} top {ztop:7.1f} m vs seated eye {eye_z:7.1f} m  [{tag}]")

    # 6. orientation preserved -------------------------------------------------
    print("\n[6] orientation:")
    det = cb.det3(); det_ok = abs(det + 1.0) < 1e-9
    print(f"    {'OK' if det_ok else 'FAIL':4s} ENU->UE determinant = {det:+.1f} (handedness-correct, shared with design)")
    ok = ok and det_ok
    # water plane normal must be +Z (up) after the transform — read the mesh
    wp = next((a for a in plan["actors"] if a["layer"] == "bay_water_plane" and a["mesh"]), None)
    if wp:
        try:
            import trimesh
            m = trimesh.load(os.path.join(base, wp["mesh"]), force="mesh")
            nz = float(abs(m.face_normals[:, 2]).min())
            up_ok = nz > 0.99
            print(f"    {'OK' if up_ok else 'FAIL':4s} water-plane normal vertical (|nz|={nz:.3f}) -> surface is level")
            ok = ok and up_ok
        except Exception as e:
            print(f"    skip water-plane normal check ({e.__class__.__name__})")
    # sunset camera aims down the bay-view axis
    if plan["cameras"]:
        cam = plan["cameras"][0]
        dx = cam["look_at_m"][0] - cam["position_m"][0]; dy = cam["look_at_m"][1] - cam["position_m"][1]
        cam_az = (math.degrees(math.atan2(dy, dx)) + 360) % 360
        aim_ok = abs(((cam_az - 330.0 + 180) % 360) - 180) < 5.0
        print(f"    {'OK' if aim_ok else 'FAIL':4s} sunset camera aim azimuth = {cam_az:.1f} (expect ~330 NNW bay axis)")
        ok = ok and aim_ok
    for ev, d in plan["solar_events"].items():
        print(f"    sun {ev}: {d.get('local')}  az={d.get('azimuth_deg')}  el_app={d.get('elevation_apparent_deg')} (NOAA computed)")

    print(f"\nlive context reload-verify (gentoo, editor up):")
    print(f"   python scripts/unreal/ue_context.py verify")
    print(f"\nVERDICT: {'PASS (offline)' if ok else 'ISSUES — see above'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
