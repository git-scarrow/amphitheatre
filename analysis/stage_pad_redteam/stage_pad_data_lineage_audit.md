# Stage-pad ~330 CY — DATA-LINEAGE AUDIT (source terrain → reported CY)

**Advisory. Changes no canon.** Reproduce with `python scripts/stage_pad_lineage_audit.py`.
Deliverables in this folder: `terrain_source_report.txt`, `stage_pad_volume_breakdown.csv`,
`adopted_stage_footprint_split.geojson`, `stage_pad_overlap_audit.csv`, plus the prior red-team
narrative `stage_pad_redteam.md`.

> **Gate language (carry verbatim until resolved):** *Existing terrain data likely supports a
> stage/forecourt low-pan warning, but the ~330 CY figure is not accepted as required imported
> fill until source terrain, footprint scope, target datum, construction assumption, and overlap
> accounting pass audit.*

**Where each of the five gates now stands after this audit:**

| Gate | Result |
|---|---|
| Source terrain | **PASS — verified** (correct existing-ground surface, same as seating/drainage/earthwork) |
| Footprint scope | **PASS** (70×34 core + apron + 2 shoulders = 3,386 sf; no internal double-count) |
| Arithmetic closure | **PASS** (330.2 CY = 3,386 sf × 2.633 ft ÷ 27; the "2,699 sf" prose was the error) |
| Target datum | **CONDITIONAL** (330 is the solid-earth-to-612.5 scenario; ~63 CY is only 612.0→612.5) |
| Construction assumption | **SELECTED 2026-07-03 → Method B (deck over compacted base)** (`STAGE_CONSTRUCTION_METHOD_DECISION.md`); ~98 CY planning estimate; solid pad (A) rejected. Precise geometry-backed CY is Phase-B EarthworkEngine (base ≥612.0, net of drainage overlap) — until then accounting treats stage as structure, not grading (0 CY) |
| Overlap accounting | **FAIL as stated** (292 sf collides with swale CUTS already in the 500.8) |

**Net:** the terrain data was *used correctly for what it computes* — a fill-to-plane volume of
existing ground under the adopted footprint. **The finding stands: the full 3,386 sf
stage/apron/shoulder union filled to 612.5 = ~330.2 CY equivalent fill.** That figure is **valid as
the solid-pad-to-612.5 upper-bound scenario** — a legitimate construction scenario, not a strawman —
but it is **not the adopted baseline unless a solid earthen pad is explicitly selected**. It is **not
proven to be required import**, and it is **not cleanly additive** to the Scenario E 500.8 CY total.
Required import remains unresolved; keep it RED.

---

## 1. Terrain source — VERIFIED (this is the audit's main new result)

The stage-pad volume was differenced against **`dem/dem_design_1ft.tif`**
(sha256 `035eb773…1666c`). Full metadata in `terrain_source_report.txt`. The prior red-team
*asserted in a comment* this was "existing grade"; this audit **proves** it:

- **It is bare existing ground, verified.** `dem_design_1ft.tif` is **byte-value identical** to the
  viewer's explicitly-named `existing_ground_1ft.tif` — `max|Δ| = 0.0000 ft` over all 563,922 valid
  cells. The name "design" is a misnomer; the surface is untouched LiDAR ground. *(observed)*
- **Provenance:** USGS 3DEP LiDAR, collection `USGS_LPC_MI_13County_2015_C16` (tiles 532749/532751),
  ground class 2 only → PDAL `writers.gdal` IDW. Generator `scripts/build_dems.py`. Band description
  `idw`; 87.9 % valid (voids interpolated). *(observed)*
- **CRS / grid:** EPSG:6494 (NAD83(2011) / Michigan Central, international ft), 1 ft pixels
  (1 sf/cell), 801×801, nodata −9999. **Vertical datum NAVD88 Geoid12A intl ft is provenance-declared
  (manifest), NOT embedded** in the GeoTIFF — a documented caveat, not a defect. *(observed)*
- **Same source as the rest of the model?** Yes, for every comparable quantity:

  | Quantity | Terrain sampled | Same as stage pad? |
  |---|---|---|
  | Seating / sightlines | `dem_design_1ft.tif` (existing) | ✅ same |
  | Drainage / swales | `dem_design_1ft.tif` (existing) | ✅ same |
  | Earthwork 500.8 CY balance | `dem_design_1ft.tif` (existing) | ✅ same |
  | ADA route grades | `proposed_grade_1ft.tif` (proposed) | ⚠️ different **by design** |
  | **stage_pad_redteam** | `dem_design_1ft.tif` (existing) | ✅ same |

  ADA is the only exception and it is correct — running/cross-slope must be checked on the finished
  (burned) surface, so ADA reads `proposed_grade_1ft.tif` (= existing + burned earthwork; generator
  `build_proposed_grade.py`). Sampling a stage **fill** against **existing ground** is the right
  choice and matches seating/drainage/earthwork. *(observed → inference: source is correct)*

**Sampling method:** `rasterize(all_touched=False)`, point-in-cell, 1 sf/cell. Appropriate for a
volume statistic (no perimeter over-burn). *(observed)*

## 2. Footprint scope — split, no internal double-count

Footprint = P_opt-placed **70×34 core** ∪ five-facet apron ∪ two shoulders (translated from the
inherited stage by the adopted lateral offset [6.42, 19.87] ft). Split geometry:
`adopted_stage_footprint_split.geojson`. Per-component fill (target 612.5):

| Component | area sf | mean fill ft | fill CY |
|---|--:|--:|--:|
| stage_core_70×34 | 2,380 | 2.629 | 231.7 |
| five_facet_apron | 316 | 2.669 | 31.2 |
| shoulder_a | 345 | 2.627 | 33.6 |
| shoulder_b | 345 | 2.632 | 33.6 |
| **Σ components** | **3,386** | | **330.1** |
| **UNION (once)** | **3,386** | 2.633 | **330.2** |

Σ components (330.1) = union (330.2) within rounding → **components tile the footprint with no
internal overlap; no double-count *within* the stage.** *(observed)*

## 3. Arithmetic closure — PASS, and the prose discrepancy explained

`area_sf × mean_fill_ft ÷ 27` = 3,386 × 2.633 ÷ 27 = **330.2 CY** = reported fill. ✔ *(observed)*

**The 2,699-vs-3,386 sf discrepancy is resolved:** 2,699 sf is the **deck footprint only**
(core + apron; confirmed independently — deck rasterizes to 2,696 cells). The 330 CY is charged over
the **3,386 sf union**, which adds the two shoulders. So:
- "ground ~2.6 ft below 612.5" is **correct** (union mean fill = 2.633 ft). *(observed)*
- Pairing "~2.6 ft" with "2,699 sf" was the prose error (2,699 × 2.633 ÷ 27 = 264 CY, not 330; and
  330 CY ÷ 2,699 sf would falsely imply 3.30 ft). The right pairing is **3,386 sf × 2.633 ft**. Area
  and depth are consistent once the footprint scope is stated correctly. *(inference, arithmetic)*

## 4. Datum scope — the number is largely a datum + construction choice (CONDITIONAL)

Volume vs target elevation (union; full table in `stage_pad_volume_breakdown.csv`):

| Target elev | fill CY | what it is |
|--:|--:|---|
| 611.3 (100-yr WSEL) | 179.7 | flood pool, not a base |
| 611.8 (500-yr WSEL) | 242.4 | flood pool |
| 612.0 (spillway crest) | 267.5 | min flood-safe base top |
| **612.5 (deck top)** | **330.2** | deck **top**, not necessarily the earthen top |

**~63 CY of the "330" is only the 612.0→612.5 lift.** Requirements fix the *deck surface* at 612.5
(sightline focus, performer access, stage usability); drainage freeboard only needs the *base* above
~612.0. Nothing requires the whole footprint to be **earth** at 612.5. "Required imported fill" is
therefore **less than 330** and depends on the earthen-base target, which is unset. *(inference; key
assumption named below)*

## 5. Construction assumption — UNSELECTED (no adopted construction record)

**There is no explicit design record adopting a construction method for the stage.** What the repo
does say:
- `dem/in_situ_grading_manifest.json`: **current accounting treats the stage as structure, not
  grading** — "low deck STRUCTURE, not grading … excluded … as in Scenario E's 500.8 CY total." The
  proposed-grade raster *deliberately never burns the stage.* *(observed — an accounting choice, not a
  construction decision)*
- `material_zones.geojson`: `hardscape_stage` carries a material label "low hardwood/composite **deck
  over compacted base** at event-floor grade." *(observed — a material default consistent with
  Scenario B below; not a ratified construction selection)*
- `SCENARIO_E_CIVIC.md`: the stage-refit earthwork delta on file is **37.8 CY** (candidate
  `az150_lat-20`) — a re-grading delta, different in scope from a solid pad. *(observed)*

The ~330 CY belongs to **one** of several construction scenarios, none of which is the adopted
baseline until explicitly selected. As three separate quantities (never one "earthwork" number):

| Scenario | earthwork fill | structure | status |
|---|--:|---|---|
| **A — solid earthen pad → 612.5** | **330.2 CY** | none | **valid upper-bound scenario**; not adopted unless selected |
| B — deck over compacted base (fill apron+shoulder edges, deck the low core) | ~98 CY | deck over 2,380 sf | matches the material label; not ratified |
| C — freestanding low deck / piers | ~0 CY (footings) | deck over 3,386 sf | lightest; not ratified |

Scenario A is a legitimate bound (a fully earthen 612.5 pad genuinely needs ~330 CY), **not a
strawman**. It is simply not the adopted construction, because no construction has been adopted. The
deck/compacted-base reading is **Scenario B**, not a universal canon. *(observed + inference)*

## 6. Spatial sanity — mostly PASS, with one flagged discrepancy

- **Core is 70×34 (2,380 sf), NOT the retired 52×26 (1,352 sf).** ✅ *(observed)*
- **No stale 85-ft stage distance participates.** ✅ Axis 150.0°, offset [6.42, 19.87] ft. *(observed)*
- **Row-1 vs stage elevation is physically plausible.** Existing ground: stage footprint mean
  **609.87**, row 1 mean **610.82**, row 2 mean **611.88** — the bowl rises away from the stage, so
  the stage/forecourt is the genuine **low point**. A deck top at 612.5 sits ~1.7 ft above row-1
  existing ground (normal for a stage above the front row). The "low-pan" observation is real.
  *(observed → inference: plausible)*
- **🔴 The brief's "stage front to row 1 = 35 ft" is contradicted → promoted to a separate RED
  issue.** The adopted footprint encodes `front_to_row1_ft = {east: 12.0, bend: 32.7, south: 21.9}`
  (min **12 ft**, east). No 35 ft anywhere. Cause and disposition are resolved in the addendum
  **`stage_placement_clearance_addendum.md`** (short version: the 35-ft figure is the retired
  single-fan `design_open_low` rule; current canon adopted a ≥12 ft pocket gate on different row-1
  geometry). *(observed — now tracked separately)*

## 7. Overlap accounting — NOT cleanly additive (FAIL as stated)

`stage_pad_overlap_audit.csv` (footprint ∩ existing quantities):

| ∩ with | overlap sf | in 500.8? | consequence |
|---|--:|:--:|---|
| east_flank_swale | 188.3 | **yes** | **collision + double-count**: area is a counted swale **cut**; stage **fill** reverses it |
| south_flank_swale | 103.5 | **yes** | same collision |
| orchestra_event_floor | 221.2 | no | shares the 612.5 plane — count **once**, not additive |
| construction_envelope | 691.1 | envelope | expected; not a volume |
| treatment_cell / cross_aisle / ada / treads | 0–0.4 | — | clear |

**~292 sf of the footprint sits on the two drainage swales.** Independently confirmed from the
raster: within the footprint, `proposed − existing` **cuts 290 cells** (mean −0.13 ft, max **+0.00** —
proposed *never* fills here) — i.e., the adopted design digs swale channels through part of the stage
footprint. Those cuts (east 36.8 + south 37.6 CY per `earthwork.csv`) are **in the 500.8**. A stage
**fill** in the same cells (a) physically conflicts with the swale cut and (b) cannot be added without
first reversing a counted cut. So **"+330 additive" is invalid as stated.** *(observed + inference)*

---

## Synthesis

**Observed (hard):** the stage-pad volume was computed against the correct bare existing-ground
LiDAR surface (verified identical to the viewer's existing-ground DEM), the same surface used for
seating, drainage, and the 500.8 CY balance; arithmetic closes at 330.2 CY over 3,386 sf × 2.633 ft;
the stage footprint is the bowl's low point; the adopted proposed grade cuts (never fills) that area
for swales.

**Inference:** the ~330 CY is a valid **solid-pad-to-612.5 upper-bound scenario**, not a proven
required import. No construction method has been adopted; if a lighter method is selected the required
earthwork is far smaller (Scenario B ~98 CY, Scenario C ~0 CY). The ~330 CY stands as the fill for the
fully-earthen bound only.

**Key assumption in the 330 figure:** that the entire core+apron+shoulder footprint is a **solid
earthen pad at 612.5**. Valid as a scenario; not the adopted baseline unless explicitly selected.

**Most decision-relevant unknowns (for the user):**
1. **Construction method + earthen-base target** — deck-on-piers vs deck-on-compacted-base vs earthen
   pad, and base top elevation (≤612.0 flood-safe vs 612.5 deck top). This selects among the ~0 / ~98 /
   ~330 CY scenarios.
2. **Stage placement vs the 35-ft rule → now a separate RED issue.** The brief's 35-ft
   stage-front-to-row-1 is contradicted by the adopted P_opt clearances (12/32.7/21.9 ft). Cause and
   disposition are worked out in **`stage_placement_clearance_addendum.md`** (RED, unresolved).
3. **Swale↔stage collision** — the ~292 sf must be netted / redesigned; the two designs are mutually
   exclusive in those cells today.

**Sufficient for the next step:** do **not** record "stage pad needs ~330 CY regardless of refit."
Record the gate language above. To close the RED item: (a) fix deck-vs-pad construction with
structural input, (b) set the earthen-base target elevation, (c) resolve the stage↔swale overlap and
net the ~292 sf already in the 500.8. The terrain data and arithmetic are sound; the **scope,
datum, construction, and overlap assumptions** are what remain unresolved.
