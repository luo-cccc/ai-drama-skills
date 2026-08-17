from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, SCRIPTS, load_module, write_json
from tests.test_script_quality import base_contract, episode


canon_mod = load_module("canon", SCRIPTS / "canon.py")
validator = load_module("canon_validator", SCRIPTS / "validate_project.py")


def base_canon(**overrides) -> dict:
    canon = {
        "schema_version": "1.0", "project_id": "PROJECT-001", "canon_version": 1,
        "claims": [], "candidates": [],
    }
    canon.update(overrides)
    return canon


def claim(claim_id: str = "CAN-001", claim_type: str = "temporary_state", content: str = "皮箱的秘密", **overrides) -> dict:
    value = {
        "claim_id": claim_id, "domain": "world", "claim_type": claim_type, "content": content,
        "scope": {"applies_to": [], "excludes": []},
        "authority": {"source": "fixture", "priority": "soft"},
        "visibility": {"reader_known_from": 1, "character_known_by": [], "hidden_from": []},
        "relations": {"conflicts_with": [], "resolves_by": None, "depends_on": []},
        "constraints": {"non_generalizable": False, "requires_cost": [], "forbidden_uses": []},
        "status": "active", "status_updated_at_episode": None, "evidence": [],
    }
    value.update(overrides)
    return value


class CanonTests(unittest.TestCase):
    def test_reveal_warning_fires_only_for_scheduled_episode(self):
        canon = base_canon(claims=[claim(
            claim_type="secret_truth", content="老周的账册",
            visibility={"reader_known_from": 1, "character_known_by": [], "hidden_from": []},
        )])
        ep = episode(ep=1)
        ep["scenes"][0]["flow"] = [{"action": "甲坐下来喝茶。"}]
        warnings = canon_mod.claim_reveal_warnings(canon, {"episodes": [ep]})
        self.assertEqual(1, len(warnings))
        self.assertIn("CAN-001", warnings[0])
        ep["scenes"][0]["flow"] = [{"action": "甲翻开老周的账册。"}]
        self.assertEqual([], canon_mod.claim_reveal_warnings(canon, {"episodes": [ep]}))
        self.assertEqual([], canon_mod.claim_reveal_warnings(canon, {"episodes": [episode(ep=2)]}))
        resolved = base_canon(claims=[claim(
            claim_type="secret_truth", content="老周的账册", status="resolved",
            visibility={"reader_known_from": 1, "character_known_by": [], "hidden_from": []},
        )])
        self.assertEqual([], canon_mod.claim_reveal_warnings(resolved, {"episodes": [ep]}))

    def test_merge_rejects_duplicate_ids_and_bumps_version(self):
        base = base_canon(claims=[claim("CAN-001")])
        incoming = base_canon(claims=[claim("CAN-001", content="另一个事实")])
        _, errors = canon_mod.merge_registered_canon(base, incoming)
        self.assertTrue(any("already registered" in item for item in errors))
        incoming = base_canon(claims=[claim("CAN-002", content="另一个事实")])
        merged, errors = canon_mod.merge_registered_canon(base, incoming)
        self.assertEqual([], errors)
        self.assertEqual(2, merged["canon_version"])
        self.assertEqual(2, len(merged["claims"]))

    def test_secret_truth_leak_gate(self):
        canon = base_canon(claims=[claim(
            claim_type="secret_truth", content="箱中装着旧案卷宗",
            visibility={"reader_known_from": 5, "character_known_by": [], "hidden_from": []},
        )])
        ep = episode(ep=2)
        ep["scenes"][0]["flow"] = [{"action": "甲打开箱盖，箱中装着旧案卷宗。"}]
        errors = canon_mod.claim_gate_errors(canon, ep)
        self.assertTrue(any("泄露" in item for item in errors))
        ep["scenes"][0]["flow"] = [{"action": "甲坐下来喝茶，什么也没说。"}]
        self.assertEqual([], canon_mod.claim_gate_errors(canon, ep))
        ep["ep"] = 6
        ep["scenes"][0]["flow"] = [{"action": "甲打开箱盖，箱中装着旧案卷宗。"}]
        self.assertEqual([], canon_mod.claim_gate_errors(canon, ep))

    def test_prohibition_gate(self):
        canon = base_canon(claims=[claim(claim_type="prohibition", content="不得动用私刑")])
        ep = episode(ep=1)
        ep["scenes"][0]["flow"] = [{"action": "甲动用私刑逼问船工。"}]
        errors = canon_mod.claim_gate_errors(canon, ep)
        self.assertTrue(any("禁令" in item for item in errors))
        ep["scenes"][0]["flow"] = [{"action": "甲坐下来喝茶。"}]
        self.assertEqual([], canon_mod.claim_gate_errors(canon, ep))

    def test_hard_rule_bypass_requires_cost(self):
        canon = base_canon(claims=[claim(
            claim_type="objective_rule", content="渡船夜航令",
            authority={"source": "fixture", "priority": "hard"},
            constraints={"non_generalizable": False, "requires_cost": ["罚银五十两"], "forbidden_uses": []},
        )])
        ep = episode(ep=1)
        ep["scenes"][0]["flow"] = [{"action": "甲动用渡船夜航令。"}]
        errors = canon_mod.claim_gate_errors(canon, ep)
        self.assertTrue(any("代价" in item for item in errors))
        ep["scenes"][0]["flow"] = [{"action": "甲下令夜航，当场缴了罚银五十两。"}]
        self.assertEqual([], canon_mod.claim_gate_errors(canon, ep))

    def test_non_generalizable_spread_gate(self):
        canon = base_canon(claims=[claim(
            content="沈知微的独门手法",
            constraints={"non_generalizable": True, "requires_cost": [], "forbidden_uses": []},
        )])
        ep = episode(ep=1)
        ep["scenes"][0]["flow"] = [{"action": "沈知微使出独门手法。"}]
        ep["contract"]["objective"]["desiredChange"] = "让所有人都学会"
        errors = canon_mod.claim_gate_errors(canon, ep)
        self.assertTrue(any("不可泛化" in item for item in errors))
        ep["contract"]["objective"]["desiredChange"] = "让周泊如一个人见识"
        self.assertEqual([], canon_mod.claim_gate_errors(canon, ep))

    def test_evolution_settles_and_records_visibility(self):
        canon = base_canon(claims=[claim()])
        ep = episode(ep=1)
        ep["contract"]["handoffState"]["knowledge"] = ["全船都知道箱里有秘密"]
        ep["contract"]["localDramaticResult"]["stateChange"] = "箱子变成公开目标"
        ep["scenes"][0]["flow"] = [{"action": "甲打开箱子，里面是皮箱的秘密。"}]
        ep["contract"]["informationPermissions"] = [{
            "subject": "箱中内容", "audience": "沈知微",
            "known": ["皮箱的秘密"], "suspected": [], "mistaken": [], "unknown": [],
        }]
        next_canon = canon_mod.derive_canon_updates(canon, {"episodes": [ep]})
        self.assertEqual("resolved", next_canon["claims"][0]["status"])
        self.assertEqual(1, next_canon["claims"][0]["status_updated_at_episode"])
        self.assertIn("沈知微", next_canon["claims"][0]["visibility"]["character_known_by"])
        self.assertEqual(2, next_canon["canon_version"])

    def test_secret_truth_settles_only_after_reveal(self):
        canon = base_canon(claims=[claim(
            claim_type="secret_truth", content="箱中装着旧案卷宗",
            visibility={"reader_known_from": 5, "character_known_by": [], "hidden_from": []},
        )])
        early = episode(ep=2)
        early["contract"]["handoffState"]["knowledge"] = ["箱中装着旧案卷宗"]
        early["scenes"][0]["flow"] = [{"action": "甲打开箱子，里面是箱中装着旧案卷宗。"}]
        next_canon = canon_mod.derive_canon_updates(canon, {"episodes": [early]})
        self.assertEqual("active", next_canon["claims"][0]["status"])
        late = episode(ep=5)
        late["contract"]["handoffState"]["knowledge"] = ["箱中装着旧案卷宗"]
        late["scenes"][0]["flow"] = [{"action": "甲掀开箱盖，箱中装着旧案卷宗。"}]
        next_canon = canon_mod.derive_canon_updates(canon, {"episodes": [late]})
        self.assertEqual("resolved", next_canon["claims"][0]["status"])

    def test_unclaimed_facts_become_candidates(self):
        canon = base_canon(claims=[claim()])
        ep = episode(ep=1)
        ep["contract"]["handoffState"]["knowledge"] = ["甲的真名是赵三"]
        next_canon = canon_mod.derive_canon_updates(canon, {"episodes": [ep]})
        self.assertEqual([{"fact": "甲的真名是赵三", "source_episode": 1}], next_canon["candidates"])

    def test_permanent_rules_and_prohibitions_never_resolve(self):
        for claim_type in ("objective_rule", "institution_rule", "prohibition"):
            with self.subTest(claim_type=claim_type):
                canon = base_canon(claims=[claim(claim_type=claim_type, content="渡船夜航令")])
                ep = episode(ep=1)
                ep["scenes"][0]["flow"] = [{"action": "甲下令渡船夜航令。"}]
                updated = canon_mod.derive_canon_updates(canon, {"episodes": [ep]})
                self.assertEqual("active", updated["claims"][0]["status"])

    def test_known_audience_updates_character_visibility_without_reader_reveal(self):
        canon = base_canon(claims=[claim(
            claim_type="secret_truth", content="箱中装着旧案卷宗",
            visibility={"reader_known_from": 5, "character_known_by": [], "hidden_from": []},
        )])
        ep = episode(ep=2)
        ep["contract"]["informationPermissions"] = [{
            "subject": "箱中内容", "audience": "沈知微",
            "known": ["箱中装着旧案卷宗"], "suspected": [], "mistaken": [], "unknown": [],
        }]
        updated = canon_mod.derive_canon_updates(canon, {"episodes": [ep]})
        self.assertEqual("active", updated["claims"][0]["status"])
        self.assertEqual(["沈知微"], updated["claims"][0]["visibility"]["character_known_by"])

    def test_contract_declaration_and_suspicion_do_not_settle_claim(self):
        canon = base_canon(claims=[claim(content="箱中装着旧案卷宗")])
        ep = episode(ep=1)
        ep["contract"]["handoffState"]["knowledge"] = ["箱中装着旧案卷宗"]
        ep["contract"]["informationPermissions"][0]["known"] = []
        ep["contract"]["informationPermissions"][0]["suspected"] = ["箱中装着旧案卷宗"]
        updated = canon_mod.derive_canon_updates(canon, {"episodes": [ep]})
        self.assertEqual("active", updated["claims"][0]["status"])

    def test_forbidden_use_is_a_hard_gate(self):
        canon = base_canon(claims=[claim(
            content="渡船夜航令",
            constraints={"non_generalizable": False, "requires_cost": [], "forbidden_uses": ["白天擅自开船"]},
        )])
        ep = episode(ep=1)
        ep["scenes"][0]["flow"] = [{"action": "甲白天擅自开船。"}]
        errors = canon_mod.claim_gate_errors(canon, ep)
        self.assertTrue(any("forbidden_use" in item for item in errors))

    def test_refresh_promotes_candidates(self):
        canon = base_canon(candidates=[{"fact": "甲的真名是赵三", "source_episode": 2}])
        next_canon = canon_mod.refresh_canon(canon)
        self.assertEqual([], next_canon["candidates"])
        self.assertEqual(1, len(next_canon["claims"]))
        self.assertEqual("CAN-001", next_canon["claims"][0]["claim_id"])
        self.assertEqual("甲的真名是赵三", next_canon["claims"][0]["content"])

    def test_validate_canon_accepts_and_rejects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = {"project": {"project_id": "PROJECT-001"}}
            write_json(root / "canon.json", base_canon(claims=[claim()]))
            errors: list[str] = []
            validator.validate_canon(root, state, errors)
            self.assertEqual([], errors)
            tampered = base_canon(claims=[claim(), claim()])
            write_json(root / "canon.json", tampered)
            errors = []
            validator.validate_canon(root, state, errors)
            self.assertTrue(any("duplicate" in item for item in errors))

    def test_canon_cli_list(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_json(root / "canon.json", base_canon(claims=[claim()]))
            completed = subprocess.run([
                sys.executable, str(SCRIPTS / "short_drama_cli.py"), "canon",
                "--project-dir", str(root), "list",
            ], capture_output=True, text=True)
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(1, len(payload["claims"]))


if __name__ == "__main__":
    unittest.main()
