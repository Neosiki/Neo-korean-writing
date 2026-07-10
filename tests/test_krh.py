# -*- coding: utf-8 -*-
"""krh.py 회귀 테스트. 실행: python3 -m unittest discover -s tests -v (저장소 루트에서)"""
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import krh  # noqa: E402

MACRO_SAMPLES = {
    "A": "이 문제는 정부에 의해 해결됐다.",
    "B": "이 정책은 참여를 제고하기 위해 마련됐다.",
    "C": "이것이 문제라는 점이다.",
    "D": "기술은 발전했고, 사회는 — 늘 그렇듯 — 뒤따랐다.",
    "E": "- **핵심:** 요약하면 이렇다.",
    "G": "이 기술은 혁신적이고 획기적이다.",
    "H": "이 약은 효과가 좋다고 평가받고 있다.",
    "I": "출시 축하 \U0001F680",
    "J": "또한, 아울러 다음을 검토한다.",
    "K": "흥미로운 점은 매출이 늘었다는 사실이다.",
    "L": "그렇다면 하나씩 살펴보자.",
    "M": "물론 효과가 있을 수 있다. 하지만 부작용 가능성도 배제할 수 없다.",
    "N": "아무도 말하지 않는 진짜 문제는 따로 있다.",
}

SUNNY_SAMPLES = {
    1: "효율적인 방식으로 처리했다.",
    2: "서비스의 개선의 방향을 잡았다.",
    3: "사용자들의 반응이 좋았다.",
    4: "이것이 문제라는 것이다.",
    5: "가능성이 있다는 점이 중요하다.",
    6: "큰 변화가 있었다.",
    7: "성공에 있어 중요한 요소다.",
}


class TestTaxonomy(unittest.TestCase):
    def test_macro_ids_A_to_N(self):
        P = krh.load_patterns()
        self.assertEqual([p["id"] for p in P["macro"]],
                         [chr(c) for c in range(ord("A"), ord("N") + 1)])

    def test_sunny_has_seven_rules(self):
        self.assertEqual(len(krh.load_patterns()["sunny"]), 7)

    def test_all_regex_compile(self):
        import re
        P = krh.load_patterns()
        for p in P["macro"]:
            for rx in p["regex"]:
                re.compile(rx)
        for r in P["sunny"]:
            re.compile(r["regex"])


class TestDiagnose(unittest.TestCase):
    def test_each_macro_pattern_fires(self):
        for pid, sample in MACRO_SAMPLES.items():
            d = krh.diagnose_data(sample)
            hit = {p["id"] for p in d["patterns"]}
            self.assertIn(pid, hit, f"패턴 {pid} 미탐지: {sample}")

    def test_clean_text_grades_A(self):
        clean = "이 제도는 시행 첫 해에만 세 번 개정됐다. 예산이 문제였다."
        d = krh.diagnose_data(clean)
        self.assertEqual(d["grade"], "A")

    def test_profile_relaxes_official(self):
        t = "이 정책은 참여를 제고하기 위해 마련됐다."
        strict = krh.diagnose_data(t)
        relaxed = krh.diagnose_data(t, profile="official")
        self.assertGreater(strict["signals"], relaxed["signals"])
        self.assertTrue(relaxed["relaxed"])


class TestSunny(unittest.TestCase):
    def test_each_sunny_rule_fires(self):
        for no, sample in SUNNY_SAMPLES.items():
            rows = {r["no"]: r for r in krh.sunny_data(sample)}
            self.assertGreater(rows[no]["density"], 0, f"Sunny {no} 미탐지: {sample}")


class TestPreserve(unittest.TestCase):
    A = '예산은 1,348억 원이며 "우리는 준비됐다"고 밝혔다. AI 도입은 실패할 수 있다. 효과가 없다.'

    def test_pass_when_facts_kept(self):
        b = '예산은 1,348억 원이다. "우리는 준비됐다"고 했다. AI 도입은 실패할 수 있다. 효과가 없다.'
        d = krh.preserve_data(self.A, b)
        self.assertTrue(d["surface_pass"])

    def test_fail_when_number_changed(self):
        b = self.A.replace("1,348억", "1,300억")
        d = krh.preserve_data(self.A, b)
        self.assertFalse(d["surface_pass"])
        self.assertEqual(d["missing"][0]["type"], "숫자")

    def test_warn_when_negation_dropped(self):
        a = "효과가 없다. 성공하지 않았다. 검증되지 않았다. 확실하지 않다."
        b = "효과가 있다. 성공했다. 검증됐다. 확실하다."
        d = krh.preserve_data(a, b)
        self.assertTrue(any(w["type"] == "부정 표현" for w in d["meaning_warnings"]))

    def test_warn_when_bullets_merged(self):
        a = "- 하나\n- 둘\n- 셋\n"
        b = "- 하나와 둘과 셋\n"
        d = krh.preserve_data(a, b)
        self.assertTrue(any(w["type"] == "불릿 항목" for w in d["meaning_warnings"]))


class TestDiffrate(unittest.TestCase):
    def test_identical_is_zero(self):
        d = krh.diffrate_data("같은 글이다. 전혀 다르지 않다.", "같은 글이다. 전혀 다르지 않다.")
        self.assertEqual(d["char_change_pct"], 0.0)
        self.assertEqual(d["sentence_change_pct"], 0.0)

    def test_rewrite_detected_at_sentence_level(self):
        a = "이 제도는 시행 첫 해에만 세 번 개정됐다."
        b = "완전히 다른 문장이 여기에 들어와 있다."
        d = krh.diffrate_data(a, b)
        self.assertGreater(d["sentence_change_pct"], 50)


class TestFormat(unittest.TestCase):
    def test_plain_text_passes(self):
        self.assertEqual(krh.format_data("별점 다섯 개를 줬다. 첫째, 빠르다.\n"), [])

    def test_markdown_and_emoji_fail(self):
        bad = krh.format_data("**볼드** 남은 글 \U0001F680\n")
        self.assertEqual(len(bad), 2)


if __name__ == "__main__":
    unittest.main()
