Resolve `<WORKSPACE_ROOT>` to the root of the current checkout. Use `$ai-drama-forging` by reading `<WORKSPACE_ROOT>/.agents/skills/ai-drama-forging/SKILL.md` and the sibling packaged domain Skills it routes to.

用户任务：把下面的完整故事制作为 90 秒现实主义短片项目，输出提示包、分场、剧本 v001、审计 v001、剧本 v002、审计 v002、资产、连续性、精确分镜和不超过 30 秒的导出片段。把产物写入 `<WORKSPACE_ROOT>/tests/.forward-runs/mature-r2`，使用英文稳定文件名和简体中文正文。

我明确预授权自动完成并确认提示包、分场与两稿剧本；授权范围包含 `screenplay-v001` 和 `screenplay-v002`。对 v002 的自动确认条件是审计后 P0=0 且 P1=0、必保元素全部可检索、90 秒主轴闭合。满足时可将 v002 记为 `confirmed` 并继续正式资产和分镜；不满足时保持待确认并说明阻断。把本段授权原文和每个自动检查点写入状态。

故事：暴雨凌晨，末班公交回到总站，清洁员沈岚在最后一排发现一个装着胰岛素的保温袋。司机高诚急着下班照顾发烧的女儿，认为失主会自行联系；沈岚从袋内褪色的就诊卡认出失主是每天独自乘车的听障老人。调度系统已关闭，车载录像也断网。沈岚坚持按老人固定下车点逆向寻找，高诚起初拒绝，最终把女儿托给邻居并重新发车。两人在积水的旧市场找到因低血糖坐倒的老人。高诚负责呼叫急救和照明，沈岚把保温袋交给医护人员，不自行给药。天亮回站，高诚把“末班清车确认”写进交接板，沈岚只擦掉车窗上的雨水。基调克制，结局明确，不夸大医疗操作。

完成后运行项目与时间轴校验，并只在最终消息中简要列出文件、状态和限制。

Windows 工具提示：`apply_patch.bat` 直接接收较长或含中文参数时可能失真。必要时解析该包装器中的 `codex.exe`，用 `--codex-run-as-apply-patch` 传入 UTF-8 补丁，并把大文件拆成多个短补丁。
