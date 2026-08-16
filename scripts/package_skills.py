#!/usr/bin/env python3
"""Build deterministic, self-contained installable skills from canonical sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUITE = "ai-drama-forging"


def copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def safe_source(relative: str) -> Path:
    source = (ROOT / relative).resolve()
    try:
        source.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"vendor source escapes repository: {relative}") from exc
    if not source.exists():
        raise ValueError(f"vendor source does not exist: {relative}")
    return source


def safe_target(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"vendor target must be a traversal-free relative path: {relative}")
    target = (root / candidate).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"vendor target escapes package: {relative}") from exc
    return target


def copy_vendor_mapping(mapping: dict, target_root: Path) -> None:
    if set(mapping) != {"source", "target"}:
        raise ValueError("vendor mapping requires exactly source and target")
    source = safe_source(mapping["source"])
    target = safe_target(target_root, mapping["target"])
    if source.is_file():
        copy_file(source, target)
        return
    for path in sorted(source.rglob("*")):
        if path.is_file():
            copy_file(path, target / path.relative_to(source))


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_skill_source(name: str, skill_dir: Path) -> None:
    skill_file = skill_dir / "SKILL.md"
    agent_file = skill_dir / "agents" / "openai.yaml"
    if not skill_file.is_file() or not agent_file.is_file():
        raise ValueError(f"{name}: missing SKILL.md or agents/openai.yaml")
    text = skill_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) > 250:
        raise ValueError(f"{name}: SKILL.md exceeds the 250-line suite target")
    if not re.match(rf"\A---\nname: {re.escape(name)}\ndescription: .+\n---\n", text):
        raise ValueError(f"{name}: invalid frontmatter")
    if "TODO" in text:
        raise ValueError(f"{name}: unresolved TODO")
    yaml = agent_file.read_text(encoding="utf-8")
    if f"${name}" not in yaml or "allow_implicit_invocation" not in yaml:
        raise ValueError(f"{name}: stale agents/openai.yaml")


def install_staged_package(staged: Path, output: Path) -> None:
    """Install a complete staged tree without partially deleting the old package."""
    if not output.exists():
        os.replace(staged, output)
        return

    identity = output / "package-manifest.json"
    if not identity.is_file():
        raise ValueError(f"refusing to replace output without package identity: {output}")
    existing = json.loads(identity.read_text(encoding="utf-8"))
    if existing.get("suite") != SUITE:
        raise ValueError(f"refusing to replace foreign output: {output}")

    reserved = Path(tempfile.mkdtemp(prefix=f".{output.name}.previous.", dir=output.parent))
    reserved.rmdir()
    try:
        os.replace(output, reserved)
    except Exception:
        # The old tree is still at output when the first rename fails.
        raise

    try:
        os.replace(staged, output)
    except Exception as install_error:
        try:
            os.replace(reserved, output)
        except Exception as rollback_error:
            raise RuntimeError(
                f"package install failed and rollback failed; previous package remains at {reserved}"
            ) from rollback_error
        raise install_error

    # Open handles may delay deletion on Windows. The new package is already complete,
    # so a leftover hidden backup is safer than treating a successful install as failed.
    shutil.rmtree(reserved, ignore_errors=True)


def build(output: Path) -> None:
    manifest = json.loads((ROOT / "skill-manifest.json").read_text(encoding="utf-8"))
    skills = manifest.get("skills", [])
    names = [item.get("name") for item in skills if isinstance(item, dict)]
    if not skills or len(names) != len(skills) or len(set(names)) != len(skills):
        raise ValueError("skill-manifest.json must declare unique named skills")
    output = output.resolve()
    if output in {ROOT, ROOT.parent, Path(output.anchor)}:
        raise ValueError("refusing unsafe output path")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        hashes: dict[str, str] = {}
        for item in sorted(skills, key=lambda entry: entry["name"]):
            name = item["name"]
            source = ROOT / "src" / "skills" / name
            validate_skill_source(name, source)
            target = temp / name
            copy_file(source / "SKILL.md", target / "SKILL.md")
            copy_file(source / "agents" / "openai.yaml", target / "agents" / "openai.yaml")
            local_references = source / "references"
            if local_references.is_dir():
                for path in sorted(local_references.glob("*.md")):
                    copy_file(path, target / "references" / path.name)
            for filename in item.get("shared_references", []):
                copy_file(ROOT / "shared" / "references" / filename, target / "references" / filename)
            for filename in item.get("scripts", []):
                copy_file(ROOT / "scripts" / filename, target / "scripts" / filename)
            for filename in item.get("schemas", []):
                copy_file(ROOT / "schemas" / filename, target / "schemas" / filename)
            for mapping in item.get("vendor_files", []):
                copy_vendor_mapping(mapping, target)
            skill_text = (target / "SKILL.md").read_text(encoding="utf-8")
            dependencies = set(re.findall(r"`((?:references|scripts)/[^`]+)`", skill_text))
            dependencies.update(re.findall(r"\]\(((?:references|scripts)/[^)]+)\)", skill_text))
            for relative in sorted(dependencies):
                if not (target / relative).is_file():
                    raise ValueError(f"{name}: unresolved packaged dependency {relative}")
            for path in sorted(target.rglob("*")):
                if path.is_file():
                    hashes[path.relative_to(temp).as_posix()] = file_hash(path)
        package_manifest = {
            "suite": SUITE,
            "schema_version": "1.0",
            "skills": [item["name"] for item in sorted(skills, key=lambda entry: entry["name"])],
            "files": hashes,
        }
        (temp / "package-manifest.json").write_text(
            json.dumps(package_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        install_staged_package(temp, output)
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    print(f"Packaged {len(skills)} skills into {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    build(Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
