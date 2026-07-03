# Orchestra event-floor re-emission — against the adopted deck edge

Rule 9 stage-footprint cleanup. Mechanism: baked into the emitter
`scripts/build_in_situ_geometry.py` (`_adopted_stage_footprint()` subtracts the
adopted P_opt footprint from the derived floor); the `material_zones/event_floor`
mirror follows via `build_site_context.py`. (An earlier standalone
`reemit_orchestra_floor.py` was folded into the emitter and removed so the normal
pipeline — not an out-of-band patch — produces the re-emitted floor.)
Patched **1** feature in `bowl_zones.geojson` (`orchestra_event_floor`) and
**1** in `material_zones.geojson` (`event_floor`, identical mirror).

## Before → after (minimal subtraction of the adopted P_opt footprint)

| metric | before | after |
|---|--:|--:|
| floor area (sf) | 2149.4 | 1925.8 |
| **deck ∩ floor (sf)** | **100.3** | **0.0** |
| **full footprint ∩ floor (sf)** | **221.2** | **0.0** |
| treads ∩ floor (sf) | 0.009 | 0.009 |
| centroid shift (ft) | — | 4.79 |
| disconnected parts | 1 | 3 |

The adopted deck/shoulder overlap is driven to ~0. The floor now begins at the
adopted footprint edge; its row-1-side extent is unchanged (area drops only by the
removed deck bite, 2149.4→1925.8 sf).

## No adopted-quantity delta (the floor is schematic/concept)

| pathway | carries a quantity? | effect of re-emission |
|---|---|---|
| volume (`earthwork.csv`) | No — floor absent, 0 CY | none |
| capacity (`terrace_treads`) | No — not seating, 0 seats | none (treads untouched: ∩ 0.009 sf) |
| drainage | No — not a swale | none |
| ADA (`design_ada_routes.py`) | indirect — floor **centroid** places one concept arrival node | node nudges **4.79 ft**; concept-tier, no CY/slope-compliance change (Phase-B ADA re-run confirms) |

## Scope

Surgical in-place patch of the two floor features; the full emitter was NOT run
(it currently also deletes the live `ada_route.geojson` — see
`analysis/repro_tickets/emitter_deletes_ada_route.md`). Surrounding stage zones
remain INHERITED (Rule 9 OPEN) pending the full Phase-B stage re-emission.
`bowl_zones` + `material_zones` are truth_package sources → refresh the package
hashes after this patch.

## Phase-B ADA re-run — confirms no downstream effect (2026-07-03)

Ran the full ADA pipeline against the re-emitted floor: stage 1
`rebuild_ada_routes.py` (preserved the re-emitted orchestra; TOPOLOGY/CONFLICTS/
SLOPES OK) → stage 2 `design_ada_routes.py` → stage 3 `design_constructed_ada.py`
(restores the C-vs-D `concepts` block that stage 2 alone omits).

| check | before (old floor) | after (re-emitted) |
|---|---|---|
| **160 boolean compliance gates** | — | **0 changed (all identical)** |
| seats displaced (D1/D2/D3/C) | 158 / 121 / 95 / 0 | **158 / 121 / 95 / 0 (identical)** |
| dignity scores | 67 / 79 / 67 / 16 | identical |
| worst detour ratios | 6.76 / 5.79 / 6.76 / 8.95 | identical |
| GOVERNING concept | C_naturalistic_promenade | **C (identical)** |
| adopted route network | — | Hausdorff **1.33 ft**, length Δ **−0.3 ft** |

The *only* movement is ±1–5 CY on the **non-adopted Concept-D alternative** cut/fill
estimates (D1 cut 126.4→131.2, D2 fill 162.1→159.7, D3 cut 90.2→91.7) — the expected
consequence of the 4.8 ft arrival-node nudge, on carried alternatives, not the
governing C route (0 CY). No adopted ADA quantity, seat count, or compliance gate
changed. Comparator audit: **PASS, 0/0**. truth_package hashes refreshed.
