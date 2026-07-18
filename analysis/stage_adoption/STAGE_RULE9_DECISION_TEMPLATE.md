# Rule 9 — adopted stage direction record

_This records the owner-selected human direction for `DESIGN_CANON` Rule 9. Its
geometry-dependent closure gate remains non-passing until the chosen geometry is emitted
and validated. See `docs/POST_EMISSION_DECISION_MEMO.md` for the distinction from the
seating-tier decision._

## What Rule 9 requires (facts on file)

The inherited stage (`design_open_low`, axis az 150°) does not match the emitted
three-section seating: centroid-frame mismatch **+25.4°**, lateral offset **−22.3 ft**,
effective fan span ≈130° vs the declared 110°/±55° (`analysis/in_situ_normalization/
section_balance.json`, `analysis/stage_refit/STAGE_REFIT_SWEEP.md`). Closure = adopting
a stage geometry + fan declaration that matches the emitted seating, or explicitly
accepting the mismatch with reasons.

## Constraints that bind this decision

1. **Visual-envelope rule, not height.** A stage candidate is judged by *incremental
   obstruction against the NW rim silhouette* (bay/foreground obstruction %), never by
   height per se. Taller utilitarian mass (incl. a roof) is acceptable where the
   obstruction study clears it (`analysis/in_situ_normalization/STAGE_SHAPE_STUDY.md`,
   `stage_typology_scores.json`).
2. **Decoupling.** Seating geometry may not be used to justify stage placement; the
   stage must justify itself (`analysis/stage_seating_decoupling/CIRCULARITY_AUDIT.md`).
3. **Open-air canon.** No view-blocking upstage wall; backdrop stays bay + sky.

## Candidates on file

| Candidate | Mismatch (sweep sign) | Lateral ft | Row-1 gap E/B/S ft | Bay obstr % | Foreground obstr % | Earthwork CY | Source |
|---|--:|--:|---|--:|--:|--:|---|
| P_inherited (az 150, status quo) | +25.4 | −22.3 | 17.3 / 20.6 / 2.2 | 0.0 | 0.0 | 0 | STAGE_SHAPE_STUDY §A |
| P_opt refit (az 150, solved from residuals) | +6.3 | −6.7 | 12.0 / 32.7 / 21.9 | 0.0 | 1.7 | 37.8 | STAGE_SHAPE_STUDY §A / tier recipe |
| + five-facet apron (319 sf, 6.0 ft projection) | — | — | 12.0 / 29.6 / 18.8 | 0.0 | 1.1 | ~8.9 | STAGE_SHAPE_STUDY §A2 |
| Typology shortlist (incl. roofed band-shell options) | per option | — | — | per option | per option | — | stage_typology_scores.json |

## Decision record

**Owner decision recorded 2026-07-18.**

- Chosen path: **A — audience-axis alignment**.
- **Target axis / audience facing:** approximately az 124° / 304°.
- **Exact footprint:** not selected by this direction-level decision; pending emission
  study.
- **Apron:** not selected by this direction-level decision.
- **Typology / roof:** not selected by this direction-level decision.
- **Decision status:** adopted.
- **Implementation status:** pending geometry emission and validation; the inherited
  az-150 stage remains provisional.
- **Rationale:** owner selection; no additional rationale recorded.

## Required follow-ups before Rule 9 geometry validation can close

Rule 9's human direction is settled, but its geometry-dependent closure gate remains
non-passing until these follow-ups are complete.

- [ ] Emit the chosen stage geometry into the adopted scenario package and re-run
      `scripts/stage_refit_sweep.py` + `scripts/audit_in_situ_package.py` (green).
- [ ] Update the fan declaration to match emitted seating (≈130° effective span).
- [ ] Update `docs/DESIGN_CANON.md` Rule 9 + ledger row; update README status table.
- [ ] Provisionally annotate `docs/claude_design_handoff.md` while the geometry gate is
      non-passing.
- [ ] Confirm stage row-1 gaps against the adopted tier's emitted geometry (gaps above
      were measured at the 1,283-seat frame).
