# Corner Bowl — one master curve, family by offset (face 312°)

The keeper geometry. The SE seating wall is a basin **corner**, not a cup, so rows
are **not arcs**. Per the directive: **author the plan logic once** as a master
three-regime terrace curve (flank · bend · flank, fair/C2), then **derive the whole
row family by normal-offset** from it — not by fitting each row.

Generator: `scripts/design_corner_bowl.py` · DEM `dem_design_1ft.tif` (3-ft
pre-smooth) · EPSG:6494 NAVD88 · **planning-grade**.

## Why arcs were wrong (measured)
Curvature along the seating-sector contour, consistent at 618/621/624 ft:
**S/SW flank R≈250–300 ft → middle bend R≈50–70 ft → E/NE flank R≈240–280 ft** —
a 5:1 ratio. One radius cannot be both; that mismatch drove every earlier
non-circularity / off-grade / centroid / trim fight.

## Method
1. **Master curve** — a single fair (C2) smoothing spline through the datum contour
   (615 ft) in the seating sector. Measured three-regime: **flank R~561 → bend R~41
   → flank R~384 ft.** One authored curve, no per-row wiggle.
   *(Swap-in point: an explicit line–clothoid–arc–clothoid–line if you want
   parametric control of flank bearing / bend radius / G2 spirals.)*
2. **Family by offset** — every row = master + k·TREAD along its unit normal.
   Outward/up-slope offsets (convex) fan safely; the 4 inner offsets are the
   forecourt, bounded by the bend radius (≈ the orchestra opening). All 17 rows
   share the master's three-part character + parallel spacing **by construction**.
3. **One asymmetric trim window** on the master (east/hook capped at 70 ft, west
   extended to 96 ft to wrap), applied to every row → coherent family. Tiers:
   **core** (window) / **bay** (reclaimed inner flank) / **lawn** (trimmed ends).

## Result
| metric | value |
|---|---|
| rows | 4 forecourt + promenade + 12 civic = **17** (all offsets of one master) |
| **family coherence** | **min adjacent spacing 2.99 ft** (= tread; never crosses) |
| formal seats | core 1,315 + bays 256 = **1,571** generous (overshoots target — dialable) |
| lawn (informal) | ~356 |
| sightlines ≥90 mm | **16/16** |
| tread leveling earthwork | **172 CY** (vs 140 on-contour, 680/889 arcs) |
| bay-seeing rows | 5–17 (forecourt 1–4 = stage zone) |
| leveling residual | 1.44 ft mean; climbs to ~2.0 ft on the top rows |

## Honest tradeoffs / dials
- **Seats overshoot (1,571 > 1,050–1,200 target).** Easy to dial down: shorten the
  core window (`EAST_CORE`/`WEST_CORE`) or drop 2–3 upper rows.
- **Outer-row leveling residual ~2.0 ft.** Constant-plan offsets drift off the true
  contour as they fan outward, so the top rows aren't perfectly level (172 CY total,
  still small). Fixable by snapping each row's elevation to its contour (a *local*
  end-condition adjust, not a re-fit) if you want it tighter.
- **Flanks came out very straight** (master R~400–560 vs measured ~270) — the
  smoothing is a touch heavy; lower `SMOOTH_K` to track the gentle flank curve.
- C-values are centreline; **per-seat flank sightlines** still want a pass. Bay
  visibility is bare-618-rim only (Bayfront tree screen is the separate view lever).

## Outputs
`master_curve.geojson` (the one authored curve) · `seating_rows.geojson` (core
tier) · `seating_bays.geojson` · `side_banks.geojson` · `composition_table.csv` ·
`plan.png` (master dotted, family offset from it).
