# ADA route alternatives — designed alignments and preferred concept

**Date:** 2026-06-12 · **Stage 2** of the ADA rebuild (stage 1 = rejection +
solver feasibility, `docs/ADA_REBUILD.md`).
**Engine:** `scripts/design_ada_routes.py` · **Outputs:**
`vectors_geojson/ada_route.geojson` (hierarchy + alternatives + landings),
`vectors_geojson/route_corridors.geojson`,
`analysis/ada_rebuild/ada_validation.json`.
**Label everywhere:** *ADA-compliant route concept pending civil/code
detailing.*

## 1 · From solver artifact to designed path

Stage 1's Dijkstra corridors proved feasibility but read as pathfinding
artifacts: 55–79 sharp turns per route at 1.2-ft mean segments. Stage 2
converts each corridor into a designed alignment: line-of-sight
rationalization inside the exact legal mask, length preserved where the
drop needs it, corners built as curves (legality-checked fillets), swale
crossings consolidated to single engineered spans, landings at rise
intervals and designed elbows.

| route (class) | length | grade / profile | turns before → after | landings |
|---|---|---|---|---|
| arrival → cross-aisle (public primary) | 365 ft | 4.2% **sloped walk** | 57 → 3 | 3 pads |
| park → floor (public primary) | 246 ft | 2.1% **sloped walk** | 22 → 7 | 3 pads |
| arrival → floor (alt A leg) | 330 ft | 7.5% ramp runs | 79 → 3 | 11 |
| cross-aisle → egress (secondary) | 440 ft | 3.8% sloped walk | 55 → 2 | 1 |
| floor → egress (secondary) | 428 ft | 6.2% ramp runs | 61 → 5 | 13 |
| cluster + service connectors | 11–15 ft | level | — | — |

Design-profile rule: ≤5% = accessible **sloped walk** (no landings/handrails
required by ADAAG); 5–8.33% = **ramp runs** with landings every 30 in of
rise. Both preferred public arrivals are sloped walks — no ramp structures
on the primary experience. Smoothness gates: ≤12 deliberate turns/route and
minimum tangent runs of 1.5 path widths between perceptible (≥15°) turns;
all routes pass.

## 2 · Three alternatives

| | **A — east rim primary** | **B — south perimeter** | **C — hybrid (PREFERRED)** |
|---|---|---|---|
| concept | Petoskey St arrival serves both levels | E Mitchell St side as access + egress | east street arrival → cross-aisle; **west park-edge low arrival → floor** |
| total length | 1,164 ft | 896 ft | 1,508 ft |
| max design grade | 7.5% (ramp to floor) | 6.2% | **6.2%, and both primary arrivals ≤4.2% walks** |
| landings | 15 | 14 | 20 |
| deliberate turns | 8 | 7 | 17 |
| disturbance (corridors) | ~7,730 sq ft | ~5,430 sq ft | ~10,280 sq ft |
| swale crossings | 3 | 2 | 4 (culvert ≤12 ft; one 9 ft) |
| treatment-cell conflict | 0 ft | 0 ft | 0 ft |
| worst detour ratio | 9.0 | 7.1 | 9.0 (floor access **4.2** via park) |
| weakness | floor reached only by a 7.5% ramp stack from the street side | single arrival side; cross-aisle far from Petoskey St crowds | largest footprint (it builds both arrivals) |

## 3 · Detour honesty (flagged, not hidden)

Desire lines are straight-line distances; the able-bodied stair path is
shorter still. Every accessible pair exceeds the 3.0 social-equity flag —
**inherent to a ~33% bowl**, and the ratios are reported, not smoothed over:

| served pair (preferred C) | desire | route | ratio |
|---|---|---|---|
| east arrival → cross-aisle | 52 ft | 365 ft | **7.1** ⚑ |
| park edge → floor | 59 ft | 246 ft | **4.2** ⚑ |
| east arrival → cross-aisle wheelchair cluster | 43 ft | 381 ft | **9.0** ⚑ |
| park edge → floor wheelchair cluster | 45 ft | 260 ft | **5.8** ⚑ |

Mitigations in C: the accessible path from the east IS the general
pedestrian promenade (everyone walks it — shared, not segregated); the
park-edge walk is the *most pleasant* floor arrival on site, not a service
alley. The flagged future refinement: an **integrated aisle-ramp study**
(ramp within the seating fan) is the only way to cut the cross-aisle ratio
materially; carried as an open design question, not attempted here.

## 4 · Corridors (`route_corridors.geojson`)

Widths: public primary 8 ft · secondary 6 ft · distribution 8 ft · service
12 ft. Per corridor: terrain cross-slope (median/p90/max), bench-cut
estimate, and flags — **benching required** on all hillside routes (p90
cross-slopes 29–37%), **edge protection** on every flank route,
**handrails/guards** on the two ramp-profile routes, retaining walls NOT
indicated (max bench cut < 3 ft). Built cross-slope ≤2% depends on the
benching — pending civil detailing.

## 5 · Hierarchy and the south/service questions

- **public primary:** east arrival walk + park-edge floor walk (C).
- **secondary egress:** both legs to the south rim crest. The south
  connection is REAL — E Mitchell Street's boundary is ~54 ft beyond the
  crest node — so it stays *public secondary*, not emergency-only.
- **distribution:** short cross-aisle / floor cluster connectors.
- **service:** `route_service_to_stage` (floor → stage right shoulder at
  the 612.5 datum, zero treatment-cell contact) is **performer/service
  access only** — excluded from the public topology graph, drawn dashed
  orange, hidden by default in the viewer. A performer reaches the stage
  via park edge → floor → stage shoulder without touching the treatment
  cell.
- **maintenance/landscape:** the schematic rim promenade loop in
  site_context remains a future landscape path; no ADA claim attaches.

## 6 · Floor datum

All floor-side design profiles target the **canonical 612.5 ft** event-floor
datum. The proposed-grade raster still reads 609.65 there (concept-tier
floor not yet graded in) — carried as a reported conflict, never silently
rerouted to the lower treatment-cell datum.

## 7 · Recommendation

**Adopt C (hybrid) as the preferred ADA concept**, with A's
arrival→floor ramp retained as a drawn alternative leg (hidden by default):

1. Both primary arrivals are ≤4.2% sloped walks — no ramp structures, no
   handrail corridors on the main experience.
2. Floor access detour drops from 13.7× (east ramp stack) to 4.2× via the
   park edge.
3. Accessible and general arrival share the same promenades on both sides —
   the least segregating configuration available on this terrain.
4. Costs: largest corridor footprint (~10,280 sq ft) and 4 declared swale
   crossings; envelope re-emission required on adoption.

**Remaining civil/code gaps** (unchecked, listed in
`ada_validation.json:unchecked_code_details`): clear widths, landing
dimensions, turning radii, handrails/guards, edge protection details,
clear floor space, companion seat dimensions, surface FSS, built cross
slope, §221 dispersion counts, winter operations — plus the integrated
aisle-ramp study above.

## Reproduce

```
.venv/bin/python scripts/rebuild_ada_routes.py     # stage 1: feasibility
.venv/bin/python scripts/design_ada_routes.py      # stage 2: design
.venv/bin/python scripts/build_human_scale_refs.py
.venv/bin/python scripts/build_viewpoints_and_events.py
.venv/bin/python scripts/build_truth_package.py
.venv/bin/python scripts/audit_in_situ_package.py
```
