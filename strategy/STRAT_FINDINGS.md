# STRAT findings — strategic/economic workstream

Discipline: every line [fact] / [inference] / [assumption]. Units NAVD88 intl ft,
EPSG:6494. Viewshed figures carry occluder set + leaf state (P-2). Provenance per
`PROVENANCE.md`; assumptions tracked in `ASSUMPTION_LEDGER.md`.

**Session 1 — 2026-07-21.** Scope executed: scaffolding, DR-1 filed, T-2 join, T-3
anchors 1–2. Not yet: T-3 comps, T-4–T-8.

---

## F1 · Valuation anchor: the pit's assessed value implies a market value at the strike

- [fact] PID 52-19-06-227-016: **SEV $1,280,700; taxable $1,280,700** (Emmet County
  tax-roll pull `emmet_parcels_park.json`, 2026-07-06; class 202, zoning COP B-2, 2.01 ac).
- [fact] Assessor-implied market value = SEV × 2 = **$2,561,400**.
- [inference] SEV lags market and embeds the assessor's view of impairment (Part 201
  status, pit condition); treat as an anchor, not an appraisal.
- [inference] Taxable = SEV exactly — consistent with post-2018-transfer uncapping and/or
  assessed decline to the cap; either way **no cap wedge**: a buyer inherits full-freight
  taxable value, so carrying-cost relief via cap arbitrage is unavailable to the current
  owner and to any purchaser.
- [inference] The model's ~$2.4M option strike sits **~6% below** assessor-implied market
  — close enough that the strike is not obviously mispriced against the public anchor;
  the real spread lives in `Π` (entitlement premium) and `L` (Part 201 liability), both
  unpriced here.

## F2 · Identifier discrepancy: the pit is two different parcel IDs in two county systems

- [fact] The tax roll (attributes service) carries the pit as **PID 52-19-06-227-016**
  (owner PETOSKEY GRAND LLC, 2.01 ac). No polygon with that ID exists in the county GIS
  parcel layer (`TaxParcel_1K`); the like-match returns only an unrelated township parcel.
- [fact] The GIS polygon covering the pit is **PARCELID 52-19-06-224-001** — 2.01 ac,
  centroid (19533096, 750798), congruent with the design repo's site frame (no datum
  offset; county-vs-repo agreement is sub-10-ft).
- [fact] The 227-block *polygons* (202/214 Petoskey St, 215 E Lake St) lie **north of
  E Lake St** — they are across-street frontage neighbors, not on-block corners.
- [inference] Same land, two identifier domains (plausibly the 2006–2007 block assembly:
  ~11 platted lots consolidated; assessor issued a new tax PID while GIS retained the
  plat-block-coded polygon). The bridge is the acreage + centroid + owner-class congruence.
- **Action implication:** any records request, RoD title search, EGLE correspondence, or
  option instrument must carry **both IDs** until the legal description is confirmed (RoD
  = Sam's manual step, see `BLOCKED.md`). Recommended DATA_GAPS entry for the design
  workstream (STRAT does not write design-canon files).

## F3 · The externality frame is now one list: 29 parcels, ~$8.1M SEV, same frame as the gate

- [fact] T-2 join (`receptor_parcel_join.csv`): all **184** v2 street receptors matched to
  **29 unique frontage parcels** (166 receptor-rows carry tax-roll attributes; the
  remainder are polygons whose attributes the public pull lacks — mostly public or
  condo-parent parcels).
- [fact] The **19 valued private parcels** sum **SEV ≈ $8,124,700** → implied market
  ≈ **$16.25M**. Largest single frontage stake: MDC JACKSON LLC (215 E Lake St,
  SEV $1.151M). **5+ public parcels** sit in the frame (City of Petoskey ×3, City Bldg
  Authority, State of Michigan).
- [inference] This is the natural boundary for both sides of the model: the set whose
  views the adopted neighbor gate protects **and** the candidate capture district for
  T-6 assessment arithmetic — one list of beneficiaries for the gate and the levy, as
  specified. Public owners in the frame can't "complain" in the Reading-B sense but do
  hold votes/consents relevant to any district instrument.
- [fact] Receptor-level band stats ride along in the CSV (clear_pct_S1 / S2-leafon per
  receptor), so `E(k)` per-parcel arguments can be made without re-touching viewshed data
  (P-1 respected).

## F4 · Status supersession and carried priors

- [fact] The bay-band v2 addendum is **ADOPTED** (commit `ecbd758`, owner instruction
  2026-07-21) — the STRAT v2 prompt's P-3 "PROPOSED" qualifier is overtaken; DP2 and DP3
  are decided (see `PROVENANCE.md` status note). T-8 may treat the T2-roof price
  (38.5% of restored S1 view; top ≤ 634.0 ft) as the figure of record.
- Carried P-5 priors (unchanged): restorable interior view is a **bend/south asset**
  (east capped ~54–62% under S1 by durable city massing); **r_m does not exist** under S2
  (either leaf state); neighbor over-stage ceiling **S1 min 635.4 ft (+22.9 ft)**,
  S2-only headroom contingent. De-treeing = **partial lever** for `E(k)`.

---

## Gap-movement table

| gap | before session 1 | after session 1 |
|---|---|---|
| Pit as-is value anchor | conversational (~$1.25M 2018 price only) | SEV/taxable [fact] + implied market $2.56M; comps OPEN |
| Externality bearer census | "frontages" (unenumerated) | 29 parcels, 19 valued (ΣSEV $8.12M), owner names attached |
| Canopy-lever asymmetry | untested claim | priors partial (P-5); tower-floor half filed as DR-1 |
| Parcel identity | single-PID assumption | dual-ID discrepancy found; RoD verification queued |
| TIF frame | undefined | frame = T-2 join CSV (parcel set fixed; millages OPEN) |
