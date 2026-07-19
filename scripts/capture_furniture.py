#!/usr/bin/env python3
"""Capture placed site furniture from Unreal into an EPSG:6494 proposal (Task 2).

Reads a placement dump exported by `unreal/ue_capture_furniture.py` (the actors a
user placed under the `Authoring_Furniture` Outliner root, D2), reverses the
coordinate contract (Unreal cm / X=North,Y=East / xUE_SCALE  ->  local ENU metres
->  EPSG:6494 intl ft / NAVD88 ft) using the frame inverses in
`scripts/unreal/civicbowl_common.py`, mints a readable stable `feature_id` per
prop (D3), and writes a single-purpose proposal GeoJSON under `requests/`.

The output is a *proposal*, not design truth. It is gated by
`scripts/validate_site_furniture.py` and only folded in by a maintainer. This tool
writes ONLY under `requests/`; it never touches `vectors_geojson/`, `dem/`, or the
export. Pure stdlib; deterministic (all provenance comes from the dump, no
wall-clock is invented).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "unreal"))
import civicbowl_common as CB          # noqa: E402  frame contract + inverses
import validate_prop_catalog as VC     # noqa: E402  catalog loader/validator

REPO = os.path.dirname(_HERE)
DEFAULT_CATALOG = VC.CATALOG
EPSG6494_CRS = {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::6494"}}
_FID_RE = re.compile(r"furn_(?P<cls>.+)_(?P<n>\d+)$")


def ue_cm_to_epsg6494(ue_cm: list[float]) -> tuple[float, float, float]:
    """Unreal cm (X=North, Y=East, Z=Up) -> (x_ft, y_ft, navd88_ft) in EPSG:6494.

    The exact reverse of the export's forward chain: undo the metre->cm scale,
    un-swap UE->ENU, then ENU metres -> intl feet."""
    ux, uy, uz = (c / CB.UE_SCALE for c in ue_cm)   # cm -> metres
    e, n, u = CB.ue_to_enu(ux, uy, uz)              # UE frame -> ENU metres
    x_ft, y_ft = CB.enu_to_ft(e, n)                 # ENU -> EPSG:6494 intl ft
    return (x_ft, y_ft, CB.m_z_to_ft(u))


def _under_root(outliner_path: str | None, root: str) -> bool:
    return bool(outliner_path) and (outliner_path == root
                                    or outliner_path.startswith(root + "/"))


def _mint_feature_ids(actors: list[dict]) -> list[str]:
    """Preserve any existing feature_id; mint furn_<class>_<nnnn> for the rest,
    continuing after the highest existing suffix per class (D3)."""
    counters: dict[str, int] = {}
    for a in actors:
        fid = a.get("feature_id")
        if fid and (m := _FID_RE.match(fid)) and m.group("cls") == a.get("object_class"):
            counters[a["object_class"]] = max(counters.get(a["object_class"], 0),
                                              int(m.group("n")))
    out: list[str] = []
    for a in actors:
        fid = a.get("feature_id")
        if not fid:
            oc = a["object_class"]
            counters[oc] = counters.get(oc, 0) + 1
            fid = f"furn_{oc}_{counters[oc]:04d}"
        out.append(fid)
    return out


def build_proposal(dump: dict, catalog: dict) -> tuple[dict | None, int, list[str]]:
    """Return (proposal_or_None, dropped_out_of_root_count, errors).

    A non-empty error list means no proposal is produced (fail closed)."""
    errors: list[str] = []
    root = dump.get("authoring_root")
    if not root:
        errors.append("dump: missing 'authoring_root' (D2 — capture scope)")
    base_commit = dump.get("base_build_git_commit")
    if not base_commit:
        errors.append("dump: missing 'base_build_git_commit' (proposal provenance)")
    actors = dump.get("actors")
    if not isinstance(actors, list):
        errors.append("dump: 'actors' must be a list")
        return None, 0, errors

    variants_by_class = {c["object_class"]: set(c.get("variants") or [])
                         for c in catalog.get("classes", [])}

    kept: list[dict] = []
    dropped = 0
    for i, a in enumerate(actors):
        if not isinstance(a, dict):
            errors.append(f"actors[{i}]: not an object")
            continue
        if not _under_root(a.get("outliner_path"), root or ""):
            dropped += 1
            continue
        oc = a.get("object_class")
        if oc not in variants_by_class:
            errors.append(f"actors[{i}] ({a.get('actor_name')!r}): object_class "
                          f"{oc!r} is not in the catalog")
            continue
        variant = a.get("variant")
        if variant is not None and variant not in variants_by_class[oc]:
            errors.append(f"actors[{i}] ({a.get('actor_name')!r}): variant "
                          f"{variant!r} not a {oc} variant")
            continue
        loc = a.get("ue_location_cm")
        if not (isinstance(loc, list) and len(loc) == 3
                and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in loc)):
            errors.append(f"actors[{i}] ({a.get('actor_name')!r}): ue_location_cm "
                          "must be 3 numbers")
            continue
        kept.append(a)

    if errors:
        return None, dropped, errors

    fids = _mint_feature_ids(kept)
    if len(set(fids)) != len(fids):
        return None, dropped, ["duplicate feature_id after minting "
                               "(a dump carried colliding ids)"]

    features = []
    for a, fid in zip(kept, fids):
        x_ft, y_ft, z_ft = ue_cm_to_epsg6494(a["ue_location_cm"])
        features.append({
            "type": "Feature",
            "id": fid,
            "geometry": {"type": "Point", "coordinates": [x_ft, y_ft]},
            "properties": {
                "feature_id": fid,
                "object_class": a["object_class"],
                "variant": a.get("variant"),
                "yaw_deg": a.get("yaw_deg", 0.0),
                "anchor_epsg6494_ft": [x_ft, y_ft],
                "anchor_navd88_ft": z_ft,
                "@review": {
                    "placed_by": dump.get("captured_by", "unknown"),
                    "base_build_git_commit": base_commit,
                    "timestamp": dump.get("captured_at"),
                    "object_truth": "proposal — not design until it passes "
                                    "scripts/validate_site_furniture.py and is "
                                    "folded in by a maintainer",
                },
            },
        })

    proposal = {
        "type": "FeatureCollection",
        "name": f"furniture_proposal_{dump.get('topic', 'capture')}",
        "crs": EPSG6494_CRS,
        "bridge": {
            "generator": "scripts/capture_furniture.py",
            "authoring_root": root,
            "base_build_git_commit": base_commit,
            "captured_by": dump.get("captured_by", "unknown"),
            "captured_at": dump.get("captured_at"),
            "coordinate_note": "geometry is EPSG:6494 intl ft (x,y); anchor_navd88_ft "
                               "is NAVD88 intl ft; reversed from Unreal via "
                               "civicbowl_common frame inverses",
            "object_truth": "proposal — reviewed + gated in the repo; Unreal is not "
                            "an acceptance authority",
        },
        "features": features,
    }
    return proposal, dropped, []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dump", help="UE placement dump JSON (from unreal/ue_capture_furniture.py)")
    ap.add_argument("--catalog", default=DEFAULT_CATALOG, help="prop catalog JSON")
    ap.add_argument("--out", default=None,
                    help="output proposal path (default: requests/"
                         "proposal_furniture_<topic>_<captured_date>.geojson)")
    args = ap.parse_args(argv)

    for pth, what in ((args.dump, "dump"), (args.catalog, "catalog")):
        if not os.path.exists(pth):
            print(f"FATAL: {what} not found: {pth}", file=sys.stderr)
            return 2
    with open(args.dump) as fh:
        dump = json.load(fh)
    with open(args.catalog) as fh:
        catalog = json.load(fh)

    cat_errs = VC.validate(catalog)
    if cat_errs:
        print("FATAL: catalog is invalid — run scripts/validate_prop_catalog.py",
              file=sys.stderr)
        return 2

    proposal, dropped, errors = build_proposal(dump, catalog)
    if errors:
        print(f"FAIL  capture blocked — {len(errors)} problem(s):")
        for e in errors:
            print(f"  • {e}")
        return 1

    out = args.out
    if not out:
        topic = dump.get("topic", "capture")
        date = (dump.get("captured_at") or "")[:10] or "undated"
        out = os.path.join(REPO, "requests", f"proposal_furniture_{topic}_{date}.geojson")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(proposal, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"wrote {os.path.relpath(out, REPO)}  "
          f"({len(proposal['features'])} prop(s) captured, {dropped} outside "
          f"'{dump.get('authoring_root')}' dropped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
