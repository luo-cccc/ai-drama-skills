# v2 项目迁移

`migrate-project` 只迁移项目状态和可安全恢复的 artifact 路径，不会猜测已被覆盖的历史内容，也不会把 asset manifest 或 continuity ledger 静默改成未被当前 CLI 完整支持的新格式。

## 迁移前

1. 保留项目备份或版本控制快照。
2. 确认没有其他进程正在写项目。
3. 先运行当前 validator，记录既有错误。

## Dry Run

```bash
python scripts/state_cli.py migrate-project --project-dir <PROJECT> --dry-run
```

输出列出：

- `schema_version` 和 `project_revision` 变化；
- report/prompt/dialogue language、visual style、delivery 和 prompt-context 默认值；
- source trust/rights 默认值；
- confirmed mutable artifact 的 snapshot 计划；
- 必须标为 invalid 的 artifact 及原因。

Dry run 不写文件。

## Apply

```bash
python scripts/state_cli.py migrate-project --project-dir <PROJECT> --apply
```

可安全迁移的 confirmed artifact 必须同时满足：

- 路径在项目内；
- 文件存在且是普通文件；
- 已登记合法 SHA-256；
- 磁盘内容与登记 hash 一致。

仍使用 mutable 路径的 artifact 会复制到同目录 `-vNNN` snapshot，并更新 state 指针。已经带版本号且 hash 匹配的路径保持不变。`locked-assets` 继续指向 `asset-manifest.json` projection。

以下情况不会猜测或覆盖，而是把 artifact 标为 `invalid`：

- 文件缺失；
- SHA 缺失或失配；
- 路径不安全；
- path/revision 结构无效。

若目标 snapshot 已存在但 hash 不同，整个 apply 失败且项目保持原状。

## 迁移后

```bash
python scripts/validate_project.py <PROJECT>
python scripts/state_cli.py migrate-project --project-dir <PROJECT> --dry-run
```

第二次 dry run 应报告无变化。对 invalid artifact，必须从可信历史来源重新导入或重新生成；不要直接改回 confirmed。

## 版本边界

迁移后的典型基线是：

- `project-state.json`: schema v2；
- `short-drama-engine.json`: attach 后 schema v2；
- `asset-manifest.json`: 当前 CLI 操作基线 schema v1；
- `continuity-ledger.json`: 当前操作格式 schema v1。

这些文件拥有独立 schema，不要求版本号同步变化。
