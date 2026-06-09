# The Inevitability Canon — governing principle for the agentic clay

**Status:** governing document for the agentic-clay system. Sits above
`PROBLEM_DEFINITION.md` (which defines the constrained optimization) and reframes
what the optimization is *for*.
**Adopted:** 2026-06-07, after the Scenario B spatial validation
(`SCENARIO_B_VALIDATION.md`) showed a minimum-fill design can be cheap and wrong.

---

## The governing sentence

> The clay is not there to answer *"Can we fit an amphitheater here?"*
> It is there to answer:
> **"What kind of amphitheater is already latent in this land, and what is the
> least, most graceful intervention needed to reveal it?"**

The clay stops being primarily an earthwork *minimizer* and becomes a site-affordance
*composer*. Its job is not the cheapest surface. It is to **discover where the site
already wants to become something, then make the smallest set of moves that intensify
that latent form.**

## The design principle

**Beauty here comes from making the intervention feel inevitable** — not invisible,
not maximally cheap, not mathematically optimal in isolation. Inevitable means:

- the rows look **found in the hill**, not imposed on it;
- the stage belongs at the **hinge** between bowl, flat pan, treatment cell, and bay;
- the outer edges **dissolve into landscape** instead of pretending every clipped
  fragment is formal seating;
- drainage, access, sightlines, and procession are **part of the composition**, not
  afterthoughts;
- the project preserves the site's **open-air character** instead of becoming a fake room.

## "Inevitable," made agent-checkable

> A design is inevitable when every visible intervention is either **compelled by a
> site affordance**, **required by performance**, or **justified by a deliberate civic
> choice** — and no major form is arbitrary, ornamental, or merely leftover from
> optimization.

Core rule:
- A move is **allowed** only if it has ≥1 site reason **and** ≥1 performance-or-civic reason.
- A move is **preferred** if it satisfies multiple reasons with one gesture (multi-duty).
- A move is **rejected** if it solves one metric while damaging the larger spatial reading.

**The final test:** *if a move can be removed without making the place worse, it was
not inevitable.* (Encoded as `Move.inevitable()` requiring a non-empty
`rejection_if_removed`.)

This is a filter that runs **before** human review, not a replacement for it. The model
can measure consistency and catch false success; it cannot know when a place has become
memorable. Final selection always requires a human.

---

## Replace "cheap" with "minimum effective intervention"

The agent must not ask *"How do I move the least dirt?"* It must ask *"What is the
least intervention that makes the place feel intentional, comfortable, accessible, and
worth visiting?"*

This is exactly why **Scenario D, not Scenario B, is the designed baseline.** The extra
~26 CY of restoration is not waste — it is the minimum effective intervention that lets
the terraces read and function as terraces. Scenario B is retained only as a
**misleading minimum-fill diagnostic**, never as a design of record.

---

## The Site Affordance Map (the missing layer)

A layer between raw terrain and engineering checks. Detected by
`scripts/harness/affordance.py` (`AffordanceEngine`); every affordance carries a
`provenance` tag (`computed` / `config` / `validation`) so an asserted constant is
never mistaken for a measurement.

| Affordance | What the agent detects | Status on this site (detected) |
|---|---|---|
| **Natural rake** | slopes already suitable for seating/lawn | fan ground rises outward over **100%** of the fan, **+28 ft** of natural rake, mean 27%/ft → the design rides a latent bowl |
| **Bowl hinge** | where flat pan becomes seating slope | R ≈ **68 ft**, elev ≈ 610 → stage/forecourt belongs here |
| **View axis** | bay, sky, stage, treatment cell | face **330° NNW** to bay (581.4 ft); upstage stays open |
| **Edge conditions** | streets, clipped tips, entrances | Petoskey/Mitchell/Lake hard clips; rows **21–25** are clipped tips → landscape |
| **Drainage paths** | where water already moves | spills **NE to bay**; treatment cell bottom 609.1 — drainage as landscape structure |
| **Strong zones** | worth spending earthwork | Band A formal lower bowl (rows 1–18) |
| **Weak zones** | should become lawn/planting/overlook | Bands B/C/D — rows 19–25 demote, don't pretend |

---

## Design moves (vocabulary, not parameters)

The agent composes with **moves that carry consequences**, not interchangeable
parameters. Defined in `scripts/harness/inevitability.py` (`MOVE_VOCAB`):

```
reveal_contour_terrace          restore_formal_tread
dissolve_row_into_lawn          thicken_edge_as_landscape_shoulder
convert_clipped_tip_to_overlook bend_access_route_with_contour
place_landing_at_view_pause     frame_stage_laterally_without_blocking_bay
use_swale_as_planted_room_edge  borrow_from_high_side_to_complete_low_tread
demote_weak_outer_capacity_to_picnic_terrace   preserve_open_upstage_view
```

Each move is stored with the schema below; a move that cannot fill it out does not survive:

```yaml
move_id: D1_restore_formal_treads
move_type: restore_formal_tread
geometry: rows 1-18 segments flagged clip_under_seat, C_ideal>=90
site_reasons:        [natural bowl curvature, within core formal seating rake]
performance_reasons: [restores 2% cross-slope, removes clip_under_seat dishing, holds C>=90mm]
civic_reasons:       [completes a continuous legible lower bowl, a terrace must read as a terrace]
cost:                {cut_cy: 0.0, fill_cy: 26, gross_cy: 26}
effects:             {formal_seats: +1235, visual_legibility: increased, drainage_risk: reduced}
rejection_if_removed:[formal seating discontinuity, clip dishing under seats, mid-tread ponding]
status: accepted
```

---

## The four ledgers — definition of done

A design is **done** only when it passes all four (`InevitabilityEngine.ledgers`):

1. **Performance ledger** — sightlines, slope, ADA, drainage, earthwork, constructability
   (sourced from `SCENARIO_B_VALIDATION.md` gates).
2. **Affordance ledger** — every move cites real detected site affordances (≥3 distinct).
3. **Role ledger** — every surface classified: formal seat / lawn / path / stage / landing /
   planting / drainage / overlook / no-count. No "ambiguous leftover."
4. **Justification ledger** — every move has a why-here and why-this-shape; none is removable
   without loss. **This is the inevitability check.**

## The ten inevitability rules (agent-checkable)

| # | Rule | Done means |
|---|---|---|
| 1 | Terrain agreement | ≥80% of formal seating on low-intervention terrain bands after restoration |
| 2 | Minimal effective intervention | every added CY tagged: formal tread / ADA / drainage / stage / landing / safety |
| 3 | Multi-duty geometry | each major move solves ≥2 problems |
| 4 | Formal hierarchy | no surface remains ambiguous; every polygon has a civic role |
| 5 | Honest capacity | formal seats only where sightline ∧ slope ∧ clipping ∧ continuity pass |
| 6 | Edge dissolution | clipped/weak outer rows become landscape, not pseudo-formal |
| 7 | View preservation | no tall upstage element blocks the bay/sky corridor |
| 8 | Processional clarity | access connects to meaningful landings, not compliance scars |
| 9 | Drainage legibility | water reinforces landform; treads don't dish/pond under seats |
| 10 | No arbitrary scars | no fragment exists only as a parameter-sweep residue; all role-tagged |

## Hard rejection rules (any one ⇒ automatic reject)

Encoded in `InevitabilityEngine.hard_rejections`:
- a formal seat counted on clipped/dished tread;
- a clipped fragment with no assigned landscape/seating role;
- low-earthwork claimed by omitting seat-zone / ADA / drainage / construction surfaces;
- a move that solves one metric while damaging the larger reading (e.g. drains by dishing seats);
- a stage element that blocks the bay/sky view without a stated civic reason;
- a surface visible in plan with no use classification;
- an arbitrary move (fails the allow rule — missing site or performance/civic reason).

## Positive acceptance (a move is strong if it does ≥2)

`uses_existing_contour · clarifies_seating_bowl · improves_sightlines · improves_access ·
improves_drainage · preserves_bay_view · creates_useful_edge_or_landing ·
reduces_artificial_grading · turns_fragment_into_landscape · adds_daily_nonevent_value`

The best moves do three or four at once (a cross-aisle that follows a contour, disperses
wheelchair seating, becomes a mid-bowl landing, offers a view pause, and intercepts drainage
behind the lower rows — one line solving five problems).

---

## Scoring (proxies, not the judge)

```
terrain_fit   = fraction of moves with a site reason
civic_fit     = fraction of moves with a civic reason
multi_duty    = mean reasons-per-move
inevitability = (terrain_fit + civic_fit)*5 + multi_duty
                − 2*arbitrary_moves − 3*hidden_failures − 0.01*gross_CY
```

The score filters before human review. It is never the final word.

---

## Worked proof — B rejected, D inevitable

`scripts/score_inevitability.py` runs the engine over both scenarios using the real
validation numbers (`analysis/inevitability/verdict.md`):

| | Scenario B (min-fill diagnostic) | Scenario D (designed baseline) |
|---|---|---|
| Verdict | **REJECTED — not inevitable** | **ACCEPTED — inevitable** |
| Ledgers (perf/aff/role/just) | ❌ ❌ ❌ ❌ | ✅ ✅ ✅ ✅ |
| Done checklist | 4/10 | 10/10 |
| Inevitability score | −10.8 | +14.2 |

B is cheap and wrong: it counts formal seats on dished tread, omits ADA/drainage to look
low-CY, and its one move has no civic or performance reason — removing it loses nothing, so
it is not inevitable. D spends the minimum effective intervention (~26 CY) so terraces read
as terraces, dissolves clipped fragments into overlook/landscape, demotes weak rows honestly,
and keeps the bay axis open. **The added dirt performs visible civic work — that is what makes
it feel found, not imposed.**

## The agent loop (target)

1. **Read the site** — affordance map (slopes, views, drainage, edges, hinge).
2. **Propose a spatial idea** — e.g. formal lower bowl + dissolving upper lawn + open bay stage.
3. **Sculpt only where the idea needs help** — restore treads, shape access, feather edges.
4. **Classify every surface** — formal / lawn / path / landing / planting / drainage / no-count.
5. **Validate hard gates** — sightline, slope, ADA, drainage, constructability, survey uncertainty.
6. **Critique the composition** — inevitable, graceful, civic, open?
7. **Produce families, not one optimum** — the Composer (`scripts/harness/composer.py`)
   *generates* one Design per family from the affordance map + validation data, and the
   engine grades each. Eight characters today: Civic Bowl · Meadow Bowl · Festival Bowl ·
   Processional Bowl · Stormwater Garden Bowl · Minimal Intervention Bowl · Ceremonial Bay
   Bowl · Neighborhood Daily-Use Bowl.

### The engine generates, then critiques itself

The Composer writes move sets; the InevitabilityEngine grades them with the same rules.
A generated family is promoted to formal only where its *ideal* plane passes every gate,
and it spends the restoration CY to earn those seats. Restoration cost scales with formal
commitment — minimal 5 CY/483 seats → civic 26 CY/1452 seats — a genuine minimum-effective-
intervention gradient, not price points on one design. **Control:** delete the restoration
move from the Civic Bowl and the same engine rejects it (formal seats on dished tread) — the
composer cannot assert capacity it has not earned. See
`analysis/inevitability/families/FAMILIES.md`.

## Implementation map

| Concern | Artifact |
|---|---|
| Site affordance detection | `scripts/harness/affordance.py` |
| Move schema, ledgers, rules, scores | `scripts/harness/inevitability.py` |
| **Design generation (families)** | `scripts/harness/composer.py` → `scripts/generate_designs.py` → `analysis/inevitability/families/` |
| **Geometry emitter (Scenario E)** | `scripts/scenarioE_civic.py` → `scripts/render_scenarioE.py` → `analysis/scenarioE_civic/` → `SCENARIO_E_CIVIC.md` |
| B-vs-D proof + affordance map output | `scripts/score_inevitability.py` → `analysis/inevitability/` |
| Performance gates (sightline/slope/clip/continuity) | `scripts/validate_scenarioB.py` → `SCENARIO_B_VALIDATION.md` |
| Constrained-optimization substrate | `PROBLEM_DEFINITION.md`, `scripts/harness/` |

### Concept → cost-proxy: the intent-vs-geometry invariant

An intent move may lift **concept** ranking but may **not** satisfy a **cost-proxy** gate
until it emits polygons (`cost_status: geometry_backed`) and passes validation on them
(`validation_status: validated`). The engine enforces this: a cost-proxy design whose ADA
or drainage rests on intent-only moves, or whose cost-bearing move reports placeholder CY,
is hard-rejected. Composed families are therefore always `concept`; only the Scenario E
emitter, which draws real surfaces, can reach `cost_proxy`.

**Scenario E status (civic_bowl):** DRAWN and ACCEPTED as cost_proxy — 10/10 acceptance
criteria, **500.8 CY** total (restored treads 172 · cross-aisle/causeway rows 9–10 **68** [section 60 + transition ramps 9] · ADA switchbacks 205 ·
flank swales 74 · +topsoil). **Formal capacity is 1,283 net seats — 1,452 nominal
minus 169 displaced by the accessible cross-aisle**, which consumes seating rows 9 and 10.
Sightlines hold C≥90 on rows 1–18; the schematic ADA straight alignments (10%/18%, FAIL)
were re-graded to 8.33% switchbacks with 9 landings; flank swales fall to the treatment
cell with **0 tread conflicts**.

**Surface-conflict integrity (added after a render audit).** Circulation/drainage may not
silently overlap counted seating. Three structural rules:
1. Every surface that touches the seating fan runs a **full-polygon intersection** test
   against the tread polygons (not centerlines/IDs); non-trivial overlap → `not_validated`.
2. **At cost-proxy, any geometry-backed move that failed its own validation hard-rejects the
   design** — proven by two controls: `_control_uncarved_aisle.json` (REJECTED — seats left on
   un-restored tread) and `_control_flat_midpoint_ponds.json` (REJECTED — flat 0% section ponds).
   The engine rejected two swale alignments and three cross-aisle attempts before clean geometry passed.
3. **The aisle IS the row object — it's a causeway over rows 9–10, not a desire line.** Said
   plainly: recolor two middle rows as one band and join them. Built from the *actual* row-9/10
   tread geometry (`union(row9,row10).difference(retained)`), not a freeform access path and not
   a concentric arc (the rows are **not** concentric about the focus — outer rows curve inward at
   the flanks, so a nominal-radius ring cut across rows 11–16). The aisle subtracts retained
   treads, so overlap is **0 sqft** by construction, and the 169 seats it occupies are displaced
   from the formal count. The nearest-row check is a **guard, not a derivation**: walk the two
   rows' spines and confirm every point's nearest row is one of them (passes by construction —
   that's the point). The old `mid_cross_aisle` desire line drifts **6 rows** and is kept only as
   a regression guard proving why the causeway is the right object. *Lesson: when a "derivation"
   collapses to a trivial reclassification, say so — don't build proof apparatus around an object
   you've already stopped drawing.*

**Plan honesty is not section honesty — the cross-aisle had to pass both.** Resolving *which rows*
(the plan question) left *how the band's surface grades* (the section question) open. A sweep of
**7 adjacent row-pairs × 5 section strategies = 35 candidates** settled it on the actual leftover
footprint, not on centerline assumptions (`scripts/sweep_cross_aisle.py`,
`analysis/cross_aisle_sweep/RECOMMENDATION.md`). Four findings are now canon:

- **Rows 9|10 is confirmed by the sweep, not assumed.** It wins balance-first among the 7 accepted
  candidates (8 rows below / 8 above, balance 1.0) at minimum effective section intervention for that
  split — the incumbent pair survived re-validation rather than being inherited.
- **Flat-midpoint cross-aisle sections are rejected because they pond.** A dead-flat datum (0% cross,
  0% longitudinal) mid-hillside fails the drainage gate. The incumbent `midpoint_datum` (621.29,
  57.4 CY) is **OVERTURNED** on drainage and kept only as a superseded diagnostic
  (`analysis/cross_aisle_sweep/_superseded_midpoint_section.json`).
- **`accessible_fit` is the only accepted section strategy in the sweep.** Every flat-datum strategy
  was eliminated on drainage; `cascade` (raw ground, 0 CY) measures a 5.97% cross-slope — flush and dry
  but ~3× the 2% ADA limit, not wheelable. Only `accessible_fit` carries **2% cross-slope + 1%
  longitudinal fall** (wheels *and* drains) and prices the residual edge drop as transition ramps.
  The wired section: datum **622.01**, 2.0% cross / 1.0% long, drains + wheelable, edge steps 1.9/2.03 ft
  carried as `ramp_23ft`/`ramp_24ft`, **68.2 CY** (60 raster + 8.6 ramp surcharge).
- **A row-derived cross-aisle is accepted only when both plan provenance AND section performance pass.**
  Criterion 5 is now a **plan ∧ section** gate: the band must be a row-reclassification clear of retained
  treads (plan) *and* its surface must drain and wheel (section). The engine enforces it — feeding a
  ponding section sets the move `not_validated`, which hard-rejects the design at cost_proxy
  (`_control_flat_midpoint_ponds.json`: REJECTED on drainage).

**Provenance must match geometry (Generate / Validate / Narrate).** The seam-aisle story was a
*provenance* failure, not a geometry failure: the code **generated** the band by row reassignment
(`union(row9,row10).difference(retained)`), **validated** it with overlap/connectivity tools, then
**narrated** it as a seam discovery. Those are three different acts, and the lie was letting
validation scaffolding pose as the generator. The fix is epistemic, enforced in three places:

- **A new move type names the act:** `reclassify_row_band_to_circulation` (not `derive_*_from_seam`,
  not `trace_access_desire_line`). The verb says what happened — a role reassignment from seating to
  circulation. `make_cross_aisle_from_rows()` is the generator; the connector/nearest-row tests are
  validation helpers that may run *after* geometry exists, never its source.
- **Every move carries `provenance`** — `geometry_source`, `seam_derived`, `source_geometry`,
  `operation` — recording the operation that actually created it. The cross-aisle declares
  `geometry_source="row_reclassification"`, `seam_derived=False`.
- **The engine enforces it (hard rejection #7):** a circulation move inside the rake that does not
  declare `row_reclassification` provenance (or that leaves `seam_derived` truthy) is rejected.
  `scripts/test_cross_aisle_provenance.py` pins all of it: the emitted band equals
  `union(row9,row10).difference(retained)` to 0 sqft, the 169 displaced seats leave the count,
  overlap is 0, the provenance fields are correct, and a seam-laundered move is rejected by the engine.

**The invariant:** *a circulation band inside the seating rake is made FROM seating geometry (a role
reassignment) unless there is a stated reason it cannot be.* This generalizes the Scenario-B/D rule —
B claimed formal seating without purchasing the surface repair; the seam aisle claimed discovered
geometry when the move was reassignment. Both violate the same law: **a design move is not honest
unless its provenance matches its geometry — the agent must state what operation actually created the
design object.**

`validation_status` on every move is set from its **actual** check result. Data-gated
remainders: survey cross-slope, geotech soil suitability, swale hydrology sizing. The cross-aisle
CY is **no longer first-pass** — it is the swept `accessible_fit` section (2% cross / 1% long, CY
measured on the realized surface via lstsq plane fit, ramps priced). Ramp-B CY remains first-pass
(nearest-node grading) and can be reduced by grade refinement.
