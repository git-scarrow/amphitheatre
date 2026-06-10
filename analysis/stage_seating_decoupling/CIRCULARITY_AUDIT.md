# Circularity audit — stage placement vs seating geometry

## The loop (evidence)

1. **The focal point descends from the stage lineage.** `design_open_low.py`
   line 21: `CX,CY=19533067.7,750799.2`; the arc centre F = base + 15 ft @ az
   150 and the stage front at F + 50 ft were fixed together (stage4 lineage).
2. **The seating march is anchored to that same point.**
   `design_extended_bays.py` lines 33-46: identical `CX,CY`; the forecourt
   starts at radius **85 ft from F** (`FORE_R=[85.0,…]`), the section windows
   are azimuths **about F** (`AZ_E_CAP=AX_AZ-47 … AZ_S_CAP=AX_AZ+65`), and the
   facing `AX_AZ=132` was chosen relative to it. The bay SHAPES are contour
   (terrain) but their radial start and angular extent are F-inherited.
3. **The harness hard-codes the anchor.** `harness_config.yaml`:
   `center_x/center_y` (same point), `stage_r_ft: 50.0` — every engine
   (sightlines, earthwork, Scenario E) evaluates about it.
4. **The frame study closed the loop.** `normalize_sections.py` derived the
   audience centroid FROM that seating and proposed re-fitting the stage to
   it — the stage would have been justified by geometry it helped create.

## What is terrain-forced vs inherited

| element | status |
|---|---|
| the flat pan (performance-front zone, 16035 sf) | terrain |
| the S/SE seating wall (slope 12-45%, faces the pan) | terrain |
| contour shapes of each bay family | terrain |
| focal point F (x,y), inner radius 85 ft, az windows, facing 312 | **inherited choices** |
| stage footprint at F+50 @ az150 | **inherited** |

## The break — three independent products (this study)

1. `audience_envelopes.geojson` — 4 terrain-first envelopes by
   facing class (+0 rejected components recorded). The
   primary NW-facing envelope re-derives the current bowl wall **without
   any stage assumption**: it contains
   65.9% of the validated seating and
   carries ~1283 seats.
2. `stage_opportunity_zones.geojson` — 3 floor zones (+
   1 rejected, incl. the NW pan sector occupied by the
   treatment cell), derived from floor feasibility, cell clearance, loading,
   backdrop allowance, storage — **not** from the seating rows.
3. `pairwise_stage_audience_scores.csv` — 12 pairings ranked;
   Pareto front ['A_NWN+S_SE', 'A_NWN+S_NE'].

## Verdict

**Winner: A_NWN+S_SW** (weighted 0.841).
The winning stage zone TIES WITH (within proxy noise) the inherited stage centroid —
the top pairs are separated by ≤0.02 weighted score — the independent analysis selects the southern pan-toe ZONE BAND, and the inherited stage centroid sits inside one of its co-leading zones. The general location therefore survives as a *re-derivation* (floor feasibility + cell clearance + backdrop allowance + loading), while the exact footprint/axis within the band remains open (Rule 9) and must come from the pairwise frame + obstruction tracer, not inheritance.

A_NWN+S_SW beats A_NWN+S_SE (viable) on weighted score: 0.841 vs 0.838; capacity: 1283 vs 1283; axis skew deg: 19.0 vs 23.7; backdrop allowance ft: 15.7 vs 17.1; pad CY: 236.2 vs 238.8; loading ft: 170.4 vs 193.8; stage→toe ft: 12.3 vs 11.2

Residual circularity, declared: the seat-density calibration
(0.0689 seats/sf) and family-overlap reporting reference the
validated bowl for CALIBRATION/LABELS only — they do not constrain where
envelopes or zones may exist.
