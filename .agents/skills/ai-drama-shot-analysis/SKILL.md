---
name: ai-drama-shot-analysis
description: 对真实视频、视频片段或带时长的有序描述执行逐镜拉片，拆解剪切点、连续时间码、场景、表演、摄影、构图、光影、对白、音效和音乐，并标明实证、估算或未知。用于视频拆镜、广告或短剧拉片、节奏研究、声音分析、摄影反推和 AI 视频反向工程。
---

# AI Drama Shot Analysis

## Role

把真实 media 或带可靠时长的描述转成逐镜证据记录。区分观察、估算和未知；不把分析结果静默写入创作 `shot-plan.json`。

## Prerequisites

- 读取 [analysis-method.md](references/analysis-method.md)、[evidence-output.md](references/evidence-output.md) 和共享 timeline/evidence contracts。
- 选择实证、估算或未知模式。只有真实可读 media 能支持实证剪切点、画幅、音轨和逐帧结论。
- 项目模式登记 source path/hash、rights、scope 和分析依赖；独立模式不声称跨批次身份或连续性。

## Execution

1. 对真实视频运行 `media_analysis_cli.py analyze`，取得容器、实测总时长、帧率、尺寸、画幅、音轨和候选切点。
2. 通览全片后逐帧复核候选边界，排除闪光、遮挡、快速运动和曝光变化等假切。
3. 分别检查首帧、中间帧、尾帧和音轨；只记录可见/可听事实。
4. 使用从 `0` 到实测总时长的连续整数毫秒时间轴；边界按帧率取值，能力不足时不伪造帧级精度。
5. 分配必要的稳定资产标签，描述构图、动作、摄影、光线、材质、对白与声音，并给每项证据状态。
6. 校验 canonical JSON，再派生 Markdown；建议或复现方案与事实记录分区。

## Outputs

- 实证模式：schema-valid `shot-analysis-vNNN.json` 与派生 Markdown。
- 估算/未知模式：明确限制的报告，不冒充真实 media audit。
- 结构化分析与证据报告；生成包或交付 media 仅在用户另行要求时由对应 storyboard/delivery workflows 创建（交付层级是项目级状态，见 `delivery-contract.md`）。

## Gates

- 候选切点、文件名、缩略图、字幕或用户描述不能替代逐帧/音轨观察。
- JSON 是分析字段和 timing 的 canonical source；Markdown 不得改变 evidence status。
- 第一段从 0 开始，相邻边界闭合，最后一段结束于实测总时长。
- 对白必须来自音轨；听不清、看不见或不能确认的内容保留 unknown。
- Contact sheet/HTML 只是汇总，不能替代逐个 media/frame inspection 或 QC。

## Shared Links

- [analysis-method.md](references/analysis-method.md)
- [evidence-output.md](references/evidence-output.md)
- `references/evidence-audit.md`
- `references/timeline-contract.md`
- `references/visual-evidence.md`
- `references/delivery-contract.md`
- `schemas/shot-analysis.schema.json`
