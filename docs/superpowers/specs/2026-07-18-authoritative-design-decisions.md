# Authoritative Design Decisions Record

**Date:** 2026-07-18  
**Authority:** Project owner  
**Scope:** Record the owner's three selected design directions without claiming that downstream geometry, exports, or engineering validation have already been completed.

## Objective

Replace the repository's ambiguous "pending human decision" state with an authoritative, machine-readable record of these owner selections:

1. **Seating scope C — ambitious shaped bowl** is adopted as the design direction. The emission-validated scope remains 1,505 Band-A seats (1,516 nominal), an increase of 262 seats and 47.3 CY over the Scenario E baseline. **Seating scope A — Scenario E baseline** remains the explicit fallback.
2. **Rule 9 Path A — audience-axis alignment** is adopted as the governing stage direction. The target axis is approximately azimuth 124 degrees, so the audience faces approximately 304 degrees. Exact footprint, apron, typology, and stage-derived geometry remain to be emitted and validated.
3. **ADA Concept C — naturalistic promenade** is adopted as the planning direction. It preserves seating and remains subject to civil/code detailing; no compliance claim is created by this decision.

## Status Model

Each decision has two independent status fields:

- `decision_status`: whether the owner has selected the direction.
- `implementation_status`: whether the repository's geometry, package outputs, and required validation represent that direction.

All three decisions have `decision_status: adopted`. Implementation status remains explicit:

- Seating C: `pending_package_propagation` until the in-situ package points at the emitted ambitious geometry and the package audit is rerun.
- Rule 9 Path A: `pending_geometry_and_validation` until the stage footprint, fan declaration, stage-front geometry, and typology are selected, emitted, and validated.
- ADA Concept C: `planning_grade_pending_civil_detailing` because the governing concept exists but civil/code details remain unchecked.

No generated artifact may translate an adopted decision into a claim of completed implementation. The currently emitted inherited azimuth-150 stage remains provisional until replaced.

## Source of Truth

Create `analysis/decision_packet/adopted_decisions.json` as the single machine-readable authority. It will contain:

- schema identifier and decision date;
- authority label (`project_owner`);
- the three decision identifiers and selected options;
- seating fallback A;
- decision and implementation status values;
- factual metrics already validated in existing sources;
- required follow-up actions and source references.

The file must not invent a rationale that the owner did not provide. Reasons will be recorded as `owner_selection_no_additional_rationale_recorded`.

## Synchronized Human Documents

Update the existing governing documents rather than adding competing narrative authorities:

- `docs/POST_EMISSION_DECISION_MEMO.md`: change the former live decisions to adopted directions and list implementation follow-ups.
- `docs/HUMAN_DECISION_BRIEF.md`: fill the seating decision record with C and fallback A.
- `analysis/stage_adoption/STAGE_RULE9_DECISION_TEMPLATE.md`: convert the template into a decision record for Path A while keeping exact footprint, apron, and typology explicitly outside this decision and retaining the closure checklist.
- `docs/ADA_CONCEPT_C_VS_D.md`: distinguish the existing recommendation from the owner's formal adoption of Concept C.
- `docs/DESIGN_CANON.md`: record the owner-selected directions without marking geometry-dependent gates as complete.
- `README.md`: replace "decision open" wording with adopted-direction and propagation-pending wording.

## Generated Truth Package

Update `scripts/build_truth_package.py` to consume `adopted_decisions.json` and emit the selected directions into `truth_package/design_state.current.json` and `web_viewer/data/site_data.js`.

The generated truth data must:

- expose the authoritative choices under `adopted_decisions`;
- stop describing seating, Rule 9 direction, and ADA concept selection as awaiting a human choice;
- continue warning that the displayed seating/package and inherited stage do not yet fully implement the adopted state;
- keep Rule 9 geometry validation non-passing until its required follow-ups are complete;
- retain planning-grade and civil/code caveats for ADA Concept C.

The existing `pending_decisions` channel may remain for genuinely unresolved implementation choices, such as exact stage footprint/apron/typology, but must not present the owner-selected A/C choices as undecided.

## Validation

Add automated checks that fail before implementation and pass afterward. They must verify:

1. The authoritative JSON records seating C with fallback A, Rule 9 Path A, and ADA Concept C.
2. The truth-package generator consumes that file rather than duplicating the choices as hard-coded strings.
3. Generated design state exposes all three decisions as adopted.
4. Generated warnings still identify seating package propagation, Rule 9 geometry/validation, and ADA civil detailing as incomplete.
5. No governing document still calls these three owner selections pending or open as human decisions.
6. Existing geometry and audit tests remain green; no geometry files are regenerated as part of this change.

## Out of Scope

- Switching the in-situ package to the ambitious seating geometry.
- Re-emitting or relocating the stage.
- Selecting a stage apron, exact footprint, or roof/typology.
- Performing Rule 9 sightline, acoustic, obstruction, or earthwork validation.
- Producing construction documents or asserting ADA compliance.
- Publishing new Speckle, Unreal, website, or other model versions.

Those actions are follow-up implementation work governed by the authoritative selections recorded here.
