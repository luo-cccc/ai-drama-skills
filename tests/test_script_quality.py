from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, SCRIPTS, load_module, write_json


script_quality = load_module("script_quality", SCRIPTS / "script_quality.py")
short_drama = load_module("script_quality_short_drama", SCRIPTS / "short_drama_cli.py")


def base_contract() -> dict:
    return {
        "incomingState": {
            "knowledge": ["前情"], "power": [], "relationship": [], "physical": [], "activeAction": [],
            "emotional": [],
        },
        "objective": {"character": "甲", "desiredChange": "乙交出账本", "whyNow": "明早之前必须拿到"},
        "opposition": {"actorOrConstraint": "乙", "goal": "保住账本", "leverage": "账本在乙手里"},
        "causalEscalation": [{
            "becauseOf": "甲查到账本下落", "choice": "甲当面摊牌", "countermove": "乙扬言撕毁账本",
            "stateChange": "账本变成双方必争之物", "nextPressure": "谁先动手谁暴露",
        }],
        "localDramaticResult": {"goalOutcome": "拿到一半", "stateChange": "乙被迫承认账本存在", "costPaid": "甲暴露了自己的线人"},
        "outgoingPressure": {"startedDecisionDangerOrQuestion": "乙会不会连夜转移账本", "whyItFollows": "乙已经知道甲在追账本"},
        "handoffState": {
            "knowledge": ["乙承认账本存在"], "power": [], "relationship": ["甲乙决裂"],
            "physical": [], "activeAction": ["乙准备转移账本"], "emotional": [],
        },
        "informationPermissions": [{
            "subject": "账本下落", "audience": "观众",
            "known": [], "suspected": [], "mistaken": [], "unknown": ["账本藏在何处"],
        }],
        "emotionalHook": "乙会不会连夜把账本转移走？",
        "endState": "账本从秘密变成公开争夺的目标",
        "hookActions": [],
    }


def episode(ep: int = 1, **overrides) -> dict:
    value = {
        "ep": ep, "targetSeconds": 120, "hook": "开场钩子", "cliff": "结尾悬念",
        "beatsClaimed": ["揭破"], "hookBeat": [1, 1],
        "scenes": [{
            "sceneId": "S01", "characters": ["C01"],
            "flow": [
                {"action": "甲推开办公室的门，把一份复印件拍在桌上。"},
                {"speaker": "C01", "line": "账本在哪。", "delivery": "逼问"},
                {"action": "乙站起来，手按在公文包上。"},
            ],
        }],
        "contract": base_contract(),
    }
    value.update(overrides)
    return value


class ScriptQualityTests(unittest.TestCase):
    def test_concrete_audience_question_accepts_valid_hooks(self):
        for text in [
            "乙会不会连夜把账本转移走？",
            "箱子里到底藏着谁的秘密？",
            "她会在天亮前把他交给警察吗？",
            "他还能算出对的数吗？",
        ]:
            self.assertTrue(script_quality.has_concrete_audience_question(text), text)

    def test_concrete_audience_question_rejects_labels_and_trivia(self):
        for text in [
            "怅然若失",
            "下集揭晓",
            "晚饭吃什么？",
            "关系更紧张了",
            "",
        ]:
            self.assertFalse(script_quality.has_concrete_audience_question(text), text)

    def test_contract_validation_requires_all_fields(self):
        script = {"episodes": [episode()]}
        self.assertEqual([], script_quality.validate_episode_contracts(script))
        broken = copy.deepcopy(script)
        del broken["episodes"][0]["contract"]["objective"]
        errors = script_quality.validate_episode_contracts(broken)
        self.assertEqual(1, len(errors))
        self.assertIn("objective", errors[0])

    def test_contract_validation_rejects_mood_label_hook(self):
        script = {"episodes": [episode()]}
        script["episodes"][0]["contract"]["emotionalHook"] = "怅然若失"
        errors = script_quality.validate_episode_contracts(script)
        self.assertTrue(any("emotionalHook" in item for item in errors))

    def test_advance_without_evidence_is_hard_error(self):
        script = {"episodes": [episode()]}
        script["episodes"][0]["contract"]["hookActions"] = [
            {"hookId": "H-001", "action": "advance", "description": "账本线索逼近", "evidence": []},
        ]
        errors = script_quality.validate_episode_contracts(script)
        self.assertTrue(any("证据" in item for item in errors))

    def test_missing_contract_is_hard_error(self):
        script = {"episodes": [episode()]}
        del script["episodes"][0]["contract"]
        errors = script_quality.validate_episode_contracts(script)
        self.assertTrue(any("contract" in item for item in errors))

    def test_handoff_chain_accepts_subset_and_previous_helpers(self):
        first = episode(ep=4)
        second = episode(ep=5)
        first["contract"]["incomingState"] = {bucket: [] for bucket in base_contract()["incomingState"]}
        first["contract"]["incomingState"]["knowledge"] = ["跨批事实", "本集补充"]
        first["contract"]["handoffState"] = {bucket: [] for bucket in base_contract()["handoffState"]}
        first["contract"]["handoffState"]["knowledge"] = ["同批事实"]
        second["contract"]["incomingState"] = {bucket: [] for bucket in base_contract()["incomingState"]}
        second["contract"]["incomingState"]["knowledge"] = ["同批事实", "下一集补充"]
        previous_state = {bucket: [] for bucket in base_contract()["handoffState"]}
        previous_state["knowledge"] = ["跨批事实"]
        script = {"episodes": [first, second]}
        self.assertEqual([], script_quality.validate_handoff_chain(script, previous_state))
        self.assertEqual(
            [],
            script_quality.validate_handoff_chain(script, {"handoff_state": previous_state}),
        )
        self.assertEqual(
            [],
            script_quality.validate_handoff_chain(
                script,
                {"episodes": [{"ep": 3, "contract": {"handoffState": previous_state}}]},
            ),
        )

    def test_handoff_chain_rejects_missing_cross_and_same_batch_facts(self):
        first = episode(ep=4)
        second = episode(ep=5)
        first["contract"]["incomingState"]["knowledge"] = []
        first["contract"]["handoffState"]["knowledge"] = ["同批事实"]
        second["contract"]["incomingState"]["knowledge"] = []
        previous = copy.deepcopy(base_contract()["handoffState"])
        previous["knowledge"] = ["跨批事实"]
        errors = script_quality.validate_handoff_chain(
            {"episodes": [first, second]}, {"handoff_state": previous},
        )
        self.assertTrue(any("跨批事实" in item for item in errors))
        self.assertTrue(any("同批事实" in item for item in errors))

    def test_information_permission_buckets_are_mutually_exclusive(self):
        ep = episode()
        permission = ep["contract"]["informationPermissions"][0]
        permission["known"] = ["账本在柜中"]
        permission["suspected"] = ["账本在柜中"]
        errors = script_quality.validate_episode_contracts({"episodes": [ep]})
        self.assertTrue(any("不能同时属于 known 与 suspected" in item for item in errors))

    def test_contract_rejects_character_name_as_hook_evidence(self):
        ep = episode()
        ep["scenes"][0]["characters"] = ["沈知微"]
        ep["contract"]["hookActions"] = [{
            "hookId": "H-001", "action": "advance", "description": "伪证推进", "evidence": ["沈知微"],
        }]
        errors = script_quality.validate_episode_contracts({"episodes": [ep]})
        self.assertTrue(any("角色名" in item for item in errors))

        current = episode()
        current["scenes"][0]["flow"][1]["delivery"] = "低声"
        issues = script_quality.check_delivery_strategy(current)
        self.assertEqual(1, len(issues))
        self.assertEqual("warning", issues[0]["severity"])
        current["scenes"][0]["flow"][1]["delivery"] = "逼问"
        self.assertEqual([], script_quality.check_delivery_strategy(current))

    def test_cross_episode_repeat_warns_on_shared_surface(self):
        previous = episode(ep=1)
        current = episode(ep=2)
        current["scenes"][0]["flow"].insert(0, {"action": "甲推开办公室的门，把一份复印件拍在桌上。"})
        previous["scenes"][0]["flow"].insert(0, {"action": "甲推开办公室的门，把一份复印件拍在桌上。"})
        issues = script_quality.check_cross_episode_repeat(
            current, [script_quality.surface_of_episode(previous)]
        )
        self.assertTrue(any(item["gate"] == "cross-episode-repeat" for item in issues))

    def test_behavior_signature_overlap_warns(self):
        previous = episode(ep=1)
        previous["scenes"][0]["flow"] = [
            {"action": "甲打开保险柜检查账目，翻看每一页。"},
            {"action": "甲打开抽屉查看合同。"},
        ]
        current = episode(ep=2)
        current["scenes"][0]["flow"] = [
            {"action": "乙打开文件柜检查合同，翻看最后一页，随即起身。"},
        ]
        issues = script_quality.check_cross_episode_repeat(
            current, [script_quality.surface_of_episode(previous)]
        )
        self.assertTrue(any(item["gate"] == "behavior-repeat" for item in issues))

    def test_payoff_rotation_warns_on_consecutive_same_type(self):
        previous = episode(ep=1)
        previous["beatsClaimed"] = ["打脸"]
        current = episode(ep=2)
        current["beatsClaimed"] = ["打脸", "揭破"]
        issues = script_quality.check_payoff_rotation(current, [{"打脸"}])
        self.assertEqual(1, len(issues))
        self.assertEqual([], script_quality.check_payoff_rotation(current, [{"兑现"}]))

    def test_ai_tells_warn_on_marker_density_and_meta_narration(self):
        current = episode()
        current["scenes"][0]["flow"] = [
            {"action": "仿佛有一道影子，忽然从走廊尽头闪过，竟然没有发出一点声音。"},
            {"action": "接下来，故事发展到了谁都没想到的地步。"},
        ]
        issues = script_quality.check_ai_tells(current)
        gates = {item["gate"] for item in issues}
        self.assertIn("surprise-marker-density", gates)
        self.assertIn("meta-narration", gates)

    def test_derive_previous_handoff_reads_predecessor_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = {"artifacts": [{
                "artifact_id": "ART-001", "type": "screenplay", "revision": 1, "status": "confirmed",
                "path": "script-v001.json", "depends_on": [], "source_refs": [],
                "scope": {"kind": "episodes", "start": 1, "end": 3}, "sha256": "x" * 64,
            }]}
            write_json(root / "script-v001.json", {"episodes": [episode(ep=1), episode(ep=2)]})
            handoff = short_drama.derive_previous_handoff(root, state, {"kind": "episodes", "start": 4, "end": 6})
            self.assertIsNotNone(handoff)
            self.assertEqual("ART-001", handoff["source_artifact_id"])
            self.assertEqual(base_contract()["handoffState"], handoff["handoff_state"])
            self.assertIsNone(short_drama.derive_previous_handoff(root, state, {"kind": "episodes", "start": 1, "end": 3}))
            self.assertIsNone(short_drama.derive_previous_handoff(root, state, {"kind": "episodes", "start": 5, "end": 6}))

    def test_run_script_quality_surfaces_canon_reveal_warnings(self):
        canon = {
            "schema_version": "1.0", "project_id": "PROJECT-001", "canon_version": 1,
            "claims": [{
                "claim_id": "CAN-001", "domain": "world", "claim_type": "secret_truth",
                "content": "老周的账册",
                "scope": {"applies_to": [], "excludes": []},
                "authority": {"source": "fixture", "priority": "soft"},
                "visibility": {"reader_known_from": 1, "character_known_by": [], "hidden_from": []},
                "relations": {"conflicts_with": [], "resolves_by": None, "depends_on": []},
                "constraints": {"non_generalizable": False, "requires_cost": [], "forbidden_uses": []},
                "status": "active", "status_updated_at_episode": None, "evidence": [],
            }],
            "candidates": [],
        }
        issues = script_quality.run_script_quality({"episodes": [episode(ep=1)]}, canon=canon)
        self.assertTrue(any(item["gate"] == "canon-reveal-missing" for item in issues))

    def test_script_quality_cli_accepts_canon_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            draft = temp / "draft.json"
            write_json(draft, {"episodes": [episode(ep=1)]})
            canon_doc = {
                "schema_version": "1.0", "project_id": "PROJECT-001", "canon_version": 1,
                "claims": [{
                    "claim_id": "CAN-001", "domain": "world", "claim_type": "secret_truth",
                    "content": "老周的账册",
                    "scope": {"applies_to": [], "excludes": []},
                    "authority": {"source": "fixture", "priority": "soft"},
                    "visibility": {"reader_known_from": 1, "character_known_by": [], "hidden_from": []},
                    "relations": {"conflicts_with": [], "resolves_by": None, "depends_on": []},
                    "constraints": {"non_generalizable": False, "requires_cost": [], "forbidden_uses": []},
                    "status": "active", "status_updated_at_episode": None, "evidence": [],
                }],
                "candidates": [],
            }
            write_json(temp / "canon.json", canon_doc)
            completed = subprocess.run([
                sys.executable, str(SCRIPTS / "short_drama_cli.py"), "script-quality",
                "--input", str(draft), "--canon", str(temp / "canon.json"),
            ], capture_output=True, text=True)
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            self.assertIn("canon-reveal-missing", completed.stdout)

    def test_script_quality_driver_reports_errors_and_warnings(self):
        script = {"episodes": [episode()]}
        issues = script_quality.run_script_quality(script)
        self.assertFalse(any(item["severity"] == "error" for item in issues))

    def test_script_quality_cli_exits_nonzero_on_contract_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            draft = Path(temp) / "draft.json"
            write_json(draft, {"episodes": [episode()]})
            del_json = copy.deepcopy({"episodes": [episode()]})
            del del_json["episodes"][0]["contract"]
            broken = Path(temp) / "broken.json"
            write_json(broken, del_json)
            completed = subprocess.run([
                sys.executable, str(SCRIPTS / "short_drama_cli.py"), "script-quality",
                "--input", str(broken),
            ], capture_output=True, text=True)
            self.assertNotEqual(0, completed.returncode)
            self.assertIn("error:", completed.stdout)
            completed = subprocess.run([
                sys.executable, str(SCRIPTS / "short_drama_cli.py"), "script-quality",
                "--input", str(draft),
            ], capture_output=True, text=True)
            self.assertEqual(0, completed.returncode)


if __name__ == "__main__":
    unittest.main()
