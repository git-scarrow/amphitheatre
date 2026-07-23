#!/usr/bin/env python3
"""T-6: TIF / assessment arithmetic on the T-2 receptor-parcel frame.

Frame: strategy/receptor_parcel_join.csv (unique parcels; taxable values from the
2026-07-06 tax-roll pull). Millage is SWEPT (apportionment report not yet obtained —
[assumption], range chosen to bracket MI non-homestead commercial in Petoskey:
city+county+extra-voted+ISD+NCMC+library ~21-28 + school operating 18 + SET 6).

Scenarios (all growth figures [assumption], swept):
  A. status quo          — pit taxable 1,280,700 taxed; no uplift
  B. amphitheater        — pit -> public ownership (taxable 0); frontage uplift swept
  C. tower (by-right 3fl)— pit redeveloped, new taxable swept 5M/8M/12M; no frontage uplift claimed
Capture destination caveat: Petoskey has an existing DDA (1994) and a waterfront/Bear
River TIFA; whether the block sits in either boundary is UNVERIFIED — increments may
already be committed. Boundary maps are on the records-request list.

Output: strategy/tif_arithmetic.csv + stdout summary. Pure stdlib, re-runnable.
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STRAT = os.path.normpath(os.path.join(HERE, ".."))
JOIN = os.path.join(STRAT, "receptor_parcel_join.csv")
OUT = os.path.join(STRAT, "tif_arithmetic.csv")

PIT_TAXABLE = 1_280_700.0
MILLS = [45.0, 48.0, 52.0]              # [assumption] swept
UPLIFT = [0.0, 0.05, 0.10, 0.20]        # [assumption] frontage taxable uplift, amphitheater scenario
TOWER_TAXABLE = [5e6, 8e6, 12e6]        # [assumption] by-right 3-story redevelopment taxable

parcels = {}
for r in csv.DictReader(open(JOIN)):
    pid = r["parcelid"]
    if pid and r["taxable"]:
        parcels[pid] = float(r["taxable"])
front_taxable = sum(parcels.values())

rows = []
for m in MILLS:
    mr = m / 1000.0
    rows.append(dict(scenario="A_status_quo", mills=m, pit_taxable=PIT_TAXABLE,
                     frontage_taxable=front_taxable, uplift="",
                     pit_tax=round(PIT_TAXABLE * mr), frontage_tax=round(front_taxable * mr),
                     annual_increment=0))
    for u in UPLIFT:
        inc = front_taxable * u * mr
        rows.append(dict(scenario="B_amphitheater", mills=m, pit_taxable=0,
                         frontage_taxable=round(front_taxable * (1 + u)), uplift=u,
                         pit_tax=0, frontage_tax=round(front_taxable * (1 + u) * mr),
                         annual_increment=round(inc - PIT_TAXABLE * mr)))
    for t in TOWER_TAXABLE:
        rows.append(dict(scenario="C_tower_by_right", mills=m, pit_taxable=t,
                         frontage_taxable=front_taxable, uplift="",
                         pit_tax=round(t * mr), frontage_tax=round(front_taxable * mr),
                         annual_increment=round((t - PIT_TAXABLE) * mr)))

with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

print(f"frontage parcels with taxable: {len(parcels)} | frontage taxable sum ${front_taxable:,.0f}")
print(f"pit tax @48 mills: ${PIT_TAXABLE*0.048:,.0f}/yr")
print(f"B (amphi, 10% uplift, 48 mills): net annual increment "
      f"${(front_taxable*0.10 - PIT_TAXABLE)*0.048:,.0f}")
print(f"C (tower 8M taxable, 48 mills): annual increment ${(8e6-PIT_TAXABLE)*0.048:,.0f}")
