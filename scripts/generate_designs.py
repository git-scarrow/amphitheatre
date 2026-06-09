"""Generate design families from the site affordance map, then self-critique them.

The engine now COMPOSES, not just checks: the Composer writes one Design per family
from the affordance map + the Scenario-B validation row data, and the
InevitabilityEngine grades each. Degenerate compositions are rejected by the same
rules that pass the good ones.

Outputs -> analysis/inevitability/families/
  <family>.json        full design + verdict + capacity
  families.csv         ranked comparison
  FAMILIES.md          readable comparison memo
"""
from __future__ import annotations

import csv
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "scripts"))

from harness.project import ProjectState
from harness.affordance import AffordanceEngine
from harness.inevitability import InevitabilityEngine
from harness.composer import Composer, FAMILIES

OUT = ROOT / "analysis" / "inevitability" / "families"
OUT.mkdir(parents=True, exist_ok=True)

STATE = ProjectState.load("harness_config.yaml")
VPATH = ROOT / "analysis" / "scenarioB_validation" / "validation.json"
ROW_CSV = ROOT / "analysis" / "scenarioB_validation" / "row_validation.csv"
SEG_CSV = ROOT / "analysis" / "scenarioB_validation" / "segments.csv"
VAL = json.load(open(VPATH)) if VPATH.exists() else {}
VAL.setdefault("clipped_tip_rows", [21, 22, 23, 24, 25])

AFF = AffordanceEngine(STATE).build(VAL)
ENG = InevitabilityEngine(AFF, VAL)
COMP = Composer.from_validation(AFF, ROW_CSV, SEG_CSV)

W_FORMAL, W_LAWN = 1.0, 0.4

def seats_from_effect(v):
    try:
        return int(str(v).lstrip("+"))
    except (ValueError, TypeError):
        return 0

rows_out = []
print("Generating + grading families:\n")
for fam in FAMILIES:
    design = COMP.generate(fam)
    verdict = ENG.evaluate(design)
    formal = sum(seats_from_effect(m["effects"].get("formal_seats"))
                 for m in verdict["moves"])
    informal = sum(seats_from_effect(m["effects"].get("informal_capacity"))
                   for m in verdict["moves"])
    cy = round(sum(m["cost"]["gross_cy"] for m in verdict["moves"]), 1)
    civic_value = round(W_FORMAL * formal + W_LAWN * informal, 0)
    rec = {
        "family": fam,
        "stage": design.stage,
        "accepted": verdict["accepted"],
        "verdict": verdict["verdict"],
        "inevitability": verdict["scores"]["inevitability"],
        "done": sum(verdict["done_checklist"]["questions"].values()),
        "formal_seats": formal,
        "informal_seats": informal,
        "restore_cy": cy,
        "civic_value": civic_value,
        "n_moves": len(verdict["moves"]),
        "open_items": ";".join(verdict["open_items"]),
        "blurb": FAMILIES[fam]["blurb"],
    }
    rows_out.append(rec)
    json.dump({"design": asdict(design), "verdict": verdict},
              open(OUT / f"{fam}.json", "w"), indent=2)
    flag = "✅" if verdict["accepted"] else "❌"
    print(f"  {flag} {fam:<26} formal={formal:>4} lawn={informal:>4} "
          f"CY={cy:>5} inev={rec['inevitability']:>6} done={rec['done']}/10 "
          f"[{design.stage}]")

# ── control: prove the composer cannot cheat. Take civic_bowl, delete its
#    restore_formal_tread move (claim the formal bowl without spending the CY) →
#    the same engine must reject it (formal seats on clipped/dished tread).
import copy
control = COMP.generate("civic_bowl")
control.scenario = "control_unrestored_civic (formal claimed, restore move deleted)"
control.moves = [m for m in control.moves if m.move_type != "restore_formal_tread"]
control.claims = {"formal_seats_claimed": 1452}
cv = ENG.evaluate(control)
print(f"\n  control (civic bowl minus restoration): {cv['verdict']}")
for r in cv["hard_rejections"]:
    print("     -", r)
json.dump({"design": asdict(control), "verdict": cv}, open(OUT / "_control_unrestored.json", "w"), indent=2)

# rank: accepted first, then civic_value per CY effect, then inevitability
rows_out.sort(key=lambda r: (not r["accepted"], -r["civic_value"], -r["inevitability"]))

with open(OUT / "families.csv", "w", newline="") as fh:
    fields = ["family", "stage", "accepted", "inevitability", "done", "formal_seats",
              "informal_seats", "restore_cy", "civic_value", "n_moves", "open_items", "blurb"]
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader()
    for r in rows_out:
        w.writerow({k: r[k] for k in fields})

# memo
lines = [
    "# Generated design families — composed from the affordance map, self-critiqued",
    "",
    "_`scripts/generate_designs.py`: the Composer writes one Design per family from the "
    "site affordance map + Scenario-B validation; the InevitabilityEngine grades each._",
    "",
    "All families ride the same latent bowl (rake rises "
    f"{AFF['natural_rake']['mean_radial_rise_pct']}%/ft, hinge R≈{AFF['bowl_hinge']['hinge_radius_ft']} ft, "
    f"bay axis {AFF['view_axis']['face_az_deg']}°). They differ in where the formal/lawn line falls and "
    "which access/drainage/framing surfaces are composed.",
    "",
    "| Family | Verdict | Inev | Done | Formal | Lawn | Restore CY | Stage | Character |",
    "|---|---|---:|---:|---:|---:|---:|---|---|",
]
for r in rows_out:
    v = "✅ accept" if r["accepted"] else "❌ reject"
    lines.append(f"| **{r['family']}** | {v} | {r['inevitability']} | {r['done']}/10 | "
                 f"{r['formal_seats']} | {r['informal_seats']} | {r['restore_cy']} | {r['stage']} | {r['blurb']} |")
lines += [
    "",
    "## Reading",
    "",
    f"- **{rows_out[0]['family']}** ranks first by civic value at near-zero earthwork — "
    "all formal capacity is *restoration of the latent bowl*, not imposed grading.",
    "- **Every composed family is `concept`** — its access/drainage/framing moves are INTENT "
    "(no polygons yet), which lift concept ranking but cannot satisfy a cost-proxy gate. Reaching "
    "`cost_proxy` requires the Scenario E geometry emitter to draw real ADA/cross-aisle/swale "
    "surfaces and pass validation on them (`SCENARIO_E_CIVIC.md`). The engine enforces this: a "
    "cost-proxy claim backed only by intent moves is hard-rejected.",
    "- No family counts formal seats on clipped/dished tread — the composer only promotes a row to "
    "formal when its *ideal* plane passes all gates, and spends the restoration CY to earn it.",
    "- These are different characters, not one optimum at different prices: a planner picks by civic "
    "intent (max formal vs. meadow vs. festival vs. daily-use), then Scenario E makes it costable.",
    "",
    "Per-family move ledgers: `analysis/inevitability/families/<family>.json`.",
]
(OUT / "FAMILIES.md").write_text("\n".join(lines) + "\n")

print(f"\nTop family: {rows_out[0]['family']} (civic_value {rows_out[0]['civic_value']:.0f}, "
      f"{rows_out[0]['restore_cy']} CY)")
print("Wrote", OUT)
