# MEMO — Stage *shape* is the blocker to facing the audience (Rule 9 Path 1)

**To:** next agent picking up stage adoption
**Date:** 2026-07-19
**Status:** open question, owner-directed. Nothing adopted. az-150 / P_opt remains the record.

## The task

Determine whether a **reshaped** stage can face the audience at **az 124.4°** while holding
row-1 clearance **≥ 12.0 ft** — or prove it cannot, in which case az-150 + wide-fan stands.

**Placement is not the problem. Shape is.** Treat the apron and shoulders as the design
variables; the core placement at 124.4° already clears.

## Evidence (measured, not assumed)

The 124.4° rotation was applied on gentoo and run through the gate suite on 2026-07-19.
`stage_current_geometry_gate` rejected it:

```
governed edge = occupied deck (core + apron)
  east   core 20.0   deck 40.3   full 7.2   shoulder_gap 7.22
  bend   core 37.9   deck 38.4   full 37.9
  south  core 23.5   deck  7.2   full 7.2   shoulder_gap 19.2
GOVERNED (deck) min = 7.24 ft -> FAIL (>= 12.0)
```

Read that carefully — it is the whole memo:

- **The core clears at 124.4°**: 20.0 / 37.9 / 23.5 ft, all ≥ 12.
- **The periphery does not**: east **shoulder** 7.22 ft, south **deck/apron** 7.2 ft.
- At the adopted az-150 P_opt, gaps are 12.0 / 32.7 / 21.9 — all pass.

So rotating the *existing* footprint fails only because the **five_facet_apron + shoulders**
swing into row 1. A different apron/shoulder footprint may clear at the same azimuth.
The rotation was fully reverted; gentoo is clean on `main`.

## The design question

At az 124.4°, can the **occupied deck** (core + apron + shoulders) be shaped to keep ≥ 12.0 ft
to row 1 on every edge? Candidate moves, cheapest first:

1. **Trim / re-facet the apron** on the east and south edges only (bend has 38 ft to spare).
2. **Asymmetric apron** — keep depth toward the bend, shallow it toward east/south.
3. **Shrink or re-place the shoulders** — east shoulder is the binding edge at 7.22 ft.
4. **Translate the deck back** along the 124.4° axis to buy clearance (interacts with
   sightlines and the focal point — re-run C-values).
5. **Swap typology** from the already-scored shortlist (see prior art) if T1_deck_only
   cannot be made to fit.

## Constraints that must hold

**Typology price (bay-band v2, adopted 2026-07-21 — `BAY_BAND_V2_DECISION_ADDENDUM.md` DP3):**
any shape+typology proposal that includes the **T2 roof** carries its repriced option cost —
**38.5% of the restored (S1) bay view** (the old 8.6% was terrain-only and is superseded) — and
must spec the roof top **≤ 634.0 ft NAVD88** (the S1 neighbor-gate pass margin is ~0.9 ft,
inside construction tolerance). The typology decision must weigh the identity tension
explicitly: the roof takes the largest single bite of exactly the asset a civic de-treeing
effort would restore.

- **Row-1 clearance ≥ 12.0 ft** on the *governed* measure (occupied deck incl. shoulders).
  This is the gate that rejected 124.4°.
- **Rule 9 fan declaration must match the emitted seating.** path-4 wide-fan
  (`formal_fan_half_deg 75`) is load-bearing under az-150; re-check whether 124.4° changes
  that — the east section sits outside ±55° under az-150.
- **Sightlines** C ≥ 90 mm bar, seat counts, ADA clearance, earthwork CY.
- **Bay view:** at 124.4° the audience faces ~304.4°, i.e. **−25.6° off the bay (330°)**.
  Path 1 requires that deviation be explicitly acknowledged and justified.

## Where this runs

**gentoo** (`sam@gentoo`, `~/projects/amphitheatre`) — has `.venv` with shapely/numpy/rasterio
and the DEM rasters. **macbook-m4 cannot validate** (no DEM, no geo deps); do not attempt
adoption there.

## Prior art — start here, do not redo

| Artifact | What it gives you |
|---|---|
| `analysis/in_situ_normalization/STAGE_SHAPE_STUDY.md` | the existing shape study |
| `analysis/in_situ_normalization/stage_typology_scores.json` | T1–T7 scored; **T1_deck_only** is adopted |
| `scripts/stage_shape_study.py` | the shape-study harness |
| `analysis/stage_adoption/RULE9_DECISION_RECORD.md` | the adopted az-150 P_opt bundle + why |
| `analysis/stage_adoption/RULE9_PATH1_AUDIENCE_AXIS_DISPATCH.md` | the 124.4° rotation script + verification checksums |
| `analysis/bay_view_obstruction/DISPATCH_EFFECTIVE_SILHOUETTE_AND_NEIGHBOR_GATE.md` | bay-band v2 work order (owner-directed 2026-07-21): effective-silhouette definition, canopy layer, far-shore band top, neighbor hard gate — re-verdicts the roof/element menu that bounds any shape+typology proposal |

## Files a shape change would touch

- `analysis/in_situ_normalization/adopted_stage_footprint.geojson` — `adopted_stage_deck`, `axis_az`
- `design_open_low/stage_floor.geojson` — `stage`, `stage_shoulder_left/right`,
  `event_floor_forecourt`, `focal_point_stage_front`

## ⚠ Two traps

1. **The gates print `FAIL` but exit `0`.** `rc` is not a usable signal — parse the verdict
   text. A run that "succeeds" may have rejected your geometry.
2. **This reverses a recorded owner decision** (az-150 P_opt, carried_provisional 2026-07-02,
   user instruction). Nothing here is adopted by finding a shape that fits — it needs owner
   sign-off and `RULE9_DECISION_RECORD.md` updated. Do not silently overwrite the record.

## Definition of done

Either:
- **(a)** a stage shape at az 124.4° that passes the **full** gate suite → present it as a
  proposal with the bay-view −25.6° deviation declared, for owner sign-off; or
- **(b)** a documented proof that no acceptable shape clears ≥ 12.0 ft at 124.4° → az-150 +
  path-4 wide-fan stands, and Rule 9 Path 1 is closed as infeasible.

Either outcome is a real result. (b) is not a failure.
