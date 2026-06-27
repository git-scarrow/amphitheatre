# W/NW context massing — vertical-accuracy audit

**Question:** Is the large building/massing W/NW of the Civic Bowl rendered at an
accurate height relative to the bowl edge / street level, or is it a context-placement
bug (vertical/registration offset)?

**Verdict: A — real and approximately correctly placed AND correctly tall.**
No vertical datum offset, no float/bury, no height inflation in the W/NW buildings.
The *visual* "domination" is a representation artifact (hidden bay water plane), not a
building-geometry error. Smallest correction proposed separately (do not apply yet).

## Reference levels (NAVD88)
| level | m | ft |
|---|---|---|
| bay water datum | 176.4 | 579 |
| stage-front street (focal) | 185.8 | 610 |
| bowl rim (60–100 m ring, median) | 192.1 | 630 |
| foreground terrain max (near bowl) | 216.9 | 712 |
| city terrain max (inland SE) | 262.2 | 860 |

## Live scene (measured via UE MCP on the saved CivicBowl.umap)
- `ctx_city_massing` is ONE merged StaticMeshActor (SMA_6), at origin, scale ×100.
  Envelope **Z 176.39 → 286.83 m**.
- `ctx_city_ground` (terrain) Z 176.39 → 261.96 m; `ctx_fg_terrain` 176.39 → 216.93 m.
- The 3 legacy proxies — `ctx_bay_water_plane`, `ctx_shoreline_proxy`,
  `ctx_distant_horizon_band` — are all **bVisible = false (hidden)**.
- Current viewport camera: UE (−4052, 4182, 19639) cm → SE of bowl, eye 196.4 m,
  yaw −35° / pitch −14° → looking NNW down the bay-view axis.

## Offline ground truth (LiDAR first-return DSM − 3DEP DTM, exactly gen_context's method)
- **Citywide real max roof-top = 283.7 m** (a building on the highest inland terrain,
  SE, ~1.37 km away, base 260 m + 23.7 m). The live merged Z-max **286.8 m matches this
  within 3.1 m** → heights were reproduced faithfully; the 286.8 m extreme is a real
  inland-SE building, **not** in the bay view and **not** a datum bug.
- **W/NW sector (az 250–360°, <700 m) real max roof-top = 213.3 m.** Every near W/NW
  building roof tops out at or below the bowl rim.

## The W/NW candidates (see suspect_heights.csv)
| building | footprint | roof top | vs bowl rim | base − terrain |
|---|---|---|---|---|
| Petoskey Police Dept (largest W/NW) | 1119 m² | 190.3 m (624 ft) | −1.8 m | −0.39 m |
| unnamed WNW | 754 m² | 189.5 m | −2.6 m | −0.24 m |
| Little Traverse Historical Society (on-axis 330.8°) | 631 m² | 184.3 m | −7.8 m | +0.05 m |
| Beards Brewery (north reference) | 551 m² | 199.0 m | +6.9 m | −0.09 m |

`base − terrain ≈ 0` everywhere → bases sit ON the terrain (not floating/buried).

## Why it *looks* like it dominates (representation, not geometry)
1. **The bay water plane is hidden.** USGS 3DEP has no water voids, so with the slab off
   the bay reads as flat land; the far (north) shore terrain fills the NNW where open
   water should be — making the bay-side context look built-up. (Matches "Google Maps
   shows that side clear/open": real water vs UE land.)
2. The real civic buildings WNW (Police Dept cluster) are the most prominent built mass
   on the left of the NNW view — but at correct, rim-level height.

## Smallest corrections (NOT applied — for decision)
- To restore the open-bay read: re-enable `ctx_bay_water_plane` (bVisible=true) **or**
  add a proper water surface on the bay. Pure visibility/material change; no geometry,
  no building moves.
- No change to any building is warranted on height/placement grounds.

## Live confirmation (UE MCP `trace_world`, vertical ray, hit elev = (40000−dist)/100 m)
| probe (UE cm) | live hit | computed | meaning |
|---|---|---|---|
| Police Dept centroid (8287, −17864) | **193.3 m** | roof 190.3 m | building roof; terrain ~180 m → real, west, on-grade, ~rim |
| Stage focal (−1720, 990) | 187.0 m | street 185.8 m | bowl ground ✓ |
| Historical Society (12185, −6783) | 184.6 m | roof 184.3 m | on-axis roof, below rim ✓✓ |
| Bay axis +200 m NNW (15600, −9010) | 176.9 m | — | flat lake-level land where bay should be |
| Bay axis +300 m NNW (24260, −14010) | 176.6 m | — | flat lake-level land — no open water |
| Inland SE Z-max zone (−91760, 104540) | 260.2 m | terrain 262 m | the high terrain carrying the 286.8 m max — behind the view |

Live probes match the LiDAR computation; the merged mesh has collision and is correctly
registered (the west building is physically west, at rim height, on the terrain).

Artifacts: `suspect_heights.csv` / `.json`, `plan_obstruction_check.png`,
`section_obstruction_check.png`, `osm_near_focal.json`.
