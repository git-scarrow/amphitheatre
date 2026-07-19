#!/usr/bin/env python3
"""Deterministic generator + verifier for data/unreal_handoff_manifest.json.

The manifest is the machine-readable index for the Unreal handoff v1 package
(docs/unreal_handoff_v1.md): it ties each importable export layer to its
authoritative repo source, records a verifiable sha256 of every committed
package file, and carries the acceptance pointer (repo gates + publish ledger)
and the MCP-runway boundary.

It INVENTS nothing: CRS, units, the authoritative-source boundary, the
planning-grade warnings, and the source-file hashes are READ from
``unreal_export/manifests/provenance.json``; the acceptance pointer is READ from
``data/speckle_publish_ledger.json``. This script never writes to either, never
touches Speckle, and never rebuilds geometry.

Usage:
  python scripts/build_unreal_handoff_manifest.py          # (re)write the manifest
  python scripts/build_unreal_handoff_manifest.py --check   # verify, no write (CI/test)

Determinism: output is a pure function of the committed tree. No wall-clock
timestamp and no current-HEAD are baked in (the build provenance commit, which
is stable, is echoed instead), so regenerating on an unchanged tree is
byte-identical and ``--check`` is a true drift gate. Exit 0 = match / written,
1 = drift, 2 = missing input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROVENANCE = os.path.join(REPO, "unreal_export", "manifests", "provenance.json")
LEDGER = os.path.join(REPO, "data", "speckle_publish_ledger.json")
MANIFEST = os.path.join(REPO, "data", "unreal_handoff_manifest.json")

SCHEMA = "unreal-handoff/manifest/1.0"

# provenance.json intentionally carries a wall-clock build timestamp: the Speckle
# publish ledger pins each build BY that timestamp (speckle_ledger.payload_hash
# hashes it deliberately). This handoff manifest has the OPPOSITE contract — it
# must regenerate byte-identically so `--check` is a true drift gate — so it
# hashes provenance's STABLE content only, excluding these build-only keys.
# Everything else in provenance (git_commit, sources, crs, warnings) is genuine
# content and stays in the fingerprint.
PROVENANCE_REL = "unreal_export/manifests/provenance.json"
VOLATILE_PROVENANCE_KEYS = ("generated",)

# ── Layer table: the handoff semantics. Hashes are filled in from the tree, so
#    this static map is the only place the accepted/proposed roles are declared,
#    and verify_unreal_export.py independently proves the export honours them. ──
LAYERS = [
    {
        "name": "seating_rows",
        "title": "Seating rows — tread polygons + per-row attributes (Scenario E)",
        "role": "accepted-read-only",
        "speckle_collection": "Seating",
        "speckle_acceptance": "accepted",
        "unreal": {"folder": "Seating", "actor_prefix": "Row_",
                   "import_as": "GeoJSON (georef) or actor_manifest anchors"},
        "authoritative_source": ["vectors_geojson/terrace_treads.geojson"],
        "validation_read_from":
            ["analysis/tier_emission/Scenario_E_baseline_reemit/validation.json"],
        "editable_in_unreal": False,
        "files": ["unreal_export/geo/seating_rows.geojson"],
    },
    {
        "name": "seating_row_splines",
        "title": "Seating row centrelines (open polylines for lofting/labels)",
        "role": "accepted-read-only",
        "speckle_collection": "Seating",
        "speckle_acceptance": "accepted",
        "unreal": {"folder": "Seating", "actor_prefix": "Row_",
                   "import_as": "GeoJSON spline"},
        "authoritative_source": ["vectors_geojson/terrace_treads.geojson"],
        "validation_read_from": [],
        "editable_in_unreal": False,
        "files": ["unreal_export/geo/seating_row_splines.geojson"],
    },
    {
        "name": "stage_floor",
        "title": "Stage / floor footprint — PROVISIONAL (DESIGN_CANON Rule 9 OPEN)",
        "role": "proposal-provisional",
        "speckle_collection": "Stage",
        "speckle_acceptance": "proposal (excluded from the accepted bundle)",
        "unreal": {"folder": "Stage", "actor_prefix": "Stage_",
                   "import_as": "GeoJSON (render-only Z)"},
        "authoritative_source": ["vectors_geojson/bowl_zones.geojson",
                                 "design_open_low/stage_floor.geojson"],
        "validation_read_from": [],
        "editable_in_unreal": "proposal-only (must keep provisional / Rule-9 label)",
        "files": ["unreal_export/geo/stage_floor.geojson"],
    },
    {
        "name": "ada_route",
        "title": "ADA route network — CONCEPT pending civil/code detailing",
        "role": "proposal-concept",
        "speckle_collection": "ADA",
        "speckle_acceptance": "proposal (carried in accepted-context bundle, status verbatim)",
        "unreal": {"folder": "ADA", "actor_prefix": "ADA_ / ADANode_",
                   "import_as": "GeoJSON"},
        "authoritative_source": ["vectors_geojson/ada_route.geojson"],
        "validation_read_from":
            ["analysis/tier_emission/Scenario_E_baseline_reemit/validation.json"],
        "editable_in_unreal":
            "proposal-only (status strings never strengthened past concept/pending)",
        "files": ["unreal_export/geo/ada_route.geojson"],
    },
    {
        "name": "sightline_table",
        "title": "Per-row sightline readout (C_mm, band, verdict) — read from validation",
        "role": "accepted-read-only",
        "speckle_collection": None,
        "speckle_acceptance": "accepted (validation readout, not geometry)",
        "unreal": {"folder": None, "actor_prefix": None,
                   "import_as": "DataTable (string/float)"},
        "authoritative_source":
            ["analysis/tier_emission/Scenario_E_baseline_reemit/validation.json"],
        "validation_read_from":
            ["analysis/tier_emission/Scenario_E_baseline_reemit/validation.json"],
        "editable_in_unreal": False,
        "files": ["unreal_export/tables/sightline_table.csv"],
    },
    {
        "name": "terrain_existing",
        "title": "Existing-grade terrain (mesh + heightfield) — reference",
        "role": "reference-read-only",
        "speckle_collection": "Reference",
        "speckle_acceptance": "accepted (reference context)",
        "unreal": {"folder": "Terrain", "actor_prefix": "Terrain_Existing",
                   "import_as": "Landscape (r16) or static mesh (glb)"},
        "authoritative_source": ["dem/dem_design_1ft.tif"],
        "validation_read_from": [],
        "editable_in_unreal": False,
        "files": ["unreal_export/terrain/heightfield_existing.heightfield.json"],
        "regenerable_binaries": [
            "unreal_export/terrain/terrain_existing.glb",
            "unreal_export/terrain/heightfield_existing.r16",
            "unreal_export/terrain/heightfield_existing.png",
        ],
    },
    {
        "name": "terrain_proposed",
        "title": "Proposed-grade terrain (mesh + heightfield) — reference",
        "role": "reference-read-only",
        "speckle_collection": "Reference",
        "speckle_acceptance": "accepted (reference context)",
        "unreal": {"folder": "Terrain", "actor_prefix": "Terrain_Proposed",
                   "import_as": "Landscape (r16) or static mesh (glb/obj)"},
        "authoritative_source": ["dem/proposed_grade_1ft.tif"],
        "validation_read_from": [],
        "editable_in_unreal": False,
        "files": ["unreal_export/terrain/heightfield_proposed.heightfield.json"],
        "regenerable_binaries": [
            "unreal_export/terrain/terrain_proposed.glb",
            "unreal_export/terrain/terrain_proposed.obj",
            "unreal_export/terrain/heightfield_proposed.r16",
            "unreal_export/terrain/heightfield_proposed.png",
        ],
    },
    {
        "name": "actor_manifest",
        "title": "Actor bridge — local-metre + EPSG:6494 anchors, source provenance",
        "role": "index-provenance",
        "speckle_collection": None,
        "speckle_acceptance": None,
        "unreal": {"folder": None, "actor_prefix": None,
                   "import_as": "placement table (json/csv)"},
        "authoritative_source": ["unreal_export/manifests/provenance.json"],
        "validation_read_from": [],
        "editable_in_unreal": False,
        "files": ["unreal_export/manifests/actor_manifest.json",
                  "unreal_export/manifests/actor_manifest.csv"],
    },
    {
        "name": "material_manifest",
        "title": "Materials — styling only, keyed to a validated attribute",
        "role": "styling-visual-only",
        "speckle_collection": None,
        "speckle_acceptance": None,
        "unreal": {"folder": None, "actor_prefix": None, "import_as": "material set"},
        "authoritative_source": ["unreal_export/manifests/provenance.json"],
        "validation_read_from": [],
        "editable_in_unreal":
            "visual-only (recolour allowed; must_label flags must survive)",
        "files": ["unreal_export/manifests/material_manifest.json"],
    },
    {
        "name": "camera_manifest",
        "title": "Cameras — viewpoints (position_local_m, azimuth, fov)",
        "role": "viewpoints-visual-only",
        "speckle_collection": None,
        "speckle_acceptance": None,
        "unreal": {"folder": "Cameras", "actor_prefix": "Cam_",
                   "import_as": "CineCamera placements"},
        "authoritative_source": ["vectors_geojson/in_situ_viewpoints.geojson"],
        "validation_read_from": [],
        "editable_in_unreal": "visual-only (spawn/move cameras freely)",
        "files": ["unreal_export/manifests/camera_manifest.json"],
    },
    {
        "name": "provenance",
        "title": "Provenance + authoritative-source boundary + planning-grade warnings",
        "role": "authority",
        "speckle_collection": None,
        "speckle_acceptance": None,
        "unreal": {"folder": None, "actor_prefix": None, "import_as": "metadata"},
        "authoritative_source": ["truth_package/design_state.current.json"],
        "validation_read_from": [],
        "editable_in_unreal": False,
        "files": ["unreal_export/manifests/provenance.json"],
    },
]

# Allowed / disallowed MCP operations (mirrors README_UNREAL.md §6/§7; the doc is
# the prose form). Kept here so an MCP bridge can read the boundary as data.
MCP_ALLOWED = [
    "spawn / move cameras; render stills and flythroughs; set bookmarks",
    "assign or recolour materials from material_manifest; toggle layer visibility",
    "spawn labels / text / decals from sightline_table.csv and feature properties",
    "toggle cut/fill overlay, validation tints, provisional hatching",
    "import the generated terrain / heightfield / GeoJSON / DataTable",
    "measure, annotate, place reference splines that are NOT exported back as design",
]
MCP_DISALLOWED = [
    "move / rescale / rotate / re-loft seating, stage, treatment cell, ADA, or terrain "
    "and call the result the design",
    "edit elevations (tread proposed_elev_navd88_ft, stage deck, ADA landings)",
    "change seat counts, C-values, ADA slopes/landings, or earthwork quantities",
    "recolour a provisional/concept element to read as accepted, or drop the "
    "Rule-9 / planning-grade labels",
    "export Unreal geometry directly into vectors_geojson/, dem/, truth_package/, "
    "or analysis/ validation outputs",
    "write back in Unreal units (cm, Y-up, local frame) without reversing the "
    "coordinate contract to EPSG:6494 intl ft / NAVD88",
]


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def jload(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)


def stable_provenance_canon(ap: str) -> bytes:
    """Canonical bytes of provenance.json with the volatile build-only keys
    removed. Both the manifest's provenance sha256 AND its reported byte count
    are taken from this stable basis, so a rebuild that only re-timestamps
    provenance (any value, any length) does NOT churn the manifest — the
    ``--check`` drift gate stays true. It follows that neither field matches a
    raw ``sha256sum``/size of the file (flagged in ``sha256_basis``)."""
    prov = jload(ap)
    stable = {k: v for k, v in prov.items() if k not in VOLATILE_PROVENANCE_KEYS}
    return json.dumps(stable, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def accepted_ledger_entry(ledger: dict) -> dict | None:
    entries = ledger.get("entries", [])
    for e in entries:
        if e.get("design_state") == "accepted":
            return e
    return entries[0] if entries else None


def build() -> dict:
    if not os.path.exists(PROVENANCE):
        sys.exit("FATAL: provenance not found — run scripts/build_unreal_export.py")
    prov = jload(PROVENANCE)

    # Layers: hash the committed package files; reference regenerable binaries.
    layers = []
    fingerprint_pairs: list[tuple[str, str]] = []
    for spec in LAYERS:
        pkg = []
        for rel in spec["files"]:
            ap = os.path.join(REPO, rel)
            if not os.path.exists(ap):
                sys.exit(f"FATAL: package file missing: {rel}")
            if rel == PROVENANCE_REL:
                canon = stable_provenance_canon(ap)
                digest = hashlib.sha256(canon).hexdigest()
                file_rec = {"path": rel, "sha256": digest, "bytes": len(canon),
                            "sha256_basis": (
                                "stable content — canonical JSON minus volatile build "
                                f"keys {list(VOLATILE_PROVENANCE_KEYS)}; sha256 and bytes "
                                "describe that stable basis, not the raw file")}
            else:
                digest = sha256_of(ap)
                file_rec = {"path": rel, "sha256": digest, "bytes": os.path.getsize(ap)}
            pkg.append(file_rec)
            fingerprint_pairs.append((rel, digest))
        entry = {k: v for k, v in spec.items() if k not in ("files", "regenerable_binaries")}
        entry["package_files"] = pkg
        if spec.get("regenerable_binaries"):
            entry["regenerable_binaries"] = {
                "status": "gitignored — heavy, rebuild from source DEM (not hashed here)",
                "rebuild": "python scripts/build_unreal_export.py",
                "paths": list(spec["regenerable_binaries"]),
            }
        layers.append(entry)

    fingerprint_pairs.sort()
    fp = hashlib.sha256()
    for rel, digest in fingerprint_pairs:
        fp.update(f"{rel}:{digest}\n".encode())
    package_fingerprint = fp.hexdigest()

    # Acceptance pointer — read from the publish ledger, never modified here.
    acceptance: dict = {
        "authority": (
            "THIS REPO is the sole acceptance authority: the Python/QGIS validation "
            "gates plus data/speckle_publish_ledger.json. Speckle version history and "
            "Unreal scene state are NEVER acceptance authority."
        ),
        "geometry_change_by_this_package": "none — indexes the existing validated "
        "export; creates and modifies no geometry, ledger, or validation output",
        "accepted_baseline": "Scenario E three-section civic bowl",
        "gates": [
            "python scripts/verify_unreal_export.py",
            "python scripts/audit_in_situ_package.py",
            "python scripts/build_unreal_handoff_manifest.py --check",
        ],
        "warnings": prov.get("warnings", []),
        "warnings_source": prov.get("warnings_source"),
    }
    if os.path.exists(LEDGER):
        entry = accepted_ledger_entry(jload(LEDGER))
        if entry:
            acceptance["ledger_entry"] = {
                "file": "data/speckle_publish_ledger.json",
                "design_state": entry.get("design_state"),
                "branch": entry.get("branch"),
                "project_id": entry.get("project_id"),
                "model_id": entry.get("model_id"),
                "version_id": entry.get("version_id"),
                "source_git_commit": entry.get("source_git_commit"),
                "export_payload_hash": entry.get("export_payload_hash"),
                "validation_passed": entry.get("validation_passed"),
                "open_decisions_count": len(entry.get("open_decisions", [])),
            }
    else:
        acceptance["ledger_entry"] = {
            "file": "data/speckle_publish_ledger.json", "status": "absent on this branch"
        }

    manifest = {
        "schema": SCHEMA,
        "package": "unreal_handoff_v1",
        "title": "Petoskey Pit Civic Bowl — Unreal handoff v1 (MCP runway index)",
        "doc": "docs/unreal_handoff_v1.md",
        "generated_by": "scripts/build_unreal_handoff_manifest.py",
        "verify": "python scripts/build_unreal_handoff_manifest.py --check",
        "purpose": (
            "repo truth -> Speckle review -> Unreal scene import -> MCP-controlled "
            "visual/proposal edits -> repo validation -> ledgered acceptance"
        ),
        "built_from": {
            "provenance": "unreal_export/manifests/provenance.json",
            "provenance_git_commit": prov.get("git_commit"),
            # provenance's wall-clock 'generated' is deliberately NOT copied here:
            # this manifest must regenerate byte-identically (see --check). The
            # build timestamp lives in provenance.json and the Speckle ledger.
            "export_generator": "scripts/build_unreal_export.py",
            "export_verifier": "scripts/verify_unreal_export.py",
        },
        "authoritative_boundary": prov.get("authoritative_boundary"),
        "crs": prov.get("crs"),
        "units": {
            "horizontal_geojson": "EPSG:6494 international feet",
            "3d_scene": "local ENU metres, Z-up (x=east, y=north, z=NAVD88 ft x 0.3048)",
            "ft_to_m": 0.3048,
            "vertical_datum": "NAVD88 (Geoid12A), international feet",
        },
        "package_fingerprint_sha256": package_fingerprint,
        "committed_package_file_count": len(fingerprint_pairs),
        "layers": layers,
        "sources": prov.get("sources", {}),
        "acceptance": acceptance,
        "speckle": {
            "role": "review / exchange surface — NOT acceptance authority",
            "principle": (
                "Speckle version history is not acceptance history; a version counts "
                "as part of the record only while its export_payload_hash still matches "
                "a ledger entry."
            ),
            "payload_generator": "scripts/export_speckle_payload.py",
            "publish_guard":
                "scripts/publish_speckle.py (dry-run first; refuses unless "
                "verify_unreal_export passes)",
            "ledger": "data/speckle_publish_ledger.json",
            "compare": "scripts/speckle_compare.py",
            "webhook": "scripts/speckle_webhook.py",
            "bundles": {
                "accepted": ["Seating", "ADA", "Reference"],
                "shipped_separately_as_proposal": ["Stage (DESIGN_CANON Rule 9 OPEN)"],
            },
            "this_handoff": "does NOT publish to Speckle and does NOT mutate the live server",
        },
        "mcp_runway": {
            "role": (
                "Unreal (optionally driven by an MCP bridge) is a presentation + "
                "proposal surface. Nothing rendered or edited there is design truth "
                "until it passes the repo gates and is ledgered."
            ),
            "allowed": MCP_ALLOWED,
            "disallowed": MCP_DISALLOWED,
            "edit_return_path": (
                "Unreal edit -> proposal GeoJSON in EPSG:6494 intl ft / NAVD88 (keep "
                "feature_id) under requests/ -> run the owning gate(s) -> only on PASS "
                "does a maintainer fold it into the authoritative sources, then rebuild "
                "this package. See docs/unreal_handoff_v1.md."
            ),
        },
    }
    return manifest


def serialize(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify the committed manifest matches the tree; no write")
    args = ap.parse_args()

    text = serialize(build())

    if args.check:
        if not os.path.exists(MANIFEST):
            print("FAIL  data/unreal_handoff_manifest.json is missing — run without --check")
            return 1
        with open(MANIFEST) as fh:
            on_disk = fh.read()
        if on_disk == text:
            print("PASS  data/unreal_handoff_manifest.json matches the tree "
                  "(layers, hashes, CRS, acceptance, MCP boundary)")
            return 0
        print("FAIL  data/unreal_handoff_manifest.json is STALE — "
              "regenerate with: python scripts/build_unreal_handoff_manifest.py")
        return 1

    with open(MANIFEST, "w") as fh:
        fh.write(text)
    print(f"wrote {os.path.relpath(MANIFEST, REPO)}  "
          f"({len(LAYERS)} layers, fingerprint {json.loads(text)['package_fingerprint_sha256'][:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
