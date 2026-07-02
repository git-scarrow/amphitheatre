# Rule 9 closure — stage adoption decision record

_Instance of `STAGE_RULE9_DECISION_TEMPLATE.md`. Closes (provisionally) `DESIGN_CANON` Rule 9 /
`docs/POST_EMISSION_DECISION_MEMO.md` Decision 2._

- **Status:** `carried_provisional` — bundle adopted 2026-07-02; **not `resolved`.**
  Provisional is a *doc* state (decision recorded, Claude Design un-paused flagged-provisional).
  `resolved` is an *audit* state, reached only when the package audit is green **and** the row-1
  gaps are re-confirmed against the adopted Decision-1 seating tier (see "Path to resolved").
- **Decided by / date:** user instruction, 2026-07-02.

---

## Provenance correction (Rule 6)

An earlier draft of this record (2026-07-02, superseded) **mis-captured the instruction** as the
stage-refit sweep's generic **Path C = `az135_lat-10`** (stage yawed to ~135°, audience facing
315°, ~15° off the bay). It then raised a "dominance flag" recommending the sweep candidate
`az150_lat-20`. **Both were wrong references:**

- The instruction was **P_opt** — the in-situ study's path-3 candidate, which **keeps az 150 and
  the 330° bay axis (0° bay Δ)**. There is no 15°-off-bay rotation; the dominance table in the
  earlier draft compared the wrong candidate.
- `az150_lat-20` comes from the **superseded sweep frame** (section-level alignment only, no row-1
  pocket check) and must not be adopted unchecked — see "Why not az150_lat-20" below.

This correction is recorded rather than silently overwritten per Rule 6 (provenance honesty).

---

## Adopted bundle (the adoption unit is a bundle, not a placement)

Source of all figures: `analysis/in_situ_normalization/STAGE_SHAPE_STUDY.md` (§A placement, §A2
front, §B–D elements) and `DESIGN_CANON.md` Rule 9 paths 1–4.

| Component | Adopted | Key measured values |
|---|---|---|
| **Placement** | **P_opt** (Rule 9 **path 3**, executed on the bay axis) | az 150 kept → audience faces **330°, bay Δ 0%**; −15.5 ft lateral + upstage pullback; **residuals −6.7 ft / −6.3° declared**; row-1 gaps **12.0 / 32.7 / 21.9 ft** (e/b/s, all ≥ 12); cell gap **32.0 ft**; deck-alone obstruction **0.0% bay / 1.7% foreground** |
| **Stage front** | **five_facet_apron** | 319 sf, 6.0 ft projection, family-aimed facets: **bend −5.6 ft**, **east pocket held at 12.0**, south 18.8; **zero obstruction delta** (0.0/1.1); adds ~8.9 CY |
| **Fan** | **path-4 wide-fan declaration** (load-bearing regardless of placement) | `formal_fan_half_deg: 75`, `formal_fan_angle_deg: 150`, `scenarioE_fan_type: wide_three_section_civic_bowl`; acoustic consequence of the wide east coverage to be noted in the config comment |
| **Element bundle** | **T1_deck_only** (adopted minimum) | **0.0% bay / 1.7% foreground**, ACCEPTABLE; op score 10/40. **T2_covered_civic (roof)** stays a *tested, separately adoptable* upgrade (8.6% bay / 1.7% foreground, op 27/40) — the stage decision does **not** smuggle in the roof/architecture decision |

**Alignment justification:** bay-axis-preserving path 3 (P_opt). The 330° bay view is retained
in full; the residual −6.7 ft / −6.3° offset is explicitly declared (the row-1 pocket forbids
zeroing it — see below). **Bay-view delta: 0°.** **Fan gate:** satisfied by the path-4 wide-fan
re-declaration (east section is inside FAN_HALF = 75°). **Front-row distance:** ≥ 12 ft every
family (bend row-1 governing gap 32.7 → 29.6 with apron, both ≥ 30 ft template floor is met at
bend; east/south are ≥ 12 ft by the tighter pocket rule). **Sightlines / ADA / earthwork:** to be
re-confirmed on emission (Phase B).

## Why not `az150_lat-20` (the superseded-frame candidate)

`az150_lat-20` is ~90% of the **full lateral shift P_lat (~−22 ft), which touches east row 1
(gap 0.0 ft) and is infeasible** under the in-situ row-1 pocket gate. Its attractive +3° mismatch
was scored in the sweep frame, which never checked whether the stage corner sits in the east
front-row pocket. The in-situ pass — the *superseding* gate — concluded the pocket **forbids
zeroing the offset**; P_opt is the constrained optimum that keeps every family ≥ 12 ft. You cannot
adopt a number the superseding gate has not priced.

## Why path-4 (wide-fan) is required regardless of placement

Under **any** az 150 stage — `az150_lat-20` included — the east section sits ~70–75° off the SF
axis, **outside the inherited ±55° fan gate** (`STAGE_REFIT_SWEEP.md` §1 structural finding). A
placement move cannot fix this; the fan must be re-declared wide (path 4). That is why the
adoption unit is a **bundle** (placement + front + fan + element), not a placement.

## Optional tie-break before finalizing (one run, not a re-sweep)

Re-score `az150_lat-20` **inside the in-situ frame** — row-1 pocket gaps + five_facet_apron +
obstruction. If it clears **every** gate ≥ 12 ft, it legitimately beats P_opt on residuals at
equal bay Δ, and is adopted **with the same bundle**. If any pocket < 12 ft (expected, given it is
90% of the infeasible P_lat), **P_opt stands**. Do **not** adopt it unchecked. (Phase B item.)

## Path to `resolved` (all OPEN — do not claim resolved until every box is checked)

- [ ] Re-emit the adopted stage footprint; re-run `scripts/stage_refit_sweep.py` +
      `scripts/audit_in_situ_package.py` → **green**.
- [ ] Run the `az150_lat-20` in-situ tie-break (above).
- [ ] **EarthworkEngine CY recompute** for the adopted footprint — replace the planar-proxy CY
      (`STAGE_REFIT_SWEEP.md` §9 data gap) with a DEM-differenced number.
- [ ] Write the path-4 fan fields into `harness_config.yaml` + acoustic note.
- [ ] Re-emit every stage-derived artifact from the adopted footprint (bowl_zones/material_zones
      orchestra + untouched-slope, the six viewpoint stations, the event-mode screen line, grading
      rasters); drop Board 01's provisional floor/backdrop patches.
- [x] **Re-confirm row-1 gaps against the adopted Decision-1 tier.** ✅ **Decision 1 ADOPTED
      2026-07-02: (A) Scenario E baseline (1,243/1,283).** Baseline *is* the 1,283 frame the P_opt
      gaps (12.0/32.7/21.9) were solved against — so they are already the adopted-tier gaps; no
      re-measurement needed. `resolved` is no longer blocked on Decision 1.
- [ ] Flip `DESIGN_CANON` Rule 9 + this record to `resolved`; drop the provisional banner in
      `docs/claude_design_handoff.md`.

## What this record changed (provisional)

Updated to `carried_provisional`: this record, `docs/DESIGN_CANON.md` Rule 9 + ledger row, and
`docs/claude_design_handoff.md` (un-paused, stage flagged provisional). **Not** changed yet
(Phase B / resolved-gated): `harness_config.yaml` fan fields, emitted stage artifacts, and the
`resolved` status. Rule 9 is **carried_provisional**, not closed.
