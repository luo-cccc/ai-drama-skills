Resolve `<WORKSPACE_ROOT>` to the root of the current checkout. Use `$ai-drama-storyboard` by reading `<WORKSPACE_ROOT>/.agents/skills/ai-drama-storyboard/SKILL.md`.

用户任务：按 `<WORKSPACE_ROOT>/tests/forward-fixtures/storyboard-135-input.md` 生成 C 级执行分镜。把 `shot-plan.json`、`storyboard-v001.md` 和导出片段 JSON 写入 `<WORKSPACE_ROOT>/tests/.forward-runs/storyboard-135`。运行发行包中的时间轴工具校验并分段；最终消息只报告文件、精确总时长与校验结果。

Windows 工具提示：`apply_patch.bat` 直接接收较长或含中文参数时可能失真。必要时解析该包装器中的 `codex.exe`，用 `--codex-run-as-apply-patch` 传入 UTF-8 补丁，并把大文件拆成多个短补丁。
