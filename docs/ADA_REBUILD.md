# ADA route network — legacy rejection and first-principles rebuild

**Date:** 2026-06-12 · **Status:** rebuilt network =
**"ADA-compliant route concept pending civil/code detailing"** (never
"ADA compliant").
**Engine:** `scripts/rebuild_ada_routes.py` ·
**Validation:** `analysis/ada_rebuild/ada_validation.json` ·
**Audit gates:** `scripts/audit_in_situ_package.py::check_ada_rebuild`

## 1 · Why the legacy layer was rejected

The 3D viewer showed the ADA-labeled geometry as disconnected squiggles
behind/left of the provisional stage. Measurement confirmed it
(`legacy_ada_rejected.geojson` carries these numbers per feature):

| legacy feature | finding |
|---|---|
| `accessible_route_A_floor` | **63% of its area inside the treatment cell**; 34.6 ft from the event floor it is named for; touches nothing |
| `ada_landing_1` / `_2` | 100% / 39% inside the treatment cell |
| `accessible_route_B_mid_row9` | crosses the south drainage swale (0.0 ft separation); stops **21.9 ft short of the cross-aisle** it is named for |
| routes A ↔ B | **115.6 ft apart** — no connection to each other, the floor, the cross-aisle, the seating, the stage, or any egress |

`Scenario_E_baseline_reemit/validation.json` reported `running_ok: true`
for both fragments because it **only ever measured slope along the
polylines**. It validated decoration, not circulation.
**That artifact is no longer treated as an ADA route validation** (its
cross-aisle band data remains valid — the cross-aisle is seating-derived
geometry, not part of the rejected layer).

## 2 · What was done

1. **Quarantine** — the 7 legacy features were removed from
   `bowl_zones.geojson` (all other features preserved) into
   `vectors_geojson/legacy_ada_rejected.geojson` with status
   `REJECTED — legacy` and per-feature rejection metrics.
   `build_in_situ_geometry.py` no longer imports the scenarioE
   ada_ramp/landing roles, so regeneration cannot resurrect them.
2. **Nodes first** — `vectors_geojson/ada_nodes.geojson`: public rim
   arrival (east|bend hinge above row 18), south rim egress (bend|south
   hinge), mid-bowl cross-aisle (622.01 datum), wheelchair clusters with
   companion seating at the cross-aisle AND the event floor, floor
   arrival, and an OPTIONAL stage-shoulder access point **classified
   service** and excluded from the public network.
3. **Routes node-to-node** — `vectors_geojson/ada_route.geojson`:
   7 routes from slope-capped Dijkstra (16-direction, ≤8.33% +0.3%
   planning tolerance) on a 5-ft-smoothed design surface over
   `proposed_grade_1ft.tif`, with hard conflict masks rasterized from
   canonical zones. Landing positions marked every ≤2.5 ft of rise.
   The emitted polylines ARE the constraint-bearing geometry (no
   simplification — validated geometry = shipped geometry).
4. **Validation, gates in order** —
   `analysis/ada_rebuild/ada_validation.json`:
   **topology → conflicts → slopes → landings → unchecked details.**

## 3 · Results

| gate | result |
|---|---|
| Topology | **PASS** — all 5 required pairs connected: arrival→floor, arrival→cross-aisle, cross-aisle→both wheelchair clusters, clusters→egress, service→stage (classified) |
| Conflicts | **PASS** — 0 ft treatment-cell contact (no crossing type exists for the cell); 0 ft stage-zone contact on public routes; 0 ft seating-wedge contact outside the aisle/promenade corridors; 4 swale contacts, each a **declared engineered culvert crossing** of 2.6–5.5 ft (cap 16 ft) |
| Slopes | **PASS** within the 8.33%+0.3% planning band (strict 8.33%: max step 8.6% on the smoothed surface — flagged, design grade is 8.33%) — checked only AFTER topology+conflicts |
| Landings | positions emitted (10–15 per descent); level pads pending civil detailing |

Route lengths: arrival→cross-aisle 418 ft (≈16 ft drop), arrival→floor
456 ft (≈28 ft drop), cross-aisle→egress 510 ft, floor→egress 555 ft,
plus short cluster/service connectors. The solver chose perimeter ramps
over switchback stacks — longer but lower-grading alignments.

**Elevated design issues (not blockers, must be carried):**
- Routes run partly **outside the legacy construction envelope**
  (`outside_legacy_envelope_ft` per route) — the envelope must be
  re-emitted when the network is adopted.
- `floor_arrival` reads 609.65 ft on the proposed grade vs the 612.5
  concept event-floor datum — the floor is concept-tier and not yet
  graded into the raster.
- Swale crossings need engineered culvert details.
- Cross slope is NOT validated (needs benched section design).

## 4 · Explicitly NOT checked (do not claim compliance)

Clear width, landing dimensions/slopes, turning radii, handrails/guards,
edge protection, wheelchair clear floor space, companion seat dimensions,
surface firmness/stability/slip resistance, built cross slope, sightline
preservation from wheelchair positions (refs carry flags only), ADAAG
§221 dispersion counts, winter operations. The full list ships inside
`ada_validation.json:unchecked_code_details`.

## 5 · Downstream updates

- **Viewer** — legacy fragments render as a hidden-by-default
  "REJECTED" layer (red dashed); the rebuilt network renders as a
  *concept*-tier layer (routes, nodes, landings). No ADA layer is
  labeled source-of-truth anymore.
- **Truth package** — `design_state.elements.ada_route` is now tier
  `concept` with the legacy-rejection record; the `ada_running` check was
  replaced by `ada_network` (topology→conflicts→slopes).
- **Human-scale refs** — the two ADA-critical figures re-anchored to
  rebuilt-route landings (ids preserved).
- **Viewpoint** — `ada_arrival_to_cross_aisle` re-anchored to the rebuilt
  arrival route.
- **Comparator memo** — all Petoskey ADA advantage claims removed;
  see `docs/AMPHITHEATRE_COMPARATORS.md` (ADA section) and
  `docs/COMPARATOR_PATCH1.md`.
- **Audit gates** — `check_ada_rebuild` FAILS on: missing validation,
  disconnected pairs, treatment-cell contact, undeclared swale crossings,
  fragment routes, legacy zones resurfacing in bowl_zones, loss of the
  concept tier or the pending-civil label. The comparator audit
  independently forbids superiority phrasing and slope-only validation
  language.

## Reproduce

```
.venv/bin/python scripts/rebuild_ada_routes.py
.venv/bin/python scripts/build_human_scale_refs.py
.venv/bin/python scripts/build_viewpoints_and_events.py
.venv/bin/python scripts/build_truth_package.py
.venv/bin/python scripts/audit_in_situ_package.py
```
