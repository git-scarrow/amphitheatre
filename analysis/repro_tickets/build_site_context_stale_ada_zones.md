# Repro ticket — `build_site_context.py` references removed `ada_ramp`/`ada_landing` zones

**Type:** generator bug (KeyError) / stale layer. **Severity:** medium (breaks the
pipeline's material-zones stage). **Status:** ✅ **RESOLVED 2026-07-03.**

## Symptom
`build_site_context.py` crashed at its `accessible_paths` material:
```
KeyError: 'ada_ramp'
  zones["cross_aisle"] + zones["ada_ramp"] + zones["ada_landing"] + ...
```

## Root cause (pre-existing, 3 weeks latent)
`build_site_context.py` and `material_zones.geojson` were last committed
**2026-06-10** (`676b43c`), when `build_in_situ_geometry.py` still emitted
`ada_ramp`/`ada_landing` zones into `bowl_zones.geojson`. The **2026-06-12** ADA
rebuild (`58179a4`) rejected that layer — the emitter stopped emitting those zones
— but `build_site_context.py:183` was never updated. It therefore KeyError'd on any
run against a post-rebuild `bowl_zones`, and `material_zones.geojson` sat stale.
This was invisible because the emitter itself was rarely run (it also deleted
`ada_route.geojson`; see `emitter_deletes_ada_route.md`).

## Fix (2026-07-03)
`accessible_paths` now sources its ADA surfaces from the **rebuilt Concept-C
corridors** (`route_corridors_C.geojson`, the governing route) plus the still-live
`cross_aisle` + `promenade_hinge` zones. `build_site_context.py` must run **after**
ADA stage 2 (which produces `route_corridors_C`). Documented in
`docs/PIPELINE_ARTIFACT_CONTRACT.md`.

## Verification
Full pipeline runs clean; regenerated `material_zones.geojson` changes only three
features vs the stale 06-10 baseline — `accessible_paths` (new rebuilt-corridor
source), `event_floor` (re-emitted orchestra), `existing_slope_grass` (derived
leftover) — the other six are byte-stable. `event_floor` mirrors
`bowl_zones/orchestra_event_floor` (symdiff 0.0). Asserted by
`scripts/check_pipeline_artifact_contract.py` (invariants 4–5).
