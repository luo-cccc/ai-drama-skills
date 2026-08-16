#!/usr/bin/env python3
"""Verify packaged skills are self-contained and match the package manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def run_help(script: Path, cwd: Path) -> list[str]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode:
        return [f"{script}: --help failed: {(completed.stdout + completed.stderr).strip()}"]
    return []


def verify(dist: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = dist / "package-manifest.json"
    if not manifest_path.is_file():
        return ["package-manifest.json is missing"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = manifest.get("files", {})
    actual = {
        path.relative_to(dist).as_posix(): digest(path)
        for path in sorted(dist.rglob("*"))
        if path.is_file() and path != manifest_path
    }
    if expected != actual:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        changed = sorted(key for key in set(expected) & set(actual) if expected[key] != actual[key])
        if missing:
            errors.append(f"package manifest missing files on disk: {missing}")
        if extra:
            errors.append(f"package manifest has unregistered files: {extra}")
        if changed:
            errors.append(f"package manifest hash mismatches: {changed}")
    before_help = {
        path.relative_to(dist).as_posix(): digest(path)
        for path in sorted(dist.rglob("*"))
        if path.is_file()
    }
    with tempfile.TemporaryDirectory() as temporary:
        outside = Path(temporary)
        for skill in sorted(path for path in dist.iterdir() if path.is_dir()):
            scripts = skill / "scripts"
            if not scripts.is_dir():
                continue
            if (scripts / "validate_project.py").is_file():
                for dependency in ("schema_validator.py", "timeline_cli.py"):
                    if not (scripts / dependency).is_file():
                        errors.append(f"{skill.name} is missing validator dependency {dependency}")
                errors.extend(run_help(scripts / "validate_project.py", outside))
            if (scripts / "state_cli.py").is_file():
                if not (scripts / "project_store.py").is_file():
                    errors.append(f"{skill.name} is missing project_store.py")
                errors.extend(run_help(scripts / "state_cli.py", outside))
            if (scripts / "short_drama_cli.py").is_file():
                if not (scripts / "project_store.py").is_file():
                    errors.append(f"{skill.name} is missing project_store.py for short drama")
                errors.extend(run_help(scripts / "short_drama_cli.py", outside))
    after_help = {
        path.relative_to(dist).as_posix(): digest(path)
        for path in sorted(dist.rglob("*"))
        if path.is_file()
    }
    if after_help != before_help:
        errors.append("isolated runtime checks modified the packaged tree")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", default="dist")
    args = parser.parse_args()
    errors = verify(Path(args.dist).resolve())
    if errors:
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"PASS: {Path(args.dist).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
