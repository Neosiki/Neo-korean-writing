# -*- coding: utf-8 -*-
"""Grok v10.2 인계 제안을 재검증하는 자체 예문 회귀 테스트.

예문은 코퍼스에서 관찰한 현상을 재현하도록 새로 지은 문장이며 기사 원문을 옮기지 않았다.
"""
import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import korean_writing  # noqa: E402
import translation_audit as ta  # noqa: E402


def missing(src, tgt):
    return {(m["kind"], m["value"]) for m in ta.audit_data(src, tgt, "en-to-ko")["surface_lock"]["missing"]}


class TestSurfaceLockReconcile(unittest.TestCase):
    def test_korean_counter_matches_bare_number(self):
        src = "More than 2,500 people were detained in 2025."
        tgt = "2025년 2500명 이상이 구금됐다."
        self.assertEqual(missing(src, tgt), set())

    def test_man_scale_matches(self):
        src = "Around 550,000 people marched."
        tgt = "약 55만명이 행진했다."
        d = ta.audit_data(src, tgt, "en-to-ko")
        self.assertEqual(d["surface_lock"]["missing"], [])
        # v9.5부터 만·억 표기는 값 정규화 단계에서 같은 토큰이 되므로 조정 목록이 아니라 추가 토큰도 남지 않는다.
        self.assertEqual(d["surface_lock"]["extra"], [])

    def test_range_hyphen_is_not_negative_sign(self):
        src = "The target is 4.5%-5% this year."
        tgt = "올해 목표는 4.5%~5%다."
        self.assertEqual(missing(src, tgt), set())

    def test_localized_acronym(self):
        src = "The US envoy met the UK PM."
        tgt = "미국 특사가 영국 총리를 만났다."
        self.assertEqual(missing(src, tgt), set())

    def test_parenthetical_conversion_not_silently_dropped(self):
        src = "The moon is about 20km (12 miles) wide; surplus hit $1.2tn (£900bn)."
        tgt = "이 위성의 지름은 약 20km다. 흑자는 1.2조달러였다."
        d = ta.audit_data(src, tgt, "en-to-ko")
        self.assertTrue(d["surface_lock"]["missing"])
        self.assertEqual(d["status"], "hold")

    def test_clock_conversion(self):
        src = "A curfew runs from 23:00 local time to 06:00."
        tgt = "통행금지는 현지 시각 오후 11시부터 오전 6시까지다."
        self.assertEqual(missing(src, tgt), set())

    def test_real_omission_still_held(self):
        src = "At least 10 people were killed and 226 lawmakers were warned."
        tgt = "여러 명이 숨졌다."
        d = ta.audit_data(src, tgt, "en-to-ko")
        vals = {m["value"] for m in d["surface_lock"]["missing"]}
        self.assertTrue({"10", "226"} <= vals)
        self.assertEqual(d["status"], "hold")

    def test_wrong_number_with_counter_not_reconciled(self):
        src = "About 1,000 officers were hurt."
        tgt = "경찰 100명이 다쳤다."
        self.assertFalse(ta.audit_data(src, tgt, "en-to-ko")["surface_lock"]["pass"])

    def test_same_direction_unchanged(self):
        d = ta.audit_data("2025년 보고서", "2025 보고서", "same")
        self.assertEqual(d["surface_lock"]["reconciled"], [])


class TestNewsCommaGuard(unittest.TestCase):
    SPARSE = ("정부는 새 대책을 내놓았으며, 시행 시기는 다음 달로 잡았다. " + "관계자는 세부 내용을 곧 공개하겠다고 말했다. " * 12)
    DENSE = "그는 웃었으며, 울었으며, 걸었으며, 뛰었으며, 다시 앉았다. "

    def _d(self, text, profile):
        return [f for f in korean_writing.diagnose_data(text, profile)["findings"] if f["id"] == "D"]

    def test_sparse_comma_relaxed_for_article(self):
        self.assertEqual(self._d(self.SPARSE, "article"), [])
        self.assertEqual(self._d(self.SPARSE, "translation"), [])

    def test_default_profile_unchanged(self):
        self.assertTrue(self._d(self.SPARSE, None))

    def test_dense_comma_still_flagged(self):
        self.assertTrue(self._d(self.DENSE, "article"))

    def test_em_dash_kept(self):
        self.assertTrue(self._d("결론은 하나다 — 다시 시작한다. " + "평범한 문장이다. " * 10, "article"))


class TestGlossaryTemplate(unittest.TestCase):
    def test_template_does_not_impose_a_universal_spacing_rule(self):
        entries = ta.load_glossary(os.path.join(ROOT, "templates", "translation-glossary.tsv"))
        res = ta.glossary_check("Victoria police said.", "빅토리아 주 경찰이 밝혔다.", entries)
        self.assertFalse(res["issues"])


class TestIntegrationSafety(unittest.TestCase):
    def test_am_pm_reversal_is_held(self):
        d = ta.audit_data("The shop closes at 23:00.", "매장은 오전 11시에 닫는다.", "en-to-ko")
        self.assertFalse(d["surface_lock"]["pass"])
        self.assertEqual(d["status"], "hold")

    def test_unqualified_twelve_hour_clock_is_held(self):
        self.assertTrue(missing("Closes at 23:00.", "11시에 닫는다."))

    def test_midnight_and_noon_remain_distinct(self):
        self.assertEqual(missing("Opens at 00:00.", "오전 12시에 연다."), set())
        self.assertTrue(missing("Opens at 00:00.", "오후 12시에 연다."))

    def test_minutes_cannot_be_borrowed_from_another_clock(self):
        self.assertTrue(missing("Opens at 09:30 and closes at 17:45.", "오전 9시 45분에 열고 오후 5시 30분에 닫는다."))

    def test_repeated_clock_count_preserved(self):
        self.assertTrue(missing("At 23:00 today and 23:00 tomorrow.", "오늘 오후 11시다."))

    def test_decimal_point_is_not_a_clock(self):
        self.assertEqual(ta.number_tokens("1.50"), ["1.50"])

    def test_timezone_parenthesis_remains_locked(self):
        self.assertTrue(missing("At 23:00 (21:00 GMT).", "오후 11시다."))

    def test_numbers_inside_parentheses_are_not_waived(self):
        d = ta.audit_data("A walk (12 people, 5 miles) starts here.", "여기서 걷기를 시작한다.", "en-to-ko")
        self.assertEqual(d["status"], "hold")

    def test_pm_without_political_context_is_not_prime_minister(self):
        self.assertIn(("acronym", "PM"), missing("Check PM status.", "총리 상태를 확인한다."))

    def test_one_political_pm_cannot_cover_two_pm_occurrences(self):
        self.assertIn(("acronym", "PM"), missing("The UK PM checks PM status.", "영국 총리는 총리 상태를 확인한다."))

    def test_correct_clock_with_minutes_matches(self):
        self.assertEqual(missing("At 13:45.", "오후 1시 45분이다."), set())

    def test_baseline_uses_the_same_localization_policy(self):
        source = "The US envoy met the UK PM."
        baseline = "US 특사가 UK PM을 만났다."
        target = "미국 특사가 영국 총리를 만났다."
        d = ta.audit_data(source, target, "en-to-ko", baseline=baseline)
        self.assertFalse(d["baseline_delta"]["surface_lock"]["introduced_missing"])
        self.assertTrue(any(r["id"] == "FID-14" and r["severity"] == "review" for r in d["risks"]))


if __name__ == "__main__":
    unittest.main()
