---
name: ai-drama-short-drama-characters
description: Run the governed shuohao character-analysis kernel for a short-drama project, validate exact source evidence, and import cast JSON, reports, image prompts, and voice prompts into Forging asset candidates. Use only when explicitly invoked or when delegated by ai-drama-short-drama.
---

# Short Drama Character Kernel

## Role

Run governed cast analysis and import stable cast candidates, source evidence, image prompts, and voice prompts. Do not lock assets or treat generated previews as identity evidence.

## Prerequisites

- Require an attached v2 governed project and an available registered source.
- Read `references/short-drama-prompt-governance.md`, `references/shuohao/workflow.md`, and its referenced character files.
- Run `prompt-context --stage characters --scope series`; require explicit prompt/dialogue language, style, aspect ratio, and candidate artifact.

## Execution

1. Place immutable prompt context before creative instructions.
2. Give every cast card a stable upstream `CNN` ID. Reuse it across regeneration and outline work; never bind by ordering alone.
3. Validate exact `persona.evidence` against source text. Treat unsupported appearance, voice, and generation prompts as inference/proposal.
4. Import with `short_drama_cli.py import-cast ... --prompt-context <context.json> --source <source>`.
5. Store TTS guidance under `visual_dna.voice`. Register actual preview media separately through visual-delivery records.

## Outputs

- Tier 1: canonical cast artifact, reports, voice/image prompts, and Forging asset candidates.
- Tier 2: optional preview media with hashes and QC records; candidate assets remain unlocked.
- Tier 3: only after dedicated Forging visual review, approved manifest evidence/locks, and delivery-manifest inclusion.

## Gates

- Exact evidence is observed/confirmed; prompts, inferred appearance, and previews are not.
- Never change or reuse an existing Forging ID. Removed upstream characters become retired mappings.
- Prompt-only or failed preview generation does not weaken cast import or downstream evidence gates.
- Profile language, style, aspect ratio, and scope cannot come from silent kernel defaults.

## Shared Links

- `references/short-drama-prompt-governance.md`
- `references/asset-contract.md`
- `references/visual-evidence.md`
- `references/delivery-contract.md`
- `schemas/prompt-context.schema.json`
- `schemas/asset-manifest.schema.json`
- `schemas/visual-delivery.schema.json`
