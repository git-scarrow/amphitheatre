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
| capacity (seats) | 1,283 nominal / 1,243 validated; options to 1,505 [C] | ~1,900 [P, weak cite] | 4,562 [P] |
| audience facing az | 312 nominal (bay corridor 330) [C] | 20.9 (pond backdrop) [I] | 95.8 (canyon backdrop) [I] |
| stage frontage (ft) | 70 (+ shoulders) [C] | ~100 (90–110) [I] | ~92 (85–100) [I] |
| stage depth (ft) | 34 [C] | ~45 (35–54) [I] | ~50 (40–79 incl. house) [I] |
| stage front → row 1 (ft) | 35 [C] | ~10 [M] | ~27 [M] |
| fan angle (deg) | 110 [C] | 113 [M] | 132 [M] |
| row-1 physical length (ft) | 132 (3 sections) [M] | short wrap at stage lip [M/I] | ~62 near-field arc [M] |
| rise row 1 → top (ft) | 22.8 [M] | 12.9 [M] | 68.8 [M] |
| avg rake (%) | 31.8 [M] | 14.3 [M] | 36.6 [M] |
| local rake range (%) | ~32.7 uniform [M] | 6–21 [M] | 16–61 [M] |
| upper-row distance (ft) | 107 [M] | 100 [M] | 215 [M] |
| rows / terraces | 15 treads × 3 sections (rows 1–18, 5/9/10 repurposed) [C] | ~8–10 seat-wall terraces + lawn [I] | ~30–40 bench rows, 3 banks [I] |
| ADA / circulation | 2 × 8.33% switchback routes + level cross-aisle rows 9/10, validated [C] | level side plazas + flanking paths + mid cross path [I] | mid-bowl cross-aisle ~100 ft radius + top concourse; ADA platform 2003 [I/P] |
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

**CHALLENGED**

- **Stage frontage 70 ft vs the row-1 arc** — Petoskey's stage covers ~43%
  of its 110° row-1 arc (70 ft vs 132 ft of physical row 1 at radius 85 ft).
  Both real venues do the opposite: the stage frontage spans or exceeds the
  near-field seating front (SB ~92 ft stage vs ~62 ft near-field arc; Meijer
  ~100 ft canopy wrapping its first seat walls). Even the capacity-matched
  Meijer runs a stage ~40% wider than Petoskey's. End-of-fan seats at
  Petoskey will view the stage obliquely across the event floor. This is the
  same tension already on record as the Rule 9 axis mismatch (+25.6°), now
  quantified against real venues: **the 70 ft core reads undersized in width
  for a 110° fan; the 34 ft depth is fine** (SB perf deck ~40–50, Meijer
  ~35–45). A Rule 9 resolution that widens effective frontage (shoulders
  counted as performance surface, or a wider low deck) would close most of
  the gap.

**STILL UNCERTAIN**

- Comparator stage deck dimensions are imagery/OSM-inferred (no venue spec
  published); ranges are carried everywhere and cross-checked, but a tech
  pack from either venue would harden the stage-size verdict.
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
