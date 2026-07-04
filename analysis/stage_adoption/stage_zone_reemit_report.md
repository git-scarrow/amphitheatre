# Phase-B stage-zone re-emission — adopted P_opt deck into the artifact pipeline

**Date:** 2026-07-04. Closes the RULE9 "re-emit every stage-derived artifact from
the adopted footprint" item for the **stage zones** (the orchestra was done
2026-07-03). The adopted P_opt deck/apron is now the geometry source of truth in
`bowl_zones` → `material_zones` → `unreal_export`; the inherited placeholder is
retired from the emitted stage.

## 1. Adopted stage geometry emitted (bowl_zones + material_zones)

`build_in_situ_geometry.py` now emits the **adopted** stage (from
`adopted_stage_footprint.geojson`, decomposed by `_adopted_stage_components`) when
the adoption artifact exists, falling back to the inherited placeholder otherwise.

| zone | area sf | edge_class | occupied | governs ≥12 ft pocket |
|---|--:|---|:--:|:--:|
| `stage_core` | 2379.7 (**70×34 preserved**) | `performance_core` | yes | no (inside deck) |
| `stage_apron` (NEW) | 319.2 | `occupied_deck_apron` | yes | **yes — governed edge** |
| `stage_shoulder_left` | 346.0 | `lateral_nonoccupied` | **no** | no |
| `stage_shoulder_right` | 346.0 | `lateral_nonoccupied` | **no** | no |

All stage zones carry `construction_method: "Method B — deck over compacted base"`
and `placement: "P_opt (Rule 9 path-3 + path-4 wide-fan)"`. Shoulders are
non-governing visual/landscape (not occupied deck unless explicitly adopted).
`stage_core` centroid now matches the adopted deck (19533098, not the inherited
19533091/750757) — **the stage moved to the adopted position.**

`material_zones/hardscape_stage` now unions core + apron + shoulders (3390.8 sf).

## 2. Orchestra re-derived against the adopted stage

`orchestra_event_floor` = `hull(adopted deck ∪ row-1) − adopted footprint − treads`
= **2885.3 sf**, overlap with the adopted deck/footprint **0.0 sf**. (Replaces the
2026-07-03 minimal subtraction that was scaffolded on the inherited hull; the clean
adopted derivation reclaims the ground the inherited stage vacated.) Schematic /
concept-tier → **no quantity change.**

## 3. design_open_low lineage quarantined from the active export

`build_unreal_export.py` no longer reads `design_open_low/stage_floor.geojson`.
`bay_view_axis` + `focal_point_stage_front` are **re-emitted from the adopted deck**
(`adopted_stage_footprint.geojson` centroid + the canonical 330° bay azimuth) into a
`Reference/BayAxis` layer. **0 actors in the export are sourced from
design_open_low** (was 2). Remaining textual mentions are honest historical-lineage
notes (treatment-cell provenance) — not active geometry sources.

## 4. Gates — all pass, no capacity movement

| gate | result |
|---|---|
| seats (truth_package) | **1283 nominal / 1243 Band-A — unchanged** |
| stage_current_geometry_gate | governed deck **12.02 ft PASS**; orchestra overlap **deck 0.0 / full 0.0** |
| pipeline artifact contract | **HELD** |
| ADA stages 1/2/3 | topology / conflicts / slopes / smoothness **OK**; **C_naturalistic_promenade governs**; seat displacement unchanged (D1 158 / D2 121 / D3 95 / C 0) |
| comparator audit | **PASS 0/0** |
| audit_in_situ_package | **ACCEPTED** (48 pass / 0 fail) |
| verify_unreal_export | **35 pass / 0 fail** |

**Intentional downstream effect (adopted-deck-caused):** the ADA arrival node
follows the orchestra centroid, which moved with the adopted stage — routes
re-solved to 8 routes + 19 landings (was 31), fewer ramp runs, all gates still
green. No seat/capacity change.

## 5. Export

`unreal_export/` rebuilt: 99 actors (45 treads, 27 ADA, 19 human-scale, **6 stage
zones incl. `stage_apron`**, 2 re-emitted bay-axis refs). Stage actors now carry
`edge_class` / `occupied` / `governs_row1_pocket` / `construction_method` /
`placement`. Source commit recorded in `unreal_export/manifests/provenance.json`.

## 6. Known residual (minor, deferred)

`human_scale_refs.geojson` positions one figure "50 ft along the stage-front axis
about `design_open_low/.../focal_point_stage_front`" — a human-scale anchor still
referencing the old focal point (~20 ft stale). It is in the human-scale layer, not
the stage. Follow-up: regenerate `human_scale_refs` against the adopted focal point
(`build_human_scale_refs.py`). Not blocking the stage verification.

## Hard rule

Unreal is the renderer, not the source of truth. This change was made in the
**artifact pipeline**; the UE scene is re-imported from these artifacts, not
hand-edited.
