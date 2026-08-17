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
2. Run characters, outline skeleton, confirmed series outline, art, then screenplay batches of at most three contiguous episodes. Import each screenplay without `--confirm` first, generate an audit context, then run `confirm-screenplay` to confirm the screenplay and its exact-target conformance audit atomically; a `pending-confirmation` candidate never supersedes confirmed work or evolves governance state.
3. Register story facts and world rules as `canon.json` claims before screenplay batches (`canon register`); the outline confirmation seeds `hook-ledger.json` from major beats, and each confirmed screenplay evolves both deterministically. Both are stored as immutable versioned snapshots bound in `short-drama-engine.canonical_state`, with root projections; `rebuild-governance` recovers a drifted ledger.
4. Require a canonical JSON audit for every screenplay range and a full-series audit before aggregation.
5. Import storyboard ranges only when screenplay and audit scopes match exactly. Each import creates the governed storyboard, scoped shot plan, H3 prompts, and generation manifest.
6. Run `aggregate-shot-plan` only after confirmed scoped plans cover every episode without gaps or overlaps. Register the series delivery manifest via `import-delivery` when `delivery_required=true`, then run `complete` only after all completion gates pass, including the hook-debt gate (unresolved hooks planted before the final episode block completion).

## Outputs

- `short-drama-engine.json` as operational state, never creative authority.
- Canonical cast, outline, screenplay, audit, storyboard, asset, scoped shot-plan, generation-manifest, and delivery-manifest artifacts.
- Immutable `hook-ledger` / `canon` governance snapshots plus `canon-register` inputs and byte-identical root projections, all bound in `short-drama-engine.canonical_state`.
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
- `references/episode-drama-contract.md`
- `references/evidence-audit.md`
- `references/timeline-contract.md`
- `references/delivery-contract.md`
- `schemas/short-drama-engine.schema.json`
- `schemas/prompt-context.schema.json`
- `schemas/episode-contract.schema.json`
- `schemas/hook-ledger.schema.json`
- `schemas/canon.schema.json`
- `schemas/generation-manifest.schema.json`
- `schemas/delivery-manifest.schema.json`
