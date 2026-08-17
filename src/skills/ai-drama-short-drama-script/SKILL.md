---
name: ai-drama-short-drama-script
description: Run the governed shuohao screenplay kernel in contiguous batches of at most three episodes, validate against confirmed upstream structure, create a scoped evidence audit, and record the screenplay checkpoint. Use only when explicitly invoked or delegated by ai-drama-short-drama.
---

# Short Drama Screenplay Kernel

## Role

Generate one governed contiguous screenplay batch and pair it with a canonical scoped conformance audit. Reports are derivatives and cannot authorize storyboard work.

## Prerequisites

- Require a v2 governed project and confirmed series outline.
- Import without `--confirm` only creates a `pending-confirmation` candidate; it does not supersede confirmed work or evolve hook/canon. Generate `prompt-context --stage audit`, then run `confirm-screenplay --screenplay ART-NNN --audit-report audit.json` for the atomic confirmation path.
- Read `references/short-drama-prompt-governance.md`, `references/episode-drama-contract.md`, `references/shuohao/workflow.md`, script pass, schema, and shared evidence contract.
- Run `prompt-context --stage script --scope START-END`; require explicit languages, target runtime, episode duration, and candidate artifact. When the scope does not start at episode 1, the context carries `previous_handoff`.

## Execution

1. Place immutable prompt context before creative instructions.
2. Generate at most three contiguous episodes, preserving confirmed structure and source-language dialogue. Every episode carries a `contract` object per `episode-drama-contract.md` and `episode-contract.schema.json`; the contract executes the beats, hook/suspense, and payoff positions planned in the confirmed outline, it does not re-plan them.
3. Carry every fact from `previous_handoff.handoff_state` into the first episode's `incomingState`; the last episode's `handoffState` seeds the next batch. Incoming state is a continuity boundary, not a creative choice.
4. Declare hook actions only as open/advance/resolve/defer; `advance` and `resolve` must name 1-3 screen-visible evidence carriers. Never manufacture hooks to fill a quota.
5. Pass adapted validation against outline, cast, and art where available. `±15%` is allowed only as screenplay-stage duration estimation.
6. Run `script-quality --input <draft> --previous <preceding confirmed screenplay JSON>` and fix every error; warnings are judgment calls.
7. Invoke `$ai-drama-script-audit` in conformance mode and produce immutable `audit-report.schema.json` JSON bound to exact screenplay path/hash and upstream basis.
8. Import the candidate with `import-script` (no `--confirm`), generate `prompt-context --stage audit`, then run `confirm-screenplay --screenplay ART-NNN --audit-report audit.json --prompt-context audit-context.json --authorization ...` to confirm screenplay and audit atomically. Superseding overlapping confirmed ranges is part of that atomic confirmation, not a separate manual step.

## Outputs

- Canonical scoped screenplay JSON (episodes carry a per-episode `contract`) and derived reports.
- Canonical scoped `audit-vNNN.json`; project `audit_result` is derived from its arrays and decision.
- A checkpoint naming exact screenplay and audit artifact IDs, hashes, range, and authorization.

## Gates

- Governed imports require matching prompt-context hash, project revision, scope, candidate artifact, and expected output schema.
- When the project configuration sets `episode_contract_required`, episodes without a valid contract are rejected at import: schema shape, non-empty contract fields, a causal chain with a citable escalation, a paid cost, outgoing pressure, a concrete emotional hook question, and evidence carriers on advance/resolve hook actions.
- Hook actions must reference hooks that exist in `hook-ledger.json`; advance/resolve evidence carriers must echo in the visible script text.
- Canon claim gates are hard: a `secret_truth` may not appear in the visible surface before its reader reveal episode, prohibitions must not be touched, hard rules cannot be bypassed without their declared cost, and non-generalizable claims must not spread to the cast at large. A claim scheduled for reader reveal this episode without a visible landing surfaces as an import `warnings` entry — use `script-quality --canon` to catch it before import.
- Validator success never creates an audit decision.
- Markdown or a v1 audit marker cannot authorize v2 storyboard work.
- Formal storyboard timing must later close exactly; screenplay `±15%` cannot pass storyboard import.
- Overlapping active screenplay/audit ranges must be superseded before replacement.

## Shared Links

- `references/short-drama-prompt-governance.md`
- `references/episode-drama-contract.md`
- `references/evidence-audit.md`
- `schemas/prompt-context.schema.json`
- `schemas/audit-report.schema.json`
- `schemas/episode-contract.schema.json`
