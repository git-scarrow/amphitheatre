#!/usr/bin/env python3
"""UE-side: dump placed site furniture for capture_furniture.py (Task 2, stub).

Runs INSIDE the Unreal editor (the Python plugin). Walks the actors under the
`Authoring_Furniture` Outliner folder (D2) and writes a placement dump that
`scripts/capture_furniture.py` reverses into an EPSG:6494 proposal. It reads only;
it changes nothing in the level and writes nothing into the repo except the dump
file it is told to write.

Per-actor authoring metadata is carried on **actor tags** (D3), so it survives a
round trip:
    class:<object_class>      e.g. class:bench      (required)
    variant:<variant>         e.g. variant:slat_1800 (optional -> catalog default)
    fid:<feature_id>          e.g. fid:furn_bench_0001 (present only after a prior
                              capture; absent for a freshly placed prop -> minted)

This is a stub: it is exercised only inside UE, never in repo CI. The dump schema
it emits is the contract; `scripts/capture_furniture.py` and its test own the
reverse transform and are fully covered offline.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

AUTHORING_ROOT = "Authoring_Furniture"

try:
    import unreal  # noqa: F401  provided by the UE Python plugin
except ImportError:  # pragma: no cover - only meaningful inside the editor
    unreal = None


def _tag_map(actor) -> dict:
    out = {}
    for t in actor.tags:  # type: ignore[attr-defined]
        s = str(t)
        if ":" in s:
            k, v = s.split(":", 1)
            out[k] = v
    return out


def collect(root: str = AUTHORING_ROOT) -> list[dict]:
    """Read placed furniture actors under `root`. UE-only."""
    if unreal is None:
        raise RuntimeError("ue_capture_furniture.collect() must run inside Unreal")
    actors = []
    for a in unreal.EditorLevelLibrary.get_all_level_actors():  # type: ignore[attr-defined]
        folder = str(a.get_folder_path())
        if not (folder == root or folder.startswith(root + "/")):
            continue
        tags = _tag_map(a)
        if "class" not in tags:
            continue  # not an authored prop
        loc = a.get_actor_location()          # UE cm, X=North Y=East Z=Up
        yaw = a.get_actor_rotation().yaw      # deg, cw-from-North (== azimuth)
        rec = {
            "actor_name": a.get_actor_label(),
            "outliner_path": folder,
            "object_class": tags["class"],
            "variant": tags.get("variant"),
            "ue_location_cm": [loc.x, loc.y, loc.z],
            "yaw_deg": yaw,
        }
        if "fid" in tags:
            rec["feature_id"] = tags["fid"]
        actors.append(rec)
    return actors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="dump JSON path to write")
    ap.add_argument("--base-build-git-commit", required=True,
                    help="commit the imported scene was built from (proposal provenance)")
    ap.add_argument("--captured-by", default="unknown")
    ap.add_argument("--captured-at", default=None,
                    help="ISO timestamp; if omitted, the editor stamps it")
    ap.add_argument("--topic", default="capture")
    args = ap.parse_args(argv)

    captured_at = args.captured_at
    if captured_at is None:
        import datetime as _dt  # capture moment; UE-side provenance, not a repo build
        captured_at = _dt.datetime.now().astimezone().isoformat(timespec="seconds")

    dump = {
        "authoring_root": AUTHORING_ROOT,
        "base_build_git_commit": args.base_build_git_commit,
        "captured_by": args.captured_by,
        "captured_at": captured_at,
        "topic": args.topic,
        "actors": collect(),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(dump, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {args.out} ({len(dump['actors'])} authored prop(s) under {AUTHORING_ROOT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
