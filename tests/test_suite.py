from __future__ import annotations

import copy
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock
from pathlib import Path

from tests.helpers import ROOT, SCRIPTS, load_module, sample_plan, tree_hashes, write_audit, write_audit_json, write_json


timeline = load_module("timeline_cli", SCRIPTS / "timeline_cli.py")
validator = load_module("validate_project", SCRIPTS / "validate_project.py")
packager = load_module("package_skills", SCRIPTS / "package_skills.py")
package_verifier = load_module("verify_dist", ROOT / "tests" / "verify_dist.py")
state_cli = load_module("state_cli", SCRIPTS / "state_cli.py")
router = load_module("route_cli", SCRIPTS / "route_cli.py")
media_analysis = load_module("media_analysis_cli", SCRIPTS / "media_analysis_cli.py")
visual_layout = load_module("visual_layout_cli", SCRIPTS / "visual_layout_cli.py")
short_drama = load_module("short_drama_cli", SCRIPTS / "short_drama_cli.py")
project_store = load_module("project_store", SCRIPTS / "project_store.py")
schema_validator = load_module("schema_validator", SCRIPTS / "schema_validator.py")
snapshot_sync = load_module("sync_shuohao_snapshot", SCRIPTS / "sync_shuohao_snapshot.py")


class SkillSuiteTests(unittest.TestCase):
    def test_manifest_and_skills(self):
        manifest = json.loads((ROOT / "skill-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(15, len(manifest["skills"]))
        self.assertEqual(15, len({item["name"] for item in manifest["skills"]}))
        shared = {path.name for path in (ROOT / "shared" / "references").glob("*.md")}
        display_names = []
        for entry in manifest["skills"]:
            skill_dir = ROOT / "src" / "skills" / entry["name"]
            text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            self.assertLessEqual(len(text.splitlines()), 250)
            self.assertNotIn("TODO", text)
            self.assertRegex(text, rf"\A---\nname: {re.escape(entry['name'])}\n")
            yaml = (skill_dir / "agents" / "openai.yaml").read_text(encoding="utf-8")
            self.assertIn(f"${entry['name']}", yaml)
            expected_policy = "false" if entry["name"].startswith("ai-drama-short-drama-") or entry["name"] == "ai-drama-screenplay" else "true"
            self.assertIn(f"allow_implicit_invocation: {expected_policy}", yaml)
            display_match = re.search(r'display_name: "([^"]+)"', yaml)
            self.assertIsNotNone(display_match)
            display_names.append(display_match.group(1))
            match = re.search(r'short_description: "([^"]+)"', yaml)
            self.assertIsNotNone(match)
            self.assertGreaterEqual(len(match.group(1)), 25)
            self.assertLessEqual(len(match.group(1)), 64)
            self.assertTrue(set(entry["shared_references"]) <= shared)
            self.assertTrue(all((ROOT / "schemas" / name).is_file() for name in entry.get("schemas", [])))
        self.assertEqual(15, len(set(display_names)))
        self.assertTrue(all(name.startswith("AI ") and "AI Drama" not in name for name in display_names))

    def test_no_stale_or_overfit_rules(self):
        corpus = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "src" / "skills").rglob("*.md"))
        for forbidden in ["Step 1b", "Step 5a", "Step 5b", "作为世界级", "最后一行严格写为"]:
            self.assertNotIn(forbidden, corpus)

    def test_packaging_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / "first"
            second = Path(temp) / "second"
            packager.build(first)
            packager.build(second)
            self.assertEqual(tree_hashes(first), tree_hashes(second))
            for skill in [path for path in first.iterdir() if path.is_dir()]:
                self.assertFalse((skill / "README.md").exists())
                if (skill / "scripts" / "validate_project.py").exists():
                    self.assertTrue(
                        (skill / "scripts" / "timeline_cli.py").exists(),
                        f"{skill.name} is missing validate_project's timeline dependency",
                    )
                    self.assertTrue(
                        (skill / "scripts" / "schema_validator.py").exists(),
                        f"{skill.name} is missing validate_project's schema dependency",
                    )
                manifest_entry = next(
                    item for item in json.loads((ROOT / "skill-manifest.json").read_text(encoding="utf-8"))["skills"]
                    if item["name"] == skill.name
                )
                for schema in manifest_entry.get("schemas", []):
                    self.assertTrue((skill / "schemas" / schema).is_file(), f"{skill.name} is missing {schema}")
                if skill.name.startswith("ai-drama-short-drama"):
                    self.assertTrue((skill / "engine" / "shuohao-runtime" / "FORGING-ADAPTATION.json").is_file())
                    self.assertTrue((skill / "THIRD_PARTY_LICENSES" / "shuohao-LICENSE").is_file())
                    self.assertTrue((skill / "THIRD_PARTY_NOTICES" / "shuohao-NOTICE").is_file())
                    self.assertTrue((skill / "THIRD_PARTY_NOTICES" / "shuohao-MODIFICATIONS.md").is_file())
                if skill.name.startswith("ai-drama-short-drama-"):
                    self.assertTrue((skill / "references" / "shuohao" / "workflow.md").is_file())
                    self.assertTrue((skill / "references" / "short-drama-prompt-governance.md").is_file())

    def test_standard_skills_repository_matches_canonical_build(self):
        installed = ROOT / ".agents" / "skills"
        self.assertEqual([], package_verifier.verify(installed))
        with tempfile.TemporaryDirectory() as temp:
            rebuilt = Path(temp) / "skills"
            packager.build(rebuilt)
            self.assertEqual(tree_hashes(rebuilt), tree_hashes(installed))

    def test_packaging_preserves_existing_output_when_swap_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "release"
            packager.build(output)
            before = tree_hashes(output)
            with mock.patch.object(packager.os, "replace", side_effect=PermissionError("busy")):
                with self.assertRaises(PermissionError):
                    packager.build(output)
            self.assertEqual(before, tree_hashes(output))
            self.assertEqual([], list(Path(temp).glob(".release.*")))

    def test_vendor_mapping_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "skill"
            target.mkdir()
            with self.assertRaises(ValueError):
                packager.copy_vendor_mapping({"source": "../outside", "target": "vendor/file"}, target)
            with self.assertRaises(ValueError):
                packager.copy_vendor_mapping({"source": "README.md", "target": "../escape"}, target)

    def test_routing_fixture_coverage(self):
        data = json.loads((ROOT / "tests" / "routing-cases.json").read_text(encoding="utf-8"))
        skills = {case["expected_skill"] for case in data["cases"]}
        expected = {item["name"] for item in json.loads((ROOT / "skill-manifest.json").read_text(encoding="utf-8"))["skills"]}
        self.assertEqual(expected, skills)
        self.assertEqual(len(data["cases"]), len({case["id"] for case in data["cases"]}))
        self.assertTrue(any(case.get("expected_fallback") == "prompt-only" for case in data["cases"]))
        for case in data["cases"]:
            actual = router.route_request(case["prompt"], case.get("mode") == "project")
            self.assertEqual(case["expected_skill"], actual["skill"], case["id"])
            self.assertEqual(case["mode"], actual["mode"], case["id"])
            if "expected_fallback" in case:
                self.assertEqual(case["expected_fallback"], actual.get("fallback"), case["id"])
            if "evidence" in case:
                self.assertEqual(case["evidence"], actual.get("evidence"), case["id"])

    def test_two_stage_requests_route_to_orchestrator(self):
        for prompt in ("请写剧本并做分镜", "write the screenplay and storyboard it"):
            routed = router.route_request(prompt)
            self.assertEqual("ai-drama-forging", routed["skill"])

    def test_timeline_durations_and_segmentation(self):
        for seconds in [4, 15, 30, 90, 135, 150, 180, 181]:
            plan = sample_plan(seconds * 1000)
            self.assertEqual([], timeline.validate_plan(plan), seconds)
            clips = timeline.segment_plan(plan)
            self.assertEqual(0, clips[0]["start_ms"])
            self.assertEqual(seconds * 1000, clips[-1]["end_ms"])
            self.assertTrue(all(clip["end_ms"] - clip["start_ms"] <= 30000 for clip in clips))
            self.assertEqual(0, clips[0]["relative_shots"][0]["relative_start_ms"])

    def test_timeline_preserves_production_fields_and_rejects_impossible_dialogue(self):
        plan = sample_plan(5000)
        plan["shots"][0].update({"performance": "停顿后抬眼", "dialogue": "我到了。", "sound": "门轴声"})
        self.assertEqual([], timeline.validate_plan(plan))
        rendered = timeline.render_markdown(plan)
        for value in ["Performance", "Dialogue", "Sound", "停顿后抬眼", "我到了。", "门轴声"]:
            self.assertIn(value, rendered)
        plan["shots"][0]["dialogue"] = "这段对白不可能在当前时长内自然完成。" * 20
        self.assertTrue(any("dialogue needs about" in error for error in timeline.validate_plan(plan)))

    def test_illegal_long_beat_is_rejected(self):
        plan = sample_plan(31000)
        plan["shots"] = [{**plan["shots"][0], "end_ms": 31000}]
        plan["beats"] = plan["beats"][:1]
        with self.assertRaises(timeline.TimelineError):
            timeline.segment_plan(plan)

    def test_timeline_rejects_duplicate_and_noncontiguous_references(self):
        duplicate = sample_plan(60000)
        duplicate["beats"][1]["beat_id"] = "BEAT-001"
        duplicate["shots"][1]["beat_id"] = "BEAT-001"
        self.assertTrue(any("duplicate beat_id" in error for error in timeline.validate_plan(duplicate)))

        unknown_scene = sample_plan(4000)
        unknown_scene["shots"][0]["scene_id"] = "SCN-999"
        self.assertTrue(any("unknown scene" in error for error in timeline.validate_plan(unknown_scene)))

        noncontiguous = sample_plan(90000)
        noncontiguous["shots"][2]["beat_id"] = "BEAT-001"
        self.assertTrue(any("not contiguous" in error for error in timeline.validate_plan(noncontiguous)))

    def test_scoped_timeline_and_generation_groups(self):
        plan = sample_plan(60000)
        plan["target_runtime_ms"] = 360000
        plan["scope"] = {"kind": "episodes", "start": 2, "end": 2}
        plan["timeline_start_ms"] = 120000
        plan["timeline_end_ms"] = 180000
        for index, shot in enumerate(plan["shots"], start=1):
            shot["start_ms"] += 120000
            shot["end_ms"] += 120000
            shot["generation_group"] = f"E02-{index:02d}"
        self.assertEqual([], timeline.validate_plan(plan))
        clips = timeline.segment_plan(plan)
        self.assertEqual(["E02-01", "E02-02"], [item["generation_group"] for item in clips])
        broken = copy.deepcopy(plan)
        broken["shots"][1]["generation_group"] = "E02-01"
        with self.assertRaises(timeline.TimelineError):
            timeline.segment_plan(broken)
        noncontiguous = copy.deepcopy(plan)
        noncontiguous["shots"].append(copy.deepcopy(noncontiguous["shots"][-1]))
        noncontiguous["shots"][-1]["shot_id"] = "SHOT-003"
        noncontiguous["shots"][-1]["beat_id"] = "BEAT-001"
        noncontiguous["shots"][-1]["start_ms"] = 180000
        noncontiguous["shots"][-1]["end_ms"] = 190000
        noncontiguous["shots"][-1]["generation_group"] = "E02-01"
        noncontiguous["timeline_end_ms"] = 190000
        self.assertTrue(any("generation group" in error for error in timeline.validate_plan(noncontiguous)))

    def test_state_cli_manifest_version_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            run = lambda *args: subprocess.run([sys.executable, str(SCRIPTS / "state_cli.py"), *args], check=True, capture_output=True, text=True)
            run("init", "--project-dir", str(project), "--title", "Test", "--slug", "test")
            run("allocate-id", "--project-dir", str(project), "--type", "character", "--name", "A")
            run("allocate-id", "--project-dir", str(project), "--type", "character", "--name", "B")
            run("allocate-variant", "--project-dir", str(project), "--base-asset-id", "CHAR-001", "--name", "A raincoat")
            manifest = json.loads((project / "asset-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(4, manifest["manifest_version"])
            self.assertEqual(["CHAR-001", "CHAR-002", "CHAR-001-V01"], [item["asset_id"] for item in manifest["assets"]])
            candidate = copy.deepcopy(manifest)
            candidate["manifest_version"] = 5
            candidate["assets"][0]["visual_dna"] = {"anchors": ["oval face"]}
            candidate_path = project / "candidate-manifest.json"
            write_json(candidate_path, candidate)
            run(
                "apply-manifest", "--project-dir", str(project), "--input", str(candidate_path),
                "--expected-version", "4",
            )
            manifest = json.loads((project / "asset-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(5, manifest["manifest_version"])
            self.assertEqual({"anchors": ["oval face"]}, manifest["assets"][0]["visual_dna"])
            self.assertFalse(list(project.glob("*.tmp")))

    def test_state_cli_resolves_relative_source_from_project_root(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            run = lambda *args: subprocess.run(
                [sys.executable, str(SCRIPTS / "state_cli.py"), *args],
                check=True,
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            run("init", "--project-dir", str(project), "--title", "Test", "--slug", "test")
            (project / "source-story.md").write_text("fixture\n", encoding="utf-8")
            run(
                "register-source",
                "--project-dir", str(project),
                "--kind", "complete-story",
                "--path", "source-story.md",
                "--availability", "available",
                "--authority", "canonical",
            )
            state = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
            self.assertEqual("source-story.md", state["sources"][0]["path"])
            self.assertEqual(
                hashlib.sha256((project / "source-story.md").read_bytes()).hexdigest(),
                state["sources"][0]["sha256"],
            )

    def test_state_cli_checkpointed_confirmation_and_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            run = lambda *args, check=True: subprocess.run(
                [sys.executable, str(SCRIPTS / "state_cli.py"), *args],
                check=check, capture_output=True, text=True,
            )
            run("init", "--project-dir", str(project), "--title", "Test", "--slug", "test")
            run(
                "configure", "--project-dir", str(project), "--target-runtime-ms", "15000",
                "--scene-count", "5", "--automatic-authorization", "true",
            )
            (project / "production-brief-v001.md").write_text("# Brief\n", encoding="utf-8")
            run(
                "register-artifact", "--project-dir", str(project), "--type", "production-brief",
                "--path", "production-brief-v001.md", "--status", "pending-confirmation",
            )
            failed = run(
                "set-artifact-status", "--project-dir", str(project), "--artifact-id", "ART-001",
                "--status", "confirmed", check=False,
            )
            self.assertNotEqual(0, failed.returncode)
            run(
                "checkpoint", "--project-dir", str(project), "--stage", "brief",
                "--decision", "confirmed", "--authorization", "fixture approval", "--affects", "ART-001",
            )
            run(
                "set-artifact-status", "--project-dir", str(project), "--artifact-id", "ART-001",
                "--status", "confirmed",
            )
            state = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
            self.assertEqual(15000, state["project"]["target_runtime_ms"])
            self.assertEqual("SCN-005", state["project"]["scene_ids"][-1])
            self.assertTrue(state["configuration"]["automatic_authorization"])
            self.assertEqual("confirmed", state["artifacts"][0]["status"])

    def test_state_cli_continuity_chain_and_atomic_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            run = lambda *args: subprocess.run(
                [sys.executable, str(SCRIPTS / "state_cli.py"), *args],
                check=True, capture_output=True, text=True,
            )
            run("init", "--project-dir", str(project), "--title", "Test", "--slug", "test")
            run("configure", "--project-dir", str(project), "--scene-count", "1")
            run("allocate-id", "--project-dir", str(project), "--type", "prop", "--name", "Cup")
            run("record-event", "--project-dir", str(project), "--scope", "scene-1", "--asset-id", "PROP-001",
                "--field", "owner", "--before", '"A"', "--after", '"B"', "--evidence-ref", "fixture",
                "--scene-ref", "SCN-001")
            ledger = json.loads((project / "continuity-ledger.json").read_text(encoding="utf-8"))
            scope = ledger["scopes"][0]
            self.assertEqual("A", scope["start_snapshot"]["PROP-001"]["owner"])
            self.assertEqual("B", scope["end_snapshot"]["PROP-001"]["owner"])
            failed = subprocess.run([
                sys.executable, str(SCRIPTS / "state_cli.py"), "record-event", "--project-dir", str(project),
                "--scope", "scene-1", "--asset-id", "PROP-001", "--field", "owner",
                "--before", '"wrong"', "--after", '"C"', "--evidence-ref", "fixture",
            ], capture_output=True, text=True)
            self.assertNotEqual(0, failed.returncode)

            target = project / "atomic-test.json"
            with mock.patch.object(state_cli.os, "replace", side_effect=OSError("fixture failure")):
                with self.assertRaises(OSError):
                    state_cli.atomic_write(target, {"ok": True})
            self.assertFalse(list(project.glob(".atomic-test.json.*.tmp")))

    def test_contract_failure_modes(self):
        root = ROOT / "examples" / "synthetic-short"
        state = json.loads((root / "project-state.json").read_text(encoding="utf-8"))
        assets = json.loads((root / "asset-manifest.json").read_text(encoding="utf-8"))
        ledger = json.loads((root / "continuity-ledger.json").read_text(encoding="utf-8"))
        refs = {item["source_id"] for item in state["sources"]} | {item["artifact_id"] for item in state["artifacts"]}
        asset_ids = {item["asset_id"] for item in assets["assets"]}

        missing = copy.deepcopy(state)
        del missing["configuration"]["audio_policy"]
        errors: list[str] = []
        validator.validate_state(root, missing, errors)
        self.assertTrue(any("configuration missing keys" in error for error in errors))

        bad_revision = copy.deepcopy(state)
        bad_revision["artifacts"][4]["revision"] = 1
        errors = []
        validator.validate_state(root, bad_revision, errors)
        self.assertTrue(any("revisions for screenplay" in error for error in errors))

        mismatched_audit = copy.deepcopy(state)
        mismatched_audit["artifacts"][2]["status"] = "confirmed"
        mismatched_audit["artifacts"][7]["depends_on"] = ["ART-003", "ART-006"]
        errors = []
        validator.validate_state(root, mismatched_audit, errors)
        self.assertTrue(any("audit does not cover" in error for error in errors))

        bad_assets = copy.deepcopy(assets)
        bad_assets["assets"][3]["evidence"][0]["level"] = "inferred"
        bad_assets["assets"].append(copy.deepcopy(bad_assets["assets"][0]))
        errors = []
        validator.validate_assets(bad_assets, "PROJECT-001", refs, errors)
        self.assertTrue(any("locked fields lack confirmed evidence" in error for error in errors))
        self.assertTrue(any("duplicate asset ID" in error for error in errors))

        bad_ledger = copy.deepcopy(ledger)
        bad_ledger["scopes"][0]["events"][0]["before"] = "wrong"
        bad_ledger["scopes"][0]["end_snapshot"]["PROP-001"]["owner"] = "wrong"
        errors = []
        scene_ids = set(state["project"]["scene_ids"])
        validator.validate_ledger(bad_ledger, "PROJECT-001", asset_ids, scene_ids, {"SHOT-001", "SHOT-002", "SHOT-003"}, errors)
        self.assertTrue(any("chain mismatch" in error for error in errors))
        self.assertTrue(any("end_snapshot" in error for error in errors))

    def test_confirmation_and_upstream_gates(self):
        root = ROOT / "examples" / "synthetic-short"
        state = json.loads((root / "project-state.json").read_text(encoding="utf-8"))

        no_checkpoints = copy.deepcopy(state)
        no_checkpoints["checkpoints"] = []
        errors: list[str] = []
        validator.validate_state(root, no_checkpoints, errors)
        self.assertTrue(any("lacks an approving" in error for error in errors))

        draft_brief = copy.deepcopy(state)
        draft_brief["artifacts"][0]["status"] = "draft"
        errors = []
        validator.validate_state(root, draft_brief, errors)
        self.assertTrue(any("confirmed production-brief dependency" in error for error in errors))

        conflicting = copy.deepcopy(state)
        conflicting["artifacts"][2]["status"] = "confirmed"
        errors = []
        validator.validate_state(root, conflicting, errors)
        self.assertTrue(any("confirmed screenplay scopes overlap" in error for error in errors))

    def test_disjoint_confirmed_screenplay_scopes_are_allowed(self):
        root = ROOT / "examples" / "synthetic-short"
        state = json.loads((root / "project-state.json").read_text(encoding="utf-8"))
        current = next(item for item in state["artifacts"] if item["artifact_id"] == "ART-005")
        current["scope"] = {"kind": "episodes", "start": 1, "end": 3}
        second = copy.deepcopy(current)
        second.update({"artifact_id": "ART-010", "revision": 3, "scope": {"kind": "episodes", "start": 4, "end": 6}})
        state["artifacts"].append(second)
        state["checkpoints"].append({
            "checkpoint_id": "CHK-007", "stage": "screenplay", "decision": "confirmed",
            "authorization": "fixture", "sequence": 7, "affects": ["ART-010"],
        })
        errors: list[str] = []
        validator.validate_state(root, state, errors)
        self.assertFalse(any("confirmed screenplay scopes overlap" in error for error in errors), errors)
        second["scope"] = {"kind": "episodes", "start": 3, "end": 4}
        errors = []
        validator.validate_state(root, state, errors)
        self.assertTrue(any("confirmed screenplay scopes overlap" in error for error in errors))

    def test_attach_rejects_confirmed_screenplay_without_mutation(self):
        source = ROOT / "examples" / "synthetic-short"
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            shutil.copytree(source, project)
            before = tree_hashes(project)
            completed = subprocess.run([
                sys.executable, str(SCRIPTS / "short_drama_cli.py"), "attach",
                "--project-dir", str(project), "--episodes", "6", "--episode-seconds", "120",
                "--genre", "suspense", "--authorization", "fixture",
            ], capture_output=True, text=True)
            self.assertNotEqual(0, completed.returncode)
            self.assertEqual(before, tree_hashes(project))

    def test_crosswalk_is_append_only_and_retired_ids_are_not_reused(self):
        engine = {"mappings": {"characters": [], "scenes": [], "props": [], "scene_occurrences": [], "storyboard": []}}
        first = short_drama.register_mapping(engine, "characters", "C01", "A", "CHAR")
        short_drama.retire_missing(engine, "characters", set())
        second = short_drama.register_mapping(engine, "characters", "C02", "B", "CHAR")
        rerun = short_drama.register_mapping(engine, "characters", "C02", "B", "CHAR")
        self.assertEqual("CHAR-001", first)
        self.assertEqual("CHAR-002", second)
        self.assertEqual(second, rerun)
        self.assertEqual("retired", engine["mappings"]["characters"][0]["status"])

    def test_outline_character_mapping_uses_names_not_cast_order(self):
        engine = {"mappings": {"characters": [], "scenes": [], "props": [], "scene_occurrences": [], "storyboard": []}}
        manifest = {"assets": []}
        second = short_drama.allocate_character_asset(manifest, "Second", [])
        first = short_drama.allocate_character_asset(manifest, "First", [])
        short_drama.reconcile_outline_characters(engine, manifest, {
            "characters": [{"id": "C01", "name": "First"}, {"id": "C02", "name": "Second"}],
        }, "ART-001")
        mappings = {item["upstream_id"]: item["forging_id"] for item in engine["mappings"]["characters"]}
        self.assertEqual(first, mappings["C01"])
        self.assertEqual(second, mappings["C02"])

    def test_cast_id_for_bound_name_fails_instead_of_minting_duplicate_asset(self):
        engine = {"mappings": {"characters": [], "scenes": [], "props": [], "scene_occurrences": [], "storyboard": []}}
        manifest = {"assets": [
            {"asset_id": "CHAR-001", "type": "character", "name": "A", "aliases": [], "lock_status": "unlocked", "locked_fields": [], "evidence": [], "visual_dna": {}},
        ]}
        engine["mappings"]["characters"].append({"upstream_id": "C01", "forging_id": "CHAR-001", "name": "A", "status": "active"})
        with self.assertRaises(ValueError):
            short_drama.register_mapping(engine, "characters", "Z01", "A", "CHAR", manifest)
        self.assertEqual(["C01"], [item["upstream_id"] for item in engine["mappings"]["characters"]])

    def test_cast_id_adopts_unbound_asset_by_name(self):
        engine = {"mappings": {"characters": [], "scenes": [], "props": [], "scene_occurrences": [], "storyboard": []}}
        manifest = {"assets": [
            {"asset_id": "CHAR-001", "type": "character", "name": "A", "aliases": [], "lock_status": "unlocked", "locked_fields": [], "evidence": [], "visual_dna": {}},
        ]}
        asset_id = short_drama.register_mapping(engine, "characters", "C01", "A", "CHAR", manifest)
        self.assertEqual("CHAR-001", asset_id)
        self.assertEqual([("C01", "CHAR-001")], [(item["upstream_id"], item["forging_id"]) for item in engine["mappings"]["characters"]])

    def test_audit_import_requires_exact_target_and_evidence_tables(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "audit.md"
            write_audit(path, screenplay_ids=["ART-001"], scope={"kind": "episodes", "start": 1, "end": 3})
            body, result = short_drama.load_audit_report(
                path, ["ART-001"], {"kind": "episodes", "start": 1, "end": 3}
            )
            self.assertTrue(body)
            self.assertEqual("pass", result["decision"])
            with self.assertRaises(ValueError):
                short_drama.load_audit_report(path, ["ART-002"], {"kind": "episodes", "start": 1, "end": 3})

    def test_v2_audit_derives_counts_and_rejects_empty_evidence(self):
        valid = {
            "schema_version": "2.0", "mode": "conformance",
            "scope": {"kind": "episodes", "start": 1, "end": 1},
            "targets": [{"artifact_id": "ART-001", "path": "screenplay-v001.json", "sha256": "a" * 64}],
            "basis": [{"kind": "screenplay", "ref": "ART-001", "sha256": "a" * 64, "availability": "available"}],
            "findings": [],
            "required_elements": [{
                "element_id": "REQ-001", "requirement": "core event", "source_ref": "ART-001", "result": "pass",
                "evidence": [{"source_ref": "ART-001", "locator": "E01", "quote": "event", "evidence_status": "observed"}],
            }],
            "differences": [], "decision": "pass", "limitations": [],
        }
        schema = json.loads((ROOT / "schemas" / "audit-report.schema.json").read_text(encoding="utf-8"))
        self.assertEqual([], schema_validator.validate_instance(valid, schema, "audit"))
        self.assertEqual(1, short_drama.derive_audit_result(valid)["required_elements_passed"])
        broken = copy.deepcopy(valid)
        broken["required_elements"][0]["evidence"] = []
        self.assertTrue(schema_validator.validate_instance(broken, schema, "audit"))
        with self.assertRaisesRegex(ValueError, "canonical JSON audit"):
            short_drama.audit_output_extension({"schema_version": "2.0"}, Path("audit.md"))
        self.assertEqual("json", short_drama.audit_output_extension({"schema_version": "2.0"}, Path("audit.json")))
        self.assertEqual("md", short_drama.audit_output_extension({"schema_version": "1.0"}, Path("audit.md")))

    def test_schema_validator_executes_engine_contract(self):
        schema = json.loads((ROOT / "schemas" / "short-drama-engine.schema.json").read_text(encoding="utf-8"))
        engine = {
            "schema_version": "1.0", "project_id": "PROJECT-001",
            "engine_snapshot": {"upstream": "x", "adaptation_version": "1", "manifest_sha256": "a" * 64},
            "profile": {
                "episode_count": 1, "episode_duration_ms": 1000, "genre": "x",
                "adaptation_mode": "core-extraction", "report_language": "zh", "prompt_language": "fr",
                "style": "realistic", "generator": "minimax-h3",
                "h3": {"max_segment_ms": 15000, "dialogue_tag": "<d>[Chinese]"},
            },
            "attachment": {"mode": "new", "status": "attached"},
            "mappings": {"characters": [], "scenes": [], "props": [], "scene_occurrences": [], "storyboard": []},
        }
        errors = schema_validator.validate_instance(engine, schema, "engine")
        self.assertTrue(any("prompt_language" in error for error in errors), errors)

    def test_short_drama_complete_cannot_bypass_specialized_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            subprocess.run([
                sys.executable, str(SCRIPTS / "state_cli.py"), "init", "--project-dir", str(project),
                "--title", "Complete", "--slug", "complete",
            ], check=True, capture_output=True, text=True)
            write_json(project / "short-drama-engine.json", {})
            completed = subprocess.run([
                sys.executable, str(SCRIPTS / "state_cli.py"), "set-stage", "--project-dir", str(project),
                "--stage", "complete",
            ], capture_output=True, text=True)
            self.assertNotEqual(0, completed.returncode)
            state = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
            self.assertNotEqual("complete", state["stage"])

    def test_recover_refuses_to_remove_active_process_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / short_drama.LOCK_FILE).write_text(f"pid={os.getpid()}\n", encoding="ascii")
            with self.assertRaises(RuntimeError):
                short_drama.command_recover(types.SimpleNamespace(project_dir=str(project)))
            self.assertTrue((project / short_drama.LOCK_FILE).exists())

    def test_snapshot_group_install_rolls_back_prior_replacement(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "first"
            second = root / "second"
            stage = root / "stage"
            first.mkdir(); second.mkdir(); stage.mkdir()
            (first / "value.txt").write_text("old-first", encoding="utf-8")
            (second / "value.txt").write_text("old-second", encoding="utf-8")
            (stage / "value.txt").write_text("new-first", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                snapshot_sync.install_replacements([(stage, first), (root / "missing-stage", second)])
            self.assertEqual("old-first", (first / "value.txt").read_text(encoding="utf-8"))
            self.assertEqual("old-second", (second / "value.txt").read_text(encoding="utf-8"))

    def test_adapted_documentation_overlays_are_reproducible(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "adapted"
            destination.mkdir()
            snapshot_sync.apply_adapted_overlays(destination)
            for relative in snapshot_sync.ADAPTED_OVERLAY_FILES:
                source = ROOT / "engine" / "shuohao-adapted" / relative
                copied = destination / relative
                self.assertTrue(copied.is_file(), relative)
                self.assertEqual(source.read_bytes(), copied.read_bytes(), relative)

    def test_shuohao_snapshot_check(self):
        manifest = json.loads((ROOT / "vendor" / "shuohao" / "snapshot-manifest.json").read_text(encoding="utf-8"))
        runtime = ROOT / "engine" / "shuohao-runtime"
        actual = {
            path.relative_to(runtime).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in runtime.rglob("*") if path.is_file()
        }
        self.assertEqual(manifest["runtime_files"], actual)
        adapted = ROOT / "engine" / "shuohao-adapted" / "skills"
        for skill in manifest["skills"]:
            subprocess.run([
                "node", str(adapted / skill / "scripts" / "selftest.mjs"),
            ], check=True, capture_output=True, text=True)

    def test_dukou_governed_pipeline_through_scoped_storyboard(self):
        engine_root = ROOT / "engine" / "shuohao-adapted" / "skills"
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "dukou"
            run_state = lambda *items: subprocess.run(
                [sys.executable, str(SCRIPTS / "state_cli.py"), *items],
                check=True, capture_output=True, text=True,
            )
            def run_short(*items):
                completed = subprocess.run(
                    [sys.executable, str(SCRIPTS / "short_drama_cli.py"), *items],
                    capture_output=True, text=True,
                )
                if completed.returncode:
                    self.fail(completed.stdout + completed.stderr)
                return completed

            def prompt_context(stage, scope="series"):
                completed = run_short(
                    "prompt-context", "--project-dir", str(project), "--stage", stage, "--scope", scope,
                )
                path = project / f"context-{stage}-{scope.replace('-', '_')}.json"
                path.write_text(completed.stdout, encoding="utf-8")
                return str(path)
            run_state("init", "--project-dir", str(project), "--title", "Dukou", "--slug", "dukou")
            source = engine_root / "novel-characters" / "examples" / "渡口.txt"
            shutil.copy2(source, project / "source.txt")
            run_state(
                "register-source", "--project-dir", str(project), "--kind", "complete-story",
                "--path", "source.txt", "--availability", "available", "--authority", "canonical",
            )
            run_short(
                "attach", "--project-dir", str(project), "--episodes", "6", "--episode-seconds", "120",
                "--genre", "period-suspense", "--immutable-core", "开箱翻案与双主角关系",
                "--authorization", "fixture brief approval", "--aspect-ratio", "16:9",
            )
            run_short(
                "import-cast", "--project-dir", str(project),
                "--input", str(engine_root / "novel-characters" / "examples" / "渡口-cast.json"),
                "--source", str(project / "source.txt"), "--prompt-context", prompt_context("characters"),
            )
            outline = engine_root / "novel-outline" / "examples" / "渡口-outline.json"
            run_short(
                "import-outline", "--project-dir", str(project), "--input", str(outline),
                "--kind", "skeleton", "--confirm", "--authorization", "fixture skeleton approval",
                "--prompt-context", prompt_context("outline"),
            )
            run_short(
                "import-outline", "--project-dir", str(project), "--input", str(outline),
                "--kind", "series", "--confirm", "--authorization", "fixture series approval",
                "--prompt-context", prompt_context("outline"),
            )
            run_short(
                "import-art", "--project-dir", str(project),
                "--input", str(engine_root / "novel-art" / "examples" / "渡口-art.json"),
                "--prompt-context", prompt_context("art"),
            )
            script = json.loads((engine_root / "novel-script" / "examples" / "渡口-script.json").read_text(encoding="utf-8"))
            script["episodes"] = script["episodes"][:1]
            batch = project / "batch-e01.json"
            write_json(batch, script)
            before_rejected_import = tree_hashes(project)
            rejected = subprocess.run([
                sys.executable, str(SCRIPTS / "short_drama_cli.py"), "import-script",
                "--project-dir", str(project), "--input", str(batch), "--confirm",
                "--authorization", "fixture screenplay approval",
            ], capture_output=True, text=True)
            self.assertNotEqual(0, rejected.returncode)
            self.assertEqual(before_rejected_import, tree_hashes(project))
            audit_report = project / "audit-e01.json"
            state_before_script = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
            candidate_id = short_drama.next_id(state_before_script["artifacts"], "artifact_id", "ART")
            candidate_revision = short_drama.next_revision(state_before_script, "screenplay")
            candidate_path = short_drama.versioned_path(
                "short-drama/script/E01-E01", "screenplay", candidate_revision, "json"
            )
            candidate_body = short_drama.json_bytes(short_drama.normalize_style_value(script))
            write_audit_json(
                audit_report,
                [{
                    "artifact_id": candidate_id,
                    "path": candidate_path,
                    "sha256": hashlib.sha256(candidate_body).hexdigest(),
                }],
                scope={"kind": "episodes", "start": 1, "end": 1},
            )
            run_short(
                "import-script", "--project-dir", str(project), "--input", str(batch),
                "--confirm", "--authorization", "fixture screenplay approval",
                "--audit-report", str(audit_report), "--prompt-context", prompt_context("script", "1-1"),
            )
            storyboard = json.loads((engine_root / "novel-storyboard" / "examples" / "渡口-storyboard.json").read_text(encoding="utf-8"))
            storyboard["episodes"][0]["segments"][-1]["cuts"][-1]["seconds"] += 1
            storyboard_path = project / "storyboard-e01.json"
            write_json(storyboard_path, storyboard)
            run_short(
                "import-storyboard", "--project-dir", str(project), "--input", str(storyboard_path),
                "--authorization", "fixture storyboard approval", "--prompt-context", prompt_context("storyboard", "1-1"),
            )
            run_short("validate", "--project-dir", str(project))
            state = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
            canonical_audit = next(
                item for item in state["artifacts"]
                if item.get("type") == "audit" and item.get("scope") == {"kind": "episodes", "start": 1, "end": 1}
            )
            self.assertTrue(canonical_audit["path"].endswith(".json"))
            self.assertEqual(
                "2.0", json.loads((project / canonical_audit["path"]).read_text(encoding="utf-8"))["schema_version"]
            )
            scoped_plan_artifact = next(
                item for item in state["artifacts"]
                if item.get("type") == "shot-plan" and item.get("scope") == {"kind": "episodes", "start": 1, "end": 1}
                and item.get("status") == "confirmed"
            )
            plan = json.loads((project / scoped_plan_artifact["path"]).read_text(encoding="utf-8"))
            self.assertEqual({"kind": "episodes", "start": 1, "end": 1}, plan["scope"])
            self.assertEqual(0, plan["timeline_start_ms"])
            self.assertEqual(120000, plan["timeline_end_ms"])
            self.assertEqual(720000, plan["target_runtime_ms"])
            self.assertTrue(all(item.get("generation_group") for item in plan["shots"]))
            self.assertTrue(all(item.get("source_scene_ref") and item.get("source_beats") for item in plan["beats"]))
            self.assertTrue(any(item.get("dialogue") for item in plan["shots"]))
            self.assertTrue(any(item.get("performance") for item in plan["shots"]))
            self.assertTrue(all(item.get("prompt_ref") for item in plan["shots"]))
            manifest = json.loads((project / "asset-manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(any(item["lock_status"] == "locked" for item in manifest["assets"]))
            report_paths = {item["path"] for item in state["artifacts"] if item.get("type") == "engine-report"}
            self.assertTrue(any(path.startswith("short-drama/script/E01-E01/report-v") and path.endswith(".html") for path in report_paths))
            self.assertTrue(any(path.startswith("short-drama/storyboard/E01-E01/report-v") and path.endswith(".html") for path in report_paths))
            self.assertTrue(all(item.get("report_stage") for item in state["artifacts"] if item.get("type") == "engine-report"))
            mapping = {item["upstream_id"]: item["name"] for item in json.loads((project / "short-drama-engine.json").read_text(encoding="utf-8"))["mappings"]["characters"]}
            self.assertEqual("沈知微", mapping["C01"])
            self.assertEqual("岸上挑灯的更夫", mapping["C05"])
            cast_artifact = next(item for item in state["artifacts"] if item.get("type") == "short-drama-cast" and item.get("status") == "confirmed")
            cast_report = next(item for item in state["artifacts"] if item.get("type") == "engine-report" and item.get("report_stage") == "development" and item.get("path", "").endswith(".html"))
            cast_json = (project / cast_artifact["path"]).read_text(encoding="utf-8")
            cast_html = (project / cast_report["path"]).read_text(encoding="utf-8")
            embedded = re.search(r'<script id="forging-source-json" type="application/json" data-encoding="base64">(.*?)</script>', cast_html, re.S)
            self.assertIsNotNone(embedded)
            self.assertEqual(cast_json, base64.b64decode(embedded.group(1)).decode("utf-8"))

    def test_short_drama_transaction_rolls_back_managed_files(self):
        source = ROOT / "examples" / "synthetic-short"
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            shutil.copytree(source, project)
            managed = [project / "project-state.json", project / "asset-manifest.json"]
            before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in managed}
            state = json.loads(managed[0].read_text(encoding="utf-8"))
            real_replace = project_store.os.replace
            calls = {"count": 0}

            def fail_second_staged_replace(source_path, target_path):
                if str(Path(source_path)).find("staged") >= 0:
                    calls["count"] += 1
                    if calls["count"] == 2:
                        raise OSError("fixture commit failure")
                return real_replace(source_path, target_path)

            with mock.patch.object(project_store.os, "replace", side_effect=fail_second_staged_replace):
                with self.assertRaises(OSError):
                    short_drama.commit(project, {
                        "short-drama/test.json": b"{\"fixture\":true}\n",
                        "project-state.json": json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
                    })
            after = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in managed}
            self.assertEqual(before, after)
            self.assertFalse((project / "short-drama" / "test.json").exists())
            self.assertFalse((project / ".short-drama-transaction").exists())

    def test_vendor_source_requires_license(self):
        sync = load_module("sync_shuohao_snapshot", SCRIPTS / "sync_shuohao_snapshot.py")
        source = ROOT.parent / "shuohao-skills-main"
        with tempfile.TemporaryDirectory() as temp:
            broken = Path(temp) / "source"
            shutil.copytree(source, broken)
            (broken / "LICENSE").unlink()
            with self.assertRaises(ValueError):
                sync.validate_source(broken)

    def test_series_audit_requires_gapless_full_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            state = {
                "project": {"project_id": "PROJECT-001", "target_runtime_ms": 720000},
                "artifacts": [
                    {"artifact_id": "ART-001", "type": "screenplay", "scope": {"kind": "episodes", "start": 1, "end": 3}},
                    {"artifact_id": "ART-002", "type": "screenplay", "scope": {"kind": "episodes", "start": 4, "end": 5}},
                    {"artifact_id": "ART-003", "type": "audit", "status": "confirmed", "scope": {"kind": "series"}, "depends_on": ["ART-001", "ART-002"]},
                ],
            }
            engine = {
                "schema_version": "1.0", "project_id": "PROJECT-001",
                "engine_snapshot": {},
                "profile": {"episode_count": 6, "episode_duration_ms": 120000, "style": "realistic", "generator": "minimax-h3"},
                "attachment": {},
                "mappings": {"characters": [], "scenes": [], "props": [], "scene_occurrences": [], "storyboard": []},
            }
            write_json(project / "project-state.json", state)
            write_json(project / "short-drama-engine.json", engine)
            self.assertTrue(any("do not cover every episode" in error for error in short_drama.validate_engine(project)))

    def test_upstream_change_invalidates_only_overlapping_scope(self):
        state = {"artifacts": [
            {"artifact_id": "ART-001", "type": "screenplay", "status": "superseded", "scope": {"kind": "episodes", "start": 1, "end": 3}, "depends_on": []},
            {"artifact_id": "ART-002", "type": "shot-plan", "status": "confirmed", "scope": {"kind": "episodes", "start": 2, "end": 2}, "depends_on": ["ART-001"]},
            {"artifact_id": "ART-003", "type": "shot-plan", "status": "confirmed", "scope": {"kind": "episodes", "start": 4, "end": 6}, "depends_on": ["ART-001"]},
        ]}
        manifest = {"assets": [
            {"asset_id": "PROP-001", "lock_status": "locked", "locked_fields": ["state"], "evidence": [{"source_ref": "ART-002"}]},
            {"asset_id": "PROP-002", "lock_status": "locked", "locked_fields": ["state"], "evidence": [{"source_ref": "ART-003"}]},
        ]}
        invalidated = short_drama.invalidate_downstream(
            state, manifest, {"ART-001"}, {"kind": "episodes", "start": 1, "end": 3}
        )
        self.assertEqual({"ART-002"}, invalidated)
        self.assertEqual("invalid", state["artifacts"][1]["status"])
        self.assertEqual("confirmed", state["artifacts"][2]["status"])
        self.assertEqual("stale", manifest["assets"][0]["lock_status"])
        self.assertEqual("locked", manifest["assets"][1]["lock_status"])

    def test_aggregate_two_scoped_shot_plans_and_series_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            configuration = sample_plan(1000)["profile"] | {
                "checkpoint_policy": "key-nodes", "automatic_authorization": False,
            }
            state = {
                "project": {"project_id": "PROJECT-001", "target_runtime_ms": 720000},
                "configuration": configuration, "sources": [], "checkpoints": [],
                "artifacts": [
                    {"artifact_id": "ART-001", "type": "screenplay", "revision": 1, "status": "confirmed", "scope": {"kind": "episodes", "start": 1, "end": 3}},
                    {"artifact_id": "ART-002", "type": "screenplay", "revision": 2, "status": "confirmed", "scope": {"kind": "episodes", "start": 4, "end": 6}},
                    {"artifact_id": "ART-003", "type": "shot-plan", "revision": 1, "status": "confirmed", "scope": {"kind": "episodes", "start": 1, "end": 3}, "path": "p1.json"},
                    {"artifact_id": "ART-004", "type": "shot-plan", "revision": 2, "status": "confirmed", "scope": {"kind": "episodes", "start": 4, "end": 6}, "path": "p2.json"},
                    {"artifact_id": "ART-005", "type": "audit", "revision": 1, "status": "confirmed", "scope": {"kind": "series"}, "path": "series-audit.md", "depends_on": ["ART-001", "ART-002"], "audit_result": {"p0_count": 0, "p1_count": 0, "p2_count": 0, "required_elements_total": 5, "required_elements_passed": 5, "decision": "pass"}},
                ],
            }
            assets = {"schema_version": "1.0", "project_id": "PROJECT-001", "manifest_version": 1, "assets": []}
            ledger = {"schema_version": "1.0", "project_id": "PROJECT-001", "ledger_version": 1, "scopes": []}
            engine = {
                "profile": {"episode_count": 6, "episode_duration_ms": 120000},
                "mappings": {"characters": [], "scenes": [], "props": [], "scene_occurrences": [], "storyboard": []},
            }
            write_json(project / "project-state.json", state)
            write_json(project / "asset-manifest.json", assets)
            write_json(project / "continuity-ledger.json", ledger)
            write_json(project / "short-drama-engine.json", engine)
            write_audit(project / "series-audit.md", screenplay_ids=["ART-001", "ART-002"], scope={"kind": "series"})
            p1 = sample_plan(360000)
            p1["scope"] = {"kind": "episodes", "start": 1, "end": 3}
            p1["timeline_start_ms"] = 0
            p1["timeline_end_ms"] = 360000
            p1["target_runtime_ms"] = 720000
            p2 = sample_plan(360000)
            p2["scope"] = {"kind": "episodes", "start": 4, "end": 6}
            p2["timeline_start_ms"] = 360000
            p2["timeline_end_ms"] = 720000
            p2["target_runtime_ms"] = 720000
            p2["scenes"] = [{"scene_id": "SCN-002"}]
            for index, beat in enumerate(p2["beats"], start=len(p1["beats"]) + 1):
                beat["beat_id"] = f"BEAT-{index:03d}"
            for index, shot in enumerate(p2["shots"], start=len(p1["shots"]) + 1):
                shot["shot_id"] = f"SHOT-{index:03d}"
                shot["scene_id"] = "SCN-002"
                shot["beat_id"] = p2["beats"][index - len(p1["shots"]) - 1]["beat_id"]
                shot["start_ms"] += 360000
                shot["end_ms"] += 360000
            write_json(project / "p1.json", p1)
            write_json(project / "p2.json", p2)
            captured = {}

            def capture_commit(_root, files):
                captured.update(files)

            with mock.patch.object(short_drama, "commit", side_effect=capture_commit):
                short_drama.command_aggregate(types.SimpleNamespace(project_dir=str(project), authorization="fixture"))
            aggregate = json.loads(captured["shot-plan.json"].decode("utf-8"))
            expected_shots = [item["shot_id"] for item in p1["shots"]] + [item["shot_id"] for item in p2["shots"]]
            self.assertEqual(expected_shots, [item["shot_id"] for item in aggregate["shots"]])
            updated_state = json.loads(captured["project-state.json"].decode("utf-8"))
            aggregate_artifact = next(item for item in updated_state["artifacts"] if item.get("type") == "shot-plan" and item.get("scope") == {"kind": "series"})
            self.assertEqual(["ART-003", "ART-004", "ART-005"], aggregate_artifact["depends_on"])

    def test_audit_metadata_is_enforced(self):
        source = ROOT / "examples" / "synthetic-short"
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            shutil.copytree(source, project)
            audit_path = project / "audit-screenplay-v002.md"
            audit_path.write_text("# Audit\n\nP0: 4\n\nBlocked.\n", encoding="utf-8")
            state = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
            audit = next(item for item in state["artifacts"] if item["artifact_id"] == "ART-006")
            audit["sha256"] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
            write_json(project / "project-state.json", state)
            errors = validator.validate_project(project)
            self.assertTrue(any("lacks an ai-drama-audit metadata block" in error for error in errors))
            self.assertTrue(any("valid confirmed audit" in error for error in errors))

        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            shutil.copytree(source, project)
            audit_path = project / "audit-screenplay-v002.md"
            body = audit_path.read_text(encoding="utf-8").replace(
                "确认 v002 后可生成正式分镜和锁定资产。",
                "P0：4 项。阻断下游，必须修订。",
            )
            audit_path.write_text(body, encoding="utf-8")
            state = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
            audit = next(item for item in state["artifacts"] if item["artifact_id"] == "ART-006")
            audit["sha256"] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
            write_json(project / "project-state.json", state)
            errors = validator.validate_project(project)
            self.assertTrue(any("contradicts metadata" in error for error in errors))
            self.assertTrue(any("blocking language" in error for error in errors))

    def test_locked_fields_require_field_level_evidence(self):
        root = ROOT / "examples" / "synthetic-short"
        state = json.loads((root / "project-state.json").read_text(encoding="utf-8"))
        assets = json.loads((root / "asset-manifest.json").read_text(encoding="utf-8"))
        refs = {item["source_id"] for item in state["sources"]} | {item["artifact_id"] for item in state["artifacts"]}
        broken = copy.deepcopy(assets)
        prop = next(item for item in broken["assets"] if item["asset_id"] == "PROP-001")
        prop["evidence"] = [item for item in prop["evidence"] if item["field"] == "state-chain"]
        errors: list[str] = []
        validator.validate_assets(broken, "PROJECT-001", refs, errors)
        self.assertTrue(any("locked fields lack confirmed evidence" in error for error in errors))

        state_without_lock_artifact = copy.deepcopy(state)
        lock_artifact = next(item for item in state_without_lock_artifact["artifacts"] if item["type"] == "locked-assets")
        lock_artifact["status"] = "draft"
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            shutil.copytree(root, project)
            write_json(project / "project-state.json", state_without_lock_artifact)
            errors = validator.validate_project(project)
            self.assertTrue(any("locked assets require" in error for error in errors))

    def test_project_and_shot_configuration_must_match(self):
        source = ROOT / "examples" / "synthetic-short"
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            shutil.copytree(source, project)
            state = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
            state["project"]["target_runtime_ms"] = 99999
            state["configuration"]["audio_policy"] = "different"
            write_json(project / "project-state.json", state)
            errors = validator.validate_project(project)
            self.assertTrue(any("target_runtime_ms does not match" in error for error in errors))
            self.assertTrue(any("profile.audio_policy does not match" in error for error in errors))

    def test_malformed_shots_return_errors_instead_of_crashing(self):
        source = ROOT / "examples" / "synthetic-short"
        for mutation in ["non-object", "non-array-assets"]:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                project = Path(temp) / "project"
                shutil.copytree(source, project)
                plan = json.loads((project / "shot-plan.json").read_text(encoding="utf-8"))
                if mutation == "non-object":
                    plan["shots"][0] = "bad"
                else:
                    plan["shots"][0]["assets"] = 7
                write_json(project / "shot-plan.json", plan)
                state = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
                artifact = next(item for item in state["artifacts"] if item["type"] == "shot-plan")
                artifact["sha256"] = hashlib.sha256((project / "shot-plan.json").read_bytes()).hexdigest()
                write_json(project / "project-state.json", state)
                errors = validator.validate_project(project)
                self.assertTrue(any("shot-plan" in error for error in errors))

    def test_continuity_time_and_references_are_validated(self):
        root = ROOT / "examples" / "synthetic-short"
        state = json.loads((root / "project-state.json").read_text(encoding="utf-8"))
        assets = json.loads((root / "asset-manifest.json").read_text(encoding="utf-8"))
        ledger = json.loads((root / "continuity-ledger.json").read_text(encoding="utf-8"))
        broken = copy.deepcopy(ledger)
        broken["scopes"][0]["events"][0]["at_ms"] = 2000
        broken["scopes"][0]["events"][1]["at_ms"] = 1000
        broken["scopes"][0]["events"][1]["scene_ref"] = "SCN-999"
        broken["scopes"][0]["events"][1]["shot_ref"] = "SHOT-999"
        errors: list[str] = []
        validator.validate_ledger(
            broken, "PROJECT-001", {item["asset_id"] for item in assets["assets"]},
            set(state["project"]["scene_ids"]), set(), errors,
        )
        self.assertTrue(any("at_ms moves backward" in error for error in errors))
        self.assertTrue(any("unknown scene" in error for error in errors))
        self.assertTrue(any("unknown shot" in error for error in errors))

    def test_schema_patterns_are_typed(self):
        def visit(value):
            if isinstance(value, dict):
                if "pattern" in value:
                    declared = value.get("type")
                    self.assertTrue(declared == "string" or isinstance(declared, list) and "string" in declared, value)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        for path in (ROOT / "schemas").glob("*.json"):
            visit(json.loads(path.read_text(encoding="utf-8")))

    def test_examples_validate(self):
        self.assertEqual([], validator.validate_project(ROOT / "examples" / "legacy-yiqiyang"))
        self.assertEqual([], validator.validate_project(ROOT / "examples" / "synthetic-short"))

    def test_legacy_regression(self):
        root = ROOT / "examples" / "legacy-yiqiyang"
        outline = (root / "scene-outline-v001.md").read_text(encoding="utf-8")
        screenplay = (root / "screenplay-v002.md").read_text(encoding="utf-8")
        scene_heading = r"^## \d+\. (?:内|外|连续场组|交叉剪辑) "
        self.assertEqual(52, len(re.findall(scene_heading, outline, re.M)))
        self.assertEqual(52, len(re.findall(r"^## 场 \d+｜", screenplay, re.M)))
        state = json.loads((root / "project-state.json").read_text(encoding="utf-8"))
        self.assertEqual("not-distributed", state["sources"][0]["availability"])
        corpus = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.md"))
        self.assertIsNone(re.search(r"\b(?:CHAR|SCN|PROP|MOTIF|COSTUME|BG)_\d+", corpus))

    def test_visual_layout_capability_compose_and_verify(self):
        capability = visual_layout.capabilities()
        if not capability["deterministic_layout"]:
            self.skipTest("Pillow or a CJK font is unavailable")
        Image, _, _, _, _ = visual_layout.pillow_modules()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.png"
            image = Image.new("RGB", (320, 180), "white")
            for x in range(320):
                for y in range(180):
                    image.putpixel((x, y), (x % 256, y % 256, (x + y) % 256))
            image.save(source)
            labels = root / "labels.json"
            write_json(labels, {
                "title": "角色设定", "asset_id": "CHAR-001", "font_size": 18,
                "labels": [{"text": "正面", "x": 20, "y": 20}], "legend": ["已确认"],
            })
            output = root / "composed.png"
            visual_layout.compose(source, labels, output, Path(capability["cjk_font"]))
            result = visual_layout.inspect_image(output)
            self.assertTrue(result["nonblank"])
            self.assertEqual((320, 180), (result["width"], result["height"]))

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg unavailable")
    def test_video_fixture_known_cuts(self):
        help_result = subprocess.run(
            [sys.executable, str(SCRIPTS / "create_video_fixture.py"), "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        help_text = help_result.stdout.lower()
        self.assertNotIn("cut", help_text)
        self.assertNotIn("1s", help_text)
        self.assertNotIn("2s", help_text)
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "known-cuts.mp4"
            subprocess.run([sys.executable, str(SCRIPTS / "create_video_fixture.py"), "--output", str(video)], check=True, capture_output=True)
            result = subprocess.run([
                shutil.which("ffmpeg"), "-hide_banner", "-i", str(video),
                "-filter:v", "select=gt(scene\\,0.1),showinfo", "-f", "null", "-",
            ], capture_output=True, text=True)
            cut_times = [float(value) for value in re.findall(r"pts_time:([0-9.]+)", result.stderr)]
            for expected in [1.0, 2.0]:
                self.assertTrue(any(abs(actual - expected) <= 2 / 25 for actual in cut_times), (expected, cut_times))
            analysis = media_analysis.build_analysis(video, 0.1)
            analysis["shots"][0]["scene_id"] = "SCENE-001"
            analysis["shots"][0]["asset_ids"] = ["CHAR-001", "PROP-001"]
            self.assertEqual([], media_analysis.validate_analysis(analysis))
            boundaries = [shot["start_ms"] for shot in analysis["shots"][1:]]
            for expected in [1000, 2000]:
                self.assertTrue(any(abs(actual - expected) <= 2 / 25 * 1000 for actual in boundaries))
            rendered = media_analysis.render_markdown(analysis)
            self.assertIn("SHOT-001", rendered)
            self.assertIn("Scene asset: SCENE-001", rendered)
            self.assertIn("Referenced assets: CHAR-001, PROP-001", rendered)
            frame_dir = Path(temp) / "review-frames"
            records = media_analysis.extract_review_frames(video, analysis, frame_dir)
            self.assertEqual(len(analysis["shots"]) * 3, len(records))
            self.assertTrue(all(Path(item["path"]).is_file() for item in records))


if __name__ == "__main__":
    unittest.main()
