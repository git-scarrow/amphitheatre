# Post-emission decision memo — what is decided, what is live

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

## The two live decisions

### Decision 1 — which seating scope to advance

Choose one of: **(A) Scenario E baseline** (1,243/1,283; no further work),
**(B) modest_normalization** (+114 for 25.3 CY — the cheapest validated step), or
**(C) ambitious seating scope** (+262 for 47.3 CY — the validated Pareto knee).
All three are emission-validated; this is now a civic/budget choice, not an open
engineering question. Adoption of B or C means: update the `DESIGN_CANON` ledger,
point the in-situ package at the chosen tier's emitted geometry
(`analysis/tier_emission/<tier>/geometry.geojson`), and re-run the package audit.

### Decision 2 — close Rule 9 (stage)

**Nothing about the stage was adopted by the emission validation.** P_opt, the faceted
aprons, and any roofed/utilitarian typology remain *tested candidates*; the emitted
tiers all carry the inherited az-150 stage with Rule 9 OPEN. Decision 1 is deliberately
independent of Decision 2 (stage–seating decoupling,
`analysis/stage_seating_decoupling/`). Close Rule 9 via
`analysis/stage_adoption/STAGE_RULE9_DECISION_TEMPLATE.md`.

## Standing guardrails

- **Claude Design stays PAUSED** (`docs/claude_design_handoff.md` banner) until Rule 9
  is closed **or** the stage is explicitly carried as provisional in the handoff.
- Seat or stage claims beyond the table above require re-emission + re-validation
  (canon Rules 3/5) before they may be quoted.
