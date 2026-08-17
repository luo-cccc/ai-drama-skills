#!/usr/bin/env python3
"""Validate, segment, and render canonical AI Drama Forging shot plans."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


SHOT_ID_RE = re.compile(r"^SHOT-\d{3}$")
BEAT_ID_RE = re.compile(r"^BEAT-\d{3}$")
SCENE_ID_RE = re.compile(r"^SCN-\d{3}$")
ASSET_ID_RE = re.compile(r"^(?:CHAR|SCENE|PROP|MOTIF|COSTUME|BG)-\d{3}(?:-V\d{2})?$")


class TimelineError(ValueError):
    pass


def load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["shot plan top level must be an object"]
    required = {"schema_version", "project_id", "plan_version", "target_runtime_ms", "profile", "scenes", "beats", "shots"}
    missing = sorted(required - plan.keys())
    if missing:
        errors.append(f"shot plan missing keys: {', '.join(missing)}")
    unknown = sorted(plan.keys() - required - {"scope", "timeline_start_ms", "timeline_end_ms"})
    if unknown:
        errors.append(f"shot plan has unknown keys: {', '.join(unknown)}")
    if plan.get("schema_version") not in {"1.0", "2.0"}:
        errors.append("shot plan schema_version must be 1.0 or 2.0")
    if not isinstance(plan.get("project_id"), str) or not re.fullmatch(r"PROJECT-\d{3}", plan.get("project_id", "")):
        errors.append(f"invalid project_id: {plan.get('project_id')}")
    if not isinstance(plan.get("plan_version"), int) or isinstance(plan.get("plan_version"), bool) or plan.get("plan_version", 0) < 1:
        errors.append("plan_version must be a positive integer")

    profile = plan.get("profile")
    if not isinstance(profile, dict):
        errors.append("profile must be an object")
        profile = {}
    profile_keys = {
        "clip_max_duration_ms", "audio_policy", "subtitle_policy", "aspect_ratio", "generator",
        "editing_policy", "visual_reset_policy", "dialogue_rate_chars_per_second",
    }
    for key in profile_keys:
        if key not in profile:
            errors.append(f"profile missing key: {key}")
    unknown_profile = sorted(profile.keys() - profile_keys)
    if unknown_profile:
        errors.append(f"profile has unknown keys: {', '.join(unknown_profile)}")
    clip_max = profile.get("clip_max_duration_ms")
    if not isinstance(clip_max, int) or isinstance(clip_max, bool) or clip_max < 1:
        errors.append("profile.clip_max_duration_ms must be a positive integer")
    for key in ["audio_policy", "subtitle_policy", "aspect_ratio", "generator", "editing_policy", "visual_reset_policy"]:
        if key in profile and not isinstance(profile[key], str):
            errors.append(f"profile.{key} must be a string")
    dialogue_rate = profile.get("dialogue_rate_chars_per_second")
    if not isinstance(dialogue_rate, (int, float)) or isinstance(dialogue_rate, bool) or not 1 <= dialogue_rate <= 20:
        errors.append("profile.dialogue_rate_chars_per_second must be between 1 and 20")

    scenes = plan.get("scenes", [])
    if not isinstance(scenes, list):
        errors.append("scenes must be an array")
        scenes = []
    scene_ids: set[str] = set()
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            errors.append(f"scene {index} must be an object")
            continue
        scene_id = scene.get("scene_id")
        unknown_scene = sorted(scene.keys() - {"scene_id", "name"})
        if unknown_scene:
            errors.append(f"scene {index} has unknown keys: {', '.join(unknown_scene)}")
        if not isinstance(scene_id, str) or not SCENE_ID_RE.fullmatch(scene_id):
            errors.append(f"invalid scene_id: {scene_id}")
        elif scene_id in scene_ids:
            errors.append(f"duplicate scene_id: {scene_id}")
        else:
            scene_ids.add(scene_id)
        if "name" in scene and (not isinstance(scene["name"], str) or not scene["name"]):
            errors.append(f"scene {scene_id or index} name must be a non-empty string")

    beats = plan.get("beats", [])
    if not isinstance(beats, list):
        errors.append("beats must be an array")
        beats = []
    beat_ids: set[str] = set()
    for index, beat in enumerate(beats, start=1):
        if not isinstance(beat, dict):
            errors.append(f"beat {index} must be an object")
            continue
        missing_beat = sorted({"beat_id", "summary", "indivisible"} - beat.keys())
        if missing_beat:
            errors.append(f"beat {index} missing keys: {', '.join(missing_beat)}")
        allowed_beat = {"beat_id", "summary", "indivisible", "source_scene_ref", "source_beat_range", "source_beats"}
        unknown_beat = sorted(beat.keys() - allowed_beat)
        if unknown_beat:
            errors.append(f"beat {index} has unknown keys: {', '.join(unknown_beat)}")
        beat_id = beat.get("beat_id")
        if not isinstance(beat_id, str) or not BEAT_ID_RE.fullmatch(beat_id):
            errors.append(f"invalid beat_id: {beat_id}")
        elif beat_id in beat_ids:
            errors.append(f"duplicate beat_id: {beat_id}")
        else:
            beat_ids.add(beat_id)
        if "summary" in beat and not isinstance(beat["summary"], str):
            errors.append(f"beat {beat_id or index} summary must be a string")
        if "indivisible" in beat and not isinstance(beat["indivisible"], bool):
            errors.append(f"beat {beat_id or index} indivisible must be boolean")
        if plan.get("schema_version") == "2.0":
            for key in ("source_scene_ref", "source_beat_range", "source_beats"):
                if key not in beat:
                    errors.append(f"beat {beat_id or index} missing v2 provenance field: {key}")
            source_range = beat.get("source_beat_range")
            if (not isinstance(source_range, list) or len(source_range) != 2
                    or any(not isinstance(item, int) or isinstance(item, bool) or item < 1 for item in source_range)
                    or source_range[1] < source_range[0]):
                errors.append(f"beat {beat_id or index} has invalid source_beat_range")
            if not isinstance(beat.get("source_beats"), list) or not beat.get("source_beats"):
                errors.append(f"beat {beat_id or index} source_beats must be non-empty")

    shots = plan.get("shots", [])
    if not isinstance(shots, list):
        errors.append("shots must be an array")
        shots = []
    target = plan.get("target_runtime_ms")
    if not isinstance(target, int) or isinstance(target, bool) or target < 1:
        errors.append("target_runtime_ms must be a positive integer")
    timeline_start = plan.get("timeline_start_ms", 0)
    timeline_end = plan.get("timeline_end_ms", target)
    scope = plan.get("scope")
    if scope is not None:
        if isinstance(scope, dict) and scope == {"kind": "series"}:
            pass
        elif (not isinstance(scope, dict) or set(scope) != {"kind", "start", "end"}
                or scope.get("kind") != "episodes"):
            errors.append("scope must be a series or episodes object")
        else:
            start_episode, end_episode = scope.get("start"), scope.get("end")
            if (not isinstance(start_episode, int) or isinstance(start_episode, bool)
                    or not isinstance(end_episode, int) or isinstance(end_episode, bool)
                    or start_episode < 1 or end_episode < start_episode):
                errors.append("scope requires integer 1 <= start <= end")
        if "timeline_start_ms" not in plan or "timeline_end_ms" not in plan:
            errors.append("scoped shot plan requires timeline_start_ms and timeline_end_ms")
    if not isinstance(timeline_start, int) or isinstance(timeline_start, bool) or timeline_start < 0:
        errors.append("timeline_start_ms must be a non-negative integer")
        timeline_start = 0
    if (not isinstance(timeline_end, int) or isinstance(timeline_end, bool)
            or timeline_end <= timeline_start):
        errors.append("timeline_end_ms must be greater than timeline_start_ms")
        timeline_end = target if isinstance(target, int) else timeline_start
    if isinstance(target, int) and not isinstance(target, bool) and timeline_end > target:
        errors.append("timeline_end_ms cannot exceed target_runtime_ms")
    seen_shots: set[str] = set()
    used_beats: set[str] = set()
    closed_beats: set[str] = set()
    active_beat: str | None = None
    closed_groups: set[str] = set()
    active_group: str | None = None
    cursor = timeline_start
    for index, shot in enumerate(shots, start=1):
        if not isinstance(shot, dict):
            errors.append(f"shot {index} must be an object")
            continue
        required_shot = {"shot_id", "scene_id", "beat_id", "start_ms", "end_ms", "framing", "angle", "movement", "transition", "visual", "assets"}
        missing_shot = sorted(required_shot - shot.keys())
        if missing_shot:
            errors.append(f"shot {index} missing keys: {', '.join(missing_shot)}")
        allowed_shot = required_shot | {"performance", "dialogue", "sound", "prompt", "prompt_ref", "negative_constraints", "model_parameters", "generation_group"}
        unknown_shot = sorted(shot.keys() - allowed_shot)
        if unknown_shot:
            errors.append(f"shot {index} has unknown keys: {', '.join(unknown_shot)}")
        shot_id = shot.get("shot_id")
        if not isinstance(shot_id, str) or not SHOT_ID_RE.fullmatch(shot_id):
            errors.append(f"invalid shot_id: {shot_id}")
        elif shot_id in seen_shots:
            errors.append(f"duplicate shot_id: {shot_id}")
        else:
            seen_shots.add(shot_id)
        start = shot.get("start_ms")
        end = shot.get("end_ms")
        if start != cursor:
            errors.append(f"shot {shot_id or index} starts at {start}, expected {cursor}")
        if (not isinstance(end, int) or isinstance(end, bool) or not isinstance(start, int)
                or isinstance(start, bool) or end <= start):
            errors.append(f"shot {shot_id or index} has invalid timing {start}-{end}")
        else:
            cursor = end
        scene_id = shot.get("scene_id")
        if not isinstance(scene_id, str) or scene_id not in scene_ids:
            errors.append(f"shot {shot_id or index} references unknown scene {scene_id}")
        beat_id = shot.get("beat_id")
        if not isinstance(beat_id, str) or beat_id not in beat_ids:
            errors.append(f"shot {shot_id or index} references unknown beat {beat_id}")
        else:
            used_beats.add(beat_id)
            if beat_id != active_beat:
                if active_beat is not None:
                    closed_beats.add(active_beat)
                if beat_id in closed_beats:
                    errors.append(f"beat {beat_id} is not contiguous")
                active_beat = beat_id
        generation_group = shot.get("generation_group")
        if generation_group is not None:
            if not isinstance(generation_group, str) or not generation_group:
                errors.append(f"shot {shot_id or index} generation_group must be a non-empty string")
            elif generation_group != active_group:
                if active_group is not None:
                    closed_groups.add(active_group)
                if generation_group in closed_groups:
                    errors.append(f"generation group {generation_group} is not contiguous")
                active_group = generation_group
        for key in ["framing", "angle", "movement", "transition", "visual"]:
            if key in shot and (not isinstance(shot[key], str) or (key == "visual" and not shot[key])):
                errors.append(f"shot {shot_id or index} {key} must be a valid string")
        for key in ["performance", "dialogue", "sound"]:
            if key in shot and not isinstance(shot[key], str):
                errors.append(f"shot {shot_id or index} {key} must be a string")
        dialogue = shot.get("dialogue")
        if isinstance(dialogue, str) and dialogue.strip() and isinstance(start, int) and isinstance(end, int) and end > start:
            cjk_units = len(re.findall(r"[\u3400-\u9fff]", dialogue))
            latin_words = len(re.findall(r"\b[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*\b", dialogue))
            speech_units = cjk_units + latin_words * 2
            if speech_units and isinstance(dialogue_rate, (int, float)) and not isinstance(dialogue_rate, bool) and dialogue_rate > 0:
                required_ms = math.ceil(speech_units / dialogue_rate * 1000)
                if end - start < required_ms:
                    errors.append(
                        f"shot {shot_id or index} dialogue needs about {required_ms}ms at "
                        f"{dialogue_rate:g} chars/s, available {end - start}ms"
                    )
        if "prompt" in shot and not isinstance(shot["prompt"], str):
            errors.append(f"shot {shot_id or index} prompt must be a string")
        if "prompt_ref" in shot and (not isinstance(shot["prompt_ref"], str) or not shot["prompt_ref"]):
            errors.append(f"shot {shot_id or index} prompt_ref must be a non-empty string")
        if plan.get("schema_version") == "2.0":
            for key in ("performance", "dialogue", "sound", "generation_group", "prompt_ref"):
                if key not in shot:
                    errors.append(f"shot {shot_id or index} missing v2 production field: {key}")
        negative = shot.get("negative_constraints", [])
        if not isinstance(negative, list) or any(not isinstance(item, str) for item in negative):
            errors.append(f"shot {shot_id or index} negative_constraints must be an array of strings")
        parameters = shot.get("model_parameters", {})
        if not isinstance(parameters, dict):
            errors.append(f"shot {shot_id or index} model_parameters must be an object")
        assets = shot.get("assets")
        if not isinstance(assets, list):
            errors.append(f"shot {shot_id or index} assets must be an array")
        else:
            string_assets = [asset for asset in assets if isinstance(asset, str)]
            if len(string_assets) != len(set(string_assets)):
                errors.append(f"shot {shot_id or index} has duplicate asset references")
            for asset in assets:
                if not isinstance(asset, str) or not ASSET_ID_RE.fullmatch(asset):
                    errors.append(f"shot {shot_id or index} has invalid asset ID: {asset}")
    if not shots:
        errors.append("shot plan has no shots")
    unused_beats = beat_ids - used_beats
    if unused_beats:
        errors.append(f"unused beats: {sorted(unused_beats)}")
    if isinstance(timeline_end, int) and cursor != timeline_end:
        errors.append(f"timeline ends at {cursor}, scoped end is {timeline_end}")
    return errors


def segment_plan(plan: dict[str, Any], maximum: int | None = None) -> list[dict[str, Any]]:
    errors = validate_plan(plan)
    if errors:
        raise TimelineError("; ".join(errors))
    shots = plan["shots"]
    max_ms = maximum if maximum is not None else plan["profile"]["clip_max_duration_ms"]
    if not isinstance(max_ms, int) or isinstance(max_ms, bool) or max_ms < 1:
        raise TimelineError("maximum clip duration must be a positive integer")
    clips: list[dict[str, Any]] = []
    if any(shot.get("generation_group") for shot in shots):
        start_index = 0
        while start_index < len(shots):
            group = shots[start_index].get("generation_group")
            if not group:
                raise TimelineError("all shots must declare generation_group when any shot declares it")
            end_index = start_index
            while end_index + 1 < len(shots) and shots[end_index + 1].get("generation_group") == group:
                end_index += 1
            selected = shots[start_index:end_index + 1]
            duration = selected[-1]["end_ms"] - selected[0]["start_ms"]
            if duration > max_ms:
                raise TimelineError(f"generation group {group} exceeds {max_ms}ms and cannot be split")
            clips.append(make_clip(clips, selected, group))
            start_index = end_index + 1
        return clips
    start_index = 0
    while start_index < len(shots):
        clip_start = shots[start_index]["start_ms"]
        limit = clip_start + max_ms
        candidates: list[int] = []
        for index in range(start_index, len(shots)):
            shot = shots[index]
            if shot["end_ms"] > limit:
                break
            is_plan_end = index == len(shots) - 1
            is_beat_end = is_plan_end or shots[index + 1]["beat_id"] != shot["beat_id"]
            if is_beat_end:
                candidates.append(index)
        if not candidates:
            beat = shots[start_index]["beat_id"]
            raise TimelineError(f"beat {beat} has no legal boundary within {max_ms}ms")
        end_index = candidates[-1]
        selected = shots[start_index : end_index + 1]
        clips.append(make_clip(clips, selected))
        start_index = end_index + 1
    return clips


def make_clip(
    clips: list[dict[str, Any]], selected: list[dict[str, Any]], generation_group: str | None = None
) -> dict[str, Any]:
    clip = {
            "clip_id": f"CLIP-{len(clips) + 1:03d}",
            "start_ms": selected[0]["start_ms"],
            "end_ms": selected[-1]["end_ms"],
            "shot_ids": [shot["shot_id"] for shot in selected],
            "beat_ids": list(dict.fromkeys(shot["beat_id"] for shot in selected)),
            "duration_ms": selected[-1]["end_ms"] - selected[0]["start_ms"],
            "relative_shots": [
                {
                    "shot_id": shot["shot_id"],
                    "source_start_ms": shot["start_ms"],
                    "source_end_ms": shot["end_ms"],
                    "relative_start_ms": shot["start_ms"] - selected[0]["start_ms"],
                    "relative_end_ms": shot["end_ms"] - selected[0]["start_ms"],
                }
                for shot in selected
            ],
        }
    if generation_group is not None:
        clip["generation_group"] = generation_group
    return clip


def format_seconds(milliseconds: int) -> str:
    seconds = milliseconds / 1000
    return f"{seconds:g}s"


def markdown_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_markdown(plan: dict[str, Any]) -> str:
    errors = validate_plan(plan)
    if errors:
        raise TimelineError("; ".join(errors))
    rows = [
        "# Shot Plan",
        "",
        f"Target runtime: {format_seconds(plan['target_runtime_ms'])}",
        "",
        "| Shot | Scene | Beat | Time | Framing | Angle | Movement | Transition | Visual | Performance | Dialogue | Sound | Assets | Prompt | Negative | Model Parameters |",
        "|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|",
    ]
    for shot in plan["shots"]:
        visual = markdown_cell(shot["visual"])
        rows.append(
            f"| {shot['shot_id']} | {shot['scene_id']} | {shot['beat_id']} | "
            f"{format_seconds(shot['start_ms'])}-{format_seconds(shot['end_ms'])} | "
            f"{markdown_cell(shot['framing'])} | {markdown_cell(shot['angle'])} | "
            f"{markdown_cell(shot['movement'])} | {markdown_cell(shot['transition'])} | "
            f"{visual} | {markdown_cell(shot.get('performance', ''))} | "
            f"{markdown_cell(shot.get('dialogue', ''))} | {markdown_cell(shot.get('sound', ''))} | "
            f"{markdown_cell(', '.join(shot['assets']))} | {markdown_cell(shot.get('prompt', ''))} | "
            f"{markdown_cell(', '.join(shot.get('negative_constraints', [])))} | "
            f"{markdown_cell(json.dumps(shot.get('model_parameters', {}), ensure_ascii=False, sort_keys=True))} |"
        )
    return "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--input", required=True)
    segment = sub.add_parser("segment")
    segment.add_argument("--input", required=True)
    segment.add_argument("--output")
    segment.add_argument("--max-ms", type=int)
    render = sub.add_parser("render")
    render.add_argument("--input", required=True)
    render.add_argument("--output", required=True)
    args = parser.parse_args()
    plan = load(args.input)
    if args.command == "validate":
        errors = validate_plan(plan)
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print("PASS: timeline is continuous and exact")
        return 0
    if args.command == "segment":
        clips = segment_plan(plan, args.max_ms)
        output = json.dumps({"clips": clips}, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
        else:
            print(output, end="")
        return 0
    Path(args.output).write_text(render_markdown(plan), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
