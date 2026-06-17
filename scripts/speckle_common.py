#!/usr/bin/env python3
"""Shared core for the Speckle review-object bridge.

This module is the single source of truth for how the *validated* Unreal handoff
package (``unreal_export/``) is reshaped into Speckle-ready review objects, and
for the object-truth boundary that the exporter and the publisher both enforce.

Boundary (see README "Speckle review boundary"):

  The GIS/design repo + its Python/QGIS gates are the ONLY acceptance authority.
  Speckle is a review / comparison / collaboration surface. Nothing rendered in
  Speckle is design truth. This bridge therefore:

    * READS unreal_export/ (which is itself downstream of the gates) and never
      recomputes a validated quantity — C-values, seat counts, ADA status,
      cut/fill, and the planning-grade warnings are copied verbatim;
    * carries full provenance on every leaf object (source_file + feature_id +
      a derived row_id join key) so any review object traces back to canon;
    * keeps provisional / concept tiers individually flagged (must_label) so a
      reviewer cannot silently promote them;
    * renders geometry in the local ENU-metre frame (viewer float precision)
      while retaining the lossless EPSG:6494 source coordinates in properties.

Stdlib only. No third-party imports, no network. ``publish_speckle.py`` is the
only place ``specklepy`` is (lazily) touched, and only on an explicit --publish.
"""
from __future__ import annotations

import json
import os
from typing import Any

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_DIR = os.path.join(REPO, "unreal_export")
OUT_DIR = os.path.join(REPO, "speckle_export")

SCHEMA = "speckle-review-bridge/0.1"

# ── coordinate contract (must match unreal_export / README_UNREAL.md §3) ──────
# Prefer the governing constants module; fall back to the committed canon so a
# fresh checkout without the geometry deps still produces an identical frame.
import sys

sys.path.insert(0, os.path.join(REPO, "scripts"))
try:  # pragma: no cover - exercised only when in_situ_common imports cleanly
    import in_situ_common as _C  # noqa: E402

    ORIGIN_X, ORIGIN_Y = _C.CX, _C.CY
    _CONST_SOURCE = "scripts/in_situ_common.py"
except Exception as _exc:  # noqa: BLE001 - deliberate broad fallback
    ORIGIN_X, ORIGIN_Y = 19533067.7, 750799.2
    _CONST_SOURCE = f"fallback canon (in_situ_common import failed: {_exc})"

FT2M = 0.3048  # exact: EPSG:6494 is INTERNATIONAL feet (docs/datum_note.md)

# Speckle project (formerly "stream") slug. One project for the venue.
SPECKLE_PROJECT_SLUG = "petoskey-pit-civic-bowl"

# Accepted/proposal/reference are the three review states. The branch (Speckle
# v3: "model") name encodes the state in its prefix; the publisher refuses to
# send a payload whose acceptance.state disagrees with the branch prefix.
STATE_ACCEPTED = "accepted"
STATE_PROPOSAL = "proposal"
STATE_REFERENCE = "reference"
VALID_STATES = (STATE_ACCEPTED, STATE_PROPOSAL, STATE_REFERENCE)

# The default accepted bundle is the validated Scenario E baseline.
DEFAULT_ACCEPTED_BRANCH = "accepted/scenario-e-baseline"

# The four load-bearing caveats that must survive into every published bundle
# (mirrors verify_unreal_export.py gate G).
REQUIRED_WARNING_TOKENS = ("PLANNING-GRADE", "Rule 9", "INTERNATIONAL feet", "understate")

# Required review/validation fields per object class. "missing validation
# fields" → the payload is not publishable. Provenance fields (source_file,
# feature_id) are required on EVERY leaf and checked separately.
PROVENANCE_FIELDS = ("source_file", "feature_id")
REQUIRED_REVIEW_FIELDS = {
    "seating_row": (
        "row_id", "section", "row", "seats_kept",
        "C_mm", "C_bar_mm", "band_status", "sightline_verdict",
        "cutfill_mean_ft", "cutfill_min_ft", "cutfill_max_ft",
    ),
    "stage_feature": ("role", "rule9_status", "provisional", "concept_tier"),
    "ada_route": ("ada_status", "design_grade_pct", "length_ft"),
    "ada_node": ("node_kind", "design_grade_pct"),
    "reference": (),  # axis / focal point / cameras / terrain carry no validation gate
}

# Keys whose presence is required but whose value may legitimately be null
# (e.g. a front row has no C_mm; only the stage *deck* carries rule9_status —
# the event floor / treatment cell / reference axes do not). validate_payload
# checks the KEY exists; emptiness is allowed for these.
NULLABLE_REVIEW_FIELDS = {"C_mm", "cutfill_mean_ft", "cutfill_min_ft", "cutfill_max_ft",
                          "design_grade_pct", "rule9_status"}


# ── geometry transform ───────────────────────────────────────────────────────
def epsg6494_ft_to_local_m(x_ft: float, y_ft: float, z_navd88_ft: float) -> list[float]:
    """EPSG:6494 intl-ft easting/northing + NAVD88 ft -> local ENU metres.

    Inverse of README_UNREAL.md §3. Recentres on the canon origin so the Speckle
    viewer (single-precision, like Unreal) does not lose the ~19.5e6 ft easting.
    """
    return [
        (x_ft - ORIGIN_X) * FT2M,
        (y_ft - ORIGIN_Y) * FT2M,
        (z_navd88_ft or 0.0) * FT2M,
    ]


def local_m_to_epsg6494_ft(x_m: float, y_m: float, z_m: float) -> list[float]:
    """Exact reverse of :func:`epsg6494_ft_to_local_m` (round-trip check)."""
    return [
        x_m / FT2M + ORIGIN_X,
        y_m / FT2M + ORIGIN_Y,
        z_m / FT2M,
    ]


def _ring_to_local(coords: list, z_ft: float) -> list[float]:
    """Flatten a GeoJSON LineString / Polygon-outer-ring to a Speckle Polyline
    ``value`` array [x,y,z, x,y,z, ...] in local metres."""
    flat: list[float] = []
    for pt in coords:
        lx, ly, lz = epsg6494_ft_to_local_m(pt[0], pt[1], z_ft)
        flat.extend([lx, ly, lz])
    return flat


# ── Speckle object factories (plain dicts; the publisher rebuilds Base) ───────
def _polyline(value: list[float], closed: bool, app_id: str) -> dict[str, Any]:
    return {
        "speckle_type": "Objects.Geometry.Polyline",
        "units": "m",
        "applicationId": app_id,
        "closed": closed,
        "value": value,
    }


def _point(x_ft: float, y_ft: float, z_ft: float, app_id: str) -> dict[str, Any]:
    lx, ly, lz = epsg6494_ft_to_local_m(x_ft, y_ft, z_ft)
    return {
        "speckle_type": "Objects.Geometry.Point",
        "units": "m",
        "applicationId": app_id,
        "x": lx, "y": ly, "z": lz,
    }


def collection(name: str, elements: list[dict], collection_type: str = "layer",
               **extra: Any) -> dict[str, Any]:
    base = {
        "speckle_type": "Objects.Organization.Collection",
        "name": name,
        "collectionType": collection_type,
        "@elements": elements,
    }
    base.update(extra)
    return base


def review_object(geometry: dict, name: str, review: dict, geo_epsg6494: dict) -> dict[str, Any]:
    """A leaf review object: renderable geometry + the verbatim validation/
    provenance block + the lossless EPSG:6494 source geometry.

    ``review`` and the source geometry are detached (``@`` prefix) so they ride
    with the object on the server and are inspectable in the Speckle viewer.
    """
    obj = dict(geometry)  # the geometry IS the object (so it renders)
    obj["name"] = name
    obj["@review"] = review
    obj["@geo_epsg6494"] = geo_epsg6494
    return obj


# ── IO ────────────────────────────────────────────────────────────────────────
def jload(path: str) -> Any:
    with open(path) as fh:
        return json.load(fh)


def load_export(export_dir: str = EXPORT_DIR) -> dict[str, Any]:
    """Load the validated unreal_export artifacts this bridge consumes."""
    g = lambda rel: jload(os.path.join(export_dir, rel))
    return {
        "seating_rows": g("geo/seating_rows.geojson"),
        "seating_splines": g("geo/seating_row_splines.geojson"),
        "stage_floor": g("geo/stage_floor.geojson"),
        "ada_route": g("geo/ada_route.geojson"),
        "provenance": g("manifests/provenance.json"),
        "materials": g("manifests/material_manifest.json"),
        "cameras": g("manifests/camera_manifest.json"),
    }


# ── validation (the object-truth boundary, enforced) ──────────────────────────
def _iter_leaves(payload: dict[str, Any]):
    """Yield every leaf review object (anything carrying an @review block)."""
    for coll in payload.get("@elements", []):
        for el in coll.get("@elements", []):
            if "@review" in el:
                yield coll.get("name"), el


def validate_payload(payload: dict[str, Any], *, require_source_exists: bool = True,
                     repo: str = REPO) -> list[str]:
    """Return a list of blocking errors. Empty list == publishable.

    Enforces, independent of the live gate:
      * root carries the verbatim planning-grade warnings (all four caveats);
      * root acceptance.state is a known state and matches the branch prefix;
      * every leaf has provenance (source_file that EXISTS + non-empty feature_id);
      * every leaf has the required validation fields for its object class;
      * ADA route status is never strengthened past 'concept'/'pending'.
    """
    errs: list[str] = []

    # root: warnings present + verbatim caveats
    warnings = payload.get("warnings") or []
    if not warnings:
        errs.append("root: warnings block is empty (planning-grade caveats dropped)")
    blob = " ".join(warnings)
    for tok in REQUIRED_WARNING_TOKENS:
        if tok not in blob:
            errs.append(f"root: required warning token missing: {tok!r}")

    # root: acceptance state + branch agreement
    acc = payload.get("acceptance") or {}
    state = acc.get("state")
    branch = acc.get("branch")
    if state not in VALID_STATES:
        errs.append(f"root: acceptance.state {state!r} not in {VALID_STATES}")
    if branch:
        prefix = branch.split("/", 1)[0]
        if prefix != state:
            errs.append(
                f"root: branch {branch!r} prefix {prefix!r} disagrees with "
                f"acceptance.state {state!r}")

    # leaves: provenance + validation fields
    n_leaves = 0
    for coll_name, leaf in _iter_leaves(payload):
        n_leaves += 1
        rv = leaf.get("@review") or {}
        oc = rv.get("object_class", "?")
        tag = f"{coll_name}/{rv.get('feature_id', leaf.get('name', '?'))}"

        for pf in PROVENANCE_FIELDS:
            val = rv.get(pf)
            if not val:
                errs.append(f"{tag}: missing provenance field {pf!r}")
            elif pf == "source_file" and require_source_exists:
                if not os.path.exists(os.path.join(repo, val)):
                    errs.append(f"{tag}: source_file does not exist: {val}")

        req = REQUIRED_REVIEW_FIELDS.get(oc)
        if req is None:
            errs.append(f"{tag}: unknown object_class {oc!r}")
            continue
        for field in req:
            if field not in rv:
                errs.append(f"{tag}: missing validation field {field!r} (class {oc})")
            elif rv[field] in (None, "") and field not in NULLABLE_REVIEW_FIELDS:
                errs.append(f"{tag}: validation field {field!r} is empty (class {oc})")

        # ADA status must not be strengthened past concept/pending
        if oc == "ada_route":
            s = (rv.get("ada_status") or "")
            low = s.lower()
            if s and "concept" not in low and "pending" not in low:
                errs.append(f"{tag}: ADA status strengthened past concept/pending: {s!r}")

        # a Rule-9-OPEN stage deck must stay flagged provisional (cannot be
        # promoted to accepted truth by inclusion in the bundle)
        if oc == "stage_feature" and rv.get("rule9_status") == "open" \
                and not rv.get("provisional"):
            errs.append(f"{tag}: Rule-9-open stage feature not flagged provisional")

    if n_leaves == 0:
        errs.append("payload has no review leaves (nothing to publish)")

    return errs


def branch_for_state(state: str, topic: str | None, date_compact: str | None) -> str:
    """Derive the conventional branch/model name for a review state."""
    if state == STATE_ACCEPTED:
        return DEFAULT_ACCEPTED_BRANCH
    if state == STATE_REFERENCE:
        return f"reference/{topic or 'context'}"
    # proposal
    t = topic or "untitled"
    return f"proposal/{t}-{date_compact}" if date_compact else f"proposal/{t}"
