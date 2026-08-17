---
name: novel-storyboard
version: 1.1.0
description: |
  给 AI 短剧出分镜：三层结构——段（一次视频生成，≤15 秒）→ 分镜（段内 2–5 秒的剪切，认领剧本节拍）
  → 分镜图（每切一张关键帧：主分镜图钉 0.00 秒，子分镜图钉各自切点）。
  每段自带一条 MiniMax H3 视频提示词（官方口径默认英文、逐镜换行，promptLang 可切中文）：对齐指令和
  [Shot k] 切点时刻由分镜结构推导、逐字对账，台词逐字进 <d> 块（写法规范已内化为
  references/h3-prompt.md，不依赖外部 skill）。
  产出 storyboard.json + Markdown + 单页评审报告（分镜节奏带 / 分集分镜表 / 生成批次单 /
  配音对齐单，含导出 JSON）。分镜图出图拿场景与角色设定图当参考图走 codex $imagegen（可选）。
  16 道质量门全部由脚本确定性检查；export 一键导出 H3 投产包（每段提示词 + 按 Picture 序的分镜图清单）。零依赖、零 API key，用当前会话额度。
  Use when asked to 分镜、出分镜、镜头表、切镜、storyboard for AI short drama。
allowed-tools:
  - Read
  - Write
  - Bash
  - Task
  - Glob
triggers:
  - novel-storyboard
  - 分镜
  - 出分镜
  - 镜头表
  - 切镜
  - 首帧
  - storyboard
  - shot list
metadata:
  license: Apache-2.0
  requires:
    bins:
      - node          # >= 18，只用标准库，无 npm 依赖
    optional:
      - codex         # 有才出首帧图；没有就只交提示词，其余照常
  runtimes:
    - claude-code
    - codex
---

## novel-storyboard

## Role

把 `script.json` 的场次节拍切成 `segment -> cut -> frame/H3 prompt`。本内核不写戏、不改台词、不创建设定资产，也不生成或剪辑视频。

## Operating Modes

### Standalone Kernel

直接使用本目录 CLI。`script.json` 是硬前提；`outline/cast/art` 按需增强检查和报告。Standalone 允许内核默认值：`promptLang=en`、`style=realistic`、默认段/切时长和 `tolerance=0.15`。这些默认值只属于独立内核，不构成 Forging 项目决策。

Standalone `validate` 的每集 `±15%` 是本地完整性门，不是正式投产闭合。Standalone `export` 的根 `manifest.json` 是 H3 文件清单，不是 Forging `generation-manifest.schema.json`。

### Forging Governed Mode

只能由 `$ai-drama-short-drama-storyboard` / `short_drama_cli.py import-storyboard` 调用。要求 v2 project state、exact-scope confirmed screenplay、canonical JSON audit，以及该 scope 的 immutable prompt context。

Governed task 必须显式携带 profile prompt language、dialogue language/tag、style、aspect ratio、generator、episode duration 和 exact timing。禁止回落到 standalone 的语言、`[Chinese]`、`16:9`、style 或 `±15%` 默认。Wrapper 将 profile 写入候选、运行内核检查，再把每个 cut 转成绝对时间的 Forging beat/shot；每集必须精确闭合到目标毫秒。

## Prerequisites

- Read [schema.md](references/schema.md), [storyboard-pass.md](references/storyboard-pass.md), and [h3-prompt.md](references/h3-prompt.md).
- Use [frame.md](references/frame.md) only when real image capability exists.
- Process the same contiguous episode range as the screenplay batch, normally at most three episodes.
- In governed mode, do not continue if prompt context, exact audit, profile fields, or scope are missing/mismatched.

## Execution

1. Seed the deterministic cutting worksheet:

```bash
node {baseDir}/scripts/novel-storyboard.mjs seed <script.json> --eps 1-3 > <workdir>/storyboard.json
```

2. Split each episode into scene-bounded generation segments; split each segment into cuts that claim contiguous script beats exactly once. Keep generated beat durations from seed; do not re-estimate them.
3. Write one frame prompt per cut and one H3 prompt per segment. Derive alignment text and cut timestamps from cut durations. Preserve dialogue verbatim in the required dialogue tag.
4. Validate until all applicable deterministic gates pass:

```bash
node {baseDir}/scripts/novel-storyboard.mjs validate <storyboard.json> \
  --script <script.json> --outline <outline.json> --cast <cast.json>
```

5. Standalone may render/export directly. Governed mode must return the candidate to the Forging importer; do not use standalone export as the authorization record.
6. Generate frames only at the requested ratio with approved scene/character/prop references. Missing capability means prompt-only, not generated media.

## Outputs

Standalone:

- `storyboard.json`, Markdown, optional HTML report.
- Per-segment `prompt.md`, optional `f1..fN` frames, and local export `manifest.json`.

Forging governed mode:

- Versioned governed storyboard JSON and derived reports.
- Canonical scoped `shot-plan` with integer-millisecond absolute series time.
- Canonical generation manifest binding each generation group to prompt SHA-256, shots, beats, assets, and absolute range.
- Tier 1 canonical plan, Tier 2 generation package, and Tier 3 only after separate media-manifest QC.

## Gates

- Every script beat is claimed once, in order, within one scene.
- Segment and cut limits, dialogue fit, references, camera vocabulary, alignment line, cut timestamps, prompt language, style phrase, and verbatim dialogue must validate.
- Governed mode requires explicit profile language, dialogue tag, aspect ratio, style, generator, and exact episode timing; silent defaults are invalid.
- Governed episode/scope boundaries close exactly. `±15%` is never governed storyboard closure.
- One segment/generation group is one model call. Editing containers cannot split or merge its identity.
- Generated frames remain delivery evidence only after individual inspection, hashes, dimensions, and required QC.

## Shared Links

- [README.md](README.md) / [README.en.md](README.en.md)
- [schema.md](references/schema.md)
- [h3-prompt.md](references/h3-prompt.md)
- [storyboard-pass.md](references/storyboard-pass.md)
- [frame.md](references/frame.md)
