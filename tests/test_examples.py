from __future__ import annotations

import json
import unittest

from tests.helpers import read_text


class ExampleDocumentationTests(unittest.TestCase):
    def test_synthetic_fidelity_evidence(self):
        phrase = "车还没走，人也不能丢"
        source = read_text("examples", "synthetic-short", "source-story.md")
        first = read_text("examples", "synthetic-short", "screenplay-v001.md")
        second = read_text("examples", "synthetic-short", "screenplay-v002.md")
        audit_first = read_text("examples", "synthetic-short", "audit-screenplay-v001.md")
        audit_second = read_text("examples", "synthetic-short", "audit-screenplay-v002.md")
        self.assertIn(phrase, source)
        self.assertNotIn(phrase, first)
        self.assertEqual(1, second.count(phrase))
        self.assertIn("检索为 0 次", audit_first)
        self.assertIn("精确检索 1 次", audit_second)

    def test_synthetic_bag_contents_are_concrete_in_source_and_brief(self):
        for relative_path in ("source-story.md", "production-brief-v001.md"):
            text = read_text("examples", "synthetic-short", relative_path)
            self.assertIn("降压药", text, relative_path)
            self.assertIn("住院押金单", text, relative_path)

    def test_synthetic_runtime_and_local_storyboard_boundary(self):
        state = json.loads(read_text("examples", "synthetic-short", "project-state.json"))
        plan = json.loads(read_text("examples", "synthetic-short", "shot-plan.json"))
        storyboard = read_text("examples", "synthetic-short", "storyboard-v001.md")

        self.assertEqual(360000, state["project"]["target_runtime_ms"])
        self.assertNotEqual("complete", state["stage"])
        self.assertEqual(360000, plan["target_runtime_ms"])
        self.assertEqual((0, 15000), (plan["timeline_start_ms"], plan["timeline_end_ms"]))
        self.assertTrue(all(shot["end_ms"] <= 15000 for shot in plan["shots"]))
        self.assertTrue(all("CHAR-004" in shot["assets"] for shot in plan["shots"]))
        self.assertIn("仅 SCN-005 的 0–15 秒局部分镜", storyboard)
        self.assertIn("不是全片逐镜头分镜", storyboard)

    def test_synthetic_assets_and_continuity_boundaries(self):
        manifest = json.loads(read_text("examples", "synthetic-short", "asset-manifest.json"))
        ledger = json.loads(read_text("examples", "synthetic-short", "continuity-ledger.json"))
        by_name = {asset["name"]: asset for asset in manifest["assets"]}

        for name in ("女儿", "老周", "末班车", "值班电台", "登记表", "墙钟", "学校礼堂"):
            self.assertIn(name, by_name)
        self.assertIn("functional-zones", by_name["学校礼堂"]["locked_fields"])
        self.assertIn("不生成固定外观", " ".join(by_name["老周"]["visual_dna"]["prohibited_drift"]))
        self.assertIn("不生成锁定车辆资产", " ".join(by_name["末班车"]["visual_dna"]["prohibited_drift"]))

        events = ledger["scopes"][0]["events"]
        event_assets = {event["asset_id"] for event in events}
        self.assertTrue({"PROP-001", "PROP-002", "PROP-003"}.issubset(event_assets))
        self.assertIn("school-hall-exterior", json.dumps(ledger, ensure_ascii=False))

    def test_synthetic_scene_titles_and_bus_causality(self):
        outline = read_text("examples", "synthetic-short", "scene-outline-v001.md")
        screenplay = read_text("examples", "synthetic-short", "screenplay-v002.md")
        self.assertIn("| 5 | 外景 学校礼堂门外 - 夜", outline)
        self.assertIn("## 场 5｜外景 学校礼堂门外 - 夜", screenplay)
        self.assertIn("驶出出口后在安全区靠边", outline)
        self.assertIn("避免在出口急停", screenplay)

    def test_legacy_assets_are_explicitly_noncanonical_inventory(self):
        state = json.loads(read_text("examples", "legacy-yiqiyang", "project-state.json"))
        inventory = read_text("examples", "legacy-yiqiyang", "asset-manifest-v001.md")
        manifest = json.loads(read_text("examples", "legacy-yiqiyang", "asset-manifest.json"))
        asset_artifact = next(item for item in state["artifacts"] if item["path"] == "asset-manifest.json")

        self.assertIn("legacy noncanonical inventory", inventory)
        self.assertIn("canonical subset", inventory)
        self.assertEqual("canonical-subset", asset_artifact["scope"])
        self.assertLess(len(manifest["assets"]), 20)

    def test_legacy_storyboard_active_and_superseded_boundaries(self):
        state = json.loads(read_text("examples", "legacy-yiqiyang", "project-state.json"))
        scene_plan = read_text("examples", "legacy-yiqiyang", "storyboard-scene-v001.md")
        detail_plan = read_text("examples", "legacy-yiqiyang", "storyboard-scenes-048-050-v001.md")
        by_path = {item["path"]: item for item in state["artifacts"]}

        self.assertEqual("superseded", by_path["storyboard-scene-v001.md"]["status"])
        self.assertEqual("confirmed", by_path["storyboard-scenes-048-050-v001.md"]["status"])
        self.assertIn("151 秒方案", scene_plan)
        self.assertIn("superseded timing draft", scene_plan)
        self.assertIn("291 秒", detail_plan)
        self.assertIn("active for scenes 48–50", detail_plan)
        self.assertIn("场 1–47、51–52", detail_plan)
        self.assertIn("非 AI-ready", detail_plan)

    def test_readme_does_not_call_synthetic_sample_full_pipeline(self):
        readme = read_text("README.md")
        self.assertNotIn("合成全链路项目", readme)
        self.assertNotRegex(readme, r"synthetic-short/[^\n]*全链路")


if __name__ == "__main__":
    unittest.main()
