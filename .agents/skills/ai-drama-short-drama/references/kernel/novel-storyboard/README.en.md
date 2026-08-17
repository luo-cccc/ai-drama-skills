[中文](README.md) · **English**

# novel-storyboard

Turns `novel-script` beats into a three-level execution structure:

```text
segment = one video-generation call, never crossing a scene
  cut = an edit inside the segment claiming contiguous script beats
    frame = one keyframe per cut, pinned at zero or that cut mark
  h3Prompt = one per segment; alignment and [Shot k] times derive from cuts
```

## Two Modes

### Standalone Kernel

Run the CLI in this directory. The self-contained kernel permits local defaults: `promptLang=en`, `style=realistic`, default segment/cut ranges, and `tolerance=0.15`. `validate` checks beat coverage, duration, dialogue fit, H3 structure, language, style, camera terms, and references.

The standalone episode `±15%` rule is only a local integrity gate. The root `manifest.json` created by `export` is a local H3 file list, not a Forging canonical generation manifest and not project authorization.

### Forging Governed Mode

Owned by `ai-drama-short-drama-storyboard` and `short_drama_cli.py import-storyboard`. It requires:

- v2 project and engine state;
- an exact-scope confirmed screenplay;
- canonical JSON audit bound to exact path/hash;
- immutable prompt context;
- explicit profile prompt/dialogue language, dialogue tag, style, aspect ratio, generator, and episode duration;
- `exact_storyboard_timing=true`.

Governed mode may not inherit silent defaults such as `promptLang=en`, `[Chinese]`, `16:9`, `realistic`, or `±15%`. Each episode must equal the profile target in integer milliseconds. Each cut becomes one Forging `BEAT` and `SHOT`; a segment remains only the `generation_group`.

## Workflow

```bash
node scripts/novel-storyboard.mjs seed script.json --eps 1-3 > storyboard.json
node scripts/novel-storyboard.mjs validate storyboard.json \
  --script script.json --outline outline.json --cast cast.json
node scripts/novel-storyboard.mjs render storyboard.json --md \
  --script script.json --outline outline.json --art art.json > storyboard.md
node scripts/novel-storyboard.mjs render storyboard.json --html --lang en \
  --script script.json --outline outline.json --art art.json > storyboard-report.html
node scripts/novel-storyboard.mjs export storyboard.json --script script.json --out h3
```

In governed mode, return the validated candidate to the Forging importer. Do not substitute standalone `export` for governed import.

## Core Gates

- Every script beat is claimed exactly once, in order, without crossing scenes.
- Segment cap, cut range, and dialogue fit follow the active parameters.
- H3 alignment and `[Shot k]` timestamps reconcile character for character.
- Claimed dialogue remains verbatim inside the required `<d>[Language] ...</d>` tag.
- Prompt prose, camera vocabulary, and style phrase match the mode/profile.
- Scene, character, and prop references reconcile with upstream data.
- Governed timing is exact; `±15%` remains a standalone/upstream-estimation concept only.

## Outputs And Delivery Tiers

Standalone produces `storyboard.json`, Markdown/HTML, per-segment `prompt.md`, optional frames, and a local export manifest.

Forging governed import produces:

- Tier 1: canonical governed storyboard and scoped shot plan;
- Tier 2: generation manifest and prompt files binding hashes, shots, beats, assets, and absolute timing;
- Tier 3: only when actual media is registered in visual/delivery manifests and passes required QC.

## Frames

When real image capability exists, create one frame per cut using approved scene, character, and prop references. The ratio comes from the active mode: explicit user input for standalone, mandatory profile aspect ratio for governed mode. Inspect each file for nonblank pixels, complete framing, identity, geometry, continuity, and ratio. Missing or failed files remain prompt-only/gaps.

## Files

- `SKILL.md`: agent contract and dual-mode rules.
- `references/schema.md`: data and timing semantics.
- `references/h3-prompt.md`: H3 structure, language, and dialogue tag.
- `references/storyboard-pass.md`: cutting method.
- `references/frame.md`: optional frame workflow.
- `scripts/novel-storyboard.mjs`: seed / validate / checkup / render / export.

## Selftest

```bash
node scripts/selftest.mjs
```

Selftest covers the standalone kernel. Forging's wrapper and project validator own governed prompt context, canonical audit, exact timing, generation-manifest, and aggregate/projection gates.
