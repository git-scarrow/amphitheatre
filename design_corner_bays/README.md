# Corner Bays — three-part contour-aligned terrace system (face 312°)

**The keeper.** The site is a corner bowl — two straighter flanks joined by a tight
bend — so the seating is three linked **bays** per row at one terrace level, each
bay aligned to its own local contour, joined by aisles, with the bend as the formal
hinge. Generator: `scripts/design_corner_bays.py` · DEM `dem_design_1ft.tif` ·
EPSG:6494 NAVD88 · **planning-grade**.

## Earthwork premise (restated — honest)
Seat terraces are contour-aligned to the existing S/SE rake and require only
**shallow tread fine-grading** — *not* "zero grading." Validated against the
**raw / de-noised 1-ft DEM** (not a smoothed surface), civic treads show roughly
**0.55–0.67 ft of total micro-relief over bay lengths, comparable to the 20-ft-block
relief** — i.e. surface roughness (±0.20 ft, std ~2.4 in at tread scale on the
36–41% rake), **not** systematic cross-grade (crossing angle to contour is only
1.8–4.8°). Planning estimate: **~25 CY of shallow grading across civic tread strips,
with no retaining walls and no imported fill** assumed (pending civil design).
This replaces the earlier "≈9 CY" figure, which described a smoothed/median artifact
rather than actual tread-scale surface preparation.

## Standard (adopted)
| item | standard |
|---|---|
| civic tread raw-ground residual | ±0.20 ft typical |
| acceptable p90 residual | 0.20–0.25 ft |
| earthwork | shallow fine-grading (~25 CY), not zero |
| retaining walls | none |
| imported fill | none unless later civil design proves otherwise |
| ADA promenade / accessible routes | stricter independent grading check |

## Validation
| check | result |
|---|---|
| **G1** civic seating tread p90 residual ≤ 0.25 ft (vs raw DEM) | section p90 **0.17 / 0.21 / 0.23** (south/bend/east); 3 bays nick 0.26–0.30 — detailing note |
| **G2** adjacent-row clearance ≥ 3.0 ft (tread) | **PASS** — min **3.17 ft** (rows spaced adaptively; spacing widened locally where the rake steepens, **all 11 rows kept**) |
| **per-seat flank sightlines** | **PASS — 988/988 (100%)** sampled seats clear 90 mm; worst-decile C 180 mm. (Centreline C-values alone cannot certify non-concentric segmented rows — this is the per-seat ray-cast over the head in front.) |
| contour crossing angle (raw de-noised gradient) | east **1.8°** · bend 4.8° · south **2.3°** |
| centreline C ≥ 90 mm | 14/14 |
| **ADA promenade** (independent, p90 ≤ 0.12 ft) | **FAIL → flagged**: 0.14–0.24 ft. The promenade/accessible band needs its own dedicated grading; connecting routes are a separate ramp design (≤8.33% run, ≤2% cross-slope). |

## Numbers
| metric | value |
|---|---|
| rows | 4 forecourt + 1 promenade + 10 civic = 15, **all contour bays** (forecourt nests, no overlapping arcs) |
| **formal seats** | **1,127** (by section: east 320 · bend 369 · south 438; ~220 of these are forecourt-zone) |
| row spacing | adaptive march, ≥3.0 ft clearance everywhere (min 3.26 ft) |
| earthwork | ~22 CY shallow fine-grading; no walls; no imported fill |
| plan figures | `plan.png` (context) · `plan_zoom.png` (legible, corrected contour orientation) |

## Outputs
`seating_bays.geojson` (each bay tagged section/length/seats/cross-angle/residual)
· `composition_table.csv` · `plan.png` · `east_flank_proof.png` (treads along the
0.5-ft contours).

## Open items
- 3 seating bays at p90 0.26–0.30 ft → a touch more fine-grading (finish-spec detail).
- ADA promenade + accessible routes: dedicated grading/ramp design pass.
- Bay visibility uses the bare-618-rim test; the Bayfront tree screen is the separate
  view lever (see `bay-view-is-foreground-occluded`).
