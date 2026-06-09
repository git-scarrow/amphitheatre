# Scenario B — Spatial Validation (where the earthwork model lied by omission)

**Date:** 2026-06-07
**Driver:** `scripts/validate_scenarioB.py` → `analysis/scenarioB_validation/`
**Supersedes the "all-clear" framing in:** `TERRACE_SWEEP_MEMO.md`

> **Headline (validated):** The extended 24-row geometry is terrain-compatible in *bulk* tread grading, but the prior memo was right for the wrong reason. The next step was never more CY optimization — it is spatial validation. Doing it shows: **clipping happens under seats, not at row ends; the as-built clipped bowl delivers only ~217 compliant formal seats, not 1,452; the full formal bowl is recoverable but only by a selective-restoration pass (Scenario D) that costs ~26 CY of the very fill the clip "saved"; and "self-balancing, no import" is a geometric statement, not a construction one.**

The validation unit is the **row segment** (≈8 ft of arc). A segment is **Band A (formal fixed seat) only if it passes sightline ∧ slope ∧ clipping ∧ surface-continuity simultaneously.** Clipped formal seats do not count as-built; they are earned back only by restoration.

---

## 1. The three prior claims, tested against the actual clipped surface

| Prior memo claim | Verdict | Evidence |
|---|---|---|
| "Fill ends of treads are clipped … those **edges** drain outward" (i.e. clip is at row ends) | **FALSE** | **395** segments clip **under seats** vs **117** at tips. Clipping concentrates wherever natural ground dips below the tread plane — distributed across the bowl, mostly mid-row. See `clipped_fill_heatmap.png`. |
| "Net −0.7 CY — **self-balancing, no truck import required**" | **GEOMETRIC ONLY** | Restoring the formal bowl (Scenario D) needs **+26 CY** of fill the clip dropped. After K=0.95 shrink the tread strip alone still imports **+5.8 CY**. Balance was measured cut-vs-fill in place, not as constructible balance. |
| All 24 rows reported as civic **seating** | **FALSE** | As-built compliant formal seats = **217**, not 1,452. Bands: B=1,349, C=243, D=86. The "1,452 formal" number is achievable, but only *after* restoration. |

The clip itself is not the problem — dropping fill at genuine row-end tips and landscape shoulders is fine. The omission is that **the model never checked where the dropped fill lands**, and most of it lands under seats, dishing the tread.

---

## 2. The key result — capacity is a band distribution, not one number

`analysis/scenarioB_validation/seat_bands.csv`

| Band | Meaning | **As-built Scenario B** | **Scenario D (selective restore)** | weight |
|---|---|---:|---:|---:|
| A | formal fixed seat (all 4 gates pass) | **217** | **1,452** | 1.0 |
| B | informal terrace / lawn (sittable, dished) | 1,349 | 114 | 0.5 |
| C | overflow / lawn edge | 243 | 243 | 0.15 |
| D | landscape / no-count (clipped tips, rim) | 86 | 86 | 0.0 |
| | **quality-banded C_formal** | **928** | **1,575** | |

- **As-built, the 0.5 ft clip demotes 85% of the formal bowl to dished benches** (Band B). They have stage sightlines but fail the seat-surface comfort/continuity gates.
- **Scenario D earns the full 1,452-seat formal bowl back for 25.9 CY** of restoration fill (the unmet fill, replaced only on rows whose *ideal* plane is formal, C_ideal ≥ 90). This is cheap — but it is **not free, and it was hidden inside "self-balancing."**
- Scenario D's A=1,452 / B=114 / C=243 / D=86 reproduces the natural-grade quality bands (`design_extended_bays/quality_bands.md`) — confirming the restoration target is the right one and the bowl geometry is sound.

**Prior numbers for comparison:** raw envelope 1,895 · prior "formal" 1,452 · prior C_formal 1,545. The prior 1,452 was correct as a *target*, presented as a *deliverable*.

---

## 3. Per-priority validation (the requested checklist)

| # | Validation | Status | Result |
|---|---|---|---|
| 1 | Map every clipped-fill cell | ✅ done | `clipped_fill_cells.csv`, `segments.csv`, heatmap. 35.2 CY total unmet; 395 under-seat segments flagged `clip_under_seat`. |
| 2 | Counted-seat mask (quality bands) | ✅ done | Bands A/B/C/D above; only all-gates-pass segments count as A. |
| 3 | Sightlines on the **actual clipped** surface | ✅ done | `row_validation.csv`: C_actual ≈ C_ideal on every row (restore Δ ≤ 0.05 ft). **Row-median sightlines survive clipping** — the damage is local seat-surface dishing, not loss of stage view. This is the one place the bowl is genuinely robust. |
| 4 | ADA / aisles / cross-aisles / landings in earthwork | ⚠️ **NOT validated** | No aisle/ADA layout exists; `accessible_route_required`/`wheelchair_space_required` emitted as `False` placeholders. **Likely the next real earthwork driver** — must be designed before any cost number. |
| 5 | DEM vs field survey | ⚠️ **NOT validated** (proxy run) | No survey on hand. Proxy = ±0.5 ft correlated-noise test (gate 8). Use LiDAR for concept tuning only, never final quantities. |
| 6 | Drainage after clipping | ⚠️ partial | Clip dishes treads (local cross-slope spikes to 5–7%, §4) → water pools mid-tread instead of draining outward. Slope direction flagged; **runoff/swale sizing not done.** |
| 7 | Full construction envelope | ✅ done (geometry) | `envelope_earthwork.csv`: tread strip 288 CY gross → tread+back-strip envelope **957 CY gross (3.3×)**. The 3.6 ft strip omits risers, back walking strip, footings, feathering, drainage. Report tread CY and venue CY separately. |
| 8 | ±0.25–0.5 ft DEM/survey sensitivity | ✅ done | `sensitivity.csv`: under 5 noise seeds, earn-back formal rows = 15–16 (stable), seat-zone clip cells 2,731–3,404. **The "clip is under seats" verdict is robust to planning-grade DEM error.** |

---

## 4. What the clip does to the seating surface (segment evidence)

Slope is measured by **least-squares plane fit per segment** on the as-built surface — not raster gradient, which on a 3.6 ft (≈4-cell) tread bleeds the inter-row riser into every cell. Example, Row 12 bend (`segments.csv`):

| station | C_band | cross% | long% | slope | clip_under_seat | formal_allowed | repair CY |
|---|---|---:|---:|---|---|---|---:|
| r12_bend_08 | A | 2.0 | 0.3 | pass | no | **True** | — |
| r12_bend_09 | A | 1.8 | 0.5 | pass | yes | False | 0.02 |
| r12_bend_11 | A | **6.6** | 0.3 | fail | yes | False | 0.14 |
| r12_bend_13 | A | **6.7** | 2.7 | fail | yes | False | 0.13 |

The clean segment is at the **start** of the arc; the dished, clipped, slope-failing segments are in the **middle** of the row. Design cross-slope is 2.0%; where the clip drops fill, the tread tilts to 5–7% — a comfort and drainage failure invisible to the ideal-plane model.

---

## 5. Construction vs geometric balance (priority 6 honesty)

`TERRACE_SWEEP_MEMO.md` should read **"geometric balance," not "construction balance."** Open items before any balance claim:
- **Shrink/swell:** tread-strip fill demand 143 CY vs usable compacted (cut × 0.95) 137 CY → **+5.8 CY shortfall** before restoration.
- **Restoration:** Scenario D adds **+26 CY** of fill to recover formal seats.
- **Haul:** 11 ft cut-centroid→fill-centroid (short — the one genuinely favorable number).
- **Topsoil:** 359 CY stripped separately, **not** structural fill (already isolated in the sweep — keep it isolated).
- **Soil suitability** of cut as structural fill: **unknown — needs geotech.**
- **Construction envelope** gross is **3.3× the tread-strip gross.**

---

## 6. Objective function — stop counting every row-foot as equal

Reframed per the tuning brief:

```
U = w1·formalA + w2·lawn(B,C) + w3·sightline − w5·gross_CY − w6·import_CY
    (w4 access, w7 drainage, w8 constructability = NOT SCORED: data-gated)
```

| | formal A | lawn (B+C) | gross CY | import CY | **U** |
|---|---:|---:|---:|---:|---:|
| As-built Scenario B | 217 | 1,592 | 288 | 5.8 | **758** |
| Scenario D (restore 26 CY) | 1,452 | 357 | 314 | 5.8 | **1,621** |

Spending 26 CY of restoration roughly **doubles** the objective by converting dished benches into formal seats. The decision is not "Scenario B vs A" on CY; it is **"adopt Scenario B's clip savings, then buy the formal bowl back with the cheapest targeted restoration."**

---

## 7. Pass/fail gates (status)

1. No counted formal seat on a clipped-fill failure zone — ✅ **enforced** (as-built A excludes all `clip_under_seat`).
2. Every formal segment passes C ≥ 90 mm on the actual surface — ✅ (C_actual ≥ 90 on all Band-A and restorable rows).
3. Every formal tread acceptable cross/long/twist — ✅ as-built A; restorable-A guaranteed by the restored plane.
4. Rows 21–25 classified honestly — ✅ Band D / shoulder (clipped single-section geometry).
5. ADA routes & cross-aisles in earthwork — ❌ **NOT done** (data-gated; next driver).
6. Drainage moves water off treads — ⚠️ **at risk** (clip dishes treads); swale design pending.
7. Cut/fill adjusted for topsoil/unsuitable/shrink/compaction — ⚠️ partial (topsoil + shrink done; soil suitability pending).
8. Survives ±0.25–0.5 ft DEM/survey sensitivity — ✅ **passes** (verdict stable across 5 seeds).

**Gates 5 and 6 are the live blockers.** Everything the LiDAR + geometry can answer, passes or is honestly quantified; the remaining failures need an aisle/ADA layout and a drainage pass, not more CY tuning.

---

## 8. Next scenario set (recommended)

- **Adopt Scenario D** (B + selective sightline/surface restoration, 26 CY) as the formal-capacity design of record — *not* as-built Scenario B.
- **Scenario E** = D + aisles + cross-aisles + ADA routes + landings + construction envelope. **Scenario E is the first number discussable as a project-cost proxy.** It requires an aisle/ADA layout that does not yet exist.
- Re-run `validate_scenarioB.py` after the aisle layout lands; wire `accessible_route_required` / `wheelchair_space_required` to real geometry and re-band.

## Outputs

```
analysis/scenarioB_validation/
  segments.csv              canonical per-segment table (24-column schema)
  row_validation.csv        per-row C_actual / C_ideal / unmet / restore
  seat_bands.csv            A/B/C/D as-built vs Scenario D
  envelope_earthwork.csv    tread strip vs construction envelope
  sensitivity.csv           ±0.5 ft DEM-noise robustness
  validation.json           machine-readable full result
  clipped_fill_heatmap.png  where the clip lands (keystone visual)
scripts/validate_scenarioB.py   reproducible driver
```
