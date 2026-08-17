#!/usr/bin/env python3
"""Shared locking and transactional storage for project files."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping


LOCK_FILE = ".short-drama.lock"
TRANSACTION_DIR = ".short-drama-transaction"
JOURNAL_FILE = "journal.json"
_RESERVED_PATHS = {LOCK_FILE, TRANSACTION_DIR}


class ConcurrentModificationError(RuntimeError):
    """Raised when a file no longer matches its captured baseline."""


def json_bytes(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalized_relative(relative: str | os.PathLike[str]) -> str:
    value = os.fspath(relative)
    if not value or "\x00" in value:
        raise ValueError("project path must be a non-empty relative path")
    portable = value.replace("\\", "/")
    if portable.startswith("/") or re.match(r"^[A-Za-z]:", portable):
        raise ValueError("project path must be relative")
    pure = PurePosixPath(portable)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("project path must not contain traversal segments")
    normalized = pure.as_posix()
    if normalized in {"", "."}:
        raise ValueError("project path must identify a file")
    if pure.parts[0] in _RESERVED_PATHS:
        raise ValueError(f"project path is reserved: {pure.parts[0]}")
    return normalized


def safe_project_path(root: Path | str, relative: str | os.PathLike[str]) -> Path:
    """Resolve a project-relative path without permitting traversal or metadata writes."""
    project_root = Path(root).resolve()
    normalized = _normalized_relative(relative)
    candidate = (project_root / Path(*PurePosixPath(normalized).parts)).resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError as exc:
        raise ValueError("project path must stay inside the project directory") from exc
    return candidate


def project_relative_path(
    root: Path | str,
    path: str | os.PathLike[str],
    *,
    allow_absolute: bool = False,
) -> str:
    """Return a normalized, safe project-relative path."""
    project_root = Path(root).resolve()
    requested = Path(path)
    if requested.is_absolute():
        if not allow_absolute:
            raise ValueError("project path must be relative")
        resolved = requested.resolve()
        try:
            relative = resolved.relative_to(project_root).as_posix()
        except ValueError as exc:
            raise ValueError("project path must stay inside the project directory") from exc
    else:
        relative = os.fspath(path)
    normalized = _normalized_relative(relative)
    safe_project_path(project_root, normalized)
    return normalized


def _current_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError(f"project file path is not a regular file: {path}")
    return sha256_file(path)


def capture_baseline(
    root: Path | str,
    paths: list[str] | tuple[str, ...] | set[str],
) -> dict[str, str | None]:
    project_root = Path(root).resolve()
    baseline: dict[str, str | None] = {}
    for relative in paths:
        normalized = project_relative_path(project_root, relative)
        baseline[normalized] = _current_hash(safe_project_path(project_root, normalized))
    return baseline


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _internal_path(root: Path, relative: str) -> Path:
    candidate = (root / Path(*PurePosixPath(relative).parts)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("transaction path escaped its directory") from exc
    return candidate


def _write_journal(transaction: Path, journal: dict[str, Any]) -> None:
    atomic_write_bytes(transaction / JOURNAL_FILE, json_bytes(journal))


def rollback_transaction(root: Path | str, transaction: Path | None = None) -> bool:
    project_root = Path(root).resolve()
    transaction = transaction or project_root / TRANSACTION_DIR
    if not transaction.exists():
        return False
    journal_path = transaction / JOURNAL_FILE
    if not journal_path.is_file():
        shutil.rmtree(transaction, ignore_errors=True)
        return True
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for item in reversed(journal.get("files", [])):
        try:
            target = safe_project_path(project_root, item["path"])
            backup = _internal_path(transaction / "backups", item["path"])
            if item.get("existed"):
                if not backup.is_file():
                    raise FileNotFoundError(f"missing transaction backup: {item['path']}")
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(backup, target)
                _fsync_directory(target.parent)
            else:
                target.unlink(missing_ok=True)
        except Exception as exc:
            errors.append(f"{item.get('path')}: {exc}")
    if errors:
        raise RuntimeError("transaction rollback failed: " + "; ".join(errors))
    shutil.rmtree(transaction)
    _fsync_directory(project_root)
    return True


def recover_transaction(root: Path | str) -> bool:
    """Recover an interrupted transaction. The caller must hold the project lock."""
    project_root = Path(root).resolve()
    transaction = project_root / TRANSACTION_DIR
    if not transaction.exists():
        return False
    journal_path = transaction / JOURNAL_FILE
    if journal_path.is_file():
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        if journal.get("state") == "committed":
            shutil.rmtree(transaction)
            _fsync_directory(project_root)
            return True
    return rollback_transaction(project_root, transaction)


def commit_files(
    root: Path | str,
    candidates: Mapping[str, bytes],
    *,
    baseline: Mapping[str, str | None] | None = None,
) -> None:
    """Commit candidate bytes as one recoverable transaction; caller holds the lock."""
    project_root = Path(root).resolve()
    if not candidates:
        raise ValueError("transaction requires at least one candidate file")
    normalized_candidates: dict[str, bytes] = {}
    for relative, content in candidates.items():
        normalized = project_relative_path(project_root, relative)
        if normalized in normalized_candidates:
            raise ValueError(f"duplicate transaction path: {normalized}")
        if not isinstance(content, bytes):
            raise TypeError(f"candidate content must be bytes: {normalized}")
        normalized_candidates[normalized] = content

    normalized_baseline: dict[str, str | None] = {}
    for relative, digest in (baseline or {}).items():
        normalized = project_relative_path(project_root, relative)
        if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"invalid baseline sha256 for {normalized}")
        normalized_baseline[normalized] = digest
    missing_baselines = set(normalized_candidates) - set(normalized_baseline)
    if baseline is not None and missing_baselines:
        raise ValueError(f"baseline is missing candidate paths: {sorted(missing_baselines)}")
    for relative, expected in normalized_baseline.items():
        actual = _current_hash(safe_project_path(project_root, relative))
        if actual != expected:
            raise ConcurrentModificationError(
                f"project file changed: {relative} (expected {expected}, found {actual})"
            )

    transaction = project_root / TRANSACTION_DIR
    if transaction.exists():
        raise RuntimeError("unfinished project transaction exists; recover it before committing")
    transaction.mkdir(parents=False)
    staged_root = transaction / "staged"
    backup_root = transaction / "backups"
    journal: dict[str, Any] = {"schema_version": "1.0", "state": "preparing", "files": []}
    _write_journal(transaction, journal)
    try:
        for relative in sorted(normalized_candidates):
            target = safe_project_path(project_root, relative)
            staged = _internal_path(staged_root, relative)
            staged.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_bytes(staged, normalized_candidates[relative])
            existed = target.exists()
            if existed and not target.is_file():
                raise ValueError(f"transaction target is not a regular file: {relative}")
            if existed:
                backup = _internal_path(backup_root, relative)
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
                with backup.open("r+b") as stream:
                    os.fsync(stream.fileno())
            journal["files"].append({
                "path": relative,
                "existed": existed,
                "baseline_sha256": _current_hash(target),
                "candidate_sha256": sha256_bytes(normalized_candidates[relative]),
            })
        journal["state"] = "prepared"
        _write_journal(transaction, journal)
        journal["state"] = "committing"
        _write_journal(transaction, journal)
        order = sorted(normalized_candidates, key=lambda item: (item == "project-state.json", item))
        for relative in order:
            target = safe_project_path(project_root, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(_internal_path(staged_root, relative), target)
            _fsync_directory(target.parent)
        journal["state"] = "committed"
        _write_journal(transaction, journal)
        shutil.rmtree(transaction)
        _fsync_directory(project_root)
    except Exception:
        rollback_transaction(project_root, transaction)
        raise


def _active_lock_pid(lock_path: Path) -> int | None:
    try:
        content = lock_path.read_text(encoding="ascii", errors="ignore")
    except FileNotFoundError:
        return None
    match = re.search(r"(?m)^pid=(\d+)$", content)
    if not match:
        return None
    pid = int(match.group(1))
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except PermissionError:
        return pid
    except OSError:
        return None
    return pid


@contextmanager
def project_lock(root: Path | str, timeout: float | None = 30.0) -> Iterator[None]:
    project_root = Path(root).resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    lock_path = project_root / LOCK_FILE
    deadline = None if timeout is None else time.monotonic() + timeout
    token = uuid.uuid4().hex
    payload = f"pid={os.getpid()}\ntoken={token}\n".encode("ascii")
    while True:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
            except FileNotFoundError:
                continue
            if age >= 2.0 and _active_lock_pid(lock_path) is None:
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass
                continue
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(f"timed out waiting for project lock: {lock_path}")
            time.sleep(0.05)
            continue
        try:
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        break
    try:
        yield
    finally:
        try:
            content = lock_path.read_text(encoding="ascii", errors="ignore")
        except FileNotFoundError:
            content = ""
        if content and f"token={token}\n" in content:
            lock_path.unlink(missing_ok=True)


class ProjectStore:
    """Project-scoped facade used by mutating CLIs."""

    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()

    @contextmanager
    def locked(self, timeout: float | None = 30.0) -> Iterator["ProjectStore"]:
        with project_lock(self.root, timeout=timeout):
            recover_transaction(self.root)
            yield self

    def path(self, relative: str | os.PathLike[str]) -> Path:
        return safe_project_path(self.root, relative)

    def relative_path(self, path: str | os.PathLike[str], *, allow_absolute: bool = False) -> str:
        return project_relative_path(self.root, path, allow_absolute=allow_absolute)

    def capture_baseline(self, paths: list[str] | tuple[str, ...] | set[str]) -> dict[str, str | None]:
        return capture_baseline(self.root, paths)

    def commit(
        self,
        candidates: Mapping[str, bytes],
        *,
        baseline: Mapping[str, str | None] | None = None,
    ) -> None:
        commit_files(self.root, candidates, baseline=baseline)

    def commit_json(
        self,
        candidates: Mapping[str, Any],
        *,
        baseline: Mapping[str, str | None] | None = None,
    ) -> None:
        self.commit({path: json_bytes(data) for path, data in candidates.items()}, baseline=baseline)


def recover_project(root: Path | str, timeout: float | None = 30.0) -> bool:
    with project_lock(root, timeout=timeout):
        return recover_transaction(root)


def commit_project(
    root: Path | str,
    candidates: Mapping[str, bytes],
    *,
    baseline: Mapping[str, str | None] | None = None,
    timeout: float | None = 30.0,
) -> None:
    store = ProjectStore(root)
    with store.locked(timeout=timeout):
        store.commit(candidates, baseline=baseline)
