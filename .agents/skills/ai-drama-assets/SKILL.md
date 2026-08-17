---
name: ai-drama-assets
description: 从剧本、分场、故事或镜头方案提取并维护可生产的影视资产清单和视觉 DNA。用于资产提取、角色/物理场景/道具稳定 ID、别名、变体、证据等级、锁定状态、视觉连续性锚点和图像生成简报；不用于直接渲染图像。
---

# AI Drama Assets

## Role

Extract reusable production assets and causally critical one-use props. Maintain canonical identity, evidence, visual DNA, variants, and locks; do not render media or rewrite story content.

## Prerequisites

- Read [asset-extraction.md](references/asset-extraction.md), [manifest-contract.md](references/manifest-contract.md), and shared data/asset contracts.
- In project mode, load project state, the complete current manifest, relevant confirmed artifacts, and continuity ledger entries.
- For a v1 project, make the project migration decision first. The current `apply-manifest` write path still accepts asset-manifest schema `1.0`; preserve v1 evidence and do not hand-flip the manifest to `2.0`. Use v2 claim semantics only when an approved compatible migration/write path is available.
- In standalone mode, limit IDs and continuity claims to the current delivery.

## Execution

1. Freeze source scope and hashes. Extract candidates needing reuse, continuity, deliberate design, or stable treatment for a material causal event.
2. Preserve IDs and aliases. Allocate `CHAR`, `SCENE`, `PROP`, `MOTIF`, `COSTUME`, and `BG` IDs by type; create `-VNN` only for reusable visual variants.
3. Record claim-level evidence: v1 `confirmed/inferred/unknown`; v2 `observed/inferred/proposed/unknown` with required provenance fields.
4. Build a complete candidate manifest at `current + 1`; preserve unknown valid fields and never weaken supported locks.
5. Apply atomically with `state_cli.py apply-manifest --expected-version <current>`, then validate IDs, variants, references, evidence, lock support, dependencies, and hashes.

## Outputs

- Canonical `asset-manifest.json` and versioned human-readable `asset-dna-vNNN.md` derivative.
- Unresolved confirmations, stale-lock notices, and exact upstream dependencies.
- Prompt-ready briefs may support planning, but assets become delivered media only through separate visual generation, manifest registration, and QC. Delivery tier labels are project-level states in `delivery-contract.md`.

## Gates

- JSON is authoritative; Markdown and preview images cannot change IDs, evidence, lock state, or visual DNA.
- Lock only continuity-critical fields with supported evidence. `partial` lists `locked_fields`; upstream changes make affected locks `stale`.
- A confirmed `locked-assets` artifact binds the exact `asset-manifest.json` hash and depends on the confirmed screenplay plus valid audit.
- Never create duplicate canonical assets, recycle IDs, orphan variants, or upgrade prompts/previews to evidence.
- Manifest updates are complete version-checked replacements, not hand-edited row patches.

## Shared Links

- [manifest-contract.md](references/manifest-contract.md)
- `references/data-contract.md`
- `references/asset-contract.md`
- `references/visual-evidence.md`
- `references/delivery-contract.md`
- `schemas/asset-manifest.schema.json`
- `schemas/visual-delivery.schema.json`
