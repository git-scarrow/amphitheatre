# Civic Contour Bowl — baseline (face 312°)

Baseline implementation of the **revised seating principle** (2026-06-05): aim the
fan at the natural fall line, split a tight stage forecourt from a terrain-true
civic bowl, and place the civic rows on **natural contours** instead of forced
circular arcs.

Generator: `scripts/design_civic_contour.py` · DEM `dem/dem_design_1ft.tif` ·
CRS EPSG:6494 · NAVD88 (Geoid12A) intl ft · **planning-grade**.

## Defaults used
- **Aim:** FACE_AZ = **312°** (AX_AZ 132°), within ~5° of the measured fall line (307°).
- **Forecourt:** rows 1–4, circular arcs on grade, **±40° fan** (tight to stage), R 85–94.
- **Civic terraces:** rows 5–20, **contour rows** (level by construction), **±55° fan**,
  marched outward at a fixed **3 ft tread**; the riser is whatever the terrain gives
  (0.6–1.5 ft).

## Result
| metric | value |
|---|---|
| rows | 4 forecourt + 16 civic = **20** |
| rise | 610.8 → 629.1 = **18.3 ft** |
| seats | **1,855 generous (22") / 2,263 compact (18")** |
| **tread earthwork** | **~175 CY balanced bench** (88 cut + 87 fill, on-site) |
| vs. arc scheme tread-leveling | **680 CY (arc@315) / 889 CY (arc@330)** |
| lateral leveling residual | **1.44 ft mean** (arc rows carried 7.7–8.7 ft) |
| sightlines (pure contour on grade) | **16/20 ≥ 90 mm** |
| sightlines (enforced) | **20/20** for **+16 CY** (4 rows lifted ≤0.3 ft on flat stretches) |
| bay-seeing rows (eye > bare 618 rim) | rows **6–20**; forecourt 1–4 + civic 5 are the stage zone |

**Headline:** contouring the civic rows removes the ~680–889 CY cross-arc leveling
penalty, replacing it with a ~175 CY balanced bench cut — a **~4–5× reduction in
tread earthwork** — while keeping every row level and holding 90 mm sightlines for
~16 CY of touch-up.

## The tradeoff (the cost of contouring)
- **Non-circularity 19–24 ft.** Across the 110° civic fan each contour row's radius
  varies by ~20 ft — the rows bow with the hillside rather than reading as crisp
  arcs. Narrowing the civic fan to ±40° roughly halves this; it is the main knob.
- **Flank sightlines unverified.** C-values here are the **centreline** check. Because
  contour rows are non-concentric, flank seats sit at different radii and need a
  **per-seat** sightline pass before this is more than planning-grade.
- **Bay visibility is bare-earth only.** "Sees bay" = eye clears the 618 ft bare rim.
  The Bayfront Park tree screen (see `bay-view-is-foreground-occluded` memory) still
  governs the actual view and is a separate vegetation-management lever.

## Outputs
- `seating_rows.geojson` — forecourt arcs + civic contour rows (tagged zone, elev, C, bay, earthwork).
- `stage_focus.geojson` — stage front / sightline focus (612.5 ft) + face azimuth.
- `sightline_table.csv` — full per-row table incl. riser, non-circularity, bench & top-up fill.
- `plan.png` — plan over the DEM (red=forecourt, blue=bay-civic, gray=no-bay).

## Knobs to react to
1. **Civic fan width** ±55° (current) → ±40° to cut non-circularity ~½ (fewer flank seats).
2. **Aim** 312° (terrain-true) ↔ 320° (toward open water; +~60 CY).
3. **Forecourt depth** 4 rows (current) ↔ 5.
4. **Tread/riser** fixed 3 ft tread (current) ↔ fixed riser (constant sightline, variable legroom).
