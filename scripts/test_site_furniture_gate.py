#!/usr/bin/env python3
"""Tests for validate_site_furniture.py (Phase 1, Task 3).

Behavioural checks use small SYNTHETIC constraint geometry (metres) so each rule
is isolated; a final smoke check loads the real committed layers. Positions are
defined in local ENU metres and converted to EPSG:6494 ft for the proposal
features (the gate converts them back), so the synthetic metre constraints and
the proposal line up.

Plain script (repo convention): exit 0 = all pass, 1 = a check failed.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "unreal"))
import civicbowl_common as CB          # noqa: E402
import validate_site_furniture as G    # noqa: E402
import validate_prop_catalog as VC     # noqa: E402

RESULTS: list[tuple[bool, str]] = []


def check(cond: bool, label: str) -> None:
    RESULTS.append((bool(cond), label))


def _has(reasons, code, *needles):
    return any(r.startswith(code) and all(n in r for n in needles) for r in reasons)


# synthetic constraint world (metres)
SITE_HULL = [(0.0, 0.0), (200.0, 0.0), (200.0, 200.0), (0.0, 200.0)]
ADA_LINE = [(0.0, 100.0), (200.0, 100.0)]                       # route at n=100
SEATING = [(140.0, 140.0), (160.0, 140.0), (160.0, 160.0), (140.0, 160.0)]
STAGE_DECK = [(20.0, 20.0), (40.0, 20.0), (40.0, 40.0), (20.0, 40.0)]
EVENT_FLOOR = [(160.0, 20.0), (180.0, 20.0), (180.0, 40.0), (160.0, 40.0)]  # stage_floor surface, not deck

CONSTRAINTS = {
    "ada_route": {"kind": "lines", "geom": [ADA_LINE]},
    "seating_tread": {"kind": "polys", "geom": [SEATING]},
    "stage_deck": {"kind": "polys", "geom": [STAGE_DECK]},
}
SURFACES = {"terrace_tread": [SEATING], "stage_floor": [STAGE_DECK, EVENT_FLOOR]}


def feat(e, n, oc="bench", fid=None, commit="84aa207", review=True):
    fid = fid or f"furn_{oc}_0001"
    props = {"feature_id": fid, "object_class": oc, "variant": None, "yaw_deg": 0.0}
    if review:
        props["@review"] = {"base_build_git_commit": commit}
    return {"type": "Feature", "id": fid,
            "geometry": {"type": "Point", "coordinates": list(CB.enu_to_ft(e, n))},
            "properties": props}


def fc(*features):
    return {"type": "FeatureCollection", "features": list(features)}


def run(*features):
    return G.validate(fc(*features), CATALOG, CONSTRAINTS, SURFACES, SITE_HULL)


def main() -> int:
    global CATALOG
    CATALOG = json.load(open(VC.CATALOG))

    # ── clean bench on context ground PASSES ──────────────────────────────────
    reasons, warns = run(feat(100, 20))
    check(reasons == [], f"clean bench on context ground PASSES ({reasons})")
    check(any("egress" in w for w in warns),
          "egress reported as uncheckable (no egress layer) — surfaced, not silently passed")

    # ── bench ON the ADA corridor FAILS B3 ────────────────────────────────────
    reasons, _ = run(feat(100, 100))
    check(_has(reasons, "B3", "ada_route"), "bench on the ADA clear route FAILS B3")

    # ── bench colliding with seating FAILS B3 ─────────────────────────────────
    reasons, _ = run(feat(150, 150))
    check(_has(reasons, "B3", "seating_tread"), "bench on a seating tread FAILS B3")

    # ── two benches closer than min_spacing FAIL B4 ───────────────────────────
    reasons, _ = run(feat(50, 50, fid="furn_bench_0001"),
                     feat(50, 50.5, fid="furn_bench_0002"))
    check(_has(reasons, "B4", "min_spacing"), "two benches within min_spacing FAIL B4")

    # ── prop outside the boundary FAILS B1 ────────────────────────────────────
    reasons, _ = run(feat(300, 300))
    check(_has(reasons, "B1"), "prop outside the site boundary FAILS B1")

    # ── B2: a tree may only go on context_ground; on stage_floor it FAILS ─────
    reasons, _ = run(feat(170, 30, oc="tree_deciduous", fid="furn_tree_deciduous_0001"))
    check(_has(reasons, "B2"), "tree on a stage_floor surface FAILS B2 (place_on)")

    # ── B5: missing provenance + duplicate id ─────────────────────────────────
    reasons, _ = run(feat(100, 20, fid="furn_bench_0001", review=False))
    check(_has(reasons, "B5", "base_build_git_commit"), "missing @review provenance FAILS B5")
    reasons, _ = run(feat(90, 20, fid="furn_bench_0009"), feat(95, 25, fid="furn_bench_0009"))
    check(_has(reasons, "B5") and any("unique" in r for r in reasons),
          "duplicate feature_id FAILS B5")

    # ── B4 count: exceed a class max_count ────────────────────────────────────
    cat2 = json.loads(json.dumps(CATALOG))
    next(c for c in cat2["classes"] if c["object_class"] == "bench")["max_count"] = 1
    r2, _ = G.validate(fc(feat(60, 20, fid="furn_bench_0001"),
                          feat(70, 20, fid="furn_bench_0002")),
                       cat2, CONSTRAINTS, SURFACES, SITE_HULL)
    check(_has(r2, "B4", "max_count"), "exceeding max_count FAILS B4")

    # ── fail closed when a required constraint layer is missing ───────────────
    with tempfile.TemporaryDirectory() as d:
        _, _, _, missing = G.load_constraints(d)
        check(missing == ["ada_route.geojson", "seating_rows.geojson",
                          "stage_floor.geojson"],
              "load_constraints reports all missing layers (fail-closed input)")

    # ── smoke: the REAL committed layers load into usable constraints ─────────
    cons, surf, hull, miss = G.load_constraints(G.GEO)
    check(miss == [] and len(hull) >= 3
          and cons["ada_route"]["geom"] and cons["seating_tread"]["geom"]
          and cons["stage_deck"]["geom"],
          "real committed layers load into constraints + a site hull")

    # ── real-data guard: a bench on an actual seating tread is rejected for
    #    COLLIDING WITH SEATING, not mislabelled as sitting on the stage floor
    #    (the concept event-floor/treatment polygons overlap the seating bowl). ─
    am = json.load(open(os.path.join(CB.repo_root(),
                        "unreal_export/manifests/actor_manifest.json")))["actors"][0]
    tread = feat(*CB.ft_xy_to_enu(*am["anchor_epsg6494_ft"]))
    r_real, _ = G.validate(fc(tread), CATALOG, cons, surf, hull)
    check(_has(r_real, "B3", "seating_tread") and not _has(r_real, "B2"),
          "bench on a real seating tread FAILS B3 (seating), not a spurious B2 stage_floor")

    # ── report ────────────────────────────────────────────────────────────────
    n_pass = sum(1 for ok, _ in RESULTS if ok)
    for ok, label in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    print(f"\n{n_pass}/{len(RESULTS)} checks pass")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
