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


class TestV8Lane(unittest.TestCase):
    def test_allowed_term_does_not_hide_whole_english_sentence(self):
        self.assertTrue(translation_audit.english_residue(
            "Aside still needs a careful manual review", allowed=["Aside"]))

    def test_link_label_is_checked(self):
        self.assertIn("still needs manual translation", translation_audit.english_residue(
            "[still needs manual translation](https://example.org)"))

    def test_tilde_fence_is_not_english_residue(self):
        self.assertEqual(translation_audit.english_residue("~~~text\nthis is sample code\n~~~\n정상"), [])

    def test_placeholder_damage_is_critical_hold(self):
        source = "Hello, {name}! You have %d new <b>messages</b>."
        target = "안녕하세요, {이름}님! 새 메시지가 %d개 있습니다."
        data = translation_audit.audit_data(source, target, direction="en-to-ko")
        self.assertEqual(data["status"], "hold")
        ph = [r for r in data["risks"] if r["id"] == "FID-10"][0]
        self.assertEqual(ph["severity"], "critical")
        self.assertEqual(data["fix_order"][0], "FID-10")

    def test_severity_orders_fixes_critical_first(self):
        source = "Budget is 1,348 won. " + "The very big model works. " * 3
        target = "예산은 1,300원이다. 매우 정말 큰 모델이 작동한다. 에 의해 쓰인다."
        data = translation_audit.audit_data(source, target, direction="en-to-ko")
        ranks = [translation_audit.SEVERITY_RANK[r["severity"]] for r in data["risks"]]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(data["risks"][0]["severity"], "critical")
        self.assertGreater(data["mqm_heuristic"]["penalty"], 25)

    def test_glossary_missing_and_forbidden(self):
        source = "The large language model uses a prompt."
        target = "거대 언어 모델은 프롬프트를 사용한다."
        glossary = [
            {"source": "large language model", "targets": ["대규모 언어 모델"], "forbid": ["거대 언어 모델"]},
            {"source": "prompt", "targets": ["프롬프트"], "forbid": []},
        ]
        data = translation_audit.audit_data(source, target, direction="en-to-ko", glossary=glossary)
        kinds = {i["kind"] for i in data["glossary"]["issues"]}
        self.assertEqual(kinds, {"missing_target", "forbidden_variant"})
        self.assertEqual(data["glossary"]["applicable"], 2)
        self.assertTrue(any(r["id"] == "TERM-2" for r in data["risks"]))

    def test_glossary_clean_passes(self):
        data = translation_audit.audit_data(
            "A prompt.", "프롬프트 하나.", direction="en-to-ko",
            glossary=[{"source": "prompt", "targets": ["프롬프트"], "forbid": []}])
        self.assertEqual(data["glossary"]["issues"], [])

    def test_glossary_loaders(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            tsv = os.path.join(d, "g.tsv")
            with open(tsv, "w", encoding="utf-8") as f:
                f.write("# 주석\nsource\ttarget\tforbid\nprompt\t프롬프트|지시문\t명령어\n")
            js = os.path.join(d, "g.json")
            with open(js, "w", encoding="utf-8") as f:
                f.write('{"token": ["토큰"]}')
            a = translation_audit.load_glossary(tsv)
            b = translation_audit.load_glossary(js)
        self.assertEqual(a[0]["targets"], ["프롬프트", "지시문"])
        self.assertEqual(a[0]["forbid"], ["명령어"])
        self.assertEqual(b[0]["targets"], ["토큰"])

    def test_paragraph_omission_suspect(self):
        long_src = "This is a fairly long paragraph about the history of the project and its goals. "
        source = "\n\n".join([long_src * 2] * 4)
        short = "프로젝트 역사와 목표를 설명하는 비교적 긴 문단이다. " * 2
        target = "\n\n".join([short, short, "짧다.", short])
        data = translation_audit.audit_data(source, target, direction="en-to-ko")
        kinds = [o["kind"] for o in data["paragraph_alignment"]["outliers"]]
        self.assertIn("omission_suspect", kinds)

    def test_missing_paragraph_count_warned(self):
        source = "One para here.\n\nTwo para here.\n\nThree para here.\n\nFour para here."
        target = "첫 문단이다.\n\n둘째 문단이다."
        data = translation_audit.audit_data(source, target, direction="en-to-ko")
        self.assertTrue(any(r["id"] == "FID-8" for r in data["risks"]))

    def test_english_residue_detected_and_acronym_skipped(self):
        target = "이 모델은 state of the art 성능을 낸다. GPT API 호출도 가능하다."
        data = translation_audit.audit_data("The model is state of the art.", target, direction="en-to-ko")
        self.assertTrue(any("state of the art" in r for r in data["english_residue"]))
        self.assertFalse(any("GPT" in r for r in data["english_residue"]))

    def test_strict_promotes_major_to_hold(self):
        target = "프롬프트를 쓴다."
        data = translation_audit.audit_data(
            "A prompt.", "프롬프트를 쓴다.", direction="en-to-ko",
            glossary=[{"source": "prompt", "targets": ["지시문"], "forbid": []}])
        self.assertEqual(data["status"], "warn")
        self.assertEqual(translation_audit._apply_strict(data)["status"], "hold")

    def test_cli_accepts_glossary_option(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            paths = {}
            for name, text in (("s.md", "A prompt."), ("t.md", "프롬프트."), ("g.tsv", "prompt\t프롬프트\n")):
                paths[name] = os.path.join(d, name)
                with open(paths[name], "w", encoding="utf-8") as f:
                    f.write(text)
            code = translation_audit.main([paths["s.md"], paths["t.md"], "--direction", "en-to-ko",
                                           "--glossary", paths["g.tsv"], "--json"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
