#!/usr/bin/env python3
"""Gate a captured site-furniture proposal (Phase 1, Task 3).

The decision surface for additive furniture. Reads a proposal GeoJSON (from
`scripts/capture_furniture.py`), the prop catalog, and the committed constraint
layers, and refuses anything that would (B1) fall outside the site, (B2) sit on a
surface its class is not allowed on, (B3) collide with the ADA clear route, the
stage deck, or seating, (B4) crowd another prop or exceed a class count, or (B5)
carry broken identity/provenance. Exit 0 = every prop passes; exit 1 = at least
one blocked (each printed with a reason); exit 2 = a required constraint layer is
missing (**fail closed** — an unverifiable proposal is never passed).

Pure stdlib: point-in-polygon (ray casting), point-to-segment distance, and a
monotone-chain convex hull are implemented here. All geometry is done in LOCAL
ENU METRES (EPSG:6494 ft -> metres via civicbowl_common.ft_xy_to_enu) so distances
compare directly against the catalog's metre footprints and spacings.

Planning-grade, additive, non-authoritative on its own: a PASS makes a proposal
eligible for a maintainer to fold in; it is NOT a civil/code ADA determination
(the ADA corridor here is a planning-grade keep-clear, not a compliance check).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "unreal"))
import civicbowl_common as CB          # noqa: E402
import validate_prop_catalog as VC     # noqa: E402

REPO = os.path.dirname(_HERE)
GEO = os.path.join(REPO, "unreal_export", "geo")

# Planning-grade keep-clear corridor half-width around an ADA route centreline
# (~3 ft each side). NOT a code determination — ADA remains concept pending civil
# detailing (docs/unreal_handoff_v1.md §4). Tunable when a real clear-width lands.
ADA_CORRIDOR_HALF_WIDTH_M = 0.915
# How far outside the derived design hull a prop may still count as "on site".
SITE_MARGIN_M = 3.0
STAGE_DECK_ZONES = {"stage_core", "stage_shoulder_left", "stage_shoulder_right"}


# ── geometry (stdlib, metres) ────────────────────────────────────────────────
def to_m(xy_ft: list[float]) -> tuple[float, float]:
    return CB.ft_xy_to_enu(xy_ft[0], xy_ft[1])


def rings_m(geometry: dict) -> list[list[tuple[float, float]]]:
    """Exterior rings of a Polygon/MultiPolygon, in metres (holes ignored —
    conservative for a keep-clear gate)."""
    t = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if t == "Polygon":
        polys = [coords]
    elif t == "MultiPolygon":
        polys = coords
    else:
        return []
    out = []
    for poly in polys:
        if poly:
            out.append([to_m(pt) for pt in poly[0]])
    return out


def lines_m(geometry: dict) -> list[list[tuple[float, float]]]:
    t = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if t == "LineString":
        return [[to_m(pt) for pt in coords]]
    if t == "MultiLineString":
        return [[to_m(pt) for pt in ln] for ln in coords]
    return []


def point_in_ring(p: tuple[float, float], ring: list[tuple[float, float]]) -> bool:
    x, y = p
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xint = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xint:
                inside = not inside
    return inside


def seg_dist(p, a, b) -> float:
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def dist_to_ring(p, ring) -> float:
    return min(seg_dist(p, ring[i], ring[(i + 1) % len(ring)]) for i in range(len(ring)))


def dist_to_line(p, line) -> float:
    if len(line) == 1:
        return math.hypot(p[0] - line[0][0], p[1] - line[0][1])
    return min(seg_dist(p, line[i], line[i + 1]) for i in range(len(line) - 1))


def hits_polys(p, polys, clearance) -> bool:
    """True if p is inside any ring, or within `clearance` of any edge."""
    for ring in polys:
        if len(ring) >= 3 and point_in_ring(p, ring):
            return True
        if ring and dist_to_ring(p, ring) < clearance:
            return True
    return False


def hits_lines(p, lines, clearance) -> bool:
    return any(line and dist_to_line(p, line) < clearance for line in lines)


def convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def footprint_radius(cls: dict) -> float:
    return max((math.hypot(x, y) for x, y in cls.get("footprint", [])), default=0.0)


# ── the gate ─────────────────────────────────────────────────────────────────
def validate(proposal: dict, catalog: dict, constraints: dict, surfaces: dict,
             site_hull: list[tuple[float, float]]) -> tuple[list[str], list[str]]:
    """Return (blocking_reasons, warnings). Empty blocking list == PASS."""
    reasons: list[str] = []
    warns: list[str] = []
    by_class = {c["object_class"]: c for c in catalog.get("classes", [])}

    feats = proposal.get("features", [])
    # B5 (collection-level): unique feature_ids
    ids = [(f.get("properties") or {}).get("feature_id") for f in feats]
    dupes = {i for i in ids if i and ids.count(i) > 1}
    for d in sorted(dupes):
        reasons.append(f"B5 {d}: feature_id is not unique in the proposal")

    placed: list[tuple[str, tuple[float, float]]] = []
    counts: dict[str, int] = {}
    for f in feats:
        pr = f.get("properties") or {}
        fid = pr.get("feature_id") or "<no-id>"
        oc = pr.get("object_class")
        p = to_m(f.get("geometry", {}).get("coordinates", [0, 0]))

        # B5 identity/provenance
        if not pr.get("feature_id"):
            reasons.append(f"B5 {fid}: missing feature_id")
        if oc not in by_class:
            reasons.append(f"B5 {fid}: object_class {oc!r} not in catalog")
            continue
        if not ((pr.get("@review") or {}).get("base_build_git_commit")):
            reasons.append(f"B5 {fid}: missing @review.base_build_git_commit")
        cls = by_class[oc]
        r = footprint_radius(cls)
        counts[oc] = counts.get(oc, 0) + 1

        # B1 in-boundary (inside the hull, or within the site margin of it)
        if site_hull:
            inside = len(site_hull) >= 3 and point_in_ring(p, site_hull)
            near = dist_to_ring(p, site_hull) <= SITE_MARGIN_M if len(site_hull) >= 2 else False
            if not (inside or near):
                reasons.append(f"B1 {fid}: outside the site boundary")

        # B2 place_on surface
        surface = "context_ground"
        if hits_polys(p, surfaces.get("stage_floor", []), 0.0):
            surface = "stage_floor"
        elif hits_polys(p, surfaces.get("terrace_tread", []), 0.0):
            surface = "terrace_tread"
        if surface not in (cls.get("place_on") or []):
            reasons.append(f"B2 {fid}: sits on {surface!r} but {oc} may only be "
                           f"placed on {cls.get('place_on')}")

        # B3 keep-clear collisions
        for kc in cls.get("keep_clear_of") or []:
            src = constraints.get(kc)
            if src is None:
                warns.append(f"B3 {fid}: keep_clear_of {kc!r} NOT evaluated — no "
                             f"constraint layer for it in the package")
                continue
            if src["kind"] == "lines":
                if hits_lines(p, src["geom"], r + ADA_CORRIDOR_HALF_WIDTH_M):
                    reasons.append(f"B3 {fid}: intrudes the {kc} planning-grade "
                                   "keep-clear corridor")
            elif hits_polys(p, src["geom"], r):
                reasons.append(f"B3 {fid}: collides with {kc}")

        placed.append((oc, p))

    # B4 spacing + count
    for i in range(len(placed)):
        oci, pi = placed[i]
        spacing = by_class[oci].get("min_spacing_m", 0)
        for j in range(i + 1, len(placed)):
            ocj, pj = placed[j]
            if oci == ocj and math.hypot(pi[0] - pj[0], pi[1] - pj[1]) < spacing:
                reasons.append(f"B4 {oci}: two props closer than min_spacing_m "
                               f"({spacing} m)")
                break
    for oc, n in counts.items():
        mx = by_class[oc].get("max_count")
        if mx is not None and n > mx:
            reasons.append(f"B4 {oc}: {n} placed exceeds max_count {mx}")

    return reasons, warns


# ── file loading (fail closed) ───────────────────────────────────────────────
def load_constraints(geo_dir: str = GEO) -> tuple[dict, dict, list, list[str]]:
    """Build constraints/surfaces/site_hull from the committed layers.
    Returns (constraints, surfaces, site_hull, missing_files)."""
    need = {"ada": "ada_route.geojson", "seating": "seating_rows.geojson",
            "stage": "stage_floor.geojson"}
    missing = [v for v in need.values() if not os.path.exists(os.path.join(geo_dir, v))]
    if missing:
        return {}, {}, [], missing

    def feats(name):
        return json.load(open(os.path.join(geo_dir, name))).get("features", [])

    ada_lines = [ln for f in feats("ada_route.geojson") for ln in lines_m(f["geometry"])]
    seating = [r for f in feats("seating_rows.geojson") for r in rings_m(f["geometry"])]
    stage_feats = feats("stage_floor.geojson")
    # The stage DECK (structural stage zones) is both a keep-clear constraint and
    # the only real "stage_floor" placement surface. The concept event-floor /
    # treatment-cell polygons are NOT placement surfaces — they are concept-tier
    # and geometrically overlap the seating bowl, so classing them as stage_floor
    # would mislabel a prop that is really on a seating tread. They still count
    # toward the site extent (hull) below.
    stage_deck = [r for f in stage_feats
                  if (f.get("properties") or {}).get("zone") in STAGE_DECK_ZONES
                  for r in rings_m(f["geometry"])]
    stage_all = [r for f in stage_feats for r in rings_m(f["geometry"])]

    constraints = {
        "ada_route": {"kind": "lines", "geom": ada_lines},
        "seating_tread": {"kind": "polys", "geom": seating},
        "stage_deck": {"kind": "polys", "geom": stage_deck},
        # "egress": intentionally absent — no egress layer in the package yet; the
        # gate reports it as uncheckable rather than silently passing it.
    }
    surfaces = {"terrace_tread": seating, "stage_floor": stage_deck}
    hull_pts = [pt for ring in (seating + stage_all) for pt in ring]
    hull_pts += [pt for line in ada_lines for pt in line]
    site_hull = convex_hull(hull_pts)
    return constraints, surfaces, site_hull, []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("proposal", help="furniture proposal GeoJSON (from capture_furniture.py)")
    ap.add_argument("--catalog", default=VC.CATALOG)
    ap.add_argument("--geo", default=GEO, help="constraint-layer directory")
    args = ap.parse_args(argv)

    for pth, what in ((args.proposal, "proposal"), (args.catalog, "catalog")):
        if not os.path.exists(pth):
            print(f"FATAL: {what} not found: {pth}", file=sys.stderr)
            return 2
    proposal = json.load(open(args.proposal))
    catalog = json.load(open(args.catalog))
    if VC.validate(catalog):
        print("FATAL: catalog invalid — run scripts/validate_prop_catalog.py", file=sys.stderr)
        return 2

    constraints, surfaces, site_hull, missing = load_constraints(args.geo)
    if missing:
        print("FAIL  cannot evaluate — required constraint layer(s) missing "
              f"(fail closed): {', '.join(missing)}")
        return 2

    reasons, warns = validate(proposal, catalog, constraints, surfaces, site_hull)
    rel = os.path.relpath(args.proposal, REPO)
    for w in warns:
        print(f"  ! {w}")
    if reasons:
        print(f"FAIL  {rel} — {len(reasons)} prop(s) blocked:")
        for r in reasons:
            print(f"  • {r}")
        return 1
    n = len(proposal.get("features", []))
    print(f"PASS  {rel} — {n} prop(s) clear (boundary / surface / keep-clear / "
          "spacing / identity)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
