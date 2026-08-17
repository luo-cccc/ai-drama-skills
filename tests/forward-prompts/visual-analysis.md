Resolve `<WORKSPACE_ROOT>` to the root of the current checkout. Use `$ai-drama-character-design` and `$ai-drama-shot-analysis` by reading these packaged Skills:

- `<WORKSPACE_ROOT>/.agents/skills/ai-drama-character-design/SKILL.md`
- `<WORKSPACE_ROOT>/.agents/skills/ai-drama-shot-analysis/SKILL.md`

用户任务：按 `<WORKSPACE_ROOT>/tests/forward-fixtures/visual-and-analysis-input.md` 完成角色综合设定与短视频逐镜拉片。先运行 `<WORKSPACE_ROOT>/scripts/create_video_fixture.py`，把视频写入输出目录后再基于实际文件分析，不要读取脚本源码来推断切点。把全部产物写入 `<WORKSPACE_ROOT>/tests/.forward-runs/visual-analysis-r2`。

图像能力可用时直接生成并检查角色图；不可用时按 Skill 降级为 `visual-brief-v001.md` 且标记 `prompt-only`。复杂中文排版不可靠时交付无字图与独立 UTF-8 标签文件。拉片必须区分实证、估算和未知。最终消息只报告产物、视觉模式与拉片范围。

Windows 工具提示：`apply_patch.bat` 直接接收较长或含中文参数时可能失真。必要时解析该包装器中的 `codex.exe`，用 `--codex-run-as-apply-patch` 传入 UTF-8 补丁。
