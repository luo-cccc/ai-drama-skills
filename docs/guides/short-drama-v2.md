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

`attach` 创建或复用 production brief，并把当前 shuohao snapshot hash 与 runtime file map 固定到 engine。faithful 模式要求可接受的来源权利状态。

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
5. `import-script`
6. `import-storyboard`

每次 import 都消费匹配的 fresh context。剧本每批最多三集，允许互不重叠的 confirmed batch。

v2 confirmed screenplay 必须附 canonical conformance audit JSON：

```bash
python scripts/short_drama_cli.py import-script ... \
  --confirm --authorization "screenplay approval" \
  --audit-report audit.json
```

也可对多个已确认 screenplay 单独导入 series audit：

```bash
python scripts/short_drama_cli.py import-audit \
  --project-dir <PROJECT> --input series-audit.json \
  --screenplay ART-001 --screenplay ART-002 --series \
  --authorization "series audit approval"
```

`accepted-with-risk` 需要独立 `--risk-authorization`。

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
- `delivery_required=true`：还必须有 confirmed、status complete 的 series delivery manifest。

## 7. 验证

```bash
python scripts/short_drama_cli.py validate --project-dir <PROJECT>
```

测试中的人工两集闭环见 [test_two_episode_pipeline.py](../../tests/test_two_episode_pipeline.py)。它验证机器契约，不调用模型，也不代表真实媒体交付。
