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
| **Scenario E** — D + aisles + ADA + drainage (489 CY total) | Cost-proxy **only** where ADA, drainage, aisle, and construction-envelope surfaces are real emitted geometry that has passed polygon-intersection validation | `SCENARIO_E_CIVIC.md`; `INEVITABILITY.md` §concept→cost-proxy |

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
