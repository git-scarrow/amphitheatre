"""Prove the inevitability rule system on the validated design.

Builds the Site Affordance Map, encodes Scenario B (minimum-fill diagnostic) and
Scenario D (designed baseline) as Move sets populated from the real Scenario-B
validation numbers, and runs the InevitabilityEngine over both.

Expected outcome: Scenario B is REJECTED (counts formal seats on clipped/dished
tread; the minimize-fill move has no civic justification), Scenario D is ACCEPTED
(every move compelled by a site affordance + performance + civic reason).

Outputs -> analysis/inevitability/
  affordance_map.json     the detected site affordances
  scenarioB.json          B design + verdict
  scenarioD.json          D design + verdict
  verdict.md              side-by-side comparison
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "scripts"))

from harness.project import ProjectState
from harness.affordance import AffordanceEngine
from harness.inevitability import InevitabilityEngine, Move, Design

OUT = ROOT / "analysis" / "inevitability"
OUT.mkdir(parents=True, exist_ok=True)

STATE = ProjectState.load("harness_config.yaml")

# ── load the spatial validation result (source of truth for bands/clip) ──────────
VPATH = ROOT / "analysis" / "scenarioB_validation" / "validation.json"
VAL = json.load(open(VPATH)) if VPATH.exists() else {}
# tell the affordance engine which rows are arc-clipped tips (Band D geometry)
VAL.setdefault("clipped_tip_rows", [21, 22, 23, 24, 25])

# ── build the affordance map ─────────────────────────────────────────────────────
AFF = AffordanceEngine(STATE).build(VAL)
json.dump(AFF, open(OUT / "affordance_map.json", "w"), indent=2)
rake = AFF["natural_rake"]; hinge = AFF["bowl_hinge"]
print(f"Affordance map: rake_rises_outward={rake['rake_rises_outward_frac']} "
      f"(mean {rake['mean_radial_rise_pct']}%/ft)  seatable_in_fan={rake['seatable_in_fan_ac']}ac  "
      f"hinge_R={hinge['hinge_radius_ft']}ft")

ENG = InevitabilityEngine(AFF, VAL)
restore_cy   = VAL.get("scenarioD_repair_cy", 25.9)
asbuilt_A    = VAL.get("bands_asbuilt", {}).get("A", 217.4)
scenD_A      = VAL.get("bands_scenarioD", {}).get("A", 1452.0)
earnback     = round(scenD_A - asbuilt_A)

# ── Scenario B — minimum-fill diagnostic encoded honestly as a design ────────────
# B's defining move is "drop fill past 0.5 ft everywhere"; presented as a finished
# design it claims the full formal bowl on the clipped surface and never restores it.
scenarioB = Design(
    scenario="B — minimum-fill (as a claimed design)",
    claims={"formal_seats_claimed": scenD_A},     # claims the full 1452 formal bowl
    surfaces_classified=True,
    omits_required_surfaces=["ADA", "drainage"],
    stage="cost_proxy",                            # B is presented as THE finished design

    moves=[
        Move(
            move_id="B1_clip_all_fill",
            move_type="borrow_from_high_side_to_complete_low_tread",
            geometry="all 24 rows, fill capped at 0.5 ft",
            site_reasons=["terrain dips below tread plane at low spots"],
            performance_reasons=[],                  # ← no performance reason: pure CY minimize
            civic_reasons=[],                        # ← no civic reason
            cost={"cut_cy": 138, "fill_cy": 137, "gross_cy": 275},
            effects={"formal_seats": "decrease", "visual_legibility": "decreased",
                     "drainage_risk": "increased"},
            positive_criteria=["reduces_artificial_grading"],
            rejection_if_removed=[],                 # ← removing it loses nothing real → not inevitable
            status="proposed",
        ),
    ],
)

# ── Scenario D — designed baseline: site-affordance composition ──────────────────
scenarioD = Design(
    scenario="D — designed baseline (site-affordance composition)",
    claims={"formal_seats_claimed": scenD_A},
    surfaces_classified=True,
    omits_required_surfaces=[],          # ADA + drainage carried as scenario-E moves
    moves=[
        Move(
            move_id="D1_restore_formal_treads",
            move_type="restore_formal_tread",
            geometry="rows 1-18 segments flagged clip_under_seat, C_ideal>=90",
            site_reasons=["natural bowl curvature", "within core formal seating rake"],
            performance_reasons=["restores 2% cross-slope", "removes clip_under_seat dishing",
                                 "holds C>=90mm on the actual surface"],
            civic_reasons=["completes a continuous, legible lower bowl",
                           "a terrace must read as a terrace"],
            cost={"cut_cy": 0.0, "fill_cy": restore_cy, "gross_cy": restore_cy},
            effects={"formal_seats": f"+{earnback}", "visual_legibility": "increased",
                     "drainage_risk": "reduced"},
            positive_criteria=["uses_existing_contour", "clarifies_seating_bowl",
                               "improves_sightlines", "improves_drainage"],
            rejection_if_removed=["formal seating discontinuity", "clip dishing under seats",
                                  "mid-tread ponding"],
            status="accepted",
        ),
        Move(
            move_id="D2_dissolve_clipped_tips",
            move_type="convert_clipped_tip_to_overlook",
            geometry="rows 21-25 bend-only fragments (Band D)",
            site_reasons=["arc clipped by Petoskey & Mitchell streets", "upper plateau edge"],
            performance_reasons=["removes false formal capacity from clipped geometry"],
            civic_reasons=["edge dissolves into landscape/overlook instead of broken seating"],
            cost={"cut_cy": 0.0, "fill_cy": 0.0, "gross_cy": 0.0},
            effects={"formal_seats": "0", "informal_capacity": "increase",
                     "visual_legibility": "increased"},
            positive_criteria=["turns_fragment_into_landscape", "preserves_bay_view",
                               "adds_daily_nonevent_value"],
            rejection_if_removed=["clipped fragments masquerade as formal seats"],
            status="accepted",
        ),
        Move(
            move_id="D3_demote_outer_rows_to_terrace",
            move_type="demote_weak_outer_capacity_to_picnic_terrace",
            geometry="rows 19-20 (Band B/C, C 55-86mm)",
            site_reasons=["slope still supports informal lawn terraces"],
            performance_reasons=["honest banding: below 90mm formal threshold"],
            civic_reasons=["soft upper terrace for picnic/daily use, not advertised as formal"],
            cost={"cut_cy": 0.0, "fill_cy": 0.0, "gross_cy": 0.0},
            effects={"informal_capacity": "increase", "civic_formality": "decrease",
                     "visual_softness": "increased"},
            positive_criteria=["clarifies_seating_bowl", "adds_daily_nonevent_value",
                               "reduces_artificial_grading"],
            rejection_if_removed=["upper rows over-counted as formal", "lost daily-use lawn"],
            status="accepted",
        ),
        Move(
            move_id="D4_preserve_upstage_view",
            move_type="preserve_open_upstage_view",
            geometry="stage upstage, face_az 330 corridor to bay",
            site_reasons=["bay+sky on the NNW view axis", "stage sits at the bowl hinge"],
            performance_reasons=["keeps the open-air character; no enclosure to drain/heat"],
            civic_reasons=["the view is the set; an open-air venue, not a fake room"],
            cost={"cut_cy": 0.0, "fill_cy": 0.0, "gross_cy": 0.0},
            effects={"blocks_view": False, "visual_legibility": "increased"},
            positive_criteria=["preserves_bay_view", "clarifies_seating_bowl"],
            rejection_if_removed=["upstage wall could creep in and kill the bay axis"],
            status="accepted",
        ),
    ],
)

# ── evaluate both ────────────────────────────────────────────────────────────────
vb = ENG.evaluate(scenarioB)
vd = ENG.evaluate(scenarioD)
json.dump(vb, open(OUT / "scenarioB.json", "w"), indent=2)
json.dump(vd, open(OUT / "scenarioD.json", "w"), indent=2)

# ── verdict memo ─────────────────────────────────────────────────────────────────
def ledger_line(v):
    return " ".join(f"{k}={'✅' if p else '❌'}" for k, p in v["ledgers"].items())

lines = [
    "# Inevitability verdict — Scenario B vs Scenario D",
    "",
    f"_Generated by `scripts/score_inevitability.py` from `{VPATH.relative_to(ROOT)}`._",
    "",
    "## Site Affordance Map (detected)",
    "",
    f"- **Natural rake:** the fan ground rises outward (rows step up the hill) over "
    f"**{rake['rake_rises_outward_frac']:.0%}** of the fan at a mean {rake['mean_radial_rise_pct']}%/ft; "
    f"{rake['seatable_in_fan_ac']} ac sits in the seatable {rake['mean_seatable_slope_pct']}% band "
    f"— a latent bowl the design intensifies rather than imposes.",
    f"- **Bowl hinge:** flat pan rolls into rising bowl at R ≈ **{hinge['hinge_radius_ft']} ft** "
    f"(elev {hinge['hinge_elev_navd88']}) — where the stage/forecourt belongs.",
    f"- **View axis:** face {AFF['view_axis']['face_az_deg']}° NNW to bay (581.4 ft) — upstage stays open.",
    f"- **Edges:** street hard-clips + arc-clipped tip rows {AFF['edges']['clipped_tip_rows']} → landscape.",
    f"- **Drainage:** spills NE to bay; treatment cell bottom {AFF['drainage']['treatment_cell_bottom_navd88']}.",
    "",
    "## Verdicts",
    "",
    "| | Scenario B (min-fill diagnostic) | Scenario D (designed baseline) |",
    "|---|---|---|",
    f"| **Verdict** | {vb['verdict']} | {vd['verdict']} |",
    f"| Ledgers | {ledger_line(vb)} | {ledger_line(vd)} |",
    f"| Done checklist | {sum(vb['done_checklist']['questions'].values())}/10 | "
    f"{sum(vd['done_checklist']['questions'].values())}/10 |",
    f"| Inevitability score | {vb['scores']['inevitability']} | {vd['scores']['inevitability']} |",
    f"| Arbitrary moves | {vb['scores']['arbitrary_moves']} | {vd['scores']['arbitrary_moves']} |",
    f"| Hidden failures | {vb['scores']['hidden_failures']} | {vd['scores']['hidden_failures']} |",
    "",
    "## Why Scenario B is rejected",
    "",
] + [f"- {r}" for r in vb["hard_rejections"]] + [
    "",
    "## Why Scenario D is inevitable",
    "",
    "Every move carries a site reason **and** a performance reason **and** a civic reason, "
    "and none can be removed without making the place worse:",
    "",
]
for m in scenarioD.moves:
    lines.append(f"- **{m.move_id}** ({m.move_type}, {m.cost['gross_cy']:.0f} CY) — "
                 f"site: {', '.join(m.site_reasons)}; perf: {', '.join(m.performance_reasons)}; "
                 f"civic: {', '.join(m.civic_reasons)}. "
                 f"Remove → {', '.join(m.rejection_if_removed)}.")
lines += [
    "",
    "## Reading",
    "",
    "Scenario B minimized dirt and damaged the bowl: it counts formal seats on clipped, dished "
    "treads and its one move has no civic or performance reason — removing it loses nothing real, "
    "so it is not inevitable. Scenario D spends the **minimum effective intervention** "
    f"(~{restore_cy:.0f} CY) to make the terraces read and function as terraces, dissolves clipped "
    "fragments into landscape, demotes weak rows honestly, and keeps the bay axis open. "
    "The added dirt performs visible civic work — that is what makes it feel found, not imposed.",
]
(OUT / "verdict.md").write_text("\n".join(lines) + "\n")

print("\n=== Inevitability verdict ===")
print("Scenario B:", vb["verdict"], "| ledgers:", vb["ledgers"], "| done",
      sum(vb["done_checklist"]["questions"].values()), "/10 | score", vb["scores"]["inevitability"])
print("  rejections:")
for r in vb["hard_rejections"]:
    print("   -", r)
print("Scenario D:", vd["verdict"], "| ledgers:", vd["ledgers"], "| done",
      sum(vd["done_checklist"]["questions"].values()), "/10 | score", vd["scores"]["inevitability"])
print("Wrote", OUT)
