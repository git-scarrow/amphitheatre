#!/usr/bin/env python3
"""Pipeline artifact contract — post-full-pipeline invariants.

The Scenario E vector state is valid ONLY after the FULL pipeline runs in order:

    build_in_situ_geometry.py      (emitter: treads/edges/bowl_zones; re-emits the
                                    schematic orchestra against the adopted deck;
                                    does NOT emit ada_ramp/ada_landing zones)
  → rebuild_ada_routes.py          (ADA stage 1: rebuilt node network + Dijkstra)
  → design_ada_routes.py           (ADA stage 2: Concept-C designed centerlines)
  → design_constructed_ada.py      (ADA stage 3: Concept-D + C-vs-D validation)
  → build_site_context.py          (material_zones/site_context; accessible_paths
                                    sourced from the rebuilt route_corridors_C)
  → build_truth_package.py         (source-hash snapshot)
  → scripts/comparators/audit_comparators.py

Emitter-only outputs are an INTERMEDIATE product — do not inspect or commit them
as the final Scenario E state. This script asserts the contract holds AFTER the
full pipeline. Exit non-zero on any violation.

Run:  .venv/bin/python scripts/check_pipeline_artifact_contract.py
"""
import json
import os
import sys

from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.affinity import translate

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VEC = os.path.join(REPO, "vectors_geojson")
fails, oks = [], []


def check(cond, msg):
    (oks if cond else fails).append(msg)


def load(rel):
    with open(os.path.join(REPO, rel)) as fh:
        return json.load(fh)


# ── 1. no stale design_open_low ADA zones may reappear in bowl_zones ──────────
bz = load("vectors_geojson/bowl_zones.geojson")
znames = [f["properties"].get("name") for f in bz["features"]]
stale = {"ada_ramp", "ada_landing"} & set(znames)
check(not stale,
      f"no stale ada_ramp/ada_landing zones in bowl_zones (found {stale})"
      if stale else "no stale ada_ramp/ada_landing zones in bowl_zones")

# ── 2. the live rebuilt ADA route survives and is the rebuilt network ─────────
ar_path = os.path.join(VEC, "ada_route.geojson")
check(os.path.exists(ar_path), "live ada_route.geojson survives the pipeline")
if os.path.exists(ar_path):
    ar = load("vectors_geojson/ada_route.geojson")
    roles = {f["properties"].get("role") for f in ar["features"]}
    check("ada_route_concept" in roles,
          f"ada_route.geojson is the rebuilt network (ada_route_concept), not legacy"
          f" (roles {roles})")
    check(len(ar["features"]) > 0, "ada_route.geojson is non-empty")

# ── 3. final ADA route gates unchanged (all pass; Concept C governs) ──────────
v = load("analysis/ada_rebuild/ada_validation.json")
check(v.get("topology", {}).get("ok") is True, "ADA topology gate OK")
check(v.get("conflicts", {}).get("ok") is True, "ADA conflicts gate OK")
check(v.get("slopes", {}).get("ok") is True, "ADA slopes gate OK")
check(v.get("smoothness", {}).get("ok") is True, "ADA smoothness gate OK")
check(v.get("recommendation_c_vs_d", {}).get("governing_recommendation")
      == "C_naturalistic_promenade",
      "ADA governing route is C_naturalistic_promenade")

# ── 4. orchestra re-emitted against the adopted deck (overlap → 0) ────────────
orch = shape([f for f in bz["features"]
              if f["properties"].get("name") == "orchestra_event_floor"][0]["geometry"])
adf_path = "analysis/in_situ_normalization/adopted_stage_footprint.geojson"
if os.path.exists(os.path.join(REPO, adf_path)):
    adf = load(adf_path)["features"][0]
    off = adf["properties"]["lateral_offset_from_inherited_ft"]
    deck = shape(adf["geometry"])
    inh = sorted((shape(f["geometry"]) for f in load(
        "analysis/scenarioE_civic/geometry.geojson")["features"]
        if f["properties"].get("role") == "stage_surface"),
        key=lambda g: g.area, reverse=True)
    full = unary_union([deck] + [translate(g, xoff=off[0], yoff=off[1]) for g in inh[1:]])
    ov = full.intersection(orch).area
    check(ov < 1.0, f"orchestra_event_floor clears the adopted stage footprint "
          f"(overlap {ov:.1f} sf, must be ~0)")

# ── 5. material_zones/event_floor mirrors bowl_zones/orchestra_event_floor ────
mz = load("vectors_geojson/material_zones.geojson")
ef = [f for f in mz["features"]
      if f["properties"].get("name") == "event_floor"]
check(bool(ef), "material_zones/event_floor mirror present")
if ef:
    sd = shape(ef[0]["geometry"]).symmetric_difference(orch).area
    check(sd < 1.0, f"material_zones/event_floor mirrors bowl_zones/"
          f"orchestra_event_floor (symdiff {sd:.1f} sf)")

# ── 6. adopted seating capacity intact (1283 nominal / 1243 Band-A) ───────────
ds = load("truth_package/design_state.current.json")
blob = json.dumps(ds)
check("1283" in blob and "1243" in blob,
      "truth_package reports seats 1283 nominal / 1243 Band-A")

# ── report ────────────────────────────────────────────────────────────────────
for m in oks:
    print(f"  ok   {m}")
for m in fails:
    print(f"  FAIL {m}")
print(f"\nPIPELINE ARTIFACT CONTRACT: {len(oks)} pass · {len(fails)} fail")
if fails:
    print("CONTRACT VIOLATED — the repo is not in a valid post-pipeline state.")
    sys.exit(1)
print("CONTRACT HELD.")
