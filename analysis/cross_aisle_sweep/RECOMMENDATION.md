# Cross-aisle section sweep — adjacent row pair × section strategy

`scripts/sweep_cross_aisle.py`. Replaces the assumed rows 9|10 + dead-flat midpoint with a swept, re-validated section decision.

Swept **7 row pairs × 5 strategies = 35 candidates**. Each band is built by the same row reclassification that makes the seats (`union(row_i,row_i+1).difference(retained)`), then re-validated on the actual surface.

## The section tension (why this is a real decision)

The row-centerline rake across a mid-bowl 2-row span is ~31.6%. But the band footprint is not the centerlines — it is the gap left between the buffered retained treads (`.difference(retained)`), and the least-squares plane fit on that actual surface measures a gentler **5.97% cross-slope** (`cascade`, raw ground, 0.0 CY, edges normal_riser/normal_riser). That is still ~3.0x the ADA limit of <= 2.0%, so the band cannot be left as-is. Yet flattening it to wheelable grade (0% both ways) makes it **pond** mid-hillside. So no single move satisfies wheelability AND drainage AND flush edges at once: `cascade` is flush + dry but too steep to wheel; the flat datums wheel but pond; only `accessible_fit` carries 2% cross + 1% longitudinal fall (wheels and drains) and buys the residual edge drop as priced ramps. That is the real decision.

## Recommended

**rows 9-10 · accessible_fit — net 1283 seats, datum 622.01, x-slope 2.0%, steps 1.9/2.03 ft (ramp_23ft/ramp_24ft), drains, section 68.2 CY**

Among 7 accepted candidates (all `accessible_fit` — every flat-datum strategy was eliminated on the drainage gate). The section strategy is settled by the gates; the row pair is then ranked balance-first (a cross-aisle's job is balanced dispersion + a centred view pause), then minimum effective intervention (section CY).

Min-earthwork alternative (if a lopsided split is acceptable): rows 7-8 · accessible_fit — net 1295 seats, datum 619.32, x-slope 2.0%, steps 1.87/1.87 ft (ramp_22ft/ramp_22ft), drains, section 58.4 CY.

## Incumbent (current Scenario E: rows 9|10, midpoint_datum)

- rows 9-10 · midpoint_datum — net 1283 seats, datum 621.29, x-slope 0.0%, steps 1.98/2.11 ft (ramp_24ft/ramp_25ft), PONDS, section 57.4 CY
- accepted: **False** (fails: drainage(ponds))
- verdict vs recommended: **OVERTURNED**

## Accepted candidates (ranked balance-first, then section CY)

| Rank | Pair | Strategy | Net seats | Below/Above | Balance | Datum | x-slope% | Steps (in/out) ft | Drains | Section CY |
|--:|--|--|--:|--|--:|--:|--:|--:|:--:|--:|
| 1 | 9-10 | accessible_fit | 1283 | 8/8 | 1.0 | 622.01 | 2.0 | 1.9/2.03 | yes | 68.2 |
| 2 | 8-9 | accessible_fit | 1290 | 7/9 | 0.78 | 620.65 | 2.0 | 1.87/1.94 | yes | 61.7 |
| 3 | 10-11 | accessible_fit | 1277 | 9/7 | 0.78 | 623.43 | 2.0 | 2.0/2.02 | yes | 72.4 |
| 4 | 7-8 | accessible_fit | 1295 | 6/10 | 0.6 | 619.32 | 2.0 | 1.87/1.87 | yes | 58.4 |
| 5 | 11-12 | accessible_fit | 1273 | 10/6 | 0.6 | 624.86 | 2.0 | 2.04/2.13 | yes | 75.2 |
| 6 | 12-13 | accessible_fit | 1266 | 11/5 | 0.45 | 626.34 | 2.0 | 2.06/2.18 | yes | 84.3 |
| 7 | 13-14 | accessible_fit | 1258 | 12/4 | 0.33 | 627.87 | 2.0 | 2.19/2.21 | yes | 87.7 |

Full grid: `analysis/cross_aisle_sweep/sweep_table.csv` (7 accepted, 28 rejected). Per-candidate proof: `proof_table.csv`; raw: `sweep.json`.

