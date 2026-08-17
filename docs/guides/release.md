# 发布与验证

## 规范源与生成物

发布只从以下规范源构建：

- `src/skills/`
- `shared/references/`
- `scripts/`
- `schemas/`
- `engine/shuohao-runtime/`
- `vendor/shuohao/` 中 manifest 指定文件

`.agents/skills/` 是从上述规范源生成并受版本控制的标准安装面。不要手工编辑 `.agents/skills/` 或 `dist/`。不要把 `engine/shuohao-adapted/` 直接当发行 runtime；runtime 由 snapshot 同步生成。

## 验证顺序

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/validate_project.py examples/synthetic-short
python scripts/validate_project.py examples/legacy-yiqiyang
python scripts/sync_shuohao_snapshot.py --source ../shuohao-skills-main --check
```

五套 adapted Node selftest 由 Python suite 覆盖，也可以单独运行对应 `selftest.mjs`。

## 构建

```bash
python scripts/package_skills.py
python tests/verify_dist.py
```

默认构建目标为 `.agents/skills/`。需要临时发布树时使用 `python scripts/package_skills.py --output dist`，并以 `python tests/verify_dist.py --dist dist` 校验。

`verify_dist.py` 检查：

- package manifest 文件集合和 SHA-256；
- validator、project store 等运行依赖是否齐全；
- 从包外目录执行脚本 `--help`；
- 隔离检查不会污染 package tree。

它不是模型端到端测试，也不会生成真实影视内容。

## 确定性

连续构建到两个空目录，比较所有相对路径和文件 SHA。任何差异都应视为 release failure。构建器不会覆盖无法识别的 foreign output，并在目录交换失败时保留旧包。

## Release Evidence

一次可复核发布至少记录：

- 日期和工作区版本标识；
- Python、Node、FFmpeg、Pillow 等环境；
- Python 测试通过/失败/skip 数；
- 五套 Node selftest 计数；
- example validator 和 Schema lint 结果；
- snapshot 文件数和 manifest hash；
- 标准安装面 Skill 数、package file 数和 package manifest SHA；
- 两次构建的 tree-hash 比较；
- 未执行或条件跳过的项目。

自动化 release evidence 与 forward/model evaluation 分开记录。release pass 不表示模型输出质量、真实媒体或外部服务已经通过。仓库记录格式见 [release-validation.md](../../tests/release-validation.md)。

## 第三方文件

shuohao upstream snapshot 保持只读。发行包应同时包含 upstream LICENSE、NOTICE 和 Forging modification addendum。来源边界见 [PROVENANCE.md](../../PROVENANCE.md)。
