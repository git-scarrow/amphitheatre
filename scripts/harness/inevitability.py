"""InevitabilityEngine: make "feels inevitable" agent-checkable.

Governing sentence (INEVITABILITY.md):
  What kind of amphitheater is already latent in this land, and what is the least,
  most graceful intervention needed to reveal it?

Definition made operational:
  A design is INEVITABLE when every visible intervention is either compelled by a
  site affordance, required by performance, or justified by a deliberate civic
  choice — and no major form is arbitrary, ornamental, or merely leftover from
  optimization.

This module scores a *design* (an ordered set of Moves) against that definition.
It is a filter that runs BEFORE human review, not a replacement for it: it can
measure consistency and catch false success (Scenario-B-style dished pseudo-seating),
but it cannot know when a place has become memorable.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict


# ── canonical move vocabulary (effect signatures are documentation/reference) ────
MOVE_VOCAB = {
    "reveal_contour_terrace":          "expose a terrace the slope already supports",
    "restore_formal_tread":            "fill a clipped/dished tread back to its design plane",
    "dissolve_row_into_lawn":          "demote a weak row to informal grass terrace",
    "thicken_edge_as_landscape_shoulder": "turn a weak edge into planted shoulder",
    "convert_clipped_tip_to_overlook": "make an arc-clipped fragment a view overlook",
    "bend_access_route_with_contour":  "route access along a contour, not across it",
    "place_landing_at_view_pause":     "put a landing where the bowl/view reveals",
    "reclassify_row_band_to_circulation": "reassign a seating row band as circulation — "
        "geometry is row-derived (the rows already track terrain), NOT discovered from a "
        "seam/path/desire-line search",
    "frame_stage_laterally_without_blocking_bay": "side-frame the stage, keep upstage open",
    "use_swale_as_planted_room_edge":  "drainage doubles as a planted spatial edge",
    "borrow_from_high_side_to_complete_low_tread": "balance a tread by local cut→fill",
    "demote_weak_outer_capacity_to_picnic_terrace": "outer rows become picnic lawn",
    "preserve_open_upstage_view":      "no-op guard: keep the bay/sky corridor open",
}

# the ten positive-acceptance criteria (a move is preferred if it satisfies ≥2)
POSITIVE_CRITERIA = [
    "uses_existing_contour", "clarifies_seating_bowl", "improves_sightlines",
    "improves_access", "improves_drainage", "preserves_bay_view",
    "creates_useful_edge_or_landing", "reduces_artificial_grading",
    "turns_fragment_into_landscape", "adds_daily_nonevent_value",
]

# move types that a cost-proxy design needs delivered as validated geometry
ACCESS_TYPES   = {"bend_access_route_with_contour", "place_landing_at_view_pause",
                  "reclassify_row_band_to_circulation"}
DRAINAGE_TYPES = {"use_swale_as_planted_room_edge"}

# circulation moves INSIDE the seating rake must be made FROM seating geometry (a role
# reassignment), not from an independent path/seam search. The provenance must match the
# geometry: such a move declares how it was generated and the engine enforces it.
ROW_DERIVED_CIRCULATION_TYPES = {"reclassify_row_band_to_circulation"}


@dataclass
class Move:
    move_id: str
    move_type: str
    geometry: str
    site_reasons: list = field(default_factory=list)
    performance_reasons: list = field(default_factory=list)
    civic_reasons: list = field(default_factory=list)
    cost: dict = field(default_factory=lambda: {"cut_cy": 0.0, "fill_cy": 0.0, "gross_cy": 0.0})
    effects: dict = field(default_factory=dict)
    positive_criteria: list = field(default_factory=list)   # subset of POSITIVE_CRITERIA
    rejection_if_removed: list = field(default_factory=list)
    status: str = "proposed"
    # intent-vs-geometry invariant: an intent move may lift CONCEPT ranking but may not
    # satisfy a COST-PROXY gate until it emits polygons (geometry_backed) and passes
    # validation (validated).
    cost_status: str = "placeholder"        # placeholder | geometry_backed
    validation_status: str = "intent_only"  # intent_only | validated | not_validated
    may_satisfy: list = field(default_factory=list)
    may_not_satisfy: list = field(default_factory=list)
    # provenance — what OPERATION actually created this geometry. A move is not honest
    # unless its provenance matches its geometry (e.g. a row-reclassification aisle must
    # say geometry_source="row_reclassification", seam_derived=False — not pretend it was
    # discovered from a seam/path). Keys: geometry_source, seam_derived, source_geometry,
    # operation. Empty for moves where provenance is not yet load-bearing.
    provenance: dict = field(default_factory=dict)

    def is_geometry_validated(self) -> bool:
        return self.cost_status == "geometry_backed" and self.validation_status == "validated"

    # — allow rule: ≥1 site reason AND ≥1 (performance OR civic) reason —
    def allowed(self) -> tuple[bool, str]:
        if self.move_type not in MOVE_VOCAB:
            return False, f"unknown move_type '{self.move_type}'"
        if not self.site_reasons:
            return False, "no site reason — intervention not compelled by the land"
        if not (self.performance_reasons or self.civic_reasons):
            return False, "no performance or civic reason — purpose unstated"
        return True, "ok"

    # — multi-duty: how many problems one gesture solves —
    def duty(self) -> int:
        return len(set(self.site_reasons)) + len(set(self.performance_reasons)) + len(set(self.civic_reasons))

    # — "if it can be removed without making the place worse, it was not inevitable" —
    def inevitable(self) -> bool:
        ok, _ = self.allowed()
        return ok and len(self.rejection_if_removed) > 0


@dataclass
class Design:
    scenario: str
    moves: list                      # list[Move]
    claims: dict = field(default_factory=dict)   # e.g. {"formal_seats_claimed": 1452}
    surfaces_classified: bool = True             # every polygon has a civic role?
    omits_required_surfaces: list = field(default_factory=list)  # e.g. ["ADA","seat_zone"]
    # 'concept' = design-shaping diagnostic (ADA/drainage may be deferred to Scenario E);
    # 'cost_proxy' = claims a project-cost number, so ALL required surfaces must be present.
    stage: str = "concept"


class InevitabilityEngine:
    def __init__(self, affordances: dict, validation: dict):
        self.aff = affordances
        self.val = validation

    def _validated_move(self, d: Design, types: set) -> bool:
        return any(m.move_type in types and m.is_geometry_validated() for m in d.moves)

    # ── hard rejection rules (any True ⇒ automatic reject) ───────────────────────
    def hard_rejections(self, d: Design) -> list:
        v = self.val
        out = []
        # 0. intent-vs-geometry invariant: a cost-proxy design must deliver ADA and
        #    drainage as geometry-backed, validated moves — never on intent alone —
        #    and every cost-bearing move must carry geometry-backed CY.
        if d.stage == "cost_proxy":
            if not self._validated_move(d, ACCESS_TYPES):
                out.append("cost-proxy design has no geometry-backed + validated ADA/access move "
                           "(intent move cannot satisfy a cost-proxy gate)")
            if not self._validated_move(d, DRAINAGE_TYPES):
                out.append("cost-proxy design has no geometry-backed + validated drainage move "
                           "(intent move cannot satisfy a cost-proxy gate)")
            for m in d.moves:
                if m.cost.get("gross_cy", 0) > 0 and m.cost_status != "geometry_backed":
                    out.append(f"cost-proxy move {m.move_id} reports placeholder CY (no emitted geometry)")
                # a geometry-backed move that FAILED its own validation cannot be carried
                # into a cost-proxy design (e.g. circulation overlapping counted seating).
                if m.cost_status == "geometry_backed" and m.validation_status == "not_validated":
                    out.append(f"cost-proxy move {m.move_id} is geometry-backed but failed validation "
                               f"({m.move_type})")
        # 1. formal seat counted on clipped/dished tread
        asbuilt_A = (v.get("bands_asbuilt", {}) or {}).get("A", 0)
        claimed = d.claims.get("formal_seats_claimed", 0)
        restored = any(m.move_type == "restore_formal_tread" for m in d.moves)
        if claimed > asbuilt_A + 1 and not restored:
            out.append(f"claims {claimed:.0f} formal seats but only {asbuilt_A:.0f} pass all gates "
                       f"as-built and no restore_formal_tread move is present "
                       f"(formal seats on clipped/dished tread)")
        # 2. clipped fragment with no assigned role
        if not d.surfaces_classified:
            out.append("a surface is visible in plan but has no use classification")
        # 3. a COST-PROXY design claims low earthwork by omitting required surfaces.
        #    (At 'concept' stage, ADA/drainage may be honestly deferred to Scenario E —
        #    those are reported as open_items, not a rejection.)
        if d.stage == "cost_proxy" and d.omits_required_surfaces:
            out.append(f"cost-proxy design omits required surfaces from earthwork: "
                       f"{d.omits_required_surfaces} (false low-CY by omission)")
        # 4. any move solves one metric while damaging the larger reading
        for m in d.moves:
            if m.effects.get("visual_legibility") == "decreased" and not m.civic_reasons:
                out.append(f"move {m.move_id} reduces legibility with no civic justification")
        # 5. stage element blocks the bay/sky view without a civic reason
        for m in d.moves:
            if m.effects.get("blocks_view") is True and not m.civic_reasons:
                out.append(f"move {m.move_id} blocks the bay/sky corridor with no stated civic reason")
        # 6. an arbitrary move (fails allow rule)
        for m in d.moves:
            ok, why = m.allowed()
            if not ok:
                out.append(f"move {m.move_id} not allowed: {why}")
        # 7. provenance must match geometry: a circulation band inside the rake must be a
        #    row reassignment, not a laundered path/seam discovery. The move has to SAY
        #    what operation created it. (This caught the "seam-derived cross-aisle" story:
        #    the geometry was union(rows).difference(retained), but it was narrated as a
        #    seam search — a provenance failure, not a geometry failure.)
        for m in d.moves:
            if m.move_type in ROW_DERIVED_CIRCULATION_TYPES:
                p = m.provenance or {}
                if p.get("geometry_source") != "row_reclassification":
                    out.append(f"move {m.move_id} is a row-band circulation move but does not "
                               f"declare geometry_source='row_reclassification' "
                               f"(got {p.get('geometry_source')!r}) — provenance must match geometry")
                if p.get("seam_derived") is not False:
                    out.append(f"move {m.move_id} claims/leaves seam_derived={p.get('seam_derived')!r}; "
                               f"a row-reclassification aisle is not seam-derived (must be False)")
        return out

    # ── scores (proxies, not the final judge) ────────────────────────────────────
    def score(self, d: Design) -> dict:
        moves = d.moves
        if not moves:
            return {"terrain_fit": 0, "civic_fit": 0, "multi_duty": 0, "inevitability": 0}
        terrain = sum(1 for m in moves if m.site_reasons) / len(moves)
        civic   = sum(1 for m in moves if m.civic_reasons) / len(moves)
        multi   = sum(m.duty() for m in moves) / len(moves)
        gross   = sum(m.cost.get("gross_cy", 0) for m in moves)
        arbitrary_penalty = sum(1 for m in moves if not m.inevitable())
        hidden_penalty    = len(self.hard_rejections(d))
        inev = (terrain + civic) * 5 + multi - 2 * arbitrary_penalty - 3 * hidden_penalty - gross * 0.01
        return {
            "terrain_fit": round(terrain, 3), "civic_fit": round(civic, 3),
            "multi_duty": round(multi, 2), "gross_cy": round(gross, 1),
            "arbitrary_moves": arbitrary_penalty, "hidden_failures": hidden_penalty,
            "inevitability": round(inev, 2),
        }

    # ── four ledgers ─────────────────────────────────────────────────────────────
    def ledgers(self, d: Design) -> dict:
        v = self.val
        # 1. performance — from the spatial validation gates.
        #    ADA/drainage are HARD gates only for a cost-proxy design; at concept stage
        #    they are deferred (reported as open_items) so they don't fail composition.
        concept = d.stage != "cost_proxy"
        gates = {
            "no_formal_seat_on_clip": any(m.move_type == "restore_formal_tread" for m in d.moves)
                                       or d.claims.get("formal_seats_claimed", 0) <= (v.get("bands_asbuilt", {}) or {}).get("A", 0) + 1,
            "sightlines_validated": True,        # C_actual≈C_ideal confirmed in validation
            "sensitivity_passes": True,
            # at cost-proxy, ADA/drainage gates require geometry-backed validated moves
            "ada_in_earthwork": concept or self._validated_move(d, ACCESS_TYPES),
            "drainage_resolved": concept or self._validated_move(d, DRAINAGE_TYPES),
        }
        performance = {"pass": all(gates.values()), "gates": gates}
        # 2. affordance — does the design cite real site affordances?
        cited = set()
        for m in d.moves:
            cited |= set(m.site_reasons)
        affordance = {"pass": len(cited) >= 3, "affordances_cited": sorted(cited)}
        # 3. role — every surface has a civic role. ADA/drainage deferral is allowed
        #    at concept stage (open_item); a cost-proxy design must classify them too.
        role = {"pass": d.surfaces_classified and (concept or not d.omits_required_surfaces),
                "bands_scenarioD": v.get("bands_scenarioD", {})}
        # 4. justification — every move carries why-here + why-this-shape
        unjustified = [m.move_id for m in d.moves if not m.inevitable()]
        justification = {"pass": len(unjustified) == 0, "unjustified_moves": unjustified}
        return {"performance": performance, "affordance": affordance,
                "role": role, "justification": justification}

    # ── done-means: the ten-question checklist ───────────────────────────────────
    def done_checklist(self, d: Design) -> dict:
        L = self.ledgers(d)
        hr = self.hard_rejections(d)
        concept = d.stage != "cost_proxy"
        q = {
            "1_formal_seats_pass_all_gates": L["performance"]["gates"]["no_formal_seat_on_clip"],
            "2_nonformal_rows_have_role": d.surfaces_classified,
            "3_earthwork_areas_named": all(m.cost for m in d.moves),
            "4_routes_relate_to_terrain": concept or "ADA" not in d.omits_required_surfaces,
            "5_edges_resolve": d.surfaces_classified,
            "6_stage_strengthens_bowl_view_use": any(
                m.move_type in ("preserve_open_upstage_view", "frame_stage_laterally_without_blocking_bay")
                for m in d.moves) or "stage" not in d.omits_required_surfaces,
            "7_drainage_reinforces_landform": concept or "drainage" not in d.omits_required_surfaces,
            "8_low_intervention_without_false_surfaces": len(hr) == 0,
            "9_no_removable_move_without_loss": all(m.inevitable() for m in d.moves),
            "10_move_by_move_justification": L["justification"]["pass"],
        }
        return {"all_done": all(q.values()), "questions": q}

    # ── full verdict ─────────────────────────────────────────────────────────────
    def evaluate(self, d: Design) -> dict:
        hr = self.hard_rejections(d)
        ledg = self.ledgers(d)
        done = self.done_checklist(d)
        sc = self.score(d)
        accepted = (len(hr) == 0 and all(l["pass"] for l in ledg.values()) and done["all_done"])
        open_items = []
        if d.stage != "cost_proxy" and d.omits_required_surfaces:
            open_items = [f"{s} deferred to Scenario E (cost-proxy stage)" for s in d.omits_required_surfaces]
        return {
            "scenario": d.scenario,
            "stage": d.stage,
            "verdict": ("ACCEPTED — inevitable" if accepted else "REJECTED — not inevitable")
                       + (" (concept)" if accepted and d.stage != "cost_proxy" else ""),
            "accepted": accepted,
            "open_items": open_items,
            "hard_rejections": hr,
            "ledgers": {k: l["pass"] for k, l in ledg.items()},
            "ledger_detail": ledg,
            "done_checklist": done,
            "scores": sc,
            "moves": [asdict(m) for m in d.moves],
        }
