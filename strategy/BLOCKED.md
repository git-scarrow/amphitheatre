# STRAT blocked items

- **All outward-facing sends ON HOLD** (hard constraint 1). Records requests, planning
  inquiries, and any counterparty contact are drafted-only if drafted at all.
- **County RoD chain-of-title** for the pit parcel: portal needs an account — **Sam's
  manual step** (carried from `requests/self_serve/FINDINGS.md`). Now higher-value: it also
  resolves the tax-PID ↔ GIS-parcel identifier discrepancy (F2) via the legal description.
- **T-1 conclusion**: BLOCKED-ON-DISPATCH → `DISPATCH_REQUESTS.md` DR-1 (design pipeline,
  gentoo). STRAT does not compute viewsheds (P-1).
- **T-8 per-floor view pricing**: blocked on DR-1 return; bracket work can proceed on
  labeled assumptions meanwhile.
- **T-5/T-4 records (drafted-only, sends ON HOLD):** City of Petoskey current 5-yr
  recreation plan grant inventory; DNR Grants Management 6(f)/MNRTF project-boundary
  maps for city waterfront grants; city TIF/DDA plan docs covering Bayfront; **Emmet
  57th Circuit records** for the Apr-2021 park-resolution ruling (corroborates F5);
  LARA/COFS entity detail for Petoskey Grand LLC (web app, may need manual pull).
- **T-6/T-8 records (drafted-only):** Emmet County apportionment report (exact
  millages); **DDA + waterfront/Bear River TIFA boundary maps + TIF plans** (is the
  block inside a capture district?); municode §1600 Schedule of Regulations current
  table (pin B-2 height 40 vs 45 ft); Levitt venue 990s / Meijer Gardens 990 (T-7).

## Records requests — DRAFTED as Gmail drafts 2026-07-22 (NOT sent; sends remain ON HOLD)

| draft | recipient | status |
|---|---|---|
| City of Petoskey FOIA (rec-plan grant inventory; DDA + TIFA plans & boundary maps) | self-addressed — city takes form/mail only (form required; FOIA coord. = City Clerk Sarah Bek) | awaiting Sam: paste into city FOIA form or mail |
| DNR Grants Management (city grant list; 6(f)/MNRTF boundary maps; conversions) | DNR-Grants@michigan.gov [verify note in draft] | awaiting Sam review + send |
| Emmet County Clerk / 57th Circuit (c. Apr-2021 ruling: complaint, register, opinion/order) | clerk@emmetcounty.org (verified) | awaiting Sam review + send |
| Emmet Equalization (apportionment report / Petoskey millages) | zbronikowski@emmetcounty.org [pattern-inferred; verify note in draft] | awaiting Sam review + send |

Court draft carries BOTH parcel IDs per F2. Not drafted (lookups, not requests):
municode §1600 pin, LARA/COFS entity detail, Levitt/Meijer 990s (ProPublica), RoD
chain-of-title (Sam's manual portal step).

## Outreach ledger (discovered via inbox sweep 2026-07-22 — sent by Sam 2026-07-20, pre-STRAT)

| thread | to | status |
|---|---|---|
| FOIA — storm drainage records, Pointe block | sbek@petoskey.us (City Clerk; **email FOIA channel confirmed**, form attached) | sent 07-20; statutory 5-business-day response due **~07-27** |
| Planning questions — resident study of the block | jiacoangeli@petoskey.us (cc sbek) | sent 07-20; no reply yet |
| RoD records search — parcel 227-016 chain | registerofdeeds@emmetcounty.org | **REPLIED 07-20** (Karen Cosens): no staff searches; self-serve at emmetcounty.org/rod (simple registration), $1.05/page; recipe: BS&A Property Search by parcel → sales history + Liber/Page → RoD search by owner names. Env/land-use history NOT in RoD records. |

Consequences: (1) RoD chain-of-title remains Sam's manual step but is now a **recipe,
not a blocker** — owner-name searches: Lake Street Petoskey Associates, Petoskey Pointe
entities, Northwestern Bank, 2013 grantee (Amash entity/LCA), Petoskey Grand LLC. It
also resolves F2's dual-ID question via the vesting deed's legal description.
(2) City records draft re-addressed to sbek@petoskey.us (supersedes the self-addressed
draft — discard that one); needs the city FOIA form attached before sending.
(3) Sam's RoD email cites predecessor parcels 52-19-06-227-005/-006 (~11 total) —
consistent with F2's block-assembly inference; the 227 tax lineage predates the
consolidation.

## Reconciliation vs requests/self_serve/ (2026-07-22 — much of the RoD scope is already in hand)

Already secured (self-serve pulls, 2026-07-06 — `requests/self_serve/FINDINGS.md`):
- **Current vesting/ownership** [fact]: Petoskey Grand LLC, PID 227-016, class 202, COP B-2
  (county parcel service) — RoD confirmation not needed for the fact itself.
- **Conveyance chain outline** [fact, press]: Northwestern Bank → Amash 2013 → Petoskey
  Grand 2018.
- **Environmental instruments at mapped level** [fact]: block is Part 201 SiteID 24000048 +
  UST 00035252 + 2006 brownfield award; EGLE's restrictive-covenant layer shows **no RC
  polygon on the block** (the 3 nearby RCs are other sites).
- **Land-use history path** [fact]: 9 LOC Sanborn volumes indexed (1885–1950, sheets not yet
  pulled) + EGLE "Petoskey Ford" identity — exactly the material Karen notes RoD won't hold.
- **MNRTF county search** [fact, §7]: known City of Petoskey awards = Skyline Recreation
  Area + Winter Sports Park; **no Bayfront/downtown hit** — strengthens F6's
  no-encumbrance direction (LWCF federal list still unchecked; DNR draft covers it).

True RoD-portal residue (the 20-minute session, via BS&A Liber/Page cross-ref):
1. **Vesting deed + legal description** — resolves F2's dual parcel-ID.
2. **Recorded easements** on the block (utility/drainage/access/party-wall) — in no layer pulled.
3. **Development agreements / reversionary clauses**, if any recorded.
4. **Predecessor-parcel consolidation instruments** (~11 lots, 227-005/-006 et al.).
5. Spot-check: any deed-recorded Part 201 covenant post-dating the EGLE layer.

Draft-narrowing note: the DNR draft can cite §7's known awards (Skyline, Winter Sports
Park) and ask only to confirm completeness + any LWCF 6(f) items for Bayfront — Sam may
add one line before sending; substance already covered.

## 2026-07-23 — browser-agent BS&A session (rod_portal_session.md)

- BS&A tasks complete without login: legal descriptions, 11/07/2018 combination, the
  29-item Liber/Page instrument index, F2 resolved. **No payments, no form fields
  touched.**
- RoD registration NOT performed (agent safety rules bar account creation; no
  credential-prompt tool in its session). **Sam:** rod.emmetcounty.org → Register tab
  (left open in Chrome) → then either run the six index searches himself or hand the
  session back for a follow-up agent run with the login.
- Then: Tier-1 purchases (~9 instruments, $1.05/page) per `rod_portal_session.md` §4 —
  they decide the recorded-environmental-control question (F10) and the predecessor-lot
  list (e).
