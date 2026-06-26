#!/usr/bin/env python3
"""Publish the latest UE review-camera renders into the web viewer.

The web viewer (``web_viewer/index.html``) is a Three.js *schematic* of the
truth package. The Unreal scene produces *photoreal* captures from review
cameras that mirror the viewer's camera presets. This script bridges the two
WITHOUT touching the audited truth build:

  1. copies ``renders/*.png`` (the latest UE captures) into
     ``web_viewer/data/renders/`` so the viewer stays self-contained, and
  2. writes ``web_viewer/data/renders_manifest.js`` (``window.UE_RENDERS``)
     mapping each viewer camera preset to its matching render.

Preset → render pairing is derived from the preset ``source`` field in
``site_data.js``: in-situ presets carry a ``:: <render_basename>`` suffix that
names the capture taken from the same viewpoint. Renders with no matching
preset are still published, in an ``unpaired`` gallery list.

Re-run this whenever the UE captures are refreshed. It is read-only with
respect to the design / truth package; it only writes under ``web_viewer/data``.

    python scripts/build_viewer_renders.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDERS_SRC = ROOT / "renders"
LIVE_SRC = RENDERS_SRC / "ue_live"  # real perspective UE captures (persisted from job-tmp)
VIEWER_DATA = ROOT / "web_viewer" / "data"
RENDERS_DST = VIEWER_DATA / "renders"
LIVE_DST = RENDERS_DST / "ue_live"
SITE_DATA = VIEWER_DATA / "site_data.js"
MANIFEST = VIEWER_DATA / "renders_manifest.js"

# Human-readable captions for renders that have no preset of their own.
UNPAIRED_LABELS = {
    "event_floor_to_treatment_cell": "Event floor → treatment cell",
    "outside_bowl_from_park_edge": "Outside bowl, from park edge",
}


def _load_presets() -> list[dict]:
    if not SITE_DATA.exists():
        raise SystemExit(f"missing {SITE_DATA} — run scripts/build_truth_package.py first")
    js = SITE_DATA.read_text()
    m = re.search(r'"presets":\s*(\[.*?\}\s*\])', js, re.S)
    if not m:
        raise SystemExit("could not locate presets[] in site_data.js")
    return json.loads(m.group(1))


def _render_basename_from_source(source: str | None) -> str | None:
    """in-situ presets tag their capture as '... :: <render_basename>'."""
    if not source or "::" not in source:
        return None
    return source.rsplit("::", 1)[1].strip()


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def main() -> None:
    presets = _load_presets()
    available = {p.stem: p for p in sorted(RENDERS_SRC.glob("*.png"))}
    if not available:
        raise SystemExit(f"no renders found in {RENDERS_SRC}")

    RENDERS_DST.mkdir(parents=True, exist_ok=True)

    # Pair presets -> renders via the source suffix.
    by_preset: dict[str, str] = {}
    paired_stems: set[str] = set()
    for p in presets:
        base = _render_basename_from_source(p.get("source"))
        if base and base in available:
            by_preset[p["id"]] = base + ".png"
            paired_stems.add(base)

    # Copy every render into the viewer and stamp provenance.
    items: dict[str, dict] = {}
    newest_mtime = 0.0
    for stem, src in available.items():
        dst = RENDERS_DST / src.name
        shutil.copy2(src, dst)
        st = src.stat()
        newest_mtime = max(newest_mtime, st.st_mtime)
        items[stem] = {
            "file": f"data/renders/{src.name}",
            "bytes": st.st_size,
            "sha256": _sha256(src)[:16],
            "captured": dt.datetime.fromtimestamp(
                st.st_mtime, dt.timezone.utc
            ).isoformat(timespec="seconds"),
        }

    unpaired = [
        {
            "stem": stem,
            "file": items[stem]["file"],
            "label": UNPAIRED_LABELS.get(stem, stem.replace("_", " ")),
        }
        for stem in sorted(available)
        if stem not in paired_stems
    ]

    # Real perspective UE captures of the live scene (renders/ue_live/). These
    # are genuine Game-View frames, distinct from the schematic placeholders
    # above; they are not preset-paired (free viewpoints), so they form their
    # own gallery group. Labels come from PROVENANCE.json when present.
    live = []
    prov = {}
    prov_path = LIVE_SRC / "PROVENANCE.json"
    if prov_path.exists():
        prov = json.loads(prov_path.read_text())
    if LIVE_SRC.is_dir():
        LIVE_DST.mkdir(parents=True, exist_ok=True)
        for src in sorted(LIVE_SRC.glob("*.png")):
            dst = LIVE_DST / src.name
            shutil.copy2(src, dst)
            st = src.stat()
            live.append(
                {
                    "file": f"data/renders/ue_live/{src.name}",
                    "label": (prov.get("frames") or {}).get(
                        src.name, src.stem.replace("_", " ")
                    ),
                    "bytes": st.st_size,
                    "captured": dt.datetime.fromtimestamp(
                        st.st_mtime, dt.timezone.utc
                    ).isoformat(timespec="seconds"),
                }
            )

    manifest = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "Unreal Engine 5.8 CivicBowl review cameras (Game View captures)",
        "newest_capture": dt.datetime.fromtimestamp(
            newest_mtime, dt.timezone.utc
        ).isoformat(timespec="seconds"),
        "by_preset": by_preset,
        "unpaired": unpaired,
        "live": live,
        "live_meta": {
            "captured": prov.get("captured"),
            "scene_state": prov.get("scene_state"),
            "umap_sha256": prov.get("umap_sha256"),
        },
        "renders": items,
    }

    MANIFEST.write_text(
        "// GENERATED by scripts/build_viewer_renders.py — do not edit.\n"
        "// Latest Unreal review-camera captures paired to viewer presets.\n"
        "window.UE_RENDERS = " + json.dumps(manifest, indent=1) + ";\n"
    )

    print(f"published {len(items)} placeholder renders → {RENDERS_DST}")
    print(f"paired {len(by_preset)} preset(s): {', '.join(sorted(by_preset)) or '—'}")
    print(f"unpaired {len(unpaired)}: {', '.join(u['stem'] for u in unpaired) or '—'}")
    print(f"live UE frames: {len(live)} → {LIVE_DST}")
    print(f"wrote {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
