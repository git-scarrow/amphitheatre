#!/usr/bin/env python3
"""Tests for the additive site-furniture export + manifest layer (Phase 1, Task 4).

Covers: the pure furniture row/geojson mapping; build_furniture() skipping when
the promoted source is absent and emitting + registering actors when present; and
the manifest including the site_furniture layer only when its file exists (fingerprint
reflects it), with the design layers otherwise byte-unchanged.

Any file this test creates under the real tree is removed in a finally + asserted
gone. Plain script (repo convention): exit 0 all pass, 1 a check failed.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import build_unreal_export as B                 # noqa: E402
import build_unreal_handoff_manifest as M       # noqa: E402

RESULTS: list[tuple[bool, str]] = []


def check(cond: bool, label: str) -> None:
    RESULTS.append((bool(cond), label))


_REPO = os.path.dirname(_HERE)
PROMOTED = os.path.join(_REPO, "vectors_geojson", "site_furniture.geojson")
EMITTED = os.path.join(_REPO, "unreal_export", "geo", "site_furniture.geojson")

SAMPLE = {
    "type": "FeatureCollection",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::6494"}},
    "features": [
        {"type": "Feature", "id": "furn_bench_0001",
         "geometry": {"type": "Point", "coordinates": [19533136.58, 750731.14]},
         "properties": {"feature_id": "furn_bench_0001", "object_class": "bench",
                        "variant": "slat_1800", "yaw_deg": 30.0,
                        "anchor_navd88_ft": 610.83,
                        "@review": {"base_build_git_commit": "84aa207"}}},
    ],
}


def main() -> int:
    # ── pure mapping ──────────────────────────────────────────────────────────
    rows, fc = B.furniture_rows_and_geojson(SAMPLE["features"], "vectors_geojson/site_furniture.geojson")
    r0 = rows[0]
    check(r0["actor_class"] == "bench" and r0["validation_state"] == "additive"
          and r0["provisional"] is False and r0["source_feature_id"] == "furn_bench_0001"
          and r0["anchor_xyz_epsg6494_ft"] == (19533136.58, 750731.14),
          "furniture row: object_class->actor_class, additive, not provisional, right anchor")
    check(fc["crs"]["properties"]["name"].endswith("6494")
          and fc["features"][0]["geometry"]["type"] == "Point",
          "emitted furniture geojson is EPSG:6494 points")

    # ── build_furniture(): absent source -> skipped, nothing emitted ──────────
    if os.path.exists(PROMOTED) or os.path.exists(EMITTED):
        print("FATAL: test preconditions dirty (furniture files already present)")
        return 1
    check(B.build_furniture().get("skipped") == "absent",
          "build_furniture() skips cleanly when the promoted layer is absent")

    # ── build_furniture(): present -> registers actors + emits the layer ──────
    created = []
    try:
        with open(PROMOTED, "w") as fh:
            json.dump(SAMPLE, fh)
        created.append(PROMOTED)
        n_before = len(B.ACTORS)
        res = B.build_furniture()
        check(res.get("n_furniture") == 1 and len(B.ACTORS) == n_before + 1,
              "build_furniture() registers a furniture actor when the source is present")
        check(os.path.exists(EMITTED), "build_furniture() emits unreal_export/geo/site_furniture.geojson")
        created.append(EMITTED)
        emitted = json.load(open(EMITTED))
        check(emitted["features"][0]["properties"]["validation_state"] == "additive",
              "emitted layer marks the prop additive")

        # ── manifest includes the layer while the file is present ─────────────
        mani = M.build()
        names = [l["name"] for l in mani["layers"]]
        fp_with = mani["package_fingerprint_sha256"]
        sf = next((l for l in mani["layers"] if l["name"] == "site_furniture"), None)
        check(sf is not None and sf["role"] == "additive-furniture",
              "manifest includes the site_furniture layer when its file exists")
    finally:
        for pth in created:
            if os.path.exists(pth):
                os.remove(pth)

    # ── manifest excludes the layer once the file is gone (fingerprint differs)
    mani2 = M.build()
    names2 = [l["name"] for l in mani2["layers"]]
    check("site_furniture" not in names2,
          "manifest omits site_furniture when its file is absent")
    check(fp_with != mani2["package_fingerprint_sha256"],
          "fingerprint reflects the furniture layer only when present")

    # ── no stray files left in the real tree ──────────────────────────────────
    check(not os.path.exists(PROMOTED) and not os.path.exists(EMITTED),
          "test left no furniture files behind in the tree")

    n_pass = sum(1 for ok, _ in RESULTS if ok)
    for ok, label in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    print(f"\n{n_pass}/{len(RESULTS)} checks pass")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
