# Spatial Continuity and Visual QA

## Immutable Scene Anchors

Hold stable across all panels and versions unless an approved variant changes them:

- Boundary, width/depth relationship, level changes, floor and ceiling heights.
- Wall, column, beam, arch, stair, roof, and ceiling topology.
- Door and window count, wall placement, proportions, and opening direction.
- Fixed furniture, fixtures, hero props, spacing, orientation, and routes.
- Material assignment, construction, wear, palette, atmosphere, time, weather, and source lighting.

Never produce several similarly decorated but structurally different rooms.

## Conservative Closure

Extend visible axes, surfaces, seams, construction, and material logic only as far as necessary to close the space. Keep hidden regions low-detail. Do not invent extra doors, windows, stairs, mezzanines, functional zones, murals, monuments, or major furniture.

Use one evidence legend:

- Solid: `confirmed` (`已确认`).
- Short dashed or low-saturation translucent: `inferred` (`保守推定`).
- Dash-dot plus `待确认`: `unknown`.

Store matching evidence in the manifest. A polished rendering does not upgrade evidence.

## Camera, Movement, and Light

Keep camera position physically valid and routes clear of walls and fixed assets. Respect the established action axis, sightlines, entrance relationships, and movement direction when shot requirements exist. Use a neutral transition or axis-line camera when crossing the 180-degree line is necessary.

Carry natural and practical light sources through every view. Shadow direction, softness, length, reflection, exposure, white balance, time, and weather must agree. Do not independently relight each panel for appearance.

## Two-Pass Text

Generate the spatial artwork without labels, arrows, UI, signatures, logos, or watermarks. Then add simplified Chinese titles, `SCENE-NNN`, directions, C1-C4, routes, view cones, evidence marks, and legend through deterministic layout. Keep labels short, avoid covering geometry, and proofread all text and IDs.

If layout is unavailable, provide the unlettered image plus `scene-SCENE-NNN-labels-vNNN.txt`; mark the labeled deliverable incomplete.

## Prompt-Only Brief

Include scene ID and mode, source/evidence summary, coordinate system, immutable anchors, inferred and pending regions, exact panel or spherical map, camera/projection, materials and lighting, positive prompt, negative constraints, size/ratio/format, label plan, and mode-specific QC.

## Quality Gate

Inspect the final pixels. Reject and repair when any of these occur:

- Boundary, opening, structure, furniture, prop, material, time, weather, or lighting drifts across views.
- Left/right mirroring, broken topology, impossible closure, mismatched scale, or conflicting floor/ceiling lines.
- Camera/view cone mismatch, wall penetration, blocked route, unusable clearance, or unmotivated axis break.
- Orthographic views contain perspective; top view is oblique; camera layout becomes CAD; VR is not a true 2:1 sphere.
- Extra assets, people, animals, filming equipment, story action, external scenery, unintended brands, or protected designs appear.
- Panels are missing, duplicated, cropped, illegible, or overcrowded.
- IDs or Chinese labels are wrong, corrupt, or placed over critical structure.

Record unresolved failures and mark the project artifact `invalid` or `pending-confirmation`; never mark a failed image `confirmed`.
