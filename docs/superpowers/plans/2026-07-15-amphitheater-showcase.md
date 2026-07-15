# Amphitheater Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing Petoskey Pit Three.js viewer into a cinematic, model-first technical review website with five synchronized evidence scenes.

**Architecture:** Preserve the static, locally openable `web_viewer` and its authoritative `window.SITE_DATA` payload. Add a declarative scene manifest and a dependency-injected controller as focused browser-compatible scripts, then adapt the existing single-page viewer to render the scrubber, evidence cards, spatial annotations, layer state, and responsive fallback around those interfaces.

**Tech Stack:** Static HTML/CSS/JavaScript, vendored Three.js r147 and OrbitControls, Node.js built-in test runner, Python 3 standard-library build verification.

## Global Constraints

- `web_viewer/data/site_data.js` remains the geometry and audit source of truth; presentation code must not recompute or strengthen claims.
- The existing model remains the dominant surface on desktop, tablet, and narrow screens.
- Use `#07110F` for the civic green-black canvas, `#9EE9C3` for validated geometry, `#F3B958` for provisional findings, and `#86D7E6` for grading evidence.
- Keep the planning-grade notice and provisional Rule 9 stage status persistently accessible.
- Preserve orbit, pan, zoom, row selection, camera presets, reset, layer controls, compass, and the non-WebGL fallback.
- Distinguish validated, provisional, illustrative, and unknown states with text and shape as well as color.
- Respect `prefers-reduced-motion`; reduced-motion users receive immediate scene changes.
- Do not add authentication, comments, persistence, or new authoritative design data.
- Do not add runtime network dependencies; the built viewer must continue to work from local files.

---

## File Structure

- Create `web_viewer/showcase_scenes.js`: immutable scene definitions and manifest validation.
- Create `web_viewer/showcase_controller.js`: framework-free scene sequencing and adapter coordination.
- Modify `web_viewer/index.html`: cinematic shell, viewer adapters, scrubber, evidence cards, annotations, responsive behavior, and fallback.
- Create `tests/web_viewer/showcase_scenes.test.cjs`: manifest contract and evidence-source tests.
- Create `tests/web_viewer/showcase_controller.test.cjs`: controller sequencing and reduced-motion tests.
- Create `tests/web_viewer/showcase_markup.test.cjs`: static integration and accessibility contract tests.
- Create `scripts/build_web_showcase.py`: deterministic static build into `dist/amphitheater-showcase/`.
- Create `tests/web_viewer/test_build_web_showcase.py`: build-content regression test.
- Modify `README_web_viewer.md`: describe the guided evidence experience and build output.

### Task 1: Declarative Evidence Scene Manifest

**Files:**
- Create: `web_viewer/showcase_scenes.js`
- Create: `tests/web_viewer/showcase_scenes.test.cjs`

**Interfaces:**
- Produces: `SHOWCASE_SCENES: ReadonlyArray<ShowcaseScene>` and `validateShowcaseScenes(scenes): true` in browsers and CommonJS.
- `ShowcaseScene` fields: `id`, `number`, `title`, `kicker`, `presetId`, `layers`, `highlight`, `cutFill`, `annotation`, and `evidenceIds`.
- Evidence IDs reference entries already present in `SITE_DATA.audit.checks`.

- [ ] **Step 1: Write the failing manifest tests**

```js
// tests/web_viewer/showcase_scenes.test.cjs
const test = require('node:test');
const assert = require('node:assert/strict');

const { SHOWCASE_SCENES, validateShowcaseScenes } =
  require('../../web_viewer/showcase_scenes.js');

test('defines the five approved scenes in review order', () => {
  assert.deepEqual(
    SHOWCASE_SCENES.map(scene => scene.id),
    ['orientation', 'seating', 'access', 'grading', 'stage']
  );
  assert.deepEqual(SHOWCASE_SCENES.map(scene => scene.number), [1, 2, 3, 4, 5]);
});

test('every scene has a camera, visible geometry, annotation, and evidence', () => {
  assert.equal(validateShowcaseScenes(SHOWCASE_SCENES), true);
  for (const scene of SHOWCASE_SCENES) {
    assert.ok(scene.presetId);
    assert.ok(scene.layers.length > 0);
    assert.ok(scene.highlight.length > 0);
    assert.ok(scene.annotation.label);
    assert.equal(scene.annotation.xy.length, 2);
    assert.ok(scene.evidenceIds.length > 0);
  }
});

test('scene evidence uses current SITE_DATA audit identifiers', () => {
  const ids = new Set(SHOWCASE_SCENES.flatMap(scene => scene.evidenceIds));
  for (const required of [
    'bay_view', 'seats_nominal', 'seats_band_a', 'sightlines',
    'ada_network', 'cross_aisle', 'earthwork', 'stage_rule9'
  ]) assert.equal(ids.has(required), true, `missing ${required}`);
});

test('validation rejects duplicate identifiers', () => {
  assert.throws(
    () => validateShowcaseScenes([SHOWCASE_SCENES[0], SHOWCASE_SCENES[0]]),
    /duplicate scene id/
  );
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test tests/web_viewer/showcase_scenes.test.cjs`  
Expected: FAIL with `Cannot find module '../../web_viewer/showcase_scenes.js'`.

- [ ] **Step 3: Implement the immutable manifest and validator**

```js
// web_viewer/showcase_scenes.js
(function expose(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.SHOWCASE_SCENES = api.SHOWCASE_SCENES;
  root.validateShowcaseScenes = api.validateShowcaseScenes;
})(typeof window === 'object' ? window : globalThis, function createManifest() {
  const scenes = [
    {
      id: 'orientation', number: 1, title: 'A bowl turned toward the bay',
      kicker: 'Site + view', presetId: 'site_overview',
      layers: ['terrainProposed', 'terrainContext', 'treads', 'siteContext', 'bay', 'bayAxis'],
      highlight: ['bayAxis'], cutFill: false,
      annotation: { label: 'Bay-view axis · 330°', xy: [32.5, -56.29] },
      evidenceIds: ['bay_view']
    },
    {
      id: 'seating', number: 2, title: 'Capacity follows the landform',
      kicker: 'Seating + sightlines', presetId: 'back_row',
      layers: ['terrainProposed', 'treads', 'humanScale', 'dimensions'],
      highlight: ['treads'], cutFill: false,
      annotation: { label: '45 audited seating treads', xy: [78, -94] },
      evidenceIds: ['seats_nominal', 'seats_band_a', 'sightlines']
    },
    {
      id: 'access', number: 3, title: 'A connected accessible route',
      kicker: 'Arrival + circulation', presetId: 'ada_cross_aisle',
      layers: ['terrainProposed', 'treads', 'circulation', 'adaPrimary', 'adaSecondary', 'adaDistribution'],
      highlight: ['adaPrimary', 'adaDistribution'], cutFill: false,
      annotation: { label: 'Preferred Concept C route', xy: [114.58, -53.25] },
      evidenceIds: ['ada_network', 'cross_aisle', 'ada_full']
    },
    {
      id: 'grading', number: 4, title: 'Measured intervention, visible limits',
      kicker: 'Grade + earthwork', presetId: 'rim_overlook',
      layers: ['terrainProposed', 'terrainContext', 'treads', 'drainage'],
      highlight: ['terrainProposed', 'drainage'], cutFill: true,
      annotation: { label: 'Cut / fill component proxy', xy: [62, -88] },
      evidenceIds: ['earthwork', 'drainage', 'groundwater', 'geotech']
    },
    {
      id: 'stage', number: 5, title: 'One consequential decision remains open',
      kicker: 'Stage · Rule 9', presetId: 'stage_to_audience',
      layers: ['terrainProposed', 'treads', 'stage', 'bayAxis'],
      highlight: ['stage'], cutFill: false,
      annotation: { label: 'Stage geometry · provisional', xy: [24.44, -42.33] },
      evidenceIds: ['stage_rule9', 'acoustics']
    }
  ];

  function validateShowcaseScenes(input) {
    const ids = new Set();
    for (const scene of input) {
      if (ids.has(scene.id)) throw new Error(`duplicate scene id: ${scene.id}`);
      ids.add(scene.id);
      for (const key of ['id', 'title', 'kicker', 'presetId'])
        if (!scene[key]) throw new Error(`${scene.id || 'scene'} missing ${key}`);
      for (const key of ['layers', 'highlight', 'evidenceIds'])
        if (!Array.isArray(scene[key]) || scene[key].length === 0)
          throw new Error(`${scene.id} missing ${key}`);
      if (!scene.annotation?.label || scene.annotation.xy?.length !== 2)
        throw new Error(`${scene.id} has invalid annotation`);
    }
    return true;
  }

  validateShowcaseScenes(scenes);
  return { SHOWCASE_SCENES: Object.freeze(scenes.map(scene => Object.freeze(scene))), validateShowcaseScenes };
});
```

- [ ] **Step 4: Run the manifest tests**

Run: `node --test tests/web_viewer/showcase_scenes.test.cjs`  
Expected: 4 tests PASS.

- [ ] **Step 5: Commit the manifest**

```bash
git add web_viewer/showcase_scenes.js tests/web_viewer/showcase_scenes.test.cjs
git commit -m "feat: define amphitheater evidence scenes"
```

### Task 2: Scene Controller and Viewer Adapter Contract

**Files:**
- Create: `web_viewer/showcase_controller.js`
- Create: `tests/web_viewer/showcase_controller.test.cjs`

**Interfaces:**
- Consumes: `SHOWCASE_SCENES` from Task 1 and `auditById: Map<string, AuditCheck>` built from `SITE_DATA.audit.checks`.
- Produces: `createShowcaseController(options)` returning `{ activate(id), next(), previous(), current() }`.
- Requires adapters: `setPreset(presetId, { animate })`, `setLayers(layerNames)`, `setHighlights(layerNames)`, and `setCutFill(enabled)`.
- Calls `onChange({ scene, evidence, index, total })` after adapters succeed.

- [ ] **Step 1: Write failing sequencing and reduced-motion tests**

```js
// tests/web_viewer/showcase_controller.test.cjs
const test = require('node:test');
const assert = require('node:assert/strict');
const { createShowcaseController } = require('../../web_viewer/showcase_controller.js');

function harness(reducedMotion = false) {
  const calls = [];
  const scenes = [
    { id: 'one', presetId: 'p1', layers: ['a'], highlight: ['a'], cutFill: false, evidenceIds: ['e1'] },
    { id: 'two', presetId: 'p2', layers: ['b'], highlight: ['b'], cutFill: true, evidenceIds: ['e2'] }
  ];
  const controller = createShowcaseController({
    scenes,
    auditById: new Map([['e1', { id: 'e1' }], ['e2', { id: 'e2' }]]),
    reducedMotion,
    adapters: {
      setPreset: (id, options) => calls.push(['preset', id, options.animate]),
      setLayers: names => calls.push(['layers', names]),
      setHighlights: names => calls.push(['highlight', names]),
      setCutFill: enabled => calls.push(['cutFill', enabled])
    },
    onChange: payload => calls.push(['change', payload.scene.id, payload.evidence.map(item => item.id)])
  });
  return { controller, calls };
}

test('activate synchronizes model state before notifying the interface', () => {
  const { controller, calls } = harness();
  controller.activate('two');
  assert.deepEqual(calls, [
    ['layers', ['b']], ['highlight', ['b']], ['cutFill', true],
    ['preset', 'p2', true], ['change', 'two', ['e2']]
  ]);
});

test('reduced motion disables camera animation', () => {
  const { controller, calls } = harness(true);
  controller.activate('one');
  assert.deepEqual(calls.find(call => call[0] === 'preset'), ['preset', 'p1', false]);
});

test('next and previous clamp at the ends', () => {
  const { controller } = harness();
  controller.activate('one');
  assert.equal(controller.previous().id, 'one');
  assert.equal(controller.next().id, 'two');
  assert.equal(controller.next().id, 'two');
});

test('missing evidence is returned as unavailable', () => {
  const changes = [];
  const controller = createShowcaseController({
    scenes: [{ id: 'one', presetId: 'p1', layers: ['a'], highlight: ['a'], cutFill: false, evidenceIds: ['missing'] }],
    auditById: new Map(), reducedMotion: false,
    adapters: { setPreset() {}, setLayers() {}, setHighlights() {}, setCutFill() {} },
    onChange: payload => changes.push(payload)
  });
  controller.activate('one');
  assert.deepEqual(changes[0].evidence, [{ id: 'missing', status: 'unavailable', value: null, source: 'Unavailable in current truth package' }]);
});
```

- [ ] **Step 2: Run the controller tests to verify they fail**

Run: `node --test tests/web_viewer/showcase_controller.test.cjs`  
Expected: FAIL with `Cannot find module '../../web_viewer/showcase_controller.js'`.

- [ ] **Step 3: Implement the controller**

```js
// web_viewer/showcase_controller.js
(function expose(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.createShowcaseController = api.createShowcaseController;
})(typeof window === 'object' ? window : globalThis, function controllerModule() {
  function createShowcaseController({ scenes, auditById, adapters, onChange, reducedMotion }) {
    let index = 0;
    const unavailable = id => ({
      id, status: 'unavailable', value: null,
      source: 'Unavailable in current truth package'
    });

    function apply(nextIndex) {
      index = Math.max(0, Math.min(nextIndex, scenes.length - 1));
      const scene = scenes[index];
      adapters.setLayers(scene.layers);
      adapters.setHighlights(scene.highlight);
      adapters.setCutFill(Boolean(scene.cutFill));
      adapters.setPreset(scene.presetId, { animate: !reducedMotion });
      const evidence = scene.evidenceIds.map(id => auditById.get(id) || unavailable(id));
      onChange({ scene, evidence, index, total: scenes.length });
      return scene;
    }

    return {
      activate(id) {
        const found = scenes.findIndex(scene => scene.id === id);
        if (found < 0) throw new Error(`unknown showcase scene: ${id}`);
        return apply(found);
      },
      next() { return apply(index + 1); },
      previous() { return apply(index - 1); },
      current() { return scenes[index]; }
    };
  }
  return { createShowcaseController };
});
```

- [ ] **Step 4: Run the controller tests**

Run: `node --test tests/web_viewer/showcase_controller.test.cjs`  
Expected: 4 tests PASS.

- [ ] **Step 5: Commit the controller**

```bash
git add web_viewer/showcase_controller.js tests/web_viewer/showcase_controller.test.cjs
git commit -m "feat: coordinate showcase scene state"
```

### Task 3: Cinematic Viewer Shell and Evidence Interface

**Files:**
- Modify: `web_viewer/index.html:8-235`
- Modify: `web_viewer/index.html:831-1030`
- Create: `tests/web_viewer/showcase_markup.test.cjs`

**Interfaces:**
- Consumes: `SHOWCASE_SCENES`, `createShowcaseController`, `SITE_DATA.audit.checks`, existing Three.js groups, and existing camera presets.
- Produces DOM IDs: `showcaseHeader`, `sceneScrubber`, `evidenceStack`, `modelAnnotation`, `utilityDrawer`, `scenePrev`, and `sceneNext`.
- Produces viewer adapter functions: `setShowcaseLayers(names)`, `setShowcaseHighlights(names)`, `setCutFillEnabled(enabled)`, and `setPresetById(id, options)`.

- [ ] **Step 1: Write the failing static integration tests**

```js
// tests/web_viewer/showcase_markup.test.cjs
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const html = fs.readFileSync('web_viewer/index.html', 'utf8');

test('loads the scene modules before the inline viewer', () => {
  assert.match(html, /<script src="showcase_scenes\.js"><\/script>/);
  assert.match(html, /<script src="showcase_controller\.js"><\/script>/);
});

test('contains the accessible cinematic review controls', () => {
  for (const id of ['showcaseHeader', 'sceneScrubber', 'evidenceStack', 'modelAnnotation', 'utilityDrawer', 'scenePrev', 'sceneNext'])
    assert.match(html, new RegExp(`id="${id}"`));
  assert.match(html, /aria-live="polite"/);
  assert.match(html, /aria-label="Evidence scenes"/);
});

test('preserves the permanent planning and stage disclosures', () => {
  assert.match(html, /PLANNING-GRADE/);
  assert.match(html, /Rule 9 open/i);
});

test('includes responsive and reduced-motion behavior', () => {
  assert.match(html, /@media \(max-width: 760px\)/);
  assert.match(html, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(html, /matchMedia\('\(prefers-reduced-motion: reduce\)'\)/);
});
```

- [ ] **Step 2: Run the markup tests to verify they fail**

Run: `node --test tests/web_viewer/showcase_markup.test.cjs`  
Expected: FAIL because the showcase scripts and DOM IDs are absent.

- [ ] **Step 3: Replace the side-panel layout with the selected cinematic shell**

Add `showcase_scenes.js` and `showcase_controller.js` immediately after `site_data.js`. Replace the fixed left audit panel with semantic overlay markup using this structure:

```html
<header id="showcaseHeader" class="showcase-header">
  <div>
    <p class="eyebrow">Petoskey, Michigan · Technical review</p>
    <h1>Petoskey Pit <span>Open Civic Bowl</span></h1>
  </div>
  <button id="utilityToggle" aria-expanded="false" aria-controls="utilityDrawer">Layers + sources</button>
</header>
<div class="persistent-status" role="note">
  <span class="status-chip planning">Planning-grade</span>
  <span>Not stamped engineering</span>
  <span class="status-chip provisional">Stage · Rule 9 open</span>
</div>
<aside id="utilityDrawer" hidden aria-label="Model layers and project sources">
  <div id="presets" class="preset-grid"></div>
  <div id="layers"></div>
  <div id="checks"></div>
  <div id="sources"></div>
</aside>
<div id="modelAnnotation" class="model-annotation" aria-hidden="true"></div>
<section id="evidenceStack" class="evidence-stack" aria-live="polite"></section>
<nav id="sceneScrubber" class="scene-scrubber" aria-label="Evidence scenes">
  <button id="scenePrev" aria-label="Previous evidence scene">←</button>
  <div id="sceneSteps"></div>
  <button id="sceneNext" aria-label="Next evidence scene">→</button>
</nav>
```

Retain the existing `#view`, `#errOverlay`, `#compass`, `#infoCard`, and `#hint` elements. Move the existing audit/source content into `#utilityDrawer` rather than deleting it.

- [ ] **Step 4: Implement the selected visual system and responsive bottom sheet**

Set the page and overlay variables to the approved palette, keep the canvas full viewport, give evidence cards a dark translucent surface with a visible truth-tier edge, and anchor the 180px scrubber to the bottom. At `max-width: 760px`, make `#evidenceStack` a scrollable bottom sheet immediately above a horizontally scrollable scene step row. Add:

```css
:root {
  --canvas: #07110f; --validated: #9ee9c3; --provisional: #f3b958;
  --grading: #86d7e6; --paper: #f0ede3; --muted: #a7b4ad;
}
body { background: var(--canvas); color: var(--paper); overflow: hidden; }
#view { position: fixed; inset: 0; background: linear-gradient(155deg,#12231f,#07110f 68%); }
.evidence-card { border-left: 4px solid var(--validated); background: rgba(7,17,15,.86); backdrop-filter: blur(18px); }
.evidence-card[data-status="warn"], .evidence-card[data-status="fail"] { border-left-color: var(--provisional); }
.scene-scrubber { position: fixed; inset: auto 0 0; min-height: 180px; }
@media (max-width: 760px) {
  .evidence-stack { inset: auto 12px 128px; max-height: 42vh; overflow: auto; }
  .scene-scrubber { min-height: 112px; }
  #sceneSteps { overflow-x: auto; scroll-snap-type: x mandatory; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; animation-duration: .01ms !important; }
}
```

- [ ] **Step 5: Register existing Three.js groups under stable layer names**

After all current groups exist, create a registry without moving or recomputing geometry:

```js
const showcaseLayerRegistry = {
  terrainProposed: [terrainProposed], terrainContext: [terrainContext],
  treads: [treadGroup], stage: zoneGroups.stage ? [zoneGroups.stage] : [],
  circulation: zoneGroups.circulation ? [zoneGroups.circulation] : [],
  drainage: zoneGroups.drainage ? [zoneGroups.drainage] : [],
  adaPrimary: [adaPrimaryGroup], adaSecondary: [adaSecondaryGroup],
  adaDistribution: [adaDistGroup], siteContext: [ctxGroup], bay: [bayGroup],
  bayAxis: [axisGroup], humanScale: [humanGroup], dimensions: [dimGroup]
};
const showcaseManagedLayers = new Set(Object.keys(showcaseLayerRegistry));
```

Store each `layerRow` checkbox in `layerCheckboxes` keyed by the same registry name. Implement `setShowcaseLayers(names)` by applying visibility to registered groups and synchronizing their checkboxes. Hoist the cut/fill state setter out of the layer panel block as `setCutFillEnabled(enabled)` so both manual controls and guided scenes update the same terrain color attribute.

- [ ] **Step 6: Implement camera, highlight, evidence, and scrubber adapters**

Implement `setPresetById(id, { animate })` by finding the existing `D.presets` entry; call `flyTo` when animated and copy camera/target immediately when not. Implement `setShowcaseHighlights(names)` by restoring cached material opacity/emissive state, then accenting only registered target objects; do not mutate geometry or data.

Build evidence cards from `D.audit.checks` with `textContent` for project-provided strings. Each card must include status text, value, note, and source. Build five scrubber buttons from `SHOWCASE_SCENES`. Initialize the controller as follows:

```js
const auditById = new Map(D.audit.checks.map(check => [check.id, check]));
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const showcase = createShowcaseController({
  scenes: SHOWCASE_SCENES, auditById, reducedMotion,
  adapters: {
    setPreset: setPresetById,
    setLayers: setShowcaseLayers,
    setHighlights: setShowcaseHighlights,
    setCutFill: setCutFillEnabled
  },
  onChange: renderShowcaseState
});
showcase.activate('orientation');
```

Wire `scenePrev`, `sceneNext`, scene buttons, `ArrowLeft`, and `ArrowRight`. Ignore shortcuts while focus is inside an input, button, or editable element. Update `aria-current="step"`, disabled previous/next states, evidence contents, and the annotation label on each change.

- [ ] **Step 7: Preserve manual review and non-WebGL behavior**

Keep row picking and the existing `#infoCard`. Manual orbiting must not change evidence values. Keep the `try/catch` WebGL boundary, but update its fallback copy to explain that the guided evidence cards, sources, and disclosures remain available. Initialize the evidence interface before `new THREE.WebGLRenderer(...)` so the fallback is usable.

- [ ] **Step 8: Run all JavaScript tests**

Run: `node --test tests/web_viewer/*.test.cjs`  
Expected: 12 tests PASS.

- [ ] **Step 9: Commit the cinematic interface**

```bash
git add web_viewer/index.html tests/web_viewer/showcase_markup.test.cjs
git commit -m "feat: add cinematic model evidence interface"
```

### Task 4: Deterministic Static Build

**Files:**
- Create: `scripts/build_web_showcase.py`
- Create: `tests/web_viewer/test_build_web_showcase.py`
- Modify: `README_web_viewer.md`

**Interfaces:**
- Consumes: `web_viewer/index.html`, `showcase_scenes.js`, `showcase_controller.js`, `data/site_data.js`, and `vendor/`.
- Produces: a self-contained `dist/amphitheater-showcase/` directory whose `index.html` can be served by any static host.

- [ ] **Step 1: Write the failing build test**

```python
# tests/web_viewer/test_build_web_showcase.py
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

class ShowcaseBuildTest(unittest.TestCase):
    def test_build_contains_model_data_runtime_and_no_design_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "site"
            subprocess.run(
                [sys.executable, str(ROOT / "scripts/build_web_showcase.py"), "--output", str(out)],
                cwd=ROOT, check=True,
            )
            expected = {
                "index.html", "showcase_scenes.js", "showcase_controller.js",
                "data/site_data.js", "vendor/three.min.js", "vendor/OrbitControls.js",
            }
            built = {str(path.relative_to(out)) for path in out.rglob("*") if path.is_file()}
            self.assertTrue(expected.issubset(built))
            self.assertFalse(any(path.startswith("vectors_geojson/") for path in built))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the build test to verify it fails**

Run: `python3 -m unittest tests.web_viewer.test_build_web_showcase -v`  
Expected: FAIL because `scripts/build_web_showcase.py` does not exist.

- [ ] **Step 3: Implement the deterministic build script**

```python
#!/usr/bin/env python3
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web_viewer"
REQUIRED = (
    "index.html", "showcase_scenes.js", "showcase_controller.js",
    "data/site_data.js", "vendor/three.min.js", "vendor/OrbitControls.js",
)

def build(output: Path) -> None:
    missing = [name for name in REQUIRED if not (SOURCE / name).is_file()]
    if missing:
        raise SystemExit("missing showcase inputs: " + ", ".join(missing))
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name in REQUIRED:
        source = SOURCE / name
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    print(output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the static amphitheater showcase")
    parser.add_argument("--output", type=Path, default=ROOT / "dist/amphitheater-showcase")
    args = parser.parse_args()
    build(args.output.resolve())
```

- [ ] **Step 4: Run the build test and production build**

Run: `python3 -m unittest tests.web_viewer.test_build_web_showcase -v`  
Expected: 1 test PASS.

Run: `python3 scripts/build_web_showcase.py`  
Expected: prints the absolute `dist/amphitheater-showcase` path and exits 0.

- [ ] **Step 5: Document the guided review and build**

Update `README_web_viewer.md` sections 1 and 2 to explain the five evidence scenes, synchronized camera/layers/evidence behavior, persistent truth-tier disclosures, keyboard arrows, reduced-motion behavior, narrow-screen bottom sheet, non-WebGL evidence fallback, and `python3 scripts/build_web_showcase.py` output.

- [ ] **Step 6: Commit the build path and documentation**

```bash
git add scripts/build_web_showcase.py tests/web_viewer/test_build_web_showcase.py README_web_viewer.md
git commit -m "build: package amphitheater showcase site"
```

### Task 5: Full Verification and Sites Publishing Handoff

**Files:**
- Verify only: all files from Tasks 1-4.
- Publishing metadata may be created only by the Sites hosting workflow after it inspects the validated static build.

**Interfaces:**
- Consumes: `dist/amphitheater-showcase/`.
- Produces: a validated local showcase and a Sites-hosted URL.

- [ ] **Step 1: Run the complete automated suite**

Run: `node --test tests/web_viewer/*.test.cjs`  
Expected: 12 tests PASS.

Run: `python3 -m unittest tests.web_viewer.test_build_web_showcase -v`  
Expected: 1 test PASS.

Run: `python3 scripts/build_web_showcase.py`  
Expected: exits 0 and produces all six required static artifacts.

- [ ] **Step 2: Run the existing truth-package verification**

Run: `.venv/bin/python scripts/build_truth_package.py`  
Expected: exits 0, regenerates the current truth package without changing authoritative source geometry, and keeps `site_data.js` valid.

Run: `git diff --check`  
Expected: no whitespace errors.

- [ ] **Step 3: Perform the user-requested product-flow verification**

Use the existing local viewer server and verify the complete story: open the orientation scene, advance through seating, access, grading, and stage, confirm each camera/layer/evidence transition, then manually orbit, toggle a layer, select a tread, and return to a guided scene. Repeat with keyboard-only navigation and reduced motion. Confirm the planning-grade and Rule 9 disclosures remain accessible and the narrow-screen bottom sheet leaves the model primary.

- [ ] **Step 4: Exercise the non-WebGL fallback contract**

Force the renderer constructor to fail in a local test copy and confirm that the five scene titles, evidence values, sources, truth-tier labels, planning-grade disclosure, and Rule 9 status remain usable while the model failure is explained plainly.

- [ ] **Step 5: Publish with the Sites hosting workflow**

Invoke `sites:sites-hosting`, point it at the validated `dist/amphitheater-showcase/` build, follow its hosting metadata requirements, publish, and verify the returned URL loads the same static assets. Do not alter the authoritative geometry or data during publishing.

- [ ] **Step 6: Commit any hosting metadata created by the hosting workflow**

```bash
git add .openai/hosting.json
git commit -m "chore: configure amphitheater showcase hosting"
```

Skip this commit only if the hosting workflow does not create repository metadata.
