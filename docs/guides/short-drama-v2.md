# 短剧 v2 工作流

## 1. Attach

在已初始化项目上固定集数、单集时长、风格、语言、画幅和 H3 上限：

```bash
python scripts/short_drama_cli.py attach \
  --project-dir <PROJECT> \
  --episodes 6 \
  --episode-seconds 120 \
  --genre period-suspense \
  --immutable-core "不可改核心" \
  --authorization "brief approval"
```

`attach` 创建或复用 production brief，并把当前内核 snapshot hash 与 runtime file map 固定到 engine。faithful 模式要求可接受的来源权利状态。

## 2. Prompt Context

每个 governed 创作阶段先生成 context：

```bash
python scripts/short_drama_cli.py prompt-context \
  --project-dir <PROJECT> --stage characters --scope series > context.json
```

阶段为 `characters`、`outline`、`art`、`script` 或 `storyboard`。episode scope 使用 `START-END`。context 绑定 state hash/revision、stage/scope、下一 artifact ID、profile、来源 trust/rights、confirmed upstream 和 engine snapshot。任何绑定内容变化后都必须重新生成。

context 是一次性控制输入，不是创作 artifact。

## 3. 五阶段导入

按依赖顺序执行：

1. `import-cast`
2. `import-outline --kind skeleton`
3. `import-outline --kind series`
4. `import-art`
5. `import-script`（默认先生成 pending candidate）
6. `prompt-context --stage audit` + conformance audit
7. `confirm-screenplay --screenplay ART-NNN --audit-report audit.json`
8. `import-storyboard`

每次 import 都消费匹配的 fresh context。剧本每批最多三集，允许互不重叠的 confirmed batch。

v2 confirmed screenplay 必须附 canonical conformance audit JSON。推荐先登记候选再确认：

```bash
python scripts/short_drama_cli.py import-script ...
python scripts/short_drama_cli.py prompt-context \
  --project-dir <PROJECT> --stage audit --scope 1-3 > audit-context.json
python scripts/short_drama_cli.py confirm-screenplay \
  --project-dir <PROJECT> --screenplay ART-001 \
  --audit-report audit.json --authorization "screenplay approval"
```

兼容入口 `import-script --confirm --audit-report ...` 仍可用于已在同一调用中准备好 exact-target audit 的自动化执行。

也可对多个已确认 screenplay 单独导入 series audit：

```bash
python scripts/short_drama_cli.py import-audit \
  --project-dir <PROJECT> --input series-audit.json \
  --screenplay ART-001 --screenplay ART-002 --series \
  --authorization "series audit approval"
```

`accepted-with-risk` 需要独立 `--risk-authorization`。

### 单集戏剧合同

`attach` 时 configuration 会写入 `episode_contract_required: true`。此后每批 screenplay 的每集条目必须携带 `contract` 对象（进入状态、目标、阻力、因果升级、局部结果、出去压力、交接状态、信息权限、情绪钩子、结尾状态与 hook 动作），import-script 会做确定性校验；合同随剧本文件一起 sha256 绑定，不产生独立 artifact。写作规范见 `shared/references/episode-drama-contract.md`。

写稿期可用质量门迭代（引擎 10 门之外的新门）：

```bash
python scripts/short_drama_cli.py script-quality \
  --input draft-script.json --previous <上一批已确认 screenplay JSON>...
```

`script` 阶段的 prompt context 会携带上一批最后一集的 `previous_handoff`（从已确认 screenplay 确定性派生，不是模型写），下一批的 `incomingState` 必须接住它；同时携带 hash 绑定的 `hook_ledger` 节，合同的 hook 动作只能引用台账中存在的 hook。

### Hook 台账

确认 series outline 时，CLI 从大纲 major beats 确定性播种 `hook-ledger.json`；每批剧本导入时按合同的 hook 动作演化（advance/resolve 的证据载体必须在正文落地）。台账是机器维护文件，不手工编辑：

```bash
python scripts/short_drama_cli.py hook-ledger --project-dir <PROJECT> status
python scripts/short_drama_cli.py hook-ledger --project-dir <PROJECT> health
```

`complete` 拒绝「最后一集之前种下且未 resolve/defer」的 hook；最后一集自身的悬念豁免（作为系列级情绪钩子，由 series audit 判断结局充分性）。

### Canon 设定库

世界规则与故事事实登记为 `canon.json` 的 claims（`schemas/canon.schema.json`），由 development/brief 阶段产出：

```bash
python scripts/short_drama_cli.py canon --project-dir <PROJECT> register \
  --input canon.json --authorization "canon approval"
python scripts/short_drama_cli.py canon --project-dir <PROJECT> list
python scripts/short_drama_cli.py canon --project-dir <PROJECT> refresh \
  --authorization "canon refresh approval"
```

每批剧本导入时执行确定性 claim 门禁（秘密真相在读者揭示集前泄露到可见正文、触碰禁令、绕过硬规则不付代价、不可泛化设定扩散，均为硬错），随后确定性演化：交接知识/局部结果/结尾状态与 claim 内容重合即 settle，信息权限更新 characterKnownBy，未认领事实进入 candidates 供 refresh 确认。

`reader_known_from == 本集` 的 claim 若没有在可见正文落点，导入结果 JSON 的 `warnings` 会列出（不阻断导入）——写稿期可用 `script-quality --canon canon.json` 提前发现，正式复核交给 conformance audit。

### 治理快照与重建

Hook 台账和 Canon 是机器维护的不可变历史：每次 seed/evolve/register/refresh 都会写入 `short-drama/governance/{hook-ledger|canon}-vNNN.json` 快照并登记为 artifact，根 `hook-ledger.json`/`canon.json` 只是当前快照的字节等价投影，`short-drama-engine.canonical_state` 记录 artifact/path/hash/revision/依赖链；`canon register` 的输入同时登记为 `canon-register` artifact。项目校验会重放整条派生链并对账，删除或篡改任一快照/投影都会被拒绝。缺绑定或漂移时可确定性重建：

```bash
python scripts/short_drama_cli.py rebuild-governance \
  --project-dir <PROJECT> --hook
python scripts/short_drama_cli.py rebuild-governance \
  --project-dir <PROJECT> --canon
```

## 4. Storyboard 产物

每次 scoped storyboard import 同时登记：

- immutable storyboard JSON；
- immutable scoped shot plan；
- generation manifest；
- 每个 generation group 的 hashed Prompt；
- Markdown/HTML 派生报告。

scoped shot plan 使用 series absolute milliseconds，并精确闭合其 episode 范围。正式分镜不能用剧本估时的 `±15%` 容差放行。

## 5. Series Aggregate

当 confirmed scoped plans 无缺口覆盖 `1..N` 且 series audit 有效时：

```bash
python scripts/short_drama_cli.py aggregate-shot-plan \
  --project-dir <PROJECT> --authorization "aggregate approval"
```

输出：

- immutable series `shot-plan-vNNN.json` canonical snapshot；
- 根 `shot-plan.json` current projection；
- engine aggregate ID/path/hash 绑定。

聚合是 scenes、beats、shots 的无损合并。scoped plans 和 generation manifests 保持 confirmed。

## 6. Lock 与 Complete

`asset-manifest.json` 中 aggregate 引用的资产必须 locked，并登记 confirmed `locked-assets` artifact。随后执行：

```bash
python scripts/short_drama_cli.py complete \
  --project-dir <PROJECT> --authorization "completion approval"
```

completion 绑定 aggregate、series audit、locked-assets 的 artifact ID 与 SHA。

- `delivery_required=false`：允许 planning complete，不声称媒体已生成。
- `delivery_required=true`：还必须有 confirmed、status complete 的 series delivery manifest。使用显式交付入口登记：

```bash
python scripts/short_drama_cli.py import-delivery \
  --project-dir <PROJECT> --input delivery-manifest.json \
  --authorization "delivery approval"
```

## 7. 验证

```bash
python scripts/short_drama_cli.py validate --project-dir <PROJECT>
```

测试中的人工两集闭环见 [test_two_episode_pipeline.py](../../tests/test_two_episode_pipeline.py)。它验证机器契约，不调用模型，也不代表真实媒体交付。

仓库更新后，重新打包 `.agents/skills/` 并同步任何外部技能安装副本（如 `~/.zcode/skills/`），否则实际执行的是旧版技能。
