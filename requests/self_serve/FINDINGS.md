# Self-serve data pulls — findings (2026-07-06)

Seven no-contact public-data pulls run per `outbox/SEND_CHECKLIST.md`. Raw payloads and
re-runnable scripts live in this directory. **One finding invalidates the framing of the
staged request letters — see §1. All sends are ON HOLD.**

Observed facts are labeled **[fact]** (returned by an authoritative service, file on disk);
interpretations are **[inference]**.

---

## 1. ⛔ SITE IDENTITY / OWNERSHIP — the letters describe the wrong place

- **[fact]** The repo's own design footprint (`basin_footprint.geojson`, EPSG:6494) sits at
  lon −84.958, lat 45.374 — the downtown block bounded by E Lake St, E Mitchell St,
  Petoskey St, and US-31. That is **not Bayfront Park**, which is the shoreline park
  northwest of Lake St (~600 m away, across the rail corridor).
- **[fact]** The parcel under the bowl centre is **PID 52-19-06-227-016, 2.01 ac, owner
  PETOSKEY GRAND LLC (PO Box 676), property class 202 (commercial vacant), zoning COP B-2**
  (Emmet County parcel service `gis.emmetcounty.org`, `emmet_parcels_park.json`).
- **[fact]** EGLE lists the same block as Part 201 site **"Petoskey Ford/Former Petoskey
  Pointe," SiteID 24000048** (45.3743, −84.9583), plus UST facility 00035252 ("Petoskey Ford
  Building," 200 E Mitchell) and a 2006 brownfield award "Petoskey Pointe Project — NW corner
  of Mitchell & Petoskey Streets (11 parcels 52-19-06-227-xxx)" (`egle_layers.json`).
- **[fact]** Press history: block demolished 2006, excavated 2007 for the Petoskey Pointe
  hotel/condo project, financing collapsed with "the hole dug but no foundation"; ownership
  passed through Northwestern Bank → Elias Amash (2013) → Petoskey Grand LLC (2018).
  ([Northern Express](https://www.northernexpress.com/news/feature/article-6229-experts-weigh-in-on-petoskeys-big-hole/),
  [Northern Mich~Mash](https://northernmichmashpreserve.weebly.com/the-hole-the-pit-pdp.html))
- **[inference]** The project's "Petoskey Pit" is the Petoskey Pointe excavation. The
  depression is neither natural nor a quarry nor historic fill — it is a **2007 construction
  excavation** into the former Petoskey Ford block. This effectively answers dossier C-5
  (depression origin) at desktop level and explains why the 1970s-era soil survey maps
  undisturbed East Lake sand over it.
- **Consequences for the staged letters** (all inherited the "Bayfront Park … west portion …
  Bear River mouth … City of Petoskey ownership" description, which appears as far back as
  `executive_summary.md`):
  - 08 (Parks & Rec inquiry): **wrong premise** — the site is not parkland; MNRTF/master-plan
    questions do not apply. Counterparties are Petoskey Grand LLC (owner), City Planning/DDA,
    and the City for ROW/storm/zoning.
  - 03/04/06 (survey/geotech/wetland field work): on **private land** — cannot mobilize
    without owner permission; premature to solicit.
  - 05 (Phase I ESA): prior Phase I/II/BEA documents almost certainly exist from the
    2005–2007 development era — obtain them (EGLE FOIA / city records) before commissioning
    new work.
  - 01/02/07 (records requests): still valuable, but site descriptors must be rewritten to
    the downtown block / PID 52-19-06-227-016, and 07 should cite SiteID 24000048 directly.
- **Key unknown for Sam:** whether to engage the private owner (and how) — that is a strategy
  decision, not a data gap.
- **Clarification (Sam, 2026-07-06):** the geography was always known — downtown pit,
  separated from Bayfront Park by US-31, ownership assumed city-or-commercial/underdeveloped.
  The "bay" component is a **design objective** (the upper rows' imperfect bay view, which the
  layout maximizes), not site adjacency. The error was confined to the letters' site
  descriptions (and `executive_summary.md`); the genuinely new facts are the owner's identity
  and the Part 201 status.

## 2. FEMA NFHL (flood) — gap closed at mapped level

- **[fact]** Countywide FIRM effective 2022-06-01 (panels 26047C0427D/0339D). At the bay
  frontage: coastal **VE and AE zones with static BFE 589.0 ft**; an unnumbered Zone A
  (no BFE) along the Bear River corridor; the downtown blocks are Zone X (`fema_nfhl.json`).
- **[inference]** The pit (floor ~609, spill 618) is far above the 589 coastal BFE and outside
  mapped SFHAs; flood elevation is not a design driver for the bowl itself. The 589 BFE is
  now the authoritative bay-side flood number for any outfall work (supersedes the
  "flood elevations UNKNOWN" gap).

## 3. NRCS soils — CN/HSG bracket narrowed (mapped, not field-verified)

- **[fact]** Bowl centre and north rim map as **East Lake loamy sand, 0–6% (EaB), HSG A,
  somewhat excessively drained**; NW area maps Emmet sandy loam (EmC, HSG B). "Borrow pits"
  (Bp) and "Made land" (Ma) units exist within the wide AOI (`nrcs_soils.json`,
  `soils_at_points.json`).
- **[inference]** Native material is sandy/HSG-A — the infiltration-friendly end of the
  CN 61↔85 / 2.0↔0.0 in/hr brackets. BUT the mapping predates the 2007 excavation; the pit
  floor exposes cut faces and possible construction debris/fill, so field infiltration tests
  (C-1) remain required. Survey-grade caveat: SSURGO here is 1:15,840-class mapping.

## 4. NLCD 2021 impervious — E-3 closed at mapped level

- **[fact]** Wide AOI mean impervious **63%** (p50 66, p90 94); the pit-block vicinity reads
  ~78% at 30 m (`nlcd_2021_impervious_wide.tif`).
- **[inference]** Any storm run-on from surrounding downtown blocks is high-runoff (CN ≈
  90s for impervious fractions) regardless of soil; the piped-network question (FOIA 01)
  stays the controlling unknown for inflow.

## 5. EGLE environmental layers — pre-answers most of request 07

- **[fact]** Within the wide AOI: **8 Part 201 sites** (incl. the site block itself; also
  Petoskey Municipal Well Field & "Lake St WF Dev" at 200 W Lake St, Former Petoskey Railroad
  at 319 State St — dry cleaner/foundry/gas/manufacturing, MDOT Railroad Parcels, Hookers
  Cleaners, Fochtman Motor, 900 Emmet St), **15 UST facilities**, **3 brownfield awards**,
  **3 restrictive-covenant polygons** (Bay Buick, Petoskey Manufacturing @ 200 W Lake,
  E-Z Mart). (`egle_layers.json`)
- **[fact]** Wellhead protection: the "PETOSKEY (Northman & Lime Kiln)" Type 1 provisional
  WHPA intersects the broader area but **does not cover the bowl centre** (`whpa.json`).
- **[fact]** Part 303 state wetland inventory: **no polygon over the bowl**; the only nearby
  feature ("hydric soils only") centroids at (−84.9645, 45.3693), ~600 m SW near the Bear
  River corridor (`part303_polygon.json`). NWI shows only the bay (lake) and a riverine
  segment.
- **[fact]** Critical dunes, high-risk erosion zones, environmental areas, local wetland
  ordinances: **0 features** in the AOI — dossier **F-5 closed**.
- **[inference]** The EGLE FOIA (07) should now be a *targeted* request for the SiteID
  24000048 / FacilityID 00035252 files (Phase I/II, BEA, due-care, closure docs) plus NPDES
  outfall records — far narrower and faster than the drafted broad sweep.

## 6. Sanborn maps — Phase-I-grade history is one click away

- **[fact]** LOC holds nine digitized Petoskey Sanborn volumes: 1885, 1890, 1896, 1901, 1907,
  1913, 1919, 1929, 1950 (`loc_sanborn_petoskey.json`; items sanborn04149_001…009).
- **[inference]** These will document the pre-Ford uses of block 227 (and the rail/industrial
  waterfront). High value for the site-history record; sheets not downloaded yet.

## 7. MNRTF / LWCF grant search — mooted by §1

- **[fact]** MNRTF publishes grant history by county (michigan.gov/dnr, "MNRTF Grant Total by
  County" PDF — bot-blocked for direct download; search results show City of Petoskey awards
  for Skyline Recreation Area and Winter Sports Park, no Bayfront/downtown hit).
- **[inference]** Grant-conversion research applies to parkland; the site is private, so this
  thread is not decision-relevant unless the strategy shifts to actual Bayfront Park land.

## 8. Emmet County Register of Deeds online — manual step remains

- **[fact]** The online search (rod.emmetcounty.org) requires account registration; not
  attempted (account creation is an outward-facing action). Ownership was instead confirmed
  via the county parcel service (§1). The RoD chain-of-title for PID 52-19-06-227-016 (and the
  2005–2018 conveyances) is the remaining lookup, either via a registered account or
  request 02 (rewritten).

---

## Status of the seven checklist pulls

| Pull | Status | Gap movement |
|---|---|---|
| NRCS soils | ✅ done | C-1/E-3 bracket narrowed (mapped HSG A sand; field tests still required) |
| NLCD impervious | ✅ done | E-3 closed at mapped level (63% wide-AOI) |
| FEMA NFHL | ✅ done | flood-elevation gap closed (coastal BFE 589.0; site in Zone X) |
| EGLE mappers | ✅ done | 07 pre-answered & sharpened; F-5 closed; site is Part 201 |
| Sanborn/LOC | ✅ indexed | 9 volumes located; sheets not yet pulled |
| MNRTF/LWCF | ◐ mooted | site is private, not grant-encumbered parkland |
| County RoD online | ✖ manual | needs account; ownership confirmed via parcel service instead |
