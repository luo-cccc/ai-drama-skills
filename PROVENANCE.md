# Provenance

本仓库整合以下来源：

- 五套确定性短剧内核（受版权保护的第三方组件），按 Apache-2.0 引用并保留其 `LICENSE`、`NOTICE` 与本仓库的 `MODIFICATIONS.md` 归属声明。
- 本仓库自有的编剧、视觉资产、剧本审计、故事板、分镜、镜头分析与治理（Forging）层。

## 内核层与运行时

| 层 | 仓库路径 | 角色 | 编辑规则 |
|:--|:--|:--|:--|
| 上游快照 | `vendor/kernels/upstream/` | 第三方内核的精确 pinned 副本；具体文件由 `vendor/kernels/snapshot-manifest.json` 中的 SHA-256 标识 | 保持只读；不在本地修改 |
| 快照清单 | `vendor/kernels/snapshot-manifest.json` | 记录第三方内核版本/哈希，并记录从上游生成的 adapted 与 runtime 文件哈希 | 由 sync 脚本生成；本仓库 `MODIFICATIONS.md` 不参与此生成 |
| 适配源 | `engine/kernels/` | 生成 runtime 投影前需要的本地化源；保留上游 LICENSE、NOTICE 与本仓库的 `MODIFICATIONS.md` 归属声明 | 本地修改记录在 `engine/kernels/MODIFICATIONS.md` |
| 运行时投影 | `engine/runtime/` | 五个 `.mjs` 引擎与 `FORGING-ADAPTATION.json` 的最小可执行投影 | 由适配源生成；不是独立上游 |
| 标准 Skills 安装 | `.agents/skills/` | 受版本控制、自包含的 Skill 包，包含用于执行的 runtime/reference 副本、包哈希与第三方 LICENSE/NOTICE 文件 | 由规范源生成；不要直接编辑 |
| 临时构建 | `dist/` | 与 `.agents/skills/` 布局一致的发布构建 | gitignore 忽略；不要作为源代码编辑 |

五个 pinned 第三方内核组件及其版本：

- `characters` 1.7.0
- `outline` 1.1.0
- `art` 1.1.0
- `script` 1.2.0
- `storyboard` 1.1.0

仓库适配元数据版本为 1.0.0。

## 适配摘要

适配层将对外风格命名规范为仓库的 `realistic` 与 `hand-painted-cel` 策略（含历史导入规范化）。周围的 Forging 集成应用 scope、evidence、audit、transaction 与 timeline 合同。运行时与打包副本是上述适配层的派生产物，不能作为「上游本身包含 Forging 治理层」的证据。

pinned 上游文件与生成的 adapted/runtime 组件文件 SHA-256 记录在 `vendor/kernels/snapshot-manifest.json`。本仓库人工维护的 `engine/kernels/MODIFICATIONS.md` 单独记录。

每次从受版权保护的第三方内核母仓同步上游副本时，本仓库的 `sync_kernel_snapshot.py` 脚本会：

1. 校验上游 LICENSE 与 NOTICE；
2. 运行上游自带的 Node 端 selftest（不联网、不调用模型）；
3. 对每个内核适配层做策略规范化，复制 upstream/adapted/runtime 三个目录并重写 manifest。

`sync_kernel_snapshot.py --check` 是 release 验证的一部分，发现漂移即视为 release failure。

## NOTICE Path Note

上游 NOTICE 按原样保留（其内容受归属合同约束）。如果上游文本提到 `skills/storycast/examples/渡口.txt` 的位置而本仓库 pinned 快照实际路径为 `skills/novel-characters/examples/渡口.txt`，本仓库在不改写上游 NOTICE 文本的前提下记录该路径差异。

## 权利边界

Apache License 2.0 的授权仅适用于通过 pinned 快照与 LICENSE/NOTICE 文件识别的第三方内核材料。该组件的存在并不重新授权其他本地来源、仓库自有创新、用户项目内容或第三方模型/媒体产品。

本仓库无权重新授权其他部分。任何公开分发需要对所有非第三方内核材料以及正在处理或生成的内容单独进行权利与归属审查。

## 本仓库原创

per-episode `contract` 扩展、hook ledger、canon claim 门禁、确定性 screenplay 质量门、prompt-context 真实性校验、canonical_state 治理快照、governance snapshot 重放、import-delivery owner、两阶段剧本确认等设施均为本仓库在 Python + JSON-schema 治理层上的独立实现，未从任何第三方内核代码复制。
