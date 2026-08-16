# Test Fixtures

此目录保留给跨文件、跨集的确定性测试资料。fixture 必须人工合成、可公开、最小但足以暴露范围、状态和连续性错误，不复制真实项目内容，也不依赖私有会话或模型调用。

当前两集 fixture 由测试代码在临时目录中构造，因此这里不重复保存一套容易漂移的 JSON 项目树。`tests/forward-fixtures/` 属于前向测试输入，和本目录的确定性 fixture 不是同一种证据。

## 两集 fixture

`tests/test_two_episode_pipeline.py` 先调用真实 `init` 和 `attach`，再以人工合成数据程序化登记最小 outline、screenplay、audit、shot-plan 和 generation-manifest artifact graph，验证从 scoped plans 到 planning complete 的机器闭环。它不调用模型，也不依赖真实项目内容。它覆盖：

- 两个互不重叠的 confirmed screenplay 与 series conformance audit；
- 两个精确闭合的 scoped shot plan，以及无损 series aggregate；
- 每集 generation manifest、Prompt 相对路径与 SHA-256 对账；
- immutable aggregate snapshot 与根 `shot-plan.json` projection 一致；
- scoped plans 和 generation manifests 在聚合后仍保持 confirmed；
- locked-assets、completion ID/SHA 绑定和最终 project/engine validator。

它不覆盖 source registration、模型执行、cast/art import、prompt-context 生成与消费、`delivery_required=true`、真实媒体或从隔离 `dist` 启动整条业务链。范围缺口、重叠、字段丢失、Prompt 篡改、completion 记录错配和媒体 QC 失败由其他 hardening tests 分别覆盖。临时文件由测试生命周期管理，不应提交运行产物或把某次临时目录当作 release evidence。
