# DR-1 tower-floor per-floor summary — water-band clear% by occluder set

Observers: **138** plan-grid positions over pit parcel `52-19-06-224-001` (2.01 ac outer envelope) @ 25 ft spacing [ASSUMPTION: plate grid, pipeline's choice per DR-1].
Floors 2-8: plate = 618 + 12·floor ft; eye = plate + 5 ft.
Band top = far-shore waterline (D3). Corridor az 318-342° at 2° (13 rays).
clear% = fraction of corridor rays seeing water. verdict: acceptable ≥80 · marginal 40-79 · blocked <40.

**Occluder sets (D2):** S0 terrain · S1 +stage+city (**durable**) · S2_leafoff canopy 2015-05-02 (**measurement, contingent**) · S2_leafon canopy crown-opacity (**assumption, contingent**). Canopy-removal band gain = clear%(S1) − clear%(S2) — what de-treeing buys.

Values are **median [p25–p75 IQR]** across grid positions.

| floor | eye ft | S0 | S1 | S2 leaf-off | S2 leaf-on | gain leaf-off | gain leaf-on |
|---|---|---|---|---|---|---|---|
| 2 | 635.0 | 100.0 [100.0–100.0] | 100.0 [53.8–100.0] | 15.4 [0.0–51.9] | 7.7 [0.0–46.2] | 46.2 | 53.8 |
| 3 | 647.0 | 100.0 [100.0–100.0] | 100.0 [84.6–100.0] | 61.5 [46.2–76.9] | 53.8 [30.8–76.9] | 19.2 | 23.1 |
| 4 | 659.0 | 100.0 [100.0–100.0] | 100.0 [100.0–100.0] | 100.0 [100.0–100.0] | 100.0 [100.0–100.0] | 0.0 | 0.0 |
| 5 | 671.0 | 100.0 [100.0–100.0] | 100.0 [100.0–100.0] | 100.0 [100.0–100.0] | 100.0 [100.0–100.0] | 0.0 | 0.0 |
| 6 | 683.0 | 100.0 [100.0–100.0] | 100.0 [100.0–100.0] | 100.0 [100.0–100.0] | 100.0 [100.0–100.0] | 0.0 | 0.0 |
| 7 | 695.0 | 100.0 [100.0–100.0] | 100.0 [100.0–100.0] | 100.0 [100.0–100.0] | 100.0 [100.0–100.0] | 0.0 | 0.0 |
| 8 | 707.0 | 100.0 [100.0–100.0] | 100.0 [100.0–100.0] | 100.0 [100.0–100.0] | 100.0 [100.0–100.0] | 0.0 | 0.0 |

Gain column = median over positions of per-position (S1 − S2) clear%. 0 (floor,position) cells fell back to the open-water dip band top on ≥1 ray (no far-shore waterline within DEM reach); flagged in the per-position CSV (`uses_dip_fallback`).

**Leaf state labels are load-bearing:** leaf-off is the winter-screen MEASUREMENT (2015-05-02 3DEP); leaf-on is a crown-opacity ASSUMPTION and the season-relevant one (summer is the operating season). No observer is credited a water view on S2 leeway alone — S2 columns are contingent on third-party (City / MDOT) canopy.

