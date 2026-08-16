# Tests

本目录包含确定性自动化测试、合成 fixture、前向测试输入，以及历史前向测试记录。不同证据类型必须分开解释。

## 自动化入口

运行 Python 测试套件：

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

主要覆盖范围包括：

- manifest、路由、打包确定性和已有包交换保护；
- 项目状态、事务、迁移、checkpoint、审查和上游失效传播；
- schema、时间线、资产、连续性、generation manifest、媒体交付和完成门禁；
- 两集 scoped plan 聚合与 series coverage；
- shuohao 上游快照、adapted/runtime 映射和五组 Node selftests；
- `examples/` 的来源、版本、canonical 边界和局部分镜回归；
- 前向 prompt 的可移植路径占位符，以及历史报告必须保持 stale/fail 标记。

## 独立校验命令

```bash
python scripts/validate_project.py examples/synthetic-short
python scripts/validate_project.py examples/legacy-yiqiyang
python scripts/sync_shuohao_snapshot.py --source ../shuohao-skills-main --check
python scripts/package_skills.py --output dist
python tests/verify_dist.py --dist dist
```

`verify_dist.py` 不属于 `test_*.py` discovery；它单独检查 package manifest、运行依赖、包外 `--help` 导入和 package tree 无污染。release acceptance 要求 Python suite 无失败、所有 skip 有记录、snapshot/examples/dist 独立检查通过，并完成两次构建 tree-hash 比较。

## 环境与 Skip

- Node.js 18+：五套 shuohao selftest 和 snapshot check 必需。
- `../shuohao-skills-main` sibling checkout：snapshot source/许可核对需要；缺失时全量 release 验证不完整。
- FFmpeg/ffprobe：视频 fixture、probe 和切点测试需要；缺少时相应测试会 skip。
- Pillow 与可用 CJK 字体：确定性中文视觉排版测试需要；能力不足时相应测试会 skip。

记录测试结果时必须列出实际 skip 数及原因，不能只写“PASS”。

## 证据分类

| 文档或目录 | 证据类型 | 能证明什么 | 不能证明什么 |
|:--|:--|:--|:--|
| Python tests 与 adapted Node selftests | 确定性代码证据 | 当前被执行 checkout 的结构、合同和回归行为 | 模型在开放任务中的质量 |
| `examples/` | 合成或历史 fixture 证据 | 固定文件之间的可重复一致性 | 新模型调用、真实媒体生成或未分发来源的忠实度 |
| [release-validation.md](release-validation.md) | 已完成 release run 记录 | 指定日期那次打包与确定性验证结果 | 当前 forward/model gate |
| [forward-test-report.md](forward-test-report.md) | 历史模型/agent 观察 | 旧运行曾观察到的行为和由此触发的修复 | 当前 checkout 的有效前向认证 |

当前 forward/model evidence gate 仍以 [forward-test-report.md](forward-test-report.md) 为准，并保持 **FAIL**，直到对当前 checkout 或当前 release package 完成新的隔离前向运行。

[fixtures/README.md](fixtures/README.md) 说明 fixture 原则；`forward-fixtures/` 和 `forward-prompts/` 是前向运行输入，不是通过结果本身。
