# 文档索引

本目录保存操作指南。机器可执行规范位于 `schemas/`，跨 Skill 的 normative contract 位于 `shared/references/`，Skill 的职责与调用规则位于 `src/skills/`，标准发现入口位于 `.agents/skills/`。

## 按任务查阅

| 任务 | 指南 | 主要规范 |
|:--|:--|:--|
| 初始化、恢复、状态与 checkpoint | [项目生命周期](guides/project-lifecycle.md) | [workflow-contract](../shared/references/workflow-contract.md) |
| 将 schema v1 项目升级到 v2 state | [v2 迁移](guides/v2-migration.md) | [data-contract](../shared/references/data-contract.md) |
| 小说改短剧及五阶段导入 | [短剧 v2](guides/short-drama-v2.md) | [prompt governance](../shared/references/short-drama-prompt-governance.md) |
| Prompt、视觉和媒体交付 | [生成、交付与 QC](guides/delivery-and-qc.md) | [delivery-contract](../shared/references/delivery-contract.md) |
| snapshot、打包和 release evidence | [发布与验证](guides/release.md) | [tests/README](../tests/README.md) |

## 事实优先级

发生冲突时按以下顺序判断：

1. 当前 `scripts/` 和 `schemas/` 的可执行行为。
2. `shared/references/` 的规范说明。
3. `src/skills/**/SKILL.md` 的执行路由。
4. 本目录的操作示例。
5. `examples/`、历史报告和生成输出。

`.agents/skills/` 是受版本控制的标准安装面，`dist/` 是可选临时构建，`engine/shuohao-runtime/` 是同步结果，`vendor/shuohao/upstream/` 是只读来源快照；它们都不是独立文档所有者。
