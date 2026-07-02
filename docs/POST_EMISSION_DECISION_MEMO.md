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

### Decision 1 — which seating scope to advance → **ADOPTED: (A) Scenario E baseline (2026-07-02)**

**Decided: (A) Scenario E baseline — 1,243 validated / 1,283 nominal Band-A seats.** No
stronger reason emerged in the docs to choose modest or ambitious: this is framed here as a
civic/budget choice, not an engineering mandate; no capacity/attendance target exists in any
doc; and the `INEVITABILITY` minimum-justified-intervention ethos leans conservative. Baseline
is the accepted control and requires **no geometry re-point** (the in-situ package already sits
on the 1,283 frame). **Off-ramp on file:** modest_normalization is the cheapest expansion
(+114 seats for ~$2k / 25.3 CY, best marginal efficiency ≈48.5 QA/$1k) — the obvious first step
*if* capacity is ever desired; re-open this decision to take it.

The options as they stood: **(A) Scenario E baseline** (1,243/1,283; no further work),
**(B) modest_normalization** (+114 for 25.3 CY — the cheapest validated step), or
**(C) ambitious seating scope** (+262 for 47.3 CY — the validated Pareto knee). All three are
emission-validated. Adopting B or C instead would mean: update the `DESIGN_CANON` ledger, point
the in-situ package at that tier's emitted geometry (`analysis/tier_emission/<tier>/geometry.geojson`),
and re-run the package audit.

### Decision 2 — close Rule 9 (stage) → **CARRIED PROVISIONAL (2026-07-02)**

The stage bundle is now adopted **provisionally** (doc state): P_opt placement (path 3, az150
kept, bay Δ 0°, residuals −6.7 ft / −6.3° declared) + five_facet_apron + path-4 wide-fan +
T1_deck_only. Record: `analysis/stage_adoption/RULE9_DECISION_RECORD.md`. **Not yet `resolved`**
— that is an *audit* state, reached only when the stage package is re-emitted against the adopted
footprint (Decision 1 = baseline), EarthworkEngine CY replaces the planar proxy, and
`scripts/audit_in_situ_package.py` is genuinely green. `carried_provisional` is a document state,
not a green audit; the red gate stands until the package is valid.

## Standing guardrails

- **Claude Design is UN-PAUSED, stage flagged provisional** (`docs/claude_design_handoff.md`) —
  depict the stage as provisional (never resolved/monumental) until Rule 9 is audit-`resolved`.
- Seat or stage claims beyond the adopted baseline require re-emission + re-validation
  (canon Rules 3/5) before they may be quoted.
