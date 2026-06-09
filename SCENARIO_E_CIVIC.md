# Scenario E — civic_bowl, drawn and validated on real geometry

_`scripts/scenarioE_civic.py`. The first family made to DRAW. Stage: **cost_proxy**._

**Engine verdict: ACCEPTED — inevitable**  ·  acceptance criteria **10/10**  ·  total earthwork **489.2 CY** (restored bowl + access + drainage).

## Earthwork (geometry-backed, per component)

| Component | Cut CY | Fill CY | Gross CY |
|---|---:|---:|---:|
| formal_restored_treads | 55.2 | 116.4 | 171.7 |
| cross_aisle | 25.0 | 23.0 | 48.1 |
| accessible_route_A_floor | 79.0 | 0.1 | 79.2 |
| accessible_route_B_mid_row9 | 2.1 | 124.0 | 126.0 |
| east_flank_swale | 36.8 | 0.0 | 36.8 |
| south_flank_swale | 37.6 | 0.0 | 37.6 |
| row_end_shoulders | 0.0 | 0.0 | 0.0 |
| **TOTAL** | 231.1 | 258.1 | **489.2** |

## Validation on the actual surface

- **Sightlines:** restored treads rows 1-18 — formal failures: **none** (min C 90 mm). Max fill on any tread 1.89 ft (no 0.5 ft clip).
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
| 5 | cross-aisle = causeway over rows 9|10 (the band IS the two rows), ≤1-row drift (nearest-row 9-10, var 1) | PASS (causeway over rows [9, 10], 169 seats displaced, 0 sqft retained-overlap) | ✅ |
| 6 | every swale has direction + receiving area + conflict check | PASS (falls to cell, 0 tread conflicts) | ✅ |
| 7 | every row fragment classified | PASS (treads/shoulders/aisles/swales all tagged) | ✅ |
| 8 | cost-bearing moves geometry-backed CY | PASS (per-component CY; total 489.2 CY) | ✅ |
| 9 | open items data-gated or resolved | DATA-GATED (cross-slope survey, soil suitability/geotech, swale hydrology sizing) | ✅ |
| 10 | design can still reject its cheapest false version | PASS (control test holds) | ✅ |

## Engine verdict (cost_proxy)

`ACCEPTED — inevitable` — ledgers performance=✅ affordance=✅ role=✅ justification=✅, done 10/10.


## Reading

civic_bowl is now drawn: restored formal treads (the Scenario D surface), a row-9 cross-aisle for wheelchair dispersion and a view pause, two switchback ramps re-graded from the too-steep schematic alignments to a compliant 8.33% with landings, swales that fall to the bay-bound pour point, and clipped tips dissolved to lawn. The same validation engine re-banded everything on the real surface. What remains is genuinely external (survey cross-slope, geotech soil suitability, swale hydrology sizing) — data-gated, not design hand-waving. This is the first civic_bowl number that can be discussed as a project-cost proxy.

Geometry: `analysis/scenarioE_civic/geometry.geojson` · earthwork: `earthwork.csv` · scorecard: `acceptance_scorecard.csv`.
