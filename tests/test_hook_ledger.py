from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, SCRIPTS, load_module, write_json
from tests.test_script_quality import base_contract, episode


hook_ledger_mod = load_module("hook_ledger", SCRIPTS / "hook_ledger.py")
short_drama = load_module("hook_ledger_short_drama", SCRIPTS / "short_drama_cli.py")
validator = load_module("hook_ledger_validator", SCRIPTS / "validate_project.py")


def outline_with_major_beats() -> dict:
    return {
        "params": {"episodes": 6, "minutesPerEpisode": 2},
        "characters": [], "scenes": [],
        "beats": [
            {"id": "B01", "type": "悬念钩", "weight": "minor", "episode": 1, "setup": "皮箱谁都不许碰", "payoff": "全船安静"},
            {"id": "B02", "type": "身份揭破", "weight": "major", "episode": 3, "setup": "右手始终揣在口袋里", "payoff": "砚底刻着县衙的印"},
            {"id": "B03", "type": "反转", "weight": "major", "episode": 5, "setup": "四十年不问客人来路", "payoff": "县城根本没有接应"},
            {"id": "B04", "type": "收束", "weight": "minor", "episode": 6, "setup": "雾开始散", "payoff": "皮箱当众打开"},
        ],
        "episodes": [
            {"ep": n, "synopsis": f"第 {n} 集梗概", "hook": "钩", "suspense": "悬", "sceneIds": ["S01"], "characterIds": ["C01"], "crowdPlan": "", "warnings": []}
            for n in range(1, 7)
        ],
    }


class HookLedgerTests(unittest.TestCase):
    def test_seed_from_major_beats_only(self):
        ledger = hook_ledger_mod.seed_hook_ledger(outline_with_major_beats(), "PROJECT-001", 6)
        self.assertEqual("1.0", ledger["schema_version"])
        self.assertEqual(1, ledger["ledger_version"])
        self.assertEqual(2, len(ledger["hooks"]))
        self.assertEqual(["H-001", "H-002"], [hook["hook_id"] for hook in ledger["hooks"]])
        self.assertEqual([3, 5], [hook["target_payoff_episode"] for hook in ledger["hooks"]])
        self.assertEqual([1, 2], [hook["planted_episode"] for hook in ledger["hooks"]])
        self.assertEqual(["mid-arc", "endgame"], [hook["timing"] for hook in ledger["hooks"]])

    def test_evidence_echoes(self):
        surface = "沈知微撕开信封，落款只有三个字。"
        self.assertTrue(hook_ledger_mod.evidence_echoes(surface, "撕开的信封"))
        self.assertTrue(hook_ledger_mod.evidence_echoes(surface, "落款只有三个字"))
        self.assertFalse(hook_ledger_mod.evidence_echoes(surface, "围观的船工"))

    def test_evidence_rejects_scattered_shared_characters(self):
        surface = "沈知微把旧印章收进袖中，转身离开。"
        self.assertFalse(hook_ledger_mod.evidence_echoes(surface, "微章转开"))

    def test_advance_requires_one_to_three_concrete_carriers(self):
        ledger = hook_ledger_mod.seed_hook_ledger(outline_with_major_beats(), "PROJECT-001", 6)
        for evidence in ([], ["甲"], ["C01"], ["印一", "印二", "印三", "印四"]):
            with self.subTest(evidence=evidence):
                ep1 = episode(ep=1)
                ep1["contract"]["hookActions"] = [{
                    "hookId": "H-001", "action": "advance", "description": "伪证推进", "evidence": evidence,
                }]
                next_ledger, errors = hook_ledger_mod.derive_hook_ledger(ledger, {"episodes": [ep1]})
                self.assertTrue(errors)
                self.assertEqual("open", next_ledger["hooks"][0]["status"])

    def test_advance_resolve_and_new_open(self):
        ledger = hook_ledger_mod.seed_hook_ledger(outline_with_major_beats(), "PROJECT-001", 6)
        ep1 = episode(ep=1)
        ep1["scenes"][0]["flow"] = [
            {"action": "甲撕开信封，落款只有三个字。"},
            {"speaker": "C01", "line": "县衙的印。", "delivery": "指认"},
        ]
        ep1["contract"]["hookActions"] = [
            {"hookId": "H-001", "action": "advance", "description": "信封线索逼近", "evidence": ["撕开的信封"]},
        ]
        next_ledger, errors = hook_ledger_mod.derive_hook_ledger(ledger, {"episodes": [ep1]})
        self.assertEqual([], errors)
        h1 = next(item for item in next_ledger["hooks"] if item["hook_id"] == "H-001")
        self.assertEqual("progressing", h1["status"])
        self.assertEqual(1, h1["last_advanced_episode"])

        ep2 = episode(ep=2)
        ep2["scenes"][0]["flow"] = [
            {"action": "甲把信封拍在桌上，落款三个字。"},
            {"action": "乙脸色变了，伸手去夺。"},
        ]
        ep2["contract"]["hookActions"] = [
            {"hookId": "H-001", "action": "resolve", "description": "落款指向县衙", "evidence": ["落款三个字"]},
            {"hookId": "[new]", "action": "open", "description": "砚底的印是谁刻的", "evidence": []},
        ]
        final_ledger, errors = hook_ledger_mod.derive_hook_ledger(next_ledger, {"episodes": [ep2]})
        self.assertEqual([], errors)
        h1 = next(item for item in final_ledger["hooks"] if item["hook_id"] == "H-001")
        self.assertEqual("resolved", h1["status"])
        self.assertEqual(2, h1["resolved_episode"])
        opened = [item for item in final_ledger["hooks"] if item["hook_id"] not in {"H-001", "H-002"}]
        self.assertEqual(1, len(opened))
        self.assertEqual("open", opened[0]["status"])
        self.assertEqual(2, opened[0]["planted_episode"])

    def test_unknown_id_and_resolved_reuse_are_errors(self):
        ledger = hook_ledger_mod.seed_hook_ledger(outline_with_major_beats(), "PROJECT-001", 6)
        ep1 = episode(ep=1)
        ep1["contract"]["hookActions"] = [
            {"hookId": "H-999", "action": "advance", "description": "幽灵引用", "evidence": []},
        ]
        _, errors = hook_ledger_mod.derive_hook_ledger(ledger, {"episodes": [ep1]})
        self.assertTrue(any("不存在" in item for item in errors))

        resolved = hook_ledger_mod.seed_hook_ledger(outline_with_major_beats(), "PROJECT-001", 6)
        for hook in resolved["hooks"]:
            hook["status"] = "resolved"
            hook["resolved_episode"] = 1
        ep1["contract"]["hookActions"] = [
            {"hookId": "H-001", "action": "advance", "description": "已收束再动", "evidence": []},
        ]
        _, errors = hook_ledger_mod.derive_hook_ledger(resolved, {"episodes": [ep1]})
        self.assertTrue(any("已收束" in item for item in errors))

    def test_unlanded_evidence_carrier_is_error(self):
        ledger = hook_ledger_mod.seed_hook_ledger(outline_with_major_beats(), "PROJECT-001", 6)
        ep1 = episode(ep=1)
        ep1["scenes"][0]["flow"] = [{"action": "甲坐下喝茶，什么也没发生。"}]
        ep1["contract"]["hookActions"] = [
            {"hookId": "H-001", "action": "advance", "description": "承诺未落地", "evidence": ["撕开的信封"]},
        ]
        _, errors = hook_ledger_mod.derive_hook_ledger(ledger, {"episodes": [ep1]})
        self.assertTrue(any("证据载体" in item for item in errors))

    def test_health_warns_on_stale_overdue_capacity_burst(self):
        ledger = hook_ledger_mod.seed_hook_ledger(outline_with_major_beats(), "PROJECT-001", 6)
        for hook in ledger["hooks"]:
            hook["status"] = "progressing"
        self.assertFalse(any(item["gate"] in {"hook-stale", "hook-overdue"} for item in hook_ledger_mod.hook_health(ledger)))

        stale = json.loads(json.dumps(ledger))
        for hook in stale["hooks"]:
            hook["planted_episode"] = 1
            hook["last_advanced_episode"] = 1
        stale["hooks"][0]["timing"] = "near-term"
        stale["hooks"][1]["timing"] = "mid-arc"
        stale["hooks"][1]["last_advanced_episode"] = 6
        warnings = hook_ledger_mod.hook_health(stale)
        self.assertTrue(any(item["gate"] == "hook-stale" for item in warnings))
        self.assertTrue(any(item["gate"] == "hook-overdue" for item in warnings))

        many = json.loads(json.dumps(stale))
        many["hooks"] = [
            {
                "hook_id": f"H-{index + 1:03d}", "name": f"债 {index}", "kind": "plot", "status": "open",
                "planted_episode": 1, "last_advanced_episode": 1, "timing": "mid-arc",
                "evidence_history": [],
            }
            for index in range(13)
        ]
        warnings = hook_ledger_mod.hook_health(many)
        self.assertTrue(any(item["gate"] == "hook-capacity" for item in warnings))

        burst = json.loads(json.dumps(stale))
        burst["hooks"][0]["status"] = "open"
        burst["hooks"][1]["status"] = "open"
        burst["hooks"][1]["planted_episode"] = 5
        burst["hooks"][1]["last_advanced_episode"] = 5
        burst["hooks"][1]["evidence_history"] = [{"episode": 5, "action": "open", "carriers": []}]
        burst["hooks"].append({
            "hook_id": "H-003", "name": "新开二", "kind": "plot", "status": "open",
            "planted_episode": 5, "last_advanced_episode": 5, "timing": "mid-arc",
            "evidence_history": [{"episode": 5, "action": "open", "carriers": []}],
        })
        warnings = hook_ledger_mod.hook_health(burst)
        self.assertTrue(any(item["gate"] == "hook-burst" for item in warnings))

    def test_completion_debt_blocks_old_hooks_and_exempts_finale(self):
        ledger = hook_ledger_mod.seed_hook_ledger(outline_with_major_beats(), "PROJECT-001", 6)
        self.assertEqual(["H-001", "H-002"], [item["hook_id"] for item in hook_ledger_mod.completion_debt(ledger, 6)])
        ledger["hooks"][0]["status"] = "resolved"
        ledger["hooks"][0]["resolved_episode"] = 3
        self.assertEqual(["H-002"], [item["hook_id"] for item in hook_ledger_mod.completion_debt(ledger, 6)])
        ledger["hooks"][1]["status"] = "deferred"
        self.assertEqual(["H-002"], [item["hook_id"] for item in hook_ledger_mod.completion_debt(ledger, 6)])
        ledger["hooks"][1]["status"] = "resolved"
        ledger["hooks"][1]["resolved_episode"] = 5
        finale_hook = {
            "hook_id": "H-003", "name": "终集悬念", "kind": "plot", "status": "open",
            "planted_episode": 6, "last_advanced_episode": 6, "timing": "endgame",
            "evidence_history": [],
        }
        ledger["hooks"].append(finale_hook)
        self.assertEqual([], hook_ledger_mod.completion_debt(ledger, 6))

    def test_validate_hook_ledger_accepts_and_rejects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = {"project": {"project_id": "PROJECT-001"}}
            good = hook_ledger_mod.seed_hook_ledger(outline_with_major_beats(), "PROJECT-001", 6)
            write_json(root / "hook-ledger.json", good)
            errors: list[str] = []
            validator.validate_hook_ledger(root, state, errors)
            self.assertEqual([], errors)
            tampered = json.loads(json.dumps(good))
            tampered["hooks"][0]["last_advanced_episode"] = 0
            write_json(root / "hook-ledger.json", tampered)
            errors = []
            validator.validate_hook_ledger(root, state, errors)
            self.assertTrue(any("precedes" in item for item in errors))

    def test_hook_ledger_cli_status_and_health(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_json(root / "hook-ledger.json", hook_ledger_mod.seed_hook_ledger(outline_with_major_beats(), "PROJECT-001", 6))
            for action in ("status", "health"):
                completed = subprocess.run([
                    sys.executable, str(SCRIPTS / "short_drama_cli.py"), "hook-ledger",
                    "--project-dir", str(root), action,
                ], capture_output=True, text=True)
                self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
                payload = json.loads(completed.stdout)
                if action == "health":
                    self.assertIn("health", payload)
                    self.assertIn("frontier_episode", payload)


if __name__ == "__main__":
    unittest.main()
