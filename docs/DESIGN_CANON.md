# Design Canon — invariant rules for the Petoskey Pit formal bowl

**Status:** governing invariants for the agentic-clay system and all human design review.
Sits below `INEVITABILITY.md` (which provides narrative rationale) and above any
individual scenario memo.

---

## Scenario status

| Scenario | Status | Authority |
|---|---|---|
| **Scenario B** — 0.5 ft fill-clip, "self-balancing" | **REJECTED** as formal seating baseline | `SCENARIO_B_VALIDATION.md` §§1–7; `INEVITABILITY.md` worked proof |
| **Scenario D** — B + selective tread restoration (+26 CY) | **ACCEPTED** as designed baseline for formal terraced seating | `INEVITABILITY.md` worked proof; `score_inevitability.py` → 10/10 ACCEPTED |
| **Scenario E** — D + aisles + ADA + drainage (500.8 CY total) | Seating / ADA / drainage cost-proxy **ACCEPTED** where geometry is emitted and validated · **Stage refit CARRIED PROVISIONAL (2026-07-02)**: bundle adopted provisionally — P_opt placement (path 3; az150 kept, bay Δ 0°, residuals −6.7 ft / −6.3° declared) + five_facet_apron front + **path-4 wide-fan** (`formal_fan_half_deg 75`) + T1_deck_only. Not yet `resolved` (package audit + EarthworkEngine CY + Decision-1 tier gap re-confirm pending; resolved blocked on Decision 1). Status: **ACCEPTED (seating/ADA/drainage) · stage carried_provisional** | `SCENARIO_E_CIVIC.md`; `analysis/stage_adoption/RULE9_DECISION_RECORD.md`; `analysis/in_situ_normalization/STAGE_SHAPE_STUDY.md`; Rule 9; `INEVITABILITY.md` §concept→cost-proxy |

---

## Eight invariant rules

Any violation produces a hard rejection from `InevitabilityEngine.hard_rejections()`.

### Rule 1 — Scenario B is a diagnostic, not a baseline

Scenario B is retained as a minimum-fill **diagnostic** that reveals where the terrain
dips below the tread plane. It is never a seating baseline. Formal seat counts derived
from the as-built B surface (217 Band-A seats) are not a deliverable — they are evidence
of what the clip costs.

### Rule 2 — Scenario D is the designed baseline

Scenario D (B + selective tread restoration) is the formal-seating design of record.
The ~26 CY restoration move is the **minimum effective intervention**: without it, treads
dish, formal seats can't be counted, and "the terraces don't read as terraces." The 26 CY
is not waste — it is what makes the form inevitable. Adopting B while quoting D's seat
count is a design lie; the engine rejects it.

### Rule 3 — Scenario E cost-proxy scope

Scenario E may claim cost-proxy status only where every cost-bearing move has:
- emitted real polygons (`cost_status: geometry_backed`), **and**
- passed polygon-intersection validation against all tread polygons (`validation_status: validated`).

Intent-only ADA routes or drainage sketches remain at `concept` tier and may not appear
in a cost table. The engine enforces this: a cost-proxy design whose ADA or drainage rests
on intent-only moves is hard-rejected. See `_control_uncarved_aisle.json` for the rejection
proof.

### Rule 4 — A row segment is formal only when all four gates pass simultaneously

Band A (formal fixed seat) requires — on the **actual built surface**, not the ideal plane:

| Gate | Threshold |
|---|---|
| Sightline | C ≥ 90 mm |
| Cross-slope | ≤ 2.5 % |
| Longitudinal slope | ≤ 1.0 % |
| Surface continuity | no `clip_under_seat` flag (or `clip_under_seat` erased by a validated restoration move) |

No gate may be silently omitted. Plane-fit slope per-segment on the actual surface is
required; raster gradient bleeds the inter-row riser into the reading and is disqualified.

### Rule 5 — Formal seating is earned by restoration, not assumed

A segment flagged `clip_under_seat` may only be counted as Band A after the restoration
move that repairs the tread to its ideal plane has been both **emitted** (real geometry)
and **validated** (passes all four gates on the restored surface). The raw count of
segments whose *ideal* plane passes gates is a target, not a deliverable.

### Rule 6 — Provenance must match geometry

A design move is honest only when its recorded provenance matches the operation that
actually created the design object. This is the **Generate / Validate / Narrate** rule:

- **Generate** — name the actual operation: row reassignment, terrain-following fill,
  contour trace, etc.
- **Validate** — confirm with geometry checks *after* the object exists.
- **Narrate** — describe what happened, not a retrospective story that makes validation
  scaffolding sound like the generator.

The cross-aisle is the canonical instance: the geometry is `union(row9,row10).difference(retained)` —
a role reassignment. The engine requires `geometry_source: row_reclassification` and
`seam_derived: False`. Labelling it a "seam discovery" or "desire-line trace" is a
provenance failure even when the geometry is correct.

### Rule 7 — Seam-derived circulation is rejected

A circulation band inside the seating rake that declares `seam_derived: True`, or that
does not declare `geometry_source: row_reclassification`, is hard-rejected by the engine.
The correct generative act for a cross-aisle is row-band reclassification. If a different
generator is used, it must be named and its provenance fields updated accordingly — the
rule is honesty, not a mandate for one specific generator.

### Rule 8 — No formal seats on clipped or dished tread

Counting formal capacity on a segment whose tread surface has been dished by the fill-clip,
without a validated restoration move on file, is hard-rejected. This applies regardless of
what the *ideal* plane would produce; the building inspector grades the actual ground, not
the drawing.

> **Accounting note (2026-06-11, tier emission validation).** ADA ramp B's switchback
> corridor crosses south row 6 and displaces ~4 seats that Scenario E's capacity never
> netted out — the same displacement class as the rows-9/10 cross-aisle, much smaller.
> Quote Scenario E strict-segment Band-A as 1,243 of 1,283 nominal (south r18 station-C
> sits 2–7 mm under the 90 mm bar, within DEM noise; bend r1 rides the 2.5 % cross-slope
> ceiling). Source: `analysis/tier_emission/TIER_EMISSION_VALIDATION.md` F4.

### Rule 9 — Stage geometry and fan declaration must match the emitted seating

> **Closure path:** fill in `analysis/stage_adoption/STAGE_RULE9_DECISION_TEMPLATE.md`.
> Status 2026-06-11: OPEN. P_opt / faceted aprons / typology shortlist are tested
> candidates, none adopted; the emission-validated seating tiers all carry the
> inherited az-150 stage. See `docs/POST_EMISSION_DECISION_MEMO.md`.

The Scenario E seating (rows 1-18, 1 283 Band-A seats across east / bend / south sections)
produces a seat-weighted audience centroid at bearing **124.4°** from the current focal point,
and an effective fan span of **≈130°** (east section centroid −74.6° from axis; south +40.1°).

The inherited stage configuration (`design_open_low`, axis 150°) does not match:

| Discrepancy | Value |
|---|---|
| Angular mismatch (stage axis vs audience centroid bearing) | **+25.6°** (stage 26° too far clockwise) |
| Lateral audience offset from stage normal axis | **−22.5 ft** (audience mass left of axis) |
| East section bearing from SF | −74.6° — outside declared ±55° fan gate (by 20°) |
| Effective seating span | ≈130°, not 110° / ±55° as declared in `harness_config.yaml` |

A stage configuration is accepted for Scenario E only when **one** of the following paths is
explicitly declared and wired:

1. **Audience-axis path** — stage axis corrected to ≈124° (audience faces ≈304°);
   bay-view deviation (26° off 330°) acknowledged and justified.
2. **Bay-axis path** — stage keeps 150° back-azimuth (audience faces 330°); focal point
   shifted ≈22 ft toward bearing 60° to centre the axis on the audience centroid; east
   section remains marginally outside ±55° and must be declared as wide-fan overflow.
3. **Compromise path** — partial yaw (e.g. az135) + partial lateral shift; both residuals
   declared and justified.
4. **Wide-fan civic override** — Scenario E is explicitly declared a wide-fan three-section
   civic bowl spanning ≈130°; `harness_config.yaml` updated with
   `formal_fan_half_deg: 75`, `formal_fan_angle_deg: 150`, `scenarioE_fan_type: wide_three_section_civic_bowl`;
   acoustic consequences of the wide-fan coverage noted.

**Adopted (carried_provisional, 2026-07-02) — a bundle, not a placement:** placement
**path 3 = P_opt** (az 150 kept, audience faces 330°, bay Δ 0°; residuals −6.7 ft / −6.3°
declared; row-1 gaps 12.0/32.7/21.9 ft, all ≥ 12; cell gap 32 ft) + **path 4 wide-fan**
declaration (`formal_fan_half_deg: 75`, `formal_fan_angle_deg: 150`,
`scenarioE_fan_type: wide_three_section_civic_bowl`) + **five_facet_apron** front +
**T1_deck_only** element (0.0% bay / 1.7% foreground). Path 4 is load-bearing regardless of
placement (the east section sits outside ±55° under any az 150). Record:
`analysis/stage_adoption/RULE9_DECISION_RECORD.md`.

Scenario E now carries status:
**"seating / ADA / drainage cost-proxy ACCEPTED · stage carried_provisional"**

The engine must not report 10/10 ACCEPTED while the stage is only provisional. **Decision 1 is
now ADOPTED: (A) Scenario E baseline (1,243/1,283)** (`POST_EMISSION_DECISION_MEMO.md`) — so the
P_opt row-1 gaps (measured at the 1,283 frame) are already against the adopted tier, and
`resolved` is **no longer blocked on Decision 1**. `resolved` now requires only: the stage
package re-emitted against the adopted footprint, the EarthworkEngine CY recompute (replacing the
planar proxy), and `scripts/audit_in_situ_package.py` genuinely green — `carried_provisional` is a
document state, not a green audit; the red gate stands until the package is valid. The sweep's `az150_lat-20` is **superseded** — it was scored in the section-level
frame without the in-situ row-1 pocket gate, and is ~90% of the full shift P_lat, which touches
east row 1 (infeasible); do not adopt it unless a one-run in-situ re-score clears every pocket
≥ 12 ft.

**Update 2026-06-10 — the in-situ studies supersede the sweep's candidate set.**
The sweep scored section-level alignment only; the in-situ pass adds row-1
pocket clearances, an independent (non-circular) stage-zone re-derivation, a
ray-traced visual-obstruction envelope, and the stage front as a geometry
variable:

- `analysis/in_situ_normalization/STAGE_SHAPE_STUDY.md` — constrained
  placement **P_opt** (az 150 kept, −15.5 ft lateral + upstage pullback;
  residuals −6.7 ft / −6.3° declared per path 3; all row-1 gaps ≥ 12 ft);
  §A2 stage-front study (family-aimed **faceted aprons** close the bend
  distance ~5.5 ft without violating the east/south pockets — symmetric arcs
  fail); §B–D superstructure element menu with per-family obstruction deltas
  and operational scores under the visual-envelope rule (height is never a
  rejection reason).
- `analysis/stage_seating_decoupling/CIRCULARITY_AUDIT.md` — seating may not
  justify stage placement (the march's focal point descends from the stage
  lineage); the southern pan-toe zone band is independently re-derived.

Adopting a path now means: placement + stage-front geometry + element bundle,
then re-emitting every stage-derived artifact from the adopted footprint
(see `rule9_implications.adoption_requires` in
`analysis/in_situ_normalization/stage_typology_scores.json`).

---

## Cross-references

| Concern | Artifact |
|---|---|
| Hard rejection enforcement | `scripts/harness/inevitability.py` — `InevitabilityEngine.hard_rejections()` |
| B-rejected / D-accepted proof | `scripts/score_inevitability.py` → `analysis/inevitability/verdict.md` |
| Spatial validation driver | `scripts/validate_scenarioB.py` → `SCENARIO_B_VALIDATION.md` |
| Provenance regression test | `scripts/test_cross_aisle_provenance.py` |
| Governing narrative | `INEVITABILITY.md` |
| Constrained-optimisation substrate | `PROBLEM_DEFINITION.md` |
| Scenario E geometry emitter | `scripts/scenarioE_civic.py` → `SCENARIO_E_CIVIC.md` |
| Stage refit sweep | `scripts/stage_refit_sweep.py` → `analysis/stage_refit/STAGE_REFIT_SWEEP.md` |
| Stage shape / front / obstruction study (2026-06-10) | `scripts/stage_shape_study.py` + `scripts/obstruction_envelope.py` → `analysis/in_situ_normalization/STAGE_SHAPE_STUDY.md` |
| Stage↔seating circularity break | `scripts/stage_seating_decoupling.py` → `analysis/stage_seating_decoupling/CIRCULARITY_AUDIT.md` |
| In-situ package audit gate | `scripts/audit_in_situ_package.py` |

---

## Quick-read decision table

| Question | Answer |
|---|---|
| Can I quote 1,452 formal seats for Scenario B? | No — as-built B yields 217 Band-A seats. |
| Can I quote 1,452 formal seats for Scenario D? | Yes — after the 26 CY restoration move passes validation. |
| Can I use Scenario B's CY numbers? | Yes — as diagnostic earthwork quantities. Not as "the cost of 1,452 seats." |
| Is the 26 CY restoration optional? | No — it is the minimum effective intervention that makes terraces read as terraces. |
| Can I call a desire-line the cross-aisle? | No — the aisle is built from row-9/10 geometry. Any other generator must be named. |
| Can Scenario E's ADA cost appear in a project budget? | Only if the ADA switchback geometry is emitted and validated. |
| Is Scenario E's stage configuration accepted? | **Carried provisional (2026-07-02).** Bundle adopted: P_opt (path 3; az150, bay Δ 0°, residuals −6.7 ft / −6.3° declared) + path-4 wide-fan + five_facet_apron + T1_deck_only (`analysis/stage_adoption/RULE9_DECISION_RECORD.md`). **Construction method SELECTED 2026-07-03: Method B — deck over compacted base** (`analysis/stage_adoption/STAGE_CONSTRUCTION_METHOD_DECISION.md`; ratifies the `material_zones` spec; solid pad rejected; ~98 CY planning estimate, precise CY Phase-B EarthworkEngine). Not yet `resolved` — package audit + geometry-backed EarthworkEngine CY + Decision-1 tier gap re-confirm pending (resolved blocked on Decision 1). |
| Can I quote Scenario E as "10/10 ACCEPTED"? | Seating, ADA, and drainage: yes. Stage/fan: no — only carried_provisional. Full 10/10 requires Rule 9 `resolved`. |
