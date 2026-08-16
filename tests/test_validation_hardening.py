from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_project.py"
SPEC = importlib.util.spec_from_file_location("validation_hardening_validator", VALIDATOR_PATH)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def profile() -> dict:
    return {
        "clip_max_duration_ms": 30000,
        "audio_policy": "preserve",
        "subtitle_policy": "unspecified",
        "aspect_ratio": "16:9",
        "generator": "unspecified",
        "editing_policy": "story-driven",
        "visual_reset_policy": "story-driven",
        "dialogue_rate_chars_per_second": 4.5,
    }


def minimal_state() -> dict:
    return {
        "schema_version": "1.0",
        "project": {
            "project_id": "PROJECT-001",
            "title": "Fixture",
            "slug": "fixture",
            "locale": "zh-CN",
            "target_runtime_ms": 1000,
            "scene_ids": [],
        },
        "stage": "intake",
        "configuration": {
            "checkpoint_policy": "key-nodes",
            "automatic_authorization": False,
            **profile(),
        },
        "sources": [],
        "artifacts": [],
        "checkpoints": [],
    }


def plan(scope: dict | None, shot_id: str, beat_id: str, start: int, end: int) -> dict:
    value = {
        "schema_version": "1.0",
        "project_id": "PROJECT-001",
        "plan_version": 1,
        "target_runtime_ms": 2000,
        "profile": profile(),
        "scenes": [{"scene_id": "SCN-001"}],
        "beats": [{"beat_id": beat_id, "summary": beat_id, "indivisible": True}],
        "shots": [{
            "shot_id": shot_id,
            "scene_id": "SCN-001",
            "beat_id": beat_id,
            "start_ms": start,
            "end_ms": end,
            "framing": "medium",
            "angle": "front",
            "movement": "static",
            "transition": "cut",
            "visual": shot_id,
            "performance": "",
            "dialogue": "",
            "sound": "",
            "assets": [],
        }],
    }
    if scope is not None:
        value["scope"] = scope
        value["timeline_start_ms"] = start
        value["timeline_end_ms"] = end
    return value


class ValidationHardeningTests(unittest.TestCase):
    def test_escaping_paths_stop_before_any_file_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            root.mkdir()
            state = minimal_state()
            state["sources"] = [{
                "source_id": "SRC-001",
                "kind": "story",
                "path": "../outside.md",
                "availability": "available",
                "authority": "canonical",
                "sha256": "0" * 64,
            }]
            state["artifacts"] = [{
                "artifact_id": "ART-001",
                "type": "notes",
                "revision": 1,
                "status": "draft",
                "path": "../outside.json",
                "depends_on": [],
                "source_refs": [],
            }]
            errors: list[str] = []
            with mock.patch.object(validator, "hash_file", side_effect=AssertionError("must not read")):
                validator.validate_state(root, state, errors)
            self.assertTrue(any("source SRC-001 path escapes" in error for error in errors), errors)
            self.assertTrue(any("artifact ART-001 path escapes" in error for error in errors), errors)
            self.assertFalse(any("available source missing" in error for error in errors), errors)
            self.assertFalse(any("artifact ART-001 file missing" in error for error in errors), errors)

    def test_series_coverage_requires_declared_final_episode(self):
        scopes = [
            {"kind": "episodes", "start": 1, "end": 3},
            {"kind": "episodes", "start": 4, "end": 5},
        ]
        self.assertTrue(validator.scopes_cover(scopes, {"kind": "series"}))
        self.assertFalse(validator.scopes_cover(scopes, {"kind": "series"}, episode_count=6))
        scopes[-1]["end"] = 6
        self.assertTrue(validator.scopes_cover(scopes, {"kind": "series"}, episode_count=6))

    def test_latest_checkpoint_revokes_prior_approval(self):
        root = ROOT / "examples" / "synthetic-short"
        state = json.loads((root / "project-state.json").read_text(encoding="utf-8"))
        state["checkpoints"].append({
            "checkpoint_id": "CHK-007",
            "stage": "screenplay",
            "decision": "revise",
            "authorization": "fixture revision",
            "sequence": 7,
            "affects": ["ART-005"],
        })
        errors: list[str] = []
        validator.validate_state(root, state, errors)
        self.assertTrue(any("ART-005 is revoked by effective checkpoint CHK-007" in error for error in errors), errors)

    def test_confirmed_downstream_rejects_blocked_intermediate_ancestor(self):
        root = ROOT / "examples" / "synthetic-short"
        state = json.loads((root / "project-state.json").read_text(encoding="utf-8"))
        next(item for item in state["artifacts"] if item["artifact_id"] == "ART-006")["status"] = "draft"
        errors: list[str] = []
        validator.validate_state(root, state, errors)
        self.assertTrue(any(
            "confirmed downstream ART-008 ancestor chain crosses invalid or draft artifacts" in error
            for error in errors
        ), errors)

    def test_locked_fields_and_evidence_must_be_eligible(self):
        manifest = {
            "schema_version": "2.0",
            "project_id": "PROJECT-001",
            "manifest_version": 1,
            "assets": [{
                "asset_id": "PROP-001",
                "type": "prop",
                "name": "Key",
                "aliases": [],
                "lock_status": "locked",
                "locked_fields": ["color", "owner"],
                "evidence": [
                    {"field": "color", "level": "confirmed", "source_ref": "ART-999:shot", "locator": "x"},
                    {"field": "owner", "level": "confirmed", "source_ref": "ART-999", "locator": "y"},
                ],
                "visual_dna": {"color": "red"},
            }],
        }
        errors: list[str] = []
        validator.validate_assets(manifest, "PROJECT-001", {"ART-001"}, errors)
        self.assertTrue(any("ineligible source or artifact" in error for error in errors), errors)
        self.assertTrue(any("locked fields missing from visual_dna: ['owner']" in error for error in errors), errors)

    def test_continuity_event_matches_shot_scene_time_and_evidence(self):
        ledger = {
            "schema_version": "1.0",
            "project_id": "PROJECT-001",
            "ledger_version": 1,
            "scopes": [{
                "scope_id": "scope-1",
                "sequence": 1,
                "start_snapshot": {"PROP-001": {"owner": "A"}},
                "events": [{
                    "event_id": "EVT-001",
                    "asset_id": "PROP-001",
                    "field": "owner",
                    "before": "A",
                    "after": "B",
                    "at_ms": 250,
                    "scene_ref": "SCN-002",
                    "shot_ref": "SHOT-001",
                    "evidence_ref": "ART-999:line-1",
                }],
                "end_snapshot": {"PROP-001": {"owner": "B"}},
            }],
        }
        errors: list[str] = []
        validator.validate_ledger(
            ledger,
            "PROJECT-001",
            {"PROP-001"},
            {"SCN-001", "SCN-002"},
            {"SHOT-001"},
            errors,
            shot_index={"SHOT-001": {"scene_id": "SCN-001", "start_ms": 100, "end_ms": 200}},
            evidence_refs={"ART-001"},
        )
        self.assertTrue(any("belongs to scene SCN-001, not SCN-002" in error for error in errors), errors)
        self.assertTrue(any("falls outside shot SHOT-001 timing 100-200" in error for error in errors), errors)
        self.assertTrue(any("evidence_ref is not eligible" in error for error in errors), errors)

    def test_engine_crosswalk_resolves_all_foreign_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            engine = {
                "schema_version": "1.0",
                "project_id": "PROJECT-001",
                "engine_snapshot": {"upstream": "x", "adaptation_version": "1", "manifest_sha256": "a" * 64},
                "profile": {
                    "episode_count": 1,
                    "episode_duration_ms": 1000,
                    "genre": "drama",
                    "adaptation_mode": "faithful",
                    "report_language": "zh",
                    "prompt_language": "zh",
                    "style": "realistic",
                    "generator": "minimax-h3",
                    "h3": {"max_segment_ms": 1000, "dialogue_tag": "<d>[Chinese]"},
                },
                "attachment": {"mode": "new", "status": "attached"},
                "mappings": {
                    "characters": [{"upstream_id": "C1", "forging_id": "CHAR-999", "name": "A", "status": "active"}],
                    "scenes": [],
                    "props": [],
                    "scene_occurrences": [{"key": "S1", "scene_asset_id": "SCENE-999", "forging_id": "SCN-999", "status": "active"}],
                    "storyboard": [{"key": "K1", "generation_group": "G-wrong", "beat_id": "BEAT-999", "shot_id": "SHOT-001", "status": "active"}],
                },
            }
            write_json(root / "short-drama-engine.json", engine)
            errors: list[str] = []
            validator.validate_short_drama_engine(
                root,
                {"project": {"project_id": "PROJECT-001", "target_runtime_ms": 1000, "scene_ids": ["SCN-001"]}},
                errors,
                asset_ids={"CHAR-001", "SCENE-001"},
                shot_index={"SHOT-001": {"beat_id": "BEAT-001", "generation_group": "G-1"}},
            )
            self.assertTrue(any("unknown manifest asset: CHAR-999" in error for error in errors), errors)
            self.assertTrue(any("unknown scene asset: SCENE-999" in error for error in errors), errors)
            self.assertTrue(any("undeclared project scene: SCN-999" in error for error in errors), errors)
            self.assertTrue(any("beat does not match shot SHOT-001" in error for error in errors), errors)
            self.assertTrue(any("generation_group does not match shot SHOT-001" in error for error in errors), errors)

    def test_shot_analysis_artifact_uses_its_schema(self):
        source = ROOT / "examples" / "synthetic-short"
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            shutil.copytree(source, project)
            write_json(project / "analysis.json", {"schema_version": "1.0", "shots": []})
            state = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
            state["artifacts"].append({
                "artifact_id": "ART-010",
                "type": "shot-analysis",
                "revision": 1,
                "status": "draft",
                "path": "analysis.json",
                "depends_on": [],
                "source_refs": [],
            })
            write_json(project / "project-state.json", state)
            errors = validator.validate_project(project)
            self.assertTrue(any("artifact ART-010 missing required property source" in error for error in errors), errors)
            self.assertTrue(any("artifact ART-010 missing required property detection" in error for error in errors), errors)

    def test_aggregate_preserves_scoped_plan_fields_losslessly(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = plan({"kind": "episodes", "start": 1, "end": 1}, "SHOT-001", "BEAT-001", 0, 1000)
            second = plan({"kind": "episodes", "start": 2, "end": 2}, "SHOT-002", "BEAT-002", 1000, 2000)
            aggregate = plan(None, "SHOT-001", "BEAT-001", 0, 1000)
            aggregate["beats"].extend(copy.deepcopy(second["beats"]))
            aggregate["shots"].extend(copy.deepcopy(second["shots"]))
            aggregate["shots"][1]["visual"] = "lossy rewrite"
            write_json(root / "p1.json", first)
            write_json(root / "p2.json", second)
            write_json(root / "shot-plan.json", aggregate)
            artifacts = [
                {"artifact_id": "ART-001", "type": "shot-plan", "status": "confirmed", "scope": first["scope"], "path": "p1.json"},
                {"artifact_id": "ART-002", "type": "shot-plan", "status": "confirmed", "scope": second["scope"], "path": "p2.json"},
                {"artifact_id": "ART-003", "type": "shot-plan", "status": "confirmed", "scope": {"kind": "series"}, "path": "shot-plan.json"},
            ]
            errors: list[str] = []
            validator.validate_shots(
                root,
                "PROJECT-001",
                set(),
                {"target_runtime_ms": 2000, "scene_ids": ["SCN-001"]},
                profile(),
                artifacts,
                errors,
            )
            self.assertTrue(any("aggregate shot-plan shots is not a lossless merge" in error for error in errors), errors)

    def test_generation_manifest_resolves_prompt_and_plan_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prompt_path = root / "short-drama" / "h3" / "E01-E01" / "E01-01" / "prompt.md"
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text("prompt\n", encoding="utf-8")
            shot_plan = plan({"kind": "episodes", "start": 1, "end": 1}, "SHOT-001", "BEAT-001", 0, 1000)
            shot_plan["shots"][0]["generation_group"] = "E01-01"
            shot_plan["shots"][0]["assets"] = ["CHAR-001"]
            write_json(root / "plan.json", shot_plan)
            manifest = {
                "schema_version": "2.0",
                "project_id": "PROJECT-001",
                "scope": {"kind": "episodes", "start": 1, "end": 1},
                "generator": {
                    "name": "minimax-h3", "version": None, "max_segment_ms": 15000,
                    "aspect_ratio": "9:16", "prompt_language": "en", "dialogue_language": "Chinese",
                },
                "groups": [{
                    "generation_group": "E01-01", "prompt": "E01-01/prompt.md",
                    "prompt_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
                    "shot_ids": ["SHOT-001"], "beat_ids": ["BEAT-001"], "asset_ids": ["CHAR-001"],
                    "start_ms": 0, "end_ms": 1000,
                }],
            }
            manifest_path = root / "short-drama" / "h3" / "E01-E01" / "generation-manifest-v001.json"
            write_json(manifest_path, manifest)
            artifacts = [
                {"artifact_id": "ART-001", "type": "shot-plan", "status": "confirmed", "path": "plan.json"},
                {"artifact_id": "ART-002", "type": "generation-manifest", "status": "confirmed", "path": "short-drama/h3/E01-E01/generation-manifest-v001.json", "depends_on": ["ART-001"]},
            ]
            errors: list[str] = []
            validator.validate_generation_manifests(root, artifacts, errors)
            self.assertEqual([], errors)
            prompt_path.write_text("tampered\n", encoding="utf-8")
            errors = []
            validator.validate_generation_manifests(root, artifacts, errors)
            self.assertTrue(any("prompt hash mismatch" in error for error in errors), errors)

    def test_visual_delivery_rejects_tampered_or_failed_qc_media(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            media = root / "visual" / "frame.png"
            media.parent.mkdir(parents=True)
            media.write_bytes(b"fixture-image")
            manifest = {
                "schema_version": "2.0", "delivery_id": "VIS-001", "project_id": "PROJECT-001",
                "asset_id": "CHAR-001", "mode": "concept", "status": "generated",
                "rights": {"status": "user-owned", "legal_clearance_claimed": False, "usage_basis": "fixture"},
                "specification": {"report_language": "zh", "prompt_language": "en", "style": "realistic", "aspect_ratio": "9:16", "width_px": 1080, "height_px": 1920, "format": "png", "projection": "planar"},
                "capabilities": {key: {"status": "available", "checked_by": "fixture", "checked_at": "2026-08-16T12:00:00Z", "details": None} for key in ("image_generation", "image_editing", "deterministic_layout", "vr_equirectangular")},
                "evidence": [], "design_decisions": [],
                "outputs": [{
                    "role": "reference", "path": "frame.png", "sha256": hashlib.sha256(media.read_bytes()).hexdigest(), "mime_type": "image/png",
                    "qc": {"decoded": True, "actual_width_px": 1080, "actual_height_px": 1920, "nonblank": True, "aspect_ratio_matches": True, "visual_review": "pass", "vr_review": "not-applicable", "notes": []},
                }],
                "failures": [],
            }
            write_json(root / "visual" / "manifest.json", manifest)
            artifacts = [{"artifact_id": "ART-001", "type": "visual-delivery", "status": "confirmed", "path": "visual/manifest.json"}]
            errors: list[str] = []
            validator.validate_media_manifests(root, artifacts, errors)
            self.assertEqual([], errors)
            media.write_bytes(b"tampered")
            manifest["outputs"][0]["qc"]["visual_review"] = "fail"
            write_json(root / "visual" / "manifest.json", manifest)
            errors = []
            validator.validate_media_manifests(root, artifacts, errors)
            self.assertTrue(any("media hash mismatch" in error for error in errors), errors)
            self.assertTrue(any("lacks passing visual review" in error for error in errors), errors)

    def test_complete_requires_consistent_completion_records(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_json(root / "short-drama-engine.json", {})
            write_json(root / "shot-plan.json", {"shots": []})
            state = {
                "stage": "complete",
                "configuration": {"delivery_required": True},
                "artifacts": [
                    {"artifact_id": "ART-001", "type": "shot-plan", "status": "confirmed", "scope": {"kind": "series"}, "path": "shot-plan.json", "sha256": "1" * 64, "depends_on": ["ART-002"]},
                    {"artifact_id": "ART-002", "type": "audit", "status": "confirmed", "scope": {"kind": "series"}, "sha256": "2" * 64, "audit_result": {"decision": "pass"}},
                    {"artifact_id": "ART-003", "type": "locked-assets", "status": "confirmed", "path": "asset-manifest.json", "sha256": "3" * 64},
                ],
            }
            engine = {
                "schema_version": "2.0",
                "aggregate": {"artifact_id": "ART-001", "shot_plan_path": "shot-plan.json", "projection_path": "shot-plan.json", "sha256": "1" * 64, "scope": {"kind": "series"}},
                "completion": {
                    "authorization": "fixture",
                    "aggregate_artifact_id": "ART-999",
                    "aggregate_sha256": "9" * 64,
                    "series_audit_artifact_id": "ART-998",
                    "series_audit_sha256": "8" * 64,
                    "locked_assets_artifact_id": "ART-997",
                    "locked_assets_sha256": "7" * 64,
                },
            }
            errors: list[str] = []
            validator.validate_short_drama_completion(root, state, {"assets": []}, errors, engine)
            self.assertTrue(any("aggregate_artifact_id does not match" in error for error in errors), errors)
            self.assertTrue(any("series_audit_sha256 does not match" in error for error in errors), errors)
            self.assertTrue(any("locked_assets_artifact_id does not match" in error for error in errors), errors)
            self.assertTrue(any("delivery_required=true" in error for error in errors), errors)

    def test_schema_shape_errors_return_messages_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_json(root / "project-state.json", {"schema_version": "2.0", "project": []})
            write_json(root / "asset-manifest.json", {"schema_version": "2.0", "assets": [7]})
            write_json(root / "continuity-ledger.json", {"schema_version": "2.0", "scopes": [7]})
            errors = validator.validate_project(root)
            self.assertTrue(errors)
            self.assertTrue(all(isinstance(error, str) for error in errors))


if __name__ == "__main__":
    unittest.main()
