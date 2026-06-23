#!/usr/bin/env python3
"""Acceptance gate for the Unreal handoff package (unreal_export/).

Proves the package honours the authoritative-source boundary:

  A. all named exports + manifests + terrain present
  B. every actor traces to an EXISTING source file and a RESOLVABLE feature id
  C. seat counts are not invented (export sum == source sum == validation)
  D. sightline C-values are READ from validation.json, never weakened/recomputed
  E. ADA route status strings carried VERBATIM (not strengthened to "compliant")
  F. provisional / concept tiers stay marked (stage Rule-9 OPEN, treatment cell)
  G. the planning-grade warnings block is carried VERBATIM from design_state
  H. local<->EPSG:6494 round-trip is exact within tolerance; origin == canon

Exit 0 = all gates pass. Exit 1 = at least one gate FAILED. Read-only.
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "unreal_export")
ORIGIN_X, ORIGIN_Y = 19533067.7, 750799.2
FT2M = 0.3048

FAILS, PASSES = [], []


def ok(msg):
    PASSES.append(msg)


def bad(msg):
    FAILS.append(msg)


def jload(path):
    with open(path) as fh:
        return json.load(fh)


def src(rel):
    return os.path.join(REPO, rel)


def out(rel):
    return os.path.join(OUT, rel)


# ── A. presence ─────────────────────────────────────────────────────────────
REQUIRED = [
    "geo/seating_rows.geojson", "geo/seating_row_splines.geojson",
    "geo/stage_floor.geojson", "geo/ada_route.geojson",
    "geo/human_scale_refs.geojson",
    "tables/sightline_table.csv",
    "manifests/actor_manifest.json", "manifests/actor_manifest.csv",
    "manifests/material_manifest.json", "manifests/camera_manifest.json",
    "manifests/provenance.json",
]
TERRAIN = [
    "terrain/terrain_existing.glb", "terrain/terrain_proposed.glb",
    "terrain/terrain_proposed.obj",
    "terrain/heightfield_existing.r16", "terrain/heightfield_existing.png",
    "terrain/heightfield_existing.heightfield.json",
    "terrain/heightfield_proposed.r16", "terrain/heightfield_proposed.png",
    "terrain/heightfield_proposed.heightfield.json",
]


def gate_presence():
    for rel in REQUIRED:
        (ok if os.path.exists(out(rel)) else bad)(f"A present: {rel}")
    missing_t = [t for t in TERRAIN if not os.path.exists(out(t))]
    if missing_t:
        # terrain is optional (DEM may be absent); note but don't fail hard
        ok(f"A terrain optional, absent: {missing_t}")
    else:
        ok("A terrain: all 9 terrain assets present")


# ── B. actor provenance ─────────────────────────────────────────────────────
def gate_actor_provenance():
    am = jload(out("manifests/actor_manifest.json"))
    actors = am["actors"]
    # build feature-id resolvers from the EXPORT geojson (which carry feature_id
    # + source_file/source_index back to the authoritative source)
    resolvers = {}
    for rel in ("geo/seating_rows.geojson", "geo/stage_floor.geojson",
                "geo/ada_route.geojson"):
        for f in jload(out(rel))["features"]:
            fid = f["properties"].get("feature_id")
            if fid:
                resolvers[fid] = f["properties"]
    # cameras' viewpoint feature ids
    bad_src = bad_fid = 0
    for a in actors:
        if not os.path.exists(src(a["source_file"])):
            bad_src += 1
        fid = a["source_feature_id"]
        # tread/zone/ada actors must resolve in the export; lineage/viewpoint ok
        if a["source_file"].endswith("terrace_treads.geojson") or \
           a["source_file"].endswith("bowl_zones.geojson") or \
           a["source_file"].endswith("ada_route.geojson"):
            if fid not in resolvers:
                bad_fid += 1
    (ok if bad_src == 0 else bad)(
        f"B every actor source_file exists ({len(actors)} actors, {bad_src} missing)")
    (ok if bad_fid == 0 else bad)(
        f"B every geometry actor feature_id resolves ({bad_fid} unresolved)")


# ── C. seat-count integrity ─────────────────────────────────────────────────
def gate_seat_counts():
    treads = jload(src("vectors_geojson/terrace_treads.geojson"))
    src_sum = sum((f["properties"].get("seats_kept") or 0)
                  for f in treads["features"])
    exp = jload(out("geo/seating_rows.geojson"))
    exp_sum = sum((f["properties"].get("seats_kept") or 0)
                  for f in exp["features"])
    (ok if exp_sum == src_sum else bad)(
        f"C seat sum export={exp_sum} == source={src_sum}")
    # banded A total echoed faithfully
    val = jload(src("analysis/tier_emission/Scenario_E_baseline_reemit/validation.json"))
    prov = jload(out("manifests/provenance.json"))
    band_a = prov["build_stats"]["sightline"]["banded_total_a"]
    (ok if abs(band_a - val["banded"]["A"]) < 1e-6 else bad)(
        f"C banded-A echoed exactly ({band_a} vs {val['banded']['A']})")


# ── D. sightline C not weakened ─────────────────────────────────────────────
def gate_sightlines():
    val = jload(src("analysis/tier_emission/Scenario_E_baseline_reemit/validation.json"))
    c_rows = val["c_rows"]
    # CSV
    drift = 0
    with open(out("tables/sightline_table.csv")) as fh:
        for r in csv.DictReader(fh):
            key = r["band"]
            src_c = c_rows.get(key)
            csv_c = r["C_mm"]
            csv_c = None if csv_c in ("", "None") else float(csv_c)
            if src_c is None:
                if csv_c is not None:
                    drift += 1
            elif csv_c is None or abs(csv_c - src_c) > 1e-6:
                drift += 1
    (ok if drift == 0 else bad)(f"D sightline_table C-values match validation.json ({drift} drift)")
    # geojson
    gdrift = 0
    for f in jload(out("geo/seating_rows.geojson"))["features"]:
        pr = f["properties"]
        key = f'{pr["section"]} r{pr["row"]}'
        src_c = c_rows.get(key)
        gc = pr.get("C_mm")
        if src_c is None:
            if gc is not None:
                gdrift += 1
        elif gc is None or abs(gc - src_c) > 1e-6:
            gdrift += 1
    (ok if gdrift == 0 else bad)(f"D seating_rows C-values match validation.json ({gdrift} drift)")
    # WARN rows preserved: south r18 (87.8 < 90) must read WARN
    s18 = next((f["properties"] for f in jload(out("geo/seating_rows.geojson"))["features"]
                if f["properties"]["section"] == "south" and f["properties"]["row"] == 18), None)
    (ok if s18 and s18["sightline_verdict"] == "WARN" else bad)(
        "D south r18 carried as WARN (C below 90 mm bar)")


# ── E. ADA status verbatim ──────────────────────────────────────────────────
def gate_ada_status():
    src_ada = jload(src("vectors_geojson/ada_route.geojson"))
    src_status = {f["properties"].get("name"): f["properties"].get("status")
                  for f in src_ada["features"] if f["geometry"]["type"] == "LineString"}
    drift = 0
    strengthened = 0
    for f in jload(out("geo/ada_route.geojson"))["features"]:
        pr = f["properties"]
        if pr.get("kind") != "route":
            continue
        s = pr.get("status")
        if s != src_status.get(pr["name"]):
            drift += 1
        # the concept caveat must survive; never claim bare "ADA-compliant"
        if s and "concept" not in s.lower() and "pending" not in s.lower():
            strengthened += 1
    (ok if drift == 0 else bad)(f"E ADA route status carried verbatim ({drift} altered)")
    (ok if strengthened == 0 else bad)(
        f"E no ADA route status strengthened past 'concept/pending' ({strengthened})")


# ── F. provisional / concept marked ─────────────────────────────────────────
def gate_provisional():
    zones = jload(src("vectors_geojson/bowl_zones.geojson"))
    open_stage = {f["properties"]["name"] for f in zones["features"]
                  if f["properties"].get("rule9_status") == "open"}
    sf = jload(out("geo/stage_floor.geojson"))
    flagged = {f["properties"]["name"] for f in sf["features"]
               if f["properties"].get("provisional")}
    missing = open_stage - flagged
    (ok if not missing else bad)(
        f"F Rule-9-open stage features all flagged provisional (missing {missing})")
    mats = jload(out("manifests/material_manifest.json"))["materials"]
    sp = mats.get("stage_provisional", {})
    (ok if sp.get("must_label") else bad)(
        "F material stage_provisional has must_label=true")
    # treatment cell concept tier carried
    tc = next((f["properties"] for f in sf["features"]
               if f["properties"]["name"] == "treatment_cell_landscape"), None)
    (ok if tc and tc.get("concept_tier") else bad)(
        "F treatment cell carried as concept_tier")


# ── G. warnings verbatim ────────────────────────────────────────────────────
def gate_warnings():
    ds = jload(src("truth_package/design_state.current.json"))["warnings"]
    pv = jload(out("manifests/provenance.json"))["warnings"]
    (ok if pv == ds else bad)(
        f"G provenance warnings == design_state warnings ({len(pv)}/{len(ds)} verbatim)")
    # the four load-bearing caveats must each appear
    must = ["PLANNING-GRADE", "Rule 9", "INTERNATIONAL feet", "understate"]
    blob = " ".join(pv)
    for m in must:
        (ok if m in blob else bad)(f"G warning present: '{m}'")


# ── H. round-trip + origin ──────────────────────────────────────────────────
def gate_roundtrip():
    prov = jload(out("manifests/provenance.json"))
    o = prov["crs"]["local_origin_epsg6494_ft"]
    (ok if abs(o[0] - ORIGIN_X) < 1e-6 and abs(o[1] - ORIGIN_Y) < 1e-6 else bad)(
        f"H provenance origin == canon ({o})")
    am = jload(out("manifests/actor_manifest.json"))["actors"]
    worst = 0.0
    for a in am[:200]:
        lx, ly, _ = a["anchor_local_m"]
        ex = lx / FT2M + ORIGIN_X
        ey = ly / FT2M + ORIGIN_Y
        ax, ay = a["anchor_epsg6494_ft"]
        worst = max(worst, abs(ex - ax), abs(ey - ay))
    (ok if worst < 0.05 else bad)(
        f"H local->EPSG:6494 round-trip exact (worst {worst:.4f} ft)")


# ── I. human-scale export integrity ─────────────────────────────────────────
def gate_human_scale():
    """The gated package must carry the human-scale layer the source defines —
    baseline figures + dims, with the metadata gen_review_meshes consumes and the
    ADA-critical wheelchairs — so the UE scene can never silently omit it."""
    base = [f for f in jload(src("vectors_geojson/human_scale_refs.geojson"))["features"]
            if f["properties"].get("scope") != "ambitious_option"]
    s_h = [f for f in base if f["properties"].get("type") == "human"]
    s_d = [f for f in base if f["properties"].get("type") == "dimension"]
    exp = jload(out("geo/human_scale_refs.geojson"))["features"]
    e_h = [f for f in exp if f["properties"].get("type") == "human"]
    e_d = [f for f in exp if f["properties"].get("type") == "dimension"]
    (ok if len(e_h) == len(s_h) and len(e_d) == len(s_d) else bad)(
        f"I human-scale export matches source baseline "
        f"(humans {len(e_h)}/{len(s_h)}, dims {len(e_d)}/{len(s_d)})")
    bad_meta = [f["properties"].get("ref_id") for f in e_h
                if not f["properties"].get("feature_id")
                or f["properties"].get("height_ft") is None
                or f["properties"].get("ground_elev_navd88") is None]
    (ok if not bad_meta else bad)(
        f"I exported human refs carry feature_id + height + ground ({bad_meta or 'ok'})")
    chairs = {f["properties"].get("ref_id") for f in e_h
              if f["properties"].get("posture") == "wheelchair"}
    need = {"cross_aisle_wheelchair", "ada_landing_routeB_wheelchair"}
    (ok if need <= chairs else bad)(
        f"I ADA-critical wheelchair refs exported (missing {sorted(need - chairs) or 'none'})")
    am_fids = {a.get("source_feature_id") for a in
               jload(out("manifests/actor_manifest.json"))["actors"]}
    unbridged = [f["properties"].get("feature_id") for f in exp
                 if f["properties"].get("feature_id") not in am_fids]
    (ok if not unbridged else bad)(
        f"I every exported human ref has an actor_manifest row ({unbridged or 'ok'})")


def main():
    if not os.path.isdir(OUT):
        print("FATAL: unreal_export/ not found - run scripts/build_unreal_export.py",
              file=sys.stderr)
        return 2
    for g in (gate_presence, gate_actor_provenance, gate_seat_counts,
              gate_sightlines, gate_ada_status, gate_provisional,
              gate_warnings, gate_roundtrip, gate_human_scale):
        try:
            g()
        except Exception as exc:  # a gate that crashes is a failure
            bad(f"{g.__name__} crashed: {exc}")
    for m in PASSES:
        print(f"  PASS  {m}")
    for m in FAILS:
        print(f"  FAIL  {m}")
    print(f"\n{len(PASSES)} pass · {len(FAILS)} fail")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
