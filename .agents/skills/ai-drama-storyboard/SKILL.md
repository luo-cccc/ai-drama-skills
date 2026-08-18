---
name: ai-drama-storyboard
description: 将已确认剧本、场景或故事节拍转换为关键分镜、场级分镜、逐镜头执行方案、3x3 视觉九宫格、故事板表格和 AI 视频提示词。用于分镜设计、镜头表、视觉预演、九宫格、连续时间轴、视频 Prompt 和生成片段规划；真实成片的反向拉片改用 ai-drama-shot-analysis。
---

# AI Drama Storyboard

## Role

把已确认叙事转成可执行镜头、绝对时间轴和生成包，不静默改写剧情、关系、对白含义或结局。真实成片反向分析交给 `$ai-drama-shot-analysis`。

## Prerequisites

- 读取 [storyboard-levels.md](references/storyboard-levels.md)、[delivery-profiles.md](references/delivery-profiles.md) 和共享 workflow/data/timeline contracts。
- 项目模式要求目标范围有可用上游；正式 C 级分镜要求 exact confirmed screenplay 与 valid audit。
- 从项目或 delivery profile 读取画幅、语言、生成器、音频、字幕、剪辑、视觉换挡、片段上限和目标时长。缺失时标为待确认，不使用静默默认。
- Governed 调用提供 prompt context 时，将其视为不可变执行头，不以会话记忆或 prose summary 替代。

## Execution

1. 选择 A 关键分镜、B 场级分镜或 C 逐镜执行分镜；3x3、表格和视频 Prompt 是交付配置，不是密度。
2. 提取完整节拍、场景、动作及直接反应、对白、声音、连续性与资产引用。不可拆节拍共享 `beat_id`。
3. 建立空间、轴线、景别、机位、运动、表演、衔接和状态变化；保持身份、服装、几何、光向、视线、持物手与道具状态一致。
4. 在 canonical `shot-plan` 中使用整数毫秒和绝对主时间轴；相邻边界完全相等，正式范围精确闭合。
5. 按完整镜头/节拍边界建立 `generation_group`。每组是一次生成调用，不能拆分或与其他组重定义合并。
6. 为投产范围生成 `generation-manifest`，绑定 prompt 相对路径及 SHA-256、shots、beats、assets 和绝对起止时间。

## Outputs

- Canonical versioned `shot-plan` JSON；Markdown、表格、九宫格和 prompts 从它派生。
- Validated canonical plan 与 `prompt-only` 派生物；产物不锁定。
- 与 shot plan 对账的 generation manifest 和 prompt 文件；可附已生成但未完成最终 QC 的 media。
- 实际 media 进入 visual/delivery manifest、哈希/尺寸/时长和所需 QC 全部通过后，项目才达到对应的交付状态；交付状态是项目级标签，见 `delivery-contract.md`。

## Gates

- JSON 对 status、ID、profile、timing、evidence 和 asset refs 有最终权威。
- 正式 storyboard 每集、scope 和 master boundary 精确闭合；`±15%` 只用于 screenplay estimate。
- 默认最大生成片段为 `30000 ms`，除非 profile 明确覆盖；无合法边界时报告冲突，不截断节拍。
- Generation manifest 必须与 shot groups、prompt hashes 和 absolute timing 精确一致。
- 系列聚合保存 immutable versioned snapshot；root `shot-plan.json` 仅为同字节 projection，不得单独编辑。
- 图像能力不可用时交付 `prompt-only`；实际 raster 必须逐张打开、验证画幅/非空并完成视觉复核后才能计入 media delivered 交付状态。

## Shared Links

- [storyboard-levels.md](references/storyboard-levels.md)
- [delivery-profiles.md](references/delivery-profiles.md)
- `references/timeline-contract.md`
- `references/performance-camera.md`
- `references/visual-evidence.md`
- `references/delivery-contract.md`
- `schemas/shot-plan.schema.json`
- `schemas/generation-manifest.schema.json`
- `schemas/delivery-manifest.schema.json`
