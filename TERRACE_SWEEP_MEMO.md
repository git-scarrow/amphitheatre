# Terrace Earthwork Sweep — Design Memo
**Date:** 2026-06-07

> ⚠️ **SUPERSEDED IN PART — see `SCENARIO_B_VALIDATION.md` (2026-06-07).** Spatial validation
> showed this memo's Scenario B framing lies by omission: the 0.5 ft clip lands **under seats**,
> not "at row ends"; "self-balancing, no import" is geometric only (+26 CY to restore the formal
> bowl); and the as-built clipped surface yields ~217 compliant formal seats, not all 24 rows.
> The bulk-CY numbers below remain valid; their interpretation as a finished, all-clear design does not.
>
> **Ruling (2026-06-07):** Scenario B is **rejected** as a formal seating baseline.
> Scenario D (B + selective tread restoration, +26 CY) is the **designed baseline** for formal
> terraced seating. See `docs/DESIGN_CANON.md` and `INEVITABILITY.md`.

## What we did

Ran a three-scenario earthwork sweep across all 24 seating rows using the
`design_extended_bays` geometry. Each row's centerline arc is buffered ±1.8 ft
to produce a 3.6 ft tread polygon. The `terrace_plane` operation sets a gently
draining planar surface (2% cross-slope, 0.5% longitudinal) anchored to the
DEM median or a fixed design elevation, then measures the cut and fill required
to achieve it.

**Scenario A — terrain-following baseline**
Each tread plane is anchored to the DEM median inside its polygon. This is the
true minimum-earthwork cost of sitting level treads on the natural slope. Net
result: 138 CY cut, 172 CY fill, +33 CY import.

**Scenario B — site-balanced (adopted primary)**
Same as A, but fill is clipped at 0.5 ft per tread where the terrain dips at
row ends. The excess fill demand at those low spots is simply not met — those
edges drain outward more steeply. Net result: 138 CY cut, 137 CY fill, −0.7 CY
(self-balancing). No truck import required.

**Scenario C — sightline-optimized**
Tread planes anchored to the design elevations from the composition table rather
than the DEM. Measures the earthwork premium of the sightline-tuned geometry.
Result is nearly identical to A (142/168/+27 CY), confirming that the
composition table elevations track the terrain closely.

## Where Scenario B fits in the design sequence

Scenario B was useful as a diagnostic: it showed the site can generate its own
fill if we accept clipped tread ends. Spatial validation (`SCENARIO_B_VALIDATION.md`)
then showed the clip lands under seats (395 of 512 clipped segments are mid-row),
dishing treads to 5–7% cross-slope and dropping Band-A formal seats from 1,452
to 217 as-built.

**The design of record is Scenario E (civic_bowl)**, which is Scenario D
(B + selective 26 CY restoration to recover the full formal bowl) plus a
row-9 cross-aisle, two switchback ADA ramps graded to 8.33%, and east/south
drainage swales. Scenario E totals 500.8 CY and is the first number discussable
as a project-cost proxy. See `SCENARIO_E_CIVIC.md`.

## What the arc clipping means

Rows 1–20 have three sections (east, bend, south) fitting within the street
envelope, covering ~76% of the theoretical full-fan arc. At row 21, both the
east section (clipped by Petoskey Street, x = 19,533,271) and the south section
(clipped by Mitchell Street, y = 750,594) exit the site. Rows 21–25 are
bend-only, representing ~25% of the theoretical arc. Their earthwork volumes
are proportionally smaller — this is correct, not a calculation artifact.

## Interpretation thresholds

The per-row interpretation is calibrated against the wall-trigger threshold
(3.0 ft delta), not the theoretical minimum:

- **excellent fit** — max delta ≤ 0.5 ft (terrain nearly matches design)
- **normal tread grading** — ≤ 1.0 ft (typical localized adjustment)
- **standard cut-and-fill** — ≤ 2.0 ft (deliberate earthwork, well below wall trigger)
- **review geometry** — > 2.0 ft (approaching wall trigger, needs attention)

No rows in the current geometry trigger "review geometry."

## Outputs

- `terrace_sweep.csv` — per-row, per-scenario cut/fill table
- `terrace_sweep.md` — formatted summary; Scenario B leads, A as baseline reference
- `scripts/terrace_sweep.py` — reproducible sweep script
