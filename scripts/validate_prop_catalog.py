#!/usr/bin/env python3
"""Validate the site-furniture prop catalog (Phase 1, Task 1).

`assets/props/catalog.json` is the repo-tracked placement authority for additive
site furniture (D1): what classes may be placed, their plan-view footprints, and
the placement rules the gate (`scripts/validate_site_furniture.py`) later enforces.
This validator is the schema gate for that file — pure stdlib, exit 0 = valid,
exit 1 = at least one problem (printed, one per line).

It checks, and only checks, the catalog's internal consistency:
  * required top-level shape (schema/version/vocabularies/classes);
  * every class is well-formed and uniquely named;
  * footprints are real polygons (>= 3 numeric xy points);
  * default_variant is one of variants;
  * place_on / keep_clear_of reference only declared vocabulary classes;
  * mesh_id is a BARE id, never a committed binary path (D1: metadata only);
  * min_spacing_m / max_count are sane.

It does NOT touch geometry, the export, or any design truth.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(REPO, "assets", "props", "catalog.json")

_MESH_BINARY_SUFFIXES = (".glb", ".obj", ".fbx", ".uasset", ".gltf")


def _is_number(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _is_str_list(v: object) -> bool:
    return isinstance(v, list) and all(isinstance(s, str) and s for s in v)


def validate(catalog: object) -> list[str]:
    """Return a list of human-readable problems; empty list == valid."""
    errs: list[str] = []
    if not isinstance(catalog, dict):
        return ["catalog root is not a JSON object"]

    if not isinstance(catalog.get("schema"), str) or not catalog.get("schema"):
        errs.append("schema: missing or not a non-empty string")
    if not isinstance(catalog.get("version"), int) or isinstance(catalog.get("version"), bool):
        errs.append("version: missing or not an integer")

    surfaces = catalog.get("surface_classes")
    constraints = catalog.get("constraint_classes")
    if not _is_str_list(surfaces) or not surfaces:
        errs.append("surface_classes: must be a non-empty list of strings")
        surfaces = []
    if not _is_str_list(constraints) or not constraints:
        errs.append("constraint_classes: must be a non-empty list of strings")
        constraints = []
    if isinstance(surfaces, list) and len(set(surfaces)) != len(surfaces):
        errs.append("surface_classes: contains duplicates")
    if isinstance(constraints, list) and len(set(constraints)) != len(constraints):
        errs.append("constraint_classes: contains duplicates")
    surface_set, constraint_set = set(surfaces), set(constraints)

    classes = catalog.get("classes")
    if not isinstance(classes, list) or not classes:
        errs.append("classes: must be a non-empty list")
        return errs

    seen: set[str] = set()
    for i, cls in enumerate(classes):
        where = f"classes[{i}]"
        if not isinstance(cls, dict):
            errs.append(f"{where}: not a JSON object")
            continue
        oc = cls.get("object_class")
        if not isinstance(oc, str) or not oc:
            errs.append(f"{where}.object_class: missing or empty")
            where = f"classes[{i}]"
        else:
            where = f"class {oc!r}"
            if oc in seen:
                errs.append(f"{where}: duplicate object_class")
            seen.add(oc)

        mesh = cls.get("mesh_id")
        if not isinstance(mesh, str) or not mesh:
            errs.append(f"{where}.mesh_id: missing or empty")
        elif ("/" in mesh or "\\" in mesh
              or mesh.lower().endswith(_MESH_BINARY_SUFFIXES)):
            errs.append(f"{where}.mesh_id: must be a bare asset id, not a path or "
                        f"binary filename (got {mesh!r}) — meshes stay external (D1)")

        fp = cls.get("footprint")
        if (not isinstance(fp, list) or len(fp) < 3
                or not all(isinstance(pt, list) and len(pt) == 2
                           and _is_number(pt[0]) and _is_number(pt[1]) for pt in fp)):
            errs.append(f"{where}.footprint: must be a polygon of >= 3 numeric [x, y] "
                        "points (local metres)")

        variants = cls.get("variants")
        default = cls.get("default_variant")
        if not _is_str_list(variants) or not variants:
            errs.append(f"{where}.variants: must be a non-empty list of strings")
        elif len(set(variants)) != len(variants):
            errs.append(f"{where}.variants: contains duplicates")
        if not isinstance(default, str) or not default:
            errs.append(f"{where}.default_variant: missing or empty")
        elif isinstance(variants, list) and default not in variants:
            errs.append(f"{where}.default_variant {default!r} is not in variants")

        place_on = cls.get("place_on")
        if not _is_str_list(place_on) or not place_on:
            errs.append(f"{where}.place_on: must be a non-empty list of strings")
        else:
            for s in place_on:
                if s not in surface_set:
                    errs.append(f"{where}.place_on: unknown surface class {s!r} "
                                "(not in surface_classes)")

        keep_clear = cls.get("keep_clear_of")
        if not isinstance(keep_clear, list) or not _is_str_list(keep_clear):
            errs.append(f"{where}.keep_clear_of: must be a list of strings")
        else:
            for s in keep_clear:
                if s not in constraint_set:
                    errs.append(f"{where}.keep_clear_of: unknown constraint class "
                                f"{s!r} (not in constraint_classes)")

        spacing = cls.get("min_spacing_m")
        if not _is_number(spacing) or spacing < 0:
            errs.append(f"{where}.min_spacing_m: must be a number >= 0")

        max_count = cls.get("max_count")
        if not (max_count is None
                or (isinstance(max_count, int) and not isinstance(max_count, bool)
                    and max_count > 0)):
            errs.append(f"{where}.max_count: must be null or a positive integer")

    return errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", default=CATALOG,
                    help="prop catalog JSON (default: assets/props/catalog.json)")
    args = ap.parse_args(argv)

    if not os.path.exists(args.catalog):
        print(f"FATAL: catalog not found: {args.catalog}", file=sys.stderr)
        return 2
    try:
        with open(args.catalog) as fh:
            catalog = json.load(fh)
    except json.JSONDecodeError as e:
        print(f"FAIL  {os.path.relpath(args.catalog, REPO)} is not valid JSON: {e}")
        return 1

    errs = validate(catalog)
    rel = os.path.relpath(args.catalog, REPO)
    if errs:
        print(f"FAIL  {rel} — {len(errs)} problem(s):")
        for e in errs:
            print(f"  • {e}")
        return 1
    n = len(catalog.get("classes", []))
    print(f"PASS  {rel} valid ({n} class(es): "
          f"{', '.join(c['object_class'] for c in catalog['classes'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
