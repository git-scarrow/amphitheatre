"""Quality-banded capacity for the street-bounded contour sweep.

Implements the design reading: the street-clipped contour sweep is the MAXIMUM
ENVELOPE, not the seating plan. The formal bowl stops at the last defensible
sightline band; upper contours become terraces / lawn / circulation / overlooks.

Capacity is reported in C-value quality bands, NOT as a single raw number:

    C_formal = N(>=90mm) + alpha * N(60-90mm) + beta * N(30-60mm),  N(<30mm)=0
    alpha = 0.5, beta = 0.15

Source of truth for per-row sightline quality (natural grade, zero-fill):
    design_extended_bays/composition_table.csv   (centreline C_mm per row)

Note: centreline C_mm slightly OVERSTATES quality for the segmented upper rows;
the extended_bays per-seat 10th-pct C (cross_angle-aware) is stricter. Flagged.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

ALPHA = 0.5    # 60-90 mm (soft upper) credit
BETA = 0.15    # 30-60 mm (marginal) credit
# bands by centreline C (mm)
FORMAL_MIN = 90
SOFT_MIN = 60
MARGINAL_MIN = 30

SRC = Path("design_extended_bays/composition_table.csv")
OUT = Path("design_extended_bays/quality_bands.md")


def band_of(c_mm, kind):
    """Front row / forecourt seats with no computed C see the stage directly -> formal."""
    if kind != "seating":
        return None
    if c_mm is None or c_mm == "":
        return "formal"        # row 1: nothing in front, best view
    c = float(c_mm)
    if c >= FORMAL_MIN:
        return "formal"
    if c >= SOFT_MIN:
        return "soft"
    if c >= MARGINAL_MIN:
        return "marginal"
    return "rim"


def main():
    rows = list(csv.DictReader(open(SRC)))

    # aggregate per row number (sum sections present in that row)
    per_row = defaultdict(lambda: {"seats": 0, "zone": "", "kind": "", "C_mm": None,
                                    "elev": None, "R": None, "max_cross": 0.0, "sections": []})
    for r in rows:
        rn = int(r["row"])
        seats = int(r["seats"] or 0)
        pr = per_row[rn]
        pr["seats"] += seats
        pr["zone"] = r["zone"]
        pr["kind"] = r["kind"]
        pr["C_mm"] = r["C_mm"] if r["C_mm"] not in ("", None) else pr["C_mm"]
        pr["elev"] = float(r["elev"])
        pr["R"] = float(r["axis_radius_ft"])
        try:
            pr["max_cross"] = max(pr["max_cross"], float(r["cross_angle_deg"]))
        except (ValueError, TypeError):
            pass
        pr["sections"].append(r["section"])

    band_seats = defaultdict(int)
    band_rows = defaultdict(list)
    forecourt_seats = 0
    rowinfo = []
    for rn in sorted(per_row):
        pr = per_row[rn]
        b = band_of(pr["C_mm"], pr["kind"])
        is_fore = pr["zone"] == "forecourt"
        if pr["kind"] == "promenade":
            b = "promenade"
        if b in ("formal", "soft", "marginal", "rim"):
            band_seats[b] += pr["seats"]
            band_rows[b].append(rn)
        if is_fore and pr["kind"] == "seating":
            forecourt_seats += pr["seats"]
        n_sec = len(set(pr["sections"]))
        clipped = n_sec < 3 and pr["zone"] == "civic"
        rowinfo.append((rn, pr["zone"], pr["kind"], pr["R"], pr["elev"],
                        pr["C_mm"], pr["seats"], round(pr["max_cross"], 0), b, n_sec, clipped))

    Nf = band_seats["formal"]
    Ns = band_seats["soft"]
    Nm = band_seats["marginal"]
    Nr = band_seats["rim"]
    C_formal = Nf + ALPHA * Ns + BETA * Nm
    total_raw = Nf + Ns + Nm + Nr

    # last contiguous formal row (the defensible stop)
    formal_rows = sorted(band_rows["formal"])
    # walk civic seating rows in order; stop at first non-formal seating row
    civic_seating = [ri for ri in rowinfo if ri[1] == "civic" and ri[2] == "seating"]
    stop_row = None
    for ri in civic_seating:
        if ri[8] != "formal":
            stop_row = ri[0] - 1
            break
    if stop_row is None and civic_seating:
        stop_row = civic_seating[-1][0]

    # build report
    L = ["# Street-bounded contour sweep — quality-banded capacity", "",
         f"Source: `{SRC}` (natural-grade contour bays, zero forced fill).",
         f"Seat width: generous (22 in) as in the extended_bays sweep. Bands by centreline C.",
         "",
         "## Band weights",
         f"- formal (C ≥ 90 mm): weight 1.0",
         f"- soft (60–90 mm): weight α = {ALPHA}",
         f"- marginal (30–60 mm): weight β = {BETA}",
         f"- rim (< 30 mm): weight 0 (not counted as seating)",
         "",
         "## Capacity by band (generous seats)",
         "| band | rows | seats | weight | weighted |",
         "|---|---|---|---|---|",
         f"| formal (≥90) | {fmt_rows(band_rows['formal'])} | {Nf} | 1.0 | {Nf} |",
         f"| soft (60–90) | {fmt_rows(band_rows['soft'])} | {Ns} | {ALPHA} | {ALPHA*Ns:.0f} |",
         f"| marginal (30–60) | {fmt_rows(band_rows['marginal'])} | {Nm} | {BETA} | {BETA*Nm:.0f} |",
         f"| rim (<30) | {fmt_rows(band_rows['rim'])} | {Nr} | 0 | 0 |",
         f"| **total raw** | — | **{total_raw}** | — | — |",
         f"| **C_formal (quality-banded)** | — | — | — | **{C_formal:.0f}** |",
         "",
         "## Headline numbers",
         f"- **Formal seats (strict, ≥90 mm):** {Nf}",
         f"- **Formal + soft upper (rows incl. 60–90 mm):** {Nf + Ns}",
         f"- **Full envelope raw (do NOT advertise as formal):** {total_raw}",
         f"- **Quality-banded C_formal:** {C_formal:.0f}",
         f"- **Defensible formal-bowl stop: civic seating row {stop_row}** "
         f"(R ≈ {dict((r[0], r[3]) for r in rowinfo).get(stop_row, '?')} ft).",
         "",
         "## Per-row detail (* = clipped: <3 sections present)",
         "| row | zone | kind | R ft | elev | C mm | seats | maxX° | band | secs |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for (rn, zone, kind, R, elev, C, seats, mx, b, nsec, clip) in rowinfo:
        L.append(f"| {rn}{'*' if clip else ''} | {zone} | {kind} | {R} | {elev} | "
                 f"{C if C not in (None,'') else '—'} | {seats} | {mx:.0f} | {b or '—'} | {nsec} |")
    OUT.write_text("\n".join(L) + "\n")

    # console
    print(f"Formal (≥90):            {Nf}")
    print(f"+ soft upper (60–90):    {Nf + Ns}   (soft alone {Ns}, rows {fmt_rows(band_rows['soft'])})")
    print(f"+ marginal (30–60):      {Nf + Ns + Nm}   (marginal {Nm}, rows {fmt_rows(band_rows['marginal'])})")
    print(f"rim (<30, not counted):  {Nr}   rows {fmt_rows(band_rows['rim'])}")
    print(f"TOTAL RAW envelope:      {total_raw}")
    print(f"C_formal (banded):       {C_formal:.0f}")
    print(f"forecourt seats incl:    {forecourt_seats}")
    print(f"Defensible formal stop:  civic seating row {stop_row}")
    print(f"\nWrote {OUT}")


def fmt_rows(rs):
    if not rs:
        return "—"
    rs = sorted(rs)
    out, start, prev = [], rs[0], rs[0]
    for x in rs[1:]:
        if x == prev + 1:
            prev = x; continue
        out.append(f"{start}-{prev}" if start != prev else f"{start}")
        start = prev = x
    out.append(f"{start}-{prev}" if start != prev else f"{start}")
    return ",".join(out)


if __name__ == "__main__":
    main()
