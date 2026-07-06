# DATA_GAPS.md — running list of missing inputs & labelled assumptions

Planning-grade project. Field values are NOT fabricated. Each gap below must be filled
before the corresponding decision is made. Items are tagged by the stage that needs them.

## ⛔ 2026-07-06 — SITE IDENTITY CORRECTION + public-data pulls (see requests/self_serve/FINDINGS.md)

- **⛔ The site is NOT Bayfront Park and NOT City-owned.** The design footprint
  (`basin_footprint.geojson`) is the downtown block at 200 E Lake St (E Lake / E Mitchell /
  Petoskey St / US-31): **PID 52-19-06-227-016, 2.01 ac, owner PETOSKEY GRAND LLC, class 202
  (commercial vacant), zoning COP B-2** (Emmet Co. parcel service). The "Bayfront Park …
  Bear River mouth … City ownership" framing in `executive_summary.md` and `requests/` is
  **wrong** and must not be propagated. (Sam clarification: the geography was always known —
  downtown pit across US-31 from Bayfront Park; "bay" = the upper rows' view the design
  maximizes. Only the letters' text was wrong.) The `requests/` package was rewritten around
  the true site same day: records requests (01/02/07) and a City Planning inquiry (08) are
  sendable; field-work RFQs (03–06) are blocked on owner access / records-first.
- **✅ Depression origin (dossier C-5) answered at desktop level:** the bowl is the 2007
  **Petoskey Pointe** construction excavation (block demolished 2006, excavated 2007,
  financing collapsed; owner chain → Petoskey Grand LLC 2018). Not natural, not a quarry,
  not historic fill. Field characterization of pit-floor debris/fill still needed.
- **⚠ The block is an EGLE Part 201 site** ("Petoskey Ford/Former Petoskey Pointe,"
  SiteID 24000048) with UST facility 00035252 and a 2006 brownfield award. Prior Phase I/II /
  BEA documents almost certainly exist — request before commissioning a new ESA.
- **✅ Flood elevations (Stage 2 gap) closed at mapped level:** 2022 countywide FIRM — coastal
  VE/AE **BFE 589.0 ft** at the bay frontage; Zone A (no BFE) on the Bear River; the site
  blocks are Zone X. Pit floor 609 is ~20 ft above the coastal BFE.
- **◐ HSG / land cover (Stage 2/3 parametric gaps) narrowed at mapped level:** bowl maps as
  East Lake loamy sand **HSG A** (SSURGO; mapping predates the excavation); NLCD 2021 wide-AOI
  impervious ≈ **63%**. Field infiltration tests remain the gate for the 0.0-in/hr case.
- **✅ Dossier F-5 closed:** no critical-dune, high-risk-erosion, or environmental-area layers
  intersect the AOI; bowl is outside the Petoskey WHPA.
- **✅ Part 303 mapped baseline:** no state wetland-inventory polygon over the bowl (nearest
  "hydric soils only" polygon ~600 m SW near the Bear River). Field delineation still decides.

## Datums / georeferencing
- **[Stage 1] ✅ CLOSED. NAVD88↔IGLD85 offset confirmed via NOAA VDatum (2026-06-06).**
  At site coordinates 45.3746°N, 84.9582°W: **NAVD88 = IGLD85 + 0.162 ft**.
  Prior planning assumption was +0.40 ft (±0.3 ft) — actual is +0.162 ft, within band but
  assumption was high by ~0.24 ft. No design decisions change. Bay water level in NAVD88
  is ~0.24 ft lower than previously assumed (e.g., IGLD85 581.4 ft → NAVD88 581.56 ft,
  not 581.80 ft); bowl-to-bay separation increases slightly to ~27.5 ft. Carry 0.162 ft
  for any future elevation tie-ins to bay or IGLD85 benchmarks.
- **[Stage 1] Brief mislabeled units as "US survey feet."** Data is **international feet**
  (Michigan SPCS exception). Resolved/documented; negligible for z, but anyone reusing
  absolute easting must treat coordinates as intl ft (else ~39 ft shift). 

## Reference / prior-analysis reconciliation  — RESOLVED
- **[Stage 1] ✅ CLOSED. Reference archive obtained** (`petoskey_pit_lidar_analysis_archive/`,
  copied from MacBook). All CSVs/PNGs present. Our pipeline reproduces
  `expanded_aoi_metrics.csv` to **0.01 ft on every percentile** (see
  `metrics/reference_reconciliation.csv`). Reference method = point-based percentiles over
  EPT box + 150 ft buffer. (Note: these files live in a chat attachment on claude.ai, NOT in
  Project knowledge — the claude-projects MCP cannot export attachment bytes, only transcript
  text; manual copy was required.)
- **[Stage 1] ✅ CLOSED. AOI footprints now defined.** Expanded = EPT box + 150 ft buffer
  (822.97 × 644.52 ft). Tight/central-bowl = EPT box (523 × 352 ft). Both reproduced.

## ⚠ Design-integrity finding (carry into every later stage)
- **The expanded-AOI relief/slope/area figures are INFLATED** by the off-site NW/north-edge
  589 ft low (at E 19532693.76, N 751107.83), which is ~1 m outside the proposed work area
  and truncated at the AOI boundary. **Use the TIGHT central bowl for all design numbers:**
  floor ≈ 607 ft, p10 ≈ 610 ft, usable relief ≈ 32 ft (r10–95), seating-arc relief ≈ 22–24 ft.
  Do NOT propagate "66.9 ft relief," "80%+ slopes," "1.08 ac below 602," or "40+ terraces."
- **NW 589 ft low — on-parcel & reachable?** Floor 607 is ~18 ft above it; it is the only
  gravity-drainage candidate but is itself a closed pocket (would become a detention/
  infiltration basin, not a true outlet) and is edge-truncated (true extent unknown). UNKNOWN
  whether on the parcel or reachable by easement. **Decision-critical for stormwater.**

## Hydrology / water (Stage 2+ — stormwater & groundwater strategy)
- **Seasonal high groundwater elevation** under the bowl — UNKNOWN. This likely sets the
  stage/event-floor elevation. Needs monitoring wells / borings + seasonal observation.
- **Soil infiltration rate / hydrologic soil group** — UNKNOWN. Needed for infiltration
  feasibility, bottom treatment cell sizing. Needs field infiltration tests + NRCS soils.
- **Depth to bedrock / Petoskey limestone** — UNKNOWN. Affects excavation & infiltration.
- **Existing storm network** (inlets, outfalls to bay/Bear River, pipe inverts) — UNKNOWN.
- **Bear River / bay flood elevations** (base flood, high-lake-stage) in NAVD88 — UNKNOWN.

## Environmental / regulatory
- **Wetland presence (Part 303)** in/near bowl bottom — UNKNOWN; assume review triggered.
- **EGLE stormwater + soil erosion (Part 91)** thresholds vs disturbed area — TBD.
- **Soil/sediment contamination** history (former park/industrial fill) — UNKNOWN.
- **Bear River coldwater fishery thermal/sediment limits** for any discharge — TBD.

## Stage 2 — stage/storage & pour point (NEW)
- **✅ Closed-bowl pour-point analysis done** (`scripts/stage_storage.py`,
  `README_stage_storage.md`). Central closed sink: **floor 609.12 ft, spill 618.04 ft,
  depth 8.92 ft, 0.93 ac, capacity 5.69 ac-ft** (NAVD88 intl ft). Pour point on the
  **north rim** (E 19532967.2, N 750904.2), spills **toward the bay** — head to bay ≈ 36.6 ft.
- **⚠ "Floor ≈ 607" refined to 609.12 ft for hydraulic purposes.** 606.99 was the point-cloud
  min; the gridded *closed-sink* floor is 609.12 ft. Use 609.12 / spill 618.04 for any
  volumetric (storage, flood-stage, treatment-cell sizing) work.
- **⚠ Closure depends on the artifact mask.** The bowl is closed only because the bay-ward
  `<595 ft` strip is treated as a barrier. The 618 ft spill is the lowest **north-rim** saddle.
  Confirm whether, in the as-built design, the north rim is the intended overflow route and
  whether the bowl should be deliberately bermed to a higher controlled spill.
- **Spill overflows toward Bear River / the bay** — the sensitive receiving water. Controlled
  outlet location, water-quality treatment, and thermal/sediment control must be designed for a
  north/bayward discharge path. **Decision-critical for the stormwater outlet design.**
- Requested floor band 604–616 ft sat entirely below the 618 spill (604–609 below the floor →
  zero storage); curve extended to spill. No fabricated values introduced.

## Stage 2 — watershed delineation & outlet (NEW)
- **⛔ DECISION-CRITICAL: City of Petoskey storm-sewer GIS / as-builts + any Bayfront Park
  drainage study.** The bare-earth LiDAR DEM **cannot resolve piped flow**, yet in this
  urban bluff setting curb inlets and the municipal storm network almost certainly control
  both (a) run-on *into* the pit and (b) the *overflow path* to Little Traverse Bay / the
  Bear River mouth. Need: inlet/manhole locations, pipe inverts & sizes, outfall locations
  to the bay/river, and the storm drainage area boundary near Bayfront Park. Without it the
  contributing area and discharge point below are **surface-only approximations**.
  Request from City of Petoskey DPW / GIS and EGLE (any permitted outfalls).
- **Surface contributing area = a RANGE, not a number.** Natural pre-fill run-on **≈ 0.29 ac**
  (pit is near-closed); depression-conditioned topographic catchment **≈ 2.09 ac** (includes
  adjacent graded micro-catchments). Cross-check: Stage-2 wide 5 ft DEM gives bowl floor
  **609.20 / spill 618.05 ft NE**, corroborating Stage-1 stage-storage (609.12 / 618.04) to
  ~0.08 ft. Confirm with the storm-network data before sizing inflow.
- **Land cover (impervious vs pervious) — NOT INGESTED.** No NLCD/impervious or City
  planimetric layer pulled. Need NLCD 2019/2021 % impervious (or City impervious polygons)
  for the contributing area to estimate the runoff coefficient / curve number.
- **Outlet trace leaves LiDAR at the bay shoreline** (~1450 ft NE→N from spill, 618→580.5 ft,
  ending where ground returns stop over open water). The point where surface flow enters the
  storm network upstream of the shore is **unknown** — depends on the requested storm GIS.

## Stage 3 — stormwater sizing & event-floor band (NEW)
- **Floor recommended at 612.5 ft (band 612.0–613.0 NAVD88)** = 100-yr,24-hr WSEL
  (611.31 ft, worst soil) + ≥1 ft freeboard. Bottom stays ~609.1 ft as a treatment cell.
  Driver `scripts/storm_sizing.py`; memo `stage3/floor_recommendation.md`.
- **✅ Rainfall sourced.** NOAA Atlas 14 Vol 8 v2, 24-hr PDS mean depths at site
  (45.3733/−84.9550): 10-yr 3.05 in, 100-yr 4.81 in, 500-yr 6.29 in. WQ storm = 1.0 in
  (EGLE first-flush). No longer a gap.
- **⛔ Curve number (land cover/impervious) — PARAMETRIC, still unfilled.** Used CN 61
  (sandy/HSG-A) and 85 (tight/HSG-C-D) to bracket. Confirm with NRCS Web Soil Survey
  HSG + NLCD/City impervious for the contributing area (also flagged in Stage 2).
- **⛔ Basin infiltration rate — PARAMETRIC, pending borings.** Used 2.0 in/hr (sandy)
  and 0.0 (tight/lined/high-GW). The 0.0 case drives the floor. Needs field infiltration
  tests + HSG. Determines whether a permanent pool / liner is needed and pond drawdown.
- **⛔ Seasonal high groundwater near the bowl floor — UNKNOWN, partially de-risked.**
  Bay-tied SHGW (581.4 + mound) is non-binding (12–28 ft below the 609.1 bottom). BUT a
  *local perched table* on a clay lens near 609 ft would force a permanent pool — still
  needs monitoring wells/borings to rule out.
- **⛔ DECISION-CRITICAL (carried from Stage 2): storm-sewer GIS / piped run-on.** The
  static route is surface-only. Back-calc: ~19 ac of external drainage at the 100-yr storm
  (CN 85) would fill the bowl to the 618-ft spill, vs the 0.29–1.16 ac surface estimate. If
  the City network routes a large area into the pit, the WSEL/floor must be re-derived from
  the real inflow hydrograph. **This is the single input that could change the answer.**
- **Freeboard standard (1.0 ft assumed)** — confirm EGLE / local detention & public-assembly
  freeboard requirement at design stage.
- **Controlled-outlet invert not yet set.** Closed-basin route is conservative and valid only
  until an outlet structure is designed; then re-route dynamically (orifice/weir stage-discharge).
- **Datum offset (carried)** still unconfirmed (NAVD88 = IGLD85 + 0.40 ±0.3 ft) — affects the
  groundwater-separation and head-to-bay numbers; confirm via NOAA VDatum/NGS.

## Geometry / design (later stages)
- ✅ Bowl rim / spill-point (pour-point) analysis COMPLETE (see Stage 2 above); supersedes the
  Stage-1 elevation-threshold north-edge mask proxy for *defining* the closed depression.
- Slope/aspect recompute on a canonical AOI (south/SE arc steepness, east-slope gentleness).
- Solar/evening-sun and bay-view sightline analysis for the south/SE seating arc.

## Stage 4 — amphitheater geometry (design assumptions, planning-grade)
- **Sightline C-target = 90 mm (0.295 ft)** eye-over-eye and **seated eye height 3.94 ft
  (1.20 m)** are stated assumptions; confirm against venue program / accessibility code.
  Staggered-seating or standing-spectator C-values would change required row rise.
- **Seat width** (compact 18 in / generous 22 in), **tread depth 3.0 ft**, and **18% arc
  aisle/vom allowance** are nominal — refine with the seating product and egress design.
- **ADA ramp alignments are schematic.** Run counts and 8.33% running slope are sized
  correctly, but exact footprints, **≤2% cross slope**, landing geometry, and handrails
  are design-phase. The bowl is a closed depression with a ~16% rim lip, so **no natural
  ADA route exists** — engineered ramps/regrading are required (confirmed from DEM).
- **Upper rows 25, 27–30 require 0.75–2.8 ft of fill** to meet sightline where the natural
  slope flattens at the rim; verify this fill is compatible with rim drainage/spill (618.04).
- **Event-floor forecourt** (612.5) implies ~1.5–2.5 ft fill over the natural pan SE of the
  stage; the stage/forecourt-to-treatment-cell grading interface is unresolved (design-phase).
- Geometry centerline az 150° and focal-point placement (+15 ft SSE of bowl centroid) are
  planning choices; a topographic survey may shift the optimal focus and fan.

## Stage 5 — finished grade & cut/fill (design assumptions, planning-grade)
- **Earth side slopes = 3:1 (33%)** for all tie-ins is a stated assumption; stable slope
  ratio depends on soil type/strength (no borings yet) and may need to be flatter (clay)
  or retained (steep SE wall). **DATA GAP: geotechnical soil strength / slope stability.**
- **30-ft tie-in apron (`D_MAX`)** = the limit of disturbance / approximate retaining-wall
  line. Beyond it existing grade is kept. The apron distance and the choice "cut slope vs.
  retaining wall" are planning assumptions to confirm with geotech + cost.
- **~20° bowl-wall slope stability (REQUIRED follow-up) — reframed.** The S/SE/E bowl wall is a
  continuous ~20° (≈35%) amphitheatre-grade rake (multi-scale DEM analysis;
  `analysis/east_flank_reality_check/REASSESSMENT_MEMO.md` §2), **not** a retaining-wall
  condition. The earlier 6–14 ft retaining figure was an artifact of the superseded narrow-fan,
  30-row `/package` geometry (fan driven straight up the slope + ADA Route B bench-cut) —
  **design vocabulary, not terrain law**. Scenario E grades access with **8.33% switchback ramps
  and landings, no walls** (max cut/fill 0.95/1.59 ft, well under the 3 ft wall trigger). What
  remains is a genuine **slope-stability check of the ~20° wall under terraced-seating loading
  and Scenario E ramp cuts** — data-gated on borings/geotech, quantitative once soils are known.
  Low (1–4 ft) seat/terrace walls, if used, are **civic design vocabulary, not emergency
  geotechnical fixes**.
- **East garden terraces** (5 benches, ENE flank az 88–122°, r 95–215 ft) were **designed
  in Stage 5** (Stage 4 left them schematic). Bench count, extent, pad elevations, and
  retaining between benches are placeholders pending a landscape program + survey.
- **ADA corridor width (10 ft) and straight-line ramp alignment** are nominal; real
  switchback footprints, landings, ≤2% cross slope, and handrails are design-phase. Route B
  benched into the steep wall is the deep-cut driver (see retaining flag).
- **Treatment-cell shaping** uses the wet-cell polygon only (bottom 609.1); the closed bowl
  is **left at natural grade** per Stage 3. Final pool/treatment grading, outlet-control
  invert, and the floor-to-cell fill interface are unresolved (design-phase).
- **Stepped seat risers** appear as near-vertical faces in the slope raster; these are
  structural step faces, not earth slopes. Terrace-edge structure/retaining is design-phase.
- **Cut/fill balance residual (~−480 CY surplus)** assumes ±~500 CY planning tolerance and
  on-site reuse of surplus (berms/mounding). A real earthwork estimate needs shrink/swell
  factors, topsoil strip/respread, and unsuitable-material handling — **none applied here.**

## Stage 6 — treatment train & outlet works (design assumptions, planning-grade)
- **Cell drawdown rate = the dominant Stage-6 unknown.** WQv drawdown (24–48 h target) and
  whether the bioretention cell needs an **underdrain** both hinge on **field infiltration
  tests + borings + seasonal-high groundwater** (already-open Stage 3 gap). SANDY → infiltrates
  in hours; TIGHT → full ponding, underdrain required. No field data yet.
- **Outlet discharge point — pipe vs. municipal tie-in.** The as-shown Ø15-in, ~467-ft buried
  outfall through the 618-ft rim is a surface-DEM solution. The **preferred** option is a
  **municipal storm-sewer tie-in**, which depends on the **storm-sewer GIS still outstanding**
  (carried from Stage 2). Connection point, pipe invert/capacity, and legal discharge location
  are unknown.
- **Piped run-on magnitude (carried, decision-critical).** The emergency spillway clears the
  surface 500-yr with 0.80 ft freeboard but loses freeboard under a ~67 cfs (~19-ac) piped
  surge. If the City network routes a large area into the pit, **widen the spillway (L=30 ft)
  and/or raise the floor** — needs the real inflow hydrograph.
- **Rim-cut earthwork (~1,700 CY) is a Stage-6 addition NOT in Stage-5's balance.** Corridor-
  difference estimate (±~30%); refine with a surveyed spillway profile. Combined site earthwork
  → ≈2,200 CY net export. Also re-check the rim-notch against slope stability (same steep-wall
  geotech gap as Stage 5).
- **Orifice Ø2 in** is clog-prone; trash rack + O&M assumed. Real sizing follows the chosen
  drawdown path (surface orifice vs. underdrain) once soils are known.
- **Part 303 wetland delineation** of the bowl-bottom treatment cell, **Part 91 SESC permit**
  (Emmet County enforcing agency), and **EGLE NPDES/CGP** coverage are all required field/permit
  steps not yet performed (see `stage6/esc_notes.md`).
- **Peak flows are rational-method brackets**, not a routed hydrograph; the static closed-basin
  WSELs (Stage 3) should be **re-routed dynamically** once the orifice/weir rating is fixed.
- **NAVD88↔IGLD85 offset (+0.40 ft)** still unconfirmed — affects any bay/groundwater tie of the
  outlet invert (carried from Stage 1/3).

## Stage 7 — Sun-path / view-glare study (added 2026-06-04)
- **Tree/canopy species & mature form** for the WNW glare grove (az 280–308°):
  need salt/bay-edge-tolerant native deciduous, ~18–26 ft mature canopy, limbed-up
  habit (block low sun, pass the under-canopy view). Growth time to effective
  height unmodeled.
- **Stage backdrop wing dimensions** (height ~16–24 ft, WNW face) are design
  targets pending architectural/structural and AV design.
- **Diffuse/sky glare and cloud frequency** not modeled — analysis is direct-beam
  geometry only. Petoskey evening cloud climatology would refine glare-hours.
- **Seated eye height (3.94 ft) and ±60° FOV** are inherited Stage 4 assumptions,
  not field-validated for this audience.
- **Event programming calendar** (typical start/curtain times) needed to confirm
  the 20:00–21:30 solstice glare window actually coincides with shows.

## Stage 8 — Package assembly & gating dossier (added 2026-06-04)
- **⛔ Deliverable package (`package/`) — SUPERSEDED.** The 2026-06-04 `package/` assembly (and
  its master index) captured the original narrow-fan, 30-row generation and is **no longer the
  governing deliverable**. Current project state is carried by
  `docs/POST_EMISSION_DECISION_MEMO.md` (the controlling statement) and the Scenario E emission
  validation (`analysis/tier_emission/TIER_EMISSION_VALIDATION.md`); the running technical record
  is this file plus `gating_dossier.md`.
- **✅ Gating dossier produced** (`gating_dossier.md`): every "before you can build" item —
  datum (A), survey (B), geotech (C), Phase I/II environmental (D), storm-sewer GIS (E),
  permitting scan (F), Parks master-plan/public process (G), and design-assumption
  confirmations (H) — each with an **owner** and **purpose**, prioritized ⛔/●/○. It
  consolidates and routes (does not replace) the open gaps listed above; this file remains the
  running technical record.
- **No new data gaps introduced by assembly.** Stage 8 created no new figures — it compiled
  existing planning-grade outputs and the disclaimer that all of them require PE-stamped
  hydrology, hydraulics, geotechnical, and structural design before construction.
