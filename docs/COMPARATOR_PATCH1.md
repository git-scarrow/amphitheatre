# Comparator benchmark — Patch 1 (basis-tightening pass)

**Date:** 2026-06-12 · applies to the benchmark committed at `30d5640`
(`docs/AMPHITHEATRE_COMPARATORS.md` was edited in place; this memo lists
what changed and why). Petoskey canonical geometry untouched — audit gate
re-verifies the source hashes.

## 1 · Petoskey stage basis: four-way frontage split

The single "stage frontage 70 ft" figure was a basis error: it collapsed the
core deck and the shouldered frontage. Measured from
`vectors_geojson/bowl_zones.geojson` (read-only, extent perpendicular to the
az-150 stage axis): **core 70.0 ft · shoulders 2 × 17.0 ft · effective
frontage 104.0 ft · uniform depth 34.0 ft · union 3,072 sq ft.**

New fields in `petoskey_metrics.json` / `comparison.json`
(`stage_frontage_ft` deleted — the audit gate now FAILS if it reappears):

| field | value | basis |
|---|---|---|
| `stage_core_width_ft` | 70.0 | canon |
| `stage_effective_frontage_ft` | 104.0 | measured (bowl_zones union) |
| `row1_chord_ft` | 139.3 | measured (2·85·sin 55°) |
| `row1_length_physical_ft` | 131.6 | measured (tread sum) |
| `frontage_coverage` | core/shouldered over chord 0.50/0.75 · over geometric arc 0.43/0.64 · over physical row 1 0.53/0.79 | measured |

**Verdict change:** "stage frontage CHALLENGED" became **"CHALLENGED —
conditionally"**: on a core-only reading the stage is undersized vs both
venues; counting shoulders as performance surface, 104 ft lands inside the
comparator family (92–110 ft). Which reading applies is the open Rule 9
programming question — the benchmark cannot settle it.

## 2 · Comparator stage dims: extended search, logged

Searched beyond venue websites: Wayback CDX sweeps of both domains,
production/rental pages, sitemaps, archived 2002 SB architectural drawings.
**Found:** SB official 2007 reserved-seating chart PDF (archived; local copy
saved) and the 2002 stage-rebuild drawing set (podium grid ≈146 ft,
corroborating deck 92 < roof 125 < podium 146). **Not found anywhere:** a
published deck W×D for either venue — dims stay `inferred_imagery` with
ranges. All failed searches logged in each `SOURCES.md` (audit-enforced).

## 3 · Capacity bases labeled

`capacity_basis` added everywhere; the board table and memo now say the
three numbers are unlike quantities: Petoskey = **geometric seat count**
(validated tread lengths), Meijer = **lawn/event capacity** (press-
circulated, no venue figure — weak), SB = **ticketing capacity**
(config-dependent 4,500/4,562/5,000). Audit fails any capacity without a
basis class.

## 4 · DEM basis verified

Both comparator DEMs confirmed **bare-earth DTM** (3DEP standard);
terrace preservation verified hillshade-vs-imagery per site and recorded as
`dem_type` (+`known_voids`: SB stage house filtered to ground, Meijer pond
flattened, sub-1 m risers unresolved). Petoskey's `dem_type` notes its
section comes from the *design surface*, not survey returns.

## 5 · ADA comparison expanded

New structured `ada_detail` (route concept / vertical drop / dispersion /
redundancy / sightline preservation, each with a basis) for all three
sites + a comparison table in the memo. Material finding from the SB 2007
chart: **SB's chart shows accessible seating at a single elevation**
(sections P + S behind the floor), while Petoskey's design disperses across
two elevations with two independent routes. Scope caveat (added after
review): the Petoskey claim rests on
`analysis/tier_emission/Scenario_E_baseline_reemit/validation.json`, which
gates running slope / flight + landing counts / cross-aisle slopes +
drainage only — not widths, clear floor space, companion seats, or §221
dispersion counts — and the SB observation is a 2007 chart. The memo
therefore presents this as a documentation comparison, **not a compliance
ranking**.

## 6 · Rule 9 left open, explicitly

Memo now states: comparators validate the **scale and typology** of a
~100 ft shouldered frontage but **cannot choose Petoskey's stage azimuth**;
the +25.6° axis mismatch is untouched. Audit greps the memo for this
disclaimer.

## 7 · Audit gate additions

New FAIL conditions: bare `stage_frontage_ft` on Petoskey (must be the
core/effective/chord/arc split, with `frontage_coverage` matrix);
`capacity_basis` missing; `dem_type` missing, not bare-earth, or lacking a
terrace-preservation verification; `ada_detail` missing any of its five
labeled fields; memo missing the Rule 9 azimuth disclaimer; SOURCES.md
missing a failed-search log. Existing hash checks on Petoskey canonical
geometry unchanged and passing.

## Changed files

`scripts/comparators/extract_metrics.py` · `render_comparator_board.py`
(table rows + caveat strip) · `audit_comparators.py` · both
`site_config.json` · both `SOURCES.md` · `petoskey_metrics.json` ·
`comparison.json` · per-site `site_metrics.json` ·
`boards/comparator_side_by_side.png` · `AMPHITHEATRE_COMPARATORS.md` ·
new `data/comparators/santa_barbara_bowl/SBB_Reserved_seating_2007_wayback.pdf`.
