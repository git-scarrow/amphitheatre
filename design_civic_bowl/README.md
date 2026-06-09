# Designed Civic Bowl — face 312° (contour-INFORMED, regularized)

Supersedes the literal-contour baseline (`design_civic_contour/`). Same premises —
**face 312°, 4-row stage forecourt, terrain-fit terraces** — but the civic rows are
now **regularized crescents** fit to the basin contours, not raw contour traces.
The word is *regularized, not optimized*: a low-order smooth radius function
`r(θ)` about the orchestra centre is least-squares fit to each natural contour,
**after** the sharp-turning flank ("hook") is excluded, so DEM wiggle cannot
become architecture and the rows read as one civic family.

Generator: `scripts/design_civic_bowl.py` · DEM `dem/dem_design_1ft.tif`
(3-ft pre-smooth) · CRS EPSG:6494 · NAVD88 · **planning-grade**.

## Form
- **Aim 312°** (≈5° off the measured fall line 307°).
- **Forecourt (rows 1–4):** regular arcs ±40° on grade — the intimate stage zone, no bay obligation.
- **Hinge promenade (row 5):** a level contour walk / accessible band + social overlook that absorbs the geometry change between performance bowl and bay terraces.
- **Civic terrace families** (each a smooth crescent, hook shed to lawn):
  - **Lower (6–8)** — stage-aware, gently opening
  - **Middle (9–12)** — the strongest crescent, best stage/land balance
  - **Upper (13–16)** — broad belvedere along the rim
- The **trimmed flanks** (~35% of each fan, incl. the east hook) become **side-bank lawn / planting** (`side_banks.geojson`), not forced seating.

## Composition tests — all pass
| test | target | result |
|---|---|---|
| curvature noise (CV) | ~0 (no wiggle) | **0.00–0.04** ✓ |
| min radius of curvature | no tight hooks (>40 ft) | **95–171 ft** ✓ |
| seat-normal splay (90th pct) | ≤28° (else per-seat toe-in) | **18–27°** ✓ |
| grade residual (90th pct) | ±0.5–1.0 ft | **0.8–1.4 ft** (mid/upper ride ~1.1) ◑ |
| non-circularity | clean crescent | **~11 ft** (was ~20 raw) ✓ |
| sightline C (centreline) | ≥90 mm | **15/15**, +0 CY top-up ✓ |

## Numbers
| metric | value |
|---|---|
| rows | 4 forecourt + 1 promenade + 11 civic = **16** |
| rise | 611.0 → 627.0 = **16.0 ft** |
| seats (fixed) | **860 generous / 1,050 compact** + lawn/side-bank informal |
| **tread earthwork** | **141 CY** (72 cut + 69 fill) |
| vs literal contour / arc@315 / arc@330 | 175 / 680 / 889 CY |
| bay-seeing rows | **5–16** (forecourt 1–4 = stage zone) |

**Legibility was nearly free:** authoring the crescents and shedding the hooks to
lawn costs ~141 CY — *less* than the literal contour (the worst flanks are gone),
and still ~5–6× under the arc schemes.

## The real tradeoff: seat count
Fixed seats drop to **~860 generous** (v2 arc target was ~1,470). The cost is the
~35% flank trim + clean crescents over a narrower effective fan. **Recoverable** by:
retaining more flank (raise `DRDT_MAX`), adding upper rows, widening the forecourt,
or counting the lawn side-banks as informal capacity.

## Honest gaps (unchanged)
- C-values are the **centreline** check; non-concentric rows need a **per-seat flank
  sightline pass** before this is more than planning-grade.
- "Sees bay" = clears the bare 618 rim; the **Bayfront tree screen** still governs the
  actual view (separate vegetation lever — see `bay-view-is-foreground-occluded`).

## Outputs
`seating_rows.geojson` (rows, tagged family/kind/tests) · `side_banks.geojson`
(trimmed lawn) · `stage_focus.geojson` · `composition_table.csv` · `plan.png`.

## Knobs
1. **Flank retention** `DRDT_MAX` 0.7 → higher keeps more crescent (more seats, looser ends).
2. **Families** fan widths / row counts per family.
3. **Aim** 312 ↔ 315/320.
4. **Promenade** as circulation-only (now) ↔ accessible seating band.
