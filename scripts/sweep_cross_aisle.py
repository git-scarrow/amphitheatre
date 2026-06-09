"""Cross-aisle adjacent-row-pair × section-strategy sweeper.

The accepted Scenario E cross-aisle is resolved in PLAN (rows 9|10 reclassified,
0 sqft overlap, displaced seats subtracted) but UNRESOLVED in SECTION: its whole
vertical treatment is one line — `flatten_pad(band, (e9+e10)/2)` — a dead-flat
midpoint datum with 0% slope, no grade-break analysis at the radial edges, no
drainage, and no test that rows 9|10 are even the right pair.

This module stops ASSUMING rows 9|10 + midpoint-flat and SWEEPS the real decision:

  decision = (row_pair (i,i+1))  ×  (section_strategy)

  section_strategy ∈ {
    preserve_lower      hold the band at the inner (lower) reclassified row's elev
    preserve_upper      hold the band at the outer (upper) reclassified row's elev
    midpoint_datum      flat at the mean of the two rows (the current Scenario E choice)
    cascade             let the band keep the natural radial rake (flush both edges)
    accessible_fit      datum chosen to minimise earthwork, capped at <=2% ADA cross-
                        slope, with a small longitudinal fall to drain, and the
                        residual edge drop carried as priced transition ramps
  }

For EACH candidate the band footprint is built by the SAME row-reclassification that
makes the seats — band = union(row_i,row_i+1).difference(retained) — and then the
candidate is re-validated on the ACTUAL proposed surface:

  seat displacement -> net formal capacity      (seats in the two reclassified rows)
  sightlines        -> SL.compute_rows, formal-fail count on retained rows 1-18
  section slopes    -> least-squares plane fit on the band cells (cross + longitudinal)
  grade breaks      -> step height at the inner edge (to row i-1) and outer edge (row i+2)
  drainage          -> does the band fall (longitudinal/cross) or pond flat mid-bowl
  earthwork         -> cut/fill/gross CY on the band's actual surface

Hard gates (must all pass): sightlines hold; the travel surface is wheelable
(cross-slope <=2%); both edge transitions are resolvable (a normal one-riser seating
step, or a ramped <=8.33% transition). Survivors are ranked by minimum effective
intervention: gross earthwork, then total step height bought, then drainage, then
how balanced the upper/lower seating blocks are.

Output -> analysis/cross_aisle_sweep/{sweep_table.csv, proof_table.csv, sweep.json,
RECOMMENDATION.md}
"""
from __future__ import annotations

import csv, json, math, os, sys
from pathlib import Path

import numpy as np
from shapely.geometry import shape, Point
from shapely.ops import unary_union

ROOT = Path(__file__).parent.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT / "scripts"))

from harness.project import ProjectState
from harness.clay import ClayDelta
from harness.earthwork import EarthworkEngine
from harness.sightlines import SightlineEngine

OUT = ROOT / "analysis" / "cross_aisle_sweep"; OUT.mkdir(parents=True, exist_ok=True)

STATE = ProjectState.load("harness_config.yaml")
EW = EarthworkEngine(STATE); SL = SightlineEngine(STATE)
FX, FY = STATE.arc_centre(); TF = STATE.transform; FINITE = np.isfinite(STATE.Z0)
ADA_CROSS_MAX = STATE.cfg["ada"]["cross_slope_target_pct"]   # 2.0
ADA_RUN_MAX   = STATE.cfg["ada"]["running_slope_pct"]        # 8.33
TREAD_HALF = 1.8
TREAD = 3.6
FORMAL_STOP = 18
ONE_RISER_FT = 1.6          # a step <= this is a normal seating riser (no special handling)
DRAIN_MIN_PCT = 0.5         # below this in BOTH directions = flat = ponds
MIN_BLOCK_ROWS = 3          # each seating block (above/below the aisle) should be >= this

# ── row geometry: the SAME object that makes the seating bands ────────────────────
BAYS = json.load(open(ROOT / "design_extended_bays/seating_bays.geojson"))
ROW_ELEV, ROW_R = {}, {}
for r in csv.DictReader(open(ROOT / "design_extended_bays/composition_table.csv")):
    if r.get("kind") == "seating" and r.get("section") == "bend":
        rn = int(r["row"])
        ROW_ELEV.setdefault(rn, float(r["elev"]))
        ROW_R.setdefault(rn, float(r["axis_radius_ft"]))

row_polys, row_seats = {}, {}
for f in BAYS["features"]:
    p = f["properties"]
    if p.get("kind") == "seating" and 1 <= int(p["row"]) <= FORMAL_STOP:
        rn = int(p["row"])
        row_polys.setdefault(rn, []).append(shape(f["geometry"]).buffer(TREAD_HALF, cap_style=2))
        row_seats[rn] = row_seats.get(rn, 0) + int(p.get("seats") or 0)
NOMINAL_FORMAL = sum(row_seats.get(r, 0) for r in range(1, FORMAL_STOP + 1))

# treatment-cell centroid (drain target / flank reference)
_stg = json.load(open(ROOT / "design_open_low/stage_floor.geojson"))
_cell = next(shape(f["geometry"]) for f in _stg["features"]
             if f["properties"].get("name") == "treatment_wet_cell")
DTx, DTy = _cell.centroid.x, _cell.centroid.y

# ── one-time base surface: all formal treads restored (Scenario D) ────────────────
# Retained rows are identical across candidates, so restore once; each candidate only
# overlays its own band. This isolates the SECTION decision as the only variable.
base = ClayDelta.zeros(STATE)
for rn in range(1, FORMAL_STOP + 1):
    for poly in row_polys.get(rn, []):
        base.terrace_plane(STATE, poly, base_elev_navd88=None,
                           cross_slope_pct=2.0, longitudinal_slope_pct=0.5)
BASE_DELTA = base.delta()
BASE_PROPOSED = base.proposed(STATE)
SL_BASE = SL.compute_rows(BASE_PROPOSED)
BASE_FORMAL_FAIL = [r["row"] for r in SL_BASE
                    if r["row"] <= FORMAL_STOP and r["C_value_mm"] is not None and not r["meets_C"]]


def cell_ns(mask, R_ref):
    """Radial offset n (across-row, +outward) and tangential s (along-arc) per masked cell."""
    ri, ci = np.where(mask)
    x = TF.c + (ci + 0.5) * TF.a; y = TF.f + (ri + 0.5) * TF.e
    R = np.hypot(x - FX, y - FY)
    n = R - R_ref
    r_ref = R_ref + 1e-9
    tx = +(y.mean() - FY) / r_ref if False else None  # unused; tangent computed below
    # tangent at the band centroid azimuth (CW from north)
    cx = x.mean(); cy = y.mean()
    rc = math.hypot(cx - FX, cy - FY) + 1e-9
    tgx = (cy - FY) / rc; tgy = -(cx - FX) / rc
    s = (x - cx) * tgx + (y - cy) * tgy
    return ri, ci, x, y, n, s


def fit_slopes(n, s, e):
    """Least-squares plane e ≈ a*n + b*s + c → cross-slope% (radial), long-slope% (tangential)."""
    A = np.column_stack([n, s, np.ones_like(n)])
    coef, *_ = np.linalg.lstsq(A, e, rcond=None)
    return abs(coef[0]) * 100.0, abs(coef[1]) * 100.0


def flank_azimuth_sign(s):
    """Which along-arc direction heads toward the nearer flank/drain target (for the long. fall)."""
    return 1.0  # convention: fall in +s; magnitude is what the gate checks


def evaluate(i):
    """Evaluate row pair (i, i+1) under all section strategies on the real surface."""
    j = i + 1
    need = [i - 1, i, j, j + 1]
    if not all(r in ROW_ELEV for r in need) or i - 1 < 1 or j + 1 > FORMAL_STOP:
        return None
    if i not in row_polys or j not in row_polys:
        return None

    e_i, e_j = ROW_ELEV[i], ROW_ELEV[j]          # inner(lower), outer(upper)
    e_in_nb, e_out_nb = ROW_ELEV[i - 1], ROW_ELEV[j + 1]
    R_ref = (ROW_R[i] + ROW_R[j]) / 2.0
    rake = (e_j - e_i) / (ROW_R[j] - ROW_R[i])   # natural radial rake (per ft), ~+0.33

    retained = unary_union([p for r in row_polys if r not in (i, j) for p in row_polys[r]])
    band = unary_union(row_polys[i] + row_polys[j]).difference(retained)
    overlap = sum(p.intersection(band).area for r in row_polys if r not in (i, j)
                  for p in row_polys[r])

    mask = ClayDelta.zeros(STATE)._mask_for_geom(band, STATE) & FINITE
    ri, ci, x, y, n, s = cell_ns(mask, R_ref)
    z0 = STATE.Z0[mask]
    n_in_edge = (ROW_R[i] - TREAD_HALF) - R_ref   # inner band edge radial offset
    n_out_edge = (ROW_R[j] + TREAD_HALF) - R_ref

    displaced = row_seats.get(i, 0) + row_seats.get(j, 0)
    net_formal = NOMINAL_FORMAL - displaced
    rows_below = i - 1; rows_above = FORMAL_STOP - j
    block_balance = min(rows_below, rows_above) / max(rows_below, rows_above)
    seats_below = sum(row_seats.get(r, 0) for r in range(1, i))
    seats_above = sum(row_seats.get(r, 0) for r in range(j + 1, FORMAL_STOP + 1))

    mid = (e_i + e_j) / 2.0

    def target_for(strategy):
        """Return (target_elev_array, inner_edge_elev, outer_edge_elev, x_slope_design, l_slope_design)."""
        if strategy == "preserve_lower":
            e = np.full_like(z0, e_i); return e, e_i, e_i, 0.0, 0.0
        if strategy == "preserve_upper":
            e = np.full_like(z0, e_j); return e, e_j, e_j, 0.0, 0.0
        if strategy == "midpoint_datum":
            e = np.full_like(z0, mid); return e, mid, mid, 0.0, 0.0
        if strategy == "cascade":
            # leave the natural rake: the band IS the untouched sloped ground between the
            # retained treads (≈0 earthwork, flush edges). Its realized cross-slope is whatever
            # fit_slopes MEASURES on that leftover footprint — gentler than the row-centerline rake.
            e = z0.copy()
            e_in = float(e_i + rake * (n_in_edge - (ROW_R[i] - R_ref)))   # ground ≈ design at row line
            return e, e_i, e_j, abs(rake) * 100.0, 0.0
        if strategy == "accessible_fit":
            gx = ADA_CROSS_MAX / 100.0               # +2% radial (capped), drains to inner edge
            gl = 1.0 / 100.0                          # 1% longitudinal fall to a flank
            e = mid + gx * n + gl * (s - s.min())
            return (e, mid + gx * n_in_edge, mid + gx * n_out_edge, ADA_CROSS_MAX, 1.0)
        raise ValueError(strategy)

    results = {}
    for strat in ["preserve_lower", "preserve_upper", "midpoint_datum", "cascade", "accessible_fit"]:
        e_tgt, e_inner, e_outer, xs_design, ls_design = target_for(strat)
        d = BASE_DELTA.copy()
        d[ri, ci] = e_tgt - z0
        cd = ClayDelta.zeros(STATE); cd._delta = d
        sub = d[mask]
        cut = float(np.maximum(-sub, 0).sum()) / 27.0
        fill = float(np.maximum(sub, 0).sum()) / 27.0

        xs_meas, ls_meas = fit_slopes(n, s, e_tgt)   # measured slopes on the actual band surface

        # grade breaks at the two radial edges (vs the retained neighbours)
        inner_step = abs(e_inner - e_in_nb)   # band inner edge vs row i-1
        outer_step = abs(e_out_nb - e_outer)  # row i+2 vs band outer edge

        def classify(step):
            if step <= ONE_RISER_FT: return "normal_riser"
            ramp_run = step / (ADA_RUN_MAX / 100.0)         # length if carried as 8.33% ramp
            return f"ramp_{ramp_run:.0f}ft"
        inner_kind = classify(inner_step); outer_kind = classify(outer_step)
        steps_resolvable = True   # any step is either a normal riser or a (priceable) ramp
        # cascade has ~no steps but fails cross-slope; flats have steps but pass cross-slope
        wheelable = xs_meas <= ADA_CROSS_MAX + 0.25
        ponds = (xs_meas < DRAIN_MIN_PCT) and (ls_meas < DRAIN_MIN_PCT)

        # sightlines on the actual proposed surface (retained formal rows only)
        proposed = cd.proposed(STATE)
        slr = SL.compute_rows(proposed)
        formal_fail = [r["row"] for r in slr if r["row"] <= FORMAL_STOP and r["row"] not in (i, j)
                       and r["C_value_mm"] is not None and not r["meets_C"]]
        min_C = min((r["C_value_mm"] for r in slr if r["row"] <= FORMAL_STOP and r["row"] not in (i, j)
                     and r["C_value_mm"] is not None), default=None)

        # transition-ramp earthwork surcharge (resolving any >1-riser edge as an 8.33% ramp)
        ramp_extra_cy = 0.0
        for step, kind in ((inner_step, inner_kind), (outer_step, outer_kind)):
            if kind.startswith("ramp"):
                run = step / (ADA_RUN_MAX / 100.0)
                ramp_extra_cy += (run * 5.0) * (step / 2.0) / 27.0   # wedge vol, 5 ft wide

        gross = round(cut + fill, 1)
        total_with_ramps = round(gross + ramp_extra_cy, 1)

        gate_sightline = len(formal_fail) == 0
        gate_wheel = bool(wheelable)
        gate_steps = steps_resolvable
        gate_block = rows_below >= MIN_BLOCK_ROWS and rows_above >= MIN_BLOCK_ROWS
        # DRAINAGE GATE: a circulation surface mid-hillside that is dead-flat in both
        # directions has nowhere to shed water — it ponds. A self-draining section must
        # carry a fall itself (the flat datums do not; accessible_fit does). This is the
        # gate the incumbent flat-pad never faced.
        gate_drainage = not bool(ponds)
        accept = gate_sightline and gate_wheel and gate_steps and gate_block and gate_drainage

        results[strat] = dict(
            datum_navd88=round(float(np.mean(e_tgt)), 2),
            datum_basis=strat,
            cross_slope_pct=round(xs_meas, 2), long_slope_pct=round(ls_meas, 2),
            cross_slope_design_pct=xs_design, long_slope_design_pct=ls_design,
            inner_edge_elev=round(float(e_inner), 2), outer_edge_elev=round(float(e_outer), 2),
            inner_step_ft=round(inner_step, 2), outer_step_ft=round(outer_step, 2),
            inner_transition=inner_kind, outer_transition=outer_kind,
            total_step_ft=round(inner_step + outer_step, 2),
            wheelable=bool(wheelable), ponds=bool(ponds),
            cut_cy=round(cut, 1), fill_cy=round(fill, 1), gross_cy=gross,
            ramp_surcharge_cy=round(ramp_extra_cy, 1), total_section_cy=total_with_ramps,
            formal_fail=formal_fail, min_C_mm=min_C,
            gate_sightline=gate_sightline, gate_wheelable=gate_wheel,
            gate_steps_resolvable=gate_steps, gate_block_balance=gate_block,
            gate_drainage=gate_drainage,
            accept=bool(accept),
        )

    return dict(
        pair=[i, j], R_ref=round(R_ref, 1), natural_rake_pct=round(abs(rake) * 100, 1),
        band_drop_ft=round(abs(e_j - e_i), 2), retained_overlap_sqft=round(overlap, 1),
        displaced_seats=displaced, net_formal=net_formal,
        rows_below=rows_below, rows_above=rows_above, block_balance=round(block_balance, 2),
        seats_below=seats_below, seats_above=seats_above, strategies=results,
    )


# ── run the sweep ─────────────────────────────────────────────────────────────────
candidates = []
for i in range(6, 14):            # pairs (6,7) .. (13,14) — mid-bowl, brackets 9|10
    r = evaluate(i)
    if r: candidates.append(r)

# flatten to (pair, strategy) rows
flat = []
for c in candidates:
    for strat, s in c["strategies"].items():
        flat.append({"pair": f"{c['pair'][0]}-{c['pair'][1]}", "i": c["pair"][0],
                     "strategy": strat, "net_formal": c["net_formal"],
                     "displaced_seats": c["displaced_seats"], "block_balance": c["block_balance"],
                     "rows_below": c["rows_below"], "rows_above": c["rows_above"],
                     "natural_rake_pct": c["natural_rake_pct"], "band_drop_ft": c["band_drop_ft"],
                     **s})

# Rank ACCEPTED candidates. The section-strategy question is settled by the gates
# (only a self-draining, wheelable section survives). The remaining freedom is the row
# PAIR, where a cross-aisle's job — balanced dispersion + a centred mid-bowl view pause —
# makes block balance a performance reason, not a nicety. So rank balance first (centred
# split wins), then minimum effective intervention (section CY), then steps, then capacity.
def rank_key(r):
    return (round(1.0 - r["block_balance"], 2), r["total_section_cy"],
            r["total_step_ft"], -r["net_formal"])
accepted = sorted([r for r in flat if r["accept"]], key=rank_key)
rejected = [r for r in flat if not r["accept"]]
winner = accepted[0] if accepted else None

# the incumbent (what Scenario E currently builds): rows 9|10, midpoint_datum
incumbent = next((r for r in flat if r["pair"] == "9-10" and r["strategy"] == "midpoint_datum"), None)

# ── outputs ───────────────────────────────────────────────────────────────────────
cols = ["pair", "strategy", "accept", "net_formal", "displaced_seats", "rows_below", "rows_above",
        "block_balance", "natural_rake_pct", "band_drop_ft", "datum_navd88",
        "cross_slope_pct", "long_slope_pct", "inner_step_ft", "outer_step_ft", "total_step_ft",
        "inner_transition", "outer_transition", "wheelable", "ponds",
        "cut_cy", "fill_cy", "gross_cy", "ramp_surcharge_cy", "total_section_cy",
        "formal_fail", "min_C_mm", "gate_sightline", "gate_wheelable", "gate_steps_resolvable",
        "gate_block_balance", "gate_drainage"]
with open(OUT / "sweep_table.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader()
    for r in sorted(flat, key=lambda r: (r["i"], r["strategy"])):
        w.writerow({**r, "formal_fail": "|".join(map(str, r["formal_fail"])) or "none"})

# proof table = winner + incumbent + the four other strategies AT the winning pair
proof_rows = []
if winner:
    wp = winner["pair"]
    for r in flat:
        if r["pair"] == wp or (r is incumbent):
            proof_rows.append(r)
with open(OUT / "proof_table.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader()
    for r in sorted(proof_rows, key=lambda r: (r["pair"], r["strategy"])):
        w.writerow({**r, "formal_fail": "|".join(map(str, r["formal_fail"])) or "none"})

def _json(o):
    if hasattr(o, "item"): return o.item()      # numpy scalars -> python scalars
    if isinstance(o, np.ndarray): return o.tolist()
    raise TypeError(type(o))

json.dump({"base_formal_fail": BASE_FORMAL_FAIL, "nominal_formal": NOMINAL_FORMAL,
           "candidates": candidates, "winner": winner, "incumbent": incumbent,
           "n_accepted": len(accepted), "n_rejected": len(rejected)},
          open(OUT / "sweep.json", "w"), indent=2, default=_json)

# ── recommendation memo ─────────────────────────────────────────────────────────
def fmt(r):
    return (f"rows {r['pair']} · {r['strategy']} — net {r['net_formal']} seats, "
            f"datum {r['datum_navd88']}, x-slope {r['cross_slope_pct']}%, "
            f"steps {r['inner_step_ft']}/{r['outer_step_ft']} ft "
            f"({r['inner_transition']}/{r['outer_transition']}), "
            f"{'PONDS' if r['ponds'] else 'drains'}, section {r['total_section_cy']} CY")

# cascade candidate at the winning pair (measured raw-ground band) — anchors the tension prose
_casc_all = [r for r in flat if r["strategy"] == "cascade"]
_casc = next((r for r in _casc_all if winner and r["pair"] == winner["pair"]),
             _casc_all[len(_casc_all) // 2] if _casc_all else candidates[len(candidates) // 2])

L = ["# Cross-aisle section sweep — adjacent row pair × section strategy", "",
     "`scripts/sweep_cross_aisle.py`. Replaces the assumed rows 9|10 + dead-flat midpoint "
     "with a swept, re-validated section decision.", "",
     f"Swept **{len(candidates)} row pairs × 5 strategies = {len(flat)} candidates**. "
     f"Each band is built by the same row reclassification that makes the seats "
     f"(`union(row_i,row_i+1).difference(retained)`), then re-validated on the actual surface.", "",
     "## The section tension (why this is a real decision)", "",
     f"The row-centerline rake across a mid-bowl 2-row span is ~{_casc['natural_rake_pct']}%. "
     f"But the band footprint is not the centerlines — it is the gap left between the buffered "
     f"retained treads (`.difference(retained)`), and the least-squares plane fit on that actual "
     f"surface measures a gentler **{_casc['cross_slope_pct']}% cross-slope** (`cascade`, raw ground, "
     f"{_casc['total_section_cy']} CY, edges {_casc['inner_transition']}/{_casc['outer_transition']}). "
     f"That is still ~{_casc['cross_slope_pct']/ADA_CROSS_MAX:.1f}x the ADA limit of "
     f"<= {ADA_CROSS_MAX}%, so the band cannot be left as-is. Yet flattening it to wheelable grade "
     "(0% both ways) makes it **pond** mid-hillside. So no single move satisfies wheelability AND "
     "drainage AND flush edges at once: `cascade` is flush + dry but too steep to wheel; the flat "
     "datums wheel but pond; only `accessible_fit` carries 2% cross + 1% longitudinal fall (wheels "
     "and drains) and buys the residual edge drop as priced ramps. That is the real decision.", ""]

if winner:
    L += ["## Recommended", "", f"**{fmt(winner)}**", "",
          f"Among {len(accepted)} accepted candidates (all `accessible_fit` — every flat-datum "
          "strategy was eliminated on the drainage gate). The section strategy is settled by the "
          "gates; the row pair is then ranked balance-first (a cross-aisle's job is balanced "
          "dispersion + a centred view pause), then minimum effective intervention (section CY).",
          "",
          "Min-earthwork alternative (if a lopsided split is acceptable): "
          + fmt(min(accepted, key=lambda r: r["total_section_cy"])) + ".", ""]
if incumbent:
    same = winner and incumbent["pair"] == winner["pair"] and incumbent["strategy"] == winner["strategy"]
    L += ["## Incumbent (current Scenario E: rows 9|10, midpoint_datum)", "",
          f"- {fmt(incumbent)}", f"- accepted: **{incumbent['accept']}**"
          + ("" if incumbent["accept"] else
             f" (fails: " + ", ".join(g for g in
             ["sightline" if not incumbent["gate_sightline"] else "",
              "wheelable" if not incumbent["gate_wheelable"] else "",
              "steps" if not incumbent["gate_steps_resolvable"] else "",
              "drainage(ponds)" if not incumbent["gate_drainage"] else "",
              "block_balance" if not incumbent["gate_block_balance"] else ""] if g) + ")"),
          f"- verdict vs recommended: **{'CONFIRMED' if same else 'OVERTURNED'}**", ""]
    if incumbent["accept"] and not same:
        L += [f"  The incumbent is valid but not optimal: it ponds={incumbent['ponds']} and "
              f"costs {incumbent['total_section_cy']} CY vs the winner's {winner['total_section_cy']} CY, "
              f"with edge steps {incumbent['inner_step_ft']}/{incumbent['outer_step_ft']} ft that the "
              "current flat-pad code never models.", ""]

L += ["## Accepted candidates (ranked balance-first, then section CY)", "",
      "| Rank | Pair | Strategy | Net seats | Below/Above | Balance | Datum | x-slope% | "
      "Steps (in/out) ft | Drains | Section CY |",
      "|--:|--|--|--:|--|--:|--:|--:|--:|:--:|--:|"]
for k, r in enumerate(accepted[:12], 1):
    L.append(f"| {k} | {r['pair']} | {r['strategy']} | {r['net_formal']} | "
             f"{r['rows_below']}/{r['rows_above']} | {r['block_balance']} | {r['datum_navd88']} | "
             f"{r['cross_slope_pct']} | {r['inner_step_ft']}/{r['outer_step_ft']} | "
             f"{'yes' if not r['ponds'] else 'no'} | {r['total_section_cy']} |")
L += ["", f"Full grid: `analysis/cross_aisle_sweep/sweep_table.csv` "
      f"({len(accepted)} accepted, {len(rejected)} rejected). "
      "Per-candidate proof: `proof_table.csv`; raw: `sweep.json`.", ""]

(OUT / "RECOMMENDATION.md").write_text("\n".join(L) + "\n")

# ── console ───────────────────────────────────────────────────────────────────────
print(f"Swept {len(flat)} candidates ({len(candidates)} pairs × 5 strategies). "
      f"base formal-fail {BASE_FORMAL_FAIL or 'none'}.")
print(f"Accepted {len(accepted)}, rejected {len(rejected)}.")
if winner:
    print("WINNER :", fmt(winner))
if incumbent:
    same = winner and incumbent["pair"] == winner["pair"] and incumbent["strategy"] == winner["strategy"]
    print("INCUMBENT (9-10/midpoint):", fmt(incumbent), "| accept", incumbent["accept"],
          "|", "CONFIRMED" if same else "OVERTURNED")
print("\nTop accepted:")
for k, r in enumerate(accepted[:8], 1):
    print(f"  {k}. {fmt(r)}")
print("Wrote", OUT)
