"""Conservative re-band: per-seat 10th-percentile C (flank-aware ray-cast).

Replicates design_extended_bays.py per-seat sightline logic (lines 211-239)
from seating_bays.geojson + DEM, then re-bands rows on the STRICTER per-seat
10th-pct C (vs centreline C). Confirms / tightens the formal-bowl stop.

Output: design_civic_core/perseat_bands.csv  (row, centreline_C, perseat_C10, pct_pass, band_*)
        console: conservative formal stop + band capacity
"""
from __future__ import annotations
import csv, json, math
from collections import defaultdict
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import rowcol  # noqa: F401 (kept for parity)

# --- params (verbatim from design_extended_bays.py) ---
DEM = "dem/dem_design_1ft.tif"
CX, CY = 19533067.7, 750799.2
AX_AZ = 132.0
FOCUS_ELEV = 612.5; F_T = 15.0; EYE_HT = 3.94; STAGE_R = 50.0
C_TARGET_FT = 0.295
AISLE = 0.18
SRC = Path("design_extended_bays/seating_bays.geojson")
OUT = Path("design_civic_core")

def U(az): a = math.radians(az); return math.sin(a), math.cos(a)
UX, UY = U(AX_AZ)
FX, FY = CX + UX * F_T, CY + UY * F_T
SFx, SFy = FX + UX * STAGE_R, FY + UY * STAGE_R
SF = np.array([SFx, SFy])

def seats(L, w):
    try: return max(0, int(float(L) * (1 - AISLE) // w))
    except (TypeError, ValueError): return 0

def band(c_mm):
    if c_mm is None: return None
    return "formal" if c_mm >= 90 else "soft" if c_mm >= 60 else "marginal" if c_mm >= 30 else "rim"

def ray_seg(p0, d, a, b):
    e = b - a; den = d[0]*(-e[1]) - d[1]*(-e[0])
    if abs(den) < 1e-9: return None
    t = ((a[0]-p0[0])*(-e[1]) - (a[1]-p0[1])*(-e[0]))/den
    u = (d[0]*(a[1]-p0[1]) - d[1]*(a[0]-p0[0]))/den
    return t if (t > 1e-6 and -0.05 <= u <= 1.05) else None

def main():
    fc = json.load(open(SRC))
    # group features by row -> {elev, kind, zone, bays:[coords...], centreCs:[], len_by_w}
    rows = defaultdict(lambda: {"elev": None, "kind": "", "zone": "", "bays": [],
                                "centreCs": [], "len": 0.0, "secs": []})
    for f in fc["features"]:
        p = f["properties"]; rn = int(p["row"])
        r = rows[rn]
        r["elev"] = p["elev"]; r["kind"] = p["kind"]; r["zone"] = p["zone"]
        r["bays"].append(f["geometry"]["coordinates"])
        r["len"] += float(p["length_ft"] or 0)
        r["secs"].append((p["section"], float(p["length_ft"] or 0)))
        if p.get("C_mm") not in (None, ""):
            r["centreCs"].append(float(p["C_mm"]))

    allseat = sorted([rn for rn in rows if rows[rn]["kind"] == "seating"],
                     key=lambda rn: rows[rn]["elev"])
    per_row = {}  # row -> (perseat_C10_mm, pct_pass)
    for idx, rn in enumerate(allseat):
        if rows[rn]["zone"] != "civic" or idx == 0:
            continue
        front = rows[allseat[idx-1]]
        fsegs = [(np.array(c[i]), np.array(c[i+1]), front["elev"])
                 for coords in front["bays"] for c in [coords] for i in range(len(c)-1)]
        Eeye = rows[rn]["elev"] + EYE_HT; Cs = []
        for coords in rows[rn]["bays"]:
            for q in coords[::2]:
                p = np.array(q); d = SF - p; Ds = float(np.hypot(*d))
                if Ds < 1e-3: continue
                dd = d / Ds; best = None
                for (a, bb, fe) in fsegs:
                    t = ray_seg(p, dd, a, bb)
                    if t is not None and t < Ds and (best is None or t < best[0]):
                        best = (t, fe)
                if best is None:
                    Cs.append(1.0); continue
                Dfoc = Ds - best[0]
                h = FOCUS_ELEV + (Eeye - FOCUS_ELEV) * Dfoc / Ds
                Cs.append(h - (best[1] + EYE_HT))
        if Cs:
            Cs = np.array(Cs)
            per_row[rn] = (round(float(np.percentile(Cs, 10)) * 304.8),
                           round(float((Cs >= C_TARGET_FT).mean()) * 100))

    # conservative stop: last contiguous civic seating row with perseat C10 >= 90
    civic = sorted(rn for rn in rows if rows[rn]["zone"] == "civic" and rows[rn]["kind"] == "seating")
    stop = None
    for rn in civic:
        c10 = per_row.get(rn, (None, None))[0]
        if c10 is None or c10 < 90:
            stop = rn - 1; break
    if stop is None: stop = civic[-1]

    # band capacity on per-seat bands (forecourt = formal; promenade excluded)
    capg = defaultdict(int); capc = defaultdict(int)
    table = []
    for rn in sorted(rows):
        r = rows[rn]
        if r["kind"] != "seating":
            table.append((rn, r["zone"], r["kind"], r["elev"],
                          min(r["centreCs"]) if r["centreCs"] else None, None, None, None, None))
            continue
        centre = min(r["centreCs"]) if r["centreCs"] else None
        c10, pp = per_row.get(rn, (None, None))
        if r["zone"] == "forecourt":
            b = "formal"                      # front/close rows, open view
        else:
            b = band(c10)
        g = seats(r["len"], 1.83); c = seats(r["len"], 1.50)
        if b in ("formal", "soft", "marginal", "rim"):
            capg[b] += g; capc[b] += c
        table.append((rn, r["zone"], r["kind"], r["elev"], centre, c10, pp,
                      band(centre) if centre is not None else ("formal" if r["zone"]=="forecourt" else None), b))

    Cf_g = capg["formal"] + 0.5*capg["soft"] + 0.15*capg["marginal"]
    Cf_c = capc["formal"] + 0.5*capc["soft"] + 0.15*capc["marginal"]

    with open(OUT/"perseat_bands.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["row","zone","kind","elev","centreline_C_mm","perseat_C10_mm","pct_pass",
                    "band_centreline","band_perseat"])
        for t in table: w.writerow(t)

    print(f"Conservative formal stop (per-seat C10 ≥ 90): civic row {stop}")
    print(f"  (centreline stop was row 18)")
    print(f"Formal (≥90 per-seat): generous {capg['formal']}  compact {capc['formal']}")
    print(f"Soft (60–90):          generous {capg['soft']}  compact {capc['soft']}")
    print(f"Marginal (30–60):      generous {capg['marginal']}  compact {capc['marginal']}")
    print(f"Rim (<30, excl):       generous {capg['rim']}  compact {capc['rim']}")
    print(f"C_formal banded:       generous {Cf_g:.0f}  compact {Cf_c:.0f}")
    print("\nrow  zone      C_centre  C10(perseat)  %pass  band_c -> band_perseat")
    for (rn,zone,kind,elev,centre,c10,pp,bc,bp) in table:
        if kind != "seating" or zone != "civic": continue
        print(f"{rn:>3}  {zone:<8}  {str(centre):>8}  {str(c10):>10}  {str(pp):>5}   {str(bc):<8}-> {bp}")
    print(f"\nWrote {OUT/'perseat_bands.csv'}")

if __name__ == "__main__":
    main()
