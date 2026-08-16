---
name: ai-drama-script-audit
description: 对故事大纲、分场和影视剧本执行证据驱动的开放诊断、上游符合性核对、版本对比与定向修订，覆盖结构因果、人物弧光、场景功能、可拍性、对白和格式。用于剧本评估、自检、改稿建议、来源忠实度、提示包或分场一致性、两稿对比和下游放行判断；不默认整篇重写。
---

# AI Drama Script Audit

## Role

对指定文本执行证据驱动的诊断、符合性核对、版本对比或授权范围内的定向修订。审计不自动改写，也不自行确认剧本。

## Prerequisites

- 完整读取目标范围，并按 `project-state.json -> 来源/约束 -> brief -> 已确认 outline -> 当前稿 -> 上一稿/审计` 建立基准。
- 项目模式读取 `references/workflow-contract.md`、`references/evidence-audit.md` 和本 Skill 的审计参考；独立模式明确缺失基准和忠实度限制。
- v1 项目先作迁移决定。未迁移时只提供 v1 兼容报告，不能声称 v2 下游授权。
- Governed v2 审计接收不可变 prompt context，精确绑定 scope、candidate artifact、目标、上游、哈希和证据要求。

## Execution

1. 选择 `diagnostic`、`conformance` 或 `revision`；版本对比作为所需维度加入。
2. 建立因果主线，先检查 P0，再检查 P1/P2；逐项核对结构、人物、场景、节奏、可拍性、对白、格式和权利风险。
3. 每个 finding 写证据、判断、影响、动作和可复查验收条件。必保元素逐项给出 `pass/fail/unverifiable` 与证据。
4. 符合性审计记录 exact target artifact/path/hash、basis、required elements、differences、decision 和 limitations。
5. 定向修订只创建新剧本版本；随后重新审计，绝不覆盖已确认稿。

## Outputs

- v2 正式审计：通过 `audit-report.schema.json` 的 immutable `audit-vNNN.json`。
- `project-state.json.audit_result`：从 canonical arrays 派生的六键摘要，不得手填或增加冲突计数。
- Markdown：人类可读派生报告。v1/独立模式可带兼容 marker，但不能授权 v2 下游。
- 门禁结论：`pass`、`revise`、`blocked` 或带明确授权的 `accepted-with-risk`。

## Gates

- JSON 是 v2 审计唯一权威；Markdown 不能覆盖目标、哈希、证据、计数或 decision。
- 任一 P0 阻断正式分镜和资产锁定。P1 风险接受必须记录具体授权。
- 无法读取 canonical source 时不得宣称忠实；节选不得外推为全剧结论。
- 证据不可检索、目标哈希错配、基准错误或摘要与 canonical arrays 不一致时，审计无效。
- 机器结构门与创意复核分开；validator success 不等于审计通过。

## Shared Links

- [audit-framework.md](references/audit-framework.md)
- [evidence-and-gates.md](references/evidence-and-gates.md)
- `references/evidence-audit.md`
- `references/workflow-contract.md`
- `references/screenplay-format.md`
- `schemas/prompt-context.schema.json`
- `schemas/audit-report.schema.json`
