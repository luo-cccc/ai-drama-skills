#!/usr/bin/env python3
"""Route AI Drama Forging requests with a deterministic, testable decision table."""

from __future__ import annotations

import argparse
import json
from typing import Any


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


SHORT_DRAMA_SKILLS = (
    "ai-drama-short-drama-characters", "ai-drama-short-drama-outline", "ai-drama-short-drama-art",
    "ai-drama-short-drama-script", "ai-drama-short-drama-storyboard",
)


def route_request(text: str, project_state_present: bool = False, project_format: str | None = None) -> dict[str, Any]:
    normalized = text.lower().strip()
    mode = "project" if project_state_present or "project-state.json" in normalized else "standalone"
    for skill in SHORT_DRAMA_SKILLS:
        if f"${skill}" in normalized:
            return {"skill": skill, "mode": "project"}
    short_drama = contains_any(normalized, (
        "小说改短剧", "小说转短剧", "短剧全流程", "短剧执行引擎", "短剧投产",
        "novel to short drama", "short drama workflow", "short-drama engine",
    )) or project_format == "ai-short-drama-series"
    if short_drama:
        return {"skill": "ai-drama-short-drama", "mode": "project"}

    shot_analysis = contains_any(normalized, (
        "拉片", "真实切点", "反向分析", "逐镜分析", "估算拉片", "shot by shot",
        "shot analysis", "analyze this video", "analyse this video", "reverse engineer this video",
    ))
    character_design = contains_any(normalized, (
        "角色参考图", "角色服装", "角色设定", "角色正交", "角色四视", "角色综合设定",
        "角色表情", "表情表", "动作表", "角色动作", "character sheet", "character turnaround",
        "expression sheet", "pose sheet", "costume sheet",
    ))
    scene_design = contains_any(normalized, (
        "场景 90 度", "场景90度", "顶视布局", "场景顶视", "vr 全景", "vr全景", "场景四视",
        "场景正交", "场景机位", "scene turnaround", "environment turnaround", "top-down layout",
        "camera layout", "equirectangular", "vr panorama",
    )) or "场景" in normalized and contains_any(normalized, ("正交", "四视图", "俯视", "顶视", "机位", "全景"))
    signals = {
        "development": contains_any(normalized, (
            "想法", "概念", "世界观", "原创故事", "原创化", "故事开发", "人物小传",
            "develop this idea", "story concept", "concept", "worldbuilding", "originalize", "originalise",
        )),
        "screenplay": contains_any(normalized, (
            "剧本", "分场", "提示包", "screenplay", "scene outline", "production brief",
        )),
        "audit": contains_any(normalized, (
            "剧本审计", "剧本自检", "审计剧本", "版本对比", "符合性核对", "script audit",
            "screenplay audit", "compare screenplay versions",
        )),
        "assets": contains_any(normalized, (
            "资产", "视觉 dna", "资产清单", "asset manifest", "assets", "visual dna", "continuity manifest",
        )),
        "storyboard": contains_any(normalized, (
            "分镜", "关键镜头", "镜头表", "时间轴", "九宫格", "视频 prompt", "轴线", "机位连续",
            "storyboard", "shot list", "shot plan", "timeline", "video prompt",
        )),
    }
    screenplay_creation = contains_any(normalized, (
        "写剧本", "创作剧本", "改写剧本", "修订剧本并", "写成分场", "写成标准剧本",
        "write the screenplay", "rewrite the screenplay", "create the screenplay",
    ))
    if (signals["audit"] or signals["assets"] or signals["storyboard"]) and not screenplay_creation:
        signals["screenplay"] = False

    cross_stage_language = contains_any(normalized, (
        "全流程", "从这个想法开始", "帮我做到", "一直做到", "端到端", "完整项目",
        "end to end", "full workflow", "take this from", "through screenplay", "through production",
    ))
    if cross_stage_language:
        mode = "project"

    specific: list[str] = []
    if shot_analysis:
        specific.append("ai-drama-shot-analysis")
    if character_design:
        specific.append("ai-drama-character-design")
    if scene_design:
        specific.append("ai-drama-scene-design")
    specific.extend(
        {
            "development": "ai-drama-development",
            "screenplay": "ai-drama-screenplay",
            "audit": "ai-drama-script-audit",
            "assets": "ai-drama-assets",
            "storyboard": "ai-drama-storyboard",
        }[key]
        for key, present in signals.items() if present
    )
    specific = list(dict.fromkeys(specific))
    if len(specific) >= 2:
        return {"skill": "ai-drama-forging", "mode": "project" if cross_stage_language else mode}

    if shot_analysis:
        evidence = "confirmed"
        if contains_any(normalized, ("没有视频", "无视频")) and contains_any(normalized, ("没有可靠时长", "无可靠时长")):
            evidence = "unknown"
        elif contains_any(normalized, ("描述", "估算")):
            evidence = "inferred"
        return {"skill": "ai-drama-shot-analysis", "evidence": evidence, "mode": mode}
    if scene_design:
        result = {"skill": "ai-drama-scene-design", "mode": mode}
        if contains_any(normalized, ("没有图像工具", "无图像工具", "不能生成图像")):
            result["fallback"] = "prompt-only"
        return result
    if character_design:
        result = {"skill": "ai-drama-character-design", "mode": mode}
        if contains_any(normalized, ("没有图像工具", "无图像工具", "不能生成图像")):
            result["fallback"] = "prompt-only"
        return result
    if signals["storyboard"]:
        return {"skill": "ai-drama-storyboard", "mode": mode}
    if signals["audit"]:
        return {"skill": "ai-drama-script-audit", "mode": mode}
    if signals["assets"]:
        return {"skill": "ai-drama-assets", "mode": mode}
    if signals["screenplay"]:
        return {"skill": "ai-drama-screenplay", "mode": mode}
    if signals["development"]:
        return {"skill": "ai-drama-development", "mode": mode}
    return {"skill": "ai-drama-forging", "mode": mode}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", required=True)
    parser.add_argument("--project-state-present", action="store_true")
    parser.add_argument("--project-format")
    args = parser.parse_args()
    print(json.dumps(route_request(args.text, args.project_state_present, args.project_format), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
