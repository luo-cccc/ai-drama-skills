from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import project_store
from tests.helpers import tree_hashes


STATE_CLI = SCRIPTS / "state_cli.py"


def run_state(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(STATE_CLI), *args],
        check=check,
        capture_output=True,
        text=True,
    )


class ProjectStoreTests(unittest.TestCase):
    def test_safe_project_paths_reject_escape_absolute_and_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            root.mkdir()
            unsafe = (
                "../outside.json",
                "nested/../../outside.json",
                "/tmp/outside.json",
                "C:/outside.json",
                ".short-drama-transaction/journal.json",
                ".short-drama.lock",
            )
            for value in unsafe:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    project_store.safe_project_path(root, value)
            self.assertEqual(
                root / "nested" / "state.json",
                project_store.safe_project_path(root, "nested/state.json"),
            )

    def test_commit_rejects_changed_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            root.mkdir()
            target = root / "state.json"
            target.write_bytes(b"baseline\n")
            store = project_store.ProjectStore(root)
            baseline = store.capture_baseline(["state.json"])
            target.write_bytes(b"concurrent\n")
            with store.locked(), self.assertRaises(project_store.ConcurrentModificationError):
                store.commit({"state.json": b"candidate\n"}, baseline=baseline)
            self.assertEqual(b"concurrent\n", target.read_bytes())
            self.assertFalse((root / project_store.TRANSACTION_DIR).exists())

    def test_commit_rolls_back_all_files_after_partial_replace(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            root.mkdir()
            first = root / "first.json"
            second = root / "second.json"
            first.write_bytes(b"old-first\n")
            second.write_bytes(b"old-second\n")
            store = project_store.ProjectStore(root)
            baseline = store.capture_baseline(["first.json", "second.json"])
            original_replace = project_store.os.replace
            failed = False

            def fail_second_staged_replace(source, target):
                nonlocal failed
                source_path = Path(source)
                target_path = Path(target)
                if not failed and target_path == second and "staged" in source_path.parts:
                    failed = True
                    raise OSError("injected replacement failure")
                return original_replace(source, target)

            with store.locked(), mock.patch.object(
                project_store.os, "replace", side_effect=fail_second_staged_replace
            ):
                with self.assertRaises(OSError):
                    store.commit(
                        {"first.json": b"new-first\n", "second.json": b"new-second\n"},
                        baseline=baseline,
                    )
            self.assertEqual(b"old-first\n", first.read_bytes())
            self.assertEqual(b"old-second\n", second.read_bytes())
            self.assertFalse((root / project_store.TRANSACTION_DIR).exists())

    def test_recover_restores_interrupted_transaction(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            root.mkdir()
            target = root / "state.json"
            target.write_bytes(b"partially-committed\n")
            transaction = root / project_store.TRANSACTION_DIR
            backup = transaction / "backups" / "state.json"
            backup.parent.mkdir(parents=True)
            backup.write_bytes(b"original\n")
            (transaction / project_store.JOURNAL_FILE).write_text(
                json.dumps({
                    "schema_version": "1.0",
                    "state": "committing",
                    "files": [{"path": "state.json", "existed": True}],
                }),
                encoding="utf-8",
            )
            self.assertTrue(project_store.recover_project(root))
            self.assertEqual(b"original\n", target.read_bytes())
            self.assertFalse(transaction.exists())

    def test_concurrent_cli_mutations_do_not_lose_allocations(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            run_state("init", "--project-dir", str(project), "--title", "Test", "--slug", "test")
            processes = [
                subprocess.Popen(
                    [
                        sys.executable,
                        str(STATE_CLI),
                        "allocate-id",
                        "--project-dir",
                        str(project),
                        "--type",
                        "character",
                        "--name",
                        f"Character {index}",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for index in range(8)
            ]
            results = [process.communicate(timeout=30) + (process.returncode,) for process in processes]
            self.assertTrue(all(returncode == 0 for _, _, returncode in results), results)
            manifest = json.loads((project / "asset-manifest.json").read_text(encoding="utf-8"))
            ids = [item["asset_id"] for item in manifest["assets"]]
            self.assertEqual([f"CHAR-{index:03d}" for index in range(1, 9)], sorted(ids))
            self.assertEqual(9, manifest["manifest_version"])

    def test_state_cli_rejects_incomplete_registrations(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            run_state("init", "--project-dir", str(project), "--title", "Test", "--slug", "test")
            no_source_path = run_state(
                "register-source", "--project-dir", str(project),
                "--kind", "complete-story", check=False,
            )
            self.assertNotEqual(0, no_source_path.returncode)
            missing_artifact = run_state(
                "register-artifact", "--project-dir", str(project),
                "--type", "screenplay", "--path", "missing.md", check=False,
            )
            self.assertNotEqual(0, missing_artifact.returncode)
            empty_checkpoint = run_state(
                "checkpoint", "--project-dir", str(project), "--stage", "brief",
                "--decision", "confirmed", "--authorization", "test", check=False,
            )
            self.assertNotEqual(0, empty_checkpoint.returncode)
            state = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
            self.assertEqual([], state["sources"])
            self.assertEqual([], state["artifacts"])
            self.assertEqual([], state["checkpoints"])
            self.assertEqual(1, state["project_revision"])

    def test_v2_init_and_source_defaults(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            run_state("init", "--project-dir", str(project), "--title", "Test", "--slug", "test")
            source_path = project / "story.md"
            source_path.write_text("story\n", encoding="utf-8")
            run_state(
                "register-source", "--project-dir", str(project),
                "--kind", "complete-story", "--path", "story.md",
            )
            state = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
            self.assertEqual("2.0", state["schema_version"])
            self.assertEqual(2, state["project_revision"])
            configuration = state["configuration"]
            self.assertFalse(configuration["delivery_required"])
            self.assertTrue(configuration["prompt_context_required"])
            self.assertEqual("zh-CN", configuration["report_language"])
            self.assertEqual("untrusted-content", state["sources"][0]["trust_status"])
            self.assertEqual({"status": "unknown"}, state["sources"][0]["rights"])

    def test_migrate_project_dry_run_then_apply(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            project.mkdir()
            state_path = project / "project-state.json"
            screenplay = project / "screenplay.json"
            screenplay.write_text('{"episode":1}\n', encoding="utf-8")
            screenplay_hash = hashlib.sha256(screenplay.read_bytes()).hexdigest()
            bad = project / "audit.md"
            bad.write_text("changed after registration\n", encoding="utf-8")
            versioned_bad = project / "outline-v001.json"
            versioned_bad.write_text("tampered versioned artifact\n", encoding="utf-8")
            original = {
                "schema_version": "1.0",
                "project": {"locale": "zh-CN"},
                "stage": "intake",
                "configuration": {},
                "sources": [{"source_id": "SRC-001"}],
                "artifacts": [
                    {
                        "artifact_id": "ART-001", "type": "screenplay", "revision": 2,
                        "status": "confirmed", "path": "screenplay.json", "sha256": screenplay_hash,
                    },
                    {
                        "artifact_id": "ART-002", "type": "audit", "revision": 1,
                        "status": "confirmed", "path": "audit.md", "sha256": "0" * 64,
                    },
                    {
                        "artifact_id": "ART-003", "type": "series-outline", "revision": 1,
                        "status": "confirmed", "path": "outline-v001.json", "sha256": "f" * 64,
                    },
                ],
                "checkpoints": [],
            }
            state_path.write_text(json.dumps(original) + "\n", encoding="utf-8")
            dry_run = run_state("migrate-project", "--project-dir", str(project), "--dry-run")
            preview = json.loads(dry_run.stdout)
            self.assertTrue(preview["changed"])
            self.assertTrue(any(item.get("action") == "snapshot" for item in preview["changes"]))
            self.assertTrue(any(item.get("action") == "invalidate" for item in preview["changes"]))
            self.assertEqual(original, json.loads(state_path.read_text(encoding="utf-8")))
            self.assertFalse((project / "screenplay-v002.json").exists())
            run_state("migrate-project", "--project-dir", str(project), "--apply")
            migrated = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual("2.0", migrated["schema_version"])
            self.assertEqual(1, migrated["project_revision"])
            self.assertEqual("zh-CN", migrated["configuration"]["report_language"])
            self.assertTrue(migrated["configuration"]["prompt_context_required"])
            self.assertEqual("untrusted-content", migrated["sources"][0]["trust_status"])
            self.assertEqual({"status": "unknown"}, migrated["sources"][0]["rights"])
            by_id = {item["artifact_id"]: item for item in migrated["artifacts"]}
            self.assertEqual("screenplay-v002.json", by_id["ART-001"]["path"])
            self.assertEqual("confirmed", by_id["ART-001"]["status"])
            self.assertEqual(screenplay.read_bytes(), (project / "screenplay-v002.json").read_bytes())
            self.assertEqual("invalid", by_id["ART-002"]["status"])
            self.assertEqual("invalid", by_id["ART-003"]["status"])
            rerun = run_state("migrate-project", "--project-dir", str(project), "--apply")
            self.assertFalse(json.loads(rerun.stdout)["changed"])

    def test_migrate_project_refuses_conflicting_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            project.mkdir()
            source = project / "screenplay.json"
            source.write_text("source\n", encoding="utf-8")
            (project / "screenplay-v001.json").write_text("conflict\n", encoding="utf-8")
            state = {
                "schema_version": "1.0", "project": {"locale": "en-US"}, "stage": "intake",
                "configuration": {}, "sources": [], "checkpoints": [],
                "artifacts": [{
                    "artifact_id": "ART-001", "type": "screenplay", "revision": 1,
                    "status": "confirmed", "path": "screenplay.json",
                    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                }],
            }
            state_path = project / "project-state.json"
            state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
            before = tree_hashes(project)
            result = run_state("migrate-project", "--project-dir", str(project), "--apply", check=False)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("migration target conflicts", result.stderr)
            self.assertEqual(before, tree_hashes(project))


if __name__ == "__main__":
    unittest.main()
