"""Composer: GENERATE designs (move sets / families) from the site affordance map.

This is the composing half of the agentic clay. The InevitabilityEngine *checks*
designs; the Composer *writes* them — and the same engine then critiques what it
wrote, so a degenerate composition (e.g. "count every row as formal") is rejected
by the very rules that generated the good ones.

Input
-----
  affordances : AffordanceEngine.build()   (latent rake, hinge, view axis, edges, drainage)
  rows        : per-row validation data     (band, seats, restorable, clip cost)

Method
------
For each row the composer assigns a ROLE from (a) the validation band and
restorability and (b) the FAMILY policy, then emits one Move per contiguous role
group with its schema auto-populated FROM THE DATA:
  site_reasons        ← affordances that compel the move (rake, hinge, edges)
  performance_reasons ← validation gates the move satisfies (C, cross-slope, clip)
  civic_reasons       ← the family's character
  cost                ← summed restoration CY for that group (0 for demote/dissolve)
  effects/seats       ← summed row seats
  rejection_if_removed← what the place loses without it (the inevitability test)

Eight families vary one small policy vector (where the formal/lawn line falls, how
much access/drainage/framing to compose), producing genuinely different characters
— not just cheaper/dearer versions of one optimum.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .inevitability import Move, Design

FORMAL_MM, SOFT_MM, MARG_MM = 90.0, 60.0, 30.0


# ── family policies ──────────────────────────────────────────────────────────────
# formal_max_row : restore formal only up to this row (None = all restorable rows)
# access / drainage / framing : compose those moves (lifts ledgers toward cost-proxy)
# character : civic reasons injected into every seating move
FAMILIES = {
    "civic_bowl": dict(
        formal_max_row=None, access=False, drainage=False, framing=False, stage="concept",
        character=["strongest formal civic bowl", "a terrace must read as a terrace"],
        blurb="Maximal formal lower bowl — the Scenario D baseline."),
    "meadow_bowl": dict(
        formal_max_row=12, access=False, drainage=False, framing=False, stage="concept",
        character=["fewer fixed terraces, more grass picnic shelves", "soft daily-use hillside"],
        blurb="Formal lower rows, the rest dissolved to lawn terraces."),
    "festival_bowl": dict(
        formal_max_row=10, access=True, drainage=False, framing=False, stage="concept",
        character=["broad flexible lawn over a compact formal core", "festival/movie crowds"],
        blurb="Compact formal core + wide flexible lawn, with festival circulation."),
    "processional_bowl": dict(
        formal_max_row=None, access=True, drainage=False, framing=False, stage="concept",
        character=["arrival sequence is the primary experience", "descend into the bowl"],
        blurb="Civic bowl whose access route + landings are the composition."),
    "stormwater_garden_bowl": dict(
        formal_max_row=None, access=False, drainage=True, framing=False, stage="concept",
        character=["the treatment cell becomes a visible planted landscape", "drainage as structure"],
        blurb="Civic bowl where swales/treatment cell are a designed garden edge."),
    # NOTE: composed designs are ALWAYS 'concept'. access/drainage/framing here are
    # INTENT moves (no polygons yet) — they lift concept ranking but cannot satisfy a
    # cost-proxy gate. Reaching cost_proxy requires the Scenario E geometry emitter.
    "ceremonial_bay_bowl": dict(
        formal_max_row=None, access=False, drainage=False, framing=True, stage="concept",
        character=["the bay/sky axis dominates", "ceremonial open-air room"],
        blurb="Civic bowl with lateral stage framing that protects the bay axis."),
    "minimal_intervention_bowl": dict(
        formal_max_row=8, access=False, drainage=False, framing=False, stage="concept",
        character=["least construction that still reads as intentional", "restraint"],
        blurb="Restore only the rows needed to read as a bowl; lawn above."),
    "neighborhood_daily_bowl": dict(
        formal_max_row=10, access=True, drainage=True, framing=False, stage="concept",
        character=["paths, shade, casual sitting edges, daily use", "neighborhood commons"],
        blurb="Daily-use commons: smaller formal core, paths + drainage gardens."),
}


class Composer:
    def __init__(self, affordances: dict, rows: list[dict]):
        self.aff = affordances
        self.rows = rows
        rake = affordances["natural_rake"]; hinge = affordances["bowl_hinge"]
        edges = affordances["edges"]; view = affordances["view_axis"]; drain = affordances["drainage"]
        # canned site-reason fragments grounded in the detected affordances
        self.site = {
            "rake": f"natural rake rises {rake['mean_radial_rise_pct']}%/ft over "
                    f"{rake['rake_rises_outward_frac']:.0%} of the fan (+{rake['natural_rise_over_fan_ft']} ft)",
            "hinge": f"bowl hinge at R≈{hinge['hinge_radius_ft']} ft",
            "tips": f"arc clipped by Petoskey/Mitchell streets (rows {edges['clipped_tip_rows']})",
            "view": f"bay+sky on the {view['face_az_deg']}° NNW view axis",
            "drain": f"site drains NE to the bay; treatment cell bottom {drain['treatment_cell_bottom_navd88']}",
        }

    @classmethod
    def from_validation(cls, affordances: dict, row_csv: str | Path,
                        seg_csv: str | Path | None = None) -> "Composer":
        # precise per-row restoration cost = sum of segment repair_fill_cy (under-seat
        # clipping only; tip clipping legitimately drains and needs no restoration).
        repair_by_row: dict[int, float] = {}
        if seg_csv and Path(seg_csv).exists():
            for s in csv.DictReader(open(seg_csv)):
                rid = int(s["row_id"])
                repair_by_row[rid] = repair_by_row.get(rid, 0.0) + float(s.get("repair_fill_cy") or 0.0)
        rows = []
        for r in csv.DictReader(open(row_csv)):
            def f(k):
                v = r.get(k, "")
                return float(v) if v not in ("", None) else None
            rid = int(r["row"])
            rows.append({
                "row": rid, "n_sec": int(r["n_sec"]),
                "seats": int(float(r["seats"])) if r.get("seats") else 0,
                "C_actual": f("C_actual_mm"), "C_ideal": f("C_ideal_mm"),
                "comp_C": f("comp_C_mm"), "unmet_cy": f("unmet_cy") or 0.0,
                "restore_cy": round(repair_by_row.get(rid, f("unmet_cy") or 0.0), 3),
            })
        return cls(affordances, rows)

    # — per-row band + restorability from the validation data —
    def _band(self, r: dict) -> str:
        c = r["C_actual"] if r["C_actual"] is not None else (r["comp_C"] if r["comp_C"] is not None else 999)
        if r["row"] == 1:
            c = 999
        if c >= FORMAL_MM: return "A"
        if c >= SOFT_MM:   return "B"
        if c >= MARG_MM:   return "C"
        return "D"

    def _restorable(self, r: dict) -> bool:
        return r["n_sec"] >= 3 and (r["row"] == 1 or (r["C_ideal"] is not None and r["C_ideal"] >= FORMAL_MM))

    # ── generate one family ──────────────────────────────────────────────────────
    def generate(self, family: str) -> Design:
        pol = FAMILIES[family]
        fmax = pol["formal_max_row"]
        groups = {"formal": [], "lawn": [], "overflow": [], "overlook": []}
        for r in self.rows:
            band = self._band(r)
            restorable = self._restorable(r)
            if restorable and (fmax is None or r["row"] <= fmax):
                groups["formal"].append(r)
            elif band in ("A", "B") and r["n_sec"] >= 3:
                groups["lawn"].append(r)          # demoted formal-capable or soft row → terrace
            elif band == "C":
                groups["overflow"].append(r)
            else:
                groups["overlook"].append(r)      # rim / clipped tips → landscape

        moves: list[Move] = []
        def seats(g): return sum(x["seats"] for x in g)
        def rows_lbl(g): return f"rows {min(x['row'] for x in g)}-{max(x['row'] for x in g)}" if g else "—"

        if groups["formal"]:
            cy = round(sum(x["restore_cy"] for x in groups["formal"]), 1)
            moves.append(Move(
                move_id=f"{family}_restore_formal",
                move_type="restore_formal_tread",
                geometry=f"{rows_lbl(groups['formal'])} (restorable, C_ideal>=90)",
                site_reasons=[self.site["rake"], self.site["hinge"]],
                performance_reasons=["restores 2% cross-slope on dished treads",
                                     "removes clip_under_seat", "holds C>=90mm on the actual surface"],
                civic_reasons=pol["character"] + ["completes a continuous legible lower bowl"],
                cost={"cut_cy": 0.0, "fill_cy": cy, "gross_cy": cy},
                effects={"formal_seats": f"+{seats(groups['formal'])}", "visual_legibility": "increased",
                         "drainage_risk": "reduced"},
                positive_criteria=["uses_existing_contour", "clarifies_seating_bowl",
                                   "improves_sightlines", "improves_drainage"],
                rejection_if_removed=["formal seating discontinuity", "clip dishing under seats"],
                status="accepted"))
        if groups["lawn"]:
            moves.append(Move(
                move_id=f"{family}_dissolve_lawn",
                move_type="dissolve_row_into_lawn",
                geometry=f"{rows_lbl(groups['lawn'])} demoted to grass terrace",
                site_reasons=[self.site["rake"]],
                performance_reasons=["honest banding below the formal threshold or beyond the formal line"],
                civic_reasons=pol["character"] + ["soft terrace for picnic/daily use, not advertised as formal"],
                cost={"cut_cy": 0.0, "fill_cy": 0.0, "gross_cy": 0.0},
                effects={"informal_capacity": f"+{seats(groups['lawn'])}", "visual_softness": "increased",
                         "civic_formality": "decrease"},
                positive_criteria=["reduces_artificial_grading", "adds_daily_nonevent_value",
                                   "clarifies_seating_bowl"],
                rejection_if_removed=["upper rows over-counted as formal", "lost daily-use lawn"],
                status="accepted"))
        if groups["overflow"]:
            moves.append(Move(
                move_id=f"{family}_overflow_terrace",
                move_type="demote_weak_outer_capacity_to_picnic_terrace",
                geometry=f"{rows_lbl(groups['overflow'])} (Band C)",
                site_reasons=[self.site["rake"]],
                performance_reasons=["C 30-60mm: overflow/standing only, not fixed seating"],
                civic_reasons=["informal overflow edge for big events"],
                cost={"cut_cy": 0.0, "fill_cy": 0.0, "gross_cy": 0.0},
                effects={"informal_capacity": f"+{seats(groups['overflow'])}"},
                positive_criteria=["turns_fragment_into_landscape", "adds_daily_nonevent_value"],
                rejection_if_removed=["weak rows masquerade as seating"],
                status="accepted"))
        if groups["overlook"]:
            moves.append(Move(
                move_id=f"{family}_dissolve_tips",
                move_type="convert_clipped_tip_to_overlook",
                geometry=f"{rows_lbl(groups['overlook'])} clipped tips → overlook/landscape",
                site_reasons=[self.site["tips"], self.site["view"]],
                performance_reasons=["removes false formal capacity from clipped single-section geometry"],
                civic_reasons=["edge dissolves into overlook instead of broken seating"],
                cost={"cut_cy": 0.0, "fill_cy": 0.0, "gross_cy": 0.0},
                effects={"visual_legibility": "increased", "informal_capacity": f"+{seats(groups['overlook'])}"},
                positive_criteria=["turns_fragment_into_landscape", "preserves_bay_view",
                                   "creates_useful_edge_or_landing"],
                rejection_if_removed=["clipped fragments masquerade as formal seats"],
                status="accepted"))

        # always-on view guard
        moves.append(Move(
            move_id=f"{family}_preserve_view",
            move_type="preserve_open_upstage_view",
            geometry="stage upstage, view corridor to bay",
            site_reasons=[self.site["view"], self.site["hinge"]],
            performance_reasons=["keeps open-air character; no enclosure to drain/heat"],
            civic_reasons=["the view is the set; an open-air venue, not a fake room"],
            cost={"cut_cy": 0.0, "fill_cy": 0.0, "gross_cy": 0.0},
            effects={"blocks_view": False, "visual_legibility": "increased"},
            positive_criteria=["preserves_bay_view", "clarifies_seating_bowl"],
            rejection_if_removed=["an upstage wall could creep in and kill the bay axis"],
            status="accepted"))

        # optional composed surfaces (lift ledgers toward a cost-proxy design)
        if pol["framing"]:
            moves.append(Move(
                move_id=f"{family}_lateral_frame",
                move_type="frame_stage_laterally_without_blocking_bay",
                geometry="side-stage planting/berms, upstage open",
                site_reasons=[self.site["hinge"], self.site["view"]],
                performance_reasons=["wind/acoustic side enclosure without blocking the corridor"],
                civic_reasons=["ceremonial framing of the open-air room"],
                cost={"cut_cy": 0.0, "fill_cy": 0.0, "gross_cy": 0.0},
                effects={"blocks_view": False, "stage_presence": "increased"},
                positive_criteria=["preserves_bay_view", "creates_useful_edge_or_landing"],
                rejection_if_removed=["stage reads as unanchored on the flat pan"],
                status="accepted"))
        omits = []
        if pol["access"]:
            moves.append(Move(
                move_id=f"{family}_processional_access",
                move_type="bend_access_route_with_contour",
                geometry="switchback ramp + cross-aisle landings on contour",
                site_reasons=[self.site["rake"], self.site["hinge"]],
                performance_reasons=["ADA running slope <=8.33%", "wheelchair dispersion at landings"],
                civic_reasons=pol["character"] + ["arrival reveals the bowl and bay progressively"],
                cost={"cut_cy": 0.0, "fill_cy": 0.0, "gross_cy": 0.0},
                effects={"access_quality": "increased", "informal_capacity": "increase"},
                positive_criteria=["improves_access", "uses_existing_contour",
                                   "creates_useful_edge_or_landing", "adds_daily_nonevent_value"],
                rejection_if_removed=["access becomes a compliance scar", "no wheelchair dispersion"],
                cost_status="placeholder", validation_status="intent_only",
                may_satisfy=["processional_clarity"],
                may_not_satisfy=["ADA_pass", "earthwork_cost_proxy"],
                status="accepted"))
        else:
            omits.append("ADA")
        if pol["drainage"]:
            moves.append(Move(
                move_id=f"{family}_swale_garden",
                move_type="use_swale_as_planted_room_edge",
                geometry="cross-aisle swales feeding the treatment cell garden",
                site_reasons=[self.site["drain"], self.site["rake"]],
                performance_reasons=["intercepts runoff behind lower rows", "treads shed to swales, no ponding"],
                civic_reasons=pol["character"] + ["drainage reads as a planted landscape room edge"],
                cost={"cut_cy": 0.0, "fill_cy": 0.0, "gross_cy": 0.0},
                effects={"drainage_risk": "reduced", "ecological_fit": "increased"},
                positive_criteria=["improves_drainage", "creates_useful_edge_or_landing",
                                   "turns_fragment_into_landscape"],
                rejection_if_removed=["clipped/lower rows pond", "treatment cell reads as leftover ditch"],
                cost_status="placeholder", validation_status="intent_only",
                may_satisfy=["drainage_legibility"],
                may_not_satisfy=["drainage_pass", "earthwork_cost_proxy"],
                status="accepted"))
        else:
            omits.append("drainage")

        formal_seats = seats(groups["formal"])
        return Design(
            scenario=f"{family} — {pol['blurb']}",
            moves=moves,
            claims={"formal_seats_claimed": formal_seats},
            surfaces_classified=True,
            omits_required_surfaces=omits,
            stage=pol["stage"],
        )

    def generate_all(self) -> dict:
        return {fam: self.generate(fam) for fam in FAMILIES}
