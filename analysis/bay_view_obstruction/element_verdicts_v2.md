# Element re-verdict v2 — section-B menu vs effective silhouette + neighbor gate

**Placement:** P_opt (front centre 19533106.6, 750762.8; axis 150°; boh west/left). Deck 612.5 ft. Elements charged ALONE (compose per STAGE_SHAPE_STUDY §B/§C).

**Interior charge** = worst-family incremental corridor bay-% newly blocked for the audience, under the v2 far-shore band top:
- **S1** = terrain + flat stage + LiDAR-verified city (DURABLE).
- **S2** = + canopy (leaf-on, operating season). Under S2 the foreground canopy already blanks most interior bands (see rn_rm_table: no row is acceptable through the trees), so element S2 charges collapse toward 0 — **that leeway is contingent on third-party trees (Bayfront Park City land / MDOT ROW) and must not pass an element** (trap #3). Elements flagged `contingent_on_canopy` clear only because of the canopy.

**Neighbor gate (Reading B, owner 2026-07-21, verbatim):** _"no owner loses any bay view"_ — NOT "no visible skyline change." Skyline change above the 618.04 rim from the streets is accepted and reported, not gated. Gate = element top vs the neighbor-ceiling raster over the element footprint. **S1 ceiling is durable**; S2-only headroom is contingent. maxH = max permissible height above deck at the footprint.

Base corridor clear% (no element): east S1=30/S2=3, bend S1=58/S2=20, south S1=72/S2=24

> **Basis note:** the v2 interior charge is the drop in corridor **clear%** (fraction of 318–342° rays that flip water→blocked when the element is added), under the far-shore band top. STAGE_SHAPE_STUDY §C's `new_bay_blocked_pct` is an area-weighted share of the existing visible band on a ray-crossing basis. The two are related but NOT the same metric, so absolute numbers are not apples-to-apples; the load-bearing finding is the **direction**: against the corrected (thinner) far-shore band, the big overhead elements charge MORE to the audience under S1 than the terrain-only study credited.

| element | top ft | old §C bay% (terrain) | v2 S1 bay% | v2 S2 bay% | gate S1 | gate S2 | maxH S1 ft | maxH S2 ft | flag |
|---|---|---|---|---|---|---|---|---|---|
| roof | 634.5 | 8.6 | 38.5 | 14.7 | PASS | PASS | 22.1 | 24.7 | — |
| canopy | 630.5 | 16.1 | 23.4 | 7.9 | PASS | PASS | 22.4 | 24.9 | — |
| service_canopy | 633.5 | 18.6 | 24.6 | 8.4 | PASS | PASS | 22.7 | 27.4 | — |
| boh | 624.5 | 7.3 | 0.9 | 0.3 | PASS | PASS | 22.2 | 26.0 | — |
| mast_l | 638.5 | 3.2 | 1.9 | 0.5 | FAIL | PASS | 23.3 | 26.7 | FAIL→owner-policy (seasonal/removable; screen night-only) |
| mast_r | 638.5 | 1.7 | 1.2 | 0.9 | FAIL | FAIL | 22.4 | 24.9 | FAIL→owner-policy (seasonal/removable; screen night-only) |
| wing_l | 624.5 | 4.3 | 0.0 | 0.0 | PASS | PASS | 23.3 | 26.7 | — |
| wing_r | 624.5 | 2.2 | 1.5 | 0.9 | PASS | PASS | 22.4 | 24.9 | — |
| apron | 613.5 | 0.0 | 0.0 | 0.0 | PASS | PASS | 24.6 | 28.7 | — |

## Verdict changes vs the terrain-only baseline

- **roof** (top 634.5 ft): interior charge S1 38.5% vs old terrain-only 8.6%; S2 14.7%; neighbor gate S1 **PASS**.
- **canopy** (top 630.5 ft): interior charge S1 23.4% vs old terrain-only 16.1%; S2 7.9%; neighbor gate S1 **PASS**.
- **service_canopy** (top 633.5 ft): interior charge S1 24.6% vs old terrain-only 18.6%; S2 8.4%; neighbor gate S1 **PASS**.
- **boh** (top 624.5 ft): interior charge S1 0.9% vs old terrain-only 7.3%; S2 0.3%; neighbor gate S1 **PASS**.
- **mast_l** (top 638.5 ft): interior charge S1 1.9% vs old terrain-only 3.2%; S2 0.5%; neighbor gate S1 **FAIL** (maxH 23.3 ft; top 26 ft); FAIL→owner-policy (seasonal/removable; screen night-only).
- **mast_r** (top 638.5 ft): interior charge S1 1.2% vs old terrain-only 1.7%; S2 0.9%; neighbor gate S1 **FAIL** (maxH 22.4 ft; top 26 ft); FAIL→owner-policy (seasonal/removable; screen night-only).
- **wing_l** (top 624.5 ft): interior charge S1 0.0% vs old terrain-only 4.3%; S2 0.0%; neighbor gate S1 **PASS**.
- **wing_r** (top 624.5 ft): interior charge S1 1.5% vs old terrain-only 2.2%; S2 0.9%; neighbor gate S1 **PASS**.
- **apron** (top 613.5 ft): interior charge S1 0.0% vs old terrain-only 0.0%; S2 0.0%; neighbor gate S1 **PASS**.

## Key reframes
- The v2 **binding interior occluder is the canopy**, not the stage or its elements: no seated row achieves an acceptable (>=80%) bay view through today's tree line (rn_rm_table r_m = none, both leaf states). Element interior charges therefore read as small increments on an already tree-limited view — real under S1 (if trees are trimmed/removed the audience regains the bay and the element charge bites), ~0 under S2 (trees present). Both must be stated with their occluder set + leaf state.
- The **durable constraint is the neighbor gate under S1**. Elements whose top exceeds the ~635 ft S1 neighbor ceiling over the stage intrude into E/S/SE street water views.

_Adopts nothing; owner sign-off required (traps #4/#5)._
