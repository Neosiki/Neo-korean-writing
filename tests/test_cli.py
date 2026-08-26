from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from neo_korean_writing import cli


class NeoKoreanWritingCliTests(unittest.TestCase):
    def test_packaged_engine_matches_source_scripts(self):
        engine_dir = ROOT / "src" / "neo_korean_writing" / "engine"
        source = (ROOT / "scripts" / "korean_writing.py").read_text(encoding="utf-8")
        packaged = (engine_dir / "korean_writing.py").read_text(encoding="utf-8")
        self.assertEqual(source, packaged.replace("from .translation_audit import main", "from translation_audit import main"))
        self.assertEqual(
            (ROOT / "scripts" / "translation_audit.py").read_text(encoding="utf-8"),
            (engine_dir / "translation_audit.py").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (ROOT / "scripts" / "patterns.json").read_text(encoding="utf-8"),
            (engine_dir / "patterns.json").read_text(encoding="utf-8"),
        )

    def test_assets_lists_prompt_and_template(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli.main(["assets"])
        self.assertEqual(code, 0)
        self.assertIn("standard-editing", output.getvalue())
        self.assertIn("editing-brief", output.getvalue())

    def test_show_prints_standard_prompt(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli.main(["show", "prompt", "standard-editing"])
        self.assertEqual(code, 0)
        self.assertIn("범용 한글 윤문 프롬프트", output.getvalue())
        self.assertIn("LOCK 항목", output.getvalue())

    def test_init_creates_selected_profile_and_common_templates(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            code = cli.main(["init", str(workspace), "--profile", "press-release"])
            self.assertEqual(code, 0)
            self.assertTrue((workspace / "prompts" / "press-release-editing.md").is_file())
            self.assertTrue((workspace / "templates" / "editing-brief.md").is_file())
            self.assertTrue((workspace / "templates" / "lock-register.md").is_file())
            self.assertTrue((workspace / "templates" / "editing-delivery.md").is_file())
            self.assertTrue((workspace / "README.md").is_file())

    def test_init_stops_before_partial_copy_when_workspace_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            (workspace / "README.md").write_text("기존 작업", encoding="utf-8")
            with self.assertRaises(SystemExit):
                cli.main(["init", str(workspace)])
            self.assertFalse((workspace / "prompts").exists())
            self.assertFalse((workspace / "templates").exists())

    def test_verify_preserves_identical_text(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "original.md"
            revised = Path(directory) / "revised.md"
            content = "2026년 8월 26일, NextAI는 \"한글 글쓰기\"를 공개했다."
            original.write_text(content, encoding="utf-8")
            revised.write_text(content, encoding="utf-8")
            code = cli.main(["verify", str(original), str(revised), "--strict"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
