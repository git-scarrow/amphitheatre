#!/usr/bin/env python3
"""T5 — Element re-verdict (section-B menu) against v2 effective silhouette +
Reading-B neighbor gate.

For each superstructure element (roof 22 · acoustic canopy 18 · service_canopy 21
· boh 12 · masts 26 · wings 12 · apron 1, tops above the 612.5 deck) at the
selected placement P_opt (front centre 19533106.6,750762.8; axis 150; boh
west/left), charge:

  (1) INTERIOR bands — incremental corridor bay-% newly blocked for the audience
      under S1 (terrain+stage+city) and S2 (+canopy, leaf-on operating season),
      using the far-shore band top. Reported as worst-family delta and compared
      to the OLD terrain-only charge in STAGE_SHAPE_STUDY.md §C.
      TRAP: under S2 the canopy already blanks most interior bands, so an
      element's S2 charge is near-zero — that leeway is CONTINGENT on third-party
      trees and is flagged contingent_on_canopy; never pass an element on it.

  (2) NEIGHBOR gate (Reading B) — element top vs the neighbor-ceiling raster
      (S1 durable / S2 contingent) sampled over the element's plan footprint.
      PASS if top <= min ceiling under the footprint. Masts are seasonal/
      removable: a mast failure is flagged for owner policy, not auto-rejected.

Output: element_verdicts_v2.md
EPSG:6494 · NAVD88 intl ft · planning-grade. Analysis only; adopts nothing.
"""
import json
import math
import os
import sys

import numpy as np
import rasterio
from shapely.geometry import shape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import in_situ_common as C
import bay_band_v2 as V
import stage_shape_study as S

REPO = C.REPO
OUT = os.path.join(REPO, "analysis", "bay_view_obstruction")
DECK = C.FOCUS_ELEV
AZS = V.azimuths()

ELEMENTS = [  # label, z_top, seasonal_removable
    ("roof", DECK + 22.0, False),
    ("canopy", DECK + 18.0, False),
    ("service_canopy", DECK + 21.0, False),
    ("boh", DECK + 12.0, False),
    ("mast_l", DECK + 26.0, True),
    ("mast_r", DECK + 26.0, True),
    ("wing_l", DECK + 12.0, False),
    ("wing_r", DECK + 12.0, False),
    ("apron", DECK + 1.0, False),
]
# old terrain-only worst-family bay% from STAGE_SHAPE_STUDY.md §C
OLD_BAY = dict(roof=8.6, canopy=16.1, service_canopy=18.6, boh=7.3,
               mast_l=3.2, mast_r=1.7, wing_l=4.3, wing_r=2.2, apron=0.0)


def element_polys():
    """Reconstruct element footprints at P_opt via stage_shape_study.typologies."""
    P = (19533106.6, 750762.8)
    az = 150.0
    best_corner_w = -1.0    # boh_corner "west/left"
    typ = S.typologies(P, az, best_corner_w)
    polys = {}
    for elements in typ.values():
        for (label, poly, zb, zt, note) in elements:
            polys[label] = poly
    # apron/service_canopy live in T7_hybrid; deck ignored
    return polys


def base_cache(eng):
    """Per (band, sample, az): terrain/stage/city/canopy silhouettes + theta_top.
    Cached once so each element only adds a cheap poly_sil."""
    cache = {}
    for section in V.SECTION_ORDER:
        for row in C.FORMAL_ROWS:
            feat = eng.treads.get((row, section))
            if not feat:
                continue
            elev = feat["properties"]["tread_elev_navd88"]
            eye = elev + C.EYE_SEATED_FT
            for (sx, sy) in eng.samples(feat["geometry"]):
                for az in AZS:
                    e, n = C.U(float(az))
                    ts, _ = eng.terrain_sil(sx, sy, e, n, eye)
                    ss, _, _ = eng.poly_sil(sx, sy, e, n, eye, eng.stage)
                    cs, _, _ = eng.poly_sil(sx, sy, e, n, eye, eng.buildings)
                    koff, _ = eng.canopy_sil(sx, sy, e, n, eye, "leafoff")
                    kon, _ = eng.canopy_sil(sx, sy, e, n, eye, "leafon")
                    _, tt, _, _ = eng.far_shore(sx, sy, e, n, eye)
                    cache[(section, row, sx, sy, float(az))] = dict(
                        sx=sx, sy=sy, e=e, n=n, eye=eye,
                        terrain=ts, stage=ss, city=cs,
                        canopy_off=koff, canopy_on=kon, tt=tt,
                        section=section, row=row)
    return cache


def clear_pct(cache, section, setkey, element_poly=None, ztop=None):
    """corridor clear% for one section aggregated over rows/samples/az, under
    setkey in {S1,S2}, optionally with an added element occluder."""
    # group by (row) then samples/az; return mean over rows of per-row clear%
    rows = {}
    for k, r in cache.items():
        if r["section"] != section:
            continue
        rows.setdefault(r["row"], []).append(r)
    perrow = []
    for row, rr in rows.items():
        n = 0; c = 0
        for r in rr:
            base = max(r["terrain"], r["stage"], r["city"])
            if setkey == "S2":
                base = max(base, r["canopy_on"])
            sil = base
            if element_poly is not None:
                es, _, _ = _poly_sil(r, element_poly, ztop)
                sil = max(sil, es)
            n += 1
            if r["tt"] > sil:
                c += 1
        perrow.append(100.0 * c / n)
    return float(np.mean(perrow)) if perrow else 0.0


def _poly_sil(r, poly, ztop):
    from shapely.geometry import LineString
    ox, oy, e, n, eye = r["sx"], r["sy"], r["e"], r["n"], r["eye"]
    line = LineString([(ox + e * 6, oy + n * 6), (ox + e * V.RAY_MAX, oy + n * V.RAY_MAX)])
    inter = line.intersection(poly)
    if inter.is_empty:
        return -90.0, None, None
    dists = []
    for g in getattr(inter, "geoms", [inter]):
        for cx, cy in (g.coords if hasattr(g, "coords") else []):
            dists.append(math.hypot(cx - ox, cy - oy))
    if not dists:
        return -90.0, None, None
    dn = min(dists)
    return math.degrees(math.atan2(ztop - eye, dn)), dn, None


def ceiling_under(poly, tif):
    ds = rasterio.open(tif)
    a = ds.read(1); nd = ds.nodata
    minx, miny, maxx, maxy = poly.bounds
    vals = []
    inv = ~ds.transform
    # sample a grid of the footprint at 2 ft
    x = minx
    while x <= maxx:
        y = miny
        while y <= maxy:
            from shapely.geometry import Point
            if poly.contains(Point(x, y)):
                c, rr = inv * (x, y)
                c = int(c); rr = int(rr)
                if 0 <= rr < a.shape[0] and 0 <= c < a.shape[1] and a[rr, c] != nd:
                    vals.append(float(a[rr, c]))
            y += 2.0
        x += 2.0
    return (min(vals) if vals else None), len(vals)


def main():
    eng = V.Engine()
    polys = element_polys()
    cache = base_cache(eng)

    # base clear% per section (no element) under S1/S2
    base = {s: {"S1": clear_pct(cache, s, "S1"), "S2": clear_pct(cache, s, "S2")}
            for s in V.SECTION_ORDER}

    rows_md = []
    verdicts = []
    for label, ztop, seasonal in ELEMENTS:
        poly = polys[label]
        chg = {"S1": {}, "S2": {}}
        for setkey in ("S1", "S2"):
            for s in V.SECTION_ORDER:
                with_el = clear_pct(cache, s, setkey, poly, ztop)
                chg[setkey][s] = round(base[s][setkey] - with_el, 1)   # bay% newly blocked
        worst_s1 = max(chg["S1"].values())
        worst_s2 = max(chg["S2"].values())
        c_s1, n_s1 = ceiling_under(poly, os.path.join(OUT, "neighbor_ceiling_S1.tif"))
        c_s2, n_s2 = ceiling_under(poly, os.path.join(OUT, "neighbor_ceiling_S2.tif"))
        gate_s1 = ("PASS" if (c_s1 is None or ztop <= c_s1 + 1e-6)
                   else "FAIL")
        gate_s2 = ("PASS" if (c_s2 is None or ztop <= c_s2 + 1e-6) else "FAIL")
        maxh_s1 = round((c_s1 - DECK), 1) if c_s1 is not None else None
        maxh_s2 = round((c_s2 - DECK), 1) if c_s2 is not None else None
        flag = "contingent_on_canopy" if (worst_s1 > 2.0 and worst_s2 <= 2.0) else ""
        if seasonal and (gate_s1 == "FAIL" or gate_s2 == "FAIL"):
            gate_note = "FAIL→owner-policy (seasonal/removable; screen night-only)"
        else:
            gate_note = ""
        verdicts.append(dict(label=label, ztop=ztop, worst_s1=worst_s1, worst_s2=worst_s2,
                             old=OLD_BAY.get(label), gate_s1=gate_s1, gate_s2=gate_s2,
                             maxh_s1=maxh_s1, maxh_s2=maxh_s2, ceil_s1=c_s1, ceil_s2=c_s2,
                             flag=flag, gate_note=gate_note, seasonal=seasonal))
        rows_md.append(
            f"| {label} | {ztop:.1f} | {OLD_BAY.get(label)} | {worst_s1} | {worst_s2} "
            f"| {gate_s1} | {gate_s2} | {maxh_s1} | {maxh_s2} | "
            f"{flag or gate_note or '—'} |")

    _write_md(base, verdicts, rows_md)
    print("element gate summary (deck 612.5):")
    for v in verdicts:
        print(f"  {v['label']:15s} top {v['ztop']:.1f}  S1 charge {v['worst_s1']:+.1f}% "
              f"(old {v['old']})  S2 {v['worst_s2']:+.1f}%  gate S1 {v['gate_s1']} "
              f"S2 {v['gate_s2']}  maxH_S1 {v['maxh_s1']}  {v['flag']}{v['gate_note']}")
    print("wrote element_verdicts_v2.md")


def _write_md(base, verdicts, rows_md):
    L = [
        "# Element re-verdict v2 — section-B menu vs effective silhouette + neighbor gate",
        "",
        "**Placement:** P_opt (front centre 19533106.6, 750762.8; axis 150°; boh west/left). "
        "Deck 612.5 ft. Elements charged ALONE (compose per STAGE_SHAPE_STUDY §B/§C).",
        "",
        "**Interior charge** = worst-family incremental corridor bay-% newly blocked for the "
        "audience, under the v2 far-shore band top:",
        "- **S1** = terrain + flat stage + LiDAR-verified city (DURABLE).",
        "- **S2** = + canopy (leaf-on, operating season). Under S2 the foreground canopy "
        "already blanks most interior bands (see rn_rm_table: no row is acceptable through "
        "the trees), so element S2 charges collapse toward 0 — **that leeway is contingent on "
        "third-party trees (Bayfront Park City land / MDOT ROW) and must not pass an element** "
        "(trap #3). Elements flagged `contingent_on_canopy` clear only because of the canopy.",
        "",
        "**Neighbor gate (Reading B, owner 2026-07-21, verbatim):** _\"no owner loses any bay "
        "view\"_ — NOT \"no visible skyline change.\" Skyline change above the 618.04 rim from "
        "the streets is accepted and reported, not gated. Gate = element top vs the "
        "neighbor-ceiling raster over the element footprint. **S1 ceiling is durable**; S2-only "
        "headroom is contingent. maxH = max permissible height above deck at the footprint.",
        "",
        f"Base corridor clear% (no element): "
        + ", ".join(f"{s} S1={base[s]['S1']:.0f}/S2={base[s]['S2']:.0f}" for s in V.SECTION_ORDER),
        "",
        "> **Basis note:** the v2 interior charge is the drop in corridor **clear%** "
        "(fraction of 318–342° rays that flip water→blocked when the element is added), "
        "under the far-shore band top. STAGE_SHAPE_STUDY §C's `new_bay_blocked_pct` is an "
        "area-weighted share of the existing visible band on a ray-crossing basis. The two "
        "are related but NOT the same metric, so absolute numbers are not apples-to-apples; "
        "the load-bearing finding is the **direction**: against the corrected (thinner) "
        "far-shore band, the big overhead elements charge MORE to the audience under S1 than "
        "the terrain-only study credited.",
        "",
        "| element | top ft | old §C bay% (terrain) | v2 S1 bay% | v2 S2 bay% | gate S1 | gate S2 | maxH S1 ft | maxH S2 ft | flag |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ] + rows_md + [
        "",
        "## Verdict changes vs the terrain-only baseline",
        "",
    ]
    # narrative
    for v in verdicts:
        note = []
        if v["old"] is not None:
            note.append(f"interior charge S1 {v['worst_s1']}% vs old terrain-only {v['old']}%")
        note.append(f"S2 {v['worst_s2']}%")
        if v["flag"]:
            note.append("**contingent_on_canopy** (S2 leeway is third-party/mutable)")
        note.append(f"neighbor gate S1 **{v['gate_s1']}**"
                    + (f" (maxH {v['maxh_s1']} ft; top {v['ztop']-DECK:.0f} ft)"
                       if v["gate_s1"] == "FAIL" else ""))
        if v["gate_note"]:
            note.append(v["gate_note"])
        L.append(f"- **{v['label']}** (top {v['ztop']:.1f} ft): " + "; ".join(note) + ".")
    L += ["",
          "## Key reframes",
          "- The v2 **binding interior occluder is the canopy**, not the stage or its elements: "
          "no seated row achieves an acceptable (>=80%) bay view through today's tree line "
          "(rn_rm_table r_m = none, both leaf states). Element interior charges therefore read "
          "as small increments on an already tree-limited view — real under S1 (if trees are "
          "trimmed/removed the audience regains the bay and the element charge bites), ~0 under "
          "S2 (trees present). Both must be stated with their occluder set + leaf state.",
          "- The **durable constraint is the neighbor gate under S1**. Elements whose top exceeds "
          "the ~635 ft S1 neighbor ceiling over the stage intrude into E/S/SE street water views.",
          "",
          "_Adopts nothing; owner sign-off required (traps #4/#5)._"]
    open(os.path.join(OUT, "element_verdicts_v2.md"), "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
