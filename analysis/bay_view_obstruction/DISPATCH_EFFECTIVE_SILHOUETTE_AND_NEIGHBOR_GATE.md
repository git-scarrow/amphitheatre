# Bay-band v2 — effective silhouette, canopy layer, far-shore band top, neighbor gate

**Status:** PROPOSED · owner-directed 2026-07-21 · **UNVALIDATED — specification only.**
Authored on macbook-m4 (no DEM, no geo deps); can only be *executed and validated* on
**gentoo** (`sam@gentoo`, `~/projects/amphitheatre`, `.venv` with shapely/numpy/rasterio,
DEM rasters, PDAL for the point cloud). Nothing here is adopted until the run completes
and the owner signs off on the outputs.

**Why this exists:** the owner redefined how bay-view obstruction is measured and charged
(conversation of 2026-07-21). Five directives, each of which changes the analysis contract:

1. **The bay band is defined against the *effective* silhouette** — per ray, the max
   occlusion angle over ALL opaque occluders (terrain, city massing, canopy, stage mass),
   not bare-earth terrain alone. The layered computation
   (`bay_view_layered_obstruction.py`) is **promoted from sensitivity study to the
   definition**; `per_row_obstruction.*` (terrain-only) becomes the S0 baseline, not the
   answer.
2. **Occluders are charged per named occluder set** (they are not equally durable):
   - **S0** terrain only (bare-earth DEM)
   - **S1** + current flat stage + LiDAR-height-verified city buildings (durable reality)
   - **S2** + canopy-today (mutable, seasonal, third-party — Bayfront Park is City land,
     the US-31 frontage is MDOT ROW)
   Leeway that exists only under S2 is real but **contingent** and must be labeled so.
3. **The band top is the far-shore waterline, not the open-water horizon.** The current
   `horizon_dip_deg = sqrt(2h/R)` places the top at the geometric tangent (~8.5 mi for a
   48-ft eye). Every ray in the 318–342° corridor lands on the **north shore of Little
   Traverse Bay at ~4–7 mi**, short of the tangent — the modeled horizon is never visible.
   Correct the band top per azimuth (T2). Error is small (~0.01–0.02°, 1–2% of band) but
   the definition should be right before v2 numbers are quoted.
4. **Neighbor hard gate (Reading B), owner-selected 2026-07-21:** no construction may
   intrude into any existing **bay band** of street receptors on the E / S / SE frontages
   (E Lake St, E Mitchell St, Petoskey St). This protects the *water view*, not the
   skyline: construction MAY appear above the 618.04 rim from the streets; that skyline
   change is accepted by the owner and must be **reported, not gated**. Interior
   (audience) bands remain a discretionary budget; neighbor bands are inviolable.
5. **r_n and r_m are outputs, not inputs.** The owner's row-threshold model (rows below
   r_n rim-blocked; r_n–r_m canopy-blocked; above r_m clear) is resolved by attribution:
   for each row, name the binding occluder below its first non-empty band.

## Fixed constants (do not re-derive)

- Bay water plane **579.45** NAVD88 ft (`in_situ_common.BAY_PLANE`); rim spill **618.04**
  (`site_context.geojson` rim_arrival_edge); bay corridor **az 318–342°** (±12° of 330);
  seated eye **+3.94 ft**; site ~45.3746°N 84.9582°W; CRS EPSG:6494 intl ft.
- Committed S0 baseline (do NOT redo): `per_row_obstruction.csv` — first acceptable row:
  **south r6, bend r11 (r7–r8 marginal), east r11**; rows 5/9/10 repurposed.
- Committed S1 partial: `layered_obstruction.csv` (terrain+stage+city; stage delta 0.0
  everywhere; east top rows already only ~46–62% clear from city massing).
- Canopy: **no layer exists** — `OBSTRUCTION_CONFIDENCE_REPORT.md` row 4b Indeterminate.
  That is the gap this dispatch closes.

## Tasks (run on gentoo, in order)

### T1 — Canopy layer (L3) from EPT first returns
- Source: the 3DEP EPT the repo's `ept.json` describes (9.25B pts, laszip). PDAL pipeline;
  windowed reads only.
- AOI: the corridor sector from the bowl centroid across US-31 to the shoreline, plus the
  W/NW band az ~300–345° out to ~3,000 ft (covers the documented densest screen at
  315–320° AND the full corridor).
- Build a first-return canopy height model (~3 ft grid); derive a **canopy silhouette
  angle per (receptor, azimuth) ray** (same 2° steps as the existing scripts).
- **Record the acquisition date(s) and leaf state from EPT metadata.** Michigan 3DEP is
  often flown leaf-off. If leaf-off: the measured silhouette is the *winter* screen;
  emit a leaf-on variant only as a labeled assumption (e.g., crown-opacity inflation),
  never as measurement. Summer is the operating season — this caveat is load-bearing.

### T2 — Band-top correction (far-shore waterline)
- Per azimuth: intersect the ray with the shoreline (OSM/NOAA coastline or the DEM water
  mask at 579.45), distance d_shore; band top
  `θ_top = −(h/d_shore + d_shore/2R)` (radians, h = eye − 579.45, R = earth radius ft).
- Assert d_shore < tangent distance `sqrt(2Rh)` per ray (expected everywhere in the
  corridor); if any ray is genuinely open-water, fall back to the dip formula there.
- Extract the far-shore landform skyline (north-shore terrain above the waterline) and
  report structure occlusion of it **separately** as a composition metric — it is part of
  the view but it is not "seeing the water."

### T3 — Interior bands per occluder set + attribution
- Recompute per-row, per-section bands under S0 / S1 / S2 (S2 in both leaf states if T1
  yields both), with the T2 band top. Keep the existing verdict convention
  (acceptable ≥80% clear · marginal 40–79 · blocked <40).
- Emit per row: band width, clear %, and **binding occluder** (which layer's silhouette
  tops the band bottom). **r_n** = first row per section with any non-empty band under
  S0; **r_m** = first row per section acceptable under S2. Publish the r_n/r_m table —
  this answers the owner's row-threshold question directly.

### T4 — Neighbor receptors + Reading-B ceiling
- Extract street-edge grades from the DEM along the three frontages
  (`site_context.geojson` street_edge lines; `design_extended_bays` boundaries), sampled
  every ~25 ft. Eyes at **+5.0 ft** (ground/storefront) and **+17.0 ft** (second story).
- Per receptor: bay band with effective silhouette under S1 and S2 (their occluders are
  the US-31 edge, the W/NW buildings, the canopy — the pit itself occludes nothing for
  them today). Receptors with an **empty band impose no constraint — record them**; the
  gate binds only where a water view exists.
- **Neighbor-ceiling raster** over the stage/event-floor zone:
  `ceiling(x,y) = min over {receptor e, corridor azimuth a whose ray crosses (x,y)} of
  z_eye(e) + dist(e,(x,y)) · tan(θ_sil_eff(e,a))`
  i.e., new mass may rise exactly to each receptor's existing silhouette ray and no
  further. Emit GeoTIFF + PNG with the S1 and S2 variants side by side. The **S1 ceiling
  is the durable one**; S2-only headroom is contingent leeway.

### T5 — Element re-verdict (section-B menu)
- Charge each element (roof 22 ft · acoustic canopy 18 · service_canopy 21 · boh 12 ·
  masts 26 · wings 12 · apron 1) against the **S1 and S2 interior bands** (report deltas
  vs the old terrain-only charges in `STAGE_SHAPE_STUDY.md` §C) and against the
  **neighbor gate: PASS/FAIL** under S1 and S2.
- Report each element's max permissible height at its plan position from the T4 raster.
- Note: masts are seasonal/removable and the screen night-only — if a mast fails the
  gate, flag for owner policy (temporary vs permanent) rather than auto-rejecting.

### T6 — Outputs & hygiene
- New artifacts under `analysis/bay_view_obstruction/`: `canopy_silhouette.csv`,
  `band_top_farshore.csv`, `per_row_bands_by_set.csv`, `rn_rm_table.md`,
  `neighbor_receptors.geojson`, `neighbor_ceiling_S1.tif` / `_S2.tif` (+ PNGs),
  `element_verdicts_v2.md`, `summary_v2.md`.
- Update `OBSTRUCTION_CONFIDENCE_REPORT.md` (canopy row: Indeterminate → measured, with
  leaf-state caveat).
- Fix the `bay_view_obstruction.py` docstring error claiming the stage is "geometrically
  behind the viewer when looking at the bay" — upstage IS the bay direction (that is the
  backdrop premise); the layered run already traced the flat deck correctly (delta 0.0).

## ⚠ Traps

1. **Scripts print FAIL but exit 0** — parse verdict text, never `rc`.
2. **Leaf-off LiDAR understates the summer screen.** Label leaf state on every canopy
   number. A leaf-on estimate is an assumption, not a measurement.
3. **Never pass an element on S2 alone.** Canopy leeway is third-party and mutable; an
   element that clears only because of trees must be flagged `contingent_on_canopy`.
4. **This changes definitions used in Rule 9 arguments** (roof/typology leeway, T2 roof
   status). Outputs inform `STAGE_SHAPE_STUDY.md` §B/§C and the stage-shape work
   (`analysis/stage_adoption/MEMO_STAGE_SHAPE_VS_AUDIENCE_AXIS.md`) but adopt nothing:
   owner sign-off required before any decision record changes.
5. **The neighbor gate standard is Reading B by explicit owner direction 2026-07-21:**
   "no owner loses any bay view" — NOT "no visible skyline change." Record it in those
   words wherever the gate is cited, so the standard committed to is the one chosen.

## Definition of done

- **(a)** `rn_rm_table.md` — r_n / r_m per section per leaf state, with binding-occluder
  attribution per row; and
- **(b)** neighbor-ceiling rasters (S1/S2) + `element_verdicts_v2.md` with the section-B
  menu re-charged and gated.

Any outcome is a result: "the T2 roof is effectively free under S2 but charged under S1,"
"the roof fails the neighbor gate at second-story eyes," and "canopy blanks rows 6–14 in
summer" are all decisions the owner can act on. What is not acceptable is quoting v2
numbers without leaf-state and occluder-set labels attached.
