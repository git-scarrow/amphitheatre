# STRAT findings — strategic/economic workstream

Discipline: every line [fact] / [inference] / [assumption]. Units NAVD88 intl ft,
EPSG:6494. Viewshed figures carry occluder set + leaf state (P-2). Provenance per
`PROVENANCE.md`; assumptions tracked in `ASSUMPTION_LEDGER.md`.

**Session 1 — 2026-07-21.** Scaffolding, DR-1 filed, T-2 join, T-3 anchors 1–2.
**Session 2 — 2026-07-22.** DR-1 answered (T-1 CONFIRMED); T-4/T-5 desk findings (F5–F6); T-6 arithmetic (F7); T-7 bounds (F8); T-8 bracket (F9).
**Session 3 — 2026-07-23.** Browser-agent BS&A session (F2 resolved; F10 instrument index). Open: T-3 comps, RoD registration + Tier-1 pulls, records list.

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
- **RESOLVED 2026-07-23 (assessor level — `rod_portal_session.md`):** [fact] BS&A carries
  both IDs for the same ~2.1-ac metes-and-bounds footprint. **224-001** is the zeroed-out
  condo-era record, legal description ending "**PETOSKEY POINTE CONDO GROUNDS**" ($0 tax
  all years shown; Key Largo FL mail address). **227-016** is the active parcel, **created
  by combination 11/07/2018** (Split #99) — one week after Berg's 10/31/2018 closing.
  Full verbatim legal description captured (Ignatius & Lewis Petoskey's Addition lots;
  deed acreage 2.10 vs assessor 2.01 — rounding-level, noted). GIS simply was never
  re-keyed after the combination. Deed-level confirmation = Tier-1 pull L1232 P646.

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

## F5 · Owner profile (T-4): identified principal, adversarial history, and a decisive litigation fact

- [fact] Petoskey Grand LLC finalized purchase of 200 E Lake St on **2018-10-31** from
  **LCA Enterprises** (upnorthlive.com); the sale extinguished the Petoskey Pointe
  entitlement ("no longer have the right to build the proposed Petoskey Pointe project").
- [fact] The principal is **Robert "Bob" Berg, Key Largo, Florida** (upnorthlive political-signs
  article names "Florida businessman Bob Berg" as owner; local tracking site adds
  business partner/daughter Katie). Prior owner chain: Elias Amash (Grand Rapids) 2013–2018.
- [inference — single-source (northernmichmashpreserve.weebly.com tracking page), needs
  corroboration via PNR archive + court records:] behavioral timeline: Jan 2019 city
  restored pre-2006 zoning (eliminating the Pointe PUD — the **by-right envelope shrank**);
  Mar 2019 Berg PUD presentation; Jul 2019 Planning Commission declined after an
  "all-or-nothing, no negotiating" developer ultimatum; Oct 2019 ultimatum to the mayor +
  threatened defamation suit against a council member; **Apr 2021 a judge ruled the
  city's park resolution for the site "illegal and void"**; 2022–2025 no development
  activity.
- [inference] Model-relevant reads (evidence line only, no strategy calls): (i) the
  **city already attempted the unilateral park move and lost in court** — any civic path
  runs through arms-length purchase, not designation; (ii) counterparty is litigious and
  ultimatum-prone → `T` (Coasean transaction costs) materially above baseline;
  (iii) 7+ years of carry (~$58–64k/yr property tax at ~45–50 mills on $1.28M taxable
  [assumption: millage pending T-6]) absorbed without income or sale suggests high `Π`
  expectations and/or non-economic holdout premium.

## F6 · Park encumbrance check (T-5, preliminary): no state-grant encumbrance surfaced on the canopy band

- [fact] The adopted **2023–2027 Emmet County Parks & Recreation Plan** Table 5-2
  ("Status Report on Grant-Assisted Recreation Acquisitions & Development", doc p.37,
  DNR Grants Management data) lists **no City of Petoskey Bayfront Park grants** — all
  entries are county properties (Cecil Bay, Camp Petosega, Headlands, rail-trail, Resort
  Bluffs, Little Traverse Bay View Park).
- [inference] A planning-consultant project page (bria2.com) describes Bayfront Park
  improvements as funded **primarily by the Petoskey TIF Authority** with State
  participation via **DNR Waterways and Recreation Services** (up to ~$5M program) —
  Waterways money attaches to marina/pier facilities, not the upland tree band.
- [fact, self-serve §7 (2026-07-06)] The MNRTF county-list search already found City of
  Petoskey awards only for **Skyline Recreation Area and Winter Sports Park — no
  Bayfront/downtown hit** (county PDF bot-blocked; search-result level).
- [inference] Direction of evidence: the canopy screen is likely encumbered by **no
  MNRTF/LWCF conversion regime**, leaving vista management a **municipal instrument**
  (city council resolution / parks vegetation policy) plus **MDOT roadside vegetation
  permit** for trees in US-31 ROW. NOT yet confirmed — the City's own five-year
  recreation plan grant inventory is the definitive source and has not been obtained.
- **DP4 instrument implication:** the concrete trigger's path (i) — "city resolution on
  vista/canopy policy" — is legally available but politically scarred: the city's last
  unilateral resolution touching this site was voided in court (F5). Any de-treeing
  instrument robust enough for DP4 likely couples a council resolution with owner/civic
  agreement rather than standing alone.
- **Records to request (drafted-only; sends ON HOLD):** City of Petoskey current 5-yr
  recreation plan (grant inventory section); DNR Grants Management project-boundary maps
  (6(f)/MNRTF) for any city waterfront grants; city TIF/DDA plan documents covering
  Bayfront; Emmet 57th Circuit case records for the 2021 park-resolution ruling.

---

## F7 · TIF arithmetic (T-6): the frontage frame alone cannot carry the amphitheater's fiscal case

- [fact] Frame taxable values (24 attributed parcels): **$4,809,575**; pit taxable
  $1,280,700 → pit tax ≈ **$61.5k/yr @48 mills** [millage swept 45/48/52,
  apportionment report queued].
- [fact, arithmetic] Amphitheater scenario (pit → public, taxable 0): breakeven
  frontage uplift = **26.6%** — implausible on the narrow frame; at a generous 10%
  uplift the district runs **−$38k/yr** vs status quo. Tower scenario at $8M new
  taxable: **+$323k/yr** increment. (`tif_arithmetic.csv`, all scenarios swept.)
- [inference] The amphitheater's economic case therefore lives in channels this
  arithmetic does not capture: sales-channel spillover `S` (F8), the wider-than-frame
  downtown premium, and avoided `E` — matching the model's structure.
- **Capture-destination caveat:** Petoskey has an existing DDA (1994) and a
  waterfront/Bear River **TIFA**; whether the block sits inside either boundary is
  unverified — increments may already be committed to existing plans. Boundary maps
  queued (records list).

## F8 · Venue economics (T-7): S bracketed from the Levitt anchor

- [fact, cited] Levitt Dayton 2024: 72,450 attendance / 44 free concerts; ~1/3 of
  visitors spend ~$60 downtown → ≈$1.5M/yr (≈$33k/event).
- [assumption, scaled] Petoskey bowl (1,243 seats, downtown-adjacent):
  **S ≈ $0.3–1.0M/yr** downtown spend at 20–40 events. `V_amph` operating: free model
  ≈ $0.5–1.5M/yr funded budget [assumption]. Details + leads:
  `VENUE_COMPARATORS_STRAT.md`.

## F9 · V_up bracket (T-8): the by-right building owns no unconditional bay view

- [fact] Zoning B-2: **3 stories, 40–45 ft** (§1600 pin queued); restored Jan 2019.
  By-right roof ≈ 658–663 ft; top plate eye ≈ 647 ft = **DR-1 floor 3**.
- [fact, DR-1 cross] Floors 2–3 are canopy-blocked/marginal (7.7% / 53.8% leaf-on);
  the unconditional-view floors (4+) are **not by-right** — the vertical option is
  substantially an **entitlement option**, its view component controlled by the
  city's two levers (trees + zoning).
- [assumption, swept] By-right pro forma bracket: 131–210k gsf, margin before
  land/soft/Part-201 ≈ $10–53M — can pencil **without any view premium**; `L`
  unpriced and could consume the low bracket. `VUP_BRACKET.md` for the full table.
- [inference, valuation mirror of DP4] De-treeing **before** site control gifts the
  by-right scheme its floor-2/3 views (+53.8/+23.1 pts), raising `V_up` and `R` at
  zero cost to the owner; the same act after site control accrues to the venue and
  neighbors. Measured magnitudes now attach to the sequencing clause.


## F10 · Recorded-instrument index (browser-agent session 2026-07-23): distress chain confirmed; possible recorded Part 201 control

- [fact] BS&A's assessor Comments field carries a ~29-item Liber/Page instrument index
  for the block (verbatim in `rod_portal_session.md` §1): early-2000s deed cluster
  (L571), condo-regime creation (L1083: two Condo Master Deeds, Restrictions, **Option
  Agreement**), distress/litigation run (lis pendens, court order, **sheriff's deed**,
  **notice of bankruptcy**, covenant deed), final judgment + **two condo terminations**
  (L1207), and a closing "CO" (L1232 P646, plausibly the combination order).
- [fact] **L571 P82 "DEQ NOTICE"** + two "RESTRICTIONS" (L1083 P979, L1096 P261) +
  "COV DEED" (L1129 P785) are recorded against the block.
- [inference] That combination is strongly consistent with a **recorded Part 201
  institutional control** — which would bear directly on `L` in the model and on any
  option instrument. This *revises* the earlier mapped-level read ("no EGLE RC polygon
  on the block"): the mapped layer may lag or the instruments may be notices short of a
  covenant. **Decided by the Tier-1 document pulls** (L571 P82, L1083 P979, L1096 P261,
  L1129 P785; ~$1.05/page) or an EGLE RC-registry check.
- [inference] The sheriff's-deed/bankruptcy chapter documents the 2009–2013 distress
  chain (Northwestern Bank era) at recorded-instrument level — corroborates the press
  chain in F5 from an independent source class.
- [fact] BS&A's Sale History grid is empty (no digitized prices/parties); exact dates,
  parties, and page counts need the RoD index — **registration remains Sam's step**
  (agent's safety rules bar account creation; the registration tab is left open in
  Chrome). Prioritized purchase list: `rod_portal_session.md` §4.

---

## Gap-movement table

| gap | before session 1 | after session 1 |
|---|---|---|
| Pit as-is value anchor | conversational (~$1.25M 2018 price only) | SEV/taxable [fact] + implied market $2.56M; comps OPEN |
| Externality bearer census | "frontages" (unenumerated) | 29 parcels, 19 valued (ΣSEV $8.12M), owner names attached |
| Canopy-lever asymmetry | untested claim | priors partial (P-5); tower-floor half filed as DR-1 |
| Parcel identity | single-PID assumption | dual-ID discrepancy found; RoD verification queued |
| TIF frame | undefined | frame = T-2 join CSV (parcel set fixed; millages OPEN) |
