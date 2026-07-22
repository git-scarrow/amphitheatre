# STRAT provenance ledger (P-4)

One row per consumed design-repo artifact. When an upstream artifact regenerates, every
dependent STRAT output is flagged STALE until re-derived.

## Status note (P-3) — 2026-07-21

The STRAT v2 prompt described `BAY_BAND_V2_DECISION_ADDENDUM.md` as PROPOSED. **Overtaken
by events the same day: the addendum was ADOPTED** (DP1–DP4 decided by owner instruction,
commit `ecbd758`) before this workstream's first output. Citations herein use the adopted
status. Consequences for STRAT:

- DP2 (masts) **decided**: (a)+(c) hybrid; re-site search (`mast_resite_search.json`,
  commit `ecbd758`) shows 55% of the stage zone admits full 26-ft masts under the S1
  ceiling; screen deploys only after civil twilight.
- DP3 (T2 roof) **decided as figure of record**: 38.5% of restored (S1) view; roof top
  ≤ 634.0 ft spec condition. T-8 may use these as decided inputs.
- DP4 trigger definition is concrete (city resolution or civic-effort instrument);
  T-5's encumbrance findings feed which instrument is available. Transition log: empty.

## Consumed artifacts

| artifact (path) | commit | producer | definition set | STRAT dependents |
|---|---|---|---|---|
| `analysis/bay_view_obstruction/neighbor_receptors.geojson` | `4e6d03a` | dispatch T4 (`scripts/neighbor_ceiling.py`) | D1–D5 | T-2 join (`receptor_parcel_join.csv`), T-6 frame |
| `analysis/bay_view_obstruction/per_row_bands_by_set.csv` | `4e6d03a` | dispatch T3 | D1–D5 | P-5 priors; E(k) modeling |
| `analysis/bay_view_obstruction/rn_rm_table.md` | `4e6d03a` | dispatch T3 | D1–D5 | P-5 priors (r_m nonexistence) |
| `analysis/bay_view_obstruction/neighbor_ceiling_S1.tif` / `_S2.tif` | `4e6d03a` | dispatch T4 | D1–D5 | P-5 priors (+22.9 ft ceiling); T-8 envelope reasoning |
| `analysis/bay_view_obstruction/element_verdicts_v2.md` | `4e6d03a` | dispatch T5 | D1–D5 | T-8 (T2 roof price via DP3) |
| `analysis/bay_view_obstruction/mast_resite_search.json` | `ecbd758` | DP2(c) one-off | D1–D5 | context only |
| `analysis/stage_adoption/BAY_BAND_V2_DECISION_ADDENDUM.md` | `ecbd758` (adopted) | owner sign-off | defines D1–D5 | vocabulary lock (P-2); DP3/DP4 inputs |
| `requests/self_serve/emmet_parcels_park.json` | repo (pull 2026-07-06) | self-serve pulls | pre-v2 (non-viewshed) | T-2 attrs; T-3 SEV/taxable anchors |
| `requests/self_serve/FINDINGS.md` | repo | self-serve pulls | pre-v2 | site identity; T-4 leads |

## STRAT-fetched external snapshots

| snapshot | source | fetched | used by |
|---|---|---|---|
| `strategy/data/parcels_block_6494.json` | gis.emmetcounty.org `ParcelPublicAccess/MapServer/13` (TaxParcel_1K), envelope 19532200,750000→19533800,751500 EPSG:6494, outSR=6494 | 2026-07-21 | T-2 join geometry |

## STRAT outputs and their upstream pins

| output | pinned to |
|---|---|
| `strategy/receptor_parcel_join.csv` | `neighbor_receptors.geojson`@`4e6d03a` + both parcel snapshots |
| `strategy/STRAT_FINDINGS.md` F1–F4 | rows above as cited per finding |
