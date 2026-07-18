# Post-emission decision memo — adopted directions and implementation status

_2026-06-11. **This memo is the controlling statement of project state.** Where it
disagrees with `analysis/intervention_tiers/INTERVENTION_TIER_REPORT.md`, this memo and
the emission validation behind it (`analysis/tier_emission/TIER_EMISSION_VALIDATION.md`,
commit `f6b1d96`) win: the tier report is pre-emission analysis; the emission validation
measured the same claims on emitted geometry._

## Validated state (emission-validated, strict per-segment Rule 4)

| Scenario | Band-A validated | Δ vs baseline | Incr earthwork | Status |
|---|--:|--:|--:|---|
| **Scenario E baseline** | 1,243 (1,283 nominal) | — | — | **ACCEPTED control** (seating/ADA/drainage). Stays the fallback regardless of the decision below. |
| **modest_normalization** (seating) | 1,357 (1,397 nominal) | **+114** | 25.3 CY | EMITTED + VALIDATED, all hard gates pass |
| **ambitious_shaped_bowl** (seating scope) | 1,505 (1,516 nominal) | **+262** | 47.3 CY | EMITTED + VALIDATED, all hard gates pass |

Geometry source for all three: Scenario E three-section civic bowl (east / bend / south,
`design_extended_bays` composition). **`design_open_low`'s single-fan geometry is
superseded for seating and must not be used as governing geometry** (it still sources
only the inherited stage object and the treatment cell).

## Rejected / not live (do not resurrect)

- **N1 east contour extension: REJECTED on emission.** 0 of its +149 seats survive —
  every walk path beyond the east az-85 cap fails the extended-bays z-resid/crossing
  gates. The east flank is terrain-bounded, proven on emitted geometry (memo F1).
- **The 1,665-seat ambitious claim is not a live validated number.** It contained N1.
  Quote ambitious as **+262 / 1,505 validated** (1,516 nominal).
- `optimized_civic_bowl`: never separately emitted; its +263 contained N1 — read as
  ≈ +114–119, a subset of ambitious. Not a distinct live option.
- `idealized_reference_geometry`: dominated reference ceiling only.
- Scenario B: diagnostic only (canon Rule 1).

## Owner decisions and implementation follow-ups

**Owner decision recorded 2026-07-18.** The human selections are settled;
geometry-dependent implementation and validation remain separate.

1. **Seating scope C — ambitious shaped bowl is adopted.** Quote 1,505 Band-A /
   1,516 nominal, +262 seats and 47.3 CY versus the validated control. **A — Scenario
   E baseline remains the fallback.** The current in-situ package still points at A
   until package propagation and re-audit are complete.
2. **Rule 9 Path A — audience-axis alignment is adopted as the stage direction.**
   Target approximately az 124° / audience facing 304°. The exact footprint, apron,
   typology, fan declaration, and stage-derived artifacts remain pending; the inherited
   az-150 stage stays provisional and Rule 9's geometry-validation gate remains
   non-passing.
3. **ADA Concept C — naturalistic promenade is adopted at planning grade.** It
   preserves seating and remains pending civil/code detailing. This adoption does not
   assert ADA compliance.

The machine-readable authority is `analysis/decision_packet/adopted_decisions.json`.
No downstream artifact may promote `decision_status: adopted` into completed
implementation without the required re-emission and validation.

## Standing guardrails

- **Claude Design stays PAUSED** (`docs/claude_design_handoff.md` banner) until Rule 9
  is closed **or** the stage is explicitly carried as provisional in the handoff.
- Seat or stage claims beyond the table above require re-emission + re-validation
  (canon Rules 3/5) before they may be quoted.
