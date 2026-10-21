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
        packaged = packaged.replace("from .translation_audit import main", "from translation_audit import main")
        packaged = packaged.replace("from .context_audit import main", "from context_audit import main")
        self.assertEqual(source, packaged)
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
        self.assertIn("detect-only", output.getvalue())
        self.assertIn("editing-brief", output.getvalue())
        self.assertIn("writer-editor-handoff", output.getvalue())

    def test_show_prints_standard_prompt(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli.main(["show", "prompt", "standard-editing"])
        self.assertEqual(code, 0)
        self.assertIn("범용 한글 윤문 프롬프트", output.getvalue())
        self.assertIn("LOCK 항목", output.getvalue())

    def test_translation_profile_delivers_craft_review_and_brief(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "translation"
            self.assertEqual(cli.main(["init", str(workspace), "--profile", "translation"]), 0)
            prompt = workspace / "prompts" / "translation-craft-review.md"
            brief = workspace / "templates" / "translation-review-brief.md"
            self.assertTrue(prompt.is_file())
            self.assertTrue(brief.is_file())
            self.assertIn("조사 종료·보류 이유", brief.read_text(encoding="utf-8"))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli.main(["show", "prompt", "translation-craft-review"]), 0)
            self.assertEqual(output.getvalue().strip(), prompt.read_text(encoding="utf-8").strip())

    def test_news_profile_delivers_article_review_with_source_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "news"
            self.assertEqual(cli.main(["init", str(workspace), "--profile", "news-translation"]), 0)
            prompt = workspace / "prompts" / "news-translation-review.md"
            brief = workspace / "templates" / "translation-review-brief.md"
            self.assertTrue(prompt.is_file())
            self.assertIn("발행·수정·사건", brief.read_text(encoding="utf-8"))
            self.assertTrue((workspace / "prompts" / "translation-postediting.md").is_file())

    def test_init_creates_selected_profile_and_common_templates(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            code = cli.main(["init", str(workspace), "--profile", "press-release"])
            self.assertEqual(code, 0)
            self.assertTrue((workspace / "prompts" / "press-release-editing.md").is_file())
            self.assertTrue((workspace / "templates" / "editing-brief.md").is_file())
            self.assertTrue((workspace / "templates" / "lock-register.md").is_file())
            self.assertTrue((workspace / "templates" / "editing-delivery.md").is_file())
            self.assertTrue((workspace / "templates" / "writer-editor-handoff.json").is_file())
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

    def test_structure_and_handoff_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            draft = Path(directory) / "draft.md"
            draft.write_text("[도입]\n내용이다.", encoding="utf-8")
            handoff = ROOT / "templates" / "writer-editor-handoff.json"
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code_structure = cli.main(["structure", str(draft), "--json"])
                code_handoff = cli.main(["handoff-validate", str(handoff), "--json"])
        self.assertEqual(code_structure, 0)
        self.assertEqual(code_handoff, 0)
        self.assertIn('"S-2"', out.getvalue())
        self.assertIn('"pass": true', out.getvalue())

    def test_translation_cli_passes_glossary_and_strict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "s.md").write_text("A prompt.", encoding="utf-8")
            (root / "t.md").write_text("프롬프트.", encoding="utf-8")
            (root / "g.tsv").write_text("prompt\t지시문\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = cli.main(["translation-audit", str(root / "s.md"), str(root / "t.md"),
                                 "--glossary", str(root / "g.tsv"), "--strict", "--json"])
            self.assertEqual(code, 2)
            self.assertIn('"hold"', output.getvalue())

    def test_context_cli_loads_packaged_engine(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.md").write_text("생성 AI를 사용한다.", encoding="utf-8")
            manifest = {"version": 1, "documents": [{"id": "a", "path": "a.md"}],
                        "terms": [{"preferred": "생성형 AI", "variants": ["생성 AI"]}]}
            (root / "m.json").write_text(json.dumps(manifest), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = cli.main(["context-audit", str(root / "m.json"), "--json"])
            self.assertEqual(code, 0)
            self.assertIn("CTX-TERM", output.getvalue())

    def test_translation_cli_forwards_v9_baseline_and_intensity(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, text in (("s.md", "A short sentence."), ("t.md", "짧은 문장이다."),
                               ("baseline.md", "짧은 문장이다.")):
                (root / name).write_text(text, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = cli.main(["translation-audit", str(root / "s.md"), str(root / "t.md"),
                                 "--baseline", str(root / "baseline.md"), "--intensity", "보수", "--json"])
            self.assertIn(code, (0, 1))
            self.assertEqual(json.loads(output.getvalue())["post_edit_scope"]["intensity"], "보수")


if __name__ == "__main__":
    unittest.main()
