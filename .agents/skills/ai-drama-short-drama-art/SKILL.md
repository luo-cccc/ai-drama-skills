---
name: ai-drama-short-drama-art
description: Run the governed shuohao art kernel for scenes and narrative props, normalize safe styles, and import visual DNA and previews without locking assets. Use only when explicitly invoked or delegated by ai-drama-short-drama after a confirmed series outline.
---

# Short Drama Art Kernel

## Role

Run governed scene/prop concept development and import visual DNA plus optional previews. This Skill creates candidates, not locked production assets or final media delivery.

## Prerequisites

- Require a confirmed series outline and v2 governed project.
- Read `references/short-drama-prompt-governance.md`, `references/shuohao/workflow.md`, and its scene, prop, schema, style, and sheet references.
- Run `prompt-context --stage art --scope series`; require explicit prompt language, style, aspect ratio, and generator profile.

## Execution

1. Place immutable prompt context before creative instructions; do not use kernel language/style/ratio defaults.
2. Produce schema-valid scene and prop JSON with anchors, states, lighting, scale, usage, prompts, and evidence limits.
3. Normalize legacy named-style values to `hand-painted-cel`; never request imitation of a protected named style.
4. Import with `short_drama_cli.py import-art ... --prompt-context <context.json>`.
5. Register actual preview images only through visual-delivery records with files, hashes, dimensions, capability result, and QC status.

## Outputs

- Tier 1: canonical imported art candidates and prompt-only briefs.
- Tier 2: preview media registered with visual-delivery evidence; assets remain `unlocked`.
- Tier 3: only after Forging character/scene design workflows review, approve, manifest-lock, and include required media in a delivery manifest.

## Gates

- Prompt context must match project revision, scope, candidate artifact, and profile.
- Prompts or previews never become confirmed evidence automatically and cannot lock assets.
- No image capability means `prompt-only`; generated but uninspected/failed-QC media remains incomplete.
- Upstream outline changes supersede affected art candidates and make dependent locks stale.

## Shared Links

- `references/short-drama-prompt-governance.md`
- `references/visual-evidence.md`
- `references/asset-contract.md`
- `references/delivery-contract.md`
- `schemas/prompt-context.schema.json`
- `schemas/visual-delivery.schema.json`
- `schemas/delivery-manifest.schema.json`
