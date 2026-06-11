"""Intervention-tier retrofit: scenario generator + common evaluator.

Compares Scenario E (locked baseline) against modest / optimized / ambitious /
idealized earthwork interventions under ONE metric set.

Governing seating geometry: scenarioE_three_section_civic_bowl
(analysis/scenarioE_civic + design_extended_bays). design_open_low is
SUPERSEDED for seating and is rejected as governing geometry by the gates.
"""
from .geometry_model import SectionSeatingModel, TierState
from .recipes import Recipe, load_recipes
from .operations import apply_operations
from .evaluator import TierEvaluator
from .cost_model import CostModel
from .gates import run_gates

__all__ = [
    "SectionSeatingModel", "TierState", "Recipe", "load_recipes",
    "apply_operations", "TierEvaluator", "CostModel", "run_gates",
]
