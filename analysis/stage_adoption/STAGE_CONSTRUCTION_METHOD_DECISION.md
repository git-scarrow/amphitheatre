# Stage construction-method decision — Method B adopted (deck over compacted base)

**Status:** ADOPTED 2026-07-03 (user selection). Closes the construction-method
half of the Rule 9 "EarthworkEngine CY" red-team item. Ratifies the existing canon
material spec; formally rules out the solid earthen pad.

## Decision

**Adopt Method B — hybrid deck/base:** a low hardwood/composite deck over a
compacted base pan (the 2,380 sf performance core) with filled apron/shoulder edges
brought to event-floor grade. This is the direct reading of the canon material spec
already on file — `material_zones.geojson` `hardscape_stage`: *"low hardwood/
composite deck over compacted base at event-floor grade."*

## Options considered (established numbers, `stage_pad_redteam.md` §5)

| option | earthwork | note |
|---|--:|---|
| A — solid earthen pad → 612.5 | 330.2 CY | **rejected** — contradicts the canon deck spec; datum-inflated (63 CY is only 612.0→612.5); double-counts ~292 sf of drainage swale already inside the 500.8 balance. Retained ONLY as the pre-trim upper-bound scenario, never as an additive quantity. |
| **B — deck over compacted base + filled edges** | **~98 CY** | **ADOPTED** — matches canon material spec; conventional/most-buildable; lowest total cost; grounds the stage in the naturalistic bowl. |
| C — freestanding low deck on footings/piers | ~0 CY | documented fallback — best flood behavior (water passes under, storage preserved) but higher structural cost and the stage floats ~1 ft over grade. Adopt only if flood-storage displacement becomes a regulatory constraint. |

## Rationale

- **Governing surfaces unchanged:** sightline focus, the ADA performer route, and
  stage usability fix only the **deck top at 612.5**. Nothing requires solid earth
  at 612.5 — a deck over a lower base delivers the same surface.
- **Flood constraint (binding):** keep the compacted base **above 612.0** (spillway
  crest / min flood-safe base top; 100-yr WSEL 611.3, 500-yr 611.8). Method B's base
  pan and filled edges must top out ≥612.0 with the deck structure band (1.0 ft)
  carrying grade to 612.5.
- **Cost / constructability:** ~98 CY of compacted fill is inexpensive vs a full
  3,386 sf elevated structure on piers (Option C); compacted-base + deck is
  conventional civil work.
- **Character:** a low grounded stage reads as part of the landscape ("open-air, not
  a room" civic bowl), where a floating deck reads as an object.

## What this decision does NOT yet settle (Phase-B EarthworkEngine)

The **~98 CY is a planning-tier estimate**, not a geometry-backed quantity, and is
**not yet additive to the 500.8 CY project total.** Before any stage CY enters
project totals, Phase-B EarthworkEngine must:
1. compute the base-fill volume from the adopted footprint with the base top pinned
   at the flood-safe datum (≥612.0), not 612.5;
2. **net out the ~292 sf drainage-swale overlap** already carried in the 500.8
   balance (avoid the double-count the red-team flagged);
3. emit the result as a geometry-backed `earthwork.csv` component.

Until then: stage accounting stays "structure, not grading" (0 CY in `earthwork.csv`);
Method B is the adopted **method**; ~98 CY is its **estimate**; 330.2 CY remains the
**upper-bound scenario only**.
