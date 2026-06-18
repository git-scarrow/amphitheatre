#!/usr/bin/env python3
"""Compare two Speckle review payloads (typically accepted vs proposal).

Works on the local ``speckle_export/*.speckle.json`` payloads (the same artifacts
publish_speckle.py sends) — no live server needed, though a payload reconstructed
from Speckle metadata has the same shape and compares identically. The diff is
object-identity based, not a geometry-mesh diff: objects are matched by a stable
key per class (seating rows by ``row_id``, everything else by ``feature_id``), and
"changed" means a tracked review field or the lossless source geometry differs.

Reports:
  * added / removed object counts by object_class;
  * changed seating row ids (and which fields moved);
  * changed ADA route ids;
  * changed stage / floor objects;
  * validation deltas (seat totals, warnings, boundary errors, leaf counts);
  * unresolved decisions on each side.

    python scripts/speckle_compare.py \
        --accepted speckle_export/petoskey_pit.accepted.speckle.json \
        --proposal speckle_export/petoskey_pit.proposal.speckle.json
    python scripts/speckle_compare.py --accepted A.json --proposal B.json --json

Stdlib only. No network. Read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import speckle_common as S  # noqa: E402
import speckle_ledger as L  # noqa: E402

# Tracked fields per object class — a change in any of these marks the object as
# "changed". Geometry is compared separately via the lossless @geo_epsg6494 hash.
TRACKED_FIELDS = {
    "seating_row": ("seats_kept", "C_mm", "C_bar_mm", "band_status",
                    "sightline_verdict", "sees_bay", "cutfill_mean_ft",
                    "proposed_elev_navd88_ft"),
    "ada_route": ("ada_status", "route_class", "design_grade_pct", "length_ft",
                  "drop_ft", "preferred", "from", "to"),
    "ada_node": ("node_kind", "design_grade_pct", "crossing"),
    "stage_feature": ("role", "rule9_status", "provisional", "concept_tier",
                      "blocks_bay_view", "max_structure_height_ft", "az_deg"),
    "reference": ("ref_kind", "look_azimuth_deg", "fov_deg", "eye_height_ft"),
}


def _identity(rv: dict) -> str:
    """Stable per-object key. Seating rows join on row_id (the sightline band key);
    everything else on feature_id."""
    if rv.get("object_class") == "seating_row" and rv.get("row_id"):
        return f"row:{rv['row_id']}"
    return f"fid:{rv.get('feature_id')}"


def _geo_hash(leaf: dict) -> str:
    """Hash of the lossless EPSG:6494 source geometry, rounded so float jitter
    below ~1e-3 ft does not register as a change."""
    geo = leaf.get("@geo_epsg6494") or {}
    coords = geo.get("coordinates")

    def rnd(x):
        if isinstance(x, (int, float)):
            return round(float(x), 3)
        if isinstance(x, list):
            return [rnd(v) for v in x]
        return x

    blob = json.dumps([geo.get("type"), rnd(coords), rnd(geo.get("z_navd88_ft"))],
                      sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def _index(payload: dict) -> dict[str, dict]:
    """{identity: {rv, leaf, class, geo_hash}} over every leaf."""
    idx: dict[str, dict] = {}
    for _coll, leaf in S._iter_leaves(payload):
        rv = leaf.get("@review") or {}
        idx[_identity(rv)] = {"rv": rv, "class": rv.get("object_class"),
                              "geo_hash": _geo_hash(leaf),
                              "name": rv.get("name") or rv.get("feature_id")}
    return idx


def _seat_total(payload: dict) -> int:
    total = 0
    for _coll, leaf in S._iter_leaves(payload):
        rv = leaf.get("@review") or {}
        if rv.get("object_class") == "seating_row":
            n = rv.get("seats_kept")
            if isinstance(n, (int, float)):
                total += int(n)
    return total


def _class_counts(idx: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for v in idx.values():
        counts[v["class"]] = counts.get(v["class"], 0) + 1
    return counts


def _field_changes(a_rv: dict, b_rv: dict, oc: str) -> dict:
    changes = {}
    for f in TRACKED_FIELDS.get(oc, ()):
        if a_rv.get(f) != b_rv.get(f):
            changes[f] = [a_rv.get(f), b_rv.get(f)]
    return changes


def compare_payloads(accepted: dict, proposal: dict) -> dict:
    """Structured diff. ``accepted`` is the baseline ('a'), ``proposal`` the new
    side ('b')."""
    ai, bi = _index(accepted), _index(proposal)
    a_keys, b_keys = set(ai), set(bi)

    added_keys = b_keys - a_keys
    removed_keys = a_keys - b_keys
    common = a_keys & b_keys

    # added/removed counts by class
    def by_class(keys, idx):
        out: dict[str, int] = {}
        for k in keys:
            c = idx[k]["class"]
            out[c] = out.get(c, 0) + 1
        return out

    changed: dict[str, list[dict]] = {}  # object_class -> list of change records
    for k in sorted(common):
        a, b = ai[k], bi[k]
        oc = a["class"] or b["class"]
        fc = _field_changes(a["rv"], b["rv"], oc)
        geo_changed = a["geo_hash"] != b["geo_hash"]
        if fc or geo_changed:
            changed.setdefault(oc, []).append({
                "identity": k,
                "name": b["name"],
                "fields": fc,
                "geometry_changed": geo_changed,
            })

    val_a = {
        "leaves": sum(_class_counts(ai).values()),
        "seat_total": _seat_total(accepted),
        "warnings": len(accepted.get("warnings") or []),
        "boundary_errors": len(S.validate_payload(accepted, require_source_exists=False)),
    }
    val_b = {
        "leaves": sum(_class_counts(bi).values()),
        "seat_total": _seat_total(proposal),
        "warnings": len(proposal.get("warnings") or []),
        "boundary_errors": len(S.validate_payload(proposal, require_source_exists=False)),
    }
    validation_delta = {k: [val_a[k], val_b[k], val_b[k] - val_a[k]] for k in val_a}

    return {
        "accepted": {
            "branch": (accepted.get("acceptance") or {}).get("branch"),
            "git_commit": (accepted.get("bridge") or {}).get("git_commit"),
            "class_counts": _class_counts(ai),
        },
        "proposal": {
            "branch": (proposal.get("acceptance") or {}).get("branch"),
            "git_commit": (proposal.get("bridge") or {}).get("git_commit"),
            "class_counts": _class_counts(bi),
        },
        "added_by_class": by_class(added_keys, bi),
        "removed_by_class": by_class(removed_keys, ai),
        "added": sorted(added_keys),
        "removed": sorted(removed_keys),
        "changed_rows": [c["identity"] for c in changed.get("seating_row", [])],
        "changed_ada_routes": [c["identity"] for c in changed.get("ada_route", [])],
        "changed_stage": [c["identity"] for c in changed.get("stage_feature", [])],
        "changed": changed,
        "validation_delta": validation_delta,
        "unresolved_decisions": {
            "accepted": L.derive_open_decisions(accepted),
            "proposal": L.derive_open_decisions(proposal),
        },
    }


def format_report(diff: dict) -> str:
    out: list[str] = []
    a, b = diff["accepted"], diff["proposal"]
    out.append("=== Speckle payload compare (accepted ← baseline · proposal → candidate) ===")
    out.append(f"  accepted: {a['branch']}  @ {a['git_commit']}")
    out.append(f"  proposal: {b['branch']}  @ {b['git_commit']}")

    out.append("\nadded objects by class:")
    out.append("  " + (", ".join(f"{k}+{v}" for k, v in sorted(diff["added_by_class"].items()))
                       or "(none)"))
    out.append("removed objects by class:")
    out.append("  " + (", ".join(f"{k}-{v}" for k, v in sorted(diff["removed_by_class"].items()))
                       or "(none)"))

    def _changes_block(title, oc):
        recs = diff["changed"].get(oc, [])
        out.append(f"\nchanged {title} ({len(recs)}):")
        if not recs:
            out.append("  (none)")
        for r in recs:
            bits = []
            for f, (av, bv) in r["fields"].items():
                bits.append(f"{f}: {av} → {bv}")
            if r["geometry_changed"]:
                bits.append("geometry moved")
            out.append(f"  · {r['name']}  [{r['identity']}]  " + "; ".join(bits))

    _changes_block("seating rows", "seating_row")
    _changes_block("ADA routes", "ada_route")
    _changes_block("ADA nodes", "ada_node")
    _changes_block("stage/floor objects", "stage_feature")

    out.append("\nvalidation deltas (accepted, proposal, Δ):")
    for k, (av, bv, d) in diff["validation_delta"].items():
        sign = f"{d:+d}" if isinstance(d, int) else d
        out.append(f"  {k:16} {av} → {bv}  ({sign})")

    out.append("\nunresolved decisions:")
    out.append(f"  accepted ({len(diff['unresolved_decisions']['accepted'])}):")
    for d in diff["unresolved_decisions"]["accepted"]:
        out.append(f"    - {d}")
    out.append(f"  proposal ({len(diff['unresolved_decisions']['proposal'])}):")
    for d in diff["unresolved_decisions"]["proposal"]:
        out.append(f"    - {d}")
    return "\n".join(out)


def _load(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--accepted", default=os.path.join(S.OUT_DIR,
                    "petoskey_pit.accepted.speckle.json"),
                    help="baseline payload (default: the accepted bundle)")
    ap.add_argument("--proposal", default=os.path.join(S.OUT_DIR,
                    "petoskey_pit.proposal.speckle.json"),
                    help="candidate payload to compare against the baseline")
    ap.add_argument("--json", action="store_true", help="emit raw JSON diff")
    args = ap.parse_args(argv)

    for label, path in (("accepted", args.accepted), ("proposal", args.proposal)):
        if not os.path.exists(path):
            print(f"FATAL: {label} payload not found: {path}\n"
                  f"  generate with: python scripts/export_speckle_payload.py "
                  f"--state {label}", file=sys.stderr)
            return 2

    diff = compare_payloads(_load(args.accepted), _load(args.proposal))
    if args.json:
        print(json.dumps(diff, indent=2, ensure_ascii=False))
    else:
        print(format_report(diff))
    return 0


if __name__ == "__main__":
    sys.exit(main())
