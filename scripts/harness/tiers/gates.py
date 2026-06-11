"""Audit gates for the intervention-tier run. ANY failure fails the run.

  G1  baseline lock — the Scenario E input files must match the SHA-256
      hashes pinned in configs/intervention_tiers/_baseline_lock.json, and
      the Scenario_E_baseline scenario must carry zero operations and the
      locked 500.8 CY total.
  G2  same evaluator — every scenario result carries the identical evaluator
      fingerprint and the identical metric key set.
  G3  no silent regression — a scenario that improves the composite score or
      aesthetics may not drop an ADA / sightline / drainage check that the
      baseline passes.
  G4  ambitious reporting — ambitious/idealized scenarios must report
      max cut/fill depth and a wall-trigger block (non-null), and cap
      violations must be surfaced, not clipped.
  G5  governing geometry — no scenario may consume design_open_low as
      governing seating geometry (recipe sources + model provenance).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

BASELINE_TOTAL_CY = 500.8
LOCK_NAME = "_baseline_lock.json"

LOCKED_FILES = (
    "analysis/scenarioE_civic/geometry.geojson",
    "analysis/scenarioE_civic/earthwork.csv",
    "design_extended_bays/composition_table.csv",
    "design_extended_bays/seating_bays.geojson",
)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def write_baseline_lock(root: Path, lock_dir: Path) -> Path:
    lock = {f: file_sha256(root / f) for f in LOCKED_FILES}
    out = lock_dir / LOCK_NAME
    out.write_text(json.dumps(lock, indent=2) + "\n")
    return out


def run_gates(root: Path, lock_dir: Path, results: dict[str, dict],
              recipes: dict[str, object]) -> dict:
    failures: list[str] = []
    warnings: list[str] = []

    # ── G1: baseline lock ───────────────────────────────────────────────
    lock_path = lock_dir / LOCK_NAME
    if not lock_path.exists():
        failures.append(f"G1: baseline lock missing ({lock_path}) — "
                        f"generate it once from the accepted Scenario E state")
    else:
        lock = json.loads(lock_path.read_text())
        for f, want in lock.items():
            p = root / f
            if not p.exists():
                failures.append(f"G1: locked baseline file missing: {f}")
            elif file_sha256(p) != want:
                failures.append(
                    f"G1: SCENARIO E BASELINE CHANGED SILENTLY — hash drift in {f}. "
                    f"If the change is intentional, re-accept Scenario E and "
                    f"regenerate the lock explicitly.")

    base = results.get("Scenario_E_baseline")
    if base is None:
        failures.append("G1: Scenario_E_baseline scenario missing from run")
    else:
        if base["op_records"]:
            failures.append("G1: baseline scenario has operations — it must be a no-op control")
        got = base["earthwork"]["total_gross_cy"]
        if abs(got - BASELINE_TOTAL_CY) > 0.5:
            failures.append(
                f"G1: baseline earthwork {got} CY != locked {BASELINE_TOTAL_CY} CY")

    # ── G2: same evaluator ──────────────────────────────────────────────
    fps = {name: r["evaluator"]["fingerprint"] for name, r in results.items()}
    if len(set(fps.values())) > 1:
        failures.append(f"G2: scenarios used different evaluators: {fps}")
    keysets = {name: tuple(sorted(r.keys())) for name, r in results.items()}
    if len(set(keysets.values())) > 1:
        failures.append("G2: scenarios report different metric key sets")

    # ── G3: no silent regression ────────────────────────────────────────
    if base is not None:
        base_checks = base["hard_checks"]
        for name, r in results.items():
            if name == "Scenario_E_baseline":
                continue
            improved = r["score"]["total"] > base["score"]["total"]
            for check in ("ada_ok", "drainage_ok", "sightlines_formal_ok"):
                if base_checks.get(check) and not r["hard_checks"].get(check):
                    if improved:
                        failures.append(
                            f"G3: {name} improves the composite score but drops "
                            f"{check} — aesthetic gain may not buy down safety")
                    else:
                        warnings.append(f"G3: {name} drops {check} (score did not improve)")

    # ── G4: ambitious reporting ─────────────────────────────────────────
    for name, r in results.items():
        if r["tier_class"] in ("ambitious", "idealized"):
            ew, walls = r["earthwork"], r["walls"]
            if ew.get("max_overall_cut_ft") is None or ew.get("max_overall_fill_ft") is None:
                failures.append(f"G4: {name} lacks max cut/fill depth reporting")
            if not isinstance(walls.get("wall_trigger"), bool):
                failures.append(f"G4: {name} lacks wall-trigger reporting")
        for rec in r["op_records"]:
            for issue in rec.get("cap_issues", []):
                warnings.append(f"G4: {name}: {issue} (reported, not clipped)")

    # ── G5: governing geometry ──────────────────────────────────────────
    for name, r in results.items():
        prov = r.get("geometry_provenance", {})
        for k, v in prov.items():
            if "design_open_low" in str(v):
                failures.append(
                    f"G5: {name} consumes design_open_low as governing geometry "
                    f"({k}={v}) — superseded for seating")
        recipe = recipes.get(name)
        if recipe is not None:
            for k, v in recipe.base_geometry.items():
                if "design_open_low" in str(v):
                    failures.append(f"G5: recipe {name} base_geometry.{k} "
                                    f"references design_open_low")
        st = r.get("stage", {})
        if st.get("rule9_status") == "resolved":
            failures.append(f"G5: {name} declares the stage fan RESOLVED while "
                            f"DESIGN_CANON Rule 9 is open")

    return {"passed": not failures, "failures": failures, "warnings": warnings}
