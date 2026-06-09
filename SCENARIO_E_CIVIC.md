# Scenario E — civic_bowl, drawn and validated on real geometry

_`scripts/scenarioE_civic.py`. The first family made to DRAW. Stage: **cost_proxy (inherited, refit open)**._

**Engine verdict: ACCEPTED — inevitable** (seating / ADA / drainage)  ·  acceptance criteria **10/10** (seating/ADA/drainage criteria only — see criterion 11 below)  ·  total earthwork **500.8 CY** (restored bowl + access + drainage).

> **Stage refit OPEN.** The inherited stage (`design_open_low`, axis 150°) carries a +25.6° audience-axis mismatch and a −22.5 ft lateral offset relative to the Scenario E validated seating. The east section (365 seats) sits outside the declared ±55° fan. This is the same pattern of inherited-assumption-carried-forward that Rules 6-8 eliminate for the seating surface. Stage acceptance requires explicit adoption of one resolution path (see `DESIGN_CANON Rule 9` and `analysis/stage_refit/STAGE_REFIT_SWEEP.md`). Best feasible candidate: `az150_lat-20` (+3° mismatch, −2.5 ft lateral, 37.8 CY delta, preserves 330° bay view). Until resolved, the earthwork total of 500.8 CY **excludes** stage refit.

## Earthwork (geometry-backed, per component)

| Component | Cut CY | Fill CY | Gross CY |
|---|---:|---:|---:|
| formal_restored_treads | 55.2 | 116.4 | 171.7 |
| cross_aisle | 8.8 | 50.8 | 59.6 |
| cross_aisle_transition_ramps | 0.0 | 0.0 | 8.6 |
| accessible_route_A_floor | 79.0 | 0.1 | 79.2 |
| accessible_route_B_mid_row9 | 2.1 | 124.0 | 126.0 |
| east_flank_swale | 36.8 | 0.0 | 36.8 |
| south_flank_swale | 37.6 | 0.0 | 37.6 |
| row_end_shoulders | 0.0 | 0.0 | 0.0 |
| **TOTAL** | 214.9 | 285.9 | **500.8** |

## Validation on the actual surface

- **Sightlines:** restored treads rows 1-18 — formal failures: **none** (min C 90 mm). Max fill on any tread 2.83 ft (no 0.5 ft clip).
- **ADA ramps:** the schematic straight alignments were 10.0% / 17.8% (FAIL); re-graded as 3/4-flight switchbacks they run at 8.33% with 9 landings (**PASS by design**; final cross-slope needs survey).
- **Drainage:** both swales fall toward the NE pour point (618.04): **True**.
- **Shoulders:** rows 21-25 → lawn/overlook, topsoil only.

## Scenario E acceptance criteria

| # | Criterion | Result | Pass |
|---|---|---|:--:|
| 1 | formal seats Band A on restored surface (1283 net, 1452 nominal - 169 cross-aisle) | PASS; aisle clear of treads (0 sqft overlap) | ✅ |
| 2 | ADA-required surfaces have real geometry | PASS (ramps A+B + landings emitted) | ✅ |
| 3 | accessible routes pass running-slope gate | PASS @ 8.33% by switchback design | ✅ |
| 4 | landings flat, sized, at meaningful intervals | PASS (9 landings + cross-aisle) | ✅ |
| 5 | cross-aisle = causeway over rows 9|10 AND section drains+wheels (plan ∧ section gate; nearest-row 9-10, var 1) | PASS (rows [9, 10], 169 displaced, 0 sqft overlap; accessible_fit 2.0% cross / 1.0% long, drains=True, wheelable=True) | ✅ |
| 6 | every swale has direction + receiving area + conflict check | PASS (falls to cell, 0 tread conflicts) | ✅ |
| 7 | every row fragment classified | PASS (treads/shoulders/aisles/swales all tagged) | ✅ |
| 8 | cost-bearing moves geometry-backed CY | PASS (per-component CY; total 500.8 CY) | ✅ |
| 9 | open items data-gated or resolved | DATA-GATED (cross-slope survey, soil suitability/geotech, swale hydrology sizing) | ✅ |
| 10 | design can still reject its cheapest false version | PASS (control test holds) | ✅ |
| 11 | stage geometry matches emitted seating fan (Rule 9) | **OPEN** — inherited az150 stage: +25.6° mismatch, −22.5 ft lateral offset, east section outside ±55° fan. Resolution path not yet declared. | ⚠️ |

## Engine verdict (cost_proxy)

`ACCEPTED — inevitable` — ledgers performance=✅ affordance=✅ role=✅ justification=✅, done 10/10.


## Reading

civic_bowl is now drawn: restored formal treads (the Scenario D surface), a row-9 cross-aisle for wheelchair dispersion and a view pause, two switchback ramps re-graded from the too-steep schematic alignments to a compliant 8.33% with landings, swales that fall to the bay-bound pour point, and clipped tips dissolved to lawn. The same validation engine re-banded everything on the real surface. What remains is genuinely external (survey cross-slope, geotech soil suitability, swale hydrology sizing) — data-gated, not design hand-waving. This is the first civic_bowl number that can be discussed as a project-cost proxy.

Geometry: `analysis/scenarioE_civic/geometry.geojson` · earthwork: `earthwork.csv` · scorecard: `acceptance_scorecard.csv`.
