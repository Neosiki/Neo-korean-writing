"""v10.13: Threads casual register check, voice-profile casual class, apply-edits --check."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import korean_writing  # noqa: E402

CLI = [sys.executable, str(ROOT / "scripts" / "korean_writing.py")]
CASUAL = "오늘은 일찍 닫았어.\n---\n손님이 없더라고. 그래서 쉬었어.\n---\n내일은 열어 보려고 해."
FORMAL = "오늘은 일찍 닫았습니다.\n---\n손님이 없었습니다. 그래서 쉬었습니다.\n---\n내일은 열 예정입니다."


def ids(data):
    return [item["id"] for item in data["findings"]]


def run(*args):
    return subprocess.run(CLI + list(args), capture_output=True, text=True, encoding="utf-8")


class ThreadsRegisterTests(unittest.TestCase):
    def test_casual_posts_pass(self):
        data = korean_writing.channel_data(CASUAL, "threads")
        self.assertNotIn("CH-15", ids(data))
        self.assertEqual(data["status"], "pass")

    def test_formal_posts_are_flagged_as_warning(self):
        data = korean_writing.channel_data(FORMAL, "threads")
        hit = next(f for f in data["findings"] if f["id"] == "CH-15")
        self.assertEqual((hit["severity"], hit["basis"]), ("warn", "editorial"))
        self.assertEqual(data["status"], "warn")

    def test_quoted_formal_sentence_is_not_counted(self):
        text = "오늘은 일찍 닫았어.\n---\n손님이 「영업 종료입니다」라고 읽었어. 웃겼어.\n---\n내일은 열어 보려고 해."
        self.assertNotIn("CH-15", ids(korean_writing.channel_data(text, "threads")))

    def test_too_few_classified_sentences_are_not_judged(self):
        self.assertNotIn("CH-15", ids(korean_writing.channel_data("영업했습니다.", "threads")))

    def test_other_channels_are_unaffected(self):
        self.assertNotIn("CH-15", ids(korean_writing.channel_data(FORMAL, "facebook")))

    def test_register_spec_is_declared_for_threads_only(self):
        channels = korean_writing.load_channel_specs()["channels"]
        self.assertEqual(channels["threads"].get("register"), "casual")
        self.assertEqual([n for n, s in channels.items() if "register" in s], ["threads"])


class VoiceCasualTests(unittest.TestCase):
    def test_casual_ending_has_its_own_class(self):
        stats = korean_writing.voice_stats("오늘은 일찍 닫았어. 손님이 없더라고. 그래서 그냥 쉬었어.")
        self.assertEqual(stats["endings"]["casual"], 1.0)
        self.assertEqual(stats["endings"]["other"], 0.0)

    def test_existing_classes_are_unchanged(self):
        stats = korean_writing.voice_stats("가격은 매장마다 다르며 반찬도 다릅니다.")
        self.assertEqual(stats["endings"]["formal"], 1.0)
        self.assertEqual(stats["endings"]["casual"], 0.0)

    def test_compare_reports_casual_to_formal_drift(self):
        sample = " ".join(["오늘은 일찍 닫았어."] * 12 + ["손님이 없더라고."] * 12)
        draft = " ".join(["오늘은 일찍 닫았습니다."] * 6)
        result = korean_writing.voice_compare(korean_writing.voice_stats(sample),
                                              korean_writing.voice_stats(draft))
        self.assertEqual(result["status"], "drift")
        self.assertTrue(any("casual" in d["message"] for d in result["drift"]))


class ApplyCheckTests(unittest.TestCase):
    SOURCE = "# 제목\n\n매출은 120만 원이었습니다. 대부분의 손님이 단골입니다.\n"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.source = self.dir / "a.md"
        self.source.write_text(self.SOURCE, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def pairs(self, old, new):
        path = self.dir / "p.json"
        path.write_text(json.dumps([{"id": "E1", "old": old, "new": new}], ensure_ascii=False),
                        encoding="utf-8")
        return path

    def test_check_runs_preserve_after_apply(self):
        out = self.dir / "b.md"
        result = run("apply-edits", str(self.pairs("대부분의 손님이 단골입니다.", "손님 10명 중 7명이 단골입니다.")),
                     str(self.source), str(out), "--check")
        self.assertIn("자동 확인 (preserve)", result.stdout)
        self.assertIn("표면 잠금 통과", result.stdout)
        self.assertTrue(out.exists())

    def test_check_fails_when_a_number_is_lost(self):
        out = self.dir / "b.md"
        result = run("apply-edits", str(self.pairs("매출은 120만 원이었습니다.", "매출은 늘었습니다.")),
                     str(self.source), str(out), "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("표면 잠금 실패", result.stdout)

    def test_check_is_skipped_when_apply_fails(self):
        out = self.dir / "b.md"
        result = run("apply-edits", str(self.pairs("없는 문장", "x")), str(self.source), str(out), "--check")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("자동 확인", result.stdout)
        self.assertFalse(out.exists())

    def test_without_check_no_extra_run(self):
        out = self.dir / "b.md"
        result = run("apply-edits", str(self.pairs("대부분의 손님이 단골입니다.", "손님 10명 중 7명이 단골입니다.")),
                     str(self.source), str(out))
        self.assertNotIn("자동 확인", result.stdout)


if __name__ == "__main__":
    unittest.main()
