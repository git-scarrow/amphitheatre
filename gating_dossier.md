# Gating Dossier — "Before You Can Build"

**Petoskey Pit amphitheater + civic event garden — Bayfront Park, Petoskey, Emmet County, MI.**

This dossier lists every field investigation, data acquisition, permit, and approval that
must be completed before the planning-grade design in `/package` can be advanced to
**PE-stamped design** and then to construction. It is compiled from the project's running
`DATA_GAPS.md` plus the standard pre-development scope for a public-assembly facility next to
a Great Lakes shoreline and a restored coldwater fishery.

**Nothing in `/package` is field-verified.** Each item below carries an **Owner** (the party
or discipline responsible), a **Purpose** (the decision it unblocks), and the **package
output it gates**. Priority: **⛔ decision-critical** (could change the design), **● required**
(needed to stamp/permit), **○ confirm** (assumption to validate, low likelihood of changing
the answer).

---

## A. Datum reconciliation

| ID | Item | Owner | Purpose / what it unblocks | Gates | Pri |
|---|---|---|---|---|---|
| A-1 | ✅ **CLOSED 2026-06-06.** NAVD88 ↔ IGLD85 offset confirmed via NOAA VDatum at site coords (45.3746°N, 84.9582°W): **NAVD88 = IGLD85 + 0.162 ft**. Prior assumption (+0.40 ft) was within the ±0.3 ft band but high by ~0.24 ft; no design decisions change. Use 0.162 ft for all future bay/IGLD85 tie-ins. | — | — | — | ✅ |

## B. Boundary & topographic survey (design control)

| ID | Item | Owner | Purpose / what it unblocks | Gates | Pri |
|---|---|---|---|---|---|
| B-1 | **Boundary & ALTA-type survey** — parcel lines, easements, ROW, utilities of record. | Licensed surveyor (PLS) | Confirms the work area is on City land; **establishes whether the NW 589-ft low and the NE outlet route are on-parcel or need an easement** (currently UNKNOWN, decision-critical for the gravity outlet). | Layout footprint (`01_layout`), outlet routing (`07_stormwater`) | ⛔ |
| B-2 | **Design-grade topographic survey** (ground shots + breaklines, 1 ft or better) tied to NAVD88 & state plane. | Surveyor (PLS) | Replaces the LiDAR DEM as the design control surface. LiDAR is ±~0.5–1 ft and 2015-vintage; seating geometry, the focal point, cut/fill, and the spillway profile all shift on real grade. | Everything geometric: `01`–`06` | ● |
| B-3 | **Bathymetric / shoreline & OHWM survey** of the bay/Bear-River edge near the outfall. | Surveyor (PLS) | Sets the legal discharge point and whether Part 301/325 (below OHWM) is triggered. | Outlet/spillway (`07`), permitting (F) | ● |

## C. Geotechnical investigation

| ID | Item | Owner | Purpose / what it unblocks | Gates | Pri |
|---|---|---|---|---|---|
| C-1 | **Soil borings + infiltration tests** (basin bottom + seating fill zones). HSG, profile, infiltration rate. Design currently **brackets CN 61↔85 and infiltration 2.0↔0.0 in/hr**. | Geotechnical engineer (PE) | Determines whether the WQ cell infiltrates (no underdrain) or ponds (underdrain required), the runoff curve number, and pond drawdown. The **0.0 in/hr "tight" case drives the floor**. | `07_stormwater` floor & treatment-train sizing | ⛔ |
| C-2 | **Seasonal high groundwater (SHGW)** — monitoring wells, ≥1 season of observation. Bay-tied SHGW is non-binding (12–28 ft below the bottom) **but a local perched table near 609 ft would force a permanent pool** and could reset the floor. | Geotechnical engineer (PE) | Confirms the event-floor elevation and whether a liner/permanent pool is needed. **Likely the single elevation-setting field input.** | `07` floor recommendation; `02` grading | ⛔ |
| C-3 | **Slope-stability analysis of the steep SE/SSE wall.** Tie-in/ramp cuts reach **6–14 ft over ~0.083 ac**; flagged as **structural retaining walls**, not earth slopes — currently **qualitative**. | Geotechnical + structural PE | Decides retaining-wall type/cost vs. graded slope; sets the 3:1 side-slope assumption or replaces it. | `02_grading` §4, ADA Route B, `01_layout` | ⛔ |
| C-4 | **Depth to bedrock (Petoskey limestone)** within the excavation footprint. | Geotechnical engineer (PE) | Affects excavation cost/method and infiltration feasibility. | `02` earthwork, `07` infiltration | ● |
| C-5 | **Is the depression natural or filled?** Borings + historical research to determine origin and fill character. | Geotechnical engineer + environmental consultant | A filled/industrial depression changes settlement, infiltration, contamination risk, and excavation handling — and ties directly to the Phase I/II below. | `02`, `07`, environmental (D) | ⛔ |

## D. Environmental site assessment (industrial/rail history)

| ID | Item | Owner | Purpose / what it unblocks | Gates | Pri |
|---|---|---|---|---|---|
| D-1 | **Phase I ESA** (ASTM E1527). Bayfront Park's history includes **mills, dams, quarry rock, a metal plate, and a former rail depot** — classic recognized-environmental-condition flags. | Environmental professional (EP) | Identifies RECs; determines whether soils/fill are suitable for excavation, reuse as berms, and infiltration. | Earthwork reuse (`02`), infiltration (`07`), permitting | ● |
| D-2 | **Phase II ESA** (likely, pending Phase I) — soil/groundwater sampling for contamination. | Environmental consultant / lab | Governs **off-site disposal vs. on-site reuse of the ~480 CY surplus + ~1,700 CY rim cut**, dewatering discharge limits, and worker safety. Contamination near a coldwater fishery is high-scrutiny. | `02` earthwork balance, `07` dewatering/ESC | ● |

## E. Municipal storm-sewer GIS / drainage study

| ID | Item | Owner | Purpose / what it unblocks | Gates | Pri |
|---|---|---|---|---|---|
| E-1 | **City of Petoskey storm-sewer GIS / as-builts + any Bayfront Park drainage study** — inlet/manhole locations, pipe inverts & sizes, outfalls to the bay/river, drainage-area boundary. | City of Petoskey DPW / GIS; civil PE to interpret | **The single input that could change the answer.** Bare-earth LiDAR cannot see piped flow. Surface run-on is 0.29–2.09 ac, but back-calc shows **~19 ac of piped drainage would fill the bowl to its spill.** If the City network routes a large area into the pit, the WSEL, floor, spillway width, and outlet must be re-derived from a real inflow hydrograph. | `07` floor/outlet/spillway; emergency-spillway freeboard | ⛔ |
| E-2 | **Storm-sewer tie-in point & capacity** near the rim (preferred over the Ø15-in buried outfall through the 618-ft rim). | City DPW; civil PE | Decides outfall method (pipe vs. tie-in), legal discharge location, and ~1,700 CY rim-cut earthwork. | `07` outlet works, `02` earthwork | ● |
| E-3 | **Land-cover / impervious layer** (NLCD 2019/2021 or City planimetric) for the contributing area. | Civil PE / GIS | Firms up the runoff coefficient / curve number (now parametric). | `07` runoff sizing | ○ |

## F. Permitting scan (assume all trigger; confirm at design)

| ID | Item | Owner | Purpose / what it unblocks | Gates | Pri |
|---|---|---|---|---|---|
| F-1 | **EGLE post-construction stormwater** review (discharge to/near the bay/Bear River). | Civil/water-resources PE → EGLE | Approves the permanent treatment train & discharge. | `07` | ● |
| F-2 | **NREPA Part 91 — Soil Erosion & Sedimentation Control** permit (>1 ac disturbance within 500 ft of the lake/tributary). Emmet County enforcing agency. | Civil PE / SESC designer → Emmet Co. | Authorizes earth change; ESC is the first line of coldwater protection. | `02`, `07/esc_notes.md` | ● |
| F-3 | **NREPA Part 303 — Wetland** delineation & permit (bowl-bottom treatment cell + bay proximity). | Wetland scientist → EGLE | Field delineation required **before grading the wet cell**; may constrain the cell footprint. | `07` treatment cell, `01` layout | ⛔ |
| F-4 | **NREPA Part 301 (Inland Lakes & Streams) / Part 325 (Great Lakes bottomlands)** — only if outlet/discharge works approach the OHWM. | Civil PE → EGLE | Authorizes work at/below the OHWM at the outfall. | `07` outfall (with B-3) | ● |
| F-5 | **Shoreland / High-Risk Erosion Area (HREA) & critical-dune** check for the bayfront. | Civil PE / EGLE Coastal | Determines if HREA/critical-dune setbacks apply to the NW (bayward) flank. | `01` layout, NW flank | ○ |
| F-6 | **MS4 / NPDES** — Construction General Permit (NOI/CGP, ≥1 ac) + post-construction obligations. | Civil PE → EGLE | Construction-phase discharge authorization. | `02`, `07/esc_notes.md` | ● |
| F-7 | **Bear River coldwater-fishery protections** — thermal & sediment load limits for any discharge. | Water-resources PE; EGLE/DNR Fisheries | Sets thermal/sediment performance the treatment train must meet (infiltrate-first, shade, dissipate). | `07` coldwater strategy | ● |

## G. City Parks master-plan amendment & public process

| ID | Item | Owner | Purpose / what it unblocks | Gates | Pri |
|---|---|---|---|---|---|
| G-1 | **Parks & Recreation master-plan amendment** to include the amphitheater/event-garden program at Bayfront Park (and protect any grant-funded park status, e.g. MNRTF). | City of Petoskey Parks & Rec; Planning Commission; City Council | Establishes the project as an approved public use; required for most state grants and for capital programming. | Whole project authorization | ● |
| G-2 | **Public engagement / stakeholder process** (neighbors, waterfront users, accessibility & arts community). | City; planning consultant | Surfaces program, capacity, noise, lighting, and parking concerns that feed back into layout, seat count, and event scheduling. | Program → `04`/`05` capacity, `06` event timing | ● |
| G-3 | **Operations & program calendar** (typical curtain times, event types). | Owner / operator | Confirms the **20:00–21:30 solstice glare window** actually coincides with shows and sizes the glare-control investment. | `06_sun_view` recommendation | ○ |

## H. Design-assumption confirmations (carry into PE design)

These are stated planning assumptions in `/package`; each must be confirmed or replaced at
design stage. They are unlikely to change the concept but will change quantities/details.

| ID | Assumption to confirm | Owner | Gates |
|---|---|---|---|
| H-1 | Freeboard **1.0 ft** over the 100-yr WSEL (vs. EGLE/local public-assembly standard). | Civil PE | `07` floor |
| H-2 | Sightline **C-target 90 mm**, seated eye **3.94 ft**, seat widths 18/22 in, 3 ft tread, 18% aisle/vom. | Theater/venue + accessibility | `04`/`05` capacity |
| H-2b | **Code occupant load** (Michigan Building Code / IBC assembly — egress/aisle/exit capacity, fixed vs. movable seats, standing/lawn) and **operational event cap** (per-event, fire-marshal/permit). The package's ~2,190/~1,790 is a **geometric planning estimate only** — neither has been computed. | Architect + code official (AHJ); operator + fire marshal | `05` seat count → permitted capacity |
| H-3 | ADA ramp footprints, **≤2% cross slope**, landings, handrails (alignments now schematic; 8.33% running slope is correct). | Civil PE / accessibility | `05` ADA, `01` |
| H-4 | Earth side slopes **3:1** and the **30-ft tie-in apron / retaining line** (depends on C-1/C-3). | Geotechnical + civil PE | `02` |
| H-5 | Earthwork **shrink/swell, topsoil strip/respread, unsuitable-material handling** — none applied to the ±500 CY balance. | Civil PE / estimator | `02` |
| H-6 | Outlet **orifice Ø2 in / weir @611.0 / Ø15-in pipe** and a **routed (dynamic) hydrograph** to replace the static closed-basin route once the rating is set. | Water-resources PE | `07` |
| H-7 | Spillway **weir C 2.6**, crest 612.0, L 25–30 ft; rim-cut ~1,700 CY (±30%) — refine on a surveyed profile. | Civil PE | `07` |
| H-8 | **Glare-grove species & mature form** (salt/bay-tolerant native deciduous, 18–26 ft, limbed-up) and **stage backdrop-wing dimensions** (16–24 ft, WNW face). | Landscape architect + architect | `06` |
| H-9 | East-garden bench geometry/count/extent (designed in Stage 5 as placeholders). | Landscape architect | `01`, `02` |

---

## Critical path (the four that can move the design)

1. **E-1 storm-sewer GIS / drainage study** — could reset inflow, WSEL, floor, spillway.
2. **C-2 seasonal high groundwater** — could reset the floor / force a permanent pool.
3. **C-1 infiltration** + **C-3 SE-wall stability** — set treatment regime and retaining cost.
4. **B-1 boundary + B-3 shoreline/OHWM** + **F-3 wetland** — set what is buildable and where it can discharge.

Everything else refines quantities and secures permits. **No construction figure in this
package may be used for bidding or building until the ● and ⛔ items are resolved and the
hydrology, hydraulics, geotechnical, and structural design are PE-stamped.**
