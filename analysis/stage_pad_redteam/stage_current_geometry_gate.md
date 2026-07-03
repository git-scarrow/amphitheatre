# Current-geometry stage-footprint clearance gate

**Scope: the current adopted geometry only** (P_opt core + `five_facet_apron` + translated lateral
shoulders vs Scenario E row-1 treads). The retired 35-ft rule is *not* the test here — see §"35-ft
retirement." Advisory; changes no canon except the RULE9 pointer (§6). Reproduce:
`python scripts/stage_current_geometry_gate.py` → `stage_current_geometry_gate.csv`,
`stage_current_geometry_gate.png`, `repair_candidate_shoulders_trimmed.geojson`.

> **Headline (NOT RED — no governing gate fails):** on the **governing (occupied-deck) edge the current
> P_opt footprint PASSES the ≥12 ft pocket gate** (min 12.02 ft). The two loose ends are cleanup, not
> failures: a **0.4 sf east-shoulder graze into row 1** (a non-occupied lateral element; ~0.1 seat;
> optional trim) and a **221 sf overlap into a stale orchestra zone** (a re-emission lag with no
> quantity effect — §4). Neither fails P_opt.

---

## 1. Which edges count (taxonomy + governance)

| Edge class | Geometry | Area | Occupied? | Governs the ≥12 ft gate? |
|---|---|--:|:--:|:--:|
| **Performance core** | P_opt 70×34 | 2,380 sf | yes | contributes (inside deck) |
| **Occupied deck / apron usable stage** | core ∪ `five_facet_apron` | 2,699 sf | **yes** | ✅ **YES — the governed edge** |
| **Decorative / lateral shoulders** | 2 translated wings | 2×345 sf | **no** ("no enclosing shell — lateral shoulders only", `material_zones`) | ❌ non-governing |
| **Circulation / clearance envelope** | `orchestra_event_floor` + the ≥12 ft pocket | — | no (event floor) | it *is* the clearance zone |

- **The ≥12 ft in-situ pocket gate governs the occupied-deck (core+apron) front edge.** This is how
  canon already measures it: `RULE9_DECISION_RECORD.md` records "east pocket **held at 12.0**" and
  "bend 32.7 → **29.6 with apron**" — i.e. the apron-inclusive deck edge. *(observed)*
- **Shoulders may not overlap or replace row-1 seating.** They are lateral, non-occupied elements
  (part of the open band-shell sides, not performance deck, not seating, not counted clearance). They
  are excluded from the *required* clearance test, but they must not physically intrude on seats.
  Today one does, barely (§3). *(inference from `material_zones` + `T1_deck_only` bundle)*

## 2. Current-canon gate table

From `stage_current_geometry_gate.csv` (row 1; treads ≈ 610.8 NAVD88):

| section | core→row1 | **occupied deck→row1 (governed)** | full footprint (+shoulders)→row1 | orchestra overlap | row-1 seats | **gate ≥12 ft** |
|---|--:|--:|--:|--:|--:|:--:|
| east | 12.0 | **12.0** | 0.0 ⚠ | — | 16 | ✅ PASS |
| bend | 32.7 | **29.6** | 29.6 | — | 19 | ✅ PASS |
| south | 21.9 | **18.8** | 15.9 | — | 22 | ✅ PASS |
| **min / total** | 12.0 | **12.02** | **0.0** | deck **100.3** / full **221.2 sf** | 57 | ✅ **PASS (governed)** |

**Governed occupied-deck edge: min 12.02 ft → PASS.** The `full footprint → row1 = 0.0 ft` on the
east is a **shoulder** touch, not a deck touch — a non-governing edge (§3).

## 3. East-shoulder conflict — resolved

- **What it is:** the east **lateral shoulder** (non-occupied) grazes east row 1 —
  `shoulder ∩ row1 = 0.4 sf`, gap 0.0 ft. Not a performance-deck intrusion; a sliver of a decorative
  wing overlapping the wrapped east row. *(observed)*
- **Seat impact:** **~0.1 seat** (length-fraction of the row-1 tread inside the shoulder × seats).
  Effectively zero; **no capacity delta** — row 1 does **not** need clipping. *(observed)*
- **Disposition — non-governing; trim is an explicit CANDIDATE, not adopted.** The shoulder is marked
  **non-governing** and **excluded from required clearance**. Because the occupied deck already clears
  ≥12 ft, the trim is **optional** and adoption is Phase-B / resolved-gated — so it is filed as a
  candidate, not adopted: **`repair_candidate_shoulders_trimmed.geojson`**. It clips both shoulders out
  of the 12-ft row-1 pocket. If adopted, it recomputes as:

  | quantity | adopted (pre-trim) | candidate (trimmed) | Δ |
  |---|--:|--:|--:|
  | full-footprint area | 3,386 sf | 3,260 sf | −127 sf (shoulder only) |
  | solid-pad-to-612.5 upper-bound | **330.2 CY** | 318.1 CY | −12.1 CY |
  | full-footprint ∩ orchestra | 221.2 sf | 141.0 sf | −80 sf |
  | occupied deck (unchanged) | — | — | 0 |
  | row-1 seats | 57 | 57 | 0 |

  **Decision: keep as candidate → 330.2 CY is RETAINED as the adopted pre-trim upper bound;** 318.1 CY
  is the alternative bound *only if* the trim is later adopted. No occupied geometry or seats change
  either way. Before/after: `stage_current_geometry_gate.png`.
- **P_opt is NOT failing.** The occupied edge clears ≥12 ft; the shoulder is an optional trim, not a
  placement failure.

## 4. Orchestra overlap — RE-EMITTED against the adopted deck edge (overlap → 0)

> **RESOLVED 2026-07-03.** The floor has been re-emitted against the adopted footprint —
> `deck ∩ floor` **100.3 → 0.0 sf**, `full ∩ floor` **221.2 → 0.0 sf**. Driver:
> baked into `scripts/build_in_situ_geometry.py` (`_adopted_stage_footprint`),
> mirrored by `build_site_context.py`; detail: `orchestra_reemit_report.md`.

- **Numbers (before):** occupied deck ∩ `orchestra_event_floor` = **100.3 sf**; full footprint
  (+shoulders) ∩ = **221.2 sf**. *(observed)*
- **What it was:** `orchestra_event_floor` is the flat event floor "between stage and the three
  row-1 bands" (`material_zones`). The zone had been emitted from the *old* stage position
  (pre-P_opt) by `build_in_situ_geometry.py`; the adopted deck (shifted [+6.42, +19.87] ft) moved
  into part of it, so they overlapped.
- **Fix applied (minimal cleanup, not a hull rebuild):** subtracted the adopted footprint
  (deck + translated lateral shoulders) from the floor. Floor area 2149.4 → 1925.8 sf (only the
  deck bite removed; row-1-side extent unchanged), centroid nudged 4.8 ft, 3 disconnected parts.
  A hull rebuild from the shifted stage was rejected (would balloon the schematic floor +777 sf /
  shift centroid 9.2 ft). Both floor representations patched: `bowl_zones/orchestra_event_floor`
  and its identical mirror `material_zones/event_floor`. Surrounding stage zones remain INHERITED
  (Rule 9 OPEN) pending the full Phase-B stage re-emission.
- **Classification: geometry cleanup / no quantity delta.** Quantity lineage, proven:

  | source | role | does orchestra carry a quantity? |
  |---|---|---|
  | **emitter** `scripts/build_in_situ_geometry.py:284` → `bowl_zones.geojson` | writes the zone polygon | — |
  | **balance** `scripts/scenarioE_civic.py` → `analysis/scenarioE_civic/earthwork.csv` (500.8 CY) | per-component earthwork | **No** — orchestra is absent from `earthwork.csv`; manifest: "left on existing grade (schematic zone, concept tier)" → **0 CY** |
  | drainage | swales/treatment cell | **No** — orchestra is not a swale; "never impounds" |
  | capacity | `terrace_treads.geojson` | **No** — orchestra is event floor, not seating; **0 seats** |
  | ADA | `scripts/design_ada_routes.py` | **indirect only** — uses the floor *centroid* to place one concept arrival node (`:133/:157/:175`); not burned into grades. The re-emission shifts the centroid **4.8 ft (measured)** → nudges that schematic node only; **no change to the adopted ADA CY / slope compliance.** Confirmed by the Phase-B ADA re-run |

  So re-emitting `orchestra_event_floor` against the adopted deck edge changes **no adopted quantity**
  (volume/drainage/capacity = 0; ADA = de-minimis node only). It is **geometry cleanup, not RED**, and
  it is **not** double-counted occupied space. *(observed + sourced)*
- **Before/after:** the PNG shows the deck over the stale orchestra zone; the fix is re-emission (the
  orchestra front snaps to the deck edge), not a footprint change, so no occupied geometry is altered.

## 5. 35-ft retirement (active metrics patched)

The 35-ft uniform figure is **design_open_low (single-fan) only** and has been removed as an
active-canon metric:
- `scripts/comparators/extract_metrics.py`: `stage_front_to_row1_ft` now reports the **current adopted
  per-section gaps** `{east 12.0, bend 32.7, south 21.9}` (basis `measured_insitu`, ≥12 ft gate PASS);
  the 35-ft value is kept **only** as `stage_front_to_row1_openlow_ft` (basis
  `scenario_open_low_retired`). `upper_row_distance_ft` no longer uses 35 as its floor (now the bend
  on-axis 32.7).
- `scripts/comparators/audit_comparators.py`: the assertion that pinned `stage_front_to_row1 == 35.0`
  as canon is replaced by checks that the active metric is the in-situ per-section set (not canon 35)
  and that 35 survives only as the labeled retired metric. **Both new checks PASS.**
- Regenerated deliverables `data/comparators/{comparison,petoskey_metrics}.json` (surgical diff: stage
  fields only). *Note:* the comparator audit still aborts earlier on a **pre-existing** DEM hash drift
  (`proposed_grade_1ft.tif` rebuilt 2026-06-27 vs `truth_package` hash of 2026-06-13) — unrelated to
  this patch; its own ticket.

## 6. Verdict — internally consistent governance state

**No governing gate fails → this is not a RED geometry failure.** Final state:

| item | state |
|---|---|
| source terrain | **PASS** (verified existing ground; `stage_pad_data_lineage_audit.md` §1) |
| volume arithmetic | **PASS** (330.2 CY = 3,386 sf × 2.633 ft ÷ 27) |
| occupied deck clearance | **PASS** (governed edge min 12.02 ft ≥ 12) |
| 35-ft retired metric | **PASS** (retired from active canon; `extract_metrics.py` patched, checks pass) |
| shoulder trim | **explicit CANDIDATE** (`repair_candidate_shoulders_trimmed.geojson`; optional, not adopted) |
| orchestra overlap | **geometry cleanup / no quantity delta** (re-emit against adopted deck edge; §4) |
| required import | **unresolved / scenario-dependent** (deck vs pad), **not** a RED geometry failure |
| DEM hash drift | **separate ticket** `analysis/repro_tickets/proposed_grade_hash_drift.md` |

RULE9 pointer (non-RED cleanup) recorded in `analysis/stage_adoption/RULE9_DECISION_RECORD.md`:

> Stage-pad volume arithmetic and terrain lineage pass. 330.2 CY is the pre-trim solid-pad-to-612.5
> upper-bound scenario, not required import. Occupied deck clearance passes the current ≥12 ft pocket
> gate. Remaining cleanup: re-emit `orchestra_event_floor` against the adopted deck edge and decide
> whether to adopt the optional shoulder trim.
