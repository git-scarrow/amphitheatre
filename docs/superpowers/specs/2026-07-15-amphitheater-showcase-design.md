# Amphitheater Showcase Website Design

**Date:** 2026-07-15  
**Status:** Approved for implementation planning

## Purpose

Create a public-facing technical review website for the Petoskey Pit Open Civic Bowl. The primary audience is technical design reviewers, followed by city decision-makers. The existing interactive Three.js model is the centerpiece. Evidence appears alongside and on top of the exact model geometry it supports so reviewers can move between spatial understanding, quantitative claims, and source provenance without leaving the experience.

The website remains explicit that the work is planning-grade, not stamped engineering. Validated, provisional, illustrative, and unknown information must never be blended or presented with equal certainty.

## Selected Visual Direction

Use the approved **Cinematic Evidence Scrubber** direction:

- A full-viewport model canvas in deep civic green-black (`#07110F`).
- Luminous mint (`#9EE9C3`) for validated technical geometry.
- Amber (`#F3B958`) for provisional findings and open decisions.
- Cyan (`#86D7E6`) for grading and terrain evidence.
- Editorial serif headings paired with compact sans-serif interface typography.
- Translucent evidence cards that connect to relevant model geometry.
- A persistent bottom scene scrubber that coordinates camera, model layers, highlights, and evidence.

The design should feel compelling enough for a city presentation while remaining legible, restrained, and technically credible.

## Core Experience

The site opens directly into the existing interactive model rather than a conventional marketing hero. A concise title, planning-grade status, and basic model controls sit over the canvas without obscuring it.

The bottom scrubber guides reviewers through five evidence scenes:

1. **Site and bay-view orientation** — establish the Petoskey Pit, the civic bowl, the stage-to-audience relationship, and the Little Traverse Bay view axis.
2. **Seating capacity and sightlines** — show the seating treads and Band-A audit geometry with the current nominal and strict seat counts.
3. **Accessible circulation** — isolate ADA routes, landings, cross-aisle geometry, and the remaining survey/code caveats.
4. **Grading and earthwork** — compare existing and proposed terrain, reveal cut/fill information, and preserve the planning-grade quantity warning.
5. **Provisional stage decision** — show the inherited stage geometry, audience-axis mismatch, lateral offset, and the open Rule 9 adoption decision.

Changing scenes updates the camera, visible layers, highlighted geometry, evidence cards, and model annotations as one synchronized transition. Reviewers may leave the guided sequence at any time to orbit or pan the model, select rows, switch layers, or use camera presets. Returning to a scene restores its intended evidence state.

## Evidence and Provenance

Evidence content is defined in a small scene manifest rather than scattered through interface code. Each scene entry specifies:

- Stable scene identifier and display order.
- Camera preset.
- Visible model layers.
- Geometry or region to emphasize.
- Headline metric and supporting explanation.
- Truth tier: validated, provisional, illustrative, or unknown.
- Source artifact label and path.
- Required caveat or unresolved decision.
- Optional annotation position and transition behavior.

`web_viewer/data/site_data.js` remains the geometry and audit source of truth. The presentation layer reads existing model data and coordinates the active scene with the viewer, scrubber, annotations, and evidence cards. It does not recompute or strengthen claims.

Evidence cards use realistic project values from current authoritative artifacts, including:

- 1,283 nominal seats.
- 1,243 strict Band-A seats.
- 500.8 CY gross planning-grade earthwork for the validated Scenario E control.
- Stage Rule 9 status as open and provisional.
- Existing pass, warn, fail, and unknown audit states.

Every claim with a quantitative or acceptance implication names its source. Unknown or missing information remains visibly unknown.

## Interface Components

### Model Canvas

Preserve and adapt the existing Three.js viewer, its local data payload, model selection behavior, layer system, camera presets, compass, and graceful non-WebGL behavior. The viewer remains the dominant surface at desktop and mobile sizes.

### Scene Scrubber

A persistent bottom rail presents five numbered evidence scenes. Selecting a scene changes the coordinated model and evidence state. Previous and next controls, arrow keys, and touch targets support sequential review. The selected state is visually clear without relying on color alone.

### Spatial Annotations

Annotations identify the relevant seat bands, routes, terrain areas, or stage geometry. They remain concise, avoid excessive overlap, and do not pretend to be surveying dimensions. Selecting an annotation opens its evidence card.

### Evidence Cards

Cards contain a metric or finding, truth-tier badge, short interpretation, source reference, and caveat where required. On desktop they float near related geometry. On narrow screens they become a bottom sheet above the scrubber so the model retains priority.

### Utility Controls

Camera presets, model layers, truth-tier legend, help, and project disclosure live in compact overlays. They remain available outside the guided scenes. The planning-grade notice and provisional stage status remain persistently accessible.

## Interaction and Accessibility

- Preserve orbit, pan, zoom, selectable rows, camera shortcuts, and reset behavior.
- Make all guided scenes, evidence cards, annotations, and utility controls keyboard accessible.
- Use visible focus states and semantic button labels.
- Provide touch targets suitable for tablets used during review meetings.
- Respect reduced-motion preferences by replacing camera interpolation and card movement with immediate state changes.
- Do not rely on color alone for truth tier or audit status.
- Keep evidence text readable over the model with sufficient contrast and controlled translucency.
- On smaller screens, collapse secondary controls and place evidence in a dismissible bottom sheet.

## Failure and Fallback Behavior

If WebGL is unavailable, replace the model canvas with a clear notice while keeping the evidence sequence, source references, status tiers, and disclosures usable. This preserves the project's existing progressive fallback.

If a scene references missing geometry or evidence, show that item as unavailable and retain its source/caveat context. Do not hide the scene, invent fallback data, or present an unsupported claim.

If a transition cannot apply a camera or layer state, keep the viewer operable and show the evidence card without claiming that the geometry is highlighted.

## Responsive Behavior

Desktop and large-tablet layouts use the full cinematic canvas with floating annotations and evidence cards. The scrubber remains anchored to the bottom edge.

On narrow screens, the model stays full height behind a compact header. Evidence cards become a bottom sheet, the scrubber becomes horizontally scrollable, and nonessential utility controls move into a menu. The experience remains a model review tool rather than collapsing into a static article.

## Verification

Implementation verification must cover:

- The existing model loads from the current local data payload.
- Orbit, pan, zoom, selection, reset, camera presets, and layer toggles still work.
- All five scenes apply their camera, layer, highlight, annotation, and evidence state.
- Displayed evidence values and source labels match current project artifacts.
- Planning-grade, provisional, illustrative, and unknown states are distinguishable.
- Keyboard, touch, focus, and reduced-motion behavior work.
- Desktop, tablet, and narrow-screen layouts preserve model priority.
- The non-WebGL fallback retains the complete evidence narrative and disclosures.
- The production build completes successfully.

## Scope Boundaries

This first version does not redesign amphitheater geometry, change authoritative project data, add collaborative comments, add authentication, or create a new persistent data store. It presents the current design and evidence more effectively. The existing repository remains the acceptance authority; the website is a review and communication surface.
