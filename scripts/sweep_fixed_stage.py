"""Fixed-stage Pareto sweep over G, theta, R, N within the feasible domain Omega.

Deterministic driver over the existing harness engines (no LLM). Stage S is held
fixed (focus elev, eye height, stage radial offset, stage size). We sweep:

  axis      face azimuth in {330,325,320,315,305}  (bowl rotated about arc centre F)
  fan       FAN_HALF (half fan angle)              -> theta
  nrows     NROWS                                  -> N
  tread     row spacing (ft)                       -> R (spacing)
  R_inner   first-row radius (held; stage-coupled) -> R (radii), noted, not swept
  G         borrow/fill circuits: G=0 (natural rake) + saved variant deltas

DOCTRINE (this project's documented failure mode):
  - The DEM is the sole source of truth for existing grade.
  - There is no retaining wall on site and none is desired. A wall is NEVER an
    input zone. A wall *requirement* emerges only from measured cut/fill depth:
    here, max per-row implied tread fill > 3 ft (G=0) or actual max_cut/max_fill
    > 3 ft (earthwork circuits), via the harness wall_trigger. Existing steep
    ground is not a wall trigger.

Ranking axes (Pareto, not a single winner):
  useful_capacity, sightlines, ADA plausibility, earthwork, drainage risk,
  view quality, constructability.

Outputs:
  sweep_fixed_stage/results.csv   every candidate, all columns
  sweep_fixed_stage/pareto.md     feasible Pareto frontier + criteria table
"""
from __future__ import annotations

import copy
import csv
import math
from itertools import product
from pathlib import Path

import sys
sys.path.insert(0, "scripts")

from harness.project import ProjectState
from harness.clay import ClayDelta
from harness.evaluators import EvaluatorSuite
from harness.scoring import MultiObjectiveScorer

ROOT = Path(".")
OUT = ROOT / "sweep_fixed_stage"
OUT.mkdir(exist_ok=True)

# --- sweep grid -------------------------------------------------------------
AXES = [330, 325, 320, 315, 305]
FAN_HALVES = [45, 50, 55, 60, 65]          # theta: fan 90..130 deg
NROWS = [12, 16, 20, 24, 28]               # N (28 rows @ tread 3 -> R_outer 166 ft)
TREADS = [2.5, 3.0, 3.5, 4.0]              # row spacing (ft)
R_INNER = 85.0                             # held fixed (stage-coupled); noted

# --- emergent (not pre-named) thresholds ------------------------------------
WALL_FILL_FT = 3.0      # measured implied/actual fill above which a wall would be needed
RAKE_STRESS_FT = 1.5    # measured fill above which the natural seating rake is stressed
ADA_MAX_PCT = 8.33

SEAT_W_C = 1.50
AISLE = 0.18

scorer = MultiObjectiveScorer()


def seats_in_row(R: float, fan_half: float) -> int:
    return max(0, int(R * math.radians(2 * fan_half) * (1 - AISLE) // SEAT_W_C))


def derive_criteria(m: dict, score: dict, hc: dict) -> dict:
    """Collapse raw metrics into the 7 ranking axes + feasibility, with the
    wall/constructability signal emerging from measured per-row cut-fill."""
    sl = m["sightlines"]
    rows = m["sightline_rows"]
    fan_half = m["_fan_half"]
    ew = m["earthwork"]
    ada = m["ada"]
    dr = m["drainage"]
    sun = m["solar"]
    aes = m["aesthetic"]

    # useful capacity = seats only in rows that actually meet the 90 mm C-value
    raw_cap = sum(seats_in_row(r["R"], fan_half) for r in rows)
    useful_cap = sum(seats_in_row(r["R"], fan_half) for r in rows if r["meets_C"])

    # measured implied tread fill (the grade change the geometry *requires*)
    max_row_fill = max((r["cut_fill_ft"] for r in rows), default=0.0)
    implied_fill_cy = sl.get("total_fill_cy", 0.0)
    n_rake_stress = sum(1 for r in rows if r["cut_fill_ft"] > RAKE_STRESS_FT)

    # actual earthwork (G circuits); ~0 for natural-rake G=0
    gross_cy = ew.get("gross_cy", 0.0)
    act_max_cut = ew.get("max_cut_ft", 0.0)
    act_max_fill = ew.get("max_fill_ft", 0.0)
    disturbance_cy = max(gross_cy, 0.0) + implied_fill_cy

    # WALL: emerges only from measured cut/fill depth, never a named zone
    wall_emergent = (
        max_row_fill > WALL_FILL_FT
        or act_max_cut > WALL_FILL_FT
        or act_max_fill > WALL_FILL_FT
        or bool(ew.get("wall_trigger", False))
    )
    worst_fill = max(max_row_fill, act_max_fill, act_max_cut)
    constructability = round(max(0.0, 1.0 - worst_fill / WALL_FILL_FT), 3)

    # ADA plausibility (authored schematic routes -> constant; reported, flagged)
    ada_max = ada.get("max_running_slope_pct", 0.0)
    ada_plaus = round(min(1.0, ADA_MAX_PCT / ada_max) if ada_max > 0 else 1.0, 3)

    # drainage risk (0 = none); storage loss + freeboard shortfall
    stor_chg = dr.get("storage_100yr_change_pct", 0.0)
    fb = dr.get("event_floor_freeboard_ft", 1.2)
    drainage_risk = round(max(0.0, -stor_chg) / 10.0 + (0.0 if fb >= 1.0 else 1.0), 3)

    # view quality: bay openness + sunset crescent + glare
    bay = aes.get("bay_view_score", 0.0)
    sunset = sun.get("upper_crescent_score", 0.0)
    glare = {"low": 1.0, "medium": 0.5, "high": 0.0}.get(sun.get("glare_penalty", "low"), 1.0)
    view_q = round(0.5 * bay + 0.3 * sunset + 0.2 * glare, 3)

    # feasibility Omega (hard gates; wall gate is the emergent one)
    failures = list(hc.get("failures", []))
    if wall_emergent and not any("wall" in f for f in failures):
        failures.append(f"emergent_wall: measured fill {worst_fill:.2f} ft > {WALL_FILL_FT} ft")
    feasible = (
        sl.get("all_pass", True)
        and dr.get("cell_function_preserved", True)
        and ada.get("delta") != "worsened"
        and bay >= 0.30
        and not wall_emergent
        and m.get("_balanced", True)
    )

    return {
        "useful_cap": useful_cap,
        "raw_cap": raw_cap,
        "min_C_mm": sl.get("min_C_mm"),
        "sl_pass": f"{sl.get('pass_count',0)}/{sl.get('pass_count',0)+sl.get('fail_count',0)}",
        "implied_fill_cy": round(implied_fill_cy, 1),
        "max_row_fill_ft": round(max_row_fill, 2),
        "rake_stress_rows": n_rake_stress,
        "gross_cy": round(gross_cy, 1),
        "disturbance_cy": round(disturbance_cy, 1),
        "ada_max_pct": round(ada_max, 1),
        "ada_plaus": ada_plaus,
        "drainage_risk": drainage_risk,
        "freeboard_ft": fb,
        "bay_view": bay,
        "sunset": sunset,
        "view_q": view_q,
        "wall_emergent": wall_emergent,
        "constructability": constructability,
        "landform_fit": aes.get("landform_fit", 0.0),
        "U_score": score.get("total", 0.0),
        "feasible": feasible,
        "fail": "; ".join(failures) if failures else "",
    }


def run_geometry(state, base_params, axis, fan_half, nrows, tread):
    p = copy.deepcopy(base_params)
    p["FACE_AZ"] = float(axis)
    p["AX_AZ"] = float((axis - 180) % 360)
    p["FAN_HALF"] = float(fan_half)
    p["NROWS"] = int(nrows)
    p["TREAD"] = float(tread)
    p["R_INNER"] = float(R_INNER)
    p["R_OUTER"] = float(R_INNER + (nrows - 1) * tread)
    state.ctx["params"] = p

    ev = EvaluatorSuite(state)
    delta = ClayDelta.zeros(state)
    m = ev.run_all(delta, bowl_axis_az=float(axis))
    m["_fan_half"] = fan_half
    m["_balanced"] = True  # G=0
    hc = ev.hard_constraints(m)
    sc = scorer.score(m)
    return m, sc, hc


def run_circuit(state, base_params, vid, delta_path, axis):
    """Evaluate a saved borrow/fill circuit (variant delta) at baseline geometry."""
    p = copy.deepcopy(base_params)  # baseline geometry, fixed stage
    state.ctx["params"] = p
    ev = EvaluatorSuite(state)
    delta = ClayDelta.load(delta_path, state)
    m = ev.run_all(delta, bowl_axis_az=float(axis))
    m["_fan_half"] = p["FAN_HALF"]
    yb = m["earthwork"].get("yield_balance", {}).get("neutral", {})
    m["_balanced"] = yb.get("balanced", True)
    nt = ev.no_touch_violations(delta)
    hc = ev.hard_constraints(m)
    if nt:
        hc["failures"] = hc.get("failures", []) + [f"no_touch: {', '.join(nt)}"]
    sc = scorer.score(m)
    return m, sc, hc


def main():
    state = ProjectState.load("harness_config.yaml")
    base_params = copy.deepcopy(state.ctx["params"])  # pristine baseline

    records = []

    # --- Stage A: geometry sweep at G=0 -----------------------------------
    n = 0
    for axis, fh, nr, tr in product(AXES, FAN_HALVES, NROWS, TREADS):
        m, sc, hc = run_geometry(state, base_params, axis, fh, nr, tr)
        crit = derive_criteria(m, sc, hc)
        rec = {"kind": "geom", "id": f"G-a{axis}-f{fh}-n{nr}-t{tr}",
               "axis": axis, "fan_half": fh, "nrows": nr, "tread": tr, "G": "0",
               **crit}
        records.append(rec)
        n += 1
    print(f"Stage A: {n} geometry candidates @ G=0")

    # --- Stage B: borrow/fill circuits (saved variant deltas) -------------
    import yaml
    vdir = ROOT / "variants"
    nb = 0
    if vdir.exists():
        for vp in sorted(vdir.glob("V*/delta.tif")):
            vid = vp.parent.name
            prop_p = vp.parent / "proposal.yaml"
            axis = 330
            intent = ""
            if prop_p.exists():
                try:
                    pr = yaml.safe_load(open(prop_p))
                    pr = pr.get("proposal", pr)
                    axis = pr.get("bowl_axis_az", 330)
                    intent = (pr.get("intent", "") or "")[:48]
                except Exception:
                    pass
            try:
                m, sc, hc = run_circuit(state, base_params, vid, vp, axis)
            except Exception as e:
                print(f"  {vid}: circuit eval failed: {e}")
                continue
            crit = derive_criteria(m, sc, hc)
            rec = {"kind": "circuit", "id": vid,
                   "axis": axis, "fan_half": base_params["FAN_HALF"],
                   "nrows": base_params["NROWS"], "tread": base_params["TREAD"],
                   "G": intent or vid, **crit}
            records.append(rec)
            nb += 1
    print(f"Stage B: {nb} borrow/fill circuit candidates")

    # --- write full CSV ---------------------------------------------------
    cols = ["kind", "id", "axis", "fan_half", "nrows", "tread", "G",
            "useful_cap", "raw_cap", "min_C_mm", "sl_pass",
            "ada_max_pct", "ada_plaus",
            "gross_cy", "implied_fill_cy", "max_row_fill_ft", "rake_stress_rows",
            "disturbance_cy", "wall_emergent", "constructability",
            "drainage_risk", "freeboard_ft", "bay_view", "sunset", "view_q",
            "landform_fit", "U_score", "feasible", "fail"]
    with open(OUT / "results.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in records:
            w.writerow({c: r.get(c, "") for c in cols})
    print(f"Wrote {OUT/'results.csv'} ({len(records)} rows)")

    # --- Pareto on feasible set ------------------------------------------
    feas = [r for r in records if r["feasible"]]
    print(f"Feasible (in Omega): {len(feas)}/{len(records)}")

    # objective vector (all maximize): useful_cap, min_C, ada_plaus,
    # -disturbance, -drainage_risk, view_q, constructability
    def objvec(r):
        return (
            r["useful_cap"],
            r["min_C_mm"] or 0,
            r["ada_plaus"],
            -r["disturbance_cy"],
            -r["drainage_risk"],
            r["view_q"],
            r["constructability"],
        )

    def dominates(a, b):
        va, vb = objvec(a), objvec(b)
        return all(x >= y for x, y in zip(va, vb)) and any(x > y for x, y in zip(va, vb))

    pareto = [r for r in feas if not any(dominates(o, r) for o in feas if o is not r)]
    for r in records:
        r["pareto"] = r in pareto

    # headline 2-axis frontier: useful_cap (max) vs disturbance_cy (min)
    def front_2d(rows):
        s = sorted(rows, key=lambda r: (-r["useful_cap"], r["disturbance_cy"]))
        out, best = [], float("inf")
        for r in s:
            if r["disturbance_cy"] < best:
                out.append(r); best = r["disturbance_cy"]
        return out
    front2 = front_2d(feas)

    # --- markdown report --------------------------------------------------
    def fmt_table(rows, title):
        L = [f"### {title}", "",
             "| id | axis | fan | N | tread | useful_cap | minC | ADA% | "
             "disturb_cy | wall | constr | drain_risk | view_q | landform | U |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            L.append(
                f"| {r['id']} | {r['axis']} | {r['fan_half']} | {r['nrows']} | "
                f"{r['tread']} | {r['useful_cap']} | {r['min_C_mm']} | {r['ada_max_pct']} | "
                f"{r['disturbance_cy']} | {'Y' if r['wall_emergent'] else '-'} | "
                f"{r['constructability']} | {r['drainage_risk']} | {r['view_q']} | "
                f"{r['landform_fit']} | {r['U_score']} |")
        return "\n".join(L)

    md = ["# Fixed-stage Pareto sweep — results", "",
          f"- Stage S fixed (focus {base_params['FOCUS_ELEV']} ft, eye {base_params['EYE_HT']} ft, "
          f"stage_r {base_params['STAGE_R']} ft, R_inner {R_INNER} ft held).",
          f"- Candidates: {len(records)} ({n} geometry @ G=0, {nb} borrow/fill circuits).",
          f"- Feasible in Omega: {len(feas)}.  Pareto-non-dominated (7-axis): {len(pareto)}.",
          "- Wall flag is EMERGENT from measured per-row cut/fill (>3 ft), not a named zone.",
          "- ADA routes are authored schematics (≈53% constant) — see §10 gaps; ADA cannot",
          "  discriminate at G=0 and is reported, not used to reject.",
          "",
          fmt_table(sorted(front2, key=lambda r: -r["useful_cap"]),
                    "Headline frontier — useful capacity ↑ vs disturbance ↓ (feasible)"),
          "",
          fmt_table(sorted(pareto, key=lambda r: -r["U_score"])[:40],
                    "7-axis Pareto-non-dominated set (top 40 by U)"),
          ""]
    (OUT / "pareto.md").write_text("\n".join(md) + "\n")
    print(f"Wrote {OUT/'pareto.md'}")

    # console summary
    print("\n=== HEADLINE FRONTIER (useful_cap vs disturbance, feasible) ===")
    print(f"{'id':<22}{'axis':>5}{'fan':>4}{'N':>4}{'tr':>5}{'use_cap':>8}"
          f"{'minC':>6}{'disturb':>9}{'wall':>5}{'constr':>7}{'view':>6}{'U':>7}")
    for r in sorted(front2, key=lambda r: -r["useful_cap"]):
        print(f"{r['id']:<22}{r['axis']:>5}{r['fan_half']:>4}{r['nrows']:>4}{r['tread']:>5}"
              f"{r['useful_cap']:>8}{r['min_C_mm']:>6}{r['disturbance_cy']:>9}"
              f"{'Y' if r['wall_emergent'] else '-':>5}{r['constructability']:>7}"
              f"{r['view_q']:>6}{r['U_score']:>7}")

    # axis effect at baseline geometry (fan55,n16,tread3)
    print("\n=== AXIS EFFECT @ baseline geom (fan55 n16 t3.0), G=0 ===")
    print(f"{'axis':>5}{'view_q':>8}{'bay':>6}{'sunset':>8}{'U':>7}{'feasible':>9}")
    for r in records:
        if r["kind"] == "geom" and r["fan_half"] == 55 and r["nrows"] == 16 and r["tread"] == 3.0:
            print(f"{r['axis']:>5}{r['view_q']:>8}{r['bay_view']:>6}{r['sunset']:>8}"
                  f"{r['U_score']:>7}{str(r['feasible']):>9}")

    print("\n=== CIRCUITS (Stage B) ===")
    print(f"{'id':<8}{'axis':>5}{'gross_cy':>9}{'maxfill':>8}{'wall':>5}"
          f"{'drain_risk':>11}{'U':>7}{'feasible':>9}")
    for r in records:
        if r["kind"] == "circuit":
            print(f"{r['id']:<8}{r['axis']:>5}{r['gross_cy']:>9}{r['max_row_fill_ft']:>8}"
                  f"{'Y' if r['wall_emergent'] else '-':>5}{r['drainage_risk']:>11}"
                  f"{r['U_score']:>7}{str(r['feasible']):>9}")


if __name__ == "__main__":
    main()
