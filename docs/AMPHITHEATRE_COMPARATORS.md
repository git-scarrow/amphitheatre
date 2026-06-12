# Amphitheatre comparator benchmark — Petoskey civic bowl vs two in-use bowls

**Date:** 2026-06-12 · **Status:** complete (planning-grade)
**Board:** `boards/comparator_side_by_side.png`
**Data:** `data/comparators/` (per-site SOURCES.md, DEM clips, configs,
derived metrics) · combined `data/comparators/comparison.json`
**Scripts:** `scripts/comparators/` (fetch → digitize → sections → arcs →
metrics → board → audit; each file header gives the reproduce command)
**Audit gate:** `scripts/comparators/audit_comparators.py`

## Purpose

Test whether the Petoskey Pit civic bowl's seating rake, stage placement,
stage size, audience distances, bowl geometry, and human-scale experience are
credible against **real, in-use amphitheatres measured from public LiDAR**,
not against generic best-practice claims.

## Basis labels (used everywhere)

| flag | meaning |
|---|---|
| **M** | measured — USGS 3DEP 1 m DEM (comparators) or repo design geometry (Petoskey) |
| **I** | inferred — digitized from Esri imagery / OSM footprints; never presented as measured |
| **P** | published — venue/press figure with URL |
| **C** | Petoskey repo canon (truth_package / in_situ_common.py, read-only) |

## Comparator selection

| candidate | terrain data | decision |
|---|---|---|
| **Frederik Meijer Gardens Amphitheater** (Grand Rapids MI, 2003) | USGS 1 m, MI_31Co_Kent_2016 (acq. 2016) | **ACCEPTED** — capacity-matched (~1,900), tiered lawn bowl, low covered stage, open landscape backdrop; closest typology to Petoskey |
| **Santa Barbara Bowl** (Santa Barbara CA, 1936/rebuilt 2002) | USGS 1 m, CA_Montecito_2018 (acq. 2018) | **ACCEPTED** — larger (4,562) terraced canyon bowl; stress-tests rake/rise/distance at scale |
| Gerald R. Ford Amphitheater (Vail CO) | covered (CO Central Western 2016) | **REJECTED** — roofed pavilion over most seating: not an open bowl typology, and bare-earth under the roof is unreliable for row-level rake |
| Red Rocks Amphitheatre (Morrison CO) | covered (CO 3DEP 1 m) | **REJECTED** — ~9,500-seat rock-landform outlier; geometry driven by the monoliths, not by civic-bowl design choices |

Both accepted DEMs post-date the venues' current geometry (SB stage rebuilt
2002, LiDAR 2018; Meijer built 2003, LiDAR 2016). Raw TNM/Nominatim/Overpass
discovery responses are archived in `data/comparators/_sources/`.

## CRS / units discipline

Comparator clips stay in native UTM meters (EPSG:26911 / 26916, NAVD88 m);
every derived number is converted to **international feet explicitly** and
suffixed `_ft` (`scripts/comparators/sites.py` documents the policy).
Petoskey stays in EPSG:6494 international feet / NAVD88 ft and **its source
geometry was not modified** — the audit gate verifies the canonical file
hashes against `truth_package/design_state.current.json`.

## Method (per comparator)

1. 1 m DEM clip via GDAL `/vsicurl/` windowed read (no full-tile download),
   provenance JSON written next to the clip.
2. Stage anchor from the OSM stage footprint (minimum rotated rectangle →
   frontage azimuth); audience-facing azimuth = perpendicular, on the seating
   side; verified against the DEM fall line and imagery (I).
3. Centerline section through the stage-front anchor along the bowl axis,
   0.5 m sampling (M); breaks (row 1 / top of seating / rim) digitized from
   the profile's fine structure (M, anchor I).
4. Fan angle + radii measured as angular extent / radial distance of
   mid-bowl elevation contours about the anchor (M). An unconstrained circle
   fit was tried and **rejected** (centers drifted uphill on <180° arcs
   flanked by natural slope — recorded in `fit_bowl_arcs.py`).
5. Stage deck dims digitized from imagery with OSM + published square
   footage as independent cross-checks (I, bounded).

## Results

| metric | Petoskey (design) | Meijer Gardens | Santa Barbara Bowl |
|---|---|---|---|
| capacity — **unlike bases, do not compare raw** | 1,283 nominal / 1,243 validated — *geometric seat count from tread lengths* [C] | ~1,900 — *lawn/event capacity, press-circulated, no venue figure* [P, weak] | 4,562 — *ticketing capacity, config-dependent (4,500 reserved-floor / 5,000 GA)* [P] |
| audience facing az | 312 nominal (bay corridor 330) [C] | 20.9 (pond backdrop) [I] | 95.8 (canyon backdrop) [I] |
| stage **core** width (ft) | 70 [C] | ~100 (90–110, single deck) [I] | ~92 (85–100, single deck) [I] |
| stage **effective frontage** w/ shoulders (ft) | 104 (core + 2×17 ft shoulders, measured from bowl_zones; counts only if shoulders are performance surface — Rule 9 OPEN) [M] | same as core [I] | same as core [I] |
| row-1 **chord** across fan (ft) | 139.3 (2·85·sin 55°) [M] | — | — |
| frontage coverage (core / shouldered) | of chord: 0.50 / 0.75 · of geometric arc: 0.43 / 0.64 · of physical row 1: 0.53 / 0.79 [M] | ≈1 (deck wraps near-field rows) [I] | ≈1.5 of near-field arc [I] |
| stage depth (ft) | 34 [C] | ~45 (35–54) [I] | ~50 (40–79 incl. house) [I] |
| stage front → row 1 (ft) | 35 [C] | ~10 [M] | ~27 [M] |
| fan angle (deg) | 110 [C] | 113 [M] | 132 [M] |
| row-1 physical length (ft) | 132 (3 sections) [M] | short wrap at stage lip [M/I] | ~62 near-field arc [M] |
| rise row 1 → top (ft) | 22.8 [M] | 12.9 [M] | 68.8 [M] |
| avg rake (%) | 31.8 [M] | 14.3 [M] | 36.6 [M] |
| local rake range (%) | ~32.7 uniform [M] | 6–21 [M] | 16–61 [M] |
| upper-row distance (ft) | 107 [M] | 100 [M] | 215 [M] |
| rows / terraces | 15 treads × 3 sections (rows 1–18, 5/9/10 repurposed) [C] | ~8–10 seat-wall terraces + lawn [I] | 40 lettered terrace rows in 4 banks + 14 floor rows — official 2007 seating chart [P] |
| ADA / circulation | 2 × 8.33% switchback routes + level cross-aisle rows 9/10, validated [C] | level side plazas + flanking paths + mid cross path [I] | designated handicapped sections P + S at one level behind floor (2007 chart) + top concourse [P/I] |
| backdrop | open to Little Traverse Bay az 330, no upstage wall [C] | pond + woodland behind low canopy [I] | full stage house against canyon hillside [I] |

## Verdicts on Petoskey dimensions

**SUPPORTED**

- **Seating rake 31.8%** — sits inside the real-venue envelope: steeper than
  Meijer's lawn (6–21%) but matching SB's mid banks and well under SB's upper
  banks (up to ~61% terrain slope). A uniform ~32% bowl is normal practice
  at civic scale.
- **Fan angle 110°** — both comparators measured wider-or-equal (113°, 132°).
  The ±55° fan is conservative-normal.
- **Bowl rise 22.8 ft** — between Meijer (12.9) and SB (68.8); proportionate
  to capacity.
- **Upper-row distance 107 ft** — nearly identical to the capacity-matched
  Meijer (100 ft); SB runs 215 ft. Petoskey's intimacy claim is real: the
  farthest formal seat is closer to the stage than SB's mid-bowl cross-aisle.
- **Open-air / no upstage shell** — Meijer demonstrates the same typology in
  the same climate band (low covered stage, open landscape backdrop, lawn
  bowl) at the same capacity. SB's full stage house is the counterexample,
  but it serves touring amplified acts, not a civic landscape program.
- **ADA/cross-aisle pattern** — Petoskey's mid-bowl level cross-aisle +
  switchback routes mirrors SB's legible mid-bowl aisle + concourse pattern,
  and is *more* explicit than either comparator (it is validated geometry,
  not inferred).

**SUPPORTED with note**

- **Stage front → row 1 = 35 ft** — the largest of the three (SB ~27 ft,
  Meijer ~10 ft). Defensible because the gap doubles as the orchestra/event
  floor (SB uses its floor the same way), but the comparators say intimacy
  would tolerate *closer*, not farther. Nothing here supports widening the
  gap.

**CHALLENGED — conditionally**

- **Stage core width 70 ft vs the seating front** — the verdict splits on
  whether the 2×17 ft lateral shoulders are programmed as performance
  surface (a Rule 9 question, currently OPEN):
  - **Core only (70 ft):** covers 0.50 of the row-1 chord (139.3 ft),
    0.43 of the geometric arc (163 ft), 0.53 of the built row-1 treads
    (131.6 ft). Both real venues run wider decks (SB ~92 ft, Meijer ~100 ft
    canopy) that span or wrap their near-field seating, and even the
    capacity-matched Meijer is ~40% wider. On a core-only reading the
    Petoskey stage is **undersized in width** for a 110° fan, and end-of-fan
    seats view it obliquely across the event floor.
  - **With shoulders (104 ft effective):** coverage rises to 0.75 of chord /
    0.79 of built row 1, and the frontage lands **inside the comparator
    family (92–110 ft)**. The challenge then dissolves into a programming
    decision, not a geometry deficit.
  - **Depth 34 ft is fine** on either reading (SB perf deck ~40–50 inferred,
    Meijer ~35–45 inferred).
  The comparators therefore validate the *scale and typology* of a ~100 ft
  shouldered frontage, but they **cannot choose Petoskey's stage azimuth or
  decide the shoulder-programming question — Rule 9 stays open**; the
  +25.6° axis mismatch on record is untouched by this benchmark.

**ADA comparison (expanded, patch 1)**

| dimension | Petoskey [C] | Meijer [I] | SB Bowl [P/I] |
|---|---|---|---|
| route concept | 2 dedicated 8.33% switchback ramps + level cross-aisle (rows 9/10) | level garden-path entries bottom + rim of a low bowl | approach to one accessible level behind the floor |
| vertical drop handled | ~21 ft rim→floor, 3–4 flights, 4–5 landings, validated | 12.9 ft total; no dedicated ramp structures needed | bowl rises 68.8 ft; accessible seating avoids it by staying low |
| dispersion | 2 elevations (floor + mid-bowl cross-aisle) | likely 2 elevations (plaza + rim), unmarked | **1 elevation** — sections P + S flanking Founders Row (2007 chart) |
| redundancy | 2 independent validated routes | flanking paths both sides | 2 flank approaches to the single level |
| sightlines from wheelchair positions | wheelchair-eye (3.90 ft) refs with blocks_bay_view flags, rim-grazing rule applied | unverified (shallow lawn) | plausibly preserved (front-of-bank), unverified |

Petoskey's accessible-seating **dispersion and route redundancy exceed both
comparators** as designed; SB — the professionally operated venue —
concentrates accessible seating at a single elevation. Petoskey's pattern is
not just plausible, it is better-documented than either real venue.

**DEM basis (verified, patch 1)**

Both comparator DEMs are **bare-earth DTMs** (USGS 3DEP 1 m standard).
Constructed seating geometry survives the bare-earth filter as graded
ground: hillshade resolves SB's concentric terrace banding and Meijer's
lawn-terrace arcs in the exact positions imagery shows them
(`diagnostic_dem.png` vs `diagnostic_imagery.png` per site). Known voids:
SB's stage house is filtered to ground beneath the deck; Meijer's pond is a
flattened water return; individual risers (~1 ft / ~18 in) are below 1 m
resolution everywhere. Petoskey's section uses the repo's **design surface**
(`proposed_grade_1ft.tif`) — designed geometry, not survey returns; its
bare-earth lineage is the 2015 USGS LiDAR + 2026 supplement.

**STILL UNCERTAIN**

- Comparator stage deck dimensions are imagery/OSM-inferred — an extended
  search (technical riders, production PDFs, sitemaps, Wayback CDX sweeps of
  both venue domains, archived 2002 SB architectural drawings; failed
  searches logged in each SOURCES.md) found **no published deck W×D for
  either venue**. SB's dims are now bounded three ways (deck ~92 < OSM roof
  125 < 2002 podium grid ~146 ft) but remain inferred.
- Meijer's 1,900 capacity is weakly cited (Wikipedia citation-needed).
- Row-level conclusions (riser heights, C-values) cannot be drawn from 1 m
  comparator DEMs — deliberately not attempted (audit enforces).
- Stage shape/orientation (Rule 9) is not resolvable from comparators; they
  only quantify the frontage shortfall.

## Reproduce

```
.venv/bin/python scripts/comparators/fetch_comparator_dem.py
.venv/bin/python scripts/comparators/fetch_imagery.py
.venv/bin/python scripts/comparators/extract_osm_geometry.py
.venv/bin/python scripts/comparators/render_diagnostics.py
.venv/bin/python scripts/comparators/extract_sections.py
.venv/bin/python scripts/comparators/fit_bowl_arcs.py
.venv/bin/python scripts/comparators/extract_metrics.py
.venv/bin/python scripts/comparators/render_comparator_board.py
.venv/bin/python scripts/comparators/audit_comparators.py
```
