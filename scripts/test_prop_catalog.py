#!/usr/bin/env python3
"""Tests for the prop-catalog schema validator (Phase 1, Task 1).

The shipped `assets/props/catalog.json` must validate; each malformed variant
must be caught. Plain script (repo convention): exit 0 = all pass, 1 = a check
failed. No pytest.
"""
from __future__ import annotations

import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate_prop_catalog as V  # noqa: E402

RESULTS: list[tuple[bool, str]] = []


def check(cond: bool, label: str) -> None:
    RESULTS.append((bool(cond), label))


def _err_mentions(errs: list[str], *needles: str) -> bool:
    """True if some error line contains all needles (case-insensitive)."""
    return any(all(n.lower() in e.lower() for n in needles) for e in errs)


def main() -> int:
    with open(V.CATALOG) as fh:
        base = json.load(fh)

    # ── the shipped catalog is valid ──────────────────────────────────────────
    check(V.validate(base) == [], "shipped assets/props/catalog.json validates clean")
    check({"bench", "tree_deciduous", "planter"}
          <= {c["object_class"] for c in base["classes"]},
          "seed catalog carries bench / tree_deciduous / planter")

    # ── duplicate object_class ────────────────────────────────────────────────
    dup = copy.deepcopy(base)
    dup["classes"].append(copy.deepcopy(dup["classes"][0]))
    check(_err_mentions(V.validate(dup), "duplicate", "object_class"),
          "duplicate object_class is rejected")

    # ── empty footprint ───────────────────────────────────────────────────────
    empty_fp = copy.deepcopy(base)
    empty_fp["classes"][0]["footprint"] = []
    check(_err_mentions(V.validate(empty_fp), "footprint"),
          "empty footprint is rejected")

    # ── footprint with a non-numeric / malformed point ────────────────────────
    bad_fp = copy.deepcopy(base)
    bad_fp["classes"][0]["footprint"] = [[0, 0], [1, "x"], [1, 1]]
    check(_err_mentions(V.validate(bad_fp), "footprint"),
          "non-numeric footprint point is rejected")

    # ── unknown keep_clear_of reference ───────────────────────────────────────
    bad_kc = copy.deepcopy(base)
    bad_kc["classes"][0]["keep_clear_of"] = ["ada_route", "not_a_real_class"]
    check(_err_mentions(V.validate(bad_kc), "keep_clear_of", "unknown"),
          "unknown keep_clear_of reference is rejected")

    # ── unknown place_on reference ────────────────────────────────────────────
    bad_po = copy.deepcopy(base)
    bad_po["classes"][0]["place_on"] = ["floating_in_air"]
    check(_err_mentions(V.validate(bad_po), "place_on", "unknown"),
          "unknown place_on surface class is rejected")

    # ── default_variant not among variants ────────────────────────────────────
    bad_dv = copy.deepcopy(base)
    bad_dv["classes"][0]["default_variant"] = "does_not_exist"
    check(_err_mentions(V.validate(bad_dv), "default_variant"),
          "default_variant outside variants is rejected")

    # ── mesh_id as a committed binary path (D1: metadata only) ────────────────
    path_mesh = copy.deepcopy(base)
    path_mesh["classes"][0]["mesh_id"] = "unreal_export/props/bench.glb"
    check(_err_mentions(V.validate(path_mesh), "mesh_id"),
          "mesh_id that is a path / binary filename is rejected (D1)")

    # ── negative spacing + non-positive max_count ─────────────────────────────
    bad_nums = copy.deepcopy(base)
    bad_nums["classes"][0]["min_spacing_m"] = -1
    bad_nums["classes"][1]["max_count"] = 0
    errs = V.validate(bad_nums)
    check(_err_mentions(errs, "min_spacing_m") and _err_mentions(errs, "max_count"),
          "negative spacing and non-positive max_count are rejected")

    # ── missing vocabulary ────────────────────────────────────────────────────
    no_vocab = copy.deepcopy(base)
    del no_vocab["surface_classes"]
    check(_err_mentions(V.validate(no_vocab), "surface_classes"),
          "missing surface_classes vocabulary is rejected")

    # ── report ────────────────────────────────────────────────────────────────
    n_pass = sum(1 for ok, _ in RESULTS if ok)
    for ok, label in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    print(f"\n{n_pass}/{len(RESULTS)} checks pass")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
