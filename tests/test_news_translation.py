"""Provenance guards and genuine numeric regressions from news review."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import evaluate_news_fixtures as news
import translation_audit as audit


class NewsTranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = json.loads(news.DEFAULT.read_text(encoding="utf-8"))

    def test_calendar_year_suffix_and_changed_year(self):
        source = "Confidence fell from 75% in 2022 to 55% this year."
        good = audit.audit_data(source, "신뢰는 2022년 75%에서 올해 55%로 낮아졌다.", "en-to-ko")
        wrong = audit.audit_data(source, "신뢰는 2023년 75%에서 올해 55%로 낮아졌다.", "en-to-ko")
        self.assertTrue(good["surface_lock"]["pass"])
        self.assertFalse(wrong["surface_lock"]["pass"])

    def test_percentage_points_are_equivalent_but_not_percent(self):
        source = "Margin is 3.9 percentage points."
        for target in ("오차는 3.9%포인트다.", "오차는 3.9퍼센트포인트다.", "오차는 3.9%p다."):
            with self.subTest(target=target):
                self.assertTrue(audit.audit_data(source, target, "en-to-ko")["surface_lock"]["pass"])
        self.assertFalse(audit.audit_data(source, "오차는 3.9%다.", "en-to-ko")["surface_lock"]["pass"])

    def test_duration_units_are_not_erased(self):
        self.assertEqual(audit.shared_locks("5 years")["number"], audit.shared_locks("5년")["number"])
        self.assertNotEqual(audit.shared_locks("5년")["number"], audit.shared_locks("5일")["number"])

    def test_news_regressions_expose_semantic_blind_spots(self):
        report = news.evaluate(self.fixtures)
        self.assertTrue(report["valid"])
        self.assertEqual(report["surface_false_positive_candidates"], 0)
        self.assertEqual(report["synthetic_mutations"], 12)
        # A population substitution leaves the exact same numeric tokens.
        poll = next(r for r in report["cases"] if r["id"] == "N21A")
        population = next(m for m in poll["mutations"] if m["authored_error"] == "population")
        self.assertTrue(population["surface_pass"])
        self.assertEqual(population["status"], "pass")

    def test_unlabelled_fake_translation_error_is_rejected(self):
        changed = copy.deepcopy(self.fixtures)
        changed["cases"][0]["mutations"][0]["synthetic"] = False
        self.assertFalse(news.evaluate(changed)["valid"])

    def test_overlong_quotation_and_missing_provenance_are_rejected(self):
        changed = copy.deepcopy(self.fixtures)
        changed["cases"][0]["source"] = "word " * 26
        changed["cases"][1]["access_scope"] = ""
        errors = news.validate(changed)
        self.assertTrue(any("quotation" in e for e in errors))
        self.assertTrue(any("access_scope" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
