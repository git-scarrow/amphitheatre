# Charlevoix comparator — Clarence Odmark Performance Pavilion, East Park

**Date:** 2026-07-21 · **Status:** data gathered, planning-grade, geometry measured
**Site data:** `data/comparators/charlevoix_odmark_pavilion/`
**Sources + failed-search log:** `data/comparators/charlevoix_odmark_pavilion/SOURCES.md`
**Section overlay:** `boards/bowl_section_overlay.png`
**Parent memo:** `docs/AMPHITHEATRE_COMPARATORS.md` (basis labels, CRS/units discipline)

## The venue

The Charlevoix waterfront performance space is the **Clarence Odmark
Performance Pavilion** (OSM: "Odmark Band Pavilion"; City of Charlevoix:
"East Park Performance Pavilion") in **East Park, 400 Bridge Street,
Charlevoix, MI**, on the west shore of **Round Lake** beside the municipal
marina. It is a **stone band shell with a permanent roof over the stage only**,
facing **open-air hillside seating**. Rebuilt in 2007 as part of an
**$11 million park and marina reconstruction**; the park reopened in 2008 and
took an APA *Great Public Spaces* designation in 2009. It carries roughly
**50 performances a year**, including the city's *Live on the Lake* series.

Named for Clarence "Odie" Odmark, Charlevoix band director 1946–1975.

## Why it is the most relevant comparator we have

Meijer Gardens and Santa Barbara test *geometry at scale*. Odmark is the first
comparator that matches Petoskey's **program and setting**, not just its
landform:

| shared trait | Petoskey Pit | Odmark | Meijer | SB Bowl |
|---|---|---|---|---|
| small-city **municipal** civic venue | yes | **yes** | no (private garden) | no (nonprofit, touring) |
| **northern Michigan** climate/season | yes | **yes** | MI, but southern | no |
| **waterfront**, water as backdrop | Little Traverse Bay | **Round Lake + marina** | pond | canyon |
| **covered stage, open-air audience** | proposed | **yes** | yes | full stage house |
| seating on a **graded hillside**, no fixed seats | yes | **yes** | yes (lawn) | no (fixed terraces) |
| free / low-cost public programming | yes | **yes** | ticketed concerts | ticketed |

It is, however, **much smaller** than Petoskey and has **no published
capacity**, so it constrains *geometry, stage typology and operations* — not
seat count. Do not derive a Petoskey capacity from it.

## Data gathered (this is the deliverable)

| item | source | basis |
|---|---|---|
| **1 m bare-earth DEM**, 600 × 600 m clip | USGS 3DEP `MI_CharlevoixCounty_2018_A18`, tile 1M_16_x63y502, LiDAR acquired **2018**, published 2024-05-22 | measured |
| DEM provenance (URL, CRS, window, stats) | `dem/provenance.json` | — |
| pavilion footprint | OSM way **1112264619** (`amenity=theatre`, `building=shelter`) | inferred |
| area OSM features (246) | Overpass, archived `_sources/overpass_charlevoix.json` | inferred |
| aerial imagery, 0.5 m site + ~0.3 m close-up | Esri World Imagery | inferred |
| centerline section, fan scan, arc fit, metrics | `derived/` | measured |
| published operations facts | City use policy + APA + HMDB | published |

CRS **EPSG:26916** (NAD83/UTM 16N, m), vertical NAVD88 m; every derived number
converted to international feet and suffixed `_ft`, per the existing units
policy. **Petoskey canon was not modified** — the audit's Petoskey hash checks
pass unchanged.

The 2018 LiDAR **post-dates the 2007 rebuild**, so the surface reflects
current geometry — the same currency test the other two comparators passed.

## Measured geometry vs Petoskey

All comparator rows are measured from the 1 m DEM; Petoskey rows are repo canon.

| metric | **Petoskey (design)** | **Odmark, Charlevoix** | Meijer Gardens |
|---|---|---|---|
| stage front → row 1 | 35 ft [canon] | **10 ft** [M] | 10 ft [M] |
| rise, row 1 → top | 22.8 ft [M] | **10.9 ft** [M] | 12.9 ft [M] |
| average rake | 31.8 % [M] | **17.1 %** [M] | 14.3 % [M] |
| local rake range | ~32.7 uniform [M] | **16.8–20.9 %** [M] | 6.2–21.0 % [M] |
| fan angle | 110° [canon] | **75.1°** [M] | 113.1° [M] |
| top-of-seating distance | 104.5 ft [M] | **74 ft** [M] | 100 ft [M] |
| floor / apron elev | 612.5 ft [canon] | **586.7 ft** [M] | 811.0 ft [M] |
| top-of-seating elev | 633.7 ft [M] | **598.0 ft** [M] | 824.1 ft [M] |
| rows | 15 treads × 3 sections [canon] | **~5–6 turf terrace bands, no fixed seats** [I] | ~8–10 seat-wall terraces + lawn [I] |
| capacity | 1,283 nominal / 1,243 validated — geometric [canon] | **NONE PUBLISHED** [see SOURCES.md] | ~1,900 lawn/event, weakly cited [P] |

**Read:** Odmark is a *half-scale* version of the same idea — half Petoskey's
rise, roughly half its rake, three-quarters of its seated depth, and a
narrower fan. In the normalized section overlay it lies almost exactly on top
of Meijer Gardens. Petoskey is materially steeper and taller than both
Michigan comparators, tracking Santa Barbara's lower bank instead.

### Site geometry, as measured

- Pavilion sits on a bench at **586.6–586.7 ft**; **Round Lake is a flat water
  return at 579.4 ft** NAVD88, beginning ~25–30 m out on az 30–140.
- The **only** monotonic rising sector around the pavilion is **az 275–345**,
  centred **az 310** — that is the seating. Audience therefore faces
  **az 130 (SE)**, ±10°. Imagery independently shows the terrace bands in
  exactly that sector.
- Rise is continuous from the apron to a **flat rim promenade at 597.4–598.1 ft**
  at s ≈ 74 ft, which then runs level out to at least s = 164 ft. Top of
  seating and rim crest coincide; there is no separate rim berm.
- Beyond az 345 and below az 275 the ground still climbs, but as long shallow
  topography toward Bridge Street (rake ~6–10 %) — street grade, not seating.

### The pavilion footprint is a circle — and that matters

OSM way 1112264619 is a **circle**: 22 nodes, all radii 7.0–8.3 m (mean 7.75 m
→ **15.5 m / 51 ft diameter**); the minimum rotated rectangle is 52 × 49 ft,
aspect 1.06. Unlike Meijer's lens-shaped canopy, **there is no long axis, so
the audience azimuth cannot be derived from the footprint.** It was taken from
the DEM fall line instead and cross-checked against imagery. Any future work
that wants a stage-orientation precedent from Charlevoix must note that this
venue's stage is *omnidirectional in plan* — it does not choose a frontage
azimuth the way a rectangular deck does.

## The covered stage — what is known, and what is not

This is the part of the ask with the weakest published record, so it is
labelled carefully.

**Established (published):**
- Permanent roof covers **the stage only**; the audience is uncovered. This is
  the Meijer typology, *not* the Vail roofed-seating typology that this project
  previously rejected as a comparator.
- Described officially as a *"stone band shell with **natural acoustics**"* —
  i.e. the shell itself is the reinforcement concept.
- The City's Use Policy (rev. 2025-11-20) states: **"Users must provide their
  own equipment."**
- The pavilion contains a **keyed, lockable room** (policy requires returning
  keys to the Recreation Department; refers to "this room").
- Operating envelope: **2-hour limit, must end by 9:30 p.m.**, max 2 uses per
  calendar month on non-sequential days, **$120 resident / $200 non-resident**,
  no admission charge without City Clerk licensing, dual Police + Recreation
  approval, and a **discretionary noise standard with no dB limit**.

**Field observation (project owner, ~July 2026, from a passing vehicle):**
- **Permanently mounted light fixtures on metal arrays — a pipe grid or truss —
  fixed to the underside of the pavilion roof.**
- This is recorded in `site_config.json` under
  `stage_infrastructure.stage_lighting` with its own basis class,
  `field_observation`. It is **not** measured and **not** published: no fixture
  count, type, circuiting, control position, or dimming capability is
  documented anywhere.

**The unresolved conflict.** A permanent ceiling rig and "users must provide
their own equipment" are both credible. The likeliest reconciliation is that
the **city owns the lighting** while performers supply **PA and backline** —
the "natural acoustics" framing points the same way. But the policy text does
not distinguish lighting from sound, and no source enumerates what is
installed. **Treat the lighting/sound package as UNRESOLVED.** One phone call
to the Charlevoix Recreation Department (**231-547-3253**) would close it.

**Not found anywhere** (full list in `SOURCES.md`): capacity/occupant load,
stage dimensions, sound-system spec, lighting schedule, electrical service
(amps/circuits/shore power), any technical rider, dB limits, load-in or
dressing-room detail, and the architect of the 2007 rebuild.

## Data limits — read before using these numbers

1. **The pavilion contaminates the bare-earth DEM.** The band shell is *not*
   removed from this nominally bare-earth DTM: it reads as a **~6–7 ft mound**
   (593.3 ft at the roof apex against a 586.6 ft surrounding apron). **No
   stage-deck height, deck size, or ground elevation beneath the shell may be
   taken from this DEM.** This is the same covered-structure limitation that
   disqualified Vail — but here it affects only the stage footprint, while the
   seating sector is open sky and cleanly resolved.
2. **Stage dimensions are the weakest numbers in the set.** The roof fully
   occludes the deck in every available overhead image. Frontage and depth are
   both given as **40 ft, range [30, 51]**, bounded above by the OSM roof
   circle and below by an assumed ~5 ft overhang. There is **no published
   dimension to cross-check against**. Do not treat these as measured.
3. **1 m DEM cannot resolve terrace risers.** Imagery shows ~5–6 turf bands;
   the DEM smooths them into a continuous ramp. Terrace count stays
   `inferred_imagery`; rake and rise stay `measured_dem`. No row-level or
   C-value conclusion may be drawn from this DEM.
4. **Capacity is null, deliberately.** No figure exists; it was not
   back-computed from bowl area.
5. Fan and radii are measured about an **inferred** stage-front anchor.
6. Like the other comparators, Odmark **cannot choose** Petoskey's stage
   azimuth or resolve Rule 9 — and being a circular band shell, it is less
   able to than either existing comparator.
7. The ADA notes here are an **imagery-inferred route concept pending
   civil/code detailing**, not a compliance ranking of the venue.

## What this changes / does not change

- **Does not change** any Petoskey design decision, Scenario E acceptance, or
  the open Rule 9 stage question. Nothing in the accepted baseline was
  modified; the two pre-existing comparators are byte-identical.
- **Supports**, with a second Michigan waterfront data point, that a
  covered-stage / open-air-hillside / water-backdrop civic venue is normal
  practice in this region and climate.
- **Flags** that Petoskey's 35 ft stage-front-to-row-1 gap is now the largest
  of *four* venues (Odmark and Meijer both sit at 10 ft, SB at 27 ft). The
  comparator set continues to say intimacy would tolerate *closer*, not
  farther.
- **Adds an operations precedent** worth having in front of the client: a
  comparable municipal venue runs on a 9:30 p.m. curfew, a 2-hour slot limit,
  a ~$120–200 use fee, and a discretionary (not numeric) noise standard.

## Next step to close the stage-infrastructure gap

Call Charlevoix Recreation Dept, 231-547-3253, and ask:
(1) does the pavilion have a house lighting rig, and is it available to users;
(2) is there a house PA, or is "natural acoustics" the whole plan;
(3) what electrical service is at the stage (amps/circuits);
(4) is there a stated occupancy for the pavilion or the East Park hillside;
(5) stage deck dimensions.
Answers (1)–(2) would resolve the documented conflict above; (5) would replace
the weakest inferred numbers in this comparator with published ones.

## Reproduce

```
.venv/bin/python scripts/comparators/fetch_comparator_dem.py
.venv/bin/python scripts/comparators/fetch_imagery.py
.venv/bin/python scripts/comparators/extract_osm_geometry.py
.venv/bin/python scripts/comparators/render_diagnostics.py
.venv/bin/python scripts/comparators/extract_sections.py
.venv/bin/python scripts/comparators/fit_bowl_arcs.py
.venv/bin/python scripts/comparators/extract_metrics.py
.venv/bin/python scripts/comparators/render_section_overlay.py
.venv/bin/python scripts/comparators/audit_comparators.py
```

Note: `render_comparator_board.py` additionally requires the gitignored,
regenerable Petoskey raster `dem/proposed_grade_1ft.tif`, which is absent from
a fresh checkout (rebuilding it needs the source LAZ tiles and the PDAL CLI).
`render_section_overlay.py` was added here to give the cross-venue comparison
without that dependency.
