# Visual Evidence And Delivery

Choose one mode before visual work:

- `reconstruction`: preserve an existing design; requires at least one usable reference.
- `concept`: create a new design from a text brief; proposed details remain inferred until confirmed and may stay omitted or `unknown` when no decision is required.

When references conflict on identity, geometry, costume, or layout, ask for the primary reference. Preserve directly visible facts as `confirmed`, minimal structural completion as `inferred`, and unresolved areas as `unknown`.

Use the original reference in every revision, not only the previous generated result. Never present a different person, room, costume, or object as a successful refinement.

## Image Capability

Treat image generation as available only when the current runtime explicitly exposes an image-generation or image-editing tool/Skill and a real invocation returns a readable raster result. Invoke that capability directly with the approved references and brief; do not infer availability from the model name, runtime brand, or ability to write prompts. Classify failures as unavailable tool, rejected request, generation error, unreadable/blank output, or failed visual QC. Open and inspect every delivered raster individually at usable scale; verify nonblank output, requested aspect ratio, complete framing, view count, grid structure, identity, geometry, and prohibited elements. An HTML report may summarize inspected results but never substitutes for per-file raster inspection.

When the capability is absent or invocation fails without a repairable result, create `visual-brief-vNNN.md`, set delivery status to `prompt-only`, record the failure class, and include positive anchors, layout, evidence limits, and negative constraints. Do not claim an image was generated.

## Text In Images

Generate the visual base without complex Chinese text, then apply deterministic labels. If reliable typography is unavailable, deliver the text-free image plus a separate labels file. Reject garbled, duplicated, clipped, or invented labels.
