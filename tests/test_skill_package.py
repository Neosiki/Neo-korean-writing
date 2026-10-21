"""Provider-specific packaging must retain the workflow without duplicate entrypoints."""
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_skill_package as builder


class SkillPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "korean-writing").mkdir()
        (self.root / "SKILL.md").write_text("Read korean-writing/SKILL.md", encoding="utf-8")
        (self.root / "korean-writing/SKILL.md").write_text("Keep the complete writing workflow.", encoding="utf-8")
        self.files = [self.root / "SKILL.md", self.root / "korean-writing/SKILL.md"]

    def test_claude_has_one_entrypoint_and_workflow_reference(self):
        output = self.root / "claude.skill"
        builder.write_package(output, self.files, "claude", self.root)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(sum(Path(n).name == "SKILL.md" for n in archive.namelist()), 1)
            self.assertIn(b"korean-writing/workflow.md", archive.read("neo-korean-writing/SKILL.md"))
            self.assertEqual(archive.read("neo-korean-writing/korean-writing/workflow.md"), self.files[1].read_bytes())
            self.assertIsNone(archive.testzip())

    def test_codex_preserves_both_entrypoints(self):
        output = self.root / "codex.skill"
        builder.write_package(output, self.files, "codex", self.root)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(sum(Path(n).name == "SKILL.md" for n in archive.namelist()), 2)
            self.assertEqual(archive.read("neo-korean-writing/SKILL.md"), self.files[0].read_bytes())

    def test_claude_conversion_does_not_modify_sources(self):
        before = [p.read_bytes() for p in self.files]
        builder.write_package(self.root / "claude.skill", self.files, "claude", self.root)
        self.assertEqual(before, [p.read_bytes() for p in self.files])
