# Examples

本目录包含用于文档说明和回归测试的 schema v1 项目样例。样例中的 `project-state.json`、JSON 产物和 Markdown 产物应当结合阅读；单个文件不能代表整个项目已经完成，也不能扩大其确认范围。`synthetic-short/` 的镜头交付是 partial，`legacy-yiqiyang/` 则保留历史状态和来源缺口。

## 样例索引

| 目录 | 定位 | 来源可用性 | 可验证范围 | 主要限制 |
|:--|:--|:--|:--|:--|
| `synthetic-short/` | 当前合成短片样例 | 完整人工合成来源随仓分发 | 来源、简报、分场、两版剧本、审查、部分资产、连续性和局部分镜之间的确定性一致性 | 项目总目标为 360 秒，但逐镜头方案只覆盖 `SCN-005` 的 0-15 秒；不是完整成片或完整逐镜头管线 |
| `legacy-yiqiyang/` | 历史迁移与边界回归样例 | 原始长会话未分发 | 已分发产物之间的内部一致性、版本状态、旧分镜范围和 canonical subset | 不能独立验证原文忠实度；不能把历史 `complete` 状态理解为当前规范下全片 AI-ready |

## 阅读规则

- 以 `project-state.json` 中的 artifact `status`、`scope`、依赖和哈希为机器可读状态基准。
- Markdown 文件用于人类审阅；JSON manifest、ledger 和 shot plan 是相应结构化边界的基准。
- `confirmed` 只表示记录范围内的确认，不自动表示来源权利、原文忠实度、媒体生成质量或全项目完成。
- `superseded` 文件保留用于版本回归，不应作为当前下游输入。
- 示例验证属于确定性仓库测试，不构成独立模型前向测试证据；模型/agent 在开放任务中的表现不在本仓库验证范围内。

[synthetic-short/README.md](synthetic-short/README.md) 说明当前合成样例的具体范围；[legacy-state-note.md](legacy-yiqiyang/legacy-state-note.md) 说明历史样例的来源缺口和状态解释。
