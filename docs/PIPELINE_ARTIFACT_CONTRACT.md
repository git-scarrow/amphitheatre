# Scenario E pipeline artifact contract

The Scenario E vector state is produced by a **multi-stage pipeline**. Individual
stages emit **intermediate** products that are only mutually consistent after the
whole chain runs. Do not inspect, trust, or commit a partial run as final state.

## Canonical order

```
1. build_in_situ_geometry.py    treads / edges / bowl_zones / scenarioE_geometry
2. rebuild_ada_routes.py        ADA stage 1 — rebuilt node network + Dijkstra
3. design_ada_routes.py         ADA stage 2 — Concept-C designed centerlines,
                                              route_corridors_C, ada_validation
4. design_constructed_ada.py    ADA stage 3 — Concept-D + C-vs-D merge into
                                              ada_validation (concepts block)
5. build_site_context.py        material_zones / site_context
6. build_truth_package.py       source-hash snapshot + web_viewer data
7. scripts/comparators/audit_comparators.py
```

Stages 2–4 must run **before** stage 5: `build_site_context.py` sources the
`accessible_paths` material from the rebuilt `route_corridors_C.geojson` (stage 2),
not from bowl_zones.

## Invariants (asserted by `scripts/check_pipeline_artifact_contract.py`)

1. **No stale `ada_ramp` / `ada_landing` zones in `bowl_zones.geojson`.** The
   scenarioE ADA layer was rejected on 2026-06-12; `build_in_situ_geometry.py`
   deliberately does not emit those zones. They must not reappear.
2. **The live `ada_route.geojson` survives** every stage and is the *rebuilt*
   network (`role: ada_route_concept`), never legacy fragments (those live in
   `legacy_ada_rejected.geojson`). The emitter must never delete it — this was the
   `emitter_deletes_ada_route` bug (now fixed + guarded).
3. **ADA route gates unchanged:** topology / conflicts / slopes / smoothness all
   OK; governing route `C_naturalistic_promenade`.
4. **`orchestra_event_floor` is re-emitted against the adopted P_opt deck edge**
   (overlap with the adopted footprint ≈ 0). Baked into the emitter, not a manual
   post-step.
5. **`material_zones/event_floor` mirrors `bowl_zones/orchestra_event_floor`**
   (produced by stage 5).
6. **Seating capacity intact:** 1283 nominal / 1243 Band-A.

## What is *not* covered here

Governance-doc state (e.g. `claude_design_handoff.md` PAUSED marker) is checked by
`audit_in_situ_package.py`, not this contract. This contract is strictly about
vector-artifact consistency across the pipeline.
