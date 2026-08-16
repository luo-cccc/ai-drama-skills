---
name: ai-drama-forging
description: 编排从影视创意、成熟故事或既有剧本到制作提示包、分场、标准剧本、证据审计、数字资产、视觉设计、分镜、AI 视频提示和拉片复盘的可追溯工作流。用于跨两个以上阶段的完整项目、查询或恢复 project-state.json 项目状态、判断下游资格、协调多个 AI Drama Forging 领域 Skill；已有项目中的单一明确编剧、审计、资产、角色、场景、分镜或拉片任务仍直接使用对应领域 Skill。
---

# AI Drama Forging

## Role

Orchestrate cross-stage work and project state. Route each creative output to its owning Skill; do not duplicate domain execution inside this Skill.

## Prerequisites

- Read `references/workflow-contract.md`, `references/data-contract.md`, and rights guidance when relevant.
- Validate an existing project before using its approvals or hashes.
- Register available sources with authority, trust, rights, and SHA-256. Missing sources remain explicit.

For `project-state.json` schema `1.0`, make a migration decision before governed v2 work:

```powershell
python scripts/state_cli.py migrate-project --project-dir <project> --dry-run
```

Apply with `--apply` only after reviewing snapshots, defaults, and invalidations. Otherwise remain in documented v1 compatibility mode; do not claim v2 prompt-context, canonical-audit, or completion guarantees.

## Execution

1. Route concept work to `$ai-drama-development`, short-drama series to `$ai-drama-short-drama`, screenplay work to `$ai-drama-screenplay`, audit to `$ai-drama-script-audit`, assets to `$ai-drama-assets`, visuals to the character/scene Skills, storyboards to `$ai-drama-storyboard`, and reverse analysis to `$ai-drama-shot-analysis`.
2. Read the artifact graph and latest checkpoint. Bind every approval to exact artifact IDs and scope.
3. Require eligible confirmed upstream artifacts before formal downstream work.
4. For governed creative stages, create the schema-valid prompt context and pass it unchanged before task instructions. Never replace exact IDs, hashes, profile, scope, or `must_not_modify` with prose.
5. Register outputs, dependencies, hashes, status, and authorization through the repository CLIs. Validate after every material update.

## Outputs

- Canonical JSON for project state, audits, assets, timed shots, generation manifests, and delivery manifests.
- Versioned immutable artifacts for confirmed revisions; Markdown, HTML, prompts, and media are derivatives or deliveries.
- A concise handoff: stage, artifact IDs and paths, gate result, limitations, and next eligible stage.

Use these delivery tiers as documentation labels, not new schema fields:

- **Tier 1 - canonical plan:** validated canonical JSON and human-readable derivatives; may be `prompt-only`.
- **Tier 2 - generation package:** Tier 1 plus a generation manifest binding groups, prompts, hashes, shots, beats, assets, and absolute timing.
- **Tier 3 - verified media:** Tier 2 plus actual media, hashes, dimensions/duration, and passing required QC in a visual or delivery manifest.

## Gates

- JSON is authoritative for status, IDs, configuration, timing, and evidence. Markdown cannot authorize v2 work.
- A formal v2 audit is immutable canonical JSON; its six-key `audit_result` is derived, never hand-counted.
- Production shots and locked assets require the exact confirmed screenplay plus a valid audit.
- A series aggregate is a versioned immutable snapshot. Root `shot-plan.json` is only its byte-equivalent projection and must never become an independently edited source.
- Upstream changes supersede or invalidate affected artifacts and make affected locks `stale`.
- Never upgrade `prompt-only`, incomplete, uninspected, or failed media to a generated or complete claim.

## Shared Links

- `references/workflow-contract.md`
- `references/data-contract.md`
- `references/evidence-audit.md`
- `references/delivery-contract.md`
- `schemas/prompt-context.schema.json`
- `schemas/audit-report.schema.json`
- `schemas/generation-manifest.schema.json`
- `schemas/delivery-manifest.schema.json`
