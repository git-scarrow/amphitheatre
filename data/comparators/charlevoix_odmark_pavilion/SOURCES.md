# Clarence Odmark Performance Pavilion, East Park — source notes

Site: East Park, 400 Bridge Street, Charlevoix, MI 49720, on Round Lake.
Also called the "Odmark Band Pavilion" (OSM) and the "East Park Performance
Pavilion" (City of Charlevoix).

Benchmark role: **nearest-typology comparator** — a municipal northern-Michigan
waterfront venue with a covered stage, open-air hillside seating, a water
backdrop, and free civic programming. It is the only one of the three
comparators that shares Petoskey's *program* (small-city public waterfront
concert venue) as well as its landform idea. It is much smaller than Petoskey
and has **no published capacity**, so it constrains geometry and stage
infrastructure, not seat count.

## Terrain (measured basis)

- Product: **USGS 1 Meter 16 x63y502 MI_CharlevoixCounty_2018_A18** (3DEP 1 m DEM)
  - URL: https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/MI_CharlevoixCounty_2018_A18/TIFF/USGS_1M_16_x63y502_MI_CharlevoixCounty_2018_A18.tif
  - LiDAR project: MI_CharlevoixCounty_2018_A18 (acquired 2018, published
    2024-05-22) — same Michigan statewide program family as the Petoskey 2015
    LiDAR and the Meijer MI_31Co_Kent_2016 collection.
  - CRS: EPSG:26916 (NAD83 / UTM 16N, m); vertical NAVD88 m.
  - Discovery: TNM Access API query archived at
    `data/comparators/_sources/tnm_charlevoix.json` (queried 2026-07-21;
    exactly one 1 m product covers the site).
  - **Post-dates the venue.** The pavilion was rebuilt in 2007 and the park
    reopened in 2008 (planning.org, below); LiDAR flown 2018 → the surface
    reflects current geometry.
- Clip: `dem/dem_clip_1m.tif` (600 × 600 m) via
  `scripts/comparators/fetch_comparator_dem.py`; provenance in
  `dem/provenance.json`.

### What the DEM does and does not support

- **Supports (measured):** bowl rise (10.9 ft row 1 → top), average rake
  (17.1 %), local rake range (16.8–20.9 %), fan angle (75.1°), row-1 and
  top-of-seating radii, water-surface elevation (Round Lake, flat return at
  579.4 ft NAVD88), apron/plaza elevation (586.6–586.7 ft), rim promenade
  (597.4–598.1 ft).
- **Does NOT support:** individual terrace risers (1 m grid smooths ~5–6
  imagery-visible turf bands into a continuous ramp), and — critically —
  **anything under the pavilion roof**. The band shell is *not* removed from
  this nominally bare-earth DTM: it reads as a ~6–7 ft mound (593.3 ft at the
  roof apex against a 586.6 ft surrounding apron). No stage-deck height, deck
  size, or ground elevation beneath the shell may be taken from this DEM.
  This is the same covered-structure limitation that disqualified the Vail
  comparator, but here it affects only the stage footprint — the seating
  sector is open sky and is cleanly resolved.

## Geometry anchors (inferred basis)

- OSM pavilion footprint: **way 1112264619** (`amenity=theatre`,
  `building=shelter`, `name=Odmark Band Pavilion`). Raw way+nodes archived at
  `data/comparators/_sources/osm_way_odmark.json`; area Overpass response at
  `_sources/overpass_charlevoix.json` (query in `_sources/op_chx.txt`);
  Nominatim lookup at `_sources/nom_odmark.json`.
- The footprint is a **circle**, not a rectangle: 22 nodes, all radii
  7.0–8.3 m (mean 7.75 m → 15.5 m / 51 ft diameter). Consequence: unlike the
  Meijer lens-canopy, **the audience azimuth cannot be derived from footprint
  orientation.** It was taken instead from the DEM fall line — the sole
  monotonic rising sector is az 275–345, centred az 310 — and cross-checked
  against imagery, which shows the terrace bands in exactly that sector.
  Audience faces the reciprocal, **az 130 (SE)**, ±10°.
- Esri World Imagery clips (`imagery/`): 0.5 m site clip and a ~0.3 m close-up
  (`esri_closeup.png`). Mosaic, acquisition date unknown → everything
  digitized from it is INFERRED. Attribution: Esri, Maxar, Earthstar
  Geographics, USDA, USGS, AeroGRID, IGN, GIS User Community.
- **Stage dimensions are the weakest numbers here.** The roof fully occludes
  the performance deck in every available overhead image, so no deck edge can
  be digitized. Frontage and depth are both given as 40 ft with range
  [30, 51], bounded above by the OSM roof circle and below by an assumed ~5 ft
  overhang. There is **no published stage dimension for this venue** to cross-
  check against (see failed searches). Do not treat these as measured.

## Published facts (with sources)

| fact | value | source |
|---|---|---|
| rebuild year | pavilion rebuilt 2007; park reopened 2008 for Venetian Festival | https://www.planning.org/greatplaces/spaces/2009/eastpark.htm |
| project cost | "$11 million park and marina reconstruction" | planning.org (same) |
| description | "the Clarence Odmark Pavilion, a newly reconstructed, stone band shell with natural acoustics and built-in hillside seating" | planning.org (same) |
| recognition | APA Great Public Spaces designation, 2009 | planning.org (same) |
| adjacent build-out | children's water fountain ($200,000 DDA TIF), trout pond, 65-slip marina, street-level viewing plaza, public restrooms | planning.org (same) |
| address / contact | 400 Bridge Street; Recreation Dept 231-547-3253 | https://www.charlevoixmi.gov/facilities/facility/details/Odmark-East-Park-Pavilion-1 |
| **equipment** | **"Users must provide their own equipment."** | Use Policy rev. 2025-11-20, https://www.charlevoixmi.gov/DocumentCenter/View/408 |
| curfew | use limited to 2 hours, must end no later than 9:30 p.m. | DocumentCenter/View/408 |
| repeat use | max 2 uses per calendar month, not on sequential days | DocumentCenter/View/408 |
| fee | $120 resident / $200 non-resident, non-refundable | DocumentCenter/View/408 |
| noise standard | discretionary — whether the event is "likely to generate noise that would adversely affect people who are not attending the event"; **no dB limit** | DocumentCenter/View/408 |
| keyed room | users must "return all keys to the Recreation Department"; policy refers to "this room" → an enclosed lockable space exists in the shell | DocumentCenter/View/408 |
| ticketing | no admission charge or gratuity solicitation without City Clerk business licensing | DocumentCenter/View/408 |
| approval | dual sign-off, Chief of Police + Recreation Dept | https://www.charlevoixmi.gov/DocumentCenter/View/407 |
| attendance field | request form asks "expected number of attendees" — applicant-supplied, **no city cap stated** | DocumentCenter/View/407 |
| programming | ~50 performances annually in East Park; city "Live on the Lake" series | https://visitmichiganupnorth.com/stories/summer_concert_series_charlevoix_michigan_east_park · https://charlevoixmi.gov/533/Live-on-the-Lake-Concert-Series |
| dedication | "Clarence 'Odie' Odmark / Charlevoix Band Director / 1946 - 1975" | https://www.hmdb.org/m.asp?m=98090 |
| **pavilion cost** | "Removal of Existing Band Shell, Fish Pond, and Restroom Building - Construction of a new pavilion/performance building, **with amphitheater seating** ($1,490,642)", listed under 2005 | https://www.charlevoixmi.gov/315/Accomplishments (verified verbatim 2026-07-21) |
| park / marina cost | East Park Construction $2,610,597; Marina Construction $4,829,500 | same |
| **building services** | "Both the Harbormaster's Building and Odmark performing arts pavilion are **heated and cooled with geothermal energy; motion sensors control building lighting**" | https://www.planning.org/greatplaces/spaces/2009/eastpark.htm (verified verbatim 2026-07-21) |
| design team | pavilion architect **Mark Buday Architect PLLC** (Harbor Springs MI); acoustical consultant **Wallmark Consulting** (Traverse City); civil/structural Performance Engineers Inc.; M/E Peter Basso and Associates; marina designer United Design Associates | 2005-07 "East Park & Marina Improvements" project plan sheet — **partially corroborated only** (Buday confirmed as a Harbor Springs architect, now Buday+Kruzel; no independent source ties the firm to this building) |
| funding | Michigan State Waterways Commission grant assistance (marina); **no** MNRTF grant for the pavilion | plan sheet credit block; cross-checked vs "Previous DNR Grants" table, https://www.charlevoixmi.gov/DocumentCenter/View/131 |

## Field observation (a basis class of its own — NOT published, NOT measured)

- **Permanently mounted light fixtures on metal arrays (a pipe grid or truss)
  fixed to the underside of the pavilion roof.** Observed by the project owner
  from a passing vehicle, ~July 2026. Undated, unmeasured, no photograph in
  hand. Recorded in `site_config.json` under
  `stage_infrastructure.stage_lighting` with basis `field_observation`.
  - This is evidence that a permanent lighting rig **exists**. It does not
    establish fixture count, type, circuiting, control location, dimming, or
    who is permitted to use it.
  - **It conflicts with the published record.** The City's Use Policy says
    users must provide their own equipment. The likeliest reconciliation is
    that the city-owned rig covers *lighting* while performers supply
    *PA/backline* — the "stone band shell with natural acoustics" language
    points the same way — but the policy text does not distinguish them.
    **Treat as UNRESOLVED** until confirmed by site visit or by calling the
    Recreation Department (231-547-3253).

## Failed searches (logged per audit requirement)

Every item below was searched for and **not found**. None of these may be
inferred or estimated downstream.

- **Capacity / occupant load — CONFIRMED ABSENT after two independent search
  passes.** Pass 1 (2026-07-21) checked the facility page (its "Feature
  Overview" block is empty), the Use Request Form, the Use Policy,
  visitcharlevoix.com, michigan.org and the APA write-up. Pass 2 (2026-07-21,
  ~32 tool calls) went after the document classes most likely to carry a
  number and also came back empty:
  - **City Parks & Recreation Master Plan facility inventory** — the strongest
    lead, since Michigan DNR requires these for grant eligibility. Full PDF
    text of **two** editions read (2017–21 draft Recreation Inventory Table 4
    via charlevoix.recdesk.com, and Chapter 4 at
    charlevoixmi.gov/DocumentCenter/View/131). East Park entries list
    amenities only — band shell, seating areas, interactive fountain — with
    **no numeric capacity**.
  - **MNRTF / State Waterways Commission grant records** — no capacity stated;
    the "Previous DNR Grants" table (1972–2010) shows no grant tied to the
    pavilion.
  - **Michigan Municipal League** placemaking material (mml.org,
    mmlfoundation.org) — Charlevoix coverage exists, no capacity figure.
  - **DDA / council accomplishment ledger** — yielded cost, not capacity.
  - **Charlevoix County building-safety / fire-code occupant load** — no
    published document found.
  - **Regional press** (Charlevoix Courier, Petoskey News-Review) on Venetian
    Festival and Live on the Lake — venue use confirmed, **no crowd-size
    figures reported**.
  - **Design firm portfolio**, **Wikidata Q34871967**, **RecDesk facility page**
    (returns "Organization Not Found") — nothing.
  Capacity is recorded as `null` with an explicit `capacity_basis` explaining
  the absence — **not** back-computed from bowl area. Treat the absence as a
  finding: this is a municipal park facility with no fixed seats, and the city
  pushes the attendance estimate onto the applicant.
- **Stage dimensions** — no width, depth, height, or shell aperture published
  anywhere.
- **Sound system** — no house PA is documented. The only published signal is
  "users must provide their own equipment."
- **Stage lighting specification** — no fixture schedule, circuit count, or
  control description. NOTE the second pass turned up *counter*-evidence
  rather than confirmation: the APA page states "motion sensors control
  building lighting", which describes architectural/service lighting, not a
  theatrical rig. See the field-observation section above — the question is
  now sharper but still open.
- **Electrical service** — no amperage, circuit count, outlet, or shore-power
  detail. (Geothermal HVAC is published, so substantial service exists; its
  capacity remains undocumented.)
- **Technical rider / tech-spec sheet** — none published; the venue is a
  municipal park facility administered by the Recreation Department, not a
  presenting house, and appears never to have produced one.
- **Decibel limits / noise-ordinance cross-reference** — only the subjective
  standard quoted above.
- **Load-in access, dressing rooms, restrooms at the pavilion itself.**
- ~~**Designer / architect of the 2007 rebuild**~~ — **RESOLVED (partially) in
  pass 2**: a 2005–07 project plan sheet names Mark Buday Architect PLLC with
  Wallmark Consulting as acoustical consultant. Moved to the published-facts
  table above; still only partially corroborated.
- **Pavilion construction or dedication date** — the HMDB marker honours
  Odmark's 1946–1975 tenure as band director; it carries no structure date.
  (The DDA ledger lists the build under **2005**, while the APA write-up says
  the park reopened **2008** — consistent with a multi-year project, but no
  single source states a pavilion completion date.)
- DocumentCenter search (`?searchPhrase=pavilion`, 46 results) surfaced no
  further Odmark documents. IDs 2568 / 3543 / 3816 are the **beach** pavilions
  (Ferry, Depot, Lake Michigan Beach) — a different facility class; ID 2338 is
  a duplicate of an older policy revision.
- hmdb.org blocks automated fetchers (Cloudflare); marker text was retrieved
  via a reader proxy.

## Processing chain

Same command sequence as the other two comparators:

```
.venv/bin/python scripts/comparators/fetch_comparator_dem.py
.venv/bin/python scripts/comparators/fetch_imagery.py
.venv/bin/python scripts/comparators/extract_osm_geometry.py
.venv/bin/python scripts/comparators/extract_sections.py
.venv/bin/python scripts/comparators/fit_bowl_arcs.py
.venv/bin/python scripts/comparators/extract_metrics.py
.venv/bin/python scripts/comparators/audit_comparators.py
```

## Known limits

- 1 m DEM cannot resolve the terrace risers; terrace count is imagery-inferred.
- The pavilion structure contaminates the bare-earth surface (see above).
- Round Lake reads as a flat 579.4 ft water return.
- Fan and radii are measured about an **inferred** stage-front anchor (the
  circular footprint gives no orientation of its own).
- No capacity exists, so the Petoskey↔Charlevoix comparison is a geometry and
  operations comparison only. Do not derive a Petoskey seat count from it.
