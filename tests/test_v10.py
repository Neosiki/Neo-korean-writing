from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import korean_writing  # noqa: E402


class DetectV10Tests(unittest.TestCase):
    def test_findings_include_exact_span_and_location(self):
        text = "첫 문장이다.\n\n이 방식은 혁신적이다."
        data = korean_writing.diagnose_data(text, "column")
        hit = next(item for item in data["findings"] if item["id"] == "G")
        self.assertEqual(hit["span"], "혁신적")
        self.assertEqual(hit["location"]["line"], 3)
        self.assertEqual(hit["location"]["paragraph"], 2)
        self.assertIn(hit["assessment"], {"clear", "contextual", "judgment_call"})

    def test_quoted_example_is_exempt(self):
        data = korean_writing.diagnose_data('예문은 “이 방식은 혁신적이다”이다.')
        self.assertFalse(any(item["id"] == "G" for item in data["findings"]))

    def test_empirical_keep_guards_reduce_false_positives(self):
        data = korean_writing.diagnose_data("판단의 기준은 이것이다. 결과를 통해 배운다.", "column")
        self.assertNotIn("A", {p["id"] for p in data["patterns"]})
        self.assertNotIn("C", {p["id"] for p in data["patterns"]})

    def test_context_fixtures_use_relaxations(self):
        fixture = ROOT / "tests/fixtures/false_positive"
        official = korean_writing.diagnose_data((fixture / "official.txt").read_text(encoding="utf-8"), "official")
        technical = korean_writing.diagnose_data((fixture / "technical.md").read_text(encoding="utf-8"), "technical")
        sns = korean_writing.diagnose_data((fixture / "sns.txt").read_text(encoding="utf-8"), "sns")
        self.assertNotIn("B", {p["id"] for p in official["patterns"]})
        self.assertNotIn("E", {p["id"] for p in technical["patterns"]})
        self.assertNotIn("I", {p["id"] for p in sns["patterns"]})


class PreservationV10Tests(unittest.TestCase):
    def test_code_and_url_changes_fail_protected_contract(self):
        before = "`timeout=3`을 쓴다. 출처: https://example.com/a"
        after = "`timeout=5`를 쓴다. 출처: https://example.com/b"
        data = korean_writing.preserve_data(before, after)
        self.assertFalse(data["protected_pass"])
        self.assertTrue({c["type"] for c in data["protected_changes"]} >= {"inline_code", "url"})

    def test_heading_and_path_changes_fail_protected_contract(self):
        before = "# 설치\n\n설정은 docs/config.yaml에 있다."
        after = "# 사용법\n\n설정은 docs/settings.yaml에 있다."
        data = korean_writing.preserve_data(before, after)
        self.assertTrue({c["type"] for c in data["protected_changes"]} >= {"heading", "file_path"})

    def test_new_p1_pattern_is_reported(self):
        before = "이 방식은 비용을 줄였다."
        after = "이 혁신적인 방식은 비용을 줄였다."
        data = korean_writing.preserve_data(before, after)
        self.assertTrue(any(item["id"] == "G" for item in data["residual_growth"]))


class StructureAndHandoffTests(unittest.TestCase):
    def test_template_slot_leak_is_clear_p0(self):
        data = korean_writing.structure_data("[도입]\n내용이다.\n\n[마무리]\n끝이다.")
        hit = next(item for item in data["findings"] if item["id"] == "S-2")
        self.assertEqual(hit["severity"], "P0")

    def test_handoff_template_is_valid(self):
        text = (ROOT / "templates/writer-editor-handoff.json").read_text(encoding="utf-8")
        data = korean_writing.handoff_data(text)
        self.assertTrue(data["pass"], data)
        self.assertEqual(data["summary"]["voice"], "preserve")

    def test_handoff_rejects_unknown_voice(self):
        data = json.loads((ROOT / "templates/writer-editor-handoff.json").read_text(encoding="utf-8"))
        data["voice"]["profile"] = "invented-persona"
        result = korean_writing.handoff_data(json.dumps(data, ensure_ascii=False))
        self.assertFalse(result["pass"])

    def test_handoff_accepts_yoon_reporter_voice(self):
        data = json.loads((ROOT / "templates/writer-editor-handoff.json").read_text(encoding="utf-8"))
        data["voice"]["profile"] = "yoon-reporter"
        result = korean_writing.handoff_data(json.dumps(data, ensure_ascii=False))
        self.assertTrue(result["pass"], result)

    def test_optional_morphology_degrades_without_changing_base_contract(self):
        data = korean_writing.morphology_data("형태소 분석은 선택 기능이다.")
        self.assertEqual(data["analyzer"], "kiwipiepy")
        self.assertIn("available", data)


if __name__ == "__main__":
    unittest.main()
