# Data Acquisition Requests

Formal letters, records requests, and RFQ templates for the field investigations and public
records required before the planning-grade design can advance to PE-stamped design.

**Site of record (corrected 2026-07-06):** the former **Petoskey Pointe** block, 200 E Lake St,
downtown Petoskey — bounded by E Lake / E Mitchell / Petoskey St / US-31. Parcel
**52-19-06-227-016** (~2.01 ac), owner **Petoskey Grand LLC**, zoned COP B-2, EGLE Part 201
site **24000048** (former Petoskey Ford; excavated 2007 for the stalled hotel project). The
"bay" in the project is a design objective — the upper rows' imperfect bay view the layout
maximizes — not site adjacency. Earlier versions of these letters wrongly described the site
as City-owned Bayfront Park; do not resurrect that framing. Evidence:
`self_serve/FINDINGS.md`.

| File | Recipient | Type | Dossier ref | Status |
|---|---|---|---|---|
| `01_city_dpw_foia.md` | City of Petoskey City Clerk (FOIA) | Michigan FOIA — storm + pit drainage records | E-1, E-2, E-3 | ✅ sendable |
| `02_county_register_records.md` | Emmet County Register of Deeds | Records inquiry — deed chain, easements | B-1, C-5/D-1 | ✅ sendable |
| `07_egle_records_request.md` | EGLE FOIA Request Center (web form) | Michigan FOIA — Part 201 file 24000048, UST, brownfield, outfalls | E-1, D-1/D-2 | ✅ sendable |
| `08_city_planning_inquiry.md` | City Planner (John Iacoangeli) | Courtesy inquiry — site status, zoning, process | G-1/G-2 reframed | ✅ sendable (verify email) |
| `03_rfq_pls_survey.md` | Michigan PLS firm | RFQ — boundary + topo (+contingent OHWM) | B-1, B-2, (B-3) | ⛔ blocked: owner access |
| `04_rfq_geotechnical.md` | Geotechnical PE firm | RFQ — borings, wells, stability | C-1–C-5 | ⛔ blocked: owner access + 2005-era borings first |
| `05_rfq_phase1_esa.md` | Environmental professional | RFQ — Phase I ESA (update) | D-1, D-2 | ⛔ blocked: EGLE records first |
| `06_rfq_wetland_delineation.md` | Wetland consultant | RFQ — delineation | F-3 | ⛔ blocked + likely unnecessary (isolated basin) |
| `withdrawn_08_city_parks_inquiry.md` | — | WITHDRAWN — parkland/MNRTF premise was wrong | — | ✖ |

## Staged for sending

`outbox/` holds send-ready versions with researched recipients and channels —
**`outbox/SEND_CHECKLIST.md`** is authoritative for send order, blockers, and Gmail-draft
housekeeping (rev-1 "Bayfront Park" drafts must be deleted; three rev-2 drafts are current).
**Nothing has been sent.**

Key channels: City FOIA → sbek@petoskey.us (form PDF in `outbox/attachments/`); County RoD →
registerofdeeds@emmetcounty.org; EGLE → michiganegle.govqa.us portal; City Planning →
jiacoangeli@petoskey.us (unverified pattern, cc clerk). Local-firm shortlists (for when the
RFQs unblock): `reference/emmet_county_prof_firms_2026-05.pdf` + `outbox/0[3-6]_*.email.md`.

## Public data already pulled (no request needed)

`self_serve/` — re-runnable scripts + raw payloads + `FINDINGS.md` (2026-07-06): parcel/owner
identity, Part 201/UST/brownfield records, FEMA BFE 589.0 (site Zone X), SSURGO HSG A, NLCD
63% impervious, no Part 303 polygon on the bowl, F-5 (dune/HREA) clear, outside WHPA, Sanborn
volume index 1885–1950.

## Recommended send order

1. **08** (City Planning inquiry — opens the conversation) then **01** (City FOIA) and **07** (EGLE FOIA).
2. **02** (County RoD) same week.
3. RFQs **only after** Sam's owner-engagement decision (03/04/06) and the EGLE file arrives (05).

See `gating_dossier.md` for the full before-you-can-build checklist (note: its B/C/D/F items
predate the site correction — read them against `DATA_GAPS.md` §2026-07-06).
