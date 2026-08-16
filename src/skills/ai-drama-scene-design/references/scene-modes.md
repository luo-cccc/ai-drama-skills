# Scene Design Modes

## Turnaround

Generate Front, Left, Right, and Back as four orthographic views of one scene. Use equal scale, floor and ceiling baselines, fixed light, and a shared cut-wall protocol: hide only the wall facing the current camera, retain its openings as light outlines, and never move other structure or furniture.

Define directions in scene coordinates. Left and Right are not mirrors. Keep parallel lines parallel; reject wide-angle distortion, three-quarter perspective, tilt, depth blur, and independent relighting. Show material and color samples only when they are traceable to visible scene assets.

## Top View

Generate a true 90-degree overhead spatial visual, not an oblique bird's-eye illustration. Show complete boundary, wall thickness logic, openings and swing direction, columns, stairs, level changes, furniture footprints and orientation, fixed props, functional zones, and usable routes.

When story or shot requirements exist, add character routes, action positions, axis, camera positions, directions, and view cones. Without story requirements, show only primary circulation and clearly label camera suggestions as proposals. Do not invent exact engineering dimensions; use relative scale or known references.

## Camera Layout

Use one horizontal board with four equal C1-C4 view panels and one shared high three-quarter cutaway or perspective layout. Every camera must exist in the lower layout, avoid walls and furniture, and point toward content actually visible in its matching panel.

- C1: 24 mm or 35 mm establishing view of orientation and hero area.
- C2: 35 mm side relationship with at least two C1 anchors.
- C3: 50 mm material or craft detail that remains locatable in the room.
- C4: 24 mm or 35 mm functional area, route, or complementary coverage.

Show camera position, direction, and view cone. Preserve verticals and avoid extreme distortion. Keep future performance and equipment clearance usable. The layout is a materialized production visualization, not CAD, a wireframe, or a flat diagram.

## VR Panorama

Deliver a true equirectangular complete sphere:

- Horizontal field: 360 degrees.
- Vertical field: 180 degrees.
- Aspect ratio: exactly 2:1.
- Viewpoint: natural eye height inside free space.
- Horizon: level, with no roll.
- Coverage: front, right, back, left, zenith, and nadir from one continuous place.

Plan a primary front landmark, connected right and left spaces, a non-duplicated rear view, complete zenith, and continuous ground or floor at nadir. Keep near, middle, and far depth. Avoid placing strong vertical edges or hero objects on the wrap seam.

Prefer 8192 x 4096; use at least 4096 x 2048 when constrained. Use PNG by default, high-quality JPEG when size matters, and HDR/EXR only when requested and supported. Do not stretch a normal perspective image or stitch unrelated views and call it VR.

Validate by checking exact ratio, rolling the panorama horizontally 50 percent to expose the seam, and inspecting six cube directions or a spherical viewer. Reject broken wrap, duplicated assets, tilted horizon, polar holes, spirals, severe stretch, visible camera/body, text, logo, or UI. If the runtime cannot perform seam, pole, and spherical-view inspection, use top-level status `incomplete` and record `qc-incomplete` as the QC marker/failure class; do not infer VR validity from a 2:1 thumbnail or HTML preview.
