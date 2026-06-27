# UE Live-Scene Actor Audit — stage-like + bay-corridor context

Live query of `/Game/Maps/CivicBowl` via the Unreal MCP host (gentoo UE 5.8),
2026-06-27. Read-only: no actor was moved, hidden, deleted, or relit.
Coordinate conversion: `z_ft = (z_cm − 17661.6) / 30.48 + 579.45`
(calibrated from the bay-water plane at 579.45 ft and stage deck at 612.5 ft).

## 1. Stage-like actor enumeration

Searched actor labels for: stage, provisional, rule9, shell, bandshell,
forecourt, platform, orchestra, performance.

| Actor (label) | Folder | Class | Z range (ft) | Visible (bHidden) | Class: current / stale / placeholder |
|---|---|---|---|---|---|
| Stage_zone_stage_core | Proposal_Editable/Stage | StaticMeshActor | 612.0–612.5 | shown | **current adopted** stage deck (Scenario E) |
| Stage_zone_stage_shoulder_left | Proposal_Editable/Stage | StaticMeshActor | 612.0–612.5 | shown | **current adopted** stage shoulder |
| Stage_zone_stage_shoulder_right | Proposal_Editable/Stage | StaticMeshActor | 612.0–612.5 | shown | **current adopted** stage shoulder |
| EventFloor_zone_orchestra_event_floor | Concept_Landscape/EventFloor | StaticMeshActor | 612.0–612.5 | shown | concept event floor (flat, stage level) |
| Ref_lineage_focal_point_stage_front | Reference/BayView | StaticMeshActor | — | shown | reference marker (not massing) |
| Human_center_stage | Reference/HumanScale | StaticMeshActor | — | shown | human-scale figure (not massing) |
| Human_stage_front_performer | Reference/HumanScale | StaticMeshActor | — | shown | human-scale figure (not massing) |
| ADA_ada_route_service_to_stage | Concept_ADA/Routes | StaticMeshActor | — | shown | ADA route ribbon (not massing) |
| Dim_dim_stage_front_to_row1 | (dimension) | StaticMeshActor | — | shown | dimension ribbon (not massing) |

**Keyword searches `shell`, `bandshell`, `provisional`, `rule9`, `forecourt`,
`platform`, `performance` → ZERO actors.**

### Acceptance result — stage system

**PASS: exactly one current stage system (3 actors: core + left + right
shoulder), no stale/duplicate/provisional stage massing.** All three sit at
Z 612.0–612.5 ft — a 0.5 ft flat slab with **no vertical shell, tower, or
proscenium**. The event floor is a separate flat slab at the same elevation.
Nothing matching a band-shell or provisional Rule-9 vertical element exists in
the live level. This independently confirms the flat/open-stage premise the
stage raycast (Claim 2) is scoped to.

## 2. Bay-corridor context actors

| Actor (label) | Folder | Z range (ft) | bHidden (runtime) | Note |
|---|---|---|---|---|
| ctx_city_massing | Context/City_LoFi/city_massing | 578.7–941.0 | false | one merged mesh; Zmax 941 ft = far inland-SE building (not in bay view); near W/NW roofs ≤ ~653 ft |
| ctx_bay_water_plane | Context/bay_water_plane | 579.5 | false | flat water datum at bay plane |
| ctx_distant_horizon_band | Context/distant_horizon_band | 579.5–973.2 | false | tall horizon backdrop band |

### Visibility caveat (unresolved)

The editor-visibility flag `bHiddenEd` is **not exposed** through the MCP
property API (read attempts errored). Only the runtime flag `bHidden` is
readable, and it is **`false`** for `ctx_bay_water_plane` and
`ctx_distant_horizon_band`. The memory record claims these legacy proxies were
hidden via `bVisible=false` (an editor-visibility / component flag). These two
facts are **not contradictory** (runtime vs editor visibility are different
flags) but they are **not reconciled** either. Therefore:

> The live editor-viewport visibility of the bay-water plane and horizon band
> is **not confirmed** by this audit. A visual confirmation in the editor (or a
> component-level `GetVisibleFlag` read) is still required before asserting the
> review render is proxy-clean. This keeps Claim 3 at **Medium**, not High.

## 3. Raycast cross-check (live UE vs Python DEM+OSM model)

`trace_world` from the **east r17 eye** (UE `(−1146, 4459, 19392)`):

| Azimuth | Python model | UE trace_world | Agree? |
|---|---|---|---|
| 322° | clear (no building crossing) | `null` (no hit) | ✅ |
| 334° | Beards Brewery hit @ ~76 m | hit @ **77.1 m** | ✅ |
| 340° | Beards Brewery hit @ ~73 m | hit @ **73.5 m** | ✅ |

Two independent methods agree to within ~1 m. The live scene confirms that the
city massing (Beards Brewery) occludes the NW half of the bay corridor from the
east-section upper rows, and that the SW half (az ≤ 326°) is clear.
