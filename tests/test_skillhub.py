import os
import tempfile
import unittest
from pathlib import Path

import skillhub


class SkillHubTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "skills"
        self.source.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write_skill(self, rel, name, description="Demo description.", body="Generic workflow."):
        skill_dir = self.source / rel
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "\n".join(
                [
                    "---",
                    f"name: {name}",
                    f'description: "{description}"',
                    "version: 1.0.0",
                    "---",
                    "",
                    f"# {name}",
                    "",
                    body,
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return skill_dir

    def test_scan_finds_recursive_skills_and_skips_noise(self):
        self.write_skill("productivity/notes", "notes")
        self.write_skill("node_modules/noisy", "noisy")

        skills = skillhub.scan_skills(self.source)

        self.assertEqual([skill["name"] for skill in skills], ["notes"])
        self.assertEqual(skills[0]["relative_path"], "productivity/notes/SKILL.md")

    def test_detects_host_specific_skill(self):
        self.write_skill("agents/codex-runner", "codex-runner", body="Use Codex CLI for implementation.")

        skills = skillhub.scan_skills(self.source)

        self.assertIn("codex", skills[0]["hosts"])
        self.assertNotIn("claude", skills[0]["hosts"])

    def test_status_marks_missing_and_linked(self):
        skill_dir = self.write_skill("demo", "demo")
        target = self.root / "target"
        target.mkdir()
        os.symlink(skill_dir, target / "demo")

        statuses = skillhub.collect_status(self.source, "claude", target)

        self.assertEqual(statuses[0]["state"], "linked")

    def test_link_skills_creates_symlink_in_target(self):
        skill_dir = self.write_skill("demo", "demo")
        target = self.root / "target"

        actions = skillhub.sync_skills(self.source, "claude", target, mode="link")

        self.assertEqual(actions[0]["action"], "linked")
        self.assertEqual(os.path.realpath(target / "demo"), str(skill_dir.resolve()))

    def test_copy_skills_reports_current_status(self):
        self.write_skill("demo", "demo")
        target = self.root / "target"

        skillhub.sync_skills(self.source, "claude", target, mode="copy")
        statuses = skillhub.collect_status(self.source, "claude", target)

        self.assertEqual(statuses[0]["state"], "copied-current")


if __name__ == "__main__":
    unittest.main()
