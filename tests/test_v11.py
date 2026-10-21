# -*- coding: utf-8 -*-
"""v11 군집 분석·분량 게이트 회귀 테스트."""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import korean_writing  # noqa: E402

HOT = ("혁신적인 변화가 새로운 지평을 열었다. 혁신적인 도약이 새로운 지평을 넓혔다. "
       "혁신적인 방식이 새로운 지평을 만들었다. ")
CLEAN = "오늘 아침 시장에서 사과 세 알을 샀다. 값은 오천 원이었고 주인은 덤으로 하나를 더 얹어 주었다. "


class TestClusters(unittest.TestCase):
    def test_hot_paragraph_detected_and_isolated_marked(self):
        text = "\n\n".join([CLEAN, HOT, CLEAN, CLEAN + "이를 통해 확인했다."])
        d = korean_writing.diagnose_data(text)
        c = d["clusters"]
        self.assertTrue(c["hot_paragraphs"], c)
        self.assertTrue(any(f.get("cluster") == "hot" for f in d["findings"]))
        self.assertIn(c["route"], {"paragraph_patch", "paragraph_rewrite"})

    def test_clean_text_has_no_hot_paragraphs(self):
        d = korean_writing.diagnose_data("\n\n".join([CLEAN] * 4))
        self.assertEqual(d["clusters"]["hot_paragraphs"], [])
        self.assertEqual(d["clusters"]["route"], "span_patch")

    def test_majority_hot_recommends_paragraph_rewrite(self):
        d = korean_writing.diagnose_data("\n\n".join([HOT, HOT, HOT, CLEAN]))
        self.assertEqual(d["clusters"]["route"], "paragraph_rewrite")


class TestSizeGate(unittest.TestCase):
    def _run(self, before, after):
        with tempfile.TemporaryDirectory() as d:
            b, a = os.path.join(d, "b.md"), os.path.join(d, "a.md")
            open(b, "w", encoding="utf-8").write(before)
            open(a, "w", encoding="utf-8").write(after)
            p = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "verify_gates.py"),
                                "--before", b, "--after", a], capture_output=True, text=True)
        return p.returncode, p.stdout

    def test_heavy_shrink_warns(self):
        before = CLEAN * 10
        code, out = self._run(before, CLEAN * 5)
        self.assertIn("P5 분량", out)
        self.assertIn("과삭제", out)
        self.assertGreaterEqual(code, 1)

    def test_same_size_is_ok(self):
        code, out = self._run(CLEAN * 4, CLEAN * 4)
        self.assertIn("[P5 분량] +0.0%", out)
        self.assertNotIn("과삭제", out)


if __name__ == "__main__":
    unittest.main()
