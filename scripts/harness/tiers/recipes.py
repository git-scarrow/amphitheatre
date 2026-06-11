"""Recipe loader/validator for configs/intervention_tiers/*.yaml.

A recipe declares: base geometry (always the locked Scenario E sources),
allowed operations, constraint caps, the operation list, and scoring weights.
Recipes that declare design_open_low as a seating-geometry source are rejected
at load time (and again by the audit gates).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

TIER_CLASSES = ("baseline", "modest", "optimized", "ambitious", "idealized")

REQUIRED_BASE_KEYS = ("scheme", "treads", "composition", "bays", "earthwork")

GOVERNING_SCHEME = "scenarioE_three_section_civic_bowl"

DEFAULT_CONSTRAINTS = {
    "max_cut_ft": 2.0,
    "max_fill_ft": 1.5,
    "wall_trigger_cut_ft": 3.0,
    "wall_trigger_fill_ft": 3.0,
    "net_balance_required": False,
    "preserve": ["treatment_cell", "bay_view_corridor", "drainage_swales"],
}

DEFAULT_WEIGHTS = {
    "capacity": 1.0,          # quality-adjusted seats vs baseline
    "sightlines": 1.5,
    "section_balance": 0.6,
    "stage_fit": 1.0,
    "ada": 1.5,
    "drainage": 1.5,
    "bay_view": 1.5,
    "acoustic": 0.8,
    "operations": 0.6,
    "earthwork_economy": 1.2,
    "wall_avoidance": 1.5,
}


@dataclass
class Recipe:
    name: str
    tier_class: str
    intent: str
    base_geometry: dict
    allowed_operations: list[str]
    constraints: dict
    operations: list[dict]
    scoring_weights: dict
    path: str = ""
    notes: str = ""

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Recipe":
        raw = yaml.safe_load(open(path))
        r = raw.get("recipe", raw)
        errors = []

        name = r.get("name") or Path(path).stem
        tier_class = r.get("tier_class", "")
        if tier_class not in TIER_CLASSES:
            errors.append(f"tier_class '{tier_class}' not in {TIER_CLASSES}")

        base = r.get("base_geometry", {})
        for k in REQUIRED_BASE_KEYS:
            if k not in base:
                errors.append(f"base_geometry missing '{k}'")
        if base.get("scheme") != GOVERNING_SCHEME:
            errors.append(
                f"base_geometry.scheme must be '{GOVERNING_SCHEME}' "
                f"(got '{base.get('scheme')}')")
        for k in ("treads", "composition", "bays", "earthwork"):
            v = str(base.get(k, ""))
            if "design_open_low" in v:
                errors.append(
                    f"base_geometry.{k} references design_open_low — superseded "
                    f"for seating, rejected as governing geometry")

        allowed = r.get("allowed_operations", [])
        ops = r.get("operations", [])
        for o in ops:
            op = o.get("op")
            if op not in allowed:
                errors.append(f"operation '{op}' not in allowed_operations")

        constraints = {**DEFAULT_CONSTRAINTS, **r.get("constraints", {})}
        weights = {**DEFAULT_WEIGHTS, **r.get("scoring_weights", {})}

        if errors:
            raise ValueError(f"Recipe {path}: " + "; ".join(errors))

        return cls(
            name=name, tier_class=tier_class,
            intent=r.get("intent", ""), base_geometry=base,
            allowed_operations=allowed, constraints=constraints,
            operations=ops, scoring_weights=weights,
            path=str(path), notes=r.get("notes", ""),
        )


def load_recipes(config_dir: str | Path) -> list[Recipe]:
    config_dir = Path(config_dir)
    recipes = []
    for p in sorted(config_dir.glob("*.yaml")):
        if p.name.startswith("_"):
            continue
        recipes.append(Recipe.from_yaml(p))
    if not recipes:
        raise FileNotFoundError(f"No tier recipes found in {config_dir}")
    return recipes
