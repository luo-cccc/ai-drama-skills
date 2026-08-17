**中文** · [English](README.en.md)

# novel-storyboard

把 `novel-script` 的节拍流切成三层执行结构：

```text
segment = 一次视频生成调用，不跨场
  cut = 段内剪切，认领连续剧本节拍
    frame = 每切一张关键帧，钉在 0 或该切点
  h3Prompt = 每段一条，alignment 与 [Shot k] 时间由 cuts 推导
```

## 两种模式

### Standalone Kernel

直接运行本目录 CLI。它是自包含切镜内核，允许本地默认值：`promptLang=en`、`style=realistic`、默认段/切时长和 `tolerance=0.15`。`validate` 检查节拍覆盖、时长、对白容纳、H3 结构、语言、风格、镜头词和引用。

Standalone 每集 `±15%` 仅是内核完整性门。`export` 生成的根 `manifest.json` 是本地 H3 文件清单，不是 Forging canonical generation manifest，也不授权项目完成。

### Forging Governed Mode

由 `ai-drama-short-drama-storyboard` 和 `short_drama_cli.py import-storyboard` 托管。要求：

- v2 project/engine state；
- exact-scope confirmed screenplay；
- 绑定 exact path/hash 的 canonical JSON audit；
- immutable prompt context；
- 显式 profile prompt/dialogue language、dialogue tag、style、aspect ratio、generator、episode duration；
- `exact_storyboard_timing=true`。

Governed mode 禁止使用 silent defaults：不能回落到 `promptLang=en`、`[Chinese]`、`16:9`、`realistic` 或 `±15%`。每集必须精确等于 profile 目标毫秒；每个 cut 转成一个 Forging `BEAT` 和 `SHOT`，segment 只保留为 `generation_group`。

## 工作流

```bash
node scripts/novel-storyboard.mjs seed script.json --eps 1-3 > storyboard.json
node scripts/novel-storyboard.mjs validate storyboard.json \
  --script script.json --outline outline.json --cast cast.json
node scripts/novel-storyboard.mjs render storyboard.json --md \
  --script script.json --outline outline.json --art art.json > storyboard.md
node scripts/novel-storyboard.mjs render storyboard.json --html --lang zh \
  --script script.json --outline outline.json --art art.json > storyboard-report.html
node scripts/novel-storyboard.mjs export storyboard.json --script script.json --out h3
```

Governed mode 在 `validate` 后把候选交回 Forging importer；不要用 standalone `export` 替代 governed import。

## 核心门

- 剧本每拍被一个 cut 恰好认领，顺序连续，不跨场。
- Segment 总时长不超过模型上限；cut 时长和对白容纳满足参数。
- H3 alignment line 与 `[Shot k]` 时间逐字对账。
- 每句认领对白按原文进入要求的 `<d>[Language] ...</d>` tag。
- Prompt 正文语言、运镜词、风格短语与模式/profile 一致。
- 场次、人物和道具引用对账上游。
- Governed timing exact；`±15%` 只保留在 standalone/上游估时语境。

## 输出和交付层级

Standalone 输出 `storyboard.json`、Markdown/HTML、每段 `prompt.md`、可选 frames 和本地 export manifest。

Forging governed import 输出：

- Tier 1：canonical governed storyboard + scoped shot plan；
- Tier 2：generation manifest + prompt files，绑定 hashes、shots、beats、assets 和 absolute timing；
- Tier 3：只有真实 media 写入 visual/delivery manifest 且通过所需 QC 后成立。

## 分镜图

有真实图像能力时，每切一张图并携带该段的场景、角色和道具参考。画幅必须来自当前模式：standalone 可由用户明确指定；governed 必须使用 profile aspect ratio。逐张检查非空、完整取景、身份、几何、连续性和比例。缺图或失败时保留 prompt-only/缺口，不装作已生成。

## 文件

- `SKILL.md`：agent 合同与双模式规则。
- `references/schema.md`：数据结构与时长语义。
- `references/h3-prompt.md`：H3 结构、语言和 dialogue tag。
- `references/storyboard-pass.md`：切镜方法。
- `references/frame.md`：可选分镜图工作流。
- `scripts/novel-storyboard.mjs`：seed / validate / checkup / render / export。

## 自测

```bash
node scripts/selftest.mjs
```

自测验证 standalone 内核。Forging governed 的 prompt context、canonical audit、exact timing、generation manifest 和 aggregate/projection 门由 Forging wrapper 与项目 validator 负责。
