---
name: ai-drama-character-design
description: 从已批准文字 DNA 或参考图设计并生成身份一致的角色生产设定板。用于角色综合设定、角色三/四/六视正交图、表情表、动作表、服装拆解和角色道具板，支持直接图像生成、确定性中文排版与 prompt-only 降级。
---

# AI Drama Character Design

## Role

Produce one declared character-design mode while preserving stable identity, evidence, asset IDs, and project continuity. Use image generation/editing for artwork; do not programmatically redraw the character.

## Prerequisites

- Read [character-modes.md](references/character-modes.md), [visual-production.md](references/visual-production.md), and shared visual evidence/layout and asset contracts.
- Choose one primary mode: `comprehensive`, `orthographic`, `expression`, `pose`, `costume`, or `prop`.
- In project mode, load state, manifest, continuity, active profile, and confirmed character/costume/prop artifacts. In standalone mode, limit continuity claims to current inputs.
- Require explicit report/prompt language, style, aspect ratio, format, dimensions when fixed, and rights basis. Do not infer governed profile values silently.

## Execution

1. Resolve stable `CHAR-NNN` and linked asset IDs. Separate immutable anchors from mode-specific mutable fields.
2. In reconstruction mode, inspect and retain the primary reference in every pass. In concept mode, mark invented details as proposals until approved.
3. Check generation/editing/layout capabilities and create a compact unlettered visual brief with evidence and exclusions.
4. Generate or edit the raster, then inspect every output individually at usable scale. Repair identity, anatomy, projection, panels, continuity, crop, and layout failures.
5. Add labels deterministically when available; verify before and after composition and proofread all text.
6. Record outputs, hashes, dimensions, evidence, decisions, failures, and QC in schema-valid `visual-delivery` JSON. Apply only approved manifest facts.

## Outputs

- `visual-brief-vNNN.md` with `prompt-only` status and no generated-media claim.
- Actual unlettered/labeled outputs registered in `visual-delivery`, with hashes and deterministic checks; unresolved visual review remains incomplete.
- Required outputs that pass individual visual review and applicable layout QC, then appear in the project delivery manifest. Delivery tier labels (Planning complete / Generation-ready / Media delivered) are project-level states in `delivery-contract.md`, not per-plate labels.

## Gates

- Prompts and generated images do not lock identity facts. Only approved evidence updates the asset manifest.
- Never replace original reference evidence with a generated result.
- `generated`/`edited` requires readable nonblank outputs with matching aspect ratio; delivery inclusion requires passing visual review.
- Failed, blank, unreadable, uninspected, or misframed outputs remain `incomplete` or `failed`, never confirmed.
- A changed locked asset requires a superseding locked-assets artifact with exact screenplay/audit dependencies and manifest hash.

## Shared Links

- [character-modes.md](references/character-modes.md)
- [visual-production.md](references/visual-production.md)
- `references/visual-evidence.md`
- `references/visual-layout-contract.md`
- `references/asset-contract.md`
- `references/delivery-contract.md`
- `schemas/visual-delivery.schema.json`
- `schemas/delivery-manifest.schema.json`
