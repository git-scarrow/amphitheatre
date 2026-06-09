"""AgentLoop: LLM harness orchestrator.

Usage:
  # Run the full agent loop for a variant family:
  python -m scripts.harness.agent --family A --n 5

  # Apply and evaluate a single YAML proposal:
  python -m scripts.harness.agent --apply proposal.yaml

  # Print baseline metrics:
  python -m scripts.harness.agent --baseline

  # Compare all saved variants:
  python -m scripts.harness.agent --compare

The LLM is called via `claude -p "<prompt>"`. ANTHROPIC_API_KEY must be set.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import yaml

# We run from the project root, so add scripts/ to path for harness imports
_HERE = Path(__file__).parent.parent  # scripts/
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from harness.project import ProjectState
from harness.clay import ClayDelta
from harness.evaluators import EvaluatorSuite
from harness.scoring import MultiObjectiveScorer
from harness.scenarios import ScenarioLibrary
from harness.variants import VariantManager


CONFIG_PATH = "harness_config.yaml"

SYSTEM_PROMPT = textwrap.dedent("""
You are the design agent for the Petoskey Pit open-air amphitheatre project.
Your job is to propose bounded terrain-modification actions (clay moves) that
improve the design without violating hard constraints.

## Harness doctrine (always enforce)
1. Do not move the LiDAR ground — only add a proposed clay delta.
2. Do not fill without identifying a borrow source.
3. Do not optimize sunset by rotating the whole amphitheater to 305°.
4. Do not damage the natural seating rake unless the gain is explicit and measured.
5. Do not erase the treatment cell without replacing drainage function.
6. Do not treat the amphitheater as an enclosed room.
7. Do not reward symmetry when the landform wants asymmetry.
8. Do not score capacity above sightlines, ADA, drainage, or earthwork sanity.
9. Reward moves that solve multiple problems with one earthwork gesture.
10. Save every variant with visible fingerprints.

## Available polygon names (from earthwork_scenarios.geojson)
{polygon_names}

## Proposal format (respond ONLY with valid YAML inside ```yaml fences):
```yaml
proposal:
  id: V{next_id}
  family: {family}
  intent: <one sentence describing the move>
  bowl_axis_az: {axis_az}   # degrees (330, 325, 320, 315, 305)
  borrow_only_ok: false
  actions:
    - cut_bench:
        polygon: <name>
        target_cut_ft: 0.8
        max_cut_ft: 2.0
    - fill_shelf:
        polygon: <name>
        target_fill_ft: auto_balance
        max_fill_ft: 1.25
    - smooth_patch:
        polygon: <name>
        sigma_ft: 8.0
  preserve:
    - treatment_cell_core
    - bay_view_corridor
    - seating_rows_on_natural_grade
```

Do not add explanatory text outside the yaml fence. The fence must start with ```yaml and end with ```.
""")


class AgentLoop:
    def __init__(self, config_path: str = CONFIG_PATH, model: str = "claude-sonnet-4-6"):
        self.config_path = Path(config_path)
        self.state = ProjectState.load(config_path)
        self.evaluators = EvaluatorSuite(self.state)
        self.scorer = MultiObjectiveScorer()
        self.scenarios = ScenarioLibrary(self.state)
        self.variants = VariantManager(self.state.root / "variants")
        self.model = model

    def baseline_metrics(self) -> dict:
        delta = ClayDelta.zeros(self.state)
        bowl_az = self.state.cfg["axes"]["face_az"]
        metrics = self.evaluators.run_all(delta, bowl_axis_az=bowl_az)
        score = self.scorer.score(metrics)
        hc = self.evaluators.hard_constraints(metrics)
        metrics["hard_failures"] = hc.get("failures", [])
        return metrics, score

    def print_baseline(self):
        print("Computing baseline metrics (delta=0)…")
        metrics, score = self.baseline_metrics()
        ew = metrics["earthwork"]
        sl = metrics["sightlines"]
        dr = metrics["drainage"]
        sun = metrics["solar"]
        print(f"\n{'='*60}")
        print(f"BASELINE (design_open_low / delta=0)")
        print(f"{'='*60}")
        print(f"  Score:          {score['total']:.1f}/100")
        print(f"  Cut/Fill/Gross: {ew['cut_cy']:.0f} / {ew['fill_cy']:.0f} / {ew['gross_cy']:.0f} CY")
        print(f"  Wall trigger:   {'YES' if ew['wall_trigger'] else 'no'}")
        print(f"  Sightlines:     {sl['pass_count']}/{sl['pass_count']+sl['fail_count']} pass")
        print(f"  Min C:          {sl.get('min_C_mm', '—')} mm")
        print(f"  Drainage:       {dr.get('cell_function_preserved') and 'ok' or 'FAIL'}")
        print(f"  Upper sunset:   {sun.get('upper_crescent_score', 0):.2f}")
        print(f"  Hard failures:  {metrics['hard_failures'] or 'none'}")

    def _polygon_names(self) -> list[str]:
        return sorted(self.scenarios.all_geoms().keys())

    def _state_summary(self, metrics: dict, score: dict, family: str, n_done: int) -> str:
        ew = metrics.get("earthwork", {})
        sl = metrics.get("sightlines", {})
        dr = metrics.get("drainage", {})
        sun = metrics.get("solar", {})
        aes = metrics.get("aesthetic", {})
        cap = metrics.get("capacity", {})

        cfg_family = self.state.cfg["variant_families"].get(family, {})
        axis_az = cfg_family.get("axis_az", 330)
        intent = cfg_family.get("intent", "")
        next_id = n_done + 1

        summary = textwrap.dedent(f"""
        ## Current state (variant {n_done} of this run)
        Family {family}: {intent}
        Bowl axis target: {axis_az}°

        ### Previous metrics (last variant or baseline if n=0)
        - Score: {score.get('total', 0):.1f}/100
        - Cut / Fill / Gross: {ew.get('cut_cy', 0):.0f} / {ew.get('fill_cy', 0):.0f} / {ew.get('gross_cy', 0):.0f} CY
        - Max cut: {ew.get('max_cut_ft', 0):.2f} ft | Max fill: {ew.get('max_fill_ft', 0):.2f} ft
        - Wall trigger: {'YES — MUST FIX' if ew.get('wall_trigger') else 'no'}
        - Yield (neutral): {'balanced' if ew.get('yield_balance', {}).get('neutral', {}).get('balanced') else 'UNBALANCED'}
        - Sightlines: {sl.get('pass_count', 0)}/{sl.get('pass_count', 0)+sl.get('fail_count', 0)} | min C: {sl.get('min_C_mm', '—')} mm
        - Drainage cell ok: {'yes' if dr.get('cell_function_preserved') else 'NO'}
        - Freeboard: {dr.get('event_floor_freeboard_ft', 0):.2f} ft
        - Upper crescent sunset: {sun.get('upper_crescent_score', 0):.2f}
        - Bay view: {aes.get('bay_view_score', 0):.2f}
        - Landform fit: {aes.get('landform_fit', 0):.2f}
        - Capacity (compact/generous): {cap.get('compact', 0):,} / {cap.get('generous', 0):,}
        - Hard failures: {metrics.get('hard_failures', []) or 'none'}

        ### Proposal guidance for next variant (id={next_id})
        - Use only polygon names from the list in POLYGON NAMES.
        - Focus on moves that improve the current weaknesses above.
        - Each fill action must have a corresponding cut action.
        - Keep max_cut_ft ≤ 2.0 and max_fill_ft ≤ 1.25 unless earthwork balance requires otherwise.
        """)
        return summary

    def _call_llm(self, prompt: str) -> str:
        """Call `claude -p` and return stdout."""
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"claude CLI failed: {result.stderr[:500]}")
        return result.stdout

    def _parse_proposal(self, llm_output: str) -> dict:
        """Extract YAML proposal from LLM output."""
        m = re.search(r"```yaml\s*(.*?)```", llm_output, re.DOTALL)
        if not m:
            raise ValueError("No ```yaml fence found in LLM output")
        raw = m.group(1).strip()
        parsed = yaml.safe_load(raw)
        if "proposal" in parsed:
            return parsed["proposal"]
        return parsed

    def apply_proposal(self, proposal: dict) -> tuple[str, dict, dict, bool]:
        """Apply a proposal, evaluate, score, save. Returns (vid, metrics, score, valid)."""
        vid = self.variants.next_id()

        # Pre-validate
        v = self.scenarios.validate_proposal(proposal, self.state)
        if not v["valid"]:
            print(f"  Pre-validation failed: {v['errors']}")
            return vid, {}, {}, False
        if v["warnings"]:
            for w in v["warnings"]:
                print(f"  Warning: {w}")

        # Build delta
        delta = ClayDelta.zeros(self.state)
        bowl_az = proposal.get("bowl_axis_az",
                                self.state.cfg["axes"]["face_az"])

        try:
            self.scenarios.apply_proposal(delta, proposal, self.state)
        except Exception as e:
            print(f"  Delta application error: {e}")
            return vid, {}, {}, False

        # Evaluate
        no_touch_viols = self.evaluators.no_touch_violations(delta)
        if no_touch_viols:
            print(f"  No-touch violations: {no_touch_viols}")
            return vid, {}, {}, False

        metrics = self.evaluators.run_all(delta, bowl_axis_az=bowl_az)
        hc = self.evaluators.hard_constraints(metrics)
        metrics["hard_failures"] = hc.get("failures", [])
        score = self.scorer.score(metrics)
        score["verdict"] = self.scorer.verdict(score, hc)

        # Save
        self.variants.save(vid, delta, metrics, score, proposal, self.state)
        return vid, metrics, score, hc["valid"]

    def run(self, family: str = "A", n_variants: int = 5):
        """Main agent loop: call LLM n_variants times for a family."""
        print(f"\n{'='*60}")
        print(f"AGENT LOOP — Family {family}, {n_variants} variants")
        print(f"{'='*60}")

        # Start from baseline
        metrics, score = self.baseline_metrics()
        polygon_names = "\n".join(f"  - {n}" for n in self._polygon_names())
        cfg_family = self.state.cfg["variant_families"].get(family, {})
        axis_az = cfg_family.get("axis_az", 330)

        for i in range(n_variants):
            print(f"\n--- Variant {i+1}/{n_variants} ---")

            state_summary = self._state_summary(metrics, score, family, i)
            polygon_list = "\n".join(f"  - {n}" for n in self._polygon_names())

            sys_prompt = SYSTEM_PROMPT.format(
                polygon_names=polygon_list,
                next_id=i + 1,
                family=family,
                axis_az=axis_az,
            )
            full_prompt = sys_prompt + "\n\n" + state_summary

            print("  Calling LLM…")
            try:
                llm_out = self._call_llm(full_prompt)
            except Exception as e:
                print(f"  LLM call failed: {e}")
                continue

            try:
                proposal = self._parse_proposal(llm_out)
            except Exception as e:
                print(f"  Parse error: {e}")
                print(f"  Raw output: {llm_out[:500]}")
                continue

            print(f"  Proposal intent: {proposal.get('intent', 'unspecified')}")
            vid, metrics, score, valid = self.apply_proposal(proposal)

            if valid:
                print(f"  ✓ {vid} score={score.get('total', 0):.1f} verdict={score.get('verdict', '?')}")
            else:
                failures = metrics.get("hard_failures", [])
                print(f"  ✗ {vid} INVALID — {failures}")

        print(f"\n{'='*60}")
        print("COMPARISON TABLE")
        print(self.variants.comparison_table())


def _run_apply(proposal_path: str):
    loop = AgentLoop()
    proposal = yaml.safe_load(open(proposal_path))
    if "proposal" in proposal:
        proposal = proposal["proposal"]
    vid, metrics, score, valid = loop.apply_proposal(proposal)
    verdict = score.get("verdict", "—")
    print(f"\nVariant {vid}: score={score.get('total', 0):.1f} verdict={verdict} valid={valid}")
    if not valid:
        print("Hard failures:", metrics.get("hard_failures", []))
    print(f"Report: variants/{vid}/report.md")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Agentic-clay harness CLI")
    parser.add_argument("--family", default="A", help="Variant family (A–E)")
    parser.add_argument("--n", type=int, default=5, help="Number of variants to generate")
    parser.add_argument("--baseline", action="store_true", help="Print baseline metrics and exit")
    parser.add_argument("--compare", action="store_true", help="Print comparison table and exit")
    parser.add_argument("--apply", help="Apply a YAML proposal file and evaluate")
    parser.add_argument("--config", default=CONFIG_PATH, help="Path to harness_config.yaml")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Model to use for agent")
    args = parser.parse_args()

    os.chdir(Path(args.config).parent)

    if args.baseline:
        loop = AgentLoop(args.config, args.model)
        loop.print_baseline()
    elif args.compare:
        loop = AgentLoop(args.config, args.model)
        print(loop.variants.comparison_table())
    elif args.apply:
        loop = AgentLoop(args.config, args.model)
        _run_apply(args.apply)
    else:
        loop = AgentLoop(args.config, args.model)
        loop.run(family=args.family, n_variants=args.n)
