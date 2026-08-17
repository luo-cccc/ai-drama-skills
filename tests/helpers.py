from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def read_text(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def markdown_files(*parts: str) -> list[Path]:
    return sorted(ROOT.joinpath(*parts).glob("*.md"))


def host_absolute_paths(text: str) -> list[str]:
    patterns = (
        r"(?<![A-Za-z0-9_])[A-Za-z]:[\/][^\s`]+",
        r"(?<![A-Za-z0-9_<])/(?:Users|home|private|tmp|var|opt|mnt)/[^\s`]+",
    )
    return [match.group(0) for pattern in patterns for match in re.finditer(pattern, text)]


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_audit_json(
    path: Path,
    targets: list[dict],
    scope: dict | None = None,
    decision: str = "pass",
) -> None:
    source_ref = targets[0]["artifact_id"]
    report = {
        "schema_version": "2.0",
        "mode": "conformance",
        "scope": scope or {"kind": "series"},
        "targets": targets,
        "basis": [{
            "kind": "screenplay", "ref": source_ref,
            "sha256": targets[0]["sha256"], "availability": "available",
        }],
        "findings": [],
        "required_elements": [{
            "element_id": "REQ-001", "requirement": "core event", "source_ref": source_ref,
            "result": "pass", "evidence": [{
                "source_ref": source_ref, "locator": "E01", "quote": "event",
                "evidence_status": "observed",
            }],
        }],
        "differences": [],
        "decision": decision,
        "limitations": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, report)


def write_audit(
    path: Path,
    decision: str = "pass",
    screenplay_ids: list[str] | None = None,
    scope: dict | None = None,
) -> None:
    result = {
        "p0_count": 0,
        "p1_count": 0,
        "p2_count": 0,
        "required_elements_total": 5,
        "required_elements_passed": 5,
        "decision": decision,
    }
    marker = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"<!-- ai-drama-audit {marker} -->\n# Evidence audit\n\n"
        "审计模式：conformance\n\n"
        f"审计对象：{', '.join(screenplay_ids or [])}\n\n"
        f"审计范围：{json.dumps(scope or {'kind': 'series'}, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## 必保元素证据表\n\n| 元素 | 证据 | 状态 |\n|---|---|---|\n| 核心事件 | E01 | 通过 |\n\n"
        "## 大纲与剧本差异表\n\n| 大纲 | 剧本 | 判断 |\n|---|---|---|\n| E01 | E01 | 等价 |\n",
        encoding="utf-8",
    )


def sample_plan(duration_ms: int) -> dict:
    shots = []
    beats = []
    cursor = 0
    index = 1
    while cursor < duration_ms:
        end = min(cursor + 30000, duration_ms)
        beat_id = f"BEAT-{index:03d}"
        beats.append({"beat_id": beat_id, "summary": f"beat {index}", "indivisible": True})
        shots.append({
            "shot_id": f"SHOT-{index:03d}", "scene_id": "SCN-001", "beat_id": beat_id,
            "start_ms": cursor, "end_ms": end, "framing": "中景", "angle": "正面",
            "movement": "固定", "transition": "cut", "visual": f"beat {index}",
            "performance": "", "dialogue": "", "sound": "", "assets": ["SCENE-001"],
        })
        cursor = end
        index += 1
    return {
        "schema_version": "1.0", "project_id": "PROJECT-001", "plan_version": 1,
        "target_runtime_ms": duration_ms,
        "profile": {
            "clip_max_duration_ms": 30000, "audio_policy": "preserve", "subtitle_policy": "unspecified",
            "aspect_ratio": "16:9", "generator": "unspecified", "editing_policy": "story-driven",
            "visual_reset_policy": "story-driven", "dialogue_rate_chars_per_second": 4.5,
        },
        "scenes": [{"scene_id": "SCN-001"}], "beats": beats, "shots": shots,
    }
