#!/usr/bin/env python3
"""Tests for capture_furniture.py (Phase 1, Task 2).

The correctness heart is the coordinate round trip: a known EPSG:6494 anchor from
the committed actor_manifest, forwarded to Unreal cm through the SAME frame
contract the export uses, then reversed by capture, must return within 1e-6 ft
(mirroring verify_unreal_export.gate_roundtrip). Plus: out-of-root actors are
dropped, uncatalogued classes fail closed, feature_ids mint/preserve correctly,
and yaw passes through.

Plain script (repo convention): exit 0 = all pass, 1 = a check failed. No pytest.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "unreal"))
import civicbowl_common as CB          # noqa: E402
import capture_furniture as CAP        # noqa: E402
import validate_prop_catalog as VC     # noqa: E402

RESULTS: list[tuple[bool, str]] = []


def check(cond: bool, label: str) -> None:
    RESULTS.append((bool(cond), label))


def epsg6494_to_ue_cm(x_ft: float, y_ft: float, z_ft: float) -> list[float]:
    """Forward chain (the export's direction), for building test dumps."""
    e, n = CB.ft_xy_to_enu(x_ft, y_ft)
    u = CB.ft_z_to_m(z_ft)
    ux, uy, uz = CB.enu_to_ue(e, n, u)
    return [ux * CB.UE_SCALE, uy * CB.UE_SCALE, uz * CB.UE_SCALE]


def _dump(actors: list[dict], **over) -> dict:
    d = {"authoring_root": "Authoring_Furniture",
         "base_build_git_commit": "84aa207", "captured_by": "tester",
         "captured_at": "2026-07-19T10:00:00-04:00", "topic": "test",
         "actors": actors}
    d.update(over)
    return d


def main() -> int:
    catalog = json.load(open(VC.CATALOG))

    # a real anchor from the committed export
    am = json.load(open(os.path.join(CB.repo_root(),
                        "unreal_export/manifests/actor_manifest.json")))
    ref = am["actors"][0]
    x0, y0 = ref["anchor_epsg6494_ft"]
    z0 = ref["z_navd88_ft"]

    # ── frame agreement: manifest anchor <-> civicbowl transform ──────────────
    # Tolerance 1e-2 m: the manifest rounds anchor_epsg6494_ft to 2 decimal feet
    # (~0.0015 m), so this is a coarse "same frame / not swapped/offset" sanity;
    # exact fidelity is proven by the round-trip check below.
    e, n = CB.ft_xy_to_enu(x0, y0)
    check(abs(e - ref["anchor_local_m"][0]) < 1e-2 and abs(n - ref["anchor_local_m"][1]) < 1e-2,
          "actor_manifest anchor_local_m agrees with the civicbowl frame transform")

    # ── the round trip (the headline) ─────────────────────────────────────────
    ue_cm = epsg6494_to_ue_cm(x0, y0, z0)
    rx, ry, rz = CAP.ue_cm_to_epsg6494(ue_cm)
    check(abs(rx - x0) < 1e-6 and abs(ry - y0) < 1e-6 and abs(rz - z0) < 1e-6,
          f"UE-cm -> EPSG:6494 round trip recovers the source anchor (<1e-6 ft) "
          f"[dx={rx-x0:.2e}, dy={ry-y0:.2e}]")

    # same, exercised through build_proposal end to end
    dump = _dump([{"actor_name": "Bench_01", "outliner_path": "Authoring_Furniture/Bench_01",
                   "object_class": "bench", "variant": "slat_1800",
                   "ue_location_cm": ue_cm, "yaw_deg": 37.5}])
    prop, dropped, errs = CAP.build_proposal(dump, catalog)
    check(not errs and prop is not None, f"build_proposal succeeds on a valid dump ({errs})")
    f0 = prop["features"][0]
    gx, gy = f0["geometry"]["coordinates"]
    check(abs(gx - x0) < 1e-6 and abs(gy - y0) < 1e-6,
          "proposal feature geometry equals the source EPSG:6494 anchor")
    check(f0["properties"]["yaw_deg"] == 37.5, "yaw passes through unchanged")
    check(prop["crs"]["properties"]["name"].endswith("6494"), "proposal CRS is EPSG:6494")
    check(f0["properties"]["@review"]["base_build_git_commit"] == "84aa207",
          "proposal carries base-build provenance for the gate")

    # ── out-of-root actors are dropped + reported (D2) ────────────────────────
    dump2 = _dump([
        {"actor_name": "Bench_in", "outliner_path": "Authoring_Furniture/Bench_in",
         "object_class": "bench", "ue_location_cm": ue_cm, "yaw_deg": 0.0},
        {"actor_name": "Bench_out", "outliner_path": "Accepted_ReadOnly/Seating/Row_01",
         "object_class": "bench", "ue_location_cm": ue_cm, "yaw_deg": 0.0},
    ])
    prop2, dropped2, errs2 = CAP.build_proposal(dump2, catalog)
    check(not errs2 and dropped2 == 1 and len(prop2["features"]) == 1,
          "actor outside Authoring_Furniture is dropped and counted (D2)")

    # ── uncatalogued class fails closed ───────────────────────────────────────
    dump3 = _dump([{"actor_name": "X", "outliner_path": "Authoring_Furniture/X",
                    "object_class": "fountain", "ue_location_cm": ue_cm, "yaw_deg": 0.0}])
    prop3, _, errs3 = CAP.build_proposal(dump3, catalog)
    check(prop3 is None and any("catalog" in e for e in errs3),
          "uncatalogued object_class fails closed (no proposal written)")

    # ── feature_id: preserve existing, mint new PAST the max suffix (D3) ──────
    # An existing id is kept verbatim; new props get monotonic ids past the
    # highest existing suffix (never reuse a possibly-deleted prop's number).
    dump4 = _dump([
        {"actor_name": "b1", "outliner_path": "Authoring_Furniture/b1",
         "object_class": "bench", "ue_location_cm": ue_cm, "yaw_deg": 0.0},
        {"actor_name": "b2", "outliner_path": "Authoring_Furniture/b2",
         "object_class": "bench", "feature_id": "furn_bench_0003",
         "ue_location_cm": ue_cm, "yaw_deg": 0.0},
        {"actor_name": "b3", "outliner_path": "Authoring_Furniture/b3",
         "object_class": "bench", "ue_location_cm": ue_cm, "yaw_deg": 0.0},
    ])
    prop4, _, errs4 = CAP.build_proposal(dump4, catalog)
    ids = [f["properties"]["feature_id"] for f in prop4["features"]]
    check(not errs4 and ids == ["furn_bench_0004", "furn_bench_0003", "furn_bench_0005"],
          f"feature_ids preserve existing and mint new past the max suffix ({ids})")

    # invalid location shape fails closed
    dump5 = _dump([{"actor_name": "bad", "outliner_path": "Authoring_Furniture/bad",
                    "object_class": "bench", "ue_location_cm": [1, 2], "yaw_deg": 0.0}])
    _, _, errs5 = CAP.build_proposal(dump5, catalog)
    check(any("ue_location_cm" in e for e in errs5), "malformed ue_location_cm fails closed")

    # ── report ────────────────────────────────────────────────────────────────
    n_pass = sum(1 for ok, _ in RESULTS if ok)
    for ok, label in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    print(f"\n{n_pass}/{len(RESULTS)} checks pass")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
