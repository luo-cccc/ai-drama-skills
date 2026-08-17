---
name: ai-drama-scene-design
description: 从已批准文字 DNA 或参考图设计并生成空间一致的影视场景。用于场景正交四视图、90 度顶视布局、演员动线、C1-C4 机位图和无缝 360x180 VR 全景，支持直接图像生成、确定性中文排版与 prompt-only 降级。
---

# AI Drama Scene Design

## Role

Build one scene deliverable from a stable spatial model. Preserve `SCENE-NNN`, topology, fixed assets, materials, lighting, coordinates, evidence, and continuity across every view.

## Prerequisites

- Read [scene-modes.md](references/scene-modes.md), [spatial-continuity.md](references/spatial-continuity.md), and shared visual evidence/layout and asset contracts.
- Choose one mode: `turnaround`, `top-view`, `camera-layout`, or `vr`.
- In project mode, load state, manifest, continuity, active profile, confirmed scene artifacts, and shot requirements. Standalone continuity is delivery-scoped.
- Require explicit report/prompt language, style, aspect ratio/projection, format, rights basis, and dimensions when fixed. Governed profile fields have no silent defaults.

## Execution

1. Resolve `SCENE-NNN` and linked `BG`/`PROP` IDs. Define Front, axes, boundaries, levels, openings, fixed furniture, routes, materials, light, time, and weather.
2. In reconstruction mode, inspect and retain primary references. In concept mode, mark hidden geometry and proposed materials as inference/proposal.
3. Check generation/editing/layout/VR capabilities and write an exact unlettered visual brief.
4. Generate, then inspect every raster individually. Repair topology, perspective, scale, light direction, camera placement, seams, poles, cropping, and asset drift.
5. Add labels deterministically when available; verify before/after composition and proofread.
6. Record files, hashes, dimensions, projection, evidence, decisions, failures, and QC in `visual-delivery`. Apply only approved manifest changes.

## Outputs

- `visual-brief-vNNN.md` with `prompt-only` status.
- Actual scene outputs in `visual-delivery`, with hashes and deterministic QC; unresolved visual/VR review remains incomplete.
- All required visual and projection reviews pass and files are included in the project delivery manifest. Delivery tier labels are project-level states in `delivery-contract.md`, not per-scene labels.

## Gates

- Prompts/previews cannot lock topology or asset facts; canonical manifest evidence controls locks.
- Generated/edited status requires decoded, nonblank, ratio-correct files and passing visual review.
- Equirectangular delivery requires 2:1 output plus seam/pole/spherical review. Ratio alone cannot pass VR QC.
- Failed, unreadable, uninspected, mirrored, inconsistent, or cropped outputs remain incomplete/failed.
- A changed locked scene requires a superseding locked-assets artifact with exact upstream dependencies and hash.

## Shared Links

- [scene-modes.md](references/scene-modes.md)
- [spatial-continuity.md](references/spatial-continuity.md)
- `references/visual-evidence.md`
- `references/visual-layout-contract.md`
- `references/asset-contract.md`
- `references/delivery-contract.md`
- `schemas/visual-delivery.schema.json`
- `schemas/delivery-manifest.schema.json`
