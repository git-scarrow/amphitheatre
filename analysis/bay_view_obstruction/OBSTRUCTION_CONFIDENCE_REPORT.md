# Bay-View Obstruction — Confidence-Banded Validation Report

> **REVISION 3 (2026-07-21, bay-band v2 — canopy MEASURED).** Closes the
> long-standing canopy gap (claim 4b). A first-return canopy-top layer was built
> from the USGS 3DEP EPT (`USGS_LPC_MI_13Co_Emmett_2015`) — acquisition
> **2015-05-02, LEAF-OFF** (northern Michigan deciduous leaf-out is mid-to-late
> May). Canopy silhouette is now a **measurement**, promoted into the effective
> silhouette per the owner's 2026-07-21 directive (`bay_band_v2.py`,
> `neighbor_ceiling.py`, `element_verdicts_v2.py`). Headline: **the foreground
> tree line, not terrain or the stage, is the binding bay-view occluder for the
> seated bowl — no seated row is acceptable (>=80% clear) through the canopy in
> either leaf state** (`rn_rm_table.md`, r_m = none). Leaf-on is a labeled
> crown-opacity assumption, not a measurement; summer is the operating season.
> The band top was also corrected to the far-shore waterline (`band_top_farshore.csv`,
> T2). Read-only: no geometry moved; adopts nothing (owner sign-off pending).

> **REVISION 2 (2026-06-27, scene-level evidence).** Adds the stage-polygon
> raycast, the live UE actor audit, the layered terrain/stage/city deltas, and
> a two-source (Python DEM+OSM ↔ live UE `trace_world`) cross-check. The
> Revision-1 table is preserved below the rule for traceability. Read-only:
> no geometry was moved, hidden, deleted, or relit.

---

## Revision-2 headline

**The terrain-only "first acceptable row" was optimistic for the EAST section.**
Adding the W/NW city massing (dominated by **Beards Brewery**, a real on-grade
building at 652 ft, ~75 m NNW of the east seats) occludes the NW half of the
bay corridor (az ≈ 328–342°) from the east upper rows. East rows 11–18, scored
97–100 % clear terrain-only, fall to **46–62 % clear** with city massing — i.e.
**marginal, not acceptable**. The SW half of the corridor (az ≤ 326°) stays
clear. Bend rows lose 3–10 %; south rows are unaffected (they face away from the
W/NW buildings). The **stage contributes 0.0 %** obstruction across every band.

Both the Python model and live UE raycast agree to ~1 m (az 334° → hit @ 77 m;
az 322° → clear). Evidence: `layered_obstruction.csv`,
`layered_delta_row_x_az.csv`, `section_beards_east.png`, `layered_plan_view.png`,
`UE_ACTOR_AUDIT.md`.

## Revision-2 claim table

| # | Claim | Confidence (was → now) | What was tested | What remains untested | Design reliance | Max without field survey |
|---|---|---|---|---|---|---|
| 1 | DEM terrain obstruction by row/section | Medium → **Medium-High** | Section profiles spot-checked; ray engine cross-validated against live UE `trace_world` (clear/blocked match) | DEM vertical datum vs survey benchmark (no control points checked) | Yes (bare-earth planning) | **High** (needs benchmark) |
| 2 | Stage does not obstruct the bay view | Medium → **High (scoped)** | Stage polygons added to raycast → **Δ = 0.0 % every band**; UE audit confirms exactly 3 flat stage actors, Z 612.0–612.5 ft, **no vertical shell** | Nothing for the current deck | Yes — current flat/open stage only | **High** (achieved, for current deck) |
| 3 | Live UE scene not contaminated by stale/provisional stage | Low → **Medium** | Full stage-like enumeration: 1 current stage system, **no** shell/provisional/rule9/duplicate; raycast cross-check matches | Editor visibility (`bHiddenEd`) of bay-water/horizon proxies not readable via API; runtime `bHidden=false` unreconciled with memory's `bVisible=false` | Yes (review renders) | **Medium-High** (needs component visibility read or visual confirm) |
| 4a | City massing **materially obstructs** the bay corridor (east section) | Indeterminate → **Medium-High** | Layered raycast: east upper rows 100 %→46–62 % clear; **confirmed by live UE trace @ 73–77 m** | Beards Brewery roof height is LiDAR DSM−DTM (10.4 m), not surveyed | Yes — supersedes terrain-only "row 11 acceptable" for east | **High** (needs roof survey) |
| 4b | Tree / canopy obstruction contribution | Indeterminate → **Medium (measured, leaf-off)** | Rev-3: first-return canopy-top layer from 3DEP EPT (2015-05-02 **leaf-off**); silhouette per (row, az) both leaf states; the canopy **tops the band bottom (binding occluder) for every seated row** — no row acceptable through the trees, r_m = none (`rn_rm_table.md`, `canopy_silhouette.csv`) | Leaf-ON is an assumption (crown-opacity closing, heights not raised); within-crown porosity (winter see-through) not measurable from first returns; canopy is mutable/3rd-party (Bayfront Park City land / MDOT ROW) | **Governs** the seated bay view — supersedes terrain/city "acceptable upper rows"; must carry leaf-state + occluder-set (S0/S1/S2) labels; never pass a stage element on S2 (canopy) leeway alone | **Medium-High** (leaf-off measured; leaf-on needs summer LiDAR or field survey) |
| 4c | Harbor obstruction | Indeterminate → **Low (does not obstruct)** | Harbor structures sit at/below the bay water plane (579.45 ft) | No per-structure raycast | Minor | **Medium** |
| 5 | Suspicious W/NW building is real & correctly placed | Medium → **Medium** | Two distinct things separated: (a) *visual "domination"* = Police Dept cluster + **hidden bay-water plane** (representation artifact); (b) *measured obstructor* = **Beards Brewery**, a named OSM building, base−terrain ≈ −0.09 m (on grade) | No field/photogrammetric survey; LiDAR-derived heights | Low (visual), but its height drives Claim 4a magnitude | **High** (needs survey) |

## Scoped strong claims (Revision 2)

> **High confidence (scoped): the current flat/open stage geometry does not
> materially obstruct the DEM-defined bay-view rays.** Stage raycast Δ = 0.0 %
> on every band; live UE confirms 3 flat actors at 612.0–612.5 ft with no
> vertical shell. **Invalidated if any Rule-9 refit adds vertical elements.**

> **Medium-High confidence: the W/NW city massing materially obstructs the NW
> half of the bay corridor from the EAST upper rows** (clear% 100 → 46–62),
> confirmed by two independent raycast methods. The obstructor is Beards
> Brewery (real, on-grade); magnitude depends on its LiDAR-derived roof height.

> **Medium confidence: the live UE scene is obstruction-clean of stale/
> provisional stage geometry** — exactly one stage system, no shell/duplicate —
> **but** the editor-visibility of the bay-water/horizon proxies is unconfirmed
> via the API, so "render is proxy-clean" is not yet High.

> **Medium (Rev-3): canopy obstruction is now MEASURED (leaf-off) and GOVERNS the
> seated bay view.** The 3DEP first-return canopy layer (2015-05-02 leaf-off; densest
> az 312–321 as the old finding predicted) tops the band bottom for every seated row:
> no row reaches acceptable (>=80% clear) through the tree line in either leaf state
> (best case ~54% clear at the top of the bend, leaf-off). The "acceptable upper rows"
> from terrain/city analysis is therefore contingent on trimming/removing third-party
> trees. Leaf-on (summer, operating season) is a labeled assumption, slightly worse.

## What changed for design reliance

- The east-section "bay-view acceptable from row 11" claim (terrain-only) is
  **downgraded to marginal** once city massing is included. Do not present east
  upper rows as having a clean bay view without naming the Beards Brewery
  occlusion of the NW corridor half.
- The stage is now cleared at **High (scoped)** — design discussion may rely on
  "the current flat stage does not block the bay," with the explicit Rule-9
  vertical-element caveat.
- South section remains the strongest: terrain- and city-clear from row 6.

---

## Confidence bands used

| Band | Definition |
|---|---|
| **High** | Tested against authoritative geometry; reproduced by ≥2 independent checks; numeric margins recorded |
| **Medium** | Tested in one authoritative source; missing live-scene or independent confirmation |
| **Low** | Plausible; based on screenshots, assertions, stale layers, or unverified context |
| **Indeterminate** | Not measured |

---

## Claim table — REVISION 1 (superseded by Revision 2 above; kept for traceability)

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

- **"Bay view acceptable" for ANY seated row** must not be stated as if the bay is
  actually visible: Rev-3 measures the foreground canopy (leaf-off) as the binding
  occluder — **no seated row is acceptable through the current tree line** in either
  leaf state (`rn_rm_table.md`, r_m = none). A clean seated bay view is contingent on
  trimming/removing the Bayfront Park (City) / US-31 (MDOT ROW) trees — third-party,
  mutable land the owner does not control.
- **Canopy (S2) leeway must never pass a stage element.** An element that "clears"
  only because the canopy already blocks the bay is `contingent_on_canopy` — charge it
  under S1 (durable) too.
- **Stage non-obstruction cannot be carried forward for any Rule-9 refit** that adds
  vertical elements without re-running the stage-inclusive raycast.
- **UE review renders must not be presented as evidence of an unobstructed bay view**
  until the live scene actor audit (claim 3) is complete. Unverified context actors
  or unhidden proxies would contaminate the visual without appearing in the DEM results.
