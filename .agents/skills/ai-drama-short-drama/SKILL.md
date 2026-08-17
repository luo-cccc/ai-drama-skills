---
name: ai-drama-short-drama
description: Govern a complete novel-to-short-drama project with a production brief, cast, outline checkpoints, three-episode screenplay batches, evidence audits, H3 storyboards, scoped shot plans, asset governance, recovery, and final aggregation. Use for 小说改短剧、短剧全流程、短剧执行引擎, or projects whose format is ai-short-drama-series.
---

# Short Drama Orchestrator

## Role

Govern the complete short-drama series. Forging owns project state, evidence, IDs, authorization, aggregation, and completion; the five adapted kernel Skills execute creative stages.

## Prerequisites

- Require episode count, exact episode duration, genre, adaptation mode, language profile, visual style, aspect ratio, generator profile, and explicit brief authorization.
- Run `attach` before outline work. If attachment is `conversion-required`, preserve the confirmed legacy outline and complete the five-part conversion decision before continuing.
- If project state is v1, run `state_cli.py migrate-project --dry-run` and explicitly choose migration or v1 compatibility. Governed v2 imports require migration.
- Run `recover` before any operation when a transaction is unfinished.

## Execution

1. Before every creative stage, run `prompt-context` for the exact stage and scope. Prepend the returned immutable JSON; do not summarize it or silently fill profile fields.
2. Run characters, outline skeleton, confirmed series outline, art, screenplay batches of at most three contiguous episodes, canonical audits, and storyboards in order.
3. Require a canonical JSON audit for every screenplay range and a full-series audit before aggregation.
4. Import storyboard ranges only when screenplay and audit scopes match exactly. Each import creates the governed storyboard, scoped shot plan, H3 prompts, and generation manifest.
5. Run `aggregate-shot-plan` only after confirmed scoped plans cover every episode without gaps or overlaps. Run `complete` only after all completion gates pass.

## Outputs

- `short-drama-engine.json` as operational state, never creative authority.
- Canonical cast, outline, screenplay, audit, storyboard, asset, scoped shot-plan, generation-manifest, and delivery-manifest artifacts.
- A versioned immutable series shot-plan snapshot plus root `shot-plan.json` as its exact projection.
- Tier 1 canonical plans, Tier 2 generation packages, and Tier 3 verified media according to the actual requested delivery.

## Gates

- Governed prompt context must contain explicit report, prompt, and dialogue languages; style; aspect ratio; exact target timing; generator; and profile-derived H3 dialogue tag. No silent defaults.
- Source dialogue remains verbatim in the source language; machine prompts use configured `prompt_language`.
- Validator success never creates an audit decision. `$ai-drama-script-audit` owns canonical audit JSON.
- H3 segment IDs are `generation_group`, not narrative beats. Each cut maps to one Forging beat and one shot.
- Every episode and scoped storyboard closes exactly in integer milliseconds. `±15%` is screenplay estimation only and cannot authorize storyboard or project completion.
- Imported prompts and previews remain unlocked. Required production assets must be locked through Forging evidence workflows.
- A generation manifest must match shot groups, prompts, hashes, assets, beats, and absolute timing.
- Completion requires a valid series audit, immutable aggregate/projection equality, exact series timing, locked required assets, and a complete confirmed delivery manifest when `delivery_required=true`.

## Shared Links

- `references/workflow-contract.md`
- `references/data-contract.md`
- `references/short-drama-prompt-governance.md`
- `references/evidence-audit.md`
- `references/timeline-contract.md`
- `references/delivery-contract.md`
- `schemas/short-drama-engine.schema.json`
- `schemas/prompt-context.schema.json`
- `schemas/generation-manifest.schema.json`
- `schemas/delivery-manifest.schema.json`
