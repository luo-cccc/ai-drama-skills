#!/usr/bin/env python3
"""Verify or update the pinned short-drama kernel engine snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_DIR = ROOT / "vendor" / "kernels" / "upstream"
ADAPTED_DIR = ROOT / "engine" / "kernels"
RUNTIME_DIR = ROOT / "engine" / "runtime"
MANIFEST_PATH = ROOT / "vendor" / "kernels" / "snapshot-manifest.json"
ROOT_FILES = ("LICENSE", "NOTICE", "CHANGELOG.md")
SKILLS = ("novel-characters", "novel-outline", "novel-art", "novel-script", "novel-storyboard")
ADAPTED_OVERLAY_FILES = (
    "MODIFICATIONS.md",
    "skills/novel-storyboard/SKILL.md",
    "skills/novel-storyboard/README.md",
    "skills/novel-storyboard/README.en.md",
    "skills/novel-storyboard/references/schema.md",
    "skills/novel-storyboard/references/h3-prompt.md",
    "skills/novel-script/SKILL.md",
    "skills/novel-script/scripts/novel-script.mjs",
    "skills/novel-script/scripts/selftest.mjs",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def allowed_files(source: Path) -> list[Path]:
    files = [source / name for name in ROOT_FILES]
    for skill in SKILLS:
        files.extend(path for path in (source / "skills" / skill).rglob("*") if path.is_file())
    return sorted(files)


def validate_source(source: Path) -> dict[str, str]:
    node = subprocess.run(["node", "--version"], capture_output=True, text=True, encoding="utf-8")
    match = re.fullmatch(r"v(\d+)\.\d+\.\d+\s*", node.stdout) if node.returncode == 0 else None
    if not match or int(match.group(1)) < 18:
        raise RuntimeError("short-drama kernel engine requires Node.js 18+")
    for name in ROOT_FILES:
        if not (source / name).is_file():
            raise ValueError(f"missing upstream file: {name}")
    license_text = (source / "LICENSE").read_text(encoding="utf-8")
    notice_text = (source / "NOTICE").read_text(encoding="utf-8")
    if "Apache License" not in license_text or "Version 2.0" not in license_text:
        raise ValueError("upstream LICENSE is not Apache-2.0")
    # NOTICE attribution is preserved verbatim from upstream; wording is fixed by the source checkout.
    if "Licensed under the Apache License" not in notice_text:
        raise ValueError("upstream NOTICE is missing required attribution")
    versions: dict[str, str] = {}
    for skill in SKILLS:
        base = source / "skills" / skill
        skill_file = base / "SKILL.md"
        script = base / "scripts" / f"{skill}.mjs"
        selftest = base / "scripts" / "selftest.mjs"
        if not skill_file.is_file() or not script.is_file() or not selftest.is_file():
            raise ValueError(f"{skill}: missing SKILL.md, runtime, or selftest")
        match = re.search(r"(?m)^version:\s*([^\s]+)\s*$", skill_file.read_text(encoding="utf-8"))
        if not match:
            raise ValueError(f"{skill}: missing version")
        versions[skill] = match.group(1)
    return versions


def run_selftests(source: Path) -> None:
    for skill in SKILLS:
        command = ["node", str(source / "skills" / skill / "scripts" / "selftest.mjs")]
        completed = subprocess.run(command, cwd=source, capture_output=True, text=True, encoding="utf-8")
        if completed.returncode:
            detail = completed.stdout + completed.stderr
            raise RuntimeError(f"{skill} selftest failed:\n{detail.strip()}")


def build_manifest(source: Path, versions: dict[str, str]) -> dict:
    files = {
        path.relative_to(source).as_posix(): sha256(path)
        for path in allowed_files(source)
    }
    return {
        "schema_version": "1.0",
        "upstream": "short-drama-kernels",
        "license": "Apache-2.0",
        "versions": versions,
        "skills": list(SKILLS),
        "files": files,
        "adaptation": {
            "version": "1.0.0",
            "style_policy": {"public": ["realistic", "hand-painted-cel"], "legacy_import_normalization": True},
            "governance": "Forging scope, evidence, audit, transaction, and timeline contracts",
        },
    }


def apply_adaptation(destination: Path) -> None:
    for path in sorted(destination.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".mjs", ".json"}:
            continue
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"(?i)studio\s+ghibli", "hand-painted cel animation", text)
        text = text.replace(".ghibli", "['hand-painted-cel']")
        text = re.sub(r"\bghibli\s*:", "'hand-painted-cel':", text)
        text = text.replace("ghibliish", "celish")
        text = re.sub(r"\bghibli\b", "hand-painted-cel", text, flags=re.IGNORECASE)
        text = text.replace("吉卜力", "手绘赛璐璐")
        text = text.replace("ジブリ", "手描きセル")
        path.write_text(text, encoding="utf-8", newline="\n")


def stage_snapshot(source: Path, destination: Path, files: list[Path]) -> Path:
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        for path in files:
            relative = path.relative_to(source)
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        return stage
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def apply_adapted_overlays(destination: Path) -> None:
    """Preserve reviewed local documentation overlays across snapshot rebuilds."""
    for relative in ADAPTED_OVERLAY_FILES:
        source = ADAPTED_DIR / relative
        if not source.is_file():
            raise FileNotFoundError(f"missing adapted overlay: {source}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def stage_runtime(adapted_source: Path) -> Path:
    stage = Path(tempfile.mkdtemp(prefix=f".{RUNTIME_DIR.name}.", dir=RUNTIME_DIR.parent))
    try:
        for skill in SKILLS:
            source = adapted_source / "skills" / skill / "scripts" / f"{skill}.mjs"
            target = stage / skill / "scripts" / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        shutil.copy2(adapted_source / "FORGING-ADAPTATION.json", stage / "FORGING-ADAPTATION.json")
        return stage
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def install_replacements(replacements: list[tuple[Path, Path]]) -> None:
    installed: list[tuple[Path, Path | None]] = []
    try:
        for staged, destination in replacements:
            destination.parent.mkdir(parents=True, exist_ok=True)
            backup: Path | None = None
            if destination.exists():
                backup = Path(tempfile.mkdtemp(prefix=f".{destination.name}.previous.", dir=destination.parent))
                backup.rmdir()
                destination.replace(backup)
            try:
                staged.replace(destination)
            except Exception:
                if backup is not None:
                    backup.replace(destination)
                raise
            installed.append((destination, backup))
    except Exception:
        for destination, backup in reversed(installed):
            remove_path(destination)
            if backup is not None and backup.exists():
                backup.replace(destination)
        raise
    for _, backup in installed:
        if backup is not None and backup.exists():
            remove_path(backup)


def update(source: Path) -> None:
    versions = validate_source(source)
    run_selftests(source)
    files = allowed_files(source)
    UPSTREAM_DIR.parent.mkdir(parents=True, exist_ok=True)
    ADAPTED_DIR.parent.mkdir(parents=True, exist_ok=True)
    upstream_stage = stage_snapshot(source, UPSTREAM_DIR, files)
    adapted_stage = stage_snapshot(source, ADAPTED_DIR, files)
    runtime_stage: Path | None = None
    manifest_stage: Path | None = None
    try:
        apply_adaptation(adapted_stage)
        apply_adapted_overlays(adapted_stage)
        manifest = build_manifest(source, versions)
        (adapted_stage / "FORGING-ADAPTATION.json").write_text(
            json.dumps(manifest["adaptation"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        run_selftests(adapted_stage)
        runtime_stage = stage_runtime(adapted_stage)
        manifest["adapted_files"] = {
            path.relative_to(adapted_stage).as_posix(): sha256(path)
            for path in sorted(adapted_stage.rglob("*")) if path.is_file()
        }
        manifest["runtime_files"] = {
            path.relative_to(runtime_stage).as_posix(): sha256(path)
            for path in sorted(runtime_stage.rglob("*")) if path.is_file()
        }
        descriptor, manifest_name = tempfile.mkstemp(prefix=f".{MANIFEST_PATH.name}.", dir=MANIFEST_PATH.parent)
        os.close(descriptor)
        manifest_stage = Path(manifest_name)
        manifest_stage.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        install_replacements([
            (upstream_stage, UPSTREAM_DIR), (adapted_stage, ADAPTED_DIR),
            (runtime_stage, RUNTIME_DIR), (manifest_stage, MANIFEST_PATH),
        ])
    except Exception:
        for staged in (upstream_stage, adapted_stage, runtime_stage, manifest_stage):
            if staged is not None and staged.exists():
                remove_path(staged)
        raise
    print(f"updated kernel snapshot: {len(manifest['files'])} files")


def check(source: Path) -> None:
    versions = validate_source(source)
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(MANIFEST_PATH)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    expected = build_manifest(source, versions)
    if {key: value for key, value in manifest.items() if key not in {"adapted_files", "runtime_files"}} != expected:
        raise ValueError("snapshot manifest differs from source; run --update after review")
    for relative, digest in manifest["files"].items():
        path = (UPSTREAM_DIR / relative).resolve()
        path.relative_to(UPSTREAM_DIR.resolve())
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"snapshot mismatch: {path}")
    for relative, digest in manifest.get("adapted_files", {}).items():
        path = (ADAPTED_DIR / relative).resolve()
        path.relative_to(ADAPTED_DIR.resolve())
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"adapted snapshot mismatch: {path}")
    for relative, digest in manifest.get("runtime_files", {}).items():
        path = (RUNTIME_DIR / relative).resolve()
        path.relative_to(RUNTIME_DIR.resolve())
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"runtime snapshot mismatch: {path}")
    expected = set(manifest["files"])
    upstream_actual = {path.relative_to(UPSTREAM_DIR).as_posix() for path in UPSTREAM_DIR.rglob("*") if path.is_file()}
    adapted_actual = {path.relative_to(ADAPTED_DIR).as_posix() for path in ADAPTED_DIR.rglob("*") if path.is_file()}
    if upstream_actual != expected:
        raise ValueError("upstream snapshot contains missing or unlisted files")
    if adapted_actual != set(manifest.get("adapted_files", {})) | {"FORGING-ADAPTATION.json"}:
        raise ValueError("adapted snapshot contains missing or unlisted files")
    runtime_actual = {path.relative_to(RUNTIME_DIR).as_posix() for path in RUNTIME_DIR.rglob("*") if path.is_file()}
    if runtime_actual != set(manifest.get("runtime_files", {})):
        raise ValueError("runtime snapshot contains missing or unlisted files")
    run_selftests(UPSTREAM_DIR)
    run_selftests(ADAPTED_DIR)
    print(f"snapshot verified: {len(manifest['files'])} files")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--update", action="store_true")
    args = parser.parse_args()
    source = Path(args.source).resolve()
    if args.update:
        update(source)
    else:
        check(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
