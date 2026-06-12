#!/usr/bin/env python3
"""Audit gate for the comparator benchmark. FAILS (exit 1) when:

  1. a comparator DEM is too coarse for seating-rake conclusions (>1.5 m),
  2. provenance is missing (source URL / acquisition / CRS),
  3. any metric lacks a basis label, or an imagery-derived stage dimension
     is presented without a range + independent cross-check note,
  4. a row-count claim carries a measured_dem basis (1 m DEM cannot resolve
     individual risers — must stay inferred/published/canon),
  5. section CSVs do not carry explicit meter AND feet columns (silent unit
     mixing),
  6. Petoskey source geometry changed (sha256 vs truth_package design state),
  7. required deliverables are missing (memo, board, SOURCES.md),
  8. Petoskey canon values in comparison.json drift from in_situ_common.

Reproduce:  .venv/bin/python scripts/comparators/audit_comparators.py
"""
import csv
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__),
                                                 "..")))
import in_situ_common as C
from sites import SITES

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
FAIL, WARN = [], []


def check(cond, msg, warn=False):
    if not cond:
        (WARN if warn else FAIL).append(msg)


def sha12(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def main():
    comp_dir = os.path.join(ROOT, "data", "comparators")
    comp = json.load(open(os.path.join(comp_dir, "comparison.json")))

    for slug in SITES:
        sd = os.path.join(comp_dir, slug)
        prov_p = os.path.join(sd, "dem", "provenance.json")
        check(os.path.exists(prov_p), f"{slug}: missing dem/provenance.json")
        if os.path.exists(prov_p):
            prov = json.load(open(prov_p))
            res = max(prov.get("native_resolution_m", [99, 99]))
            check(res <= 1.5,
                  f"{slug}: DEM resolution {res} m too coarse for "
                  "seating-rake conclusions")
            for k in ("source_url", "native_crs", "vertical"):
                check(bool(prov.get(k)), f"{slug}: provenance missing {k}")
            check(bool(prov.get("dem_product", {}).get("lidar_acquisition")),
                  f"{slug}: provenance missing lidar acquisition date")
        check(os.path.exists(os.path.join(sd, "SOURCES.md")),
              f"{slug}: missing SOURCES.md")

        m = comp.get(slug, {})
        for key, v in m.items():
            if isinstance(v, dict) and "basis" in v:
                check(v["basis"] in ("measured_dem", "inferred_imagery",
                                     "published", "canon"),
                      f"{slug}.{key}: unknown basis {v['basis']}")
        # imagery-derived stage dims must be inferred + range + cross-check
        for key in ("stage_frontage_ft", "stage_depth_ft"):
            v = m.get(key, {})
            check(v.get("basis") == "inferred_imagery",
                  f"{slug}.{key}: stage dims must be labeled "
                  "inferred_imagery (no venue spec published)")
            check("range" in v,
                  f"{slug}.{key}: imagery-derived dim lacks a range")
            check(bool(v.get("note")),
                  f"{slug}.{key}: imagery-derived dim lacks an independent "
                  "cross-check note")
        v = m.get("row_count_est", {})
        check(v.get("basis") != "measured_dem",
              f"{slug}: row count must not claim measured_dem at 1 m "
              "resolution")

        sec = os.path.join(sd, "derived", "centerline_section.csv")
        check(os.path.exists(sec), f"{slug}: missing centerline_section.csv")
        if os.path.exists(sec):
            with open(sec) as f:
                hdr = next(csv.reader(f))
            for col in ("s_m", "s_ft", "z_m_navd88", "z_ft_navd88"):
                check(col in hdr,
                      f"{slug}: section CSV missing explicit unit col {col}")

    # Petoskey geometry unchanged vs truth package design state
    ds = json.load(open(os.path.join(ROOT, "truth_package",
                                     "design_state.current.json")))
    for name in ("treads", "zones", "dem_proposed"):
        src = ds["sources"][name]
        p = os.path.join(ROOT, src["path"])
        check(os.path.exists(p), f"petoskey: canonical source missing {p}")
        if os.path.exists(p):
            check(sha12(p) == src["sha256_12"],
                  f"petoskey: {src['path']} hash changed — comparator work "
                  "must not modify Petoskey source geometry")

    # canon drift
    pz = comp["petoskey"]
    check(pz["fan_angle_deg"]["value"] == 110.0, "petoskey fan != 110")
    check(pz["stage_frontage_ft"]["value"] == 70.0, "petoskey stage W != 70")
    check(pz["stage_depth_ft"]["value"] == 34.0, "petoskey stage D != 34")
    check(pz["stage_front_to_row1_ft"]["value"] == 35.0,
          "petoskey stage->row1 != 35")
    check(C.AX_AZ == 132.0 and C.STAGE_RULE9_STATUS == "open",
          "in_situ_common canon changed (AX_AZ / Rule 9)")

    # deliverables
    for p in ("docs/AMPHITHEATRE_COMPARATORS.md",
              "boards/comparator_side_by_side.png",
              "data/comparators/comparison.json",
              "data/comparators/petoskey_metrics.json"):
        check(os.path.exists(os.path.join(ROOT, p)), f"missing deliverable {p}")

    # acquisition-vs-construction sanity (geometry currency)
    check("2018" in SITES["santa_barbara_bowl"]["dem_product"]
          ["lidar_acquisition"], "SB acquisition note drifted", warn=True)

    for w in WARN:
        print("WARN:", w)
    if FAIL:
        for f_ in FAIL:
            print("FAIL:", f_)
        sys.exit(1)
    print(f"AUDIT PASS — {len(WARN)} warning(s), 0 failures. "
          "Comparator benchmark is honest: measured vs inferred labeled, "
          "units explicit, Petoskey canon untouched.")


if __name__ == "__main__":
    main()
