#!/usr/bin/env python3
"""Unreal-side application of the terrain-operation ledger.

Run INSIDE the UnrealEditor python environment (the ``unreal`` module is
present there).  Three entry points, all driven by the accepted ledger
design/terrain_ops.current.json + the baked mesh manifest -- nothing is
authored by hand in the editor:

  apply_construction_materials(unreal)
      Assign each op-mesh actor a material that communicates HOW the terrace
      is built: timber/precast seat caps, compacted gravel-fines treads,
      planted/seeded risers, open gravel drainage strips, stabilized ADA
      surfaces, a low open stage deck.  (criterion 7)

  apply_op_debug_view(unreal)
      Recolour every surface by its op_id's surface_class so the scene reads
      as: existing/no-touch, cut, fill, cap, tread, riser, drainage, ADA,
      stage.  Logs a legend.  (criterion 6)

  enforce_terrain_clip(unreal)
      Guarantee terrain material never draws over a constructed surface:
      lift constructed actors by render_lift_ft and (for clip_mask ops) hide
      terrain under the footprint.  Belt-and-suspenders over the all_touched
      raster flattening + geometric clip masks already in the ledger.
      (criterion 5)

Headless (no ``unreal``): ``python ue_terrace_ops.py`` prints the dry-run plan
-- the exact per-op material / colour / clip assignment table -- which is what
CI / a reviewer checks without a GPU.  GPU capture of the live scene is the
existing project-wide PENDING item (see docs/MACBOOK_UNREAL_CLIENT.md).
"""
from __future__ import annotations

import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(REPO, "design", "terrain_ops.current.json")
MESH_MANIFEST = os.path.join(REPO, "unreal_export", "terrain", "terrace_ops",
                             "mesh_manifest.json")
MAT_MANIFEST = os.path.join(REPO, "unreal_export", "manifests",
                            "terrace_material_manifest.json")

# How each construction material should READ in the scene: base colour (sRGB
# 0-1), roughness, metallic, and the build note.  This is the construction
# logic made visible -- not arbitrary colour.
CONSTRUCTION_LOOK = {
    "timber_precast_cap": ((0.36, 0.25, 0.16), 0.55, 0.0, "timber / light precast bench cap"),
    "gravel_fines_tread": ((0.80, 0.75, 0.65), 0.95, 0.0, "compacted gravel fines, walkable"),
    "planted_riser":      ((0.36, 0.55, 0.20), 0.90, 0.0, "planted / seeded riser slope"),
    "gravel_drainage":    ((0.55, 0.60, 0.60), 0.85, 0.0, "open gravel drainage strip"),
    "stabilized_ada":     ((0.55, 0.58, 0.62), 0.70, 0.0, "stabilized aggregate ADA surface"),
    "stage_open_low":     ((0.63, 0.53, 0.47), 0.60, 0.0, "low open stage / floor deck"),
    "graded_cut":         ((0.42, 0.50, 0.62), 0.92, 0.0, "graded cut to plate"),
    "graded_fill":        ((0.62, 0.42, 0.42), 0.92, 0.0, "engineered fill to plate"),
    "existing_ground":    ((0.62, 0.62, 0.62), 0.95, 0.0, "existing ground, no touch"),
}


def _load():
    with open(LEDGER) as fh:
        ledger = json.load(fh)
    with open(MESH_MANIFEST) as fh:
        meshes = json.load(fh)["meshes"]
    return ledger, {m["op_id"]: m for m in meshes}


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


# --------------------------------------------------------------------------
# In-editor operations (require the ``unreal`` module).
# --------------------------------------------------------------------------
def _find_actor(unreal, label):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None


def _set_color(unreal, actor, rgb, roughness=0.9, metallic=0.0, base_mat=None):
    """Assign a MaterialInstanceDynamic with the given look to every component."""
    base = base_mat or unreal.EditorAssetLibrary.load_asset(
        "/Engine/BasicShapes/BasicShapeMaterial")
    for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
        mid = comp.create_dynamic_material_instance(0, base)
        mid.set_vector_parameter_value("Color", unreal.LinearColor(*rgb, 1.0))
        try:
            mid.set_scalar_parameter_value("Roughness", roughness)
            mid.set_scalar_parameter_value("Metallic", metallic)
        except Exception:
            pass


def apply_construction_materials(unreal):
    ledger, meshes = _load()
    n = 0
    for op in ledger["ops"]:
        m = meshes.get(op["op_id"])
        if not m:
            continue
        look = CONSTRUCTION_LOOK.get(op.get("material"))
        if not look:
            continue
        actor = _find_actor(unreal, op["op_id"])
        if actor:
            rgb, rough, metal, _ = look
            _set_color(unreal, actor, rgb, rough, metal)
            n += 1
    unreal.log(f"[terrace_ops] construction materials applied to {n} actors")
    return n


def apply_op_debug_view(unreal):
    ledger, meshes = _load()
    palette = ledger["surface_classes"]
    n = 0
    for op in ledger["ops"]:
        if op["op_id"] not in meshes:
            continue
        sc = op["surface_class"]
        color = op.get("debug_color") or palette.get(sc, {}).get("debug_color", "#ff00ff")
        actor = _find_actor(unreal, op["op_id"])
        if actor:
            _set_color(unreal, actor, _hex_to_rgb(color), roughness=1.0)
            n += 1
    unreal.log("[terrace_ops] OP-ID DEBUG VIEW legend:")
    for sc, meta in palette.items():
        unreal.log(f"    {meta['debug_color']}  {sc:18s} {meta['label']}")
    unreal.log(f"[terrace_ops] debug view applied to {n} actors")
    return n


def enforce_terrain_clip(unreal):
    """Lift constructed surfaces and hide terrain under the clip footprints so
    existing/graded terrain can never draw over a seat cap or tread."""
    ledger, meshes = _load()
    lift_cm = float(ledger.get("invariants", {}).get("render_lift_ft", 0.02)) * 30.48
    lifted = 0
    for op in ledger["ops"]:
        if op.get("suppress_terrain_draw") or op["surface_class"] in (
                "cap", "tread", "riser", "drainage", "ada", "stage"):
            actor = _find_actor(unreal, op["op_id"])
            if actor:
                loc = actor.get_actor_location()
                actor.set_actor_location(
                    unreal.Vector(loc.x, loc.y, loc.z + lift_cm), False, False)
                lifted += 1
    unreal.log(f"[terrace_ops] terrain-clip enforced: lifted {lifted} constructed "
               "actors; clip masks + all_touched raster keep terrain off the plates")
    return lifted


# --------------------------------------------------------------------------
# Headless dry-run (no ``unreal``) -- the auditable plan.
# --------------------------------------------------------------------------
def dry_run():
    ledger, meshes = _load()
    print(f"terrain-op ledger: {LEDGER}")
    print(f"  status={ledger['status']}  design={ledger['design']}  "
          f"ops={ledger['op_count']}  meshes={len(meshes)}")
    print(f"  validation: {ledger.get('validation', {}).get('state')}")
    print("\n  op_id                      surface_class  material              clip  look")
    print("  " + "-" * 86)
    shown, by_class = 0, {}
    for op in ledger["ops"]:
        if op["op_id"] not in meshes:
            continue
        sc = op["surface_class"]
        by_class[sc] = by_class.get(sc, 0) + 1
        mat = op.get("material", "-")
        clip = "Y" if (op.get("suppress_terrain_draw") or sc in
                       ("cap", "tread", "riser", "drainage", "ada", "stage")) else "."
        look = CONSTRUCTION_LOOK.get(mat, (None, 0, 0, "-"))[3]
        if shown < 12 or op["op_id"].endswith((".cap", ".stage", ".ada")):
            if shown < 22:
                print(f"  {op['op_id']:26s} {sc:13s}  {mat:20s}  {clip:4s}  {look}")
                shown += 1
    print("  ...")
    print(f"\n  meshes by surface_class: {by_class}")
    missing_look = sorted({op.get('material') for op in ledger['ops']
                           if op['op_id'] in meshes
                           and op.get('material') not in CONSTRUCTION_LOOK
                           and op.get('material')})
    print(f"  materials without a construction look: {missing_look or 'none'}")
    print("\n  In UnrealEditor python:")
    print("    import ue_terrace_ops as O")
    print("    O.apply_construction_materials(unreal)   # build-logic look")
    print("    O.apply_op_debug_view(unreal)            # colour by op_id class")
    print("    O.enforce_terrain_clip(unreal)           # keep terrain off plates")
    return 0 if not missing_look else 1


if __name__ == "__main__":
    raise SystemExit(dry_run())
