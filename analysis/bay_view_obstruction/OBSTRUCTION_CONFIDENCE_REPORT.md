# Bay-View Obstruction — Confidence-Banded Validation Report

Generated 2026-06-27.
Scope: confidence assessment of the evidence already in hand.
No design changes, no reruns, no scene edits in this pass.

---

## Confidence bands used

| Band | Definition |
|---|---|
| **High** | Tested against authoritative geometry; reproduced by ≥2 independent checks; numeric margins recorded |
| **Medium** | Tested in one authoritative source; missing live-scene or independent confirmation |
| **Low** | Plausible; based on screenshots, assertions, stale layers, or unverified context |
| **Indeterminate** | Not measured |

---

## Claim table

| # | Claim | Current confidence | Evidence already supporting it | Missing evidence | Test needed to raise confidence | Max confidence after test | Design decisions may rely on this? |
|---|---|---|---|---|---|---|---|
| 1 | DEM-only terrain obstruction is correct by row/section | **Medium** | DEM in EPSG:6494 ft, same CRS as treads; Z range 588–662 ft consistent with site; 1 ft pixel; tread elevations from canonical Scenario E pipeline (commit 676b43c) | No survey benchmark comparison; no spot-check of ray profiles against section plots; no recorded clearance margin per ray | Check DEM Z against ≥3 survey-grade control points; plot ray profiles at 2–3 representative rows; record eye-elev / silhouette-angle / horizon-dip / clearance for each | **High** (if DEM benchmarks pass and spot-checks match) | **Yes** — first-acceptable-row conclusions (east/bend r11, south r6) drive seating-band discussions |
| 2 | Stage does not obstruct the bay view | **Medium** | Stage core at az 254–308° from all seat positions; bay corridor is 318–342°; bend section is tightest (core 10–18° outside corridor); stage right shoulder NW corner reaches az ~340° from bend r1 but subtends −2.1° elevation angle — well below terrain silhouette (+1–2°) at that azimuth; stage deck at 612.5 ft is 2.3–22 ft below seated eye across all rows; `blocks_bay_view=False` asserted in scene canon | Stage geometry is provisional (Rule 9 OPEN); no explicit raycast against stage polygon geometry — only DEM used; no stage elements confirmed absent above 612.5 ft deck; only flat-deck geometry assumed | Include stage polygon geometry in raycast; for each bay-corridor ray (318–342°, 2° step) from each seated eye point, test intersection with every stage surface polygon extruded to its highest declared element; record minimum clearance | **High** if clearances confirmed positive with current flat deck; drops to **Medium** if any Rule-9 refit candidate adds vertical elements above deck | **Yes** — used to assert bay view is uncompromised by the stage |
| 3 | Live UE scene is not visually contaminated by stale/provisional stage or bad context geometry | **Low** | HEIGHT_AUDIT_SUMMARY.md (parallel MCP audit) confirmed city massing actors at correct heights; 3 legacy bay proxies (ctx_bay_water_plane, ctx_shoreline_proxy, ctx_distant_horizon_band) confirmed bVisible=false; ctx_city_massing Z envelope 176–287 m matches LiDAR DSM | No enumeration of ALL visible actors by current bVisible state; no confirmation that provisional stage actors are not doubled or misregistered; audit camera was above the rim (196 m / 644 ft), not from within the bowl; no UE-native raycast from seated eye points | Enumerate all actors in active level with bVisible=true; classify each as adopted / provisional / placeholder / context / stale; run UE linecasts from ≥3 seated eye points across 318–342° at 2° steps; compare hit actors and distances to DEM-only results | **Medium** (actor-hit classification added; still not High without survey ground-truth on context mesh origins) | **Yes** — any review presentation from the UE scene implicitly claims this |
| 4 | Non-terrain context (city, harbor, canopy) does not materially add obstruction | **Indeterminate** | HEIGHT_AUDIT_SUMMARY.md: W/NW buildings at or below bowl rim (190–199 m); Beards Brewery (az ~348°, roof 199 m / 653 ft) is 6° outside the 318–342° corridor; harbor structures at bay water level; Little Traverse Hist. Soc. (az ~327°, roof 184 m / 604 ft) is just inside the lower corridor bound and has not been ray-tested from seated rows | No layered raycast separating terrain / stage / city / trees / harbor contributions; foreground tree band (az 315–320) explicitly excluded from DEM and not separately modelled; no per-layer blocked-% delta by row and azimuth | Run 4-pass layered raycast: (a) terrain only, (b) +stage, (c) +city massing, (d) +trees/harbor; produce delta table blocked-% by (row, section, azimuth) per layer | **High** for layers with accurate geometry; **Medium** if trees rely on canopy estimates rather than measured heights | **Yes** — cannot state "bay view acceptable" for rows 6–10 without the tree-band contribution |
| 5 | The suspicious W/NW building is real and correctly placed | **Medium** | HEIGHT_AUDIT_SUMMARY.md (parallel MCP + OSM + LiDAR): Police Dept 1,119 m² az ~299° roof 190 m base–terrain −0.39 m; Hist. Soc. 631 m² az ~327° roof 184 m on grade; Beards Brewery 551 m² az ~348° roof 199 m on grade; "domination" effect is the hidden bay water plane (bVisible=false), not height inflation; confirmed by Google Maps showing open water where UE renders land | No floor-level seating-bowl camera showing labelled buildings; Hist. Soc. (az 327°) inside the 318–342° corridor has not been ray-tested from mid/upper seats; no photogrammetric or field survey | Check Hist. Soc. footprint against the corridor from mid/upper seats; produce labelled plan-view and a seated-camera screenshot with actors named; compare roof elevation to terrain-rim silhouette angle from representative rows | **High** if seated capture and plan both confirm on-grade placement at correct az; remains **Medium** if only overhead evidence exists | **Low** — UE visual impression matters for presentations; does not affect DEM analysis |

---

## Scope of the existing "valid" claims

The terrain-rim DEM analysis uses the correct datum, CRS, and tread geometry.
Its conclusions are reliable at planning grade within that scope:

> **Medium confidence: DEM-only terrain obstruction results are valid for bare-earth
> planning-grade analysis. East/bend first-acceptable row = 11. South first-acceptable
> row = 6. These numbers will not change unless the DEM or Scenario-E tread elevations
> are revised.**

The stage non-obstruction claim is geometrically well-supported by measured azimuths
and elevations, but depends on the provisional flat-deck assumption holding:

> **Medium confidence: the current provisional stage deck does not obstruct the
> bay-view corridor from any seated row. Basis: stage az 254–308° from seats vs.
> corridor 318–342°; deck 2–22 ft below seated eye; stage right shoulder nearest
> point 10° outside the corridor even from the tightest bend-section front row.
> This drops to Low if any Rule-9 refit adds vertical elements above 612.5 ft.**

Everything involving the live UE scene, context layers, or canopy is Low or Indeterminate:

> **Low confidence: live UE visual obstruction is clean.**
> **Indeterminate: city/canopy/harbor delta contribution to obstruction.**

---

## Priority order for closing evidence gaps

| Priority | Gap | Effort | Unblocks |
|---|---|---|---|
| 1 | DEM benchmark check (3 survey control points) | Low | Terrain claim → High |
| 2 | Stage polygon included in raycast; clearance margins recorded | Low–Medium | Stage claim → High (current deck) |
| 3 | Foreground tree band modelled as separate raycast pass | Medium | Resolves canopy delta for transition rows 6–10 |
| 4 | UE actor enumeration + bVisible audit + seated-eye linecasts | Medium | UE scene claim → Medium |
| 5 | Labelled plan-view + seated camera for W/NW buildings | Low | Hist. Soc. corridor question → High |

---

## What design decisions MUST NOT rely on current evidence

- **"Bay view acceptable" for rows 6–10** must not be stated without qualification
  until the foreground tree band (az 315–320) is separately modelled. Those rows
  are in the DEM-marginal zone (south r6 = 90% clear DEM-only; east r8 = 18% clear)
  where moderate canopy could push blocked-% substantially higher.
- **Stage non-obstruction cannot be carried forward for any Rule-9 refit** that adds
  vertical elements without re-running the stage-inclusive raycast.
- **UE review renders must not be presented as evidence of an unobstructed bay view**
  until the live scene actor audit (claim 3) is complete. Unverified context actors
  or unhidden proxies would contaminate the visual without appearing in the DEM results.
