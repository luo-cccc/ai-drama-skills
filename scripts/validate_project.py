#!/usr/bin/env python3
"""Validate AI Drama Forging canonical project data and artifact relationships."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
PROJECT_FILES = ["project-state.json", "asset-manifest.json", "continuity-ledger.json"]
ASSET_RE = re.compile(r"^(CHAR|SCENE|PROP|MOTIF|COSTUME|BG)-\d{3}(?:-V\d{2})?$")
PREFIX_BY_TYPE = {
    "character": "CHAR",
    "scene": "SCENE",
    "prop": "PROP",
    "motif": "MOTIF",
    "costume": "COSTUME",
    "background-group": "BG",
}
STAGES = {"intake", "development", "brief", "outline", "screenplay", "audit", "shots", "assets", "complete"}
ARTIFACT_STATUSES = {"draft", "pending-confirmation", "confirmed", "superseded", "invalid"}
LOCK_STATUSES = {"unlocked", "partial", "locked", "stale"}
SOURCE_AVAILABILITY = {"available", "missing", "not-distributed"}
SOURCE_AUTHORITY = {"canonical", "constraint", "reference", "unknown"}
CHECKPOINT_POLICIES = {"key-nodes", "automatic", "every-stage"}
CHECKPOINT_DECISIONS = {"confirmed", "revise", "automatic", "rejected"}
EVIDENCE_LEVELS = {"confirmed", "inferred", "unknown"}
AUDIT_DECISIONS = {"pass", "revise", "blocked", "accepted-with-risk"}
CHECKPOINT_STAGES = {"development", "brief", "outline", "screenplay", "audit", "shots", "assets"}
CONFIRMATION_STAGE_BY_TYPE = {
    "production-brief": "brief",
    "outline-skeleton": "outline",
    "series-outline": "outline",
    "scene-outline": "outline",
    "screenplay": "screenplay",
    "audit": "audit",
    "shot-plan": "shots",
    "storyboard": "shots",
    "short-drama-storyboard": "shots",
    "h3-export": "shots",
    "locked-assets": "assets",
    "asset-report": "assets",
    "generation-manifest": "shots",
    "delivery-manifest": "shots",
    "visual-delivery": "assets",
}
ARTIFACT_STAGE_BY_TYPE = {
    **CONFIRMATION_STAGE_BY_TYPE,
    "audit": "audit",
    "shot-plan": "shots",
    "storyboard": "shots",
    "short-drama-storyboard": "shots",
    "h3-export": "shots",
    "short-drama-cast": "development",
    "short-drama-art": "assets",
    "engine-report": "development",
    "storyboard-key": "shots",
    "storyboard-scene": "shots",
    "storyboard-detail": "shots",
    "locked-assets": "assets",
    "asset-report": "assets",
}
FORMAL_DOWNSTREAM_TYPES = {
    "shot-plan",
    "storyboard",
    "short-drama-storyboard",
    "h3-export",
    "storyboard-key",
    "storyboard-scene",
    "storyboard-detail",
    "locked-assets",
    "asset-report",
    "generation-manifest",
    "delivery-manifest",
    "visual-delivery",
}
PROJECT_SINGLETON_TYPES = {"production-brief", "outline-skeleton", "series-outline", "scene-outline"}
RANGED_TYPES = {"screenplay", "audit", "storyboard", "short-drama-storyboard", "shot-plan", "h3-export"}
PROJECT_ID_RE = re.compile(r"^PROJECT-\d{3}$")
SOURCE_ID_RE = re.compile(r"^SRC-\d{3}$")
ARTIFACT_ID_RE = re.compile(r"^ART-\d{3}$")
CHECKPOINT_ID_RE = re.compile(r"^CHK-\d{3}$")
EVENT_ID_RE = re.compile(r"^EVT-\d{3}$")
SHOT_ID_RE = re.compile(r"^SHOT-\d{3}$")
SCENE_ID_RE = re.compile(r"^SCN-\d{3}$")
SUPPORTED_SCHEMA_VERSIONS = {"1.0", "2.0"}
ARTIFACT_SCHEMA_BY_TYPE = {
    "shot-analysis": "shot-analysis.schema.json",
    "generation-manifest": "generation-manifest.schema.json",
    "delivery-manifest": "delivery-manifest.schema.json",
    "visual-delivery": "visual-delivery.schema.json",
    "hook-ledger": "hook-ledger.schema.json",
    "canon": "canon.schema.json",
    "canon-register": "canon.schema.json",
}


def safe_project_path(root: Path, value: Any, label: str, errors: list[str]) -> Path | None:
    """Resolve a project-relative path without ever following it outside the project."""
    if not isinstance(value, str) or not value:
        errors.append(f"{label} path must be a non-empty project-relative string")
        return None
    try:
        candidate = Path(value)
        if candidate.is_absolute():
            errors.append(f"{label} path escapes project directory: {value}")
            return None
        resolved_root = root.resolve()
        resolved = (resolved_root / candidate).resolve()
        resolved.relative_to(resolved_root)
    except ValueError:
        errors.append(f"{label} path escapes project directory: {value}")
        return None
    except (OSError, RuntimeError) as exc:
        errors.append(f"{label} path is invalid: {value!r}: {exc}")
        return None
    return resolved


def schema_path_for(name: str, version: Any) -> Path | None:
    base = SCHEMAS / name
    if version == "1.0":
        return base
    if version != "2.0":
        return None
    stem = name.removesuffix(".schema.json")
    candidates = [
        SCHEMAS / f"{stem}-v2.schema.json",
        SCHEMAS / f"{stem}.v2.schema.json",
        SCHEMAS / "v2" / name,
        base,
    ]
    for candidate in candidates:
        if not candidate.is_file():
            continue
        if candidate == base:
            try:
                schema = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                return candidate
            declared = schema.get("properties", {}).get("schema_version", {})
            if declared.get("const") != "2.0" and "2.0" not in declared.get("enum", []):
                continue
        return candidate
    return None


def validate_with_schema(instance: Any, schema_name: str, label: str, errors: list[str]) -> None:
    version = instance.get("schema_version") if isinstance(instance, dict) else None
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"{label} has unsupported schema_version: {version}")
        return
    if version == "1.0" and schema_name == "project-state.schema.json":
        return
    schema_path = schema_path_for(schema_name, version)
    if schema_path is None:
        errors.append(f"{label} schema_version {version} has no matching schema")
        return
    try:
        from schema_validator import validate_file  # pylint: disable=import-outside-toplevel
        errors.extend(validate_file(instance, schema_path, label))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"{label} schema validation failed safely: {exc}")


def evidence_base_ref(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return re.split(r"[:#]", value, maxsplit=1)[0]


def read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            errors.append(f"invalid JSON {path.name}: top level must be an object")
            return {}
        return value
    except FileNotFoundError:
        errors.append(f"missing file: {path.name}")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"invalid JSON {path.name}: {exc}")
    return {}


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_keys(obj: dict[str, Any], keys: set[str], label: str, errors: list[str]) -> None:
    missing = sorted(keys - obj.keys())
    if missing:
        errors.append(f"{label} missing keys: {', '.join(missing)}")


def reject_unknown_keys(obj: dict[str, Any], keys: set[str], label: str, errors: list[str]) -> None:
    unknown = sorted(obj.keys() - keys)
    if unknown:
        errors.append(f"{label} has unknown keys: {', '.join(unknown)}")


def duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    return {value for value in values if value in seen or seen.add(value)}


def is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def require_unique_strings(value: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        errors.append(f"{label} must be an array of strings")
        return []
    repeated = duplicates(value)
    if repeated:
        errors.append(f"{label} contains duplicates: {sorted(repeated)}")
    return value


def validate_scope(value: Any, label: str, errors: list[str]) -> None:
    if value is None or isinstance(value, str):
        return
    if not isinstance(value, dict):
        errors.append(f"{label} scope must be null, a legacy string, or an object")
        return
    kind = value.get("kind")
    if kind == "series":
        if set(value) != {"kind"}:
            errors.append(f"{label} series scope has unknown keys")
        return
    if kind == "episodes":
        if set(value) != {"kind", "start", "end"}:
            errors.append(f"{label} episode scope must contain only kind, start, and end")
            return
        start, end = value.get("start"), value.get("end")
        if (not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int)
                or isinstance(end, bool) or start < 1 or end < start):
            errors.append(f"{label} episode scope requires integer 1 <= start <= end")
        return
    errors.append(f"{label} scope has unsupported kind: {kind}")


def scope_interval(value: Any) -> tuple[int | None, int | None] | None:
    if value is None or isinstance(value, dict) and value.get("kind") == "series":
        return (None, None)
    if isinstance(value, dict) and value.get("kind") == "episodes":
        start, end = value.get("start"), value.get("end")
        if isinstance(start, int) and not isinstance(start, bool) and isinstance(end, int) and not isinstance(end, bool):
            return (start, end)
    return None


def scopes_overlap(left: Any, right: Any) -> bool:
    left_interval, right_interval = scope_interval(left), scope_interval(right)
    if left_interval == (None, None) or right_interval == (None, None):
        return True
    if left_interval is None or right_interval is None:
        return left == right
    return left_interval[0] <= right_interval[1] and right_interval[0] <= left_interval[1]


def scopes_cover(scopes: list[Any], target: Any, episode_count: int | None = None) -> bool:
    target_interval = scope_interval(target)
    if target_interval == (None, None):
        if any(scope_interval(scope) == (None, None) for scope in scopes):
            return True
        intervals = sorted(
            interval for scope in scopes
            if (interval := scope_interval(scope)) not in {None, (None, None)}
        )
        if not intervals or intervals[0][0] != 1:
            return False
        cursor = 1
        for start, end in intervals:
            if start > cursor:
                return False
            cursor = max(cursor, end + 1)
        return episode_count is None or cursor == episode_count + 1
    if target_interval is None:
        return target in scopes or any(scope_interval(scope) == (None, None) for scope in scopes)
    if any(scope_interval(scope) == (None, None) for scope in scopes):
        return True
    intervals = sorted(
        interval for scope in scopes
        if (interval := scope_interval(scope)) not in {None, (None, None)}
    )
    cursor = target_interval[0]
    for start, end in intervals:
        if end < cursor:
            continue
        if start > cursor:
            return False
        cursor = max(cursor, end + 1)
        if cursor > target_interval[1]:
            return True
    return False


def validate_audit_result(value: Any, label: str, errors: list[str]) -> dict[str, Any] | None:
    keys = {
        "p0_count", "p1_count", "p2_count", "required_elements_total",
        "required_elements_passed", "decision",
    }
    if not isinstance(value, dict):
        errors.append(f"{label} audit_result must be an object")
        return None
    require_keys(value, keys, f"{label} audit_result", errors)
    reject_unknown_keys(value, keys, f"{label} audit_result", errors)
    for key in keys - {"decision"}:
        item = value.get(key)
        if not isinstance(item, int) or isinstance(item, bool) or item < 0:
            errors.append(f"{label} audit_result.{key} must be a non-negative integer")
    decision = value.get("decision")
    if not isinstance(decision, str) or decision not in AUDIT_DECISIONS:
        errors.append(f"{label} audit_result has invalid decision: {decision}")
    total = value.get("required_elements_total")
    passed = value.get("required_elements_passed")
    if isinstance(total, int) and not isinstance(total, bool) and isinstance(passed, int) and not isinstance(passed, bool):
        if passed > total:
            errors.append(f"{label} audit_result passes more required elements than its total")
    p0 = value.get("p0_count")
    p1 = value.get("p1_count")
    counts_valid = all(
        isinstance(value.get(key), int) and not isinstance(value.get(key), bool) and value[key] >= 0
        for key in keys - {"decision"}
    )
    if counts_valid and decision == "pass" and (p0 != 0 or p1 >= 3 or passed != total):
        errors.append(f"{label} audit_result cannot pass with P0, three or more P1, or missing required elements")
    if counts_valid and decision == "accepted-with-risk" and (p0 != 0 or passed != total):
        errors.append(f"{label} accepted-with-risk cannot override P0 or missing required elements")
    return value


def validate_audit_body(text: str, result: dict[str, Any], label: str, errors: list[str]) -> None:
    marker_counts = {
        severity: len(re.findall(rf"(?mi)^#{{2,6}}\s+\[{severity}\](?:\s|$)", text))
        for severity in ("P0", "P1", "P2")
    }
    for severity, count in marker_counts.items():
        expected = result.get(f"{severity.lower()}_count")
        if count != expected:
            errors.append(f"{label} body has {count} [{severity}] findings, metadata declares {expected}")

    count_patterns = {
        "p0_count": r"(?:P0|致命问题数量)\s*[:：]?\s*(?:\*\*)?(\d+)\s*项?",
        "p1_count": r"(?:P1|高优先级问题数量)\s*[:：]?\s*(?:\*\*)?(\d+)\s*项?",
        "p2_count": r"(?:P2|可优化问题数量)\s*[:：]?\s*(?:\*\*)?(\d+)\s*项?",
    }
    for key, pattern in count_patterns.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if int(match.group(1)) != result.get(key):
                errors.append(
                    f"{label} body count {match.group(0)!r} contradicts metadata {key}={result.get(key)}"
                )

    if result.get("decision") == "pass" and re.search(
        r"阻断下游|必须修订|不得进入(?:正式)?分镜|禁止(?:正式)?分镜|禁止锁定资产", text
    ):
        errors.append(f"{label} body contains blocking language while metadata decision is pass")


def read_embedded_audit_result(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"{label} audit report cannot be read: {exc}")
        return None
    match = re.search(r"<!--\s*ai-drama-audit\s*(\{.*?\})\s*-->", text, re.DOTALL)
    if not match:
        errors.append(f"{label} audit report lacks an ai-drama-audit metadata block")
        return None
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        errors.append(f"{label} audit metadata is invalid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label} audit metadata must be a JSON object")
        return None
    error_count = len(errors)
    validate_audit_body(text, value, label, errors)
    if len(errors) != error_count:
        return None
    return value


def validate_state(
    root: Path, state: dict[str, Any], errors: list[str], episode_count: int | None = None
) -> tuple[set[str], set[str]]:
    version = state.get("schema_version")
    legacy = version == "1.0"
    state_keys = {"schema_version", "project", "stage", "configuration", "sources", "artifacts", "checkpoints"}
    require_keys(state, state_keys, "project-state", errors)
    if legacy:
        reject_unknown_keys(state, state_keys, "project-state", errors)
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"project-state has unsupported schema_version: {version}")
    if not isinstance(state.get("stage"), str) or state.get("stage") not in STAGES:
        errors.append(f"invalid project stage: {state.get('stage')}")
    project = state.get("project", {})
    if not isinstance(project, dict):
        errors.append("project must be an object")
        project = {}
    require_keys(project, {"project_id", "title", "slug", "locale", "scene_ids"}, "project", errors)
    if legacy:
        reject_unknown_keys(
            project,
            {"project_id", "title", "slug", "locale", "format", "target_runtime_ms", "scene_ids"},
            "project",
            errors,
        )
    declared_episode_count = project.get("episode_count")
    if declared_episode_count is not None and not is_positive_int(declared_episode_count):
        errors.append("project episode_count must be a positive integer")
    if episode_count is None and is_positive_int(declared_episode_count):
        episode_count = declared_episode_count
    project_id = project.get("project_id")
    if not isinstance(project_id, str) or not PROJECT_ID_RE.fullmatch(project_id):
        errors.append(f"invalid project_id: {project_id}")
    if not isinstance(project.get("title"), str) or not project.get("title"):
        errors.append("project title must be a non-empty string")
    if not isinstance(project.get("slug"), str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", project.get("slug", "")):
        errors.append("project slug must use lowercase ASCII letters, digits, and hyphens")
    if not isinstance(project.get("locale"), str) or len(project.get("locale", "")) < 2:
        errors.append("project locale must be a string of at least two characters")
    target_runtime = project.get("target_runtime_ms")
    if target_runtime is not None and not is_positive_int(target_runtime):
        errors.append("project target_runtime_ms must be null or a positive integer")
    scene_ids = require_unique_strings(project.get("scene_ids", []), "project scene_ids", errors)
    for scene_id in scene_ids:
        if not SCENE_ID_RE.fullmatch(scene_id):
            errors.append(f"invalid project scene ID: {scene_id}")

    configuration = state.get("configuration", {})
    if not isinstance(configuration, dict):
        errors.append("configuration must be an object")
        configuration = {}
    configuration_keys = {
        "checkpoint_policy", "automatic_authorization", "clip_max_duration_ms", "audio_policy",
        "subtitle_policy", "aspect_ratio", "generator", "editing_policy", "visual_reset_policy",
        "dialogue_rate_chars_per_second",
    }
    require_keys(configuration, configuration_keys, "configuration", errors)
    if legacy:
        reject_unknown_keys(configuration, configuration_keys, "configuration", errors)
    if (not isinstance(configuration.get("checkpoint_policy"), str)
            or configuration.get("checkpoint_policy") not in CHECKPOINT_POLICIES):
        errors.append(f"invalid checkpoint policy: {configuration.get('checkpoint_policy')}")
    if not isinstance(configuration.get("automatic_authorization"), bool):
        errors.append("automatic_authorization must be boolean")
    if not is_positive_int(configuration.get("clip_max_duration_ms")):
        errors.append("clip_max_duration_ms must be a positive integer")
    for key in ["audio_policy", "subtitle_policy", "aspect_ratio", "generator", "editing_policy", "visual_reset_policy"]:
        if not isinstance(configuration.get(key), str):
            errors.append(f"{key} must be a string")
    rate = configuration.get("dialogue_rate_chars_per_second")
    if not isinstance(rate, (int, float)) or isinstance(rate, bool) or not 1 <= rate <= 20:
        errors.append("dialogue_rate_chars_per_second must be between 1 and 20")

    sources = state.get("sources", [])
    artifacts = state.get("artifacts", [])
    checkpoints = state.get("checkpoints", [])
    if not isinstance(sources, list):
        errors.append("sources must be an array")
        sources = []
    if not isinstance(artifacts, list):
        errors.append("artifacts must be an array")
        artifacts = []
    if not isinstance(checkpoints, list):
        errors.append("checkpoints must be an array")
        checkpoints = []
    source_ids = [
        item.get("source_id", "") for item in sources
        if isinstance(item, dict) and isinstance(item.get("source_id"), str)
    ]
    artifact_ids = [
        item.get("artifact_id", "") for item in artifacts
        if isinstance(item, dict) and isinstance(item.get("artifact_id"), str)
    ]
    for value in sorted(duplicates(source_ids)):
        errors.append(f"duplicate source ID: {value}")
    for value in sorted(duplicates(artifact_ids)):
        errors.append(f"duplicate artifact ID: {value}")
    source_set = set(source_ids)
    artifact_set = set(artifact_ids)
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            errors.append(f"source {index} must be an object")
            continue
        require_keys(source, {"source_id", "kind", "path", "availability", "authority", "sha256"}, f"source {source.get('source_id')}", errors)
        if legacy:
            reject_unknown_keys(
                source,
                {"source_id", "kind", "path", "availability", "authority", "sha256"},
                f"source {source.get('source_id')}",
                errors,
            )
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
            errors.append(f"invalid source_id: {source_id}")
        if not isinstance(source.get("kind"), str) or not source.get("kind"):
            errors.append(f"source {source_id} kind must be a non-empty string")
        if not isinstance(source.get("availability"), str) or source.get("availability") not in SOURCE_AVAILABILITY:
            errors.append(f"source {source_id} has invalid availability")
        if not isinstance(source.get("authority"), str) or source.get("authority") not in SOURCE_AUTHORITY:
            errors.append(f"source {source_id} has invalid authority")
        if source.get("availability") == "available":
            path = safe_project_path(root, source.get("path"), f"source {source_id}", errors)
            if path is None:
                continue
            if not path.is_file():
                errors.append(f"available source missing on disk: {source.get('source_id')}")
            else:
                try:
                    actual_hash = hash_file(path)
                except OSError as exc:
                    errors.append(f"source {source_id} cannot be read: {exc}")
                else:
                    if source.get("sha256") != actual_hash:
                        errors.append(f"source hash mismatch: {source.get('source_id')}")
        elif source.get("sha256") is not None:
            errors.append(f"unavailable source must not claim a hash: {source.get('source_id')}")
    confirmed_screenplays: set[str] = set()
    valid_audits: set[str] = set()
    artifacts_by_id = {
        item["artifact_id"]: item for item in artifacts
        if isinstance(item, dict) and isinstance(item.get("artifact_id"), str)
    }
    revisions: dict[str, list[int]] = {}
    dependencies_by_id: dict[str, set[str]] = {}
    audit_results: dict[str, dict[str, Any]] = {}
    for index, artifact in enumerate(artifacts, start=1):
        if not isinstance(artifact, dict):
            errors.append(f"artifact {index} must be an object")
            continue
        label = f"artifact {artifact.get('artifact_id')}"
        require_keys(artifact, {"artifact_id", "type", "revision", "status", "path", "depends_on", "source_refs"}, label, errors)
        if legacy:
            reject_unknown_keys(
                artifact,
                {"artifact_id", "type", "revision", "status", "path", "depends_on", "source_refs", "scope", "sha256", "audit_result", "report_stage"},
                label,
                errors,
            )
        artifact_id = artifact.get("artifact_id")
        if not isinstance(artifact_id, str) or not ARTIFACT_ID_RE.fullmatch(artifact_id):
            errors.append(f"invalid artifact_id: {artifact_id}")
        artifact_type = artifact.get("type")
        if not isinstance(artifact_type, str) or not artifact_type:
            errors.append(f"{label} type must be a non-empty string")
        report_stage = artifact.get("report_stage")
        if artifact_type == "engine-report":
            if not isinstance(report_stage, str) or report_stage not in CHECKPOINT_STAGES:
                errors.append(f"{label} engine-report requires a valid report_stage")
        elif report_stage is not None:
            errors.append(f"{label} report_stage is only valid for engine-report artifacts")
        revision = artifact.get("revision")
        if not is_positive_int(revision):
            errors.append(f"{label} revision must be a positive integer")
        elif isinstance(artifact_type, str):
            revisions.setdefault(artifact_type, []).append(revision)
        status = artifact.get("status")
        if not isinstance(status, str) or status not in ARTIFACT_STATUSES:
            errors.append(f"{label} has invalid status {artifact.get('status')}")
        dependencies = require_unique_strings(artifact.get("depends_on"), f"{label} depends_on", errors)
        source_refs = require_unique_strings(artifact.get("source_refs"), f"{label} source_refs", errors)
        validate_scope(artifact.get("scope"), label, errors)
        if isinstance(artifact_id, str):
            dependencies_by_id[artifact_id] = set(dependencies)
        missing_deps = set(dependencies) - artifact_set
        missing_sources = set(source_refs) - source_set
        if missing_deps:
            errors.append(f"{label} has missing dependencies: {sorted(missing_deps)}")
        if missing_sources:
            errors.append(f"{label} has missing source refs: {sorted(missing_sources)}")
        path_value = artifact.get("path")
        if artifact_type == "locked-assets" and path_value != "asset-manifest.json":
            errors.append(f"{label} must use canonical path asset-manifest.json")
        path = safe_project_path(root, path_value, label, errors)
        if path is not None:
            if not path.is_file():
                errors.append(f"{label} file missing: {artifact.get('path')}")
            else:
                try:
                    actual_hash = hash_file(path)
                except OSError as exc:
                    errors.append(f"{label} cannot be read: {exc}")
                else:
                    if artifact.get("sha256") and artifact["sha256"] != actual_hash:
                        errors.append(f"{label} hash mismatch")
                    elif status == "confirmed" and not artifact.get("sha256"):
                        errors.append(f"{label} confirmed artifact must record sha256")
        artifact_schema = ARTIFACT_SCHEMA_BY_TYPE.get(artifact_type)
        if artifact_schema and path is not None and path.is_file() and status != "invalid":
            artifact_data = read_json(path, errors)
            if artifact_data:
                validate_with_schema(artifact_data, artifact_schema, label, errors)
        if artifact_type == "audit":
            result = artifact.get("audit_result")
            if status == "confirmed" or result is not None:
                validated = validate_audit_result(result, label, errors)
                if path and path.is_file() and path.suffix.lower() == ".json":
                    report = read_json(path, errors)
                    if report:
                        validate_with_schema(report, "audit-report.schema.json", label, errors)
                        findings = report.get("findings", []) if isinstance(report.get("findings"), list) else []
                        required = report.get("required_elements", []) if isinstance(report.get("required_elements"), list) else []
                        derived = {
                            "p0_count": sum(item.get("severity") == "P0" for item in findings if isinstance(item, dict)),
                            "p1_count": sum(item.get("severity") == "P1" for item in findings if isinstance(item, dict)),
                            "p2_count": sum(item.get("severity") == "P2" for item in findings if isinstance(item, dict)),
                            "required_elements_total": len(required),
                            "required_elements_passed": sum(item.get("result") == "pass" for item in required if isinstance(item, dict)),
                            "decision": report.get("decision"),
                        }
                        if validated != derived:
                            errors.append(f"{label} canonical audit content does not match project-state summary")
                        elif isinstance(artifact_id, str):
                            audit_results[artifact_id] = derived
                else:
                    embedded = read_embedded_audit_result(path, label, errors) if path and path.is_file() else None
                    if validated is not None and embedded is not None and embedded != validated:
                        errors.append(f"{label} audit metadata does not match project-state")
                    if (validated is not None and embedded == validated and isinstance(artifact_id, str)):
                        audit_results[artifact_id] = validated
        elif artifact.get("audit_result") is not None:
            errors.append(f"{label} audit_result is only valid for audit artifacts")
        if artifact_type == "screenplay" and status == "confirmed" and isinstance(artifact_id, str):
            confirmed_screenplays.add(artifact["artifact_id"])
    for artifact_type, values in revisions.items():
        if sorted(values) != list(range(1, max(values) + 1)):
            errors.append(f"artifact revisions for {artifact_type} must be unique and continuous from 1")

    dependency_graph = {
        artifact_id: dependencies_by_id.get(artifact_id, set()) & artifact_set
        for artifact_id in artifacts_by_id
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(artifact_id: str) -> None:
        if artifact_id in visiting:
            errors.append(f"artifact dependency cycle includes {artifact_id}")
            return
        if artifact_id in visited:
            return
        visiting.add(artifact_id)
        for dependency in dependency_graph.get(artifact_id, set()):
            visit(dependency)
        visiting.remove(artifact_id)
        visited.add(artifact_id)

    for artifact_id in dependency_graph:
        visit(artifact_id)

    checkpoint_ids: list[str] = []
    checkpoints_by_artifact: dict[str, list[dict[str, Any]]] = {}
    for index, checkpoint in enumerate(checkpoints, start=1):
        if not isinstance(checkpoint, dict):
            errors.append(f"checkpoint {index} must be an object")
            continue
        checkpoint_id = checkpoint.get("checkpoint_id")
        if isinstance(checkpoint_id, str):
            checkpoint_ids.append(checkpoint_id)
        require_keys(checkpoint, {"checkpoint_id", "stage", "decision", "authorization", "sequence", "affects"}, f"checkpoint {checkpoint_id}", errors)
        if legacy:
            reject_unknown_keys(
                checkpoint,
                {"checkpoint_id", "stage", "decision", "authorization", "sequence", "affects"},
                f"checkpoint {checkpoint_id}",
                errors,
            )
        if not isinstance(checkpoint_id, str) or not CHECKPOINT_ID_RE.fullmatch(checkpoint_id):
            errors.append(f"invalid checkpoint_id: {checkpoint_id}")
        stage = checkpoint.get("stage")
        decision = checkpoint.get("decision")
        if not isinstance(stage, str) or stage not in CHECKPOINT_STAGES:
            errors.append(f"checkpoint {checkpoint_id} has invalid stage")
        if not isinstance(decision, str) or decision not in CHECKPOINT_DECISIONS:
            errors.append(f"checkpoint {checkpoint_id} has invalid decision")
        if decision == "automatic" and configuration.get("automatic_authorization") is not True:
            errors.append(f"checkpoint {checkpoint_id} uses automatic decision without project authorization")
        if not isinstance(checkpoint.get("authorization"), str) or not checkpoint.get("authorization"):
            errors.append(f"checkpoint {checkpoint_id} authorization must be non-empty")
        affects = require_unique_strings(checkpoint.get("affects"), f"checkpoint {checkpoint_id} affects", errors)
        missing_affects = set(affects) - artifact_set
        if missing_affects:
            errors.append(f"checkpoint {checkpoint_id} affects unknown artifacts: {sorted(missing_affects)}")
        for affected_id in affects:
            artifact = artifacts_by_id.get(affected_id)
            expected_stage = ARTIFACT_STAGE_BY_TYPE.get(artifact.get("type")) if artifact else None
            if expected_stage and stage != expected_stage:
                errors.append(
                    f"checkpoint {checkpoint_id} stage {stage} does not match {affected_id} stage {expected_stage}"
                )
            checkpoints_by_artifact.setdefault(affected_id, []).append(checkpoint)
    for value in sorted(duplicates(checkpoint_ids)):
        errors.append(f"duplicate checkpoint ID: {value}")
    sequences = [item.get("sequence") for item in checkpoints if isinstance(item, dict)]
    if sequences != list(range(1, len(sequences) + 1)):
        errors.append("checkpoint sequence must be continuous from 1")

    effective_checkpoints: dict[str, dict[str, Any]] = {}
    for artifact_id, rows in checkpoints_by_artifact.items():
        valid_rows = [row for row in rows if is_positive_int(row.get("sequence"))]
        if valid_rows:
            effective_checkpoints[artifact_id] = max(valid_rows, key=lambda row: row["sequence"])

    def is_effectively_approved(artifact_id: str, stage: str | None = None) -> bool:
        checkpoint = effective_checkpoints.get(artifact_id)
        return bool(
            checkpoint
            and checkpoint.get("decision") in {"confirmed", "automatic"}
            and (stage is None or checkpoint.get("stage") == stage)
        )

    for artifact_id, checkpoint in effective_checkpoints.items():
        if (
            artifacts_by_id.get(artifact_id, {}).get("status") == "confirmed"
            and checkpoint.get("decision") in {"revise", "rejected"}
        ):
            errors.append(
                f"confirmed artifact {artifact_id} is revoked by effective checkpoint "
                f"{checkpoint.get('checkpoint_id')} decision {checkpoint.get('decision')}"
            )

    def ancestors(artifact_id: str, trail: set[str] | None = None) -> set[str]:
        active = set() if trail is None else trail
        if artifact_id in active:
            return set()
        active.add(artifact_id)
        result: set[str] = set()
        for dependency in dependency_graph.get(artifact_id, set()):
            result.add(dependency)
            result.update(ancestors(dependency, active))
        active.remove(artifact_id)
        return result

    confirmed_by_type: dict[str, set[str]] = {}
    for artifact_id, artifact in artifacts_by_id.items():
        if artifact.get("status") == "confirmed" and isinstance(artifact.get("type"), str):
            confirmed_by_type.setdefault(artifact["type"], set()).add(artifact_id)

    for artifact_type, stage in CONFIRMATION_STAGE_BY_TYPE.items():
        if legacy and artifact_type not in {"production-brief", "outline-skeleton", "series-outline", "scene-outline", "screenplay"}:
            continue
        current = confirmed_by_type.get(artifact_type, set())
        if artifact_type in PROJECT_SINGLETON_TYPES and len(current) > 1:
            errors.append(f"multiple confirmed {artifact_type} revisions: {sorted(current)}")
        for artifact_id in current:
            if not is_effectively_approved(artifact_id, stage):
                checkpoint = effective_checkpoints.get(artifact_id)
                if checkpoint and checkpoint.get("decision") in {"revise", "rejected"}:
                    errors.append(
                        f"confirmed {artifact_type} {artifact_id} is revoked by effective "
                        f"checkpoint {checkpoint.get('checkpoint_id')} decision {checkpoint.get('decision')}"
                    )
                else:
                    errors.append(f"confirmed {artifact_type} {artifact_id} lacks an approving {stage} checkpoint")

    for artifact_type in RANGED_TYPES:
        current = sorted(confirmed_by_type.get(artifact_type, set()))
        for index, left_id in enumerate(current):
            for right_id in current[index + 1:]:
                left_scope = artifacts_by_id[left_id].get("scope")
                right_scope = artifacts_by_id[right_id].get("scope")
                series_range_exception = artifact_type in {"audit", "shot-plan"} and (
                    scope_interval(left_scope) == (None, None)
                ) != (
                    scope_interval(right_scope) == (None, None)
                )
                if not series_range_exception and scopes_overlap(left_scope, right_scope):
                    errors.append(f"confirmed {artifact_type} scopes overlap: {left_id}, {right_id}")

    confirmed_briefs = confirmed_by_type.get("production-brief", set())
    confirmed_outlines = confirmed_by_type.get("scene-outline", set()) | confirmed_by_type.get("series-outline", set())
    for outline_id in confirmed_outlines:
        if not ancestors(outline_id) & confirmed_briefs:
            errors.append(f"confirmed outline {outline_id} lacks a confirmed production-brief dependency")
    for screenplay_id in confirmed_screenplays:
        upstream = ancestors(screenplay_id)
        if not upstream & confirmed_briefs:
            errors.append(f"confirmed screenplay {screenplay_id} lacks a confirmed production-brief dependency")
        if not upstream & confirmed_outlines:
            errors.append(f"confirmed screenplay {screenplay_id} lacks a confirmed outline dependency")

    for audit_id, result in audit_results.items():
        artifact = artifacts_by_id.get(audit_id, {})
        screenplay_dependencies = {
            dependency for dependency in dependency_graph.get(audit_id, set())
            if artifacts_by_id.get(dependency, {}).get("type") == "screenplay"
        }
        if not screenplay_dependencies:
            errors.append(f"audit {audit_id} must depend on at least one screenplay revision")
        dependency_scopes = [artifacts_by_id[item].get("scope") for item in screenplay_dependencies]
        if screenplay_dependencies and not scopes_cover(dependency_scopes, artifact.get("scope"), episode_count):
            if scope_interval(artifact.get("scope")) == (None, None) and episode_count is not None:
                errors.append(
                    f"audit {audit_id} screenplay dependencies do not cover every episode through {episode_count}"
                )
            else:
                errors.append(f"audit {audit_id} screenplay dependencies do not cover its scope")
        if artifact.get("status") != "confirmed":
            continue
        decision = result.get("decision")
        if decision == "pass":
            if not legacy and not is_effectively_approved(audit_id, "audit"):
                errors.append(f"audit {audit_id} lacks an effective approving audit checkpoint")
            else:
                valid_audits.add(audit_id)
        elif decision == "accepted-with-risk":
            if not legacy and is_effectively_approved(audit_id, "audit"):
                checkpoint = effective_checkpoints.get(audit_id, {})
                if checkpoint.get("authorization_kind") != "risk-acceptance":
                    errors.append(f"audit {audit_id} accepted-with-risk requires risk-acceptance authorization")
                else:
                    valid_audits.add(audit_id)
            elif legacy:
                valid_audits.add(audit_id)
            else:
                errors.append(f"audit {audit_id} accepted-with-risk lacks an effective approving audit checkpoint")

    for screenplay_id in confirmed_screenplays:
        automatic = effective_checkpoints.get(screenplay_id, {}).get("decision") == "automatic"
        if automatic and not any(screenplay_id in dependency_graph.get(audit_id, set()) for audit_id in valid_audits):
            errors.append(f"automatically confirmed screenplay {screenplay_id} lacks a valid covering audit")

    for artifact_id, artifact in artifacts_by_id.items():
        if artifact.get("type") not in FORMAL_DOWNSTREAM_TYPES or artifact.get("status") != "confirmed":
            continue
        upstream = ancestors(artifact_id)
        blocked_ancestors = sorted(
            ancestor_id for ancestor_id in upstream
            if artifacts_by_id.get(ancestor_id, {}).get("status") in {"invalid", "draft"}
        )
        if blocked_ancestors:
            errors.append(
                f"confirmed downstream {artifact_id} ancestor chain crosses invalid or draft artifacts: "
                f"{blocked_ancestors}"
            )
        screenplay_deps = upstream & confirmed_screenplays
        audit_deps = upstream & valid_audits
        artifact_scope = artifact.get("scope")
        if not screenplay_deps:
            errors.append(f"{artifact_id} requires a confirmed screenplay dependency")
        elif not scopes_cover(
            [artifacts_by_id[item].get("scope") for item in screenplay_deps], artifact_scope, episode_count
        ):
            errors.append(f"{artifact_id} confirmed screenplay does not cover its scope")
        if not audit_deps:
            errors.append(f"{artifact_id} requires a valid confirmed audit dependency")
        elif screenplay_deps:
            covered_screenplays = set().union(
                *(dependency_graph.get(audit_id, set()) & screenplay_deps for audit_id in audit_deps)
            )
            if covered_screenplays != screenplay_deps:
                errors.append(f"{artifact_id} audit does not cover its confirmed screenplay")
            if not scopes_cover(
                [artifacts_by_id[item].get("scope") for item in audit_deps], artifact_scope, episode_count
            ):
                errors.append(f"{artifact_id} audit does not cover its scope")
    return confirmed_screenplays, valid_audits


def validate_assets(
    manifest: dict[str, Any], project_id: str, evidence_refs: set[str], errors: list[str]
) -> set[str]:
    version = manifest.get("schema_version")
    legacy = version == "1.0"
    require_keys(manifest, {"schema_version", "project_id", "manifest_version", "assets"}, "asset-manifest", errors)
    if legacy:
        reject_unknown_keys(manifest, {"schema_version", "project_id", "manifest_version", "assets"}, "asset-manifest", errors)
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"asset-manifest has unsupported schema_version: {version}")
    if manifest.get("project_id") != project_id:
        errors.append("asset-manifest project_id does not match project-state")
    if not is_positive_int(manifest.get("manifest_version")):
        errors.append("manifest_version must be a positive integer")
    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        errors.append("assets must be an array")
        assets = []
    ids = [
        item.get("asset_id", "") for item in assets
        if isinstance(item, dict) and isinstance(item.get("asset_id"), str)
    ]
    for value in sorted(duplicates(ids)):
        errors.append(f"duplicate asset ID: {value}")
    for index, asset in enumerate(assets, start=1):
        if not isinstance(asset, dict):
            errors.append(f"asset {index} must be an object")
            continue
        asset_id = asset.get("asset_id", "")
        require_keys(asset, {"asset_id", "type", "name", "aliases", "lock_status", "locked_fields", "evidence", "visual_dna"}, f"asset {asset_id}", errors)
        if legacy:
            reject_unknown_keys(
                asset,
                {"asset_id", "type", "name", "aliases", "lock_status", "locked_fields", "evidence", "visual_dna"},
                f"asset {asset_id}",
                errors,
            )
        if not isinstance(asset_id, str) or not ASSET_RE.fullmatch(asset_id):
            errors.append(f"invalid asset ID: {asset_id}")
        asset_type = asset.get("type")
        if (not isinstance(asset_type, str) or asset_type not in PREFIX_BY_TYPE
                or not isinstance(asset_id, str)
                or not asset_id.startswith(PREFIX_BY_TYPE.get(asset_type, "?") + "-")):
            errors.append(f"asset ID/type mismatch: {asset_id}/{asset_type}")
        if not isinstance(asset.get("name"), str) or not asset.get("name"):
            errors.append(f"asset {asset_id} name must be a non-empty string")
        require_unique_strings(asset.get("aliases"), f"asset {asset_id} aliases", errors)
        locked_fields = require_unique_strings(asset.get("locked_fields"), f"asset {asset_id} locked_fields", errors)
        lock_status = asset.get("lock_status")
        if not isinstance(lock_status, str) or lock_status not in LOCK_STATUSES:
            errors.append(f"invalid lock status for {asset_id}: {asset.get('lock_status')}")
        evidence = asset.get("evidence", [])
        if not isinstance(evidence, list):
            errors.append(f"asset {asset_id} evidence must be an array")
            evidence = []
        confirmed_fields: set[str] = set()
        for evidence_index, item in enumerate(evidence, start=1):
            if not isinstance(item, dict):
                errors.append(f"asset {asset_id} evidence {evidence_index} must be an object")
                continue
            require_keys(item, {"field", "level", "source_ref", "locator"}, f"asset {asset_id} evidence {evidence_index}", errors)
            if legacy:
                reject_unknown_keys(
                    item,
                    {"field", "level", "source_ref", "locator"},
                    f"asset {asset_id} evidence {evidence_index}",
                    errors,
                )
            level = item.get("level")
            if not isinstance(item.get("field"), str) or not item.get("field"):
                errors.append(f"asset {asset_id} evidence {evidence_index} field must be non-empty")
            if not isinstance(level, str) or level not in EVIDENCE_LEVELS:
                errors.append(f"asset {asset_id} evidence {evidence_index} has invalid level")
            elif level == "confirmed" and isinstance(item.get("field"), str):
                confirmed_fields.add(item["field"])
            source_ref = item.get("source_ref")
            base_ref = evidence_base_ref(source_ref)
            if source_ref is not None and (base_ref is None or base_ref not in evidence_refs):
                errors.append(f"asset {asset_id} evidence references ineligible source or artifact: {source_ref}")
            locator = item.get("locator")
            if locator is not None and not isinstance(locator, str):
                errors.append(f"asset {asset_id} evidence {evidence_index} locator must be string or null")
            if level == "confirmed" and (not isinstance(source_ref, str) or not source_ref):
                errors.append(f"asset {asset_id} confirmed evidence {evidence_index} requires source_ref")
            if level == "confirmed" and (not isinstance(locator, str) or not locator):
                errors.append(f"asset {asset_id} confirmed evidence {evidence_index} requires locator")
        missing_locked_evidence = set(locked_fields) - confirmed_fields
        if lock_status in {"locked", "partial"} and missing_locked_evidence:
            errors.append(f"asset {asset_id} locked fields lack confirmed evidence: {sorted(missing_locked_evidence)}")
        if lock_status == "locked" and not locked_fields:
            errors.append(f"locked asset must list locked_fields: {asset_id}")
        if lock_status == "partial" and not locked_fields:
            errors.append(f"partial asset must list locked_fields: {asset_id}")
        if lock_status == "unlocked" and locked_fields:
            errors.append(f"unlocked asset must not list locked_fields: {asset_id}")
        visual_dna = asset.get("visual_dna")
        if not isinstance(visual_dna, dict):
            errors.append(f"asset {asset_id} visual_dna must be an object")
        elif lock_status in {"locked", "partial"} and not visual_dna:
            errors.append(f"asset {asset_id} locked state requires non-empty visual_dna")
        elif version == "2.0" and lock_status in {"locked", "partial"}:
            missing_visual_fields = sorted(set(locked_fields) - set(visual_dna))
            if missing_visual_fields:
                errors.append(
                    f"asset {asset_id} locked fields missing from visual_dna: {missing_visual_fields}"
                )
        variant = re.fullmatch(r"(.+)-V\d{2}", str(asset_id))
        if variant and variant.group(1) not in ids:
            errors.append(f"variant asset lacks base asset: {asset_id}")
    return set(ids)


def validate_ledger(
    ledger: dict[str, Any], project_id: str, asset_ids: set[str], scene_ids: set[str],
    shot_ids: set[str], errors: list[str], shot_index: dict[str, dict[str, Any]] | None = None,
    evidence_refs: set[str] | None = None,
) -> None:
    version = ledger.get("schema_version")
    legacy = version == "1.0"
    shot_index = shot_index or {}
    require_keys(ledger, {"schema_version", "project_id", "ledger_version", "scopes"}, "continuity-ledger", errors)
    if legacy:
        reject_unknown_keys(ledger, {"schema_version", "project_id", "ledger_version", "scopes"}, "continuity-ledger", errors)
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"continuity-ledger has unsupported schema_version: {version}")
    if ledger.get("project_id") != project_id:
        errors.append("continuity-ledger project_id does not match project-state")
    if not is_positive_int(ledger.get("ledger_version")):
        errors.append("ledger_version must be a positive integer")
    scopes = ledger.get("scopes", [])
    if not isinstance(scopes, list):
        errors.append("continuity scopes must be an array")
        scopes = []
    scope_sequences = [item.get("sequence") for item in scopes if isinstance(item, dict)]
    if scope_sequences != list(range(1, len(scope_sequences) + 1)):
        errors.append("continuity scope sequence must be continuous from 1")
    scope_ids: list[str] = []
    event_ids: list[str] = []
    for scope_index, scope in enumerate(scopes, start=1):
        if not isinstance(scope, dict):
            errors.append(f"continuity scope {scope_index} must be an object")
            continue
        scope_id = scope.get("scope_id")
        if isinstance(scope_id, str):
            scope_ids.append(scope_id)
        require_keys(scope, {"scope_id", "sequence", "start_snapshot", "events", "end_snapshot"}, f"continuity scope {scope_id}", errors)
        if legacy:
            reject_unknown_keys(
                scope,
                {"scope_id", "sequence", "start_snapshot", "events", "end_snapshot"},
                f"continuity scope {scope_id}",
                errors,
            )
        if not isinstance(scope_id, str) or not scope_id:
            errors.append(f"continuity scope {scope_index} has invalid scope_id")
        start_snapshot = scope.get("start_snapshot")
        end_snapshot = scope.get("end_snapshot")
        if not isinstance(start_snapshot, dict):
            errors.append(f"continuity scope {scope_id} start_snapshot must be an object")
            start_snapshot = {}
        if not isinstance(end_snapshot, dict):
            errors.append(f"continuity scope {scope_id} end_snapshot must be an object")
            end_snapshot = {}
        expected = copy.deepcopy(start_snapshot)
        for snapshot_name, snapshot in [("start_snapshot", start_snapshot), ("end_snapshot", end_snapshot)]:
            for asset_id, fields in snapshot.items():
                if asset_id not in asset_ids:
                    errors.append(f"continuity {snapshot_name} references unknown asset: {asset_id}")
                if not isinstance(fields, dict):
                    errors.append(f"continuity {snapshot_name} for {asset_id} must be an object")
        events = scope.get("events", [])
        if not isinstance(events, list):
            errors.append(f"continuity scope {scope_id} events must be an array")
            events = []
        last_at_ms: int | None = None
        for event_index, event in enumerate(events, start=1):
            if not isinstance(event, dict):
                errors.append(f"continuity event {scope_id}/{event_index} must be an object")
                continue
            require_keys(event, {"event_id", "asset_id", "field", "before", "after", "evidence_ref"}, f"continuity event {scope_id}/{event_index}", errors)
            if legacy:
                reject_unknown_keys(
                    event,
                    {"event_id", "asset_id", "field", "before", "after", "at_ms", "scene_ref", "shot_ref", "evidence_ref"},
                    f"continuity event {scope_id}/{event_index}",
                    errors,
                )
            event_id = event.get("event_id", "")
            if isinstance(event_id, str):
                event_ids.append(event_id)
            if not isinstance(event_id, str) or not EVENT_ID_RE.fullmatch(event_id):
                errors.append(f"invalid continuity event_id: {event_id}")
            asset_id = event.get("asset_id")
            if not isinstance(asset_id, str) or asset_id not in asset_ids:
                errors.append(f"continuity event references unknown asset: {asset_id}")
            field = event.get("field")
            if not isinstance(field, str) or not field:
                errors.append(f"continuity event {event_id} field must be non-empty")
                continue
            current_fields = expected.get(asset_id) if isinstance(asset_id, str) else None
            if not isinstance(current_fields, dict):
                errors.append(f"continuity chain lacks start value for {asset_id}.{field}")
                if isinstance(asset_id, str):
                    expected[asset_id] = {field: event.get("after")}
            elif field not in current_fields:
                errors.append(f"continuity chain lacks start value for {asset_id}.{field}")
                current_fields[field] = event.get("after")
            else:
                if current_fields[field] != event.get("before"):
                    errors.append(f"continuity chain mismatch for {asset_id}.{field}")
                current_fields[field] = event.get("after")
            at_ms = event.get("at_ms")
            if at_ms is not None and (not isinstance(at_ms, int) or isinstance(at_ms, bool) or at_ms < 0):
                errors.append(f"continuity event {event_id} at_ms must be null or a non-negative integer")
            elif isinstance(at_ms, int) and not isinstance(at_ms, bool):
                if last_at_ms is not None and at_ms < last_at_ms:
                    errors.append(f"continuity event {event_id} at_ms moves backward")
                last_at_ms = at_ms
            scene_ref = event.get("scene_ref")
            if scene_ref is not None and (not isinstance(scene_ref, str) or not SCENE_ID_RE.fullmatch(scene_ref)):
                errors.append(f"continuity event {event_id} has invalid scene_ref")
            elif scene_ref is not None and scene_ref not in scene_ids:
                errors.append(f"continuity event {event_id} references unknown scene: {scene_ref}")
            shot_ref = event.get("shot_ref")
            if shot_ref is not None:
                if not isinstance(shot_ref, str) or not SHOT_ID_RE.fullmatch(shot_ref):
                    errors.append(f"continuity event {event_id} has invalid shot_ref")
                elif shot_ref not in shot_ids:
                    errors.append(f"continuity event {event_id} references unknown shot: {shot_ref}")
                else:
                    shot = shot_index.get(shot_ref, {})
                    if scene_ref is not None and shot.get("scene_id") != scene_ref:
                        errors.append(
                            f"continuity event {event_id} shot {shot_ref} belongs to scene "
                            f"{shot.get('scene_id')}, not {scene_ref}"
                        )
                    if isinstance(at_ms, int) and not isinstance(at_ms, bool):
                        start, end = shot.get("start_ms"), shot.get("end_ms")
                        if isinstance(start, int) and isinstance(end, int) and not start <= at_ms <= end:
                            errors.append(
                                f"continuity event {event_id} at_ms {at_ms} falls outside shot "
                                f"{shot_ref} timing {start}-{end}"
                            )
            evidence_ref = event.get("evidence_ref")
            if not isinstance(evidence_ref, str) or not evidence_ref:
                errors.append(f"continuity event {event_id} evidence_ref must be non-empty")
            elif evidence_refs is not None and evidence_base_ref(evidence_ref) not in evidence_refs:
                errors.append(f"continuity event {event_id} evidence_ref is not eligible: {evidence_ref}")
        if expected != end_snapshot:
            errors.append(f"continuity scope {scope_id} end_snapshot does not match applied events")
    for value in sorted(duplicates(scope_ids)):
        errors.append(f"duplicate continuity scope ID: {value}")
    for value in sorted(duplicates(event_ids)):
        errors.append(f"duplicate continuity event ID: {value}")


def validate_shots(
    root: Path,
    project_id: str,
    asset_ids: set[str],
    project: dict[str, Any],
    configuration: dict[str, Any],
    artifacts: list[dict[str, Any]],
    errors: list[str],
    shot_index: dict[str, dict[str, Any]] | None = None,
) -> set[str]:
    scripts_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(scripts_dir))
    from timeline_cli import validate_plan  # pylint: disable=import-outside-toplevel
    shot_index = shot_index if shot_index is not None else {}
    plan_entries = [
        {**item, "aggregate": item.get("scope") == {"kind": "series"}}
        for item in artifacts
        if isinstance(item, dict) and item.get("type") == "shot-plan" and item.get("status") != "invalid"
    ]
    registered_paths = {item.get("path") for item in plan_entries}
    if (root / "shot-plan.json").exists() and "shot-plan.json" not in registered_paths:
        plan_entries.append({"artifact_id": "aggregate", "path": "shot-plan.json", "scope": {"kind": "series"}, "aggregate": True})
    all_shot_ids: set[str] = set()
    loaded_plans: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for entry in plan_entries:
        relative = entry.get("path")
        label = f"shot-plan {entry.get('artifact_id')}"
        path = safe_project_path(root, relative, label, errors)
        if path is None or not path.is_file():
            continue
        plan = read_json(path, errors)
        if not plan:
            continue
        validate_with_schema(plan, "shot-plan.schema.json", label, errors)
        loaded_plans.append((entry, plan))
        if plan.get("project_id") != project_id:
            errors.append(f"{label} project_id does not match project-state")
        timeline_plan = plan
        if plan.get("schema_version") == "2.0":
            timeline_plan = copy.deepcopy(plan)
            timeline_plan["schema_version"] = "1.0"
            for beat in timeline_plan.get("beats", []) if isinstance(timeline_plan.get("beats"), list) else []:
                if isinstance(beat, dict):
                    for key in ("source_scene_ref", "source_beat_range", "source_beats"):
                        beat.pop(key, None)
            for shot in timeline_plan.get("shots", []) if isinstance(timeline_plan.get("shots"), list) else []:
                if isinstance(shot, dict):
                    shot.pop("prompt_ref", None)
        errors.extend(f"{label}: {error}" for error in validate_plan(timeline_plan))
        if isinstance(entry.get("scope"), dict) and entry.get("scope") != {"kind": "series"} and plan.get("scope") != entry.get("scope"):
            errors.append(f"{label} scope does not match artifact scope")
        target_runtime = project.get("target_runtime_ms")
        if target_runtime is None:
            errors.append(f"project target_runtime_ms is required when {relative} exists")
        elif plan.get("target_runtime_ms") != target_runtime:
            errors.append(f"{label} target_runtime_ms does not match project-state")
        profile = plan.get("profile")
        if isinstance(profile, dict):
            for key in [
                "clip_max_duration_ms", "audio_policy", "subtitle_policy", "aspect_ratio", "generator",
                "editing_policy", "visual_reset_policy", "dialogue_rate_chars_per_second",
            ]:
                if key in configuration and profile.get(key) != configuration.get(key):
                    errors.append(f"{label} profile.{key} does not match project configuration")
        declared_scenes = set(project.get("scene_ids", [])) if isinstance(project.get("scene_ids"), list) else set()
        plan_scenes = plan.get("scenes", [])
        referenced_scenes = {
            item.get("scene_id") for item in plan_scenes
            if isinstance(item, dict) and isinstance(item.get("scene_id"), str)
        } if isinstance(plan_scenes, list) else set()
        if not declared_scenes:
            errors.append(f"project scene_ids are required when {relative} exists")
        elif referenced_scenes - declared_scenes:
            errors.append(f"{label} references undeclared project scenes: {sorted(referenced_scenes - declared_scenes)}")
        shots = plan.get("shots", [])
        if not isinstance(shots, list):
            continue
        for shot in shots:
            if not isinstance(shot, dict):
                continue
            shot_id = shot.get("shot_id")
            if isinstance(shot_id, str):
                if shot_id in all_shot_ids and not entry.get("aggregate"):
                    errors.append(f"duplicate shot ID across shot plans: {shot_id}")
                if not entry.get("aggregate"):
                    all_shot_ids.add(shot_id)
                    shot_index[shot_id] = {
                        "scene_id": shot.get("scene_id"),
                        "beat_id": shot.get("beat_id"),
                        "start_ms": shot.get("start_ms"),
                        "end_ms": shot.get("end_ms"),
                        "generation_group": shot.get("generation_group"),
                        "plan_artifact_id": entry.get("artifact_id"),
                    }
            assets = shot.get("assets", [])
            if not isinstance(assets, list):
                continue
            missing = {item for item in assets if isinstance(item, str)} - asset_ids
            if missing:
                errors.append(f"shot {shot_id} references unknown assets: {sorted(missing)}")

    aggregate_plans = [plan for entry, plan in loaded_plans if entry.get("aggregate")]
    scoped_plans = [
        (entry, plan) for entry, plan in loaded_plans
        if entry.get("status") == "confirmed"
        and not entry.get("aggregate")
        and scope_interval(entry.get("scope")) not in {None, (None, None)}
    ]
    scoped_plans.sort(key=lambda pair: scope_interval(pair[0].get("scope"))[0])
    if aggregate_plans and scoped_plans:
        aggregate = aggregate_plans[0]
        for field in ("scenes", "beats", "shots"):
            expected: list[Any] = []
            if field == "scenes":
                by_id: dict[Any, Any] = {}
                order: list[Any] = []
                for _, plan in scoped_plans:
                    rows = plan.get(field, [])
                    if not isinstance(rows, list):
                        continue
                    for row in rows:
                        key = row.get("scene_id") if isinstance(row, dict) else None
                        if key not in by_id:
                            order.append(key)
                        by_id[key] = row
                expected = [by_id[key] for key in order]
            else:
                for _, plan in scoped_plans:
                    rows = plan.get(field, [])
                    if isinstance(rows, list):
                        expected.extend(rows)
            if aggregate.get(field) != expected:
                errors.append(f"aggregate shot-plan {field} is not a lossless merge of scoped plans")
    return all_shot_ids


def validate_generation_manifests(
    root: Path, artifacts: list[dict[str, Any]], errors: list[str]
) -> None:
    state_probe = read_json(root / "project-state.json", [])
    if not isinstance(state_probe, dict):
        state_probe = {}
    project_id = state_probe.get("project", {}).get("project_id") if isinstance(state_probe.get("project"), dict) else None
    configuration = state_probe.get("configuration", {}) if isinstance(state_probe.get("configuration"), dict) else {}
    by_id = {
        item.get("artifact_id"): item for item in artifacts
        if isinstance(item, dict) and isinstance(item.get("artifact_id"), str)
    }
    for artifact in artifacts:
        if not isinstance(artifact, dict) or artifact.get("type") != "generation-manifest" or artifact.get("status") == "invalid":
            continue
        label = f"generation-manifest {artifact.get('artifact_id')}"
        manifest_path = safe_project_path(root, artifact.get("path"), label, errors)
        if manifest_path is None or not manifest_path.is_file():
            continue
        manifest = read_json(manifest_path, errors)
        if not manifest:
            continue
        if project_id is not None and manifest.get("project_id") != project_id:
            errors.append(f"{label} project_id does not match project-state")
        if artifact.get("scope") is not None and manifest.get("scope") != artifact.get("scope"):
            errors.append(f"{label} scope does not match registered artifact scope")
        profile = configuration
        generator = manifest.get("generator") if isinstance(manifest.get("generator"), dict) else {}
        if generator.get("name") != profile.get("generator") and profile.get("generator") not in {None, "", "unspecified", "minimax-h3"}:
            errors.append(f"{label} generator does not match project configuration")
        groups = manifest.get("groups")
        if not isinstance(groups, list):
            continue
        plan_ids = [
            dependency for dependency in artifact.get("depends_on", [])
            if by_id.get(dependency, {}).get("type") == "shot-plan"
            and by_id.get(dependency, {}).get("status") == "confirmed"
        ]
        if not plan_ids:
            errors.append(f"{label} requires a confirmed shot-plan dependency")
            continue
        expected: dict[str, dict[str, Any]] = {}
        for plan_id in plan_ids:
            plan_artifact = by_id[plan_id]
            plan_path = safe_project_path(root, plan_artifact.get("path"), f"{label} dependency {plan_id}", errors)
            if plan_path is None or not plan_path.is_file():
                continue
            plan = read_json(plan_path, errors)
            beats = {row.get("beat_id"): row for row in plan.get("beats", []) if isinstance(row, dict)}
            for shot in plan.get("shots", []) if isinstance(plan.get("shots"), list) else []:
                if not isinstance(shot, dict) or not isinstance(shot.get("generation_group"), str):
                    continue
                row = expected.setdefault(shot["generation_group"], {
                    "shot_ids": [], "beat_ids": [], "asset_ids": [],
                    "start_ms": shot.get("start_ms"), "end_ms": shot.get("end_ms"),
                })
                row["shot_ids"].append(shot.get("shot_id"))
                if shot.get("beat_id") in beats and shot.get("beat_id") not in row["beat_ids"]:
                    row["beat_ids"].append(shot.get("beat_id"))
                for asset_id in shot.get("assets", []) if isinstance(shot.get("assets"), list) else []:
                    if asset_id not in row["asset_ids"]:
                        row["asset_ids"].append(asset_id)
                row["start_ms"] = min(row["start_ms"], shot.get("start_ms"))
                row["end_ms"] = max(row["end_ms"], shot.get("end_ms"))
        actual_ids = [row.get("generation_group") for row in groups if isinstance(row, dict)]
        if set(actual_ids) != set(expected):
            errors.append(f"{label} groups do not match dependent shot-plan generation groups")
        if len(actual_ids) != len(set(actual_ids)):
            errors.append(f"{label} contains duplicate generation groups")
        manifest_parent = Path(str(artifact.get("path"))).parent
        for row in groups:
            if not isinstance(row, dict):
                continue
            group = row.get("generation_group")
            wanted = expected.get(group)
            if wanted is not None:
                for field in ("shot_ids", "beat_ids", "asset_ids", "start_ms", "end_ms"):
                    if row.get(field) != wanted[field]:
                        errors.append(f"{label} group {group} {field} does not match dependent shot-plan")
            prompt_value = row.get("prompt")
            prompt_relative = (manifest_parent / prompt_value).as_posix() if isinstance(prompt_value, str) else prompt_value
            prompt_path = safe_project_path(root, prompt_relative, f"{label} group {group} prompt", errors)
            if prompt_path is None:
                continue
            if not prompt_path.is_file():
                errors.append(f"{label} group {group} prompt file missing: {prompt_relative}")
                continue
            try:
                prompt_hash = hash_file(prompt_path)
            except OSError as exc:
                errors.append(f"{label} group {group} prompt cannot be read: {exc}")
            else:
                if row.get("prompt_sha256") != prompt_hash:
                    errors.append(f"{label} group {group} prompt hash mismatch")


def validate_media_manifests(root: Path, artifacts: list[dict[str, Any]], errors: list[str]) -> None:
    for artifact in artifacts:
        if not isinstance(artifact, dict) or artifact.get("status") == "invalid":
            continue
        artifact_type = artifact.get("type")
        if artifact_type not in {"delivery-manifest", "visual-delivery"}:
            continue
        label = f"{artifact_type} {artifact.get('artifact_id')}"
        path = safe_project_path(root, artifact.get("path"), label, errors)
        if path is None or not path.is_file():
            continue
        data = read_json(path, errors)
        if not data:
            continue
        state_project_id = None
        try:
            state_probe = read_json(root / "project-state.json", [])
            state_project_id = state_probe.get("project", {}).get("project_id")
        except Exception:
            pass
        rows: list[dict[str, Any]] = []
        if artifact_type == "delivery-manifest":
            if state_project_id is not None and data.get("project_id") != state_project_id:
                errors.append(f"{label} project_id does not match project-state")
            if artifact.get("scope") is not None and data.get("scope") != artifact.get("scope"):
                errors.append(f"{label} scope does not match registered artifact scope")
            rows.extend(item for item in data.get("artifacts", []) if isinstance(item, dict))
            rows.extend(item for item in data.get("storyboard_images", []) if isinstance(item, dict))
            if data.get("status") == "complete":
                if not data.get("artifacts") or not data.get("storyboard_images"):
                    errors.append(f"{label} complete status requires delivered artifacts and storyboard images")
                for item in data.get("artifacts", []):
                    if isinstance(item, dict) and (
                        item.get("status") != "delivered" or item.get("qc_status") not in {"pass", "not-applicable"}
                    ):
                        errors.append(f"{label} complete status includes an undelivered or failed-QC artifact")
                for item in data.get("storyboard_images", []):
                    if isinstance(item, dict) and item.get("qc_status") != "pass":
                        errors.append(f"{label} complete status includes a failed-QC storyboard image")
                if data.get("known_gaps"):
                    errors.append(f"{label} complete status cannot contain known gaps")
        else:
            rows.extend(item for item in data.get("outputs", []) if isinstance(item, dict))
            if data.get("status") in {"generated", "edited"} and not rows:
                errors.append(f"{label} generated or edited status requires outputs")
            for item in rows:
                qc = item.get("qc", {})
                if not all(qc.get(key) is True for key in ("decoded", "nonblank", "aspect_ratio_matches")):
                    errors.append(f"{label} output {item.get('path')} failed deterministic visual QC")
                if qc.get("visual_review") != "pass":
                    errors.append(f"{label} output {item.get('path')} lacks passing visual review")
                if data.get("specification", {}).get("projection") == "equirectangular" and qc.get("vr_review") != "pass":
                    errors.append(f"{label} panorama output {item.get('path')} lacks passing VR review")
        manifest_parent = Path(str(artifact.get("path"))).parent
        for item in rows:
            value = item.get("path")
            relative = (manifest_parent / value).as_posix() if isinstance(value, str) else value
            media_path = safe_project_path(root, relative, f"{label} media", errors)
            if media_path is None:
                continue
            if not media_path.is_file():
                errors.append(f"{label} media file missing: {relative}")
                continue
            try:
                digest = hash_file(media_path)
            except OSError as exc:
                errors.append(f"{label} media file cannot be read: {exc}")
            else:
                if digest != item.get("sha256"):
                    errors.append(f"{label} media hash mismatch: {relative}")


def validate_short_drama_engine(
    root: Path, state: dict[str, Any], errors: list[str], asset_ids: set[str] | None = None,
    shot_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    asset_ids = asset_ids or set()
    shot_index = shot_index or {}
    path = root / "short-drama-engine.json"
    if not path.exists():
        return {}
    engine = read_json(path, errors)
    if not engine:
        return {}
    validate_with_schema(engine, "short-drama-engine.schema.json", "short-drama-engine", errors)
    version = engine.get("schema_version")
    required = {"schema_version", "project_id", "engine_snapshot", "profile", "attachment", "mappings"}
    require_keys(engine, required, "short-drama-engine", errors)
    if version == "1.0":
        reject_unknown_keys(engine, required | {"aggregate", "completion"}, "short-drama-engine", errors)
    project = state.get("project", {}) if isinstance(state.get("project"), dict) else {}
    if version not in SUPPORTED_SCHEMA_VERSIONS or engine.get("project_id") != project.get("project_id"):
        errors.append("short-drama-engine schema_version/project_id mismatch")
    if version == "2.0":
        snapshot = engine.get("engine_snapshot", {}) if isinstance(engine.get("engine_snapshot"), dict) else {}
        snapshot_manifest = ROOT / "vendor" / "kernels" / "snapshot-manifest.json"
        runtime_root = ROOT / "engine" / "runtime"
        if not snapshot_manifest.is_file():
            errors.append("short-drama-engine pinned snapshot manifest is missing")
        else:
            try:
                manifest_hash = hash_file(snapshot_manifest)
                manifest = json.loads(snapshot_manifest.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(f"short-drama-engine pinned snapshot manifest cannot be read: {exc}")
            else:
                if snapshot.get("manifest_sha256") != manifest_hash:
                    errors.append("short-drama-engine manifest_sha256 does not match pinned snapshot")
                expected_runtime = snapshot.get("runtime_files")
                if expected_runtime != manifest.get("runtime_files"):
                    errors.append("short-drama-engine runtime_files do not match pinned snapshot manifest")
                if isinstance(expected_runtime, dict):
                    actual_runtime = {
                        item.relative_to(runtime_root).as_posix(): hash_file(item)
                        for item in runtime_root.rglob("*") if item.is_file()
                    }
                    if expected_runtime != actual_runtime:
                        errors.append("short-drama-engine runtime snapshot files or hashes have drifted")
    profile = engine.get("profile", {})
    if not isinstance(profile, dict):
        errors.append("short-drama-engine profile must be an object")
        return engine
    count, duration = profile.get("episode_count"), profile.get("episode_duration_ms")
    if not is_positive_int(count) or not is_positive_int(duration):
        errors.append("short-drama-engine requires positive episode_count and episode_duration_ms")
    elif project.get("target_runtime_ms") != count * duration:
        errors.append("short-drama-engine runtime does not match project target")
    if profile.get("style") not in {"realistic", "hand-painted-cel"}:
        errors.append("short-drama-engine has unsafe or unsupported style")
    if profile.get("generator") != "minimax-h3":
        errors.append("short-drama-engine generator must be minimax-h3")
    mappings = engine.get("mappings", {})
    if not isinstance(mappings, dict):
        errors.append("short-drama-engine mappings must be an object")
        return engine
    for key in ("characters", "scenes", "props", "scene_occurrences", "storyboard"):
        rows = mappings.get(key)
        if not isinstance(rows, list):
            errors.append(f"short-drama-engine mappings.{key} must be an array")
            continue
        upstream = [item.get("upstream_id", item.get("key")) for item in rows if isinstance(item, dict)]
        forging = [item.get("forging_id", item.get("shot_id")) for item in rows if isinstance(item, dict)]
        upstream_markers = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in upstream]
        forging_markers = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in forging]
        if len(upstream_markers) != len(set(upstream_markers)):
            errors.append(f"short-drama-engine mappings.{key} has duplicate upstream keys")
        if len(forging_markers) != len(set(forging_markers)):
            errors.append(f"short-drama-engine mappings.{key} reuses Forging IDs")

    active_assets: set[str] = set()
    for key in ("characters", "scenes", "props"):
        rows = mappings.get(key, [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or row.get("status") == "retired":
                continue
            forging_id = row.get("forging_id")
            if not isinstance(forging_id, str) or forging_id not in asset_ids:
                errors.append(f"short-drama-engine mappings.{key} references unknown manifest asset: {forging_id}")
            else:
                active_assets.add(forging_id)

    project_scenes = set(project.get("scene_ids", [])) if isinstance(project.get("scene_ids"), list) else set()
    for row in mappings.get("scene_occurrences", []) if isinstance(mappings.get("scene_occurrences"), list) else []:
        if not isinstance(row, dict) or row.get("status") == "retired":
            continue
        scene_asset = row.get("scene_asset_id")
        occurrence = row.get("forging_id")
        if scene_asset not in asset_ids:
            errors.append(f"short-drama-engine scene occurrence references unknown scene asset: {scene_asset}")
        if occurrence not in project_scenes:
            errors.append(f"short-drama-engine scene occurrence references undeclared project scene: {occurrence}")

    for row in mappings.get("storyboard", []) if isinstance(mappings.get("storyboard"), list) else []:
        if not isinstance(row, dict) or row.get("status") == "retired":
            continue
        shot_id = row.get("shot_id")
        shot = shot_index.get(shot_id)
        if shot is None:
            errors.append(f"short-drama-engine storyboard mapping references unknown shot: {shot_id}")
            continue
        if row.get("beat_id") != shot.get("beat_id"):
            errors.append(f"short-drama-engine storyboard mapping beat does not match shot {shot_id}")
        if row.get("generation_group") != shot.get("generation_group"):
            errors.append(f"short-drama-engine storyboard mapping generation_group does not match shot {shot_id}")
    aggregate_record = engine.get("aggregate")
    if isinstance(aggregate_record, dict) and aggregate_record.get("projection_path") == "shot-plan.json":
        projection_path = root / "shot-plan.json"
        if not projection_path.is_file():
            errors.append("short-drama-engine aggregate references missing shot-plan.json projection")
        else:
            try:
                projection_hash = hash_file(projection_path)
            except OSError as exc:
                errors.append(f"short-drama-engine aggregate projection cannot be read: {exc}")
            else:
                if aggregate_record.get("sha256") != projection_hash:
                    errors.append("short-drama-engine aggregate projection does not match the immutable snapshot")
    return engine


def validate_short_drama_completion(
    root: Path, state: dict[str, Any], manifest: dict[str, Any], errors: list[str],
    engine: dict[str, Any] | None = None,
) -> None:
    if state.get("stage") != "complete" or not (root / "short-drama-engine.json").exists():
        return
    engine = engine or {}
    completion = engine.get("completion")
    if not isinstance(completion, dict) or not isinstance(completion.get("authorization"), str) or not completion.get("authorization"):
        errors.append("complete short-drama project requires an engine completion authorization record")
    aggregate_record = engine.get("aggregate")
    aggregate_projection = aggregate_record.get("projection_path", aggregate_record.get("shot_plan_path")) if isinstance(aggregate_record, dict) else None
    if not isinstance(aggregate_record, dict) or aggregate_projection != "shot-plan.json" or aggregate_record.get("scope") != {"kind": "series"}:
        errors.append("complete short-drama project requires an engine aggregate record for shot-plan.json")
    artifacts = state.get("artifacts", []) if isinstance(state.get("artifacts"), list) else []
    aggregate_id = aggregate_record.get("artifact_id") if isinstance(aggregate_record, dict) else None
    aggregate_snapshot = aggregate_record.get("shot_plan_path") if isinstance(aggregate_record, dict) else None
    aggregate = next((
        item for item in artifacts
        if isinstance(item, dict) and item.get("type") == "shot-plan"
        and item.get("status") == "confirmed" and item.get("scope") == {"kind": "series"}
        and item.get("artifact_id") == aggregate_id and item.get("path") == aggregate_snapshot
    ), None)
    if aggregate is None:
        errors.append("complete short-drama project requires a confirmed aggregate shot-plan artifact")
        return
    aggregate_dependencies = set(aggregate.get("depends_on", [])) if isinstance(aggregate.get("depends_on"), list) else set()
    series_audit = next((
        item for item in artifacts
        if isinstance(item, dict) and item.get("type") == "audit"
        and item.get("status") == "confirmed" and item.get("scope") == {"kind": "series"}
        and isinstance(item.get("audit_result"), dict)
        and item["audit_result"].get("decision") in {"pass", "accepted-with-risk"}
        and item.get("artifact_id") in aggregate_dependencies
    ), None)
    if series_audit is None:
        errors.append("complete short-drama project requires a valid series audit used by the aggregate")
    locked_assets_artifact = next((
        item for item in artifacts
        if isinstance(item, dict) and item.get("type") == "locked-assets"
        and item.get("status") == "confirmed" and item.get("path") == "asset-manifest.json"
    ), None)
    if locked_assets_artifact is None:
        errors.append("complete short-drama project requires a confirmed locked-assets artifact")

    configuration = state.get("configuration", {}) if isinstance(state.get("configuration"), dict) else {}
    if configuration.get("delivery_required") is True:
        delivery = next((
            item for item in artifacts
            if isinstance(item, dict) and item.get("type") == "delivery-manifest"
            and item.get("status") == "confirmed" and item.get("scope") == {"kind": "series"}
        ), None)
        if delivery is None:
            errors.append("complete project with delivery_required=true requires a confirmed series delivery-manifest")
        else:
            delivery_path = safe_project_path(root, delivery.get("path"), "complete delivery-manifest", errors)
            delivery_data = read_json(delivery_path, errors) if delivery_path and delivery_path.is_file() else {}
            if delivery_data.get("status") != "complete":
                errors.append("complete project delivery-manifest status must be complete")
    if engine.get("schema_version") == "2.0" and isinstance(completion, dict):
        expected_records = {
            "aggregate": aggregate,
            "series_audit": series_audit,
            "locked_assets": locked_assets_artifact,
        }
        for prefix, artifact in expected_records.items():
            if artifact is None:
                continue
            expected_id = artifact.get("artifact_id")
            expected_hash = artifact.get("sha256")
            if completion.get(f"{prefix}_artifact_id") != expected_id:
                errors.append(f"complete record {prefix}_artifact_id does not match project-state")
            if completion.get(f"{prefix}_sha256") != expected_hash:
                errors.append(f"complete record {prefix}_sha256 does not match project-state")
        if isinstance(aggregate_record, dict):
            if aggregate_record.get("artifact_id") != aggregate.get("artifact_id"):
                errors.append("engine aggregate artifact_id does not match project-state")
            if aggregate_record.get("sha256") != aggregate.get("sha256"):
                errors.append("engine aggregate sha256 does not match project-state")
    aggregate_path = root / "shot-plan.json"
    aggregate_data = read_json(aggregate_path, errors) if aggregate_path.is_file() else {}
    if aggregate is not None and aggregate_path.is_file():
        try:
            projection_hash = hash_file(aggregate_path)
        except OSError as exc:
            errors.append(f"aggregate projection cannot be read: {exc}")
        else:
            if projection_hash != aggregate.get("sha256"):
                errors.append("aggregate projection does not match the immutable aggregate snapshot")
    required_assets = {
        asset_id for shot in aggregate_data.get("shots", []) if isinstance(shot, dict)
        for asset_id in shot.get("assets", []) if isinstance(asset_id, str)
    }
    rows = manifest.get("assets", []) if isinstance(manifest.get("assets"), list) else []
    locked = {
        item.get("asset_id") for item in rows
        if isinstance(item, dict) and item.get("lock_status") == "locked"
    }
    missing = sorted(required_assets - locked)
    if missing:
        errors.append(f"complete short-drama project has unlocked required assets: {missing}")


def validate_canonical_ref(
    root: Path, state: dict[str, Any], errors: list[str], key: str, ref: dict[str, Any], projection_name: str,
) -> None:
    """Verify an engine canonical_state ref against its snapshot artifact and projection."""
    artifacts = {
        item.get("artifact_id"): item for item in state.get("artifacts", [])
        if isinstance(item, dict) and isinstance(item.get("artifact_id"), str)
    }
    artifact_id = ref.get("artifact_id")
    artifact = artifacts.get(artifact_id)
    if artifact is None or artifact.get("type") != key or artifact.get("status") != "confirmed":
        errors.append(f"{key} canonical_state references an unknown or unconfirmed snapshot artifact")
        return
    projection_path = root / projection_name
    projection_hash = hash_file(projection_path) if projection_path.is_file() else None
    snapshot_path = ref.get("snapshot_path")
    snapshot_hash = None
    if isinstance(snapshot_path, str):
        snapshot_file = root / snapshot_path
        snapshot_hash = hash_file(snapshot_file) if snapshot_file.is_file() else None
        if artifact.get("path") != snapshot_path:
            errors.append(f"{key} snapshot artifact path does not match canonical_state")
    if ref.get("projection_path") != projection_name:
        errors.append(f"{key} canonical_state projection_path is invalid")
    if ref.get("sha256") != projection_hash or (snapshot_path is not None and ref.get("sha256") != snapshot_hash):
        errors.append(f"{key} canonical_state sha256 does not match projection or snapshot")
    if ref.get("sha256") != artifact.get("sha256"):
        errors.append(f"{key} canonical_state sha256 does not match snapshot artifact")
    if snapshot_hash is not None and snapshot_hash != projection_hash:
        errors.append(f"{key} projection and snapshot are not byte-identical")
    if ref.get("revision") != artifact.get("revision"):
        errors.append(f"{key} canonical_state revision does not match snapshot artifact")


def replay_hook_ledger(root: Path, state: dict[str, Any], errors: list[str]) -> None:
    """Deterministically re-derive the hook ledger and compare it to the projection.

    Only runs when a confirmed series-outline and at least one confirmed
    episode-scoped screenplay exist, so a missing or legacy project is not
    spuriously rejected.
    """
    outline = next(
        (item for item in state.get("artifacts", []) if isinstance(item, dict)
         and item.get("type") == "series-outline" and item.get("status") == "confirmed"),
        None,
    )
    screenplays = sorted(
        (item for item in state.get("artifacts", []) if isinstance(item, dict)
         and item.get("type") == "screenplay" and item.get("status") == "confirmed"
         and isinstance(item.get("scope"), dict) and item["scope"].get("kind") == "episodes"),
        key=lambda item: item["scope"]["start"],
    )
    if outline is None or not screenplays:
        return
    outline_path = root / outline["path"]
    if not outline_path.is_file():
        return
    outline_data = read_json(outline_path, errors)
    if errors:
        return
    project_id = state.get("project", {}).get("project_id")
    engine = read_json(root / "short-drama-engine.json", errors) if (root / "short-drama-engine.json").is_file() else {}
    episode_count = engine.get("profile", {}).get("episode_count") if isinstance(engine, dict) else None
    if not is_positive_int(episode_count):
        episode_count = max((item["scope"]["end"] for item in screenplays), default=1)
    scripts_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(scripts_dir))
    from hook_ledger import seed_hook_ledger, derive_hook_ledger  # pylint: disable=import-outside-toplevel
    ledger = seed_hook_ledger(outline_data, project_id, episode_count)
    for screenplay in screenplays:
        screenplay_path = root / screenplay["path"]
        if not screenplay_path.is_file():
            continue
        script = read_json(screenplay_path, errors)
        if errors:
            return
        ledger, derivation_errors = derive_hook_ledger(ledger, script)
        if derivation_errors:
            errors.append(
                f"hook-ledger replay derivation failed for {screenplay['artifact_id']}: "
                + "; ".join(derivation_errors)
            )
            return
    projection_path = root / "hook-ledger.json"
    if projection_path.is_file():
        current = read_json(projection_path, errors)
        if errors:
            return
        if current != ledger:
            errors.append("hook-ledger does not match deterministic replay from confirmed outline and screenplays")


def validate_hook_ledger(root: Path, state: dict[str, Any], errors: list[str]) -> None:
    path = root / "hook-ledger.json"
    engine = read_json(root / "short-drama-engine.json", errors) if (root / "short-drama-engine.json").is_file() else {}
    ref = engine.get("canonical_state", {}).get("hook_ledger") if isinstance(engine, dict) else None
    if state.get("schema_version") == "2.0" and engine.get("attachment", {}).get("status") == "active" and not path.is_file():
        errors.append("active short-drama project requires hook-ledger.json")
        return
    if not path.is_file():
        return
    ledger = read_json(path, errors)
    if errors:
        return
    validate_with_schema(ledger, "hook-ledger.schema.json", "hook-ledger", errors)
    if isinstance(ref, dict):
        validate_canonical_ref(root, state, errors, "hook_ledger", ref, "hook-ledger.json")
    elif state.get("schema_version") == "2.0" and engine.get("attachment", {}).get("status") == "active":
        errors.append("active short-drama project lacks hook-ledger canonical_state binding")
    project = state.get("project") if isinstance(state.get("project"), dict) else {}
    if ledger.get("project_id") != project.get("project_id", ""):
        errors.append("hook-ledger project_id does not match project-state")
    episode_count = engine.get("profile", {}).get("episode_count") if isinstance(engine, dict) else None
    hooks = ledger.get("hooks") if isinstance(ledger.get("hooks"), list) else []
    ids = [hook.get("hook_id") for hook in hooks if isinstance(hook, dict)]
    if len(ids) != len(set(ids)):
        errors.append("hook-ledger has duplicate hook ids")
    for hook in hooks:
        if not isinstance(hook, dict):
            continue
        label = hook.get("hook_id", "?")
        planted = hook.get("planted_episode")
        advanced = hook.get("last_advanced_episode")
        resolved = hook.get("resolved_episode")
        target = hook.get("target_payoff_episode")
        if is_positive_int(episode_count):
            for field, value in (("planted_episode", planted), ("last_advanced_episode", advanced), ("resolved_episode", resolved), ("target_payoff_episode", target)):
                if is_positive_int(value) and value > episode_count:
                    errors.append(f"hook {label} {field} exceeds episode_count {episode_count}")
        if isinstance(advanced, int) and isinstance(planted, int) and advanced < planted:
            errors.append(f"hook {label} last_advanced_episode precedes planted_episode")
        if hook.get("status") == "resolved" and not isinstance(resolved, int):
            errors.append(f"hook {label} is resolved but has no resolved_episode")
        if isinstance(resolved, int) and hook.get("status") != "resolved":
            errors.append(f"hook {label} has resolved_episode but is not resolved")
        history = hook.get("evidence_history") if isinstance(hook.get("evidence_history"), list) else []
        history_episodes = [entry.get("episode") for entry in history if isinstance(entry, dict)]
        if history_episodes != sorted(history_episodes):
            errors.append(f"hook {label} evidence_history is not ordered by episode")
    replay_hook_ledger(root, state, errors)


def replay_canon(root: Path, state: dict[str, Any], errors: list[str]) -> None:
    """Replay the canon snapshot chain and compare it to the projection.

    Each canon snapshot records its transformation source through `depends_on`:
    a `canon-register` artifact for a register step, a `screenplay` artifact for
    an evolve step, and otherwise a refresh step. Walking those immutable inputs
    in revision order reproduces the canonical bytes deterministically.
    """
    by_id = {
        item.get("artifact_id"): item for item in state.get("artifacts", [])
        if isinstance(item, dict) and isinstance(item.get("artifact_id"), str)
    }
    snapshots = sorted(
        (item for item in state.get("artifacts", []) if isinstance(item, dict)
         and item.get("type") == "canon" and item.get("status") in {"confirmed", "superseded"}),
        key=lambda item: item.get("revision", 0),
    )
    if not snapshots:
        return
    project_id = state.get("project", {}).get("project_id")
    current = {"schema_version": "1.0", "project_id": project_id, "canon_version": 0, "claims": [], "candidates": []}
    scripts_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(scripts_dir))
    from canon import merge_registered_canon, refresh_canon, derive_canon_updates  # pylint: disable=import-outside-toplevel
    for snapshot in snapshots:
        snapshot_path = root / snapshot["path"]
        if not snapshot_path.is_file():
            return
        snapshot_data = read_json(snapshot_path, errors)
        if errors:
            return
        op = "refresh"
        input_artifact = None
        for dependency in snapshot.get("depends_on", []):
            artifact = by_id.get(dependency)
            if artifact is None:
                continue
            if artifact.get("type") == "canon-register":
                op = "register"
                input_artifact = artifact
            elif artifact.get("type") == "screenplay":
                op = "evolve"
                input_artifact = artifact
        if op == "register":
            if input_artifact is None:
                errors.append(f"canon snapshot {snapshot['artifact_id']} register step lacks a canon-register input")
                return
            incoming = read_json(root / input_artifact["path"], errors)
            if errors:
                return
            next_canon, merge_errors = merge_registered_canon(current, incoming)
            if merge_errors:
                errors.append(f"canon replay register failed at {snapshot['artifact_id']}: " + "; ".join(merge_errors))
                return
        elif op == "evolve":
            if input_artifact is None:
                errors.append(f"canon snapshot {snapshot['artifact_id']} evolve step lacks a screenplay input")
                return
            script = read_json(root / input_artifact["path"], errors)
            if errors:
                return
            next_canon = derive_canon_updates(current, script)
        else:
            next_canon = refresh_canon(current)
        if next_canon != snapshot_data:
            errors.append(f"canon snapshot {snapshot['artifact_id']} does not match deterministic replay")
        current = next_canon
    projection_path = root / "canon.json"
    if projection_path.is_file():
        projection = read_json(projection_path, errors)
        if errors:
            return
        if projection != current:
            errors.append("canon projection does not match deterministic replay")


def validate_canon(root: Path, state: dict[str, Any], errors: list[str]) -> None:
    path = root / "canon.json"
    engine = read_json(root / "short-drama-engine.json", errors) if (root / "short-drama-engine.json").is_file() else {}
    ref = engine.get("canonical_state", {}).get("canon") if isinstance(engine, dict) else None
    requires_canon = state.get("schema_version") == "2.0" and engine.get("attachment", {}).get("status") == "active" and any(
        item.get("type") == "screenplay" and item.get("status") == "confirmed" for item in state.get("artifacts", []) if isinstance(item, dict)
    )
    if requires_canon and not path.is_file():
        errors.append("confirmed short-drama screenplay requires canon.json")
        return
    if not path.is_file():
        return
    canon = read_json(path, errors)
    if errors:
        return
    validate_with_schema(canon, "canon.schema.json", "canon", errors)
    if isinstance(ref, dict):
        validate_canonical_ref(root, state, errors, "canon", ref, "canon.json")
    elif requires_canon:
        errors.append("confirmed short-drama screenplay lacks canon canonical_state binding")
    project = state.get("project") if isinstance(state.get("project"), dict) else {}
    if canon.get("project_id") != project.get("project_id", ""):
        errors.append("canon project_id does not match project-state")
    episode_count = engine.get("profile", {}).get("episode_count") if isinstance(engine, dict) else None
    claims = canon.get("claims") if isinstance(canon.get("claims"), list) else []
    ids = [claim.get("claim_id") for claim in claims if isinstance(claim, dict)]
    if len(ids) != len(set(ids)):
        errors.append("canon has duplicate claim ids")
    if is_positive_int(episode_count):
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            label = claim.get("claim_id", "?")
            reader_known_from = claim.get("visibility", {}).get("reader_known_from") if isinstance(claim.get("visibility"), dict) else None
            status_episode = claim.get("status_updated_at_episode")
            for field, value in (("reader_known_from", reader_known_from), ("status_updated_at_episode", status_episode)):
                if is_positive_int(value) and value > episode_count:
                    errors.append(f"canon {label} {field} exceeds episode_count {episode_count}")
        for candidate in canon.get("candidates", []) if isinstance(canon.get("candidates"), list) else []:
            if isinstance(candidate, dict) and is_positive_int(candidate.get("source_episode")) and candidate.get("source_episode") > episode_count:
                errors.append(f"canon candidate source_episode exceeds episode_count {episode_count}")
    replay_canon(root, state, errors)


def validate_project(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        root = root.resolve()
    except OSError as exc:
        return [f"project directory cannot be resolved: {exc}"]
    if not root.is_dir():
        return [f"project directory does not exist: {root}"]
    state = read_json(root / "project-state.json", errors)
    assets = read_json(root / "asset-manifest.json", errors)
    ledger = read_json(root / "continuity-ledger.json", errors)
    if errors:
        return errors
    validate_with_schema(state, "project-state.schema.json", "project-state", errors)
    validate_with_schema(assets, "asset-manifest.schema.json", "asset-manifest", errors)
    validate_with_schema(ledger, "continuity-ledger.schema.json", "continuity-ledger", errors)
    validate_hook_ledger(root, state, errors)
    validate_canon(root, state, errors)
    project = state.get("project") if isinstance(state.get("project"), dict) else {}
    configuration = state.get("configuration") if isinstance(state.get("configuration"), dict) else {}
    project_id = project.get("project_id", "")
    sources = state.get("sources") if isinstance(state.get("sources"), list) else []
    artifacts = state.get("artifacts") if isinstance(state.get("artifacts"), list) else []
    engine_path = root / "short-drama-engine.json"
    engine_probe = read_json(engine_path, errors) if engine_path.is_file() else {}
    profile = engine_probe.get("profile") if isinstance(engine_probe.get("profile"), dict) else {}
    episode_count = profile.get("episode_count") if is_positive_int(profile.get("episode_count")) else None
    validate_state(root, state, errors, episode_count)
    eligible_source_ids = {
        item.get("source_id") for item in sources
        if isinstance(item, dict) and isinstance(item.get("source_id"), str)
        and item.get("availability") == "available"
        and item.get("authority") in {"canonical", "constraint", "reference"}
    }
    eligible_artifact_ids = {
        item.get("artifact_id") for item in artifacts
        if isinstance(item, dict) and isinstance(item.get("artifact_id"), str)
        and item.get("status") == "confirmed"
    }
    evidence_refs = eligible_source_ids | eligible_artifact_ids
    asset_ids = validate_assets(assets, project_id, evidence_refs, errors)
    asset_rows = assets.get("assets", []) if isinstance(assets.get("assets"), list) else []
    has_locked_assets = any(
        isinstance(item, dict) and item.get("lock_status") == "locked" for item in asset_rows
    )
    confirmed_locked_manifest = any(
        isinstance(item, dict) and item.get("type") == "locked-assets"
        and item.get("status") == "confirmed" and item.get("path") == "asset-manifest.json"
        for item in artifacts
    )
    if has_locked_assets and not confirmed_locked_manifest:
        errors.append("locked assets require a confirmed locked-assets artifact for asset-manifest.json")
    shot_index: dict[str, dict[str, Any]] = {}
    shot_ids = validate_shots(
        root, project_id, asset_ids, project, configuration, artifacts, errors, shot_index
    )
    scene_ids = set(project.get("scene_ids", [])) if isinstance(project.get("scene_ids"), list) else set()
    validate_ledger(
        ledger, project_id, asset_ids, scene_ids, shot_ids, errors,
        shot_index=shot_index, evidence_refs=evidence_refs,
    )
    validate_generation_manifests(root, artifacts, errors)
    validate_media_manifests(root, artifacts, errors)
    engine = validate_short_drama_engine(root, state, errors, asset_ids, shot_index)
    validate_short_drama_completion(root, state, assets, errors, engine)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir")
    args = parser.parse_args()
    root = Path(args.project_dir).resolve()
    errors = validate_project(root)
    if errors:
        print(f"FAILED: {len(errors)} issue(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"PASS: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
