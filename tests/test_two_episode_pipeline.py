from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

from tests.helpers import ROOT, SCRIPTS, load_module, write_audit_json, write_json


short_drama = load_module("two_episode_short_drama", SCRIPTS / "short_drama_cli.py")
validator = load_module("two_episode_validator", SCRIPTS / "validate_project.py")
STATE_CLI = SCRIPTS / "state_cli.py"
SHORT_CLI = SCRIPTS / "short_drama_cli.py"


def run_cli(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        raise AssertionError(completed.stdout + completed.stderr)
    return completed


def artifact_bytes(value: dict) -> bytes:
    return short_drama.json_bytes(value)


def scoped_plan(episode: int) -> dict:
    start = (episode - 1) * 1000
    end = episode * 1000
    scene_id = f"SCN-{episode:03d}"
    beat_id = f"BEAT-{episode:03d}"
    shot_id = f"SHOT-{episode:03d}"
    group = f"E{episode:02d}-01"
    return {
        "schema_version": "2.0",
        "project_id": "PROJECT-001",
        "plan_version": episode,
        "scope": {"kind": "episodes", "start": episode, "end": episode},
        "timeline_start_ms": start,
        "timeline_end_ms": end,
        "target_runtime_ms": 2000,
        "profile": {
            "clip_max_duration_ms": 15000,
            "audio_policy": "preserve-dialogue-environment",
            "subtitle_policy": "unspecified",
            "aspect_ratio": "9:16",
            "generator": "minimax-h3",
            "editing_policy": "story-driven",
            "visual_reset_policy": "story-driven",
            "dialogue_rate_chars_per_second": 4.5,
        },
        "scenes": [{"scene_id": scene_id, "name": f"Episode {episode}"}],
        "beats": [{
            "beat_id": beat_id,
            "summary": f"Episode {episode} resolves one causal beat",
            "indivisible": True,
            "source_scene_ref": scene_id,
            "source_beat_range": [1, 1],
            "source_beats": [{"index": 1, "action": f"event {episode}"}],
        }],
        "shots": [{
            "shot_id": shot_id,
            "scene_id": scene_id,
            "beat_id": beat_id,
            "start_ms": start,
            "end_ms": end,
            "framing": "medium",
            "angle": "front",
            "movement": "static",
            "transition": "cut",
            "visual": f"Episode {episode} event",
            "performance": "controlled reaction",
            "dialogue": "",
            "sound": "room tone",
            "generation_group": group,
            "prompt_ref": f"short-drama/h3/E{episode:02d}-E{episode:02d}/{group}/prompt.md",
            "assets": [],
        }],
    }


class TwoEpisodePipelineTests(unittest.TestCase):
    def test_two_episode_aggregate_generation_and_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            run_cli(STATE_CLI, "init", "--project-dir", str(project), "--title", "Two Episodes", "--slug", "two-episodes")
            run_cli(
                SHORT_CLI,
                "attach",
                "--project-dir", str(project),
                "--episodes", "2",
                "--episode-seconds", "1",
                "--genre", "fixture",
                "--immutable-core", "two linked episode events",
                "--authorization", "fixture brief approval",
            )

            state, assets, ledger, engine = short_drama.load_project(project)
            state["project"]["scene_ids"] = ["SCN-001", "SCN-002"]
            brief = short_drama.latest_artifact(state, "production-brief", "confirmed")
            assert brief is not None
            files: dict[str, bytes] = {}

            outline_path = "short-drama/outline/outline-v001.json"
            outline_body = artifact_bytes({"episodes": [1, 2], "causal_spine": "event 1 enables event 2"})
            outline_id = short_drama.add_artifact(
                state, "series-outline", outline_path, outline_body,
                [brief["artifact_id"]], {"kind": "series"}, "confirmed", "fixture outline approval",
            )
            files[outline_path] = outline_body

            screenplay_ids: list[str] = []
            for episode in (1, 2):
                path = f"short-drama/script/E{episode:02d}-E{episode:02d}/screenplay-v{episode:03d}.json"
                body = artifact_bytes({"episode": episode, "scenes": [f"SCN-{episode:03d}"]})
                screenplay_ids.append(short_drama.add_artifact(
                    state, "screenplay", path, body, [outline_id],
                    {"kind": "episodes", "start": episode, "end": episode},
                    "confirmed", f"fixture screenplay {episode} approval",
                ))
                files[path] = body

            audit_path = project / "series-audit-source.json"
            targets = []
            for artifact_id in screenplay_ids:
                artifact = next(item for item in state["artifacts"] if item["artifact_id"] == artifact_id)
                targets.append({
                    "artifact_id": artifact_id,
                    "path": artifact["path"],
                    "sha256": artifact["sha256"],
                })
            write_audit_json(audit_path, targets, scope={"kind": "series"})
            audit_body = audit_path.read_bytes()
            canonical_audit_path = "short-drama/script/series/audit-v001.json"
            audit_id = short_drama.add_artifact(
                state, "audit", canonical_audit_path, audit_body, screenplay_ids,
                {"kind": "series"}, "confirmed", "fixture series audit approval",
                audit_result={
                    "p0_count": 0, "p1_count": 0, "p2_count": 0,
                    "required_elements_total": 1, "required_elements_passed": 1,
                    "decision": "pass",
                },
            )
            files[canonical_audit_path] = audit_body

            plan_ids: list[str] = []
            for episode in (1, 2):
                plan = scoped_plan(episode)
                plan_path = f"short-drama/storyboard/E{episode:02d}-E{episode:02d}/shot-plan-v{episode:03d}.json"
                plan_body = artifact_bytes(plan)
                plan_id = short_drama.add_artifact(
                    state, "shot-plan", plan_path, plan_body,
                    [screenplay_ids[episode - 1], audit_id],
                    {"kind": "episodes", "start": episode, "end": episode},
                    "confirmed", f"fixture shot plan {episode} approval",
                )
                plan_ids.append(plan_id)
                files[plan_path] = plan_body

                group = f"E{episode:02d}-01"
                prompt_relative = f"short-drama/h3/E{episode:02d}-E{episode:02d}/{group}/prompt.md"
                prompt_body = f"[Shot 1] Episode {episode} exact 1 second action.\n".encode("utf-8")
                manifest_path = f"short-drama/h3/E{episode:02d}-E{episode:02d}/generation-manifest-v{episode:03d}.json"
                manifest = {
                    "schema_version": "2.0",
                    "project_id": "PROJECT-001",
                    "scope": {"kind": "episodes", "start": episode, "end": episode},
                    "generator": {
                        "name": "minimax-h3", "version": None, "max_segment_ms": 15000,
                        "aspect_ratio": "9:16", "prompt_language": "en",
                        "dialogue_language": "Chinese",
                    },
                    "groups": [{
                        "generation_group": group,
                        "prompt": f"{group}/prompt.md",
                        "prompt_sha256": hashlib.sha256(prompt_body).hexdigest(),
                        "shot_ids": [f"SHOT-{episode:03d}"],
                        "beat_ids": [f"BEAT-{episode:03d}"],
                        "asset_ids": [],
                        "start_ms": (episode - 1) * 1000,
                        "end_ms": episode * 1000,
                    }],
                }
                manifest_body = artifact_bytes(manifest)
                short_drama.add_artifact(
                    state, "generation-manifest", manifest_path, manifest_body, [plan_id],
                    {"kind": "episodes", "start": episode, "end": episode},
                    "confirmed", f"fixture generation manifest {episode} approval",
                )
                files[prompt_relative] = prompt_body
                files[manifest_path] = manifest_body

            asset_body = artifact_bytes(assets)
            locked_id = short_drama.add_artifact(
                state, "locked-assets", "asset-manifest.json", asset_body,
                [audit_id], {"kind": "series"}, "confirmed",
            )
            state["checkpoints"].append({
                "checkpoint_id": "CHK-011", "stage": "assets", "decision": "confirmed",
                "authorization": "fixture locked assets approval", "authorization_kind": "approval",
                "sequence": len(state.get("checkpoints", [])) + 1, "affects": [locked_id],
            })
            files.update({
                "project-state.json": artifact_bytes(state),
                "asset-manifest.json": asset_body,
                "continuity-ledger.json": artifact_bytes(ledger),
                "short-drama-engine.json": artifact_bytes(engine),
            })
            short_drama.commit(project, files)

            short_drama.command_aggregate(types.SimpleNamespace(
                project_dir=str(project), authorization="fixture aggregate approval"
            ))
            state = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
            engine = json.loads((project / "short-drama-engine.json").read_text(encoding="utf-8"))
            aggregate = next(
                item for item in state["artifacts"]
                if item.get("type") == "shot-plan" and item.get("scope") == {"kind": "series"}
                and item.get("status") == "confirmed"
            )
            self.assertTrue(all(
                next(item for item in state["artifacts"] if item["artifact_id"] == plan_id)["status"] == "confirmed"
                for plan_id in plan_ids
            ))
            self.assertTrue(all(
                item["status"] == "confirmed"
                for item in state["artifacts"] if item.get("type") == "generation-manifest"
            ))
            self.assertNotEqual("shot-plan.json", aggregate["path"])
            self.assertEqual(aggregate["path"], engine["aggregate"]["shot_plan_path"])
            self.assertEqual("shot-plan.json", engine["aggregate"]["projection_path"])
            self.assertEqual(
                aggregate["sha256"],
                hashlib.sha256((project / "shot-plan.json").read_bytes()).hexdigest(),
            )

            # The hook-debt completion gate is exercised in test_hook_ledger.py against
            # completion_debt() directly; this pipeline fixture uses stub screenplays whose
            # deterministic hook replay is empty, so completion succeeds on a clean ledger.
            short_drama.command_complete(types.SimpleNamespace(
                project_dir=str(project), authorization="fixture completion approval"
            ))
            state = json.loads((project / "project-state.json").read_text(encoding="utf-8"))
            engine = json.loads((project / "short-drama-engine.json").read_text(encoding="utf-8"))
            self.assertEqual("complete", state["stage"])
            self.assertEqual(aggregate["artifact_id"], engine["completion"]["aggregate_artifact_id"])
            self.assertEqual(audit_id, engine["completion"]["series_audit_artifact_id"])
            self.assertEqual(locked_id, engine["completion"]["locked_assets_artifact_id"])
            self.assertEqual([], validator.validate_project(project))
            self.assertEqual([], short_drama.validate_engine(project))


if __name__ == "__main__":
    unittest.main()
