---
name: ai-drama-short-drama-script
description: Run the governed shuohao screenplay kernel in contiguous batches of at most three episodes, validate against confirmed upstream structure, create a scoped evidence audit, and record the screenplay checkpoint. Use only when explicitly invoked or delegated by ai-drama-short-drama.
---

# Short Drama Screenplay Kernel

## Role

Generate one governed contiguous screenplay batch and pair it with a canonical scoped conformance audit. Reports are derivatives and cannot authorize storyboard work.

## Prerequisites

- Require a v2 governed project and confirmed series outline.
- Read `references/short-drama-prompt-governance.md`, `references/shuohao/workflow.md`, script pass, schema, and shared evidence contract.
- Run `prompt-context --stage script --scope START-END`; require explicit languages, target runtime, episode duration, and candidate artifact.

## Execution

1. Place immutable prompt context before creative instructions.
2. Generate at most three contiguous episodes, preserving confirmed structure and source-language dialogue.
3. Pass adapted validation against outline, cast, and art where available. `±15%` is allowed only as screenplay-stage duration estimation.
4. Invoke `$ai-drama-script-audit` in conformance mode and produce immutable `audit-report.schema.json` JSON bound to exact screenplay path/hash and upstream basis.
5. Import screenplay plus audit with explicit authorization. Supersede overlapping confirmed ranges before replacement.

## Outputs

- Canonical scoped screenplay JSON and derived reports.
- Canonical scoped `audit-vNNN.json`; project `audit_result` is derived from its arrays and decision.
- A checkpoint naming exact screenplay and audit artifact IDs, hashes, range, and authorization.

## Gates

- Governed imports require matching prompt-context hash, project revision, scope, candidate artifact, and expected output schema.
- Validator success never creates an audit decision.
- Markdown or a v1 audit marker cannot authorize v2 storyboard work.
- Formal storyboard timing must later close exactly; screenplay `±15%` cannot pass storyboard import.
- Overlapping active screenplay/audit ranges must be superseded before replacement.

## Shared Links

- `references/short-drama-prompt-governance.md`
- `references/evidence-audit.md`
- `schemas/prompt-context.schema.json`
- `schemas/audit-report.schema.json`
