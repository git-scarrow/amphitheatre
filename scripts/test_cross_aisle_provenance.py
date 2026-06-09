"""Acceptance test: the cross-aisle is a ROW RECLASSIFICATION, not a seam/path discovery.

This pins the provenance, not just the geometry. The geometry was never the bug — the bug
was narrating a role reassignment (union(row9,row10).difference(retained)) as a seam search.
So the final assertions are cultural as much as technical: they force the system to stop
laundering a simple role reassignment through a more sophisticated story.

Run:  .venv/bin/python scripts/test_cross_aisle_provenance.py
Exits 0 on pass, raises AssertionError on the first violation. Requires that
scripts/scenarioE_civic.py has been run (reads its emitted geometry + validation).
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = Path(__file__).parent.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT / "scripts"))

EPS_AREA = 1.0          # sqft — "approximately zero" overlap / geometry mismatch
TREAD_HALF = 1.8        # must match scenarioE_civic.py
AISLE_ROWS = [9, 10]

geo = json.load(open(ROOT / "analysis/scenarioE_civic/geometry.geojson"))
val = json.load(open(ROOT / "analysis/scenarioE_civic/validation.json"))
bays = json.load(open(ROOT / "design_extended_bays/seating_bays.geojson"))

# emitted cross-aisle (the thing the plan actually draws)
xa_feats = [f for f in geo["features"] if f["properties"]["role"] == "cross_aisle"]
assert len(xa_feats) == 1, f"expected exactly one cross_aisle feature, got {len(xa_feats)}"
xa = xa_feats[0]; xa_geom = shape(xa["geometry"]); props = xa["properties"]

# regenerate the band from the SAME row object, via the SAME operation, independently
row_polys = {}
for feat in bays["features"]:
    p = feat["properties"]
    if p["kind"] == "seating" and 1 <= int(p["row"]) <= 18:
        row_polys.setdefault(int(p["row"]), []).append(
            shape(feat["geometry"]).buffer(TREAD_HALF, cap_style=2))
retained = unary_union([q for r in row_polys if r not in AISLE_ROWS for q in row_polys[r]])
regen = unary_union(row_polys[9] + row_polys[10]).difference(retained)

# 1. the emitted geometry equals union(row9,row10).difference(retained) within tolerance
#    (area-form of equals_exact: vertex order may differ, the set of points may not)
mismatch = xa_geom.symmetric_difference(regen).area
assert mismatch < EPS_AREA, (
    f"cross-aisle is not union(row9,row10).difference(retained): "
    f"symmetric-difference area {mismatch:.3f} sqft >= {EPS_AREA}")

# 2. displaced seats genuinely LEFT the capacity count
nominal = val["nominal_formal"]; displaced = val["displaced_by_cross_aisle"]; net = val["formal_seats_emitted"]
assert displaced > 0, "the aisle should displace seats; 0 displaced means it isn't over seating"
assert nominal - displaced == net, (
    f"displaced seats not removed from capacity: {nominal} nominal - {displaced} displaced "
    f"!= {net} net")

# 3. overlap with retained seating is approximately zero (0 by construction)
overlap = xa_geom.intersection(retained).area
assert overlap <= EPS_AREA, f"cross-aisle overlaps retained seating by {overlap:.3f} sqft"

# 4 & 5. provenance matches geometry — row-derived, NOT seam-derived. This is the point:
#        the move must SAY what operation created it, and may not relabel itself a path.
assert props["geometry_source"] == "row_reclassification", (
    f'geometry_source is {props["geometry_source"]!r}, must be "row_reclassification"')
assert props["seam_derived"] is False, (
    f'seam_derived is {props["seam_derived"]!r}, must be False (a reclassification is not a seam)')
assert props["operation"] == ["union_source_rows", "subtract_retained_seating", "assign_role:cross_aisle"], \
    f'operation does not record the actual generative steps: {props["operation"]}'

# 6. the ENGINE rejects a seam-laundered version — provenance failure is a hard rejection.
from harness.inevitability import Move, Design, InevitabilityEngine
eng = InevitabilityEngine({}, {})
def aisle_move(prov):
    return Move("xa", "reclassify_row_band_to_circulation", "band",
                site_reasons=["natural mid-bowl contour band"],
                performance_reasons=["creates cross-bowl circulation"],
                rejection_if_removed=["no mid-bowl access band"], provenance=prov)
hr_good = eng.hard_rejections(Design("good", [aisle_move(
    {"geometry_source": "row_reclassification", "seam_derived": False})]))
hr_bad = eng.hard_rejections(Design("bad", [aisle_move(
    {"geometry_source": "seam_search", "seam_derived": True})]))
assert not any("provenance must match geometry" in r or "seam_derived" in r for r in hr_good), \
    f"honest provenance was wrongly rejected: {hr_good}"
assert any("provenance must match geometry" in r for r in hr_bad), \
    "engine failed to reject a circulation move with non-row_reclassification provenance"
assert any("seam_derived" in r for r in hr_bad), \
    "engine failed to reject a circulation move claiming seam_derived=True"

print("PASS — cross-aisle provenance:")
print(f"  geometry == union(row9,row10).difference(retained)  (Δarea {mismatch:.3f} sqft)")
print(f"  capacity: {nominal} nominal - {displaced} displaced == {net} net")
print(f"  retained overlap {overlap:.3f} sqft  (<= {EPS_AREA})")
print(f"  geometry_source={props['geometry_source']!r}  seam_derived={props['seam_derived']}")
print(f"  engine rejects seam-laundered move: {[r for r in hr_bad if 'provenance' in r or 'seam' in r]}")
