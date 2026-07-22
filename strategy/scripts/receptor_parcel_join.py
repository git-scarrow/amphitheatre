#!/usr/bin/env python3
"""T-2: join the 184 bay-band-v2 street receptors to county parcels + tax-roll attributes.

Inputs (read-only):
  analysis/bay_view_obstruction/neighbor_receptors.geojson  [commit 4e6d03a, EPSG:6494]
  strategy/data/parcels_block_6494.json   TaxParcel_1K polygons, gis.emmetcounty.org,
                                          pulled 2026-07-21, outSR=6494 (esriJSON)
  requests/self_serve/emmet_parcels_park.json  tax-roll attributes (PID, OWNER1, SEV, TAX,
                                          PROP_CLASS, ZONING1), pulled 2026-07-06, no geometry

Method: for each receptor point, nearest parcel-polygon boundary (min point-to-segment
distance over all rings), excluding the pit polygon (52-19-06-224-001), the 223-156 sliver,
and rail/MDOT ROW pseudo-parcels. Attributes joined by PARCELID == PID (exact string).
Receptors farther than MAX_DIST_FT from any parcel are flagged no_match.

Output: strategy/receptor_parcel_join.csv  (one row per receptor, band stats carried
through so T-6 assessment arithmetic shares this exact frame), plus a stdout summary.

Pure stdlib; re-runnable anywhere. EPSG:6494 intl ft throughout.
"""
import csv
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))

RECEPTORS = os.path.join(REPO, "analysis", "bay_view_obstruction", "neighbor_receptors.geojson")
POLYGONS = os.path.join(REPO, "strategy", "data", "parcels_block_6494.json")
ATTRS = os.path.join(REPO, "requests", "self_serve", "emmet_parcels_park.json")
OUT = os.path.join(REPO, "strategy", "receptor_parcel_join.csv")

EXCLUDE_IDS = {"52-19-06-224-001", "52-19-06-223-156"}  # pit polygon; zero-area sliver
MAX_DIST_FT = 150.0


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def poly_dist(px, py, rings):
    d = float("inf")
    for ring in rings:
        for i in range(len(ring) - 1):
            d = min(d, seg_dist(px, py, ring[i][0], ring[i][1], ring[i + 1][0], ring[i + 1][1]))
    return d


def main():
    receptors = json.load(open(RECEPTORS))["features"]
    polys = json.load(open(POLYGONS))["features"]
    attrs = {f["attributes"]["PID"]: f["attributes"]
             for f in json.load(open(ATTRS))["features"]}

    parcels = []
    for p in polys:
        pid = p["attributes"].get("PARCELID") or ""
        if pid in EXCLUDE_IDS or pid.startswith(("RR", "MDOT", "52-N")):
            continue
        parcels.append((pid, p["geometry"]["rings"]))

    rows, matched, with_attrs = [], 0, 0
    for i, r in enumerate(receptors):
        x, y = r["geometry"]["coordinates"]
        pr = r["properties"]
        best_pid, best_d = None, float("inf")
        for pid, rings in parcels:
            d = poly_dist(x, y, rings)
            if d < best_d:
                best_pid, best_d = pid, d
        if best_d > MAX_DIST_FT:
            best_pid, best_d = "", None
        a = attrs.get(best_pid, {})
        if best_pid:
            matched += 1
        if a:
            with_attrs += 1
        rows.append({
            "receptor_idx": i,
            "frontage": pr["frontage"],
            "eye": pr["eye"],
            "E_6494": x, "N_6494": y,
            "eye_elev_navd88": pr["eye_elev_navd88"],
            "clear_pct_S1": pr["clear_pct_S1"],
            "clear_pct_S2_leafon": pr["clear_pct_S2_leafon"],
            "has_bay_band_S1": pr["has_bay_band_S1"],
            "has_bay_band_S2": pr["has_bay_band_S2"],
            "parcelid": best_pid,
            "join_dist_ft": round(best_d, 1) if best_d is not None else "",
            "owner1": a.get("OWNER1", ""),
            "owner2": a.get("OWNER2", ""),
            "parcel_addr": a.get("PAR_ADDR", ""),
            "prop_class": a.get("PROP_CLASS", ""),
            "zoning1": a.get("ZONING1", ""),
            "sev": a.get("SEV", ""),
            "taxable": a.get("TAX", ""),
            "attr_source": "emmet_parcels_park.json 2026-07-06" if a else "",
        })

    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    uniq = sorted({r["parcelid"] for r in rows if r["parcelid"]})
    print(f"receptors {len(rows)} | matched {matched} | with tax-roll attrs {with_attrs}")
    print(f"unique frontage parcels: {len(uniq)}")
    for pid in uniq:
        rr = [r for r in rows if r["parcelid"] == pid]
        a = rr[0]
        n_s1 = sum(1 for r in rr if r["has_bay_band_S1"])
        print(f"  {pid} | {str(a['owner1'])[:28]:28s} | SEV {a['sev'] or '?':>10} | "
              f"receptors {len(rr):3d} | S1-banded {n_s1:3d}")


if __name__ == "__main__":
    main()
