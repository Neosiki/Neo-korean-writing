# -*- coding: utf-8 -*-
"""v7 번역 충실성 감사 회귀 테스트."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import translation_audit  # noqa: E402


class TestTranslationAudit(unittest.TestCase):
    def test_identical_text_passes(self):
        text = "예산은 1,348억 원이다. GPT-4를 사용한다."
        data = translation_audit.audit_data(text, text, direction="same")
        self.assertEqual(data["status"], "pass")
        self.assertTrue(data["surface_lock"]["pass"])

    def test_missing_number_holds(self):
        source = "예산은 1,348억 원이며 GPT-4를 사용한다."
        target = "예산은 1,300억 원이며 GPT-4를 사용한다."
        data = translation_audit.audit_data(source, target, direction="same")
        self.assertEqual(data["status"], "hold")
        self.assertFalse(data["surface_lock"]["pass"])
        self.assertTrue(any(x["id"] == "FID-6" for x in data["risks"]))

    def test_en_to_ko_pronoun_injection_is_warned(self):
        source = "John sat down. He looked at his watch."
        target = "존은 앉았다. 그는 시계를 보았다. 그의 표정은 매우 불안했다. 정말 초조해 보였다."
        data = translation_audit.audit_data(source, target, direction="en-to-ko")
        ids = {x["id"] for x in data["risks"]}
        self.assertIn("FID-1", ids)
        self.assertIn("LIT-3", ids)

    def test_structure_change_holds(self):
        source = "- 하나\n- 둘\n"
        target = "하나와 둘이다.\n"
        data = translation_audit.audit_data(source, target, direction="same")
        self.assertEqual(data["status"], "hold")
        self.assertIn("bullet_items", {x["kind"] for x in data["structure"]["warnings"]})

    def test_literary_profile_is_contrastive(self):
        data = translation_audit.audit_data("A scene.", "한 장면이다.", direction="en-to-ko", literary=True)
        profile = data["literary_profile"]
        self.assertIn("contrastive", profile["baseline"])
        self.assertTrue(any("모호성" in item for item in profile["preserve"]))


if __name__ == "__main__":
    unittest.main()
