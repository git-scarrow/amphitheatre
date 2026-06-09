#!/usr/bin/env python3
"""
Stage 3 — Stormwater facility sizing & event-floor recommendation for the Petoskey Pit.

Static (closed-basin) volume routing of NRCS-CN runoff onto the Stage-1/2
stage-storage curve. Planning-grade. All elevations NAVD88 (Geoid12A), intl ft.

Method rationale
----------------
The bowl has NO engineered outlet below its natural spill (618.04 ft). Until it
spills it is hydraulically CLOSED: every inflow increment is either stored or
infiltrated. So the peak water-surface elevation (WSEL) is found by a volume
balance, NOT a dynamic flood route:

    V_stored(WSEL)  =  V_inflow  -  V_infiltrated_during_event

and WSEL = the stage at which the stage-storage curve equals that stored volume.
Ignoring simultaneous outflow is conservative (highest WSEL) and correct here
because no low-level outlet exists yet.

Inflow has two parts (kept separate to avoid double counting):
  * Direct precipitation on the bowl footprint (0.93 ac) -- lands in the basin,
    delivered ~100%  ->  P * A_bowl
  * External run-on from the contributing area beyond the bowl rim, via CN  ->
    Q(P,CN) * A_external

Two coherent soil scenarios bracket the answer:
  * SANDY  : low CN (HSG A), high basin infiltration  -> little/no ponding
  * TIGHT  : high CN (HSG D), ~no infiltration credit  -> full volume ponds
             (also covers a clay liner or a high/perched water table)
The TIGHT, no-infiltration-credit case is the FLOOR-SETTING upper bound.
"""
import numpy as np
import csv, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "stage3")
os.makedirs(OUT, exist_ok=True)

# ----------------------------------------------------------------------------
# 1. Design rainfall  -- NOAA Atlas 14 Vol 8 (Midwestern States) v2, PDS, 24-hr
#    Point: lat 45.3733, lon -84.9550 (Petoskey / Bayfront Park). Depth, inches.
#    Mean quantiles row for the 24-hr duration. Confidence band (lower/upper 90%)
#    retained for the headline storms.
# ----------------------------------------------------------------------------
ATLAS14 = {  # ARI(yr): (mean, lower90, upper90)  inches, 24-hr
    1:    (1.87, 1.60, 2.20),
    2:    (2.14, 1.83, 2.52),
    10:   (3.05, 2.59, 3.61),
    25:   (3.70, 3.07, 4.54),
    100:  (4.81, 4.06, 5.43),
    500:  (6.29, 4.62, 7.42),   # extreme / check
    1000: (6.98, 5.00, 8.29),
}
# Water-quality storm: Michigan / EGLE first-flush treatment standard = 1.0 in.
# (Channel-protection reference = 1-yr,24-hr = 1.87 in, reported but not the WQv.)
WQ_DEPTH_IN = 1.00

# Storms to model: (label, depth_in, note)
STORMS = [
    ("WQ_firstflush_1.0in", WQ_DEPTH_IN, "Michigan/EGLE water-quality treatment storm (first 1.0 in)"),
    ("10yr_24hr",  ATLAS14[10][0],  "NOAA Atlas14 10-yr 24-hr"),
    ("100yr_24hr", ATLAS14[100][0], "NOAA Atlas14 100-yr 24-hr"),
    ("500yr_24hr", ATLAS14[500][0], "NOAA Atlas14 500-yr 24-hr (extreme/check)"),
]

# ----------------------------------------------------------------------------
# 2. Catchment geometry (Stage 2)  -- all areas in acres
# ----------------------------------------------------------------------------
A_BOWL = 0.93          # bowl footprint at spill -> direct-precip catch
A_EXT_LOW = 0.29       # natural pre-fill external run-on (near-closed bowl)
A_EXT_HIGH = 2.09 - A_BOWL   # conditioned catchment minus bowl = 1.16 ac external
STORM_DUR_HR = 24.0

# CN scenarios (external contributing area, mixed urban park/parking)
CN_SANDY = 61   # HSG A, open space/park w/ some impervious
CN_TIGHT = 85   # HSG C/D, urban
# Basin-bottom infiltration rates (parametric -- PENDING BORINGS)
INFIL_SANDY_INHR = 2.0   # HSG A sand
INFIL_TIGHT_INHR = 0.0   # HSG D / clay liner / high water table  (no credit)

FREEBOARD_FT = 1.0       # event-floor freeboard above design WSEL

# ----------------------------------------------------------------------------
# Stage-storage curve (Stage 1/2)
# ----------------------------------------------------------------------------
SS = os.path.join(ROOT, "stage_storage.csv")
stage, area_ac, vol_acft = [], [], []
with open(SS) as f:
    for r in csv.DictReader(f):
        stage.append(float(r["stage_ft_navd88"]))
        area_ac.append(float(r["inundated_area_ac"]))
        vol_acft.append(float(r["storage_volume_acft"]))
stage = np.array(stage); area_ac = np.array(area_ac); vol_acft = np.array(vol_acft)
FLOOR = 609.12          # closed-sink floor (gridded)
SPILL = 618.04          # pour-point / spill
CAP_ACFT = float(np.interp(SPILL, stage, vol_acft))   # capacity to spill


def cn_runoff_in(P, CN):
    """NRCS curve-number runoff depth (inches) for rainfall P (in)."""
    S = 1000.0 / CN - 10.0
    Ia = 0.2 * S
    if P <= Ia:
        return 0.0
    return (P - Ia) ** 2 / (P - Ia + S)


def wsel_from_volume(V_acft):
    """Invert the stage-storage curve: stage at which storage == V."""
    if V_acft <= 0:
        return FLOOR
    if V_acft >= CAP_ACFT:
        return SPILL  # would overtop -> spills, capped at spill
    return float(np.interp(V_acft, vol_acft, stage))


def inflow_volume(P_in, CN_ext, A_ext):
    """Inflow ac-ft = direct precip on bowl + CN run-on from external area."""
    v_direct = P_in / 12.0 * A_BOWL
    Q = cn_runoff_in(P_in, CN_ext)
    v_ext = Q / 12.0 * A_ext
    return v_direct, v_ext, v_direct + v_ext, Q


def infil_loss_acft(rate_inhr, A_pond_ac):
    """Infiltration loss over the event (in-ft) over a ponded area, capped later."""
    return rate_inhr * STORM_DUR_HR / 12.0 * A_pond_ac


# ----------------------------------------------------------------------------
# 3. Route every storm under both scenarios x both contributing-area bounds
# ----------------------------------------------------------------------------
rows = []
for label, P, note in STORMS:
    for scen, CN, infil in [("SANDY", CN_SANDY, INFIL_SANDY_INHR),
                            ("TIGHT", CN_TIGHT, INFIL_TIGHT_INHR)]:
        for aname, A_ext in [("Aext_low_0.29ac", A_EXT_LOW),
                            ("Aext_high_1.16ac", A_EXT_HIGH)]:
            v_dir, v_ext, v_in, Q = inflow_volume(P, CN, A_ext)
            # Infiltration credit: applied over the ponded area. Iterate once:
            # first pass WSEL with no credit -> ponded area -> infiltration -> WSEL.
            wsel0 = wsel_from_volume(v_in)
            A_pond = float(np.interp(wsel0, stage, area_ac))
            v_infil = min(infil_loss_acft(infil, max(A_pond, 0.05)), v_in)
            v_req = max(v_in - v_infil, 0.0)
            wsel = wsel_from_volume(v_req)
            depth = wsel - FLOOR
            rows.append(dict(
                storm=label, P_in=round(P, 2), scenario=scen, CN_ext=CN,
                infil_inhr=infil, contrib=aname, A_ext_ac=round(A_ext, 2),
                Q_runoff_in=round(Q, 3),
                V_direct_acft=round(v_dir, 4), V_ext_acft=round(v_ext, 4),
                V_inflow_acft=round(v_in, 4), V_infil_acft=round(v_infil, 4),
                V_required_acft=round(v_req, 4),
                WSEL_ft=round(wsel, 2), pond_depth_ft=round(depth, 2),
                pct_of_capacity=round(100 * v_req / CAP_ACFT, 1),
                spills=(wsel >= SPILL - 1e-6),
            ))

# ----------------------------------------------------------------------------
# 4. Groundwater lower bound (parametric, tied to bay 581.4 NAVD88)
# ----------------------------------------------------------------------------
BAY_NAVD88 = 581.4
# Perched bluff setting: SHGW under the bowl is UNKNOWN. Parametrize as bay +
# gradient mound. Bowl floor 609.12 sits ~28 ft above the bay.
GW_CASES = {
    "bay_level": BAY_NAVD88,
    "bay_plus_5ft_mound": BAY_NAVD88 + 5.0,
    "bay_plus_15ft_mound": BAY_NAVD88 + 15.0,
    "perched_at_floor_worstcase": FLOOR,   # hypothetical local perched table
}

# ----------------------------------------------------------------------------
# 5. Back-calculation: contributing area that would fill the bowl to spill
#    (the threshold the storm-sewer GIS must rule out). 100-yr, CN_TIGHT.
# ----------------------------------------------------------------------------
P100 = ATLAS14[100][0]
Q100 = cn_runoff_in(P100, CN_TIGHT)
v_direct_100 = P100 / 12.0 * A_BOWL
# need v_direct + Q/12 * A_ext = CAP  -> solve A_ext
A_ext_to_spill = (CAP_ACFT - v_direct_100) / (Q100 / 12.0)

# ----------------------------------------------------------------------------
# Write storm_sizing.csv  (runoff volumes per storm/scenario/area)
# ----------------------------------------------------------------------------
sz_path = os.path.join(OUT, "storm_sizing.csv")
fields = list(rows[0].keys())
with open(sz_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

# wsel_by_storm.csv : compact peak WSEL per storm, bracketed by scenario
wsel_path = os.path.join(OUT, "wsel_by_storm.csv")
with open(wsel_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["storm", "P_in", "WSEL_low_ft(sandy,Aext_low)",
                "WSEL_high_ft(tight,Aext_high)", "depth_high_ft",
                "pct_cap_high", "spills_high", "freeboard_ft",
                "event_floor_min_ft(high+FB)"])
    for label, P, note in STORMS:
        lo = min(r["WSEL_ft"] for r in rows if r["storm"] == label)
        hi_row = max((r for r in rows if r["storm"] == label),
                     key=lambda r: r["WSEL_ft"])
        hi = hi_row["WSEL_ft"]
        w.writerow([label, round(P, 2), lo, hi, hi_row["pond_depth_ft"],
                    hi_row["pct_of_capacity"], hi_row["spills"],
                    FREEBOARD_FT, round(hi + FREEBOARD_FT, 2)])

# Headline numbers for the markdown
gov = max((r for r in rows if r["storm"] == "100yr_24hr"),
          key=lambda r: r["WSEL_ft"])
gov500 = max((r for r in rows if r["storm"] == "500yr_24hr"),
             key=lambda r: r["WSEL_ft"])
summary = dict(
    capacity_to_spill_acft=round(CAP_ACFT, 2),
    floor=FLOOR, spill=SPILL,
    wsel_100yr_high=gov["WSEL_ft"], depth_100yr_high=gov["pond_depth_ft"],
    pct_cap_100yr_high=gov["pct_of_capacity"],
    wsel_500yr_high=gov500["WSEL_ft"], pct_cap_500yr_high=gov500["pct_of_capacity"],
    event_floor_min=round(gov["WSEL_ft"] + FREEBOARD_FT, 2),
    A_ext_to_spill_ac=round(A_ext_to_spill, 1),
    bay_navd88=BAY_NAVD88, gw_cases=GW_CASES,
)
with open(os.path.join(OUT, "_summary.json"), "w") as f:
    json.dump(summary, f, indent=2)

print("=== Stage-storage anchors ===")
print(f"floor {FLOOR}  spill {SPILL}  capacity_to_spill {CAP_ACFT:.2f} ac-ft")
print("\n=== Peak WSEL by storm (TIGHT, Aext_high = design driver) ===")
for label, P, note in STORMS:
    hi = max((r for r in rows if r["storm"] == label), key=lambda r: r["WSEL_ft"])
    lo = min(r["WSEL_ft"] for r in rows if r["storm"] == label)
    print(f"{label:22s} P={P:4.2f}in  WSEL {lo:.2f}–{hi['WSEL_ft']:.2f} ft  "
          f"depth {hi['pond_depth_ft']:.2f} ft  {hi['pct_of_capacity']:.1f}% cap  "
          f"spills={hi['spills']}")
print(f"\n100-yr governing WSEL (high) = {gov['WSEL_ft']} ft  "
      f"-> min event floor +{FREEBOARD_FT}ft FB = {gov['WSEL_ft']+FREEBOARD_FT:.2f} ft")
print(f"500-yr check WSEL (high) = {gov500['WSEL_ft']} ft  "
      f"({gov500['pct_of_capacity']}% of capacity)  spills={gov500['spills']}")
print(f"\nBack-calc: external area to fill bowl to SPILL @100yr/CN{CN_TIGHT} "
      f"= {A_ext_to_spill:.1f} ac  (vs surface estimate 0.29–1.16 ac)")
print(f"\nWrote: {sz_path}\n       {wsel_path}\n       {os.path.join(OUT,'_summary.json')}")
