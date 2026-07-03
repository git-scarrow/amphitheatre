# Stage placement / row-1 clearance — RED issue addendum

**Status: 🔴 RED — unresolved.** Advisory. Changes no canon (this addendum only *marks* the
placement/clearance issue RED, per instruction). Companion to `stage_pad_data_lineage_audit.md`.
Reproduce: `python scripts/stage_placement_clearance.py` →
`stage_placement_clearance.csv`, `stage_placement_clearance.png`.

> **Gate language (carry verbatim):** *Stage volume arithmetic and source terrain pass. The ~330 CY
> figure is valid only as the solid-pad-to-612.5 upper-bound scenario. Required import remains
> unresolved. A separate RED issue is now stage placement: current P_opt clearances appear
> inconsistent with the stated 35-ft stage-front-to-row-1 design rule.*

---

## The contradiction

| | value | source |
|---|---|---|
| Stated design rule | stage front → row 1 = **35 ft** (uniform) | brief; `design_open_low` docs; `scripts/comparators/extract_metrics.py:188` (`STAGE_FRONT_TO_ROW1 = 35.0`) |
| Current adopted clearance | **{east 12.0, bend 32.7, south 21.9} ft** | `analysis/in_situ_normalization/adopted_stage_footprint.geojson`; **matches `DESIGN_CANON.md:145`** |

No side confirms 35 ft. The audit reproduced the canon gaps exactly (core-front → row 1 =
12.0 / 32.7 / 21.9), so this is **not a measurement error in the audit** — the two numbers describe
**two different geometries**.

## Cause — evaluated against A–E

| Hyp. | Verdict | Evidence |
|---|---|---|
| **A. 35-ft standard is stale** | **PRIMARY — true** | 35 ft is native to the **retired** `design_open_low` single-fan (concentric, row 1 at radius 85, uniform 35-ft setback). `design_open_low/seat_count.md` labels that whole geometry "a retired alternative." **No 35-ft rule appears in current `DESIGN_CANON.md`;** it survives only in `design_open_low/` docs and the comparator module. Current canon (Rule 9, 2026-07-02) adopted a **≥12 ft pocket gate**, not a 35-ft setback (`DESIGN_CANON.md:145,174`). |
| **B. P_opt is not the adopted placement** | **False (but provisional)** | P_opt **is** the adopted placement — but `carried_provisional`, not `resolved` (`DESIGN_CANON.md:15`). The tight gaps were *explicitly declared* on adoption ("row-1 gaps 12.0/32.7/21.9 ft, all ≥ 12"). So the clearances are intentional-provisional, not accidental. |
| **C. Clearance measured from the wrong stage edge** | **Contributing** | Canon `front_to_row1` is measured from the **core** downstage edge (`stage_shape_study.py:292`, `rect(P,az,35,-34)` = the 70×34 core), **excluding the five-facet apron** that projects toward the audience. Measured to the actual **deck (core+apron)** front, gaps shrink: bend 32.7→**29.6**, south 21.9→**18.8** (east unchanged, no apron there). The canon number understates intrusion. |
| **D. Audit row-1 ≠ current adopted row-1** | **False — they are the same** | Both use Scenario E `terrace_treads.geojson` row 1. The 35-ft/613.5 figures come from `design_open_low`'s *different* row-1 geometry (radius-85 single fan). The audit's row 1 **is** the current adopted row 1 (tread elev 610.83 ≈ existing 610.82). |
| **E. Stage intrudes into orchestra/forecourt space** | **True** | Adopted footprint **∩ `orchestra_event_floor` = 221.2 sf** (`stage_pad_overlap_audit.csv`). Front rows 1–4 carry `zone: "forecourt"`. The compressed east clearance (12 ft, or 0 ft to the shoulder — see below) consumes the orchestra buffer the 35-ft rule preserved. |

**Bottom line:** the 35 ft is a **stale rule (A)** attached to a **superseded geometry (D-mismatch)**;
the current adopted geometry uses a **≥12 ft pocket gate**, its canonical gaps **understate** the true
clearance because they omit the apron **(C)**, and the deck **intrudes 221 sf into the orchestra
floor (E)**. The placement is internally consistent with *current* canon but **contradicts the
historical 35-ft orchestra-buffer rule with no design record reconciling the change** — hence RED.

## Measured stage-edge-to-row clearances (by segment)

Full table: `stage_placement_clearance.csv`. Row 1 (all tread elev ≈ 610.8):

| section | core-front (canon) | deck-front (+apron) | full footprint (+shoulders) | shortfall vs 35 ft |
|---|--:|--:|--:|--:|
| east | 12.0 | 12.0 | **0.0** ⚠ | 23.0 |
| bend | 32.7 | 29.6 | 29.6 | 2.3 |
| south | 21.9 | 18.8 | 15.9 | 13.1 |

⚠ **East full-footprint → row 1 = 0.0 ft:** the east stage **shoulder abuts row 1** (hard adjacency).
Bend is near the 35-ft locus (33 ft); east and south fall well inside it.

## Row-elevation reconciliation (resolves the "613.5" citation)

| figure | value | what it actually is | current? |
|---|--:|---|:--:|
| this audit "row 1" | 610.82 (existing) / **610.83** (proposed tread) | Scenario E row 1, `terrace_treads.geojson` `tread_elev_navd88` | ✅ current |
| prior summaries "row 1 ≈ 613.5" | **613.54** | **`design_open_low` row 1** (retired single-fan, radius 85) | ❌ stale |
| possible confusion | 613.03 | Scenario E **row 3** (not row 1) | current, wrong row |

The "613.5" is the **superseded** `design_open_low` row-1 tread — same lineage as the 35-ft rule. In
current Scenario E, row 1 = 610.8; 613 is reached at **row 3**. The audit's 610.82 (existing) matches
the adopted proposed tread 610.83 because row 1 sits ~on grade (z_resid 0.17 ft). **No conflict — two
different design generations.**

## Plan-view diagnostic

`stage_placement_clearance.png` — current adopted stage core / five-facet apron / shoulders, row 1
(forecourt) and row 2 by section, `orchestra_event_floor`, the P_opt core centre, per-section
clearance leaders (12 / 33 / 22 ft), and the **35-ft rule locus** (front edge offset 35 ft
downstage). Bend row 1 lands near the locus; east and south sit well inside it; the deck overlaps the
orchestra floor.

## Disposition (to clear RED)

1. **Decide whether the 35-ft orchestra-buffer rule still governs.** If yes, P_opt (12 ft east,
   0 ft to the east shoulder) fails it and must move — but a full shift (P_lat) touches east row 1 and
   is infeasible (`DESIGN_CANON.md:162`). If no, **retire the 35-ft figure explicitly** (it still lives
   in `extract_metrics.py:188` as "canon") so the comparator module and DESIGN_CANON stop disagreeing.
2. **Re-measure `front_to_row1` from the deck (apron) edge, not the core** — the governing clearance
   is 29.6 / 18.8, and 12.0/0.0 on the east.
3. **Resolve the 221 sf orchestra intrusion + the east-shoulder-to-row-1 = 0 ft adjacency.**

Until (1)–(3) are recorded, **stage placement/clearance = RED**.
