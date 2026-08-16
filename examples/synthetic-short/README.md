# Synthetic Short Example

`synthetic-short` 是完全人工合成、可随仓分发的确定性回归样例。项目《最后一班灯》的源故事位于 `source-story.md`，因此可以对来源、创作产物和结构化状态进行本地交叉验证，不依赖私有会话或外部模型调用。

## 覆盖内容

| 阶段 | 文件 | 状态与用途 |
|:--|:--|:--|
| 来源 | `source-story.md` | canonical 合成来源 |
| 制作简报 | `production-brief-v001.md` | confirmed |
| 分场 | `scene-outline-v001.md` | confirmed |
| 剧本一稿 | `screenplay-v001.md` | superseded；保留缺失必保台词的回归案例 |
| 一稿审查 | `audit-screenplay-v001.md` | superseded；记录 revise 决定 |
| 剧本二稿 | `screenplay-v002.md` | confirmed；恢复必保台词并通过范围内审查 |
| 二稿审查 | `audit-screenplay-v002.md` | confirmed；P0/P1/P2 均为 0，必保元素 5/5 |
| 资产 | `asset-manifest.json`、`asset-manifest-v001.md` | confirmed 的结构化资产基线及其可读视图 |
| 连续性 | `continuity-ledger.json` | 场景范围内的事件与状态边界 |
| 镜头 | `shot-plan.json`、`storyboard-v001.md` | confirmed，但只覆盖 `SCN-005` 的 0-15 秒 |

## 明确边界

- 项目目标时长是 `360000 ms`；`shot-plan.json` 的时间线仅为 `0-15000 ms`。
- 当前项目阶段是 `shots`，不是 `complete`。
- 局部分镜用于验证镜头时间、资产引用和连续性约束，不能称为全片逐镜头分镜。
- 示例没有生成或附带最终图片、视频、音频，也不提供模型表现证据。
- checkpoint 中的 authorization 是合成 fixture 决定，只为验证状态机和依赖关系，不代表真实用户批准。

仓库测试会检查必保台词、包内物件、场景标题、车辆动作因果、资产边界、连续性和局部分镜范围。完整测试入口见 [tests/README.md](../../tests/README.md)。
