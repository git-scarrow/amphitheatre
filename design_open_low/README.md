# Open Civic Bowl — minimal-work, open-arc amphitheater

**Petoskey Pit, Bayfront Park, Petoskey, Emmet County, MI.** Planning-grade.
NAVD88 (Geoid12A) intl ft · CRS **EPSG:6494**. Audience faces **az 330°** (NNW — bay + evening sun).

> ⚠ **Planning-grade, not stamped engineering.** Geometry is fit to public LiDAR
> (`dem/dem_design_1ft.tif`) plus labelled assumptions. The field/permit prerequisites in
> [`../gating_dossier.md`](../gating_dossier.md) still govern before any construction.

> ## ⛔ SUPERSEDED FOR SEATING (2026-07-02)
> **This "Open Civic Bowl" seating geometry is not governing.** The **±55° / 110° open arc**,
> **16-row / R130 stop**, uniform **35 ft stage-to-row-1**, and **~1,797 / 1,472 seat** figures
> below describe a retired low-intervention *alternative*. Per
> [`../docs/POST_EMISSION_DECISION_MEMO.md`](../docs/POST_EMISSION_DECISION_MEMO.md),
> `design_open_low`'s single-fan geometry **"must not be used as governing geometry"** for seating.
>
> **The validated object is the Scenario E three-section civic bowl** (east / bend / south,
> **~130° effective span**): **18 rows** climbing the continuous **~20° bowl wall**, plus two
> emission-validated expansion tiers to rows 19–20 → Band-A **1,243 baseline / 1,357 modest /
> 1,505 ambitious** seats ([`../SCENARIO_E_CIVIC.md`](../SCENARIO_E_CIVIC.md),
> `../analysis/tier_emission/TIER_EMISSION_VALIDATION.md`). At the selected **P_opt** stage
> placement the row-1 gaps are **12.0 / 32.7 / 21.9 ft by section**, not a uniform 35 ft
> (`../analysis/in_situ_normalization/STAGE_SHAPE_STUDY.md`). The "retaining band" mentioned below
> was proven an **artifact of the retired narrow-fan design, not a terrain condition**
> (`../analysis/east_flank_reality_check/REASSESSMENT_MEMO.md`).
>
> **What still survives from this file:** only the **inherited stage object** (az-150 footprint,
> Rule 9 **OPEN**) and the **treatment cell** — not the seating fan. Retained as historical record.

---

## The idea

The first design (`/package`, Stage 4/5) is a **tight rake on a narrow arc** — ±30° (60°), 30 rows
driven straight **up the steep S/SSE wall**, which forces rim-flatten fill and **6–14 ft structural
retaining walls** (the bulk of its cost). This design does the opposite move, and the terrain rewards it:

- **Open the arc** to **±55° (110° total)** — wider, less constrained.
- **Stop low** at **16 rows / R 130 ft**, *below* the rim-flatten + retaining band.

Because the bowl's S/SE wall **is already a ~33% natural rake (~18°, gentler than Epidaurus' ~26°)**,
the seat treads land on existing grade. Opening the arc recovers (and exceeds) the capacity lost by
using fewer rows — each row is longer.

**Stage forward.** The first design parked the stage at the *far (bay) edge* of the flat pan, so
the whole 85-ft pan fell *between* stage and audience. Here the stage is pushed **forward into the
orchestra**, so the front row is **35 ft from the stage front** (not 85) and the flat pan, the
**dry/ephemeral treatment cell**, and the **distant bay (~200 m)** sit *beyond* the stage as the
scenic foreground. Pulling the stage that close steepens the front sightlines, so the **front ~5 rows
take ≤0.2 ft of fill (~9 CY total)**; sightlines are re-derived to the nearer focus and clear 90 mm in
**all 16 rows as designed**. The fill is confined to the front — the back rows carry 150–280 mm of
clearance surplus, which absorbs the re-rake so nothing behind is blocked and the bowl gets no taller.

**Water note.** The treatment cell holds **no permanent water** — it is a dry bioretention/infiltration
cell that ponds only shallowly and transiently after large storms (≈0.9 ft after the WQ storm, ≈2.2 ft
after the 100-yr; in well-draining soil, not at all). A standing "reflecting pool" would have to be
engineered (liner/makeup water or a perched table) and is **not** assumed here. The bay is the distant
view ~200 m NNW, not an on-site water body.

**Setting note — open-air, not a room.** This is a landscape venue, not an enclosed hall: no walls,
no ceiling, no back wall. The audience faces NNW *over* the stage, so the **backdrop is the open
foreground (treatment cell) → middle distance → Little Traverse Bay + sky** — the view is the set.
Consequence: the stage stays **low and open on the bay (upstage) side** — the side "shoulders" are
**lateral, floor-level framing** (band-shell logic for projection toward the seating), **not** an
enclosing wall, and there is deliberately **no tall upstage shell or fly tower** that would block the
bay view. Stage presence is judged against the open landscape and the seating fan, not an enclosure.

## What it delivers

| Metric | Open Civic Bowl | First design (`/package`) |
|---|---|---|
| Fan / arc | **±55° (110°)** | ±30° (60°) |
| **Stage** | **70 × 34  ft core + angled side shoulders (~104 ft frontage)** | 52 × 26 ft |
| Stage frontage vs row-1 arc (~163 ft) | **~64%** (anchors the fan) | ~32% |
| **Stage front → row 1** | **35 ft** | 85 ft |
| Rows · rise | **16 · ~15 ft** | 30 · ~30 ft |
| Seats (compact / generous)¹ | **~1,797 / ~1,472** | ~2,192 / ~1,794 |
| **Seat-tread earthwork** | **≈ 9 CY — front ~5 rows ≤0.2 ft, rest on grade** | fill-only, 5 upper rows regraded |
| **Retaining walls** | **none** (ends ~11 ft below the steep band) | 6–14 ft over ~0.083 ac |
| Sightlines (90 mm C) | **all 16 rows pass on BARE terrain** | 25/30 on terrain; rest regraded |
| Accessible-route drop | A ~6 ft · B ~8 ft | A 5.3 ft · **B 10.5 ft** |

¹ Geometric planning estimate only — **not** a code occupant load or event cap (see `seat_count.md`, `../gating_dossier.md` H-2/H-2b).

## Constraints satisfied

- **Minimal work / materials / labor** — seating on the natural rake (~9 CY tread fill, front rows only), **no retaining walls**;
  remaining earthwork is only the shared stage/forecourt pad, ADA ramps, and treatment-cell shaping, all cut-balanced on site (**never imports fill**).
- **Less constrained than the first design** — arc opened 60° → 110°, rake eased, bowl height halved.
- **Drainage logic preserved** — bowl bottom kept at **609.1 ft as the treatment cell** (the `treatment_wet_cell` polygon is reused verbatim); event floor **612.5 ft**, ~1.2 ft over the 100-yr WSEL (Stage 3). Nothing about the stormwater train changes.
- **ADA plausible** — the closed rim still needs engineered ramps, but the **15 ft bowl (vs ~30 ft)** makes them shorter; Route A to the floor, Route B to a level mid cross-aisle with wheelchair dispersion.

## Files (the design)

| File | What |
|---|---|
| `plan_and_sections.png` | the design drawing — plan (110° fan on hillshade), centerline section (treads on grade), per-row C-value |
| `seating_rows.geojson` | 16 terraced row arcs, per-row tread/terrain/cut-fill/C-value/seats (EPSG:6494) |
| `stage_floor.geojson` | focal point, stage, opened forecourt sector, **treatment cell (reused)**, bay-view axis |
| `ada_route.geojson` | Route A (floor), Route B (mid), level cross-aisle |
| `sightline_table.csv` | per-row geometry + sightline + seat table |
| `seat_count.md` | capacity, earthwork, sightline, ADA summary |

## Reproduce

```bash
source .venv/bin/activate
python scripts/design_open_low.py        # geometry → geojson/csv
python scripts/design_open_low_plot.py   # figure + seat_count.md
```

Parameters (arc, rows, radii) are at the top of `scripts/design_open_low.py`. The sweep that
chose them is `scripts/design_open_low_sweep.py` (fan × outer-radius vs seats/fill).
