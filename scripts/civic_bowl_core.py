"""Civic-bowl core + upper civic landscape — design partition.

Brief: treat the street-bounded contour sweep as the MAXIMUM ENVELOPE, not the
seating plan. Optimize a formal civic-bowl core that stops at the last defensible
sightline band; convert the remaining upper contours into lawn/picnic terraces,
circulation, overlooks, and ADA-accessible rim connections. Report capacity in
quality bands, never a single raw number.

Operates on the existing natural-grade contour bays (design_extended_bays/
seating_bays.geojson) — re-tags real geometry, invents no new seating. New
features added are SCHEMATIC overlook points and ADA rim-entry points (planning
grade; alignment requires survey).

Outputs:
  design_civic_core/zones.geojson   bays re-tagged by design_zone + overlooks + ADA entries
  design_civic_core/README.md       program, band capacity, ADA strategy, public number
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

SRC = Path("design_extended_bays/seating_bays.geojson")
OUT = Path("design_civic_core")
OUT.mkdir(exist_ok=True)

AISLE = 0.18
ALPHA, BETA = 0.5, 0.15
OBLIQUE_DEG = 40.0          # advisory: flank seats beyond this are oblique to the stage

# streets (EPSG:6494) — the outer envelope; rim sits ~at street grade
X_PETOSKEY = 19533270.8     # E boundary (N-S line), ~643 ft
Y_MITCHELL = 750593.6       # S boundary (E-W line), ~641 ft
Y_LAKE     = 750943.1       # N boundary (E-W line), ~617 ft  (low / bay side)


def seats(L, w):
    try:
        return max(0, int(float(L) * (1 - AISLE) // w))
    except (TypeError, ValueError):
        return 0


def band_of(c, kind):
    if kind != "seating":
        return None
    if c in ("", None):
        return "formal"               # front row: nothing in front
    c = float(c)
    return "formal" if c >= 90 else "soft" if c >= 60 else "marginal" if c >= 30 else "rim"


def main():
    fc = json.load(open(SRC))
    feats = fc["features"]

    # --- per-row aggregation for the stop decision -----------------------
    rows = defaultdict(lambda: {"kind": "", "zone": "", "Cs": [], "secs": set(),
                                "elev": None, "R": None})
    for f in feats:
        p = f["properties"]
        rn = int(p["row"])
        r = rows[rn]
        r["kind"] = p["kind"]
        r["zone"] = p["zone"]
        r["secs"].add(p["section"])
        r["elev"] = p["elev"]
        if p.get("C_mm") not in (None, ""):
            r["Cs"].append(float(p["C_mm"]))

    # AUTHORITATIVE bands = per-seat 10th-pct C (flank-aware), from perseat_reband.py.
    # Falls back to centreline min-section C if the per-seat CSV is absent.
    pband = {}
    pb_path = OUT / "perseat_bands.csv"
    if pb_path.exists():
        import csv as _csv
        for r in _csv.DictReader(open(pb_path)):
            if r["band_perseat"]:
                pband[int(r["row"])] = r["band_perseat"]

    def row_band(rn):
        r = rows[rn]
        if r["kind"] == "promenade":
            return "promenade"
        if r["zone"] == "forecourt":
            return "formal"               # front/close rows, open view
        if rn in pband:
            return pband[rn]              # per-seat (authoritative)
        if not r["Cs"]:
            return "formal" if r["kind"] == "seating" else None
        return band_of(min(r["Cs"]), "seating")

    civic_seating = sorted(rn for rn in rows
                           if rows[rn]["zone"] == "civic" and rows[rn]["kind"] == "seating")
    # last defensible band = last contiguous row whose per-seat 10th-pct C >= 90
    stop = None
    for rn in civic_seating:
        if row_band(rn) != "formal":
            stop = rn - 1
            break
    if stop is None:
        stop = civic_seating[-1]

    # --- design_zone assignment per bay (per-seat band) ------------------
    def design_zone(p):
        rn = int(p["row"]); kind = p["kind"]
        if kind == "promenade":
            return "promenade"            # ADA distribution cross-aisle
        if p["zone"] == "forecourt":
            return "formal_core"
        b = row_band(rn)
        if b == "formal":
            return "formal_core"
        if b == "soft":
            return "soft_edge"            # optional upper seating
        return "upper_landscape"          # terrace / lawn / overlook

    # --- band capacity for the CORE (truncated) + landscape tally --------
    cap = {"formal": {"c": 0, "g": 0}, "soft": {"c": 0, "g": 0},
           "landscape_seats_reallocated": {"c": 0, "g": 0}}
    oblique_core = []
    for f in feats:
        p = f["properties"]
        dz = design_zone(p)
        c = seats(p["length_ft"], 1.50); g = seats(p["length_ft"], 1.83)
        if dz == "formal_core" and p["kind"] == "seating":
            cap["formal"]["c"] += c; cap["formal"]["g"] += g
            if float(p.get("cross_angle_deg") or 0) > OBLIQUE_DEG:
                oblique_core.append((p["row"], p["section"], p["cross_angle_deg"]))
        elif dz == "soft_edge":
            cap["soft"]["c"] += c; cap["soft"]["g"] += g
        elif dz == "upper_landscape" and p["kind"] == "seating":
            cap["landscape_seats_reallocated"]["c"] += c
            cap["landscape_seats_reallocated"]["g"] += g

    Cformal_g = cap["formal"]["g"] + ALPHA * cap["soft"]["g"]
    Cformal_c = cap["formal"]["c"] + ALPHA * cap["soft"]["c"]

    # --- re-tagged geojson + schematic overlooks & ADA entries -----------
    out_feats = []
    for f in feats:
        p = dict(f["properties"])
        p["design_zone"] = design_zone(p)
        p["band"] = band_of(p.get("C_mm"), p["kind"])
        p["oblique"] = float(p.get("cross_angle_deg") or 0) > OBLIQUE_DEG
        out_feats.append({"type": "Feature", "geometry": f["geometry"], "properties": p})

    # endpoints of upper-landscape bays, by section, for overlook siting
    def bay_pts(f):
        g = f["geometry"]
        return g["coordinates"]

    upper = [f for f in feats if design_zone(f["properties"]) == "upper_landscape"
             and f["properties"]["kind"] == "seating"]
    # overlook points: midpoint of the highest bay in each section present up top
    by_sec_top = {}
    for f in upper:
        s = f["properties"]["section"]; rn = int(f["properties"]["row"])
        if s not in by_sec_top or rn > by_sec_top[s][0]:
            by_sec_top[s] = (rn, f)
    for s, (rn, f) in by_sec_top.items():
        pts = bay_pts(f)
        mid = pts[len(pts) // 2]
        out_feats.append({"type": "Feature",
                          "geometry": {"type": "Point", "coordinates": [round(mid[0], 2), round(mid[1], 2)]},
                          "properties": {"design_zone": "overlook", "kind": "bay_overlook",
                                         "section": s, "top_row": rn,
                                         "elev": f["properties"]["elev"],
                                         "faces": "bay (FACE_AZ 312, NW)",
                                         "note": "schematic — best bay view, weakest stage sightline; at ~rim grade"}})

    # ADA rim entry points: drop from nearest rim bay endpoint to the street line
    def rim_endpoint(section_filter, key):
        """Return the extreme bay endpoint (max elev row) for a section group."""
        cand = [f for f in feats if f["properties"]["kind"] in ("seating", "promenade")
                and f["properties"]["section"] in section_filter]
        if not cand:
            return None
        f = max(cand, key=lambda f: f["properties"]["elev"])
        pts = bay_pts(f)
        return f, (pts[0], pts[-1])

    ada_entries = [
        ("east",   {"east"},  "Petoskey St (E, ~643 ft)", ("x", X_PETOSKEY)),
        ("south",  {"south", "bend"}, "E Mitchell St (S, ~641 ft)", ("y", Y_MITCHELL)),
        ("north",  None,      "E Lake St (N, ~617 ft — bay/stage side)", ("y", Y_LAKE)),
    ]
    for label, secs, street, (axis, val) in ada_entries:
        if secs is None:
            # north/bay side: tie to the promenade (lowest cross-aisle)
            prom = [f for f in feats if f["properties"]["kind"] == "promenade"]
            if not prom:
                continue
            pts = bay_pts(prom[0]); end = pts[len(pts) // 2]
        else:
            r = rim_endpoint(secs, axis)
            if not r:
                continue
            _, (p0, p1) = r
            end = p0 if (axis == "x" and abs(p0[0] - val) < abs(p1[0] - val)) or \
                        (axis == "y" and abs(p0[1] - val) < abs(p1[1] - val)) else p1
        street_pt = [val, end[1]] if axis == "x" else [end[0], val]
        out_feats.append({"type": "Feature",
                          "geometry": {"type": "LineString",
                                       "coordinates": [[round(street_pt[0], 2), round(street_pt[1], 2)],
                                                       [round(end[0], 2), round(end[1], 2)]]},
                          "properties": {"design_zone": "ada_rim_connection", "kind": "ada_entry",
                                         "from_street": street,
                                         "note": "SCHEMATIC accessible entry at rim grade; alignment/slope require survey"}})

    json.dump({"type": "FeatureCollection", "features": out_feats},
              open(OUT / "zones.geojson", "w"))

    # --- README ----------------------------------------------------------
    stop_R = rows[stop]["R"] = rows[stop].get("R")
    stop_elev = rows[stop]["elev"]
    md = f"""# Civic-Bowl Core + Upper Civic Landscape

Design partition of the street-bounded contour envelope
(`design_extended_bays/seating_bays.geojson`, natural grade, face 312).
**The envelope is the maximum site reach; this partition is the seating plan.**

## Formal-bowl stop (last defensible sightline band)
- **Formal seating stops at civic row {stop}** (elev ≈ {stop_elev} ft).
- Stop rule: last contiguous row whose **min-section** centreline C ≥ 90 mm.
- Row {stop+1} (soft edge, 60–90 mm) is offered as *optional* upper seating only.
- Rows {stop+2}+ fall to 30–60 / <30 mm AND lose their east/south sections to the
  streets (clipped) → **landscape, not seats.**

## Capacity by quality band (NOT a single raw number)
| band | generous 22-in | compact 18-in | weight |
|---|---|---|---|
| **Formal core (≥90 mm, rows ≤{stop} + forecourt)** | {cap['formal']['g']} | {cap['formal']['c']} | 1.0 |
| Soft edge (row {stop+1}, 60–90 mm, optional) | {cap['soft']['g']} | {cap['soft']['c']} | {ALPHA} |
| **C_formal (quality-banded)** | **{Cformal_g:.0f}** | **{Cformal_c:.0f}** | — |
| Upper rows reallocated to landscape (NOT counted as seats) | {cap['landscape_seats_reallocated']['g']} | {cap['landscape_seats_reallocated']['c']} | 0 |

**Public-facing:** *"~{cap['formal']['g']:,}–{cap['formal']['c']:,} high-quality formal seats,
+{cap['soft']['g']}–{cap['soft']['c']} optional upper-edge seats, plus lawn/terrace overflow
and bay overlooks along the rim."* Do **not** advertise the full envelope as formal seating.

## Upper civic landscape program (rows {stop+2}+)
The weakest-stage rows are the **best bay-view** rows and sit **at street grade** — so the
upper contours become public landscape, not forced seats:
- **Lawn / picnic terraces** — the broad upper contour benches (informal seating, blankets,
  standing overflow during large events).
- **Bay overlooks** — schematic points at the top of each section (face NW / 312 toward the
  bay); best panorama in the park, reached at grade.
- **Rim circulation** — perimeter path along the top tying the three street frontages.
- **ADA-accessible rim connections** — at-grade entries from Petoskey (E), E Mitchell (S),
  and E Lake (N, bay/stage side → promenade). Because the rim is ~at street grade, the
  **upper rim is the natural accessible viewing zone**; switchback ramps descend from the
  rim/promenade to mid-bowl accessible positions (row {[rn for rn in rows if rows[rn]['kind']=='promenade'][0] if any(rows[rn]['kind']=='promenade' for rn in rows) else 5}).

## Public-space hierarchy
1. Stage + forecourt (event focus)
2. Formal raked bowl (rows ≤{stop}) — every seat reliable view geometry
3. Soft upper-edge seating (row {stop+1}, optional)
4. Lawn / picnic terraces + bay overlooks (rows {stop+2}+)
5. Street-edge rim circulation + ADA connections (Petoskey / E Lake / E Mitchell)

## Caveats (observed)
- Bands use **centreline** C; per-seat 10th-pct C (flank-aware) is stricter — formal counts
  are an upper bound. {('Oblique core flank rows (cross-angle >'+str(OBLIQUE_DEG)+'°): '+', '.join(f'r{r}/{s}/{a}°' for r,s,a in oblique_core)) if oblique_core else 'No core rows exceed the oblique flank threshold.'}
- Overlook & ADA features are **schematic** (planning grade); alignment/slope require survey.
- Geometry inherits the extended_bays gates (tread z-residual ≤0.25 ft, zero forced fill,
  no retaining wall) — feasibility carried from that sweep, not re-run here.
"""
    (OUT / "README.md").write_text(md)

    # console
    print(f"Formal-bowl stop: civic row {stop} (elev ~{stop_elev} ft)")
    print(f"Formal core seats:   generous {cap['formal']['g']}   compact {cap['formal']['c']}")
    print(f"Soft edge (row {stop+1}):   generous {cap['soft']['g']}   compact {cap['soft']['c']}")
    print(f"C_formal banded:     generous {Cformal_g:.0f}   compact {Cformal_c:.0f}")
    print(f"Reallocated to landscape (not seats): generous {cap['landscape_seats_reallocated']['g']}  compact {cap['landscape_seats_reallocated']['c']}")
    print(f"Overlooks: {sum(1 for f in out_feats if f['properties'].get('kind')=='bay_overlook')}  "
          f"ADA entries: {sum(1 for f in out_feats if f['properties'].get('kind')=='ada_entry')}")
    if oblique_core:
        print(f"Oblique core flank rows (>{OBLIQUE_DEG}°): {oblique_core}")
    print(f"Wrote {OUT/'zones.geojson'} and {OUT/'README.md'}")


if __name__ == "__main__":
    main()
