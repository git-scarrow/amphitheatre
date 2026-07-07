#!/usr/bin/env python3
"""Convert the validated Unreal handoff package into Speckle review objects.

    repo (authoritative)  ->  unreal_export/ (validated viewer layer)  ->  THIS
                                                                            |
                                                          speckle_export/*.speckle.json
                                                                            |
                                                          publish_speckle.py (dry-run first)

This is a READ-ONLY derivation. It recomputes nothing: C-values, seat counts,
ADA status strings, cut/fill, and the planning-grade warnings are copied
verbatim from ``unreal_export/`` (which is itself downstream of the Python/QGIS
gates). Every leaf review object preserves, per the brief:

    source_file · feature_id · row_id · C-value · ADA status · cut/fill · warnings

Geometry renders in the local ENU-metre frame (viewer float precision); the
lossless EPSG:6494 source geometry rides along in ``@geo_epsg6494``.

Output: ``speckle_export/petoskey_pit.<state>.speckle.json`` — a single Speckle
Collection tree (Seating / Stage / ADA / Reference) ready for publish_speckle.py.

Stdlib only. No network. Never writes outside speckle_export/.

Usage:
    python scripts/export_speckle_payload.py                 # accepted baseline
    python scripts/export_speckle_payload.py --state proposal --topic ambitious-seating
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import speckle_common as S  # noqa: E402


# ── per-feature review-block builders ─────────────────────────────────────────
def _row_id(pr: dict) -> str:
    """Canonical seating join key '<section> r<row>' — the same key used by
    sightline_table.csv and validation.json c_rows. Derived, not native."""
    return f'{pr.get("section")} r{pr.get("row")}'


def _warn_labels(materials: dict, material_id: str | None) -> list[str]:
    """The must-label strings a provisional/concept element must always carry."""
    m = (materials.get("materials") or {}).get(material_id or "", {})
    if m.get("must_label"):
        return [m.get("label", material_id)]
    return []


def _site_base_elev_ft(export: dict) -> float:
    """Lowest seating-row NAVD88 elevation ≈ the event-floor / bowl-base grade.

    Used as the RENDER-ONLY Z for planimetric Stage/ADA features (those with no
    source elevation) so they sit at the bowl base instead of dropping to datum
    0 — i.e. NAVD88 0 ft, ~186 m below grade — which made them look "so far off"
    in the viewer. The faithful source z is preserved separately in @geo.
    """
    zs = []
    for key in ("seating_rows", "seating_splines"):
        for f in export.get(key, {}).get("features", []):
            z = f.get("properties", {}).get("proposed_elev_navd88_ft")
            if isinstance(z, (int, float)) and z > 0:
                zs.append(z)
    return min(zs) if zs else 0.0


def build_seating(export: dict) -> dict:
    """Seating rows -> closed-polyline tread + open-polyline centreline objects.

    Geometry uses the row *spline* (review-friendly centreline). The tread
    polygon outline is kept in @geo_epsg6494 so nothing is lost.
    """
    splines = {f["properties"]["feature_id"]: f
               for f in export["seating_splines"]["features"]}
    elements = []
    for feat in export["seating_rows"]["features"]:
        pr = feat["properties"]
        fid = pr["feature_id"]
        spline = splines.get(fid)
        z = pr.get("proposed_elev_navd88_ft") or 0.0

        # render geometry: prefer the centreline spline (LineString), else the
        # tread polygon outer ring (closed).
        if spline is not None:
            coords = spline["geometry"]["coordinates"]
            geom = S._polyline(S._ring_to_local(coords, z), closed=False, app_id=fid)
        else:
            ring = feat["geometry"]["coordinates"][0]
            geom = S._polyline(S._ring_to_local(ring, z), closed=True, app_id=fid)

        review = {
            "object_class": "seating_row",
            "acceptance": S.STATE_ACCEPTED,  # Scenario E seating is accepted
            "source_file": pr.get("source_file"),
            "feature_id": fid,
            "row_id": _row_id(pr),
            "row_id_derivation": "section + ' r' + row (sightline band key; "
                                 "join to sightline_table.csv / validation.json c_rows)",
            "section": pr.get("section"),
            "section_family": pr.get("section_family"),
            "row": pr.get("row"),
            "zone": pr.get("zone"),
            "seats_kept": pr.get("seats_kept"),
            "band_a_seats": pr.get("band_a_seats"),
            "band_status": pr.get("band_status"),
            "C_mm": pr.get("C_mm"),
            "C_bar_mm": pr.get("C_bar_mm"),
            "pass_frac": pr.get("pass_frac"),
            "sightline_verdict": pr.get("sightline_verdict"),
            "sees_bay": pr.get("sees_bay"),
            "fail_reasons": pr.get("fail_reasons"),
            "ada_status": None,
            "cutfill_mean_ft": pr.get("cutfill_mean_ft"),
            "cutfill_min_ft": pr.get("cutfill_min_ft"),
            "cutfill_max_ft": pr.get("cutfill_max_ft"),
            "cutfill_cells": pr.get("cutfill_cells"),
            "cutfill_sign": pr.get("cutfill_sign"),
            "cutfill_source": pr.get("cutfill_source"),
            "proposed_elev_navd88_ft": z,
            "datum": pr.get("datum"),
            "material_id": pr.get("material_id"),
            "geometry_source": pr.get("geometry_source"),
            "provenance": pr.get("provenance"),
        }
        geo = {
            "type": "Polygon",
            "coordinates": feat["geometry"]["coordinates"],
            "z_navd88_ft": z,
            "crs": "EPSG:6494 intl ft; z=NAVD88 ft",
        }
        name = (export["_actor_by_fid"].get(fid) or {}).get("actor_name") or f"Row_{fid}"
        elements.append(S.review_object(geom, name, review, geo))
    return S.collection("Seating", elements, region="three-section civic bowl (Scenario E)")


def build_stage(export: dict, materials: dict, base_elev_ft: float = 0.0) -> dict:
    elements = []
    for feat in export["stage_floor"]["features"]:
        pr = feat["properties"]
        fid = pr["feature_id"]
        gtype = feat["geometry"]["type"]
        z_src = pr.get("elev_navd88_ft")
        # render Z: drape planimetric (no-elevation) footprints to the bowl base
        z = z_src if isinstance(z_src, (int, float)) and z_src else base_elev_ft

        if gtype == "Point":
            geom = S._point(feat["geometry"]["coordinates"][0],
                            feat["geometry"]["coordinates"][1], z, fid)
        elif gtype == "LineString":
            geom = S._polyline(S._ring_to_local(feat["geometry"]["coordinates"], z),
                               closed=False, app_id=fid)
        elif gtype == "Polygon":
            geom = S._polyline(S._ring_to_local(feat["geometry"]["coordinates"][0], z),
                               closed=True, app_id=fid)
        else:  # MultiPolygon -> first ring of first polygon (event floor footprint)
            ring = feat["geometry"]["coordinates"][0][0]
            geom = S._polyline(S._ring_to_local(ring, z), closed=True, app_id=fid)

        provisional = bool(pr.get("provisional"))
        concept = bool(pr.get("concept_tier"))
        review = {
            "object_class": "stage_feature",
            # provisional/concept stage elements are NOT accepted truth
            "acceptance": (S.STATE_PROPOSAL if (provisional or concept) else S.STATE_ACCEPTED),
            "source_file": pr.get("source_file"),
            "feature_id": fid,
            "name": pr.get("name"),
            "role": pr.get("role"),
            "rule9_status": pr.get("rule9_status"),
            "provisional": provisional,
            "concept_tier": concept,
            "must_label": provisional or concept,
            "labels": _warn_labels(materials, pr.get("material_id")),
            "blocks_bay_view": pr.get("blocks_bay_view"),
            "open_to_bay_side": pr.get("open_to_bay_side"),
            "max_structure_height_ft": pr.get("max_structure_height_ft"),
            "elev_navd88_ft": pr.get("elev_navd88_ft"),
            "az_deg": pr.get("az_deg"),
            "ada_status": None,
            # stage footprints are concept/provisional: cut/fill not sampled
            "cutfill_note": "not sampled — stage deck is provisional (Rule 9 "
                            "carried_provisional; geometry not re-emitted, still "
                            "flagged open); event floor / treatment cell are concept-tier",
            "material_id": pr.get("material_id"),
            "lineage": pr.get("lineage"),
            "note": pr.get("note"),
            "provenance": pr.get("provenance"),
        }
        geo = {"type": gtype, "coordinates": feat["geometry"]["coordinates"],
               "z_navd88_ft": z_src,  # faithful source z (null when planimetric)
               "z_render_navd88_ft": z,
               "z_draped": not (isinstance(z_src, (int, float)) and z_src),
               "crs": "EPSG:6494 intl ft; z=NAVD88 ft"}
        elements.append(S.review_object(geom, pr.get("name") or fid, review, geo))
    return S.collection("Stage", elements,
                        caveat="Stage deck PROVISIONAL (DESIGN_CANON Rule 9 "
                               "carried_provisional — bundle adopted 2026-07-02, "
                               "geometry not re-emitted); event floor + treatment "
                               "cell are concept-tier")


def build_ada(export: dict, base_elev_ft: float = 0.0) -> dict:
    elements = []
    for feat in export["ada_route"]["features"]:
        pr = feat["properties"]
        fid = pr["feature_id"]
        kind = pr.get("kind")
        gtype = feat["geometry"]["type"]
        z_src = pr.get("elev_navd88_ft")
        # render Z: drape planimetric (no-elevation) routes/nodes to the bowl base
        z = z_src if isinstance(z_src, (int, float)) and z_src else base_elev_ft

        if kind == "route":
            geom = S._polyline(S._ring_to_local(feat["geometry"]["coordinates"], z),
                               closed=False, app_id=fid)
            grading = pr.get("grading_required") or {}
            review = {
                "object_class": "ada_route",
                "acceptance": S.STATE_PROPOSAL,  # ADA is concept pending civil/code
                "source_file": pr.get("source_file"),
                "feature_id": fid,
                "name": pr.get("name"),
                "row_id": None,
                "route_class": pr.get("route_class"),
                "ada_status": pr.get("status"),  # VERBATIM — never strengthened
                "must_label": True,
                "preferred": pr.get("preferred"),
                "alternatives": pr.get("alternatives"),
                "profile": pr.get("profile"),
                "design_grade_pct": pr.get("design_grade_pct"),
                "length_ft": pr.get("length_ft"),
                "drop_ft": pr.get("drop_ft"),
                "landings_marked": pr.get("landings_marked"),
                "from": pr.get("from"),
                "to": pr.get("to"),
                # cut/fill for ADA = grading_required block (carried verbatim)
                "cut_ft": grading.get("max_cut_ft"),
                "fill_ft": grading.get("max_fill_ft"),
                "cutfill_mean_abs_ft": grading.get("mean_abs_ft"),
                "cutfill_note": grading.get("note"),
                "validation_running_slope_pct": pr.get("validation_running_slope_pct"),
                "validation_running_ok": pr.get("validation_running_ok"),
                "validation_landings": pr.get("validation_landings"),
                "validation_flights": pr.get("validation_flights"),
                "material_id": pr.get("material_id"),
                "provenance": pr.get("provenance"),
            }
            name = f"ADA_{pr.get('name') or fid}"
        else:  # turn-pad / rise-interval node (Point)
            if gtype == "Point":
                c = feat["geometry"]["coordinates"]
                geom = S._point(c[0], c[1], z, fid)
            else:
                geom = S._polyline(S._ring_to_local(feat["geometry"]["coordinates"], z),
                                   closed=False, app_id=fid)
            review = {
                "object_class": "ada_node",
                "acceptance": S.STATE_PROPOSAL,
                "source_file": pr.get("source_file"),
                "feature_id": fid,
                "name": pr.get("name"),
                "node_kind": kind,
                "crossing": pr.get("crossing"),
                "design_grade_pct": pr.get("design_grade_pct"),
                "elev_navd88_ft": pr.get("elev_navd88_ft"),
                "ada_status": None,
                "material_id": pr.get("material_id"),
                "provenance": pr.get("provenance"),
            }
            name = f"ADANode_{pr.get('name') or fid}"
        geo = {"type": gtype, "coordinates": feat["geometry"]["coordinates"],
               "z_navd88_ft": z_src,  # faithful source z (null when planimetric)
               "z_render_navd88_ft": z,
               "z_draped": not (isinstance(z_src, (int, float)) and z_src),
               "crs": "EPSG:6494 intl ft; z=NAVD88 ft"}
        elements.append(S.review_object(geom, name, review, geo))
    return S.collection("ADA", elements,
                        caveat="ADA route concept pending civil/code detailing — "
                               "status strings carried verbatim, never strengthened")


def build_reference(export: dict) -> dict:
    """Cameras + terrain pointers. Non-decision context; no validation gate."""
    elements = []
    cams = export["cameras"].get("cameras", [])
    for cam in cams:
        pos = cam.get("position_epsg6494_ft") or [S.ORIGIN_X, S.ORIGIN_Y]
        z = cam.get("eye_elev_navd88_ft") or 0.0
        geom = S._point(pos[0], pos[1], z, cam.get("source_feature_id") or cam["camera_name"])
        review = {
            "object_class": "reference",
            "acceptance": S.STATE_REFERENCE,
            "source_file": cam.get("source_file"),
            "feature_id": cam.get("source_feature_id") or cam["camera_name"],
            "ref_kind": "camera",
            "camera_name": cam.get("camera_name"),
            "look_azimuth_deg": cam.get("look_azimuth_deg"),
            "fov_deg": cam.get("fov_deg"),
            "eye_height_ft": cam.get("eye_height_ft"),
            "description": cam.get("description"),
            "ada_status": None,
            "provenance": cam.get("provenance"),
        }
        geo = {"type": "Point", "coordinates": pos, "z_navd88_ft": z,
               "crs": "EPSG:6494 intl ft; z=NAVD88 ft"}
        elements.append(S.review_object(geom, cam["camera_name"], review, geo))

    # terrain pointers (the GLB/heightfields are regenerable binaries; Speckle
    # gets a reference object, not the mesh — terrain stays a viewer asset).
    for mesh in export["provenance"]["build_stats"]["terrain"].get("meshes", []):
        fid = f'terrain_{mesh["name"]}'
        review = {
            "object_class": "reference",
            "acceptance": S.STATE_REFERENCE,
            "source_file": mesh.get("source"),
            "feature_id": fid,
            "ref_kind": "terrain",
            "glb": mesh.get("glb"),
            "grid": mesh.get("grid"),
            "z_navd88_ft": mesh.get("z_navd88_ft"),
            "frame": mesh.get("frame"),
            "ada_status": None,
            "provenance": f'unreal_export/{mesh.get("glb")} (regenerable; not pushed inline)',
        }
        # a zero-extent placeholder point at origin keeps it a valid leaf
        geom = S._point(S.ORIGIN_X, S.ORIGIN_Y, mesh.get("z_navd88_ft", [0])[0], fid)
        geo = {"type": "Point", "coordinates": [S.ORIGIN_X, S.ORIGIN_Y],
               "z_navd88_ft": mesh.get("z_navd88_ft", [0])[0], "crs": "EPSG:6494 intl ft"}
        elements.append(S.review_object(geom, fid, review, geo))
    return S.collection("Reference", elements, collection_type="reference",
                        note="cameras + terrain pointers; non-decision context")


# ── payload assembly ──────────────────────────────────────────────────────────
def build_payload(export: dict, state: str, topic: str | None,
                  layers: set[str] | None = None) -> dict:
    prov = export["provenance"]
    materials = export["materials"]
    export.setdefault("_actor_by_fid", {})  # populated by main(); display names

    gen = prov.get("generated", "")
    date_compact = "".join(ch for ch in gen[:10] if ch.isdigit()) or None
    branch = S.branch_for_state(state, topic, date_compact)

    base_elev_ft = _site_base_elev_ft(export)
    elements = [
        build_seating(export),
        build_stage(export, materials, base_elev_ft),
        build_ada(export, base_elev_ft),
        build_reference(export),
    ]
    # Layer selection. ``layers=None`` keeps every collection (used by the tests
    # so the fixture still documents every object schema). The accepted bundle
    # excludes the Rule-9 carried_provisional "Stage" — it ships as a labelled proposal instead,
    # so the accepted review surface shows only accepted-context geometry.
    if layers is not None:
        elements = [c for c in elements if c["name"] in layers]

    acceptance = {
        "state": state,
        "branch": branch,
        "project": S.SPECKLE_PROJECT_SLUG,
        "rationale": _acceptance_rationale(state),
        "decision_refs": [
            "docs/POST_EMISSION_DECISION_MEMO.md",
            "docs/DESIGN_CANON.md (Rule 9)",
            "docs/ADA_CONCEPT_C_VS_D.md",
        ],
        "per_element_acceptance": "each leaf carries @review.acceptance; provisional/"
                                  "concept elements are individually flagged must_label",
    }

    return {
        "schema": S.SCHEMA,
        "speckle_type": "Objects.Organization.Collection",
        "collectionType": "project",
        "name": f"Petoskey Pit Civic Bowl — {state}",
        "units": "m",
        "applicationId": f"{S.SPECKLE_PROJECT_SLUG}/{branch}",
        "bridge": {
            "generator": "scripts/export_speckle_payload.py",
            "generated_from": prov.get("generated"),
            "source_package": "unreal_export/",
            "git_commit": prov.get("git_commit"),
            "constants_source": S._CONST_SOURCE,
            "object_truth": "Speckle is a review / comparison / collaboration surface. "
                            "It is NOT design truth. The Python/QGIS validation repo "
                            "is the only acceptance authority. Geometry edited in "
                            "Speckle must return as a proposal GeoJSON in EPSG:6494 and "
                            "pass the existing gates before it can become design truth.",
            "recompute_policy": "nothing recomputed; C-values, seat counts, ADA status, "
                                "cut/fill, and warnings are copied verbatim from unreal_export/",
        },
        "crs": {
            "horizontal": prov["crs"]["horizontal"],
            "vertical": prov["crs"]["vertical"],
            "render_frame": "local ENU metres, Z-up, recentred on canon origin "
                            "(viewer float precision)",
            "local_origin_epsg6494_ft": [S.ORIGIN_X, S.ORIGIN_Y],
            "ft_to_m": S.FT2M,
            "reverse_transform": prov["crs"]["reverse_transform"],
            "note": "render geometry is local metres; @geo_epsg6494 on each leaf is "
                    "the lossless EPSG:6494 source geometry",
        },
        "acceptance": acceptance,
        "warnings": prov.get("warnings", []),
        "warnings_source": prov.get("warnings_source"),
        "provenance": {
            "sources": prov.get("sources"),
            "build_stats": {k: prov["build_stats"][k]
                            for k in ("seating", "stage", "ada", "sightline")
                            if k in prov.get("build_stats", {})},
        },
        "@elements": elements,
    }


def minimal_fixture(payload: dict) -> dict:
    """Trim a full payload to one leaf per (object_class, ref_kind/node_kind) so
    the committed fixture documents every object schema while staying tiny. The
    result is still a complete, boundary-valid payload."""
    import copy
    p = copy.deepcopy(payload)
    p["name"] = p["name"] + " — minimal schema fixture"
    p.setdefault("bridge", {})["fixture"] = (
        "trimmed to one leaf per object schema (committed sample for regression "
        "review; regenerate: python scripts/export_speckle_payload.py --emit-fixture <path>)")
    for coll in p["@elements"]:
        seen, kept = set(), []
        for el in coll["@elements"]:
            rv = el.get("@review", {})
            key = (rv.get("object_class"), rv.get("ref_kind"), rv.get("node_kind"))
            if key not in seen:
                seen.add(key)
                kept.append(el)
        coll["@elements"] = kept
    return p


def _acceptance_rationale(state: str) -> str:
    if state == S.STATE_ACCEPTED:
        return ("Scenario E three-section seating / ADA topology / drainage is the "
                "validated control (ACCEPTED). The Rule-9 carried_provisional stage "
                "(geometry not re-emitted) is NOT in this accepted bundle — it ships "
                "separately as proposal/stage-rule9-open so the "
                "accepted surface shows only accepted-context geometry. The ADA route "
                "concept rides inside individually flagged proposal/provisional and is "
                "not promoted by inclusion.")
    if state == S.STATE_REFERENCE:
        return "Non-decision context (terrain, cameras) for orientation only."
    return ("Proposal bundle for review/comparison. Not accepted. Any geometry must "
            "pass the Python/QGIS gates before it can fold into the authoritative sources.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", choices=S.VALID_STATES, default=S.STATE_ACCEPTED,
                    help="review state (default: accepted = Scenario E baseline)")
    ap.add_argument("--topic", default=None,
                    help="proposal/reference topic slug (for branch naming)")
    ap.add_argument("--layers", default=None,
                    help="comma-separated collections to include "
                         "(Seating,Stage,ADA,Reference). Default: accepted excludes "
                         "the Rule-9 carried_provisional Stage; other states include all.")
    ap.add_argument("--export-dir", default=S.EXPORT_DIR)
    ap.add_argument("--out-dir", default=S.OUT_DIR)
    ap.add_argument("--emit-fixture", metavar="PATH", default=None,
                    help="write a minimal one-leaf-per-schema fixture to PATH "
                         "(maintenance: regenerates tests/fixtures/...) and exit")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.export_dir):
        print("FATAL: unreal_export/ not found — run scripts/build_unreal_export.py first",
              file=sys.stderr)
        return 2

    export = S.load_export(args.export_dir)
    # build the actor-name lookup (best display names)
    actor_path = os.path.join(args.export_dir, "manifests/actor_manifest.json")
    if os.path.exists(actor_path):
        am = S.jload(actor_path)
        export["_actor_by_fid"] = {a["source_feature_id"]: a for a in am.get("actors", [])}
    else:
        export["_actor_by_fid"] = {}

    if args.layers:
        layers = {s.strip() for s in args.layers.split(",") if s.strip()}
    elif args.state == S.STATE_ACCEPTED:
        layers = {"Seating", "ADA", "Reference"}  # Rule-9 carried_provisional stage ships as a proposal
    else:
        layers = None
    payload = build_payload(export, args.state, args.topic, layers)

    if args.emit_fixture:
        fix = minimal_fixture(payload)
        ferrs = S.validate_payload(fix, repo=S.REPO)
        os.makedirs(os.path.dirname(os.path.abspath(args.emit_fixture)), exist_ok=True)
        with open(args.emit_fixture, "w") as fh:
            json.dump(fix, fh, indent=1, ensure_ascii=False)
        n = sum(len(c["@elements"]) for c in fix["@elements"])
        print(f"wrote fixture {args.emit_fixture}  ({n} leaves)")
        if ferrs:
            print(f"  WARNING: fixture has {len(ferrs)} boundary error(s)", file=sys.stderr)
            return 1
        print("  fixture boundary self-check: OK")
        return 0

    # self-check: refuse to write a payload that would not pass the boundary
    errs = S.validate_payload(payload, repo=S.REPO)
    os.makedirs(args.out_dir, exist_ok=True)
    out = os.path.join(args.out_dir, f"petoskey_pit.{args.state}.speckle.json")
    with open(out, "w") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)

    n_leaves = sum(len(c["@elements"]) for c in payload["@elements"])
    print(f"wrote {os.path.relpath(out, S.REPO)}")
    print(f"  state={args.state}  branch={payload['acceptance']['branch']}")
    print(f"  collections={len(payload['@elements'])}  leaves={n_leaves}")
    print(f"  warnings carried={len(payload['warnings'])}")
    if errs:
        print(f"\n  WARNING: {len(errs)} boundary error(s) in this payload — it will "
              f"NOT be publishable until fixed:", file=sys.stderr)
        for e in errs[:20]:
            print(f"    - {e}", file=sys.stderr)
        return 1
    print("  boundary self-check: OK (publishable, pending the live verify gate)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
