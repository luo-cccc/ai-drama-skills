# AI Drama Forging

AI Drama Forging 是一套本地、可追溯、可验证的 AI 影视生产 Skill 套件。它用结构化项目状态管理来源、创作版本、审计、资产、连续性、分镜、生成输入和交付结果，并把模型创作与机器门禁分开。

## 能力地图

| 入口 | 职责 |
|:--|:--|
| `ai-drama-forging` | 跨阶段路由、项目状态、版本、checkpoint、资格判断、回退与恢复 |
| `ai-drama-development` | 概念、世界观、人物、故事结构和原创化改编 |
| `ai-drama-screenplay` | 制作提示包、分场和标准剧本 |
| `ai-drama-script-audit` | 证据审计、版本对比、修订门禁和风险结论 |
| `ai-drama-assets` | 资产提取、稳定 ID、视觉 DNA、证据、锁定和连续性 |
| `ai-drama-character-design` | 角色、表情、动作、服装和道具视觉设定 |
| `ai-drama-scene-design` | 场景视图、空间布局、机位和 VR 规格 |
| `ai-drama-storyboard` | 创作分镜、主时间轴、镜头表和视频 Prompt |
| `ai-drama-shot-analysis` | 真实视频探测、切点复核和逐镜分析 |
| `ai-drama-short-drama` | Forging 治理下的小说改短剧编排、审计、聚合和完成门禁 |
| `ai-drama-short-drama-*` | 角色、大纲、美术、剧本、分镜五个显式委派内核 |

单一明确任务使用对应领域 Skill。跨阶段、恢复项目、判断下游资格或协调多个领域时使用编排器。

## 工作模式

- **项目模式**：发现 `project-state.json` 后，所有物质状态变化都登记来源、版本、依赖、SHA-256、scope、checkpoint 和授权。
- **独立模式**：完成单次任务，不强制创建项目，也不声称跨批次身份、资产或连续性已经锁定。

稳定阶段为：

```text
intake -> development -> brief -> outline -> screenplay -> audit -> shots/assets -> complete
```

`complete` 不是普通阶段写入。短剧项目只能通过专用完成门禁进入。

## 结构化真源

| 数据 | 当前角色 |
|:--|:--|
| `project-state.json` | 项目配置、来源、artifact graph、checkpoint 和阶段；新项目为 schema v2 |
| `asset-manifest.json` | 资产、视觉 DNA、证据与锁定；当前 CLI 基线仍为 schema v1 |
| `continuity-ledger.json` | 状态变化与范围快照；当前操作格式为 schema v1 |
| `hook-ledger.json` | 短剧悬念台账的根投影；权威字节是 `short-drama/governance/hook-ledger-vNNN.json` 不可变快照，由大纲 major beats 播种、剧本合同 hook 动作确定性演化，`short-drama-engine.canonical_state` 绑定 |
| `canon.json` | 短剧故事事实/世界规则 claims 的根投影；权威字节是 `short-drama/governance/canon-vNNN.json` 不可变快照（register 输入另存 `canon-register-vNNN.json`），剧本导入时确定性门禁与演化 |
| `short-drama-engine.json` | 短剧 profile、runtime snapshot、crosswalk、aggregate 和 completion 绑定 |
| `audit-vNNN.json` | v2 正式审计的 canonical JSON |
| scoped `shot-plan-vNNN.json` | 分集范围内的 canonical 时间轴与镜头计划 |
| series `shot-plan-vNNN.json` | 无损聚合后的 immutable canonical snapshot |
| 根 `shot-plan.json` | 当前 series aggregate 的 projection，必须与 snapshot 字节一致 |
| `generation-manifest-vNNN.json` | Prompt、镜头、节拍、资产和时间的生成输入清单 |
| visual/delivery manifest | 视觉文件或媒体交付、hash、声明性 probe/QC 和失败记录 |

Markdown、HTML 和排版图通常是面向人的派生产物。完整契约见 [数据契约](shared/references/data-contract.md)。

项目 schema、Skill manifest schema、package manifest schema 和 snapshot manifest schema 是相互独立的版本空间；文件中的 `1.0` 不等于项目仍停留在 schema v1。

## 三种交付状态

1. **Planning complete**：`delivery_required=false`，剧本、series audit、scoped plans、series aggregate 和 locked assets 通过门禁。它不表示真实媒体已经生成。
2. **Generation-ready**：每个 scoped storyboard 已产生 generation manifest，Prompt 文件存在且 hash 与 shot plan 对账。
3. **Media delivered**：`delivery_required=true`，还必须有 confirmed、状态为 complete 的 series delivery manifest，文件、hash 和 QC 声明通过验证。

项目 validator 校验结构、依赖、文件、hash 和声明的 QC。真实媒体 probe、抽帧和人工视觉复核必须先由相应工具产生证据，validator 不会凭声明重新完成全部媒体分析。

## 快速开始

克隆仓库后，ZCode、Codex 等兼容 Skills 发现器可直接读取 `.agents/skills/`。每个目录都是自包含 Skill，至少包含 `SKILL.md`，并按需携带 `references/`、`scripts/`、`assets/`、`schemas/` 和运行时文件。

初始化：

```bash
python scripts/state_cli.py init --project-dir <PROJECT> --title "项目名" --slug project-slug
python scripts/validate_project.py <PROJECT>
```

迁移旧项目：

```bash
python scripts/state_cli.py migrate-project --project-dir <PROJECT> --dry-run
python scripts/state_cli.py migrate-project --project-dir <PROJECT> --apply
python scripts/validate_project.py <PROJECT>
```

短剧项目先 `attach`，每个创作阶段先生成 fresh prompt context，再把 context 传入对应 import。完整流程见 [短剧 v2 指南](docs/guides/short-drama-v2.md)。

## 文档地图

- [文档总索引](docs/README.md)
- [项目生命周期](docs/guides/project-lifecycle.md)
- [v2 迁移](docs/guides/v2-migration.md)
- [短剧 v2 工作流](docs/guides/short-drama-v2.md)
- [生成、交付与 QC](docs/guides/delivery-and-qc.md)
- [发布与验证](docs/guides/release.md)
- [共享规范](shared/references/workflow-contract.md)
- [示例边界](examples/README.md)
- [测试矩阵](tests/README.md)
- [来源与修改说明](PROVENANCE.md)

## 仓库分层

```text
.agents/skills/          标准、受版本控制、可直接发现的 15 个自包含 Skill
docs/                    操作指南和导航
src/skills/              15 个 Skill 的规范源
shared/references/       跨 Skill 的 packageable 规范契约
schemas/                 JSON Schema
scripts/                 状态、验证、写作质量门、悬念台账与正典、时间轴、媒体、打包和 snapshot 工具
engine/kernels/  内核适配源与修改说明
engine/runtime/  同步生成的精简执行副本
vendor/kernels/ 第三方内核与版本快照，不手工修改
examples/                v1 兼容与局部契约样例
tests/                   自动化测试、fixture 和历史 forward 记录
dist/                    可选的临时发布构建，不受版本控制
```

编辑 `src/skills/`、共享规范、脚本或 Schema 后，运行打包器刷新 `.agents/skills/`。不要直接编辑 `.agents/skills/` 或 `dist/`。

## 验证

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/validate_project.py examples/synthetic-short
python scripts/validate_project.py examples/legacy-yiqiyang
python scripts/sync_kernel_snapshot.py --source ../shuohao-skills-main --check
python scripts/package_skills.py
python tests/verify_dist.py
```

环境依赖、skip 条件和 release acceptance 见 [tests/README.md](tests/README.md)。最近一次记录的自动化发布验证见 [tests/release-validation.md](tests/release-validation.md)。历史 forward 报告仍是 stale evidence，不代表当前模型工作流通过。

## 发布边界

`.agents/skills/` 是仓库的标准安装面，`dist/` 仅在需要独立临时产物时通过 `--output dist` 生成。两者都只携带 Skill 执行所需的文档、脚本、Schema、runtime 和第三方通知，不包含操作指南。upstream、adapted、runtime 和安装面的来源与修改关系见 [PROVENANCE.md](PROVENANCE.md)。这些说明用于工程溯源与许可披露，不替代法律意见。
