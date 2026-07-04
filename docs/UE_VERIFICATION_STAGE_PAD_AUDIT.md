# UE verification — Scenario E stage-pad audit

**Commit:** `3afaf49` (pass 1, pre-Phase-B) → **`b0b0e38`** (pass 2, Phase-B
adopted-deck re-import). Branch `stage-pad-audit-deck-method`.
**Date:** 2026-07-04. **Type:** read-only visual verification. **No design edits
in UE** — geometry is imported from the artifact pipeline, never hand-edited.

---

## PASS 2 — Phase-B adopted-deck re-import (commit `b0b0e38`) ✅

The Phase-B stage-zone re-emission (`stage_zone_reemit_report.md`) put the adopted
P_opt deck into the pipeline. The UE stage was then **re-imported from the new
export** (not hand-moved): `gen_review_meshes.py` staged the 4 adopted stage OBJ
meshes → imported via `StaticMeshTools.import_file` into `/Game/Meshes/CivicBowl`
→ spawned as 4 actors at the plan transform (origin, scale ×100) in
`Proposal_Editable/Stage` → the 3 inherited placeholder actors removed → level +
meshes saved.

**Result (definitive):**
- `Stage_zone*` (inherited placeholder) actors: **0** — placeholder gone.
- `Stage_adopted*` actors: **4** — core + apron + L/R shoulders present.
- New `stage_core` bounds match the old size but are **shifted +6.37 m (≈ 20.9 ft
  = the P_opt offset magnitude)** to the adopted position; scale ×100 correct.

**Post-reimport screenshots** (`unreal_export/verification/post_reimport/`):
- `04_overhead_plan.png` — adopted deck at the bowl focus; seating + orchestra +
  context intact.
- `03_stage_3quarter.png` — 3/4 aerial: deck + orchestra floor + bay + sunset.
- `01_audience_to_stage_bay.png` — human scale: the deck reads as a **low flat
  open-air deck (no upstage wall)** with the park/city/bay backdrop beyond; the
  re-emitted bay-axis marker sits alongside.

**Criteria (pass 2):** adopted P_opt deck **visible** ✅ · placeholder **gone** ✅
· stage = core + apron + shoulders (70×34 core preserved) ✅ · open-air, no shell ✅
· seating/ADA/treatment/context unchanged ✅. Pipeline gates for `b0b0e38` are all
green (see `stage_zone_reemit_report.md` §4).

**Hard-rule note:** the geometry came from the exported meshes at the exported
transforms; no actor was hand-moved, scaled, or reshaped. Context/Review/lighting
layers were untouched (targeted stage-only replacement).

---

## PASS 1 — pre-Phase-B read-only verification (commit `3afaf49`)

*(Superseded by pass 2. Retained for provenance: this pass found the D1
discrepancy — the scene still showed the inherited placeholder because only the
orchestra had been re-emitted. Phase-B (pass 2) resolved it.)*

## Live-UE status — EXECUTED (read-only, via UE MCP)

The user brought the UE MCP back up; this pass drove it **read-only** (no actors
placed/moved, no import, no scene save — camera moves + captures only, per the hard
rule). Loaded level: **`/Game/Maps/CivicBowl`**.

**Scene identity (enumerated live):** a full Scenario E review scene —
`Accepted_ReadOnly/Seating` = **45 tread actors**; `Proposal_Editable/Stage` =
3 actors labeled `Stage_zone_stage_core` + `stage_shoulder_left/right`;
`Concept_Landscape/EventFloor` = event-floor actor `StaticMeshActor_143`;
`Concept_ADA/Routes`+`/Landings` = ADA nodes/routes; treatment cell; full
`Context/*` city + terrain + bay + sunset lighting; canonical review CineCameras.

**Live geometry verification (via `get_actor_bounds`, compared to committed
`3afaf49` bowl_zones):**
- `Stage_zone_stage_core` bounds **77.6 × 64.4 ft** == committed `stage_core`
  (70×34-ish core) — **not** stale 52×26. ✅
- `event_floor` bounds major axis **98.9 ft** == committed re-emitted
  `orchestra_event_floor` (98.9 ft). ✅
- committed `orchestra ∩ stage_core = 0.0 sf` — the floor does **not** sit on the
  stage. ✅

**Currency caveat:** the scene was assembled in prior sessions and was **not
re-imported** from the `3afaf49` export in this pass. Its geometry matches the
committed state within AABB tolerance (~2.6 ft on the floor's minor axis, i.e.
within mesh-bound padding), but that tolerance exceeds the orchestra re-emission's
minor-axis delta, so I **cannot guarantee** the event-floor actor is the exact
re-emitted mesh vs a prior import. **Recommendation: re-import `unreal_export/`
(after D1 is resolved) to guarantee currency before any sign-off render.**

## Import source (same directory the pipeline writes)

`unreal_export/` — rebuilt by `scripts/build_unreal_export.py` from
`vectors_geojson/` (the pipeline's authoritative artifacts). Verified by
`scripts/verify_unreal_export.py` → **35 pass · 0 fail**. Provenance records
`git_commit: 3afaf49` in `unreal_export/manifests/provenance.json`, so the import
is pinned to this commit.

## Imported artifacts (110 actors)

| user checklist item | in export? | detail |
|---|---|---|
| seating rows | ✅ | 45 treads (`terrace_treads.geojson`); Band-A capacity 1243 |
| re-emitted `orchestra_event_floor` | ✅ | 1925.8 sf (re-emitted), from `bowl_zones` |
| treatment cell | ✅ | `treatment_cell_landscape` 5985.3 sf |
| ADA route | ✅ | `ada_route.geojson` (39 actors: 8 routes + 31 landings) |
| stage core (70×34) | ✅ (size) | `stage_core` 2379.7 sf ≈ 70×34 — see **D1** on position |
| **adopted stage/deck footprint** | ❌ | **not wired into the export** — see **D1** |
| `material_zones/event_floor` mirror | ➖ | export sources the `bowl_zones` orchestra directly (mirror not separately imported; the geometry it mirrors is present) |
| `route_corridors_C` | ➖ | export carries `ada_route` centerlines/landings, not the C corridor surfaces |
| Method B construction metadata | ❌ | not represented visually (annotation only — see criteria 8) |
| terrain (existing + proposed) | ✅ | 160,801-vert meshes + heightfields |
| cameras | ✅ | 7 (rim / row1 / row9 / upper_row / stage / ada_route) |

## Data-level verification vs the 8 criteria

| # | criterion | result | evidence |
|---|---|---|---|
| 1 | stage is current 70×34 core + adopted deck/apron, **not 52×26** | ⚠ **PARTIAL** | core is 2379.7 sf ≈ **70×34** and there is **no 52×26 anywhere**; BUT the export shows the **inherited** `stage_core` position without the five_facet_apron — the **adopted P_opt deck (2698.7 sf) is 19 ft away and not in the export** → **D1** |
| 2 | row/stage matches current Scenario E, not retired 35-ft open_low | ✅ (data) | 35-ft is retired from active metrics (comparator patched); adopted gaps 12.0/32.7/21.9 measured against the adopted deck. *Visual gap in the export reflects the inherited stage (D1).* |
| 3 | orchestra no longer intrudes into the adopted deck | ✅ | re-emitted floor 1925.8 sf, overlap with adopted footprint **0.0 sf** |
| 4 | ADA route present, not deleted | ✅ | `ada_route.geojson` present, 39 actors, rebuilt network |
| 5 | no stale `ada_ramp`/`ada_landing` zones | ✅ | **0** ada_ramp/ada_landing actors (string hits were labels only) |
| 6 | seats remain 1283/1243 | ✅ | export sightline table Band-A **1243.1**; nominal 1283 |
| 7 | Concept C route governing | ✅ | `ada_validation` governing = `C_naturalistic_promenade` |
| 8 | labels match Method B deck-over-compacted-base, not solid pad | ✅ (data) | Method B adopted (`STAGE_CONSTRUCTION_METHOD_DECISION.md`); 330.2 CY = rejected solid-pad upper-bound. *Not yet an in-scene annotation.* |

## Discrepancies — RETURN TO PIPELINE (do not fix in UE)

- **D1 — exported stage is the inherited position, not the adopted P_opt deck.**
  `build_unreal_export.py` sources the stage from `bowl_zones/stage_core`, which is
  still the **inherited** Rule-9-OPEN placeholder (correct 70×34 size, but inherited
  location, no five_facet_apron). This is expected: this session baked only the
  **orchestra** re-emission; the **stage-zone** re-emission to the adopted footprint
  is the deferred **Phase-B item** (`RULE9_DECISION_RECORD.md` "re-emit every
  stage-derived artifact from the adopted footprint"). **Until that Phase-B step
  runs, the adopted deck cannot be visually verified in UE.** Fix belongs in the
  pipeline (re-emit stage zones + optionally add the adopted footprint overlay to
  the export), not in UE.
- **D2 — two reference lines from a superseded source (low severity).**
  `bay_view_axis` and `focal_point_stage_front` are sourced from
  `design_open_low/stage_floor.geojson`. The 330° bay axis they encode is still
  canon-valid (P_opt keeps az150 / audience-faces-330), so the geometry is fine, but
  the **source file is the superseded package** — a provenance smell to re-home onto
  a current source during the Phase-B stage re-emission.

## Ready-to-execute UE protocol (for the live pass)

1. Sync the UE workspace to `3afaf49` (or the branch); confirm the project imports
   from this `unreal_export/`.
2. Create level/layer **`ScenarioE_StagePadAudit_Verification`**.
3. Import the verified artifacts above. **Do not import** `design_open_low` stage
   geometry, `seating_rows.geojson`/`stage_floor.geojson` from the old package, any
   `ada_ramp`/`ada_landing`, or a stale orchestra floor.
4. Debug overlays: stage core; occupied deck/apron (from `adopted_stage_footprint`
   once D1 is resolved); non-governing shoulders; `orchestra_event_floor` (show 0
   overlap vs adopted deck); ADA route; row 1 + row 2; treatment cell; annotation
   *"330.2 CY = rejected solid-pad upper bound, not adopted fill; construction =
   Method B deck-over-compacted-base."*
5. Cameras + screenshots → `unreal_export/verification/` (or `renders/ue_live/`):
   - `01_row1_to_stage_human_scale.png`
   - `02_row5_ada_cross_aisle.png`
   - `03_centerline_section.png`
   - `04_overhead_plan_stage_orchestra_row1.png`
   - `05_toward_bay_open_backdrop.png`
6. Confirm each criterion visually; append PASS/FAIL + screenshot paths here.

## Screenshots (captured live, read-only)

Saved under `unreal_export/verification/`:
- `04_overhead_plan.png` — overhead plan: three-section seating bowl, stage at
  focus, orchestra floor, bay/city/terrain context. **The decisive verification
  frame** (stage / orchestra / row-1 clearance visible from above).
- `04_overhead_plan_labeled.png` — same, with actor labels (cameras + ADA nodes).
- `00_stage_focus_annotated.png` — stage area with grid + labels (cameras, ADA
  nodes, `Ref_lineage_focal_point_stage`).
- `01_row1_to_stage.png` — human-scale row-1 eye level toward the stage: the deck
  reads as a **thin flat plane** with open park/bay beyond and **no upstage wall**
  (confirms the open-air "flat actors, no shell" stage).

Not captured (deferred with the re-import): a dedicated row-5/ADA cross-aisle view,
centerline section, and a clean toward-bay backdrop — these add little until the
export is re-imported and D1 is resolved (they would document the inherited stage).

## Hard-rule compliance

Read-only throughout: only viewport-camera moves and captures + actor bounds/label
queries. **No actors placed or moved, no import, no scene edit or save, nothing
"fixed."** The substantive findings (D1, and the re-import currency caveat) are
recorded and returned to the artifact pipeline, per the hard rule.
