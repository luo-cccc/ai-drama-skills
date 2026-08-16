---
name: ai-drama-short-drama-storyboard
description: Run the governed shuohao H3 storyboard kernel for an audited screenplay range, preserve exact prompt alignment, and convert every cut into model-neutral Forging beats and shots on an absolute series timeline. Use only when explicitly invoked or delegated by ai-drama-short-drama.
---

# Short Drama Storyboard Kernel

## Role

Run the adapted H3 storyboard kernel inside Forging governance and import its engine output as canonical scoped shots plus a generation package. This Skill is not the standalone kernel interface.

## Prerequisites

- Require v2 governed project state, an attached short-drama engine, and a confirmed screenplay plus valid canonical audit with the exact same episode scope.
- Read `references/short-drama-prompt-governance.md`, `references/shuohao/workflow.md`, and its frame, H3 prompt, schema, and storyboard-pass references.
- Run `prompt-context --stage storyboard --scope START-END` before generation.

## Execution

1. Pass the immutable prompt context before creative instructions. Require explicit `profile.prompt_language`, `profile.dialogue_language`, `profile.aspect_ratio`, `profile.target_runtime_ms`, `profile.exact_storyboard_timing=true`, and profile-derived `h3.dialogue_tag`; do not use kernel defaults.
2. Validate the adapted storyboard against the exact screenplay, outline, cast, and art inputs. Preserve source dialogue verbatim inside the governed dialogue tag.
3. Import through `short_drama_cli.py import-storyboard ... --prompt-context <context.json> --authorization ...`.
4. Map every cut to one `BEAT-NNN` and one `SHOT-NNN`. Preserve the H3 segment only as `generation_group`.
5. Keep integer-millisecond absolute series time. Treat one generation group as one model call; editing containers may assemble calls but cannot redefine group identity.

## Outputs

- Versioned governed storyboard JSON and derived Markdown/HTML reports.
- Versioned scoped `shot-plan` JSON as canonical timing and asset truth.
- H3 `prompt.md` files and canonical `generation-manifest` JSON binding prompt hashes, shots, beats, assets, groups, and absolute ranges.
- Tier 1 after validated canonical plan import; Tier 2 after the generation manifest and prompt files reconcile; Tier 3 only after separately delivered media passes manifest-backed QC.

## Gates

- No silent prompt-language, dialogue-tag, aspect-ratio, style, generator, or timing defaults in governed mode.
- Every cut duration converts losslessly to integer milliseconds; every episode and scope closes exactly at its configured boundary.
- The screenplay `±15%` estimate is never a formal storyboard closure rule.
- Prompt alignment lines, cut timestamps, camera terms, language, and tagged dialogue must reconcile exactly.
- Generation-manifest groups must equal shot-plan `generation_group` values and prompt SHA-256 values must match files.
- The scoped plan may feed aggregation only while confirmed and unsuperseded.

## Shared Links

- `references/short-drama-prompt-governance.md`
- `references/timeline-contract.md`
- `references/data-contract.md`
- `references/delivery-contract.md`
- `schemas/prompt-context.schema.json`
- `schemas/shot-plan.schema.json`
- `schemas/generation-manifest.schema.json`
