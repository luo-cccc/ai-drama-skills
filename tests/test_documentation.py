from __future__ import annotations

import re
import unittest
from pathlib import Path

from tests.helpers import ROOT


LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def maintained_markdown() -> list[Path]:
    files = [ROOT / "README.md", ROOT / "PROVENANCE.md"]
    for directory in (
        ROOT / "docs",
        ROOT / "shared" / "references",
        ROOT / "src" / "skills",
        ROOT / ".agents" / "skills",
        ROOT / "examples",
        ROOT / "tests",
    ):
        files.extend(directory.rglob("*.md"))
    files.extend([
        ROOT / "engine" / "kernels" / "MODIFICATIONS.md",
        ROOT / "engine" / "kernels" / "skills" / "novel-storyboard" / "SKILL.md",
        ROOT / "engine" / "kernels" / "skills" / "novel-storyboard" / "README.md",
        ROOT / "engine" / "kernels" / "skills" / "novel-storyboard" / "README.en.md",
        ROOT / "engine" / "kernels" / "skills" / "novel-storyboard" / "references" / "schema.md",
        ROOT / "engine" / "kernels" / "skills" / "novel-storyboard" / "references" / "h3-prompt.md",
    ])
    return sorted({path for path in files if path.is_file() and ".forward-runs" not in path.parts})


class DocumentationContractTests(unittest.TestCase):
    def test_local_markdown_links_resolve(self):
        missing: list[str] = []
        manifest = __import__("json").loads((ROOT / "skill-manifest.json").read_text(encoding="utf-8"))
        packaged_refs = {
            entry["name"]: set(entry.get("shared_references", []))
            for entry in manifest["skills"]
        }
        for path in maintained_markdown():
            text = path.read_text(encoding="utf-8")
            for raw_target in LINK_RE.findall(text):
                target = raw_target.strip().split("#", 1)[0]
                if not target or target.startswith(("http://", "https://", "mailto:", "<")):
                    continue
                portable = target.replace("%20", " ")
                resolved = (path.parent / portable).resolve()
                if resolved.exists():
                    continue
                parts = path.relative_to(ROOT).parts
                if len(parts) >= 4 and parts[:2] == ("src", "skills") and portable.startswith("references/"):
                    skill_name = parts[2]
                    reference_name = Path(portable).name
                    local = ROOT / "src" / "skills" / skill_name / portable
                    if local.is_file() or reference_name in packaged_refs.get(skill_name, set()):
                        continue
                missing.append(f"{path.relative_to(ROOT).as_posix()} -> {raw_target}")
        self.assertEqual([], missing)

    def test_v2_audit_language_is_canonical_json(self):
        corpus = "\n".join(path.read_text(encoding="utf-8") for path in maintained_markdown())
        self.assertNotIn("--audit-report <audit.md>", corpus)
        self.assertNotIn("audit-report-vNNN.md`, canonical", corpus)
        shared = (ROOT / "shared" / "references" / "evidence-audit.md").read_text(encoding="utf-8")
        self.assertIn("audit-report.schema.json", shared)
        self.assertIn("P0", shared)
        self.assertIn("P1", shared)
        self.assertIn("P2", shared)
        self.assertNotRegex(shared, r"(?m)^- `(?:fatal|high|optimize)`")

    def test_timeline_snapshot_projection_contract(self):
        timeline = (ROOT / "shared" / "references" / "timeline-contract.md").read_text(encoding="utf-8").lower()
        self.assertIn("immutable", timeline)
        self.assertIn("snapshot", timeline)
        self.assertIn("projection", timeline)
        self.assertIn("shot-plan.json", timeline)

    def test_examples_and_forward_evidence_are_scoped(self):
        examples = (ROOT / "examples" / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("schema v1", examples)
        self.assertIn("partial", examples)
        self.assertIn("legacy", examples)

    def test_delivery_and_modification_notices_are_packaged(self):
        manifest = (ROOT / "skill-manifest.json").read_text(encoding="utf-8")
        self.assertTrue((ROOT / "shared" / "references" / "delivery-contract.md").is_file())
        self.assertTrue((ROOT / "engine" / "kernels" / "MODIFICATIONS.md").is_file())
        self.assertIn('"delivery-contract.md"', manifest)
        self.assertIn('"target": "THIRD_PARTY_NOTICES/shuohao-MODIFICATIONS.md"', manifest)


if __name__ == "__main__":
    unittest.main()
