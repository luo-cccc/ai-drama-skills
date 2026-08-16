from __future__ import annotations

import unittest

from tests.helpers import host_absolute_paths, markdown_files, read_text


class ForwardAssetTests(unittest.TestCase):
    def test_forward_prompts_use_workspace_placeholder(self):
        prompts = markdown_files("tests", "forward-prompts")
        self.assertTrue(prompts)
        for path in prompts:
            text = path.read_text(encoding="utf-8")
            self.assertIn("<WORKSPACE_ROOT>", text, path.name)
            self.assertEqual([], host_absolute_paths(text), path.name)

    def test_forward_report_is_explicitly_legacy_and_not_revalidated(self):
        report = read_text("tests", "forward-test-report.md").upper()
        self.assertIn("STALE", report)
        self.assertIn("LEGACY", report)
        self.assertIn("FAIL", report)
        self.assertIn("NOT REVALIDATED", report)


if __name__ == "__main__":
    unittest.main()
