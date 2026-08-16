# 生成、交付与 QC

## Generation Manifest

每个 scoped storyboard import 生成 `generation-manifest-vNNN.json`。每个 generation group 必须精确记录：

- shot、beat、asset ID；
- series absolute start/end milliseconds；
- Prompt 相对路径和 SHA-256；
- generator、版本、片段上限、画幅、Prompt 语言和对白语言。

Prompt 路径相对 manifest 解析。validator 会对照 confirmed shot plan 检查 group、ID、资产、时间和 Prompt hash。

## Visual Delivery

visual delivery 用于角色、场景、关键帧或 VR 图像。它记录：

- 来源和权利声明；
- 目标规格与能力探测；
- 项目内文件路径、MIME 和 SHA-256；
- decoded、实际尺寸、nonblank、画幅、visual review 和 VR review；
- 失败和限制。

生成或编辑状态的 raster 必须真实存在并通过相应 QC。equirectangular 输出还需要通过 VR review；能力不足只能标为未完成 QC，不能冒充成品。

## Delivery Manifest

series delivery manifest 汇总真实媒体、storyboard images、generation group、probe 声明、QC、失败类型和 known gaps。

状态为 `complete` 时：

- 所有要求项都已 delivered；
- QC 为 pass 或 not-applicable；
- 没有 known gaps；
- 文件存在且 hash 匹配。

`delivery_required=true` 的项目只能在 confirmed complete series delivery manifest 存在时进入 complete。

## 媒体证据边界

项目 validator 检查 manifest 结构、文件、hash、状态和已记录的 QC。它不会替代以下证据生产：

```bash
python scripts/media_analysis_cli.py probe ...
python scripts/media_analysis_cli.py detect-cuts ...
python scripts/media_analysis_cli.py extract-frames ...
python scripts/visual_layout_cli.py verify ...
```

自动检测的切点是 inferred，需要帧审查后才能成为 confirmed evidence。视频的真实 duration、codec、尺寸和音频应来自 ffprobe 或等价工具；不要手写 probe 字段后声称已独立验证。

## 失败处理

- 无图像生成能力：交付 prompt-only brief，不能标 generated。
- 文件缺失或 hash 漂移：artifact invalid，重新生成或重新登记。
- raster 解码、nonblank、画幅或视觉复核失败：不得 confirmed delivery。
- VR 能力不足：记录 `qc-incomplete` 或等价失败状态。
- 生成 group 超过模型时长上限：回到 shot plan 重新分组，不在 manifest 中伪造拆分。

完整字段见 [delivery contract](../../shared/references/delivery-contract.md) 和对应 Schema。
