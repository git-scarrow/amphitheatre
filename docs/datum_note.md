# Datum & CRS Note — Petoskey Pit, Stage 1

## Horizontal CRS (confirmed from LAZ header)
- **EPSG:6494 — NAD83(2011) / Michigan Central**
- Lambert Conformal Conic 2SP; standard parallels 45.7° / 44.18333°; lat-of-origin
  43.31667°; central meridian −84.36667°; false easting 19 685 039.37 ft, false northing 0.
- **Linear unit: INTERNATIONAL foot (0.3048 m exactly, EPSG:9002).**

> **Correction to project brief.** The brief states "US survey feet." The header is
> unambiguous: Michigan State Plane is legally defined in **international feet** (Michigan
> is the national exception that adopted the international foot for SPCS). Both tiles carry
> `UNIT["foot",0.3048,EPSG:9002]` horizontally and vertically.
>
> Practical impact:
> - **Elevations / relief:** intl ft vs US survey ft differ by 2 ppm → at z ≈ 660 ft this is
>   ~0.0013 ft. **Negligible.** All elevation statistics here are international feet.
> - **Horizontal coordinates:** the *false easting* is ~19.7 million ft, so a 2 ppm unit
>   error misread as US-survey-ft would shift absolute easting by ~**39 ft**. Anyone
>   reusing these coordinates MUST treat them as international feet to avoid that shift.
>   Relative distances/areas within the AOI are unaffected at planning grade.

## Vertical datum (confirmed from LAZ header)
- **NAVD88, GEOID12A, international feet** (`VERT_CS["NAVD88 - Geoid12A (Intl Feet)"]`).
- This is the elevation datum of `dem_design_1ft.tif` and `dem_context_2p5ft.tif`.

## NAVD88 ↔ IGLD85 reconciliation (planning-grade)
Lake/bay stages for Little Traverse Bay are quoted in **IGLD 1985**
(bay surface ≈ **581 ft IGLD85**). The LiDAR is **NAVD88**. To compare lake or
groundwater levels against the DEM, convert into a common datum first.

**Why they differ (and why the offset is small):** IGLD85 and NAVD88 are *not*
independent datums. Both derive from the **same 1985 General Adjustment** of the
North-American leveling network and the **same origin** (tide gauge at Pointe-au-Père /
Rimouski, Québec). They share identical geopotential numbers. The only difference is the
height system used to turn geopotential into an elevation:
- **IGLD85** publishes **dynamic heights** (geopotential ÷ normal gravity at 45° lat).
- **NAVD88** publishes **Helmert orthometric heights** (geopotential ÷ mean gravity along
  the plumb line).

The resulting difference is **location-dependent and sub-foot** across the Great Lakes.

**Working value used downstream (CONFIRMED — `gating_dossier.md` gate A-1):**
```
NAVD88_elev  =  IGLD85_elev  +  Δ      Δ = +0.162 ft  (CONFIRMED 2026-06-06, NOAA VDatum)
bay surface  ≈  581 ft IGLD85  ≈  581.16 ft NAVD88  (Δ now exact; residual band is the
                                                     ≈581 ft IGLD85 bay-stage estimate itself)
```
- Δ is carried as an explicit parameter, **not** baked into rasters. The DEM stays pure NAVD88.
- **CLOSED 2026-06-06 (gate A-1).** The sign and magnitude are now confirmed via **NOAA VDatum**
  at the site (45.3746°N, 84.9582°W): **NAVD88 = IGLD85 + 0.162 ft**. The prior **+0.40 ft was a
  labelled assumption** (within the ±0.3 ft band but ~0.24 ft high) and is **superseded**; use
  +0.162 ft for all future bay/IGLD85 tie-ins. No design decisions change (see DATA_GAPS.md).

## Implication for stage goals
Stage/event-floor elevation is to be set by stormwater **and groundwater** strategy.
Any comparison of the ~595–610 ft NAVD88 basin floor against the ~581 ft IGLD85 bay
must first apply Δ. At the working Δ the basin floor sits **~14–29 ft above bay level**,
so hydraulic head toward the bay/Bear River is ample; the binding constraint is far more
likely to be **seasonal high groundwater** (unknown — see DATA_GAPS.md), not bay backwater.
