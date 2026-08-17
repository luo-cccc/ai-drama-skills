#!/usr/bin/env python3
"""Atomically maintain AI Drama Forging project JSON files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from project_store import ProjectStore, json_bytes
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from project_store import ProjectStore, json_bytes


STATE_FILE = "project-state.json"
ASSET_FILE = "asset-manifest.json"
LEDGER_FILE = "continuity-ledger.json"
SHOT_FILE = "shot-plan.json"
ID_PREFIXES = {
    "character": "CHAR",
    "scene": "SCENE",
    "prop": "PROP",
    "motif": "MOTIF",
    "costume": "COSTUME",
    "background-group": "BG",
}
ASSET_ID_RE = re.compile(r"^(CHAR|SCENE|PROP|MOTIF|COSTUME|BG)-(\d{3})(?:-V\d{2})?$")
LOCK_STATUSES = {"unlocked", "partial", "locked", "stale"}
EVIDENCE_LEVELS = {"confirmed", "inferred", "unknown"}
STAGES = {"intake", "development", "brief", "outline", "screenplay", "audit", "shots", "assets", "complete"}
ARTIFACT_STATUSES = {"draft", "pending-confirmation", "confirmed", "superseded", "invalid"}
AUDIT_DECISIONS = {"pass", "revise", "blocked", "accepted-with-risk"}
ARTIFACT_STAGE_BY_TYPE = {
    "production-brief": "brief", "outline-skeleton": "outline", "series-outline": "outline",
    "scene-outline": "outline", "screenplay": "screenplay",
    "audit": "audit", "shot-plan": "shots", "storyboard": "shots",
    "short-drama-storyboard": "shots", "h3-export": "shots",
    "short-drama-cast": "development", "short-drama-art": "assets", "engine-report": "development",
    "storyboard-key": "shots", "storyboard-scene": "shots", "storyboard-detail": "shots",
    "locked-assets": "assets", "asset-report": "assets",
}
PROJECT_SINGLETON_TYPES = {"production-brief", "outline-skeleton", "series-outline", "scene-outline"}
RANGED_TYPES = {"screenplay", "audit", "storyboard", "short-drama-storyboard", "shot-plan", "h3-export"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def next_id(items: list[dict[str, Any]], key: str, prefix: str) -> str:
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d{{3}})$")
    numbers = [int(match.group(1)) for item in items if (match := pattern.match(item.get(key, "")))]
    value = max(numbers, default=0) + 1
    if value > 999:
        raise ValueError(f"{prefix} ID space exhausted")
    return f"{prefix}-{value:03d}"


def split_csv(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def parse_scope(value: str | None) -> Any:
    if value is None:
        return None
    stripped = value.strip()
    if stripped.startswith("{"):
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise ValueError("scope JSON must be an object")
        scope_interval(parsed)
        return parsed
    return value


def scope_interval(value: Any) -> tuple[int | None, int | None] | None:
    if value is None or isinstance(value, dict) and value.get("kind") == "series":
        return (None, None)
    if isinstance(value, dict) and value.get("kind") == "episodes":
        start, end = value.get("start"), value.get("end")
        if (not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int)
                or isinstance(end, bool) or start < 1 or end < start or set(value) != {"kind", "start", "end"}):
            raise ValueError("episode scope requires integer 1 <= start <= end")
        return (start, end)
    if isinstance(value, str):
        return None
    raise ValueError("scope must be null, a legacy string, or a supported object")


def scopes_overlap(left: Any, right: Any) -> bool:
    left_interval, right_interval = scope_interval(left), scope_interval(right)
    if left_interval == (None, None) or right_interval == (None, None):
        return True
    if left_interval is None or right_interval is None:
        return left == right
    return left_interval[0] <= right_interval[1] and right_interval[0] <= left_interval[1]


def project_paths(project_dir: str) -> tuple[Path, Path, Path, Path, Path]:
    root = Path(project_dir).resolve()
    return root, root / STATE_FILE, root / ASSET_FILE, root / LEDGER_FILE, root / SHOT_FILE


def project_store(args: argparse.Namespace) -> ProjectStore:
    store = getattr(args, "_project_store", None)
    if store is None:
        store = ProjectStore(Path(args.project_dir).resolve())
    return store


def load_candidate(args: argparse.Namespace, relative: str) -> tuple[dict[str, Any], dict[str, str | None]]:
    store = project_store(args)
    baseline = store.capture_baseline([relative])
    return load_json(store.path(relative)), baseline


def commit_json(
    args: argparse.Namespace,
    candidates: dict[str, dict[str, Any]],
    baseline: dict[str, str | None],
    *,
    increment_revision: bool = True,
) -> None:
    state = candidates.get(STATE_FILE)
    if increment_revision and state is not None and "project_revision" in state:
        revision = state["project_revision"]
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise ValueError("project_revision must be a positive integer")
        state["project_revision"] = revision + 1
    project_store(args).commit_json(candidates, baseline=baseline)


def command_init(args: argparse.Namespace) -> None:
    root, state_path, asset_path, ledger_path, _ = project_paths(args.project_dir)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.slug):
        raise ValueError("slug must use lowercase ASCII letters, digits, and hyphens")
    root.mkdir(parents=True, exist_ok=True)
    existing = [path.name for path in (state_path, asset_path, ledger_path) if path.exists()]
    if existing:
        raise FileExistsError(f"refusing to overwrite existing project files: {', '.join(existing)}")
    state = {
        "schema_version": "2.0",
        "project_revision": 1,
        "project": {
            "project_id": "PROJECT-001",
            "title": args.title,
            "slug": args.slug,
            "locale": args.locale,
            "format": None,
            "target_runtime_ms": None,
            "scene_ids": [],
        },
        "stage": "intake",
        "configuration": {
            "checkpoint_policy": "key-nodes",
            "automatic_authorization": False,
            "clip_max_duration_ms": 30000,
            "audio_policy": "preserve-dialogue-environment",
            "subtitle_policy": "unspecified",
            "aspect_ratio": "unspecified",
            "generator": "unspecified",
            "editing_policy": "story-driven",
            "visual_reset_policy": "story-driven",
            "dialogue_rate_chars_per_second": 4.5,
            "report_language": args.locale,
            "prompt_language": args.locale,
            "dialogue_language": args.locale,
            "visual_style": "unspecified",
            "delivery_required": False,
            "prompt_context_required": True,
        },
        "sources": [],
        "artifacts": [],
        "checkpoints": [],
    }
    assets = {"schema_version": "1.0", "project_id": "PROJECT-001", "manifest_version": 1, "assets": []}
    ledger = {"schema_version": "1.0", "project_id": "PROJECT-001", "ledger_version": 1, "scopes": []}
    baseline = project_store(args).capture_baseline([STATE_FILE, ASSET_FILE, LEDGER_FILE])
    commit_json(
        args,
        {STATE_FILE: state, ASSET_FILE: assets, LEDGER_FILE: ledger},
        baseline,
        increment_revision=False,
    )
    print(json.dumps({"project_dir": str(root), "project_id": "PROJECT-001"}, ensure_ascii=False))


def command_source(args: argparse.Namespace) -> None:
    root, _, _, _, _ = project_paths(args.project_dir)
    state, baseline = load_candidate(args, STATE_FILE)
    source_id = next_id(state["sources"], "source_id", "SRC")
    source_path = None
    if args.path:
        stored_path = project_store(args).relative_path(args.path, allow_absolute=True)
        source_path = project_store(args).path(stored_path)
    elif args.availability == "available":
        raise ValueError("available source requires --path")
    availability = args.availability
    digest = None
    stored_path = None if source_path is None else project_store(args).relative_path(source_path, allow_absolute=True)
    if source_path:
        if availability == "available":
            if not source_path.is_file():
                raise FileNotFoundError(source_path)
            digest = sha256(source_path)
    state["sources"].append({
        "source_id": source_id,
        "kind": args.kind,
        "path": stored_path,
        "availability": availability,
        "authority": args.authority,
        "trust_status": args.trust_status,
        "rights": {"status": args.rights},
        "sha256": digest,
    })
    commit_json(args, {STATE_FILE: state}, baseline)
    print(source_id)


def command_artifact(args: argparse.Namespace) -> None:
    _, _, _, _, _ = project_paths(args.project_dir)
    state, baseline = load_candidate(args, STATE_FILE)
    if args.status not in ARTIFACT_STATUSES:
        raise ValueError(f"invalid artifact status: {args.status}")
    if args.status == "confirmed":
        raise ValueError("register artifacts as draft or pending-confirmation, then record approval before confirmation")
    stored_path = project_store(args).relative_path(args.path)
    artifact_path = project_store(args).path(stored_path)
    if not artifact_path.is_file():
        raise FileNotFoundError(artifact_path)
    digest = sha256(artifact_path)
    same_type = [item for item in state["artifacts"] if item["type"] == args.type]
    revision = max((item["revision"] for item in same_type), default=0) + 1
    artifact_id = next_id(state["artifacts"], "artifact_id", "ART")
    artifact = {
        "artifact_id": artifact_id,
        "type": args.type,
        "revision": revision,
        "status": args.status,
        "path": stored_path,
        "depends_on": split_csv(args.depends_on),
        "source_refs": split_csv(args.source_refs),
        "scope": parse_scope(args.scope),
        "sha256": digest,
    }
    audit_values = [
        args.p0_count, args.p1_count, args.p2_count,
        args.required_elements_total, args.required_elements_passed, args.audit_decision,
    ]
    if args.type == "audit":
        if any(value is None for value in audit_values):
            raise ValueError("audit artifacts require structured counts, required-element totals, and decision")
        if any(value < 0 for value in audit_values[:-1]):
            raise ValueError("audit counts must be non-negative")
        if args.required_elements_passed > args.required_elements_total:
            raise ValueError("required_elements_passed cannot exceed required_elements_total")
        artifact["audit_result"] = {
            "p0_count": args.p0_count,
            "p1_count": args.p1_count,
            "p2_count": args.p2_count,
            "required_elements_total": args.required_elements_total,
            "required_elements_passed": args.required_elements_passed,
            "decision": args.audit_decision,
        }
    elif any(value is not None for value in audit_values):
        raise ValueError("audit result options are only valid for audit artifacts")
    state["artifacts"].append(artifact)
    commit_json(args, {STATE_FILE: state}, baseline)
    print(json.dumps(artifact, ensure_ascii=False))


def command_artifact_status(args: argparse.Namespace) -> None:
    _, _, _, _, _ = project_paths(args.project_dir)
    state, baseline = load_candidate(args, STATE_FILE)
    if args.status not in ARTIFACT_STATUSES:
        raise ValueError(f"invalid artifact status: {args.status}")
    artifact = next((item for item in state["artifacts"] if item["artifact_id"] == args.artifact_id), None)
    if artifact is None:
        raise KeyError(args.artifact_id)
    if args.status == "confirmed":
        path = project_store(args).path(artifact["path"])
        if not path.is_file() or not artifact.get("sha256") or sha256(path) != artifact["sha256"]:
            raise ValueError("confirmed artifact requires a present file matching its registered sha256")
        required_stage = ARTIFACT_STAGE_BY_TYPE.get(artifact.get("type"))
        if artifact.get("type") in {"production-brief", "outline-skeleton", "series-outline", "scene-outline", "screenplay"}:
            approved = any(
                args.artifact_id in checkpoint.get("affects", [])
                and checkpoint.get("stage") == required_stage
                and checkpoint.get("decision") in {"confirmed", "automatic"}
                for checkpoint in state["checkpoints"]
            )
            if not approved:
                raise ValueError(f"{args.artifact_id} lacks an approving {required_stage} checkpoint")
        conflicting = []
        for item in state["artifacts"]:
            if item is artifact or item.get("type") != artifact.get("type") or item.get("status") != "confirmed":
                continue
            series_range_exception = artifact.get("type") in {"audit", "shot-plan"} and (
                artifact.get("scope") == {"kind": "series"}
            ) != (
                item.get("scope") == {"kind": "series"}
            )
            if artifact.get("type") in PROJECT_SINGLETON_TYPES or (
                artifact.get("type") in RANGED_TYPES and not series_range_exception
                and scopes_overlap(item.get("scope"), artifact.get("scope"))
            ):
                conflicting.append(item["artifact_id"])
        if conflicting:
            raise ValueError(f"supersede confirmed revisions before confirming {args.artifact_id}: {conflicting}")
    artifact["status"] = args.status
    commit_json(args, {STATE_FILE: state}, baseline)
    print(args.artifact_id)


def command_checkpoint(args: argparse.Namespace) -> None:
    state, baseline = load_candidate(args, STATE_FILE)
    if args.decision == "automatic" and state["configuration"].get("automatic_authorization") is not True:
        raise ValueError("automatic checkpoint requires project automatic_authorization")
    affects = split_csv(args.affects)
    if not affects:
        raise ValueError("checkpoint affects must be non-empty")
    artifacts = {item["artifact_id"]: item for item in state["artifacts"]}
    missing = set(affects) - artifacts.keys()
    if missing:
        raise KeyError(f"checkpoint affects unknown artifacts: {sorted(missing)}")
    for artifact_id in affects:
        expected = ARTIFACT_STAGE_BY_TYPE.get(artifacts[artifact_id].get("type"))
        if expected and expected != args.stage:
            raise ValueError(f"checkpoint stage {args.stage} does not match {artifact_id} stage {expected}")
    checkpoint_id = next_id(state["checkpoints"], "checkpoint_id", "CHK")
    checkpoint = {
        "checkpoint_id": checkpoint_id,
        "stage": args.stage,
        "decision": args.decision,
        "authorization": args.authorization,
        "sequence": len(state["checkpoints"]) + 1,
        "affects": affects,
    }
    state["checkpoints"].append(checkpoint)
    commit_json(args, {STATE_FILE: state}, baseline)
    print(checkpoint_id)


def command_stage(args: argparse.Namespace) -> None:
    root, _, _, _, _ = project_paths(args.project_dir)
    if args.stage not in STAGES:
        raise ValueError(f"invalid stage: {args.stage}")
    state, baseline = load_candidate(args, STATE_FILE)
    if args.stage == "complete" and (root / "short-drama-engine.json").exists():
        raise ValueError("short-drama projects must enter complete through short_drama_cli.py complete")
    state["stage"] = args.stage
    commit_json(args, {STATE_FILE: state}, baseline)
    print(args.stage)


def command_configure(args: argparse.Namespace) -> None:
    state, baseline = load_candidate(args, STATE_FILE)
    project = state["project"]
    configuration = state["configuration"]
    if args.target_runtime_ms is not None:
        if args.target_runtime_ms < 1:
            raise ValueError("target_runtime_ms must be positive")
        project["target_runtime_ms"] = args.target_runtime_ms
    if args.format is not None:
        project["format"] = args.format
    if args.scene_count is not None:
        if args.scene_count < 1 or args.scene_count > 999:
            raise ValueError("scene_count must be between 1 and 999")
        project["scene_ids"] = [f"SCN-{index:03d}" for index in range(1, args.scene_count + 1)]
    if args.clip_max_duration_ms is not None:
        if args.clip_max_duration_ms < 1:
            raise ValueError("clip_max_duration_ms must be positive")
        configuration["clip_max_duration_ms"] = args.clip_max_duration_ms
    for key in [
        "audio_policy", "subtitle_policy", "aspect_ratio", "generator",
        "editing_policy", "visual_reset_policy", "checkpoint_policy",
        "report_language", "prompt_language", "dialogue_language", "visual_style",
    ]:
        value = getattr(args, key)
        if value is not None:
            configuration[key] = value
    if args.automatic_authorization is not None:
        configuration["automatic_authorization"] = args.automatic_authorization == "true"
    for key in ["delivery_required", "prompt_context_required"]:
        value = getattr(args, key)
        if value is not None:
            configuration[key] = value == "true"
    if args.dialogue_rate_chars_per_second is not None:
        if not 1 <= args.dialogue_rate_chars_per_second <= 20:
            raise ValueError("dialogue_rate_chars_per_second must be between 1 and 20")
        configuration["dialogue_rate_chars_per_second"] = args.dialogue_rate_chars_per_second
    commit_json(args, {STATE_FILE: state}, baseline)
    print(json.dumps({"project": project, "configuration": configuration}, ensure_ascii=False))


def command_allocate(args: argparse.Namespace) -> None:
    manifest, baseline = load_candidate(args, ASSET_FILE)
    prefix = ID_PREFIXES[args.type]
    asset_id = next_id(manifest["assets"], "asset_id", prefix)
    asset = {
        "asset_id": asset_id,
        "type": args.type,
        "name": args.name,
        "aliases": split_csv(args.aliases),
        "lock_status": "unlocked",
        "locked_fields": [],
        "evidence": [],
        "visual_dna": {},
    }
    manifest["assets"].append(asset)
    manifest["manifest_version"] += 1
    commit_json(args, {ASSET_FILE: manifest}, baseline)
    print(asset_id)


def command_allocate_variant(args: argparse.Namespace) -> None:
    manifest, baseline = load_candidate(args, ASSET_FILE)
    base = next((item for item in manifest["assets"] if item["asset_id"] == args.base_asset_id), None)
    if base is None or re.search(r"-V\d{2}$", args.base_asset_id):
        raise ValueError("base_asset_id must identify an existing non-variant asset")
    pattern = re.compile(rf"^{re.escape(args.base_asset_id)}-V(\d{{2}})$")
    versions = [
        int(match.group(1))
        for item in manifest["assets"]
        if (match := pattern.fullmatch(item.get("asset_id", "")))
    ]
    version = max(versions, default=0) + 1
    if version > 99:
        raise ValueError(f"variant ID space exhausted for {args.base_asset_id}")
    asset_id = f"{args.base_asset_id}-V{version:02d}"
    manifest["assets"].append({
        "asset_id": asset_id,
        "type": base["type"],
        "name": args.name,
        "aliases": split_csv(args.aliases),
        "lock_status": "unlocked",
        "locked_fields": [],
        "evidence": [],
        "visual_dna": {},
    })
    manifest["manifest_version"] += 1
    commit_json(args, {ASSET_FILE: manifest}, baseline)
    print(asset_id)


def validate_manifest_candidate(candidate: Any, current: dict[str, Any]) -> None:
    if not isinstance(candidate, dict):
        raise ValueError("candidate manifest must be a JSON object")
    expected_keys = {"schema_version", "project_id", "manifest_version", "assets"}
    if set(candidate) != expected_keys:
        raise ValueError(f"candidate manifest keys must be {sorted(expected_keys)}")
    if candidate.get("schema_version") != "1.0" or candidate.get("project_id") != current.get("project_id"):
        raise ValueError("candidate schema_version and project_id must match the current manifest")
    if candidate.get("manifest_version") != current.get("manifest_version", 0) + 1:
        raise ValueError("candidate manifest_version must increment exactly once")
    assets = candidate.get("assets")
    if not isinstance(assets, list):
        raise ValueError("candidate assets must be an array")
    seen: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}
    prefix_by_type = {value: key for key, value in ID_PREFIXES.items()}
    for index, asset in enumerate(assets, start=1):
        if not isinstance(asset, dict):
            raise ValueError(f"asset {index} must be an object")
        required = {"asset_id", "type", "name", "aliases", "lock_status", "locked_fields", "evidence", "visual_dna"}
        if set(asset) != required:
            raise ValueError(f"asset {index} keys must be {sorted(required)}")
        asset_id = asset.get("asset_id")
        match = ASSET_ID_RE.fullmatch(asset_id) if isinstance(asset_id, str) else None
        if not match or asset_id in seen:
            raise ValueError(f"invalid or duplicate asset_id: {asset_id}")
        seen.add(asset_id)
        by_id[asset_id] = asset
        if asset.get("type") != prefix_by_type.get(match.group(1)):
            raise ValueError(f"asset ID/type mismatch: {asset_id}/{asset.get('type')}")
        if not isinstance(asset.get("name"), str) or not asset["name"]:
            raise ValueError(f"asset {asset_id} requires a name")
        for key in ("aliases", "locked_fields"):
            value = asset.get(key)
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value) or len(value) != len(set(value)):
                raise ValueError(f"asset {asset_id} {key} must contain unique strings")
        status = asset.get("lock_status")
        if status not in LOCK_STATUSES:
            raise ValueError(f"asset {asset_id} has invalid lock_status")
        evidence = asset.get("evidence")
        if not isinstance(evidence, list):
            raise ValueError(f"asset {asset_id} evidence must be an array")
        confirmed_fields: set[str] = set()
        for item in evidence:
            if not isinstance(item, dict) or set(item) != {"field", "level", "source_ref", "locator"}:
                raise ValueError(f"asset {asset_id} has malformed evidence")
            if not isinstance(item.get("field"), str) or not item["field"] or item.get("level") not in EVIDENCE_LEVELS:
                raise ValueError(f"asset {asset_id} has invalid evidence field or level")
            if item["level"] == "confirmed":
                if not isinstance(item.get("source_ref"), str) or not item["source_ref"]:
                    raise ValueError(f"asset {asset_id} confirmed evidence requires source_ref")
                if not isinstance(item.get("locator"), str) or not item["locator"]:
                    raise ValueError(f"asset {asset_id} confirmed evidence requires locator")
                confirmed_fields.add(item["field"])
        locked_fields = set(asset["locked_fields"])
        if status in {"locked", "partial"} and (not locked_fields or not locked_fields <= confirmed_fields):
            raise ValueError(f"asset {asset_id} locks fields without confirmed evidence")
        if status == "unlocked" and locked_fields:
            raise ValueError(f"asset {asset_id} is unlocked but lists locked_fields")
        if not isinstance(asset.get("visual_dna"), dict):
            raise ValueError(f"asset {asset_id} visual_dna must be an object")
        variant = re.fullmatch(r"(.+)-V\d{2}", asset_id)
        if variant and variant.group(1) not in seen and variant.group(1) not in {item.get("asset_id") for item in assets if isinstance(item, dict)}:
            raise ValueError(f"variant asset lacks base asset: {asset_id}")

    previous = {item["asset_id"]: item for item in current.get("assets", [])}
    missing = set(previous) - set(by_id)
    if missing:
        raise ValueError(f"candidate removes existing assets: {sorted(missing)}")
    for asset_id, old in previous.items():
        new = by_id[asset_id]
        if new["type"] != old["type"]:
            raise ValueError(f"candidate changes asset type: {asset_id}")
        weakened = set(old.get("locked_fields", [])) - set(new.get("locked_fields", []))
        if weakened and new.get("lock_status") != "stale":
            raise ValueError(f"candidate weakens locked fields without marking stale: {asset_id}")


def command_apply_manifest(args: argparse.Namespace) -> None:
    current, baseline = load_candidate(args, ASSET_FILE)
    candidate_relative = project_store(args).relative_path(args.input, allow_absolute=True)
    candidate_path = project_store(args).path(candidate_relative)
    candidate = load_json(candidate_path)
    if args.expected_version is not None and current.get("manifest_version") != args.expected_version:
        raise ValueError(
            f"manifest version changed: expected {args.expected_version}, found {current.get('manifest_version')}"
        )
    validate_manifest_candidate(candidate, current)
    commit_json(args, {ASSET_FILE: candidate}, baseline)
    print(candidate["manifest_version"])


def command_event(args: argparse.Namespace) -> None:
    root, state_path, asset_path, ledger_path, shot_path = project_paths(args.project_dir)
    store = project_store(args)
    baseline = store.capture_baseline([LEDGER_FILE])
    ledger = load_json(ledger_path)
    manifest = load_json(asset_path)
    if args.asset_id not in {item["asset_id"] for item in manifest["assets"]}:
        raise KeyError(f"unknown asset ID: {args.asset_id}")
    if not args.field:
        raise ValueError("field must be non-empty")
    if not args.evidence_ref:
        raise ValueError("evidence_ref must be non-empty")
    if args.at_ms is not None and args.at_ms < 0:
        raise ValueError("at_ms must be non-negative")
    if args.scene_ref is not None:
        state = load_json(project_paths(args.project_dir)[1])
        scenes = set(state.get("project", {}).get("scene_ids", []))
        if args.scene_ref not in scenes:
            raise KeyError(f"unknown screenplay scene ID: {args.scene_ref}")
    if args.shot_ref is not None:
        state = load_json(state_path)
        plan_paths = [shot_path]
        plan_paths.extend(
            store.path(item["path"]) for item in state.get("artifacts", [])
            if item.get("type") == "shot-plan" and item.get("status") != "invalid" and isinstance(item.get("path"), str)
        )
        shots: set[str] = set()
        for path in dict.fromkeys(plan_paths):
            if not path.is_file():
                continue
            plan = load_json(path)
            shots.update(item.get("shot_id") for item in plan.get("shots", []) if isinstance(item, dict))
        if not shots:
            raise FileNotFoundError("shot_ref requires a registered shot plan")
        if args.shot_ref not in shots:
            raise KeyError(f"unknown shot ID: {args.shot_ref}")
    before = json.loads(args.before)
    after = json.loads(args.after)
    scope = next((item for item in ledger["scopes"] if item["scope_id"] == args.scope), None)
    if scope is None:
        scope = {
            "scope_id": args.scope,
            "sequence": len(ledger["scopes"]) + 1,
            "start_snapshot": {args.asset_id: {args.field: before}},
            "events": [],
            "end_snapshot": {args.asset_id: {args.field: before}},
        }
        ledger["scopes"].append(scope)
    prior_events = [
        event for event in scope["events"]
        if event["asset_id"] == args.asset_id and event["field"] == args.field
    ]
    if prior_events:
        expected_before = prior_events[-1]["after"]
    else:
        initial = scope["start_snapshot"].setdefault(args.asset_id, {})
        if args.field not in initial:
            initial[args.field] = before
            scope["end_snapshot"].setdefault(args.asset_id, {})[args.field] = before
        expected_before = initial[args.field]
    if before != expected_before:
        raise ValueError(
            f"before value does not match continuity state for {args.asset_id}.{args.field}"
        )
    timed_events = [event["at_ms"] for event in scope["events"] if event.get("at_ms") is not None]
    if args.at_ms is not None and timed_events and args.at_ms < timed_events[-1]:
        raise ValueError("at_ms must not move backward within a continuity scope")
    all_events = [event for item in ledger["scopes"] for event in item["events"]]
    event_id = next_id(all_events, "event_id", "EVT")
    event = {
        "event_id": event_id,
        "asset_id": args.asset_id,
        "field": args.field,
        "before": before,
        "after": after,
        "at_ms": args.at_ms,
        "scene_ref": args.scene_ref,
        "shot_ref": args.shot_ref,
        "evidence_ref": args.evidence_ref,
    }
    scope["events"].append(event)
    scope["end_snapshot"].setdefault(args.asset_id, {})[args.field] = after
    ledger["ledger_version"] += 1
    commit_json(args, {LEDGER_FILE: ledger}, baseline)
    print(event_id)


def immutable_migration_path(path: str, revision: int) -> str:
    source = Path(path.replace("\\", "/"))
    version_marker = re.compile(r"-v\d{3}$", re.IGNORECASE)
    if version_marker.search(source.stem):
        return source.as_posix()
    name = f"{source.stem}-v{revision:03d}{source.suffix}"
    return (source.parent / name).as_posix()


def command_migrate_project(args: argparse.Namespace) -> None:
    store = project_store(args)
    state, state_baseline = load_candidate(args, STATE_FILE)
    version = state.get("schema_version")
    changes: list[dict[str, Any]] = []
    candidate = json.loads(json.dumps(state))
    files: dict[str, bytes] = {}
    tracked_paths = {STATE_FILE}
    if version == "1.0":
        candidate["schema_version"] = "2.0"
        candidate["project_revision"] = 1
        changes.extend([
            {"field": "schema_version", "from": "1.0", "to": "2.0"},
            {"field": "project_revision", "from": None, "to": 1},
        ])
        configuration = candidate.setdefault("configuration", {})
        locale = candidate.get("project", {}).get("locale", "zh-CN")
        configuration_defaults = {
            "report_language": locale,
            "prompt_language": locale,
            "dialogue_language": locale,
            "visual_style": "unspecified",
            "delivery_required": False,
            "prompt_context_required": True,
        }
        for key, value in configuration_defaults.items():
            if key not in configuration:
                configuration[key] = value
                changes.append({"field": f"configuration.{key}", "from": None, "to": value})
        for source in candidate.get("sources", []):
            source_id = source.get("source_id", "unknown")
            if "trust_status" not in source:
                source["trust_status"] = "untrusted-content"
                changes.append({"field": f"sources.{source_id}.trust_status", "from": None, "to": "untrusted-content"})
            if "rights" not in source:
                source["rights"] = {"status": "unknown"}
                changes.append({"field": f"sources.{source_id}.rights", "from": None, "to": {"status": "unknown"}})
        for artifact in candidate.get("artifacts", []):
            if artifact.get("status") != "confirmed":
                continue
            artifact_id = artifact.get("artifact_id", "unknown")
            source_path = artifact.get("path")
            revision = artifact.get("revision")
            if not isinstance(source_path, str) or not isinstance(revision, int) or isinstance(revision, bool):
                artifact["status"] = "invalid"
                changes.append({"artifact_id": artifact_id, "action": "invalidate", "reason": "invalid path or revision"})
                continue
            try:
                source_file = store.path(source_path)
            except (ValueError, OSError):
                artifact["status"] = "invalid"
                changes.append({"artifact_id": artifact_id, "action": "invalidate", "reason": "unsafe artifact path"})
                continue
            tracked_paths.add(source_path)
            registered_hash = artifact.get("sha256")
            if not source_file.is_file() or not isinstance(registered_hash, str) or sha256(source_file) != registered_hash:
                artifact["status"] = "invalid"
                changes.append({"artifact_id": artifact_id, "action": "invalidate", "reason": "missing or hash-mismatched source artifact"})
                continue
            if artifact.get("type") == "locked-assets":
                continue
            target_path = immutable_migration_path(source_path, revision)
            if target_path == source_path:
                continue
            tracked_paths.add(target_path)
            content = source_file.read_bytes()
            target_file = store.path(target_path)
            if target_file.exists():
                if not target_file.is_file() or sha256(target_file) != registered_hash:
                    raise ValueError(f"migration target conflicts with existing file: {target_path}")
            else:
                files[target_path] = content
            artifact["path"] = target_path
            changes.append({
                "artifact_id": artifact_id, "action": "snapshot",
                "from": source_path, "to": target_path, "sha256": registered_hash,
            })
    elif version == "2.0":
        revision = candidate.get("project_revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise ValueError("2.0 project state requires a positive integer project_revision")
    else:
        raise ValueError(f"unsupported project-state schema_version for migration: {version}")
    if args.apply and changes:
        files[STATE_FILE] = json_bytes(candidate)
        baseline = store.capture_baseline(tracked_paths)
        if baseline.get(STATE_FILE) != state_baseline.get(STATE_FILE):
            raise RuntimeError("project state changed during migration planning")
        for relative in files:
            baseline.setdefault(relative, None)
        store.commit(files, baseline=baseline)
    print(json.dumps({
        "mode": "apply" if args.apply else "dry-run",
        "changed": bool(changes),
        "changes": changes,
    }, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--project-dir", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--slug", required=True)
    init.add_argument("--locale", default="zh-CN")
    init.set_defaults(handler=command_init)

    source = sub.add_parser("register-source")
    source.add_argument("--project-dir", required=True)
    source.add_argument("--kind", required=True)
    source.add_argument("--path")
    source.add_argument("--availability", choices=["available", "missing", "not-distributed"], default="available")
    source.add_argument("--authority", choices=["canonical", "constraint", "reference", "unknown"], default="canonical")
    source.add_argument(
        "--trust-status",
        choices=["untrusted-content", "trusted-project-data", "trusted-control"],
        default="untrusted-content",
    )
    source.add_argument(
        "--rights",
        choices=[
            "user-owned", "authorized", "public-domain", "factual",
            "third-party-restricted", "unknown",
        ],
        default="unknown",
    )
    source.set_defaults(handler=command_source)

    artifact = sub.add_parser("register-artifact")
    artifact.add_argument("--project-dir", required=True)
    artifact.add_argument("--type", required=True)
    artifact.add_argument("--path", required=True)
    artifact.add_argument("--status", default="draft")
    artifact.add_argument("--depends-on", default="")
    artifact.add_argument("--source-refs", default="")
    artifact.add_argument("--scope")
    artifact.add_argument("--p0-count", type=int)
    artifact.add_argument("--p1-count", type=int)
    artifact.add_argument("--p2-count", type=int)
    artifact.add_argument("--required-elements-total", type=int)
    artifact.add_argument("--required-elements-passed", type=int)
    artifact.add_argument("--audit-decision", choices=sorted(AUDIT_DECISIONS))
    artifact.set_defaults(handler=command_artifact)

    artifact_status = sub.add_parser("set-artifact-status")
    artifact_status.add_argument("--project-dir", required=True)
    artifact_status.add_argument("--artifact-id", required=True)
    artifact_status.add_argument("--status", required=True)
    artifact_status.set_defaults(handler=command_artifact_status)

    checkpoint = sub.add_parser("checkpoint")
    checkpoint.add_argument("--project-dir", required=True)
    checkpoint.add_argument("--stage", choices=["development", "brief", "outline", "screenplay", "audit", "shots", "assets"], required=True)
    checkpoint.add_argument("--decision", choices=["confirmed", "revise", "automatic", "rejected"], required=True)
    checkpoint.add_argument("--authorization", required=True)
    checkpoint.add_argument("--affects", default="")
    checkpoint.set_defaults(handler=command_checkpoint)

    stage = sub.add_parser("set-stage")
    stage.add_argument("--project-dir", required=True)
    stage.add_argument("--stage", required=True)
    stage.set_defaults(handler=command_stage)

    configure = sub.add_parser("configure")
    configure.add_argument("--project-dir", required=True)
    configure.add_argument("--target-runtime-ms", type=int)
    configure.add_argument("--format")
    configure.add_argument("--scene-count", type=int)
    configure.add_argument("--clip-max-duration-ms", type=int)
    configure.add_argument("--audio-policy")
    configure.add_argument("--subtitle-policy")
    configure.add_argument("--aspect-ratio")
    configure.add_argument("--generator")
    configure.add_argument("--editing-policy")
    configure.add_argument("--visual-reset-policy")
    configure.add_argument("--dialogue-rate-chars-per-second", type=float)
    configure.add_argument("--checkpoint-policy", choices=["key-nodes", "automatic", "every-stage"])
    configure.add_argument("--automatic-authorization", choices=["true", "false"])
    configure.add_argument("--report-language")
    configure.add_argument("--prompt-language")
    configure.add_argument("--dialogue-language")
    configure.add_argument("--visual-style")
    configure.add_argument("--delivery-required", choices=["true", "false"])
    configure.add_argument("--prompt-context-required", choices=["true", "false"])
    configure.set_defaults(handler=command_configure)

    allocate = sub.add_parser("allocate-id")
    allocate.add_argument("--project-dir", required=True)
    allocate.add_argument("--type", choices=sorted(ID_PREFIXES), required=True)
    allocate.add_argument("--name", required=True)
    allocate.add_argument("--aliases", default="")
    allocate.set_defaults(handler=command_allocate)

    variant = sub.add_parser("allocate-variant")
    variant.add_argument("--project-dir", required=True)
    variant.add_argument("--base-asset-id", required=True)
    variant.add_argument("--name", required=True)
    variant.add_argument("--aliases", default="")
    variant.set_defaults(handler=command_allocate_variant)

    apply_manifest = sub.add_parser("apply-manifest")
    apply_manifest.add_argument("--project-dir", required=True)
    apply_manifest.add_argument("--input", required=True)
    apply_manifest.add_argument("--expected-version", type=int)
    apply_manifest.set_defaults(handler=command_apply_manifest)

    event = sub.add_parser("record-event")
    event.add_argument("--project-dir", required=True)
    event.add_argument("--scope", required=True)
    event.add_argument("--asset-id", required=True)
    event.add_argument("--field", required=True)
    event.add_argument("--before", required=True, help="JSON value")
    event.add_argument("--after", required=True, help="JSON value")
    event.add_argument("--evidence-ref", required=True)
    event.add_argument("--at-ms", type=int)
    event.add_argument("--scene-ref")
    event.add_argument("--shot-ref")
    event.set_defaults(handler=command_event)

    migrate = sub.add_parser("migrate-project")
    migrate.add_argument("--project-dir", required=True)
    mode = migrate.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    migrate.set_defaults(handler=command_migrate_project)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    store = ProjectStore(Path(args.project_dir).resolve())
    with store.locked():
        args._project_store = store
        args.handler(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
