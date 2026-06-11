# Rule 9 closure — stage adoption decision record (TEMPLATE)

_Fill this in to close `DESIGN_CANON` Rule 9. Until every section is complete and the
follow-ups are done, `rule9_status` stays `open` and Claude Design stays paused
(`docs/claude_design_handoff.md`). See `docs/POST_EMISSION_DECISION_MEMO.md` for why
this decision is independent of the seating-tier decision._

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

## Candidates on file (tested, none adopted)

| Candidate | Mismatch (sweep sign) | Lateral ft | Row-1 gap E/B/S ft | Bay obstr % | Foreground obstr % | Earthwork CY | Source |
|---|--:|--:|---|--:|--:|--:|---|
| P_inherited (az 150, status quo) | +25.4 | −22.3 | 17.3 / 20.6 / 2.2 | 0.0 | 0.0 | 0 | STAGE_SHAPE_STUDY §A |
| P_opt refit (az 150, solved from residuals) | +6.3 | −6.7 | 12.0 / 32.7 / 21.9 | 0.0 | 1.7 | 37.8 | STAGE_SHAPE_STUDY §A / tier recipe |
| + five-facet apron (319 sf, 6.0 ft projection) | — | — | 12.0 / 29.6 / 18.8 | 0.0 | 1.1 | ~8.9 | STAGE_SHAPE_STUDY §A2 |
| Typology shortlist (incl. roofed band-shell options) | per option | — | — | per option | per option | — | stage_typology_scores.json |

## Decision record (FILL IN)

- **Chosen candidate:** ______ (one of the above, or "accept inherited with reasons")
- **Axis az / placement:** ______
- **Apron:** none / faceted (which front): ______
- **Typology / roof:** ______ (cite its obstruction clearance)
- **rule9_status →** `resolved` | `carried_provisional` (provisional = Claude Design
  may resume with the stage flagged provisional in every artifact)
- **Reasons (site / performance / civic — the inevitability standard):**
  - ______
- **Decided by / date:** ______

## Required follow-ups before Rule 9 is marked closed

- [ ] Emit the chosen stage geometry into the adopted scenario package and re-run
      `scripts/stage_refit_sweep.py` + `scripts/audit_in_situ_package.py` (green).
- [ ] Update the fan declaration to match emitted seating (≈130° effective span).
- [ ] Update `docs/DESIGN_CANON.md` Rule 9 + ledger row; update README status table.
- [ ] Un-pause or provisionally annotate `docs/claude_design_handoff.md`.
- [ ] If a tier was adopted in Decision 1, confirm stage row-1 gaps against that
      tier's emitted geometry (gaps above were measured at the 1,283-seat frame).
