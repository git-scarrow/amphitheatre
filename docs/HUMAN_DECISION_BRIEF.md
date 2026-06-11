# Human decision brief — seating scope (Decision 1)

_2026-06-11. One page. Source of truth: `docs/POST_EMISSION_DECISION_MEMO.md` (controlling)
and the emission validation behind it (`analysis/tier_emission/TIER_EMISSION_VALIDATION.md`,
commit `f6b1d96`). Visuals: `boards/04_seating_options_comparison.png` (plan, same scale),
`boards/05_seating_options_section.png` (true-scale section). Table:
`analysis/decision_packet/decision_table.csv`._

## What you are deciding

Which seating scope to advance. **All three options are emission-validated on the real
surface** — this is a civic/budget choice, not an open engineering question.

| | Option | Band-A validated | Δ seats | Incr. earthwork | Status |
|---|---|--:|--:|--:|---|
| **A** | Scenario E baseline | 1,243 (1,283 nominal) | — | — | ACCEPTED control; the fallback regardless |
| **B** | modest_normalization | 1,357 (1,397 nominal) | **+114** | 25.3 CY | EMITTED + VALIDATED, all hard gates pass |
| **C** | ambitious (seating scope) | 1,505 (1,516 nominal) | **+262** | 47.3 CY | EMITTED + VALIDATED, all hard gates pass |

## What the options physically are (board 05)

The same 3.6-ft treads continued up the already-validated natural rake — no new typology,
no retaining walls (max incremental depths 0.95 ft cut / 1.59 ft fill, well under the 3-ft
trigger). **B** promotes row 19 in all three families. **C** promotes rows 19–20 and adds
a 100-mm comfort regrade of rows 11–18, which also heals the baseline's soft south r18.
Promoted-row seated eyes sit at 640+ ft, well above the 618.5-ft NW rim — the bay + sky
backdrop is preserved.

## Cost framing

Emitted CY is ~2–2.6× the earlier band-area accounting (terraced-edge effect); at planning
unit rates the difference is **$300–900 with factors — noise against the $2k–56k tier
costs. The Pareto ordering is unchanged**: C remains the validated knee.

## Guardrails (do not relitigate)

- **N1 east contour extension is REJECTED on emission** — 0 of its +149 seats survive.
  The east flank is terrain-bounded, proven on emitted geometry. It is not drawn on any
  board and must not be resurrected.
- **1,665 is not a validated seat count** (it contained N1). Ambitious is quoted
  **1,505 validated / +262**.
- `optimized_civic_bowl` is not a distinct live option (its surviving content is a subset
  of C); `idealized_reference_geometry` is a dominated reference ceiling; Scenario B is
  diagnostic only.

## The stage is NOT part of this decision

Rule 9 remains **OPEN**. Every option carries the inherited az-150 stage as
**provisional** — drawn dashed in all visuals. P_opt, the faceted aprons, and the roofed
typologies are tested candidates only; none is adopted. Close Rule 9 separately via
`analysis/stage_adoption/STAGE_RULE9_DECISION_TEMPLATE.md` (Decision 2 — deliberately
independent, per the stage–seating decoupling study). Claude Design stays paused until
Rule 9 closes or the stage is explicitly carried provisional in the handoff.

## Recommended posture

If any expansion is funded, **C (ambitious seating scope) is the validated Pareto knee** —
most seats per validated CY. **B** is the cheapest validated step if budget is capped.
**A** costs nothing further and remains the fallback in all cases.

## Decision record (FILL IN)

- **Chosen scope:** A / B / C: ______
- **Reasons (civic / budget):** ______
- **Decided by / date:** ______

**Follow-ups on adopting B or C:** update the `DESIGN_CANON` ledger; point the in-situ
package at `analysis/tier_emission/<tier>/geometry.geojson`; re-run the package audit.
Seat or stage claims beyond the table above require re-emission + re-validation
(canon Rules 3/5) before they may be quoted.
