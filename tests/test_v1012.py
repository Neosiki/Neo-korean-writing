"""v10.12: review-signals and apply-edits."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import edit_review  # noqa: E402

CLI = [sys.executable, str(ROOT / "scripts" / "korean_writing.py")]

SAMPLE = """# 제목

첫 문단입니다. 이 문장은 길지 않습니다.

둘째 문단입니다. 대부분의 사장님은 광고를 따로 하지 않습니다.
"""


def codes(data):
    return [item["code"] for item in data["findings"]]


def run(*args):
    return subprocess.run(CLI + list(args), capture_output=True, text=True, encoding="utf-8")


class SignalTests(unittest.TestCase):
    def test_quantity_claim_without_number(self):
        data = edit_review.signals_data(SAMPLE)
        self.assertIn("SIG-1", codes(data))

    def test_quantity_claim_with_number_is_not_flagged(self):
        data = edit_review.signals_data("대부분의 가게 12곳이 문을 닫았습니다.\n")
        self.assertNotIn("SIG-1", codes(data))

    def test_always_word_is_flagged_only_as_a_word(self):
        self.assertIn("SIG-1", codes(edit_review.signals_data("손님은 늘 같은 자리에 앉습니다.\n")))
        self.assertNotIn("SIG-1", codes(edit_review.signals_data("가게가 늘어났습니다.\n")))

    def test_quote_is_not_scanned_for_quantity(self):
        data = edit_review.signals_data("그는 「대부분 그렇다」고 적었습니다.\n")
        self.assertNotIn("SIG-1", codes(data))

    def test_third_person_self_reference_needs_first_person_text(self):
        mixed = "저는 매일 씁니다. 제가 아는 한 그렇습니다. 작가는 늘 고민합니다.\n"
        self.assertIn("SIG-2", codes(edit_review.signals_data(mixed)))
        third_only = "작가는 매일 씁니다. 작가는 고민합니다.\n"
        self.assertNotIn("SIG-2", codes(edit_review.signals_data(third_only)))

    def test_three_sentences_with_same_opening(self):
        text = "그래서 문을 열었다. 그래서 불을 켰다. 그래서 앉았다.\n"
        self.assertIn("SIG-3", codes(edit_review.signals_data(text)))

    def test_casual_register_is_recognized(self):
        text = "오늘은 일찍 닫았어. 손님이 없더라고. 그래서 쉬었어.\n"
        data = edit_review.signals_data(text)
        self.assertEqual(data["register"]["dominant"], "어체")

    def test_mixed_register_in_one_paragraph(self):
        text = ("오늘은 일찍 닫았어. 손님이 없더라고. 그래서 쉬었어.\n\n"
                "다음 날에는 문을 열었습니다. 손님이 왔습니다. 그래도 조용했어요.\n")
        data = edit_review.signals_data(text)
        self.assertIn("SIG-4", codes(data))

    def test_front_matter_and_code_are_ignored(self):
        text = "---\ntitle: 모두\n---\n\n```\n대부분\n```\n\n본문입니다.\n"
        self.assertEqual(codes(edit_review.signals_data(text)), [])

    def test_every_finding_is_a_candidate(self):
        for item in edit_review.signals_data(SAMPLE)["findings"]:
            self.assertEqual(item["basis"], "heuristic-candidate")


class ApplyTests(unittest.TestCase):
    def pair(self, old, new, ident="E1"):
        return {"id": ident, "old": old, "new": new}

    def test_single_replacement(self):
        out, rows, errors = edit_review.apply_data(
            [self.pair("대부분의 사장님은", "사장님 10명 중 7명은")], SAMPLE)
        self.assertEqual(errors, [])
        self.assertIn("사장님 10명 중 7명은 광고를", out)
        self.assertEqual(len(rows), 1)

    def test_text_outside_pair_is_unchanged(self):
        out, _, _ = edit_review.apply_data([self.pair("첫 문단입니다.", "첫 문단이에요.")], SAMPLE)
        self.assertEqual(out.replace("첫 문단이에요.", "첫 문단입니다."), SAMPLE)

    def test_refuses_zero_occurrences(self):
        out, _, errors = edit_review.apply_data([self.pair("없는 문장", "새 문장")], SAMPLE)
        self.assertIsNone(out)
        self.assertTrue(any("0회" in e for e in errors))

    def test_refuses_two_occurrences(self):
        out, _, errors = edit_review.apply_data(
            [self.pair("입니다", "이에요")], SAMPLE)
        self.assertIsNone(out)
        self.assertTrue(any("회 나옵니다" in e for e in errors))

    def test_refuses_identical_text(self):
        out, _, errors = edit_review.apply_data([self.pair("첫 문단입니다.", "첫 문단입니다.")], SAMPLE)
        self.assertIsNone(out)
        self.assertTrue(errors)

    def test_refuses_empty_old(self):
        out, _, errors = edit_review.apply_data([{"id": "E1", "old": "", "new": "x"}], SAMPLE)
        self.assertIsNone(out)
        self.assertTrue(errors)

    def test_refuses_overlapping_pairs(self):
        out, _, errors = edit_review.apply_data(
            [self.pair("대부분의 사장님은 광고를", "A", "E1"),
             self.pair("사장님은 광고를 따로", "B", "E2")], SAMPLE)
        self.assertIsNone(out)
        self.assertTrue(any("겹칩니다" in e for e in errors))

    def test_one_bad_pair_blocks_all(self):
        out, _, errors = edit_review.apply_data(
            [self.pair("첫 문단입니다.", "고침"), self.pair("없는 문장", "x", "E2")], SAMPLE)
        self.assertIsNone(out)
        self.assertEqual(len(errors), 1)

    def test_refuses_locked_span_unless_allowed(self):
        source = "그는 「대부분 그렇다」고 적었습니다.\n"
        out, _, errors = edit_review.apply_data([self.pair("대부분 그렇다", "모두 그렇다")], source)
        self.assertIsNone(out)
        self.assertTrue(any("보호 구간" in e for e in errors))
        out, _, errors = edit_review.apply_data(
            [self.pair("대부분 그렇다", "모두 그렇다")], source, allow_locked=True)
        self.assertEqual(errors, [])
        self.assertIn("모두 그렇다", out)

    def test_compare_reports_volume_and_numbers(self):
        before = "매출은 120만 원입니다.\n"
        after = "매출은 150만 원입니다. 이 문장은 새로 붙인 설명입니다. 이 문장도 붙였습니다.\n"
        report = edit_review.compare_data(before, after)
        self.assertTrue(report["volume_exceeded"])
        self.assertTrue(report["numbers_lost"])
        self.assertTrue(report["numbers_new"])


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.source = self.dir / "a.md"
        self.source.write_text(SAMPLE, encoding="utf-8")
        self.pairs = self.dir / "p.json"
        self.pairs.write_text(json.dumps(
            [{"id": "E1", "old": "대부분의 사장님은", "new": "사장님 10명 중 7명은"}],
            ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_review_signals_cli(self):
        result = run("review-signals", str(self.source), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SIG-1", [f["code"] for f in json.loads(result.stdout)["findings"]])

    def test_apply_edits_cli_writes_copy_and_keeps_source(self):
        out = self.dir / "b.md"
        result = run("apply-edits", str(self.pairs), str(self.source), str(out))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("사장님 10명 중 7명은", out.read_text(encoding="utf-8"))
        self.assertEqual(self.source.read_text(encoding="utf-8"), SAMPLE)

    def test_apply_edits_refuses_same_path(self):
        result = run("apply-edits", str(self.pairs), str(self.source), str(self.source))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.source.read_text(encoding="utf-8"), SAMPLE)

    def test_apply_edits_refuses_existing_output_without_overwrite(self):
        out = self.dir / "b.md"
        out.write_text("기존", encoding="utf-8")
        result = run("apply-edits", str(self.pairs), str(self.source), str(out))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(out.read_text(encoding="utf-8"), "기존")
        result = run("apply-edits", str(self.pairs), str(self.source), str(out), "--overwrite")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_apply_edits_writes_nothing_on_failure(self):
        bad = self.dir / "bad.json"
        bad.write_text(json.dumps([{"id": "E1", "old": "없는 문장", "new": "x"}], ensure_ascii=False),
                       encoding="utf-8")
        out = self.dir / "c.md"
        result = run("apply-edits", str(bad), str(self.source), str(out))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(out.exists())

    def test_apply_edits_json_summary(self):
        out = self.dir / "d.md"
        result = run("apply-edits", str(self.pairs), str(self.source), str(out), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["applied"], 1)
        self.assertIn(summary["status"], ("applied", "applied_with_flags"))


if __name__ == "__main__":
    unittest.main()
