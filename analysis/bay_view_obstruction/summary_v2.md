# Bay-band v2 — summary (effective silhouette · far-shore band top · canopy · neighbor gate)

**Status: UNADOPTED analysis. Owner sign-off pending (dispatch traps #4/#5).** No
decision record, canon, or adopted geometry was changed. Emitted 2026-07-21 by the
gentoo pipeline per `DISPATCH_EFFECTIVE_SILHOUETTE_AND_NEIGHBOR_GATE.md`.

## What changed in the contract (owner directives, 2026-07-21)

1. The bay band is defined against the **effective silhouette** (max over all opaque
   occluders), not bare-earth terrain. Occluders charged per named set:
   **S0** terrain · **S1** +flat stage +LiDAR-verified city (durable) · **S2** +canopy
   (mutable, third-party — Bayfront Park City land / US-31 MDOT ROW).
2. Band **top = far-shore waterline**, not the open-water horizon (T2).
3. **Neighbor hard gate (Reading B):** _"no owner loses any bay view"_ — protect the
   E/S/SE street water views; skyline change above the 618.04 rim is accepted+reported.
4. **r_n / r_m are outputs** (row-threshold model resolved by attribution).

## T1 — Canopy layer (MEASURED, leaf-off)

- Source: USGS 3DEP EPT `USGS_LPC_MI_13Co_Emmett_2015`, windowed NW AOI, reprojected to
  EPSG:6494 ft. First-return DSM − ground DTM = CHM; canopy = CHM 6–90 ft with OSM
  building footprints subtracted (this delivery has **no** ASPRS veg/building classes,
  so canopy is geometric, not classified). 255k leaf-off canopy cells; CHM mean 30 ft,
  p90 59 ft.
- **Acquisition 2015-05-02 → LEAF-OFF** (GpsTime-decoded; N-Michigan 45.37°N leaf-out is
  mid-to-late May). The measured silhouette is the **winter screen**. Leaf-on is a
  labeled **crown-opacity assumption** (gaps morphologically closed; heights NOT raised)
  — summer is the operating season, so it is reported but is not a measurement.
- Screen is densest **az 312–321** (63–70 canopy cells/ray), thinning toward 330–342 —
  reproducing the prior "densest az 315–320" finding from independent data.

## T2 — Far-shore band top

- Every corridor ray lands on the north shore of Little Traverse Bay at **d_shore ≈
  9.8k–12.6k ft (1.85–2.4 mi)**, far short of the ~44.8k ft (8.5 mi) geometric tangent
  → the open-water horizon is never visible; 0 rays fall back to the dip formula.
- The far waterline sits **below** the open-water horizon by ~0.12–0.18° (θ_top ≈ −0.24
  to −0.30° vs dip −0.12°). This is a real, not negligible, correction: it thins the
  visible water band and slightly lowers clear% for marginal rows. Far-shore landform
  skyline (Harbor Springs/Point bluff, up to ~+0.7°) reported separately in
  `band_top_farshore.csv` as a composition metric (backdrop, not water).

## T3 — r_n / r_m per section per leaf state  (the owner's row-threshold answer)

| section | r_n (S0 non-empty) | r_m (S2 leaf-off accept) | r_m (S2 leaf-on accept) | binding r_n..r_m |
|---|---|---|---|---|
| east | 8 | none | none | canopy |
| bend | 6 | none | none | canopy |
| south | 6 | none | none | canopy |

- **r_m = none in every section, both leaf states.** No seated row achieves an
  acceptable (≥80% clear) bay view through today's canopy. Best case is ~54% clear
  (marginal) at the top of the bend, leaf-off. Under S2 the **binding occluder flips
  from terrain to canopy for every row.**
- Under **S0/S1** the upper rows read 92–100% clear (terrain/city), reproducing the
  committed baseline (small differences trace to the stricter T2 band top). The canopy
  is what erases that view. **The seated bay view is gated by the foreground tree line,
  a mutable third-party screen — not by terrain, the stage, or the city massing.**
- Caveat: the leaf-off silhouette treats the bare-crown envelope as opaque, so it does
  not credit winter see-through between branches (real winter visibility ≥ the leaf-off
  numbers); leaf-on (summer) fills those gaps and is slightly worse.

Full per-row clear% + binding occluder per set: `per_row_bands_by_set.csv`,
`rn_rm_table.md`.

## T4 — Neighbor receptors + Reading-B ceiling

- 184 street receptors (E Lake N, E Mitchell S, Petoskey E; every 25 ft; eyes +5 ft
  ground and +17 ft second-story). Under **S1, 178/184 have a protected water band**;
  under **S2 (leaf-on) only 72** — the canopy blanks most neighbors' bay view too.
- Neighbor-ceiling over the stage/event-floor zone (max new-mass top that does not
  intrude into any protected receptor's water band):

  | set | ceiling over stage (min / median NAVD88 ft) | headroom over deck 612.5 (min ft) |
  |---|---|---|
  | **S1 (durable)** | **635.4 / 637.1** | **+22.9** |
  | S2 (contingent) | 638.3 / 642.5 | +25.8 |

  The **S1 ceiling ~635 ft is the durable gate**; the extra ~3 ft of S2 headroom exists
  only because the canopy already screens the neighbors and is contingent leeway.
  Rasters: `neighbor_ceiling_S1.tif/.png`, `neighbor_ceiling_S2.tif/.png`;
  receptors `neighbor_receptors.geojson`.

## T5 — Element re-verdict (section-B menu)  vs S1/S2 bands + neighbor gate

Deck 612.5 ft. Interior charge = worst-family corridor bay-% newly blocked (basis
differs from §C — see `element_verdicts_v2.md`); gate = top vs neighbor ceiling.

| element | top ft | old §C bay% | v2 S1 | v2 S2 | gate S1 | gate S2 |
|---|---|---|---|---|---|---|
| roof | 634.5 | 8.6 | 38.5 | 14.7 | PASS | PASS |
| acoustic canopy | 630.5 | 16.1 | 23.4 | 7.9 | PASS | PASS |
| service_canopy | 633.5 | 18.6 | 24.6 | 8.4 | PASS | PASS |
| boh | 624.5 | 7.3 | 0.9 | 0.3 | PASS | PASS |
| mast_l / mast_r | 638.5 | 3.2 / 1.7 | 1.9 / 1.2 | 0.5 / 0.9 | **FAIL** | FAIL(r) |
| wing_l / wing_r | 624.5 | 4.3 / 2.2 | 0.0 / 1.5 | 0.0 / 0.9 | PASS | PASS |
| apron | 613.5 | 0.0 | 0.0 | 0.0 | PASS | PASS |

**Verdict changes vs the terrain-only baseline:**
- **Masts (26 ft, top 638.5) FAIL the durable S1 neighbor gate** (~635 ceiling; intrude
  ~3 ft into E/S/SE street water views). Masts are seasonal/removable and the screen is
  night-only → **flagged for owner policy (temporary vs permanent), not auto-rejected**.
- **All permanent overhead elements (roof, both canopies, boh, wings, apron) PASS the
  neighbor gate** — their tops (≤634.5) stay below the ~635 S1 ceiling. Roof passes by a
  hair (top 634.5 vs ceiling ~634.6).
- **Overhead elements charge MORE to the audience under S1 than the terrain-only §C
  credited** (roof 8.6→38.5, canopies up 7–8 pts) because the corrected far-shore band
  top is thinner. That charge is **real only if the trees are trimmed** (S1); with trees
  present (S2) it shrinks (roof 14.7%, canopies ~8%) — but must never be waved through on
  canopy leeway (trap #3).

## Bottom line for the owner

1. **The foreground canopy governs the seated bay view.** No seated row is acceptable
   through the current tree line in either leaf state. The design's promised upper-row
   bay view is contingent on trimming/removing third-party (City/MDOT) trees.
2. **The durable design constraint is the S1 neighbor ceiling (~635 ft over the stage).**
   Every permanent element in the section-B menu fits under it; only the 26-ft movie
   masts exceed it — an owner policy call (they are removable), not a hard reject.
3. Every number here carries its **occluder-set (S0/S1/S2) and leaf-state** label, as
   required. Nothing is adopted; owner sign-off is the next step.

### Artifacts
`canopy_silhouette.csv` · `band_top_farshore.csv` · `per_row_bands_by_set.csv` ·
`rn_rm_table.md` · `canopy_top_leafoff_3ft.tif` / `canopy_top_leafon_3ft.tif` ·
`canopy_layer_provenance.json` · `neighbor_receptors.geojson` ·
`neighbor_ceiling_S1.tif/.png` · `neighbor_ceiling_S2.tif/.png` ·
`neighbor_ceiling_summary.json` · `element_verdicts_v2.md` ·
scripts: `build_canopy_layer.py` · `bay_band_v2.py` · `neighbor_ceiling.py` ·
`element_verdicts_v2.py`.
