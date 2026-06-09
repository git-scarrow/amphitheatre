# Stage 2 — Stage/Storage Curve, Central Closed Bowl

Builds the stage–area–storage relationship for the **closed central depression** of the
Petoskey Pit from `dem/dem_design_1ft.tif`, and locates the **pour point** (spill).

> Naming: this is a separate doc from the Stage‑1 `README.md` (which documents the DEM
> build) so that record is preserved. All outputs below sit at the project root.

| Output | Description |
|---|---|
| `stage_storage.csv` | stage vs inundated area (ac, ft²) and cumulative storage (ft³, ac‑ft), 604→618.25 ft @ 0.25 |
| `basin_footprint.geojson` | dissolved polygon of the closed bowl (EPSG:6494) with floor/spill/depth attrs |
| `pour_point.geojson` | spill saddle point, outflow bearing, head to bay |
| `stage_storage_curve.png` | stage–area and stage–storage panels |
| `scripts/stage_storage.py` | reproducible driver (priority‑flood fill, no richdem/pysheds needed) |

## Headline result (international feet, NAVD88 Geoid12A)

| quantity | value |
|---|---|
| **closed‑bowl floor** | **609.12 ft** at E 19533014.2, N 750800.2 (≈ grid centre) |
| **spill / pour‑point elevation** | **618.04 ft** |
| max depth (spill − floor) | **8.92 ft** |
| footprint area at spill | **0.93 ac** (40,698 ft²) |
| **total storage at spill** | **5.69 ac‑ft** (≈ 248,000 ft³) |
| pour point | north rim, E 19532967.2, N 750904.2 — spills **toward the bay** (grid bearing 45°/NE at the 1‑ft saddle; macro‑direction north) |
| head, spill → bay | **36.6 ft** (bay 581.4 ft NAVD88, from 581 IGLD85 + assumed Δ0.40) |

## Method
1. **Domain** = valid DEM cells **minus the artifact mask**, with the mask treated as a
   **barrier**, not an open outlet. (If the bay‑ward `<595 ft` low were an open outlet, the
   bowl would falsely drain to the bay and never register as a closed sink.)
2. **Priority‑flood depression fill** (Barnes/Planchon, 8‑connected, heap‑based — pure
   numpy/scipy, since `richdem`/`pysheds`/`whitebox` are absent from the venv). Outlets seed
   from grid‑edge cells and cells touching the barrier. `fill − dem` = depression depth.
3. **Closed bowl** = the connected depression component holding the deepest cell. Its constant
   fill value **is** the spill elevation.
4. **Pour point** = the bowl‑perimeter cell whose lowest exterior neighbour is the global
   drainage exit; outflow direction points to that neighbour.
5. **Stage/storage**, restricted to the bowl footprint: for each stage *E*, area = count of
   footprint cells with `dem < E` (1 ft² each); volume = `Σ(E − dem)` over those cells.

## ⚠ Correction to the requested floor range (read this)
The task specified floor candidates **604–616 ft**, premised on the earlier "floor ≈ 607 ft."
The depression analysis shows that figure does **not** describe the *closed* bowl:
- The **hydraulically closed** central sink bottoms at **609.12 ft** (gridded) and **spills at
  618.04 ft**. The whole requested 604–616 band lies **below the spill**, and 604–609 lies
  **below the closed floor** (zero area — see the leading rows of the CSV).
- Therefore the curve is **extended up to the spill (618.25 ft)** so the full bowl capacity and
  the pour point are captured. The requested 604–616 rows are retained verbatim.

**Reconciling 609 vs 607:** 606.99 ft was the *point‑cloud minimum* of the tight bowl (a single
lowest ground return); 609.12 ft is the lowest **cell of the closed sink** after IDW gridding
(window_size=3 smooths pinholes, and the absolute point‑min can sit in a non‑closing micro‑pinch).
For stage/storage — a volumetric, hydraulic quantity — the gridded closed‑sink floor is the
correct datum. The ~2 ft difference is gridding/▢definition, not new terrain.

## Notes & caveats (carried to DATA_GAPS.md)
- **The bowl is genuinely closed only because the artifact strip is walled off.** In bare
  topography the floor lies on the bay‑ward flank; the 618 ft spill is the lowest rim saddle on
  the **north** side, ~100 ft south of the masked strip (confirmed not a mask‑edge artifact).
  The exit neighbour sits at the same 618.04 fill (a shared‑level pocket that drains onward) —
  expected at a saddle.
- **Pour point governs overflow routing.** Once the bowl fills to 618 ft it overflows north
  toward the bay/Bear River — the receiving water the brief flags as sensitive. Any design that
  raises an event floor and berms the bowl as a treatment cell must site its controlled outlet
  with this in mind.
- IDW DEMs contain many sub‑inch micro‑pits (5,938 trivial depressions at a 0.001 ft threshold);
  none affect the single dominant bowl used here.
- Datum offset Δ (NAVD88 = IGLD85 + 0.40 ft) is an **unconfirmed assumption**; the 36.6 ft head
  to bay carries a ±0.3 ft band and the sign must be confirmed via NOAA VDatum before any
  freeboard/outlet‑invert decision.

Reproduce: `python scripts/stage_storage.py` (inside `.venv`).
