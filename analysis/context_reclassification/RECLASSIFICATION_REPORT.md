# Civic Bowl context massing — reclassification by source & confidence

**Date:** 2026-06-27 · **Scope:** read-only audit of context massing around
`/Game/Maps/CivicBowl`. No scene geometry was moved, hidden, deleted, or relit.
**Driver:** `scripts/unreal/reclassify_context_massing.py` +
`scripts/unreal/reclassify_plan_render.py`.

## Governing rule

> A massing object may be classified as a **building** only when it has explicit
> building-**footprint** support — an OSM building polygon, a Microsoft ML
> building footprint, or a manual confirmation. A vertical cluster known only
> from a LiDAR/aerial **height** signal, with no footprint behind it, is **not**
> a building. It becomes a **tree-canopy** object (if a vegetation source
> explains it) or an **unknown-vertical-obstruction** object (if nothing does).

## Headline

| Question | Answer |
|---|---|
| Former "building" objects reclassified as **trees** | **0** |
| Former "building" objects reclassified as **unknown vertical** | **0** |
| Objects that **remained verified buildings** | **890** |
| **Did the obstruction factor change?** | **No** — the bay-view occluder set (18 buildings) is byte-identical before and after |

**Why nothing reclassified:** the existing pipeline already enforces the rule.
Every one of the 890 context buildings carries an OSM building footprint
(`building=*` tag + `osm_id` + footprint polygon). LiDAR (`DSM−DTM`),
Microsoft ML, OSM `levels`, and the type-typology heuristic are used **only to
set roof height on an existing footprint** — never to promote a bare height
cluster into a building block (`gen_context.py:505–592`). No height-only
"building" exists in the auditable inventory, so the strict rule produces zero
demotions and the occluder set is unchanged.

## The three diagnostic classes (visible overlay)

`analysis/context_reclassification/context_reclassification.geojson` ·
`reclassification_plan.png`

| Class | Count | Source basis | used_for_obstruction |
|---|---|---|---|
| **verified_building** | 890 | OSM building footprint (ODbL) | 18 (the W/NW corridor occluders) |
| **tree_canopy** | 2 | vegetation, **no footprint** | 0 (currently unmodelled) |
| **unknown_vertical_obstruction** | 0 | — | 0 |

The two `tree_canopy` objects are the genuinely non-footprint vertical
obstructions in the scene — drawn as **vegetation proxies**, never building
blocks:

1. **Foreground tree screen (az ~315–320)** — observed in the EPT viewshed
   analysis; overlaps the 318–342 bay corridor's lower edge. No footprint, no
   scene actor → **indeterminate**, `candidate_for_obstruction=true`. This is
   the object the user's rule is meant to protect: it must stay vegetation, not
   become a "building" because something is tall there.
2. **`fg_canopy`** — the manifest's declared occluder layer, **deferred** (no
   geometry fetched yet).

## Confidence model

Footprint certainty and height certainty are tracked separately; a verified
building's overall confidence is governed by its weaker leg (height, since the
bay-view obstruction magnitude depends on roof height). Bands match
`OBSTRUCTION_CONFIDENCE_REPORT.md` (High / Medium-High / Medium / Low /
Indeterminate).

| Overall confidence | Count | Meaning |
|---|---|---|
| **Medium-High** | 18 | OSM footprint + **LiDAR-measured** roof height (the corridor occluders, incl. Beards Brewery). Capped below High because heights are LiDAR `DSM−DTM`, not survey. |
| **Medium** | 1 | OSM footprint + OSM `levels` tag |
| **Low** | 871 | OSM footprint + **typology-generic** height (no measured or tagged height) |
| **Indeterminate** | 2 | the two tree-canopy objects (no footprint, no height) |

So the bay-view obstruction factor rests on the **18 Medium-High** occluders;
the 871 Low-confidence buildings are footprint-certain but height-approximate
and almost all sit outside the bay corridor or below the sightline.

## Obstruction-factor invariance (proof)

The bay-view obstruction factor is computed (`bay_view_layered_obstruction.py`)
over the LiDAR-height-verified W/NW corridor occluder set. The reclassification
keeps all 18 of those as `verified_building`, so:

```
bay-view occluders before : 18  (set S)
bay-view occluders after   : 18  (set S, identical osm_ids)
obstruction_occluder_set_identical : true
obstruction_factor_changed         : false
```

Because no occluder was removed, demoted, or swapped to a porous proxy, the
prior result stands unchanged: **Beards Brewery occludes the NW half of the bay
corridor from the east upper rows (clear 100% → 46–62%)**, confirmed earlier by
two independent raycasts (Python DEM+OSM ↔ live UE `trace_world`, ~1 m).

## "Replacing false building primitives with vegetation proxies"

There were **no false (height-only) building primitives to replace** — so the
re-render of the camera shows the same buildings. The substitution mechanic the
request describes is nonetheless exercised on the one legitimate target: the
foreground tree screen is rendered as a hatched **green vegetation proxy** in
the corridor, not a solid block. If a future ingest ever introduces a height-only
cluster, this audit will catch it (it falls through to
`unknown_vertical_obstruction`) instead of silently shipping it as a building.

## Re-render note

`reclassification_plan.png` is the analysis-grade re-render (deterministic, no
live editor): full-extent panel + bay-corridor zoom, colored by class. A live UE
viewport re-capture from the same review camera is a one-command follow-up once
the editor is up (`open_and_frame_civicbowl.py` + capture) — deferred here
because nothing in the building inventory changed, so the live frame is identical
to the current `01_current_camera_upper_rim_to_bay.png` except for the (additive,
indeterminate) tree-canopy proxy.

## Recommendation

1. **Adopt this audit as a gate.** Run `reclassify_context_massing.py` after any
   context re-ingest; fail the build if `unknown_vertical_obstruction > 0` or if
   any object reaches `verified_building` without footprint support.
2. **Model the foreground tree screen** as a vegetation proxy (the only open
   obstruction unknown for transition rows 6–10). Until then, "bay view
   acceptable" for those rows stays qualified, per the confidence report.
3. **Carry the 871 Low-confidence heights honestly** — footprints are sound,
   heights are typology guesses; do not present non-occluder roofs as measured.
