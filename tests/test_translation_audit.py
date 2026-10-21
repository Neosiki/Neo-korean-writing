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


class TestV9Translationese(unittest.TestCase):
    def _te(self, target, source="A sentence.", **kw):
        return translation_audit.audit_data(source, target, direction="en-to-ko", **kw)

    def _fid7(self, data):
        return [r for r in data["risks"] if r["id"] == "FID-7" and "군집" not in r["label"]]

    def test_single_tonghae_is_not_reported(self):
        data = self._te("자료를 통해 확인했다. 결과는 분명했다.")
        self.assertEqual(self._fid7(data), [])
        below = [t["id"] for t in data["translationese"]["below_threshold"]]
        self.assertIn("P2", below)

    def test_tonghae_repetition_escalates_by_frequency(self):
        three = self._te("자료를 통해 보았다. 면담을 통해 들었다. 현장을 통해 확인했다.")
        five = self._te("자료를 통해 보았다. 면담을 통해 들었다. 현장을 통해 확인했다. 표를 통해 비교했다. 기록을 통해 검증했다.")
        self.assertEqual(self._fid7(three)[0]["severity"], "minor")
        self.assertEqual(self._fid7(five)[0]["severity"], "major")

    def test_double_passive_is_reported_even_once(self):
        data = self._te("보고서가 작성되어졌다.")
        labels = [r["label"] for r in self._fid7(data)]
        self.assertTrue(any("이중 피동" in x for x in labels))

    def test_hot_paragraph_cluster(self):
        text = ("보고서는 팀에 의해 작성되어졌다. 이 연구는 가격이 오른다는 것을 보여준다. 이 시스템은 시장에 있어서 변화를 가능하게 한다. "
                "그는 자료를 통해 분석을 통해 시장을 통해 설명했다.")
        data = self._te(text)
        hot = data["translationese"]["hot_paragraphs"]
        self.assertEqual(len(hot), 1)
        self.assertGreaterEqual(len(hot[0]["types"]), 3)
        self.assertTrue(any(r["label"] == "번역투 군집 문단" for r in data["risks"]))

    def test_source_influence_japanese_like(self):
        data = self._te("그는 학생으로서의 책임을 다했다. 연구라고 하는 작업에서의 경험과 회사에서의 경험은 다르다.")
        self.assertEqual(data["translationese"]["source_influence"]["inferred"], "japanese-like")

    def test_source_influence_english_like(self):
        data = self._te("그는 문을 열었다. 그의 손은 떨렸다. 그가 말했다. 그는 가지고 있던 열쇠를 내려놓았다.")
        self.assertEqual(data["translationese"]["source_influence"]["inferred"], "english-like")

    def test_register_mix_flagged_and_quotes_excluded(self):
        mixed = self._te("보고서를 제출합니다. 결과는 다음과 같습니다. 원인은 단순하다. 대책은 분명하다. 비용은 낮다.")
        self.assertTrue(mixed["register"]["mixed"])
        self.assertTrue(any(r["id"] == "FID-11" for r in mixed["risks"]))
        quoted = self._te("그가 말했다. \u201c제출합니다. 확인합니다. 감사합니다.\u201d 방은 조용하다. 불은 꺼져 있다. 창은 닫혀 있다.")
        self.assertFalse(quoted["register"]["mixed"])

    def test_list_period_inconsistency(self):
        bad = self._te("- 첫째 항목이다.\n- 둘째 항목\n- 셋째 항목이다.\n")
        good = self._te("- 첫째 항목\n- 둘째 항목\n- 셋째 항목\n")
        self.assertTrue(any(r["id"] == "FID-12" for r in bad["risks"]))
        self.assertFalse(any(r["id"] == "FID-12" for r in good["risks"]))

    def test_hedge_increase_vs_source(self):
        source = "The price rose. The cost fell. The firm grew."
        target = "가격이 오를 수 있다. 비용이 줄 수 있다. 회사가 클 가능성이 있다. 결과가 달라질 수도 있다."
        data = self._te(target, source=source)
        self.assertTrue(any(r["id"] == "FID-13" for r in data["risks"]))
        faithful = self._te("가격이 올랐다. 비용이 줄었다.", source=source)
        self.assertFalse(any(r["id"] == "FID-13" for r in faithful["risks"]))

    def test_korean_checks_skipped_for_ko_to_en(self):
        data = translation_audit.audit_data("그는 자료를 통해 분석을 통해 말했다.", "He spoke.", direction="ko-to-en")
        self.assertIsNone(data["translationese"])
        self.assertIsNone(data["register"])


class TestV9PostEditScope(unittest.TestCase):
    BASE = "첫 문장이다. 둘째 문장이다. 셋째 문장이다. 넷째 문장이다. 다섯째 문장이다. 여섯째 문장이다. 일곱째 문장이다. 여덟째 문장이다."

    def test_identical_is_light_without_risk(self):
        data = translation_audit.audit_data(self.BASE, self.BASE, direction="same", baseline=self.BASE)
        scope = data["post_edit_scope"]
        self.assertEqual(scope["tier"], "가벼움")
        self.assertFalse(any(r["id"].startswith("EDIT") for r in data["risks"]))

    def test_without_baseline_no_scope(self):
        data = translation_audit.audit_data(self.BASE, self.BASE, direction="same")
        self.assertIsNone(data["post_edit_scope"])

    def test_heavy_rewrite_holds(self):
        final = "전혀 다른 글이다. 새로 쓴 둘째다. 새로 쓴 셋째다. 새로 쓴 넷째다. 새로 쓴 다섯째다. 새로 쓴 여섯째다. 일곱째 문장이다. 여덟째 문장이다."
        data = translation_audit.audit_data(self.BASE, final, direction="same", baseline=self.BASE)
        edit = [r for r in data["risks"] if r["id"] == "EDIT-1"]
        self.assertEqual(edit[0]["level"], "hold")
        self.assertEqual(data["status"], "hold")
        self.assertEqual(data["post_edit_scope"]["tier"], "많음")

    def test_intensity_changes_threshold(self):
        final = self.BASE.replace("셋째 문장이다.", "셋째를 고친 문장이다.").replace("넷째 문장이다.", "넷째를 고친 문장이다.").replace("다섯째 문장이다.", "다섯째를 고친 문장이다.")
        conservative = translation_audit.audit_data(self.BASE, final, direction="same", baseline=self.BASE, intensity="보수")
        aggressive = translation_audit.audit_data(self.BASE, final, direction="same", baseline=self.BASE, intensity="적극")
        self.assertTrue(any(r["id"] == "EDIT-1" and r["level"] == "hold" for r in conservative["risks"]))
        self.assertFalse(any(r["id"] == "EDIT-1" for r in aggressive["risks"]))

    def test_size_delta_warned(self):
        final = self.BASE + " " + "덧붙인 문장이 이어진다. " * 4
        data = translation_audit.audit_data(self.BASE, final, direction="same", baseline=self.BASE)
        self.assertTrue(any(r["id"] == "EDIT-2" for r in data["risks"]))

    def test_cli_baseline_and_bad_intensity(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            paths = {}
            for name in ("s.md", "t.md", "b.md"):
                paths[name] = os.path.join(d, name)
                with open(paths[name], "w", encoding="utf-8") as f:
                    f.write(self.BASE)
            ok = translation_audit.main([paths["s.md"], paths["t.md"], "--direction", "same",
                                         "--baseline", paths["b.md"], "--json"])
            bad = translation_audit.main([paths["s.md"], paths["t.md"], "--intensity", "과격"])
        self.assertEqual(ok, 0)
        self.assertEqual(bad, 3)


class TestV91ReceiveCodexResearch(unittest.TestCase):
    """v9.1: 용어집 권장어·허용어·고정 모드, 위험 근거 표기, 초벌 대비 변화."""

    SRC = "We use a large language model. The prompt matters."

    def _glossary(self, mode):
        return [{"source": "large language model", "targets": ["대규모 언어 모델", "LLM"], "forbid": [],
                 "mode": mode, "context": "", "preferred": "대규모 언어 모델"},
                {"source": "prompt", "targets": ["프롬프트"], "forbid": [], "mode": "flex", "context": "",
                 "preferred": "프롬프트"}]

    def test_allowed_variant_is_not_an_error(self):
        tgt = "우리는 LLM을 쓴다. 프롬프트가 중요하다."
        data = translation_audit.audit_data(self.SRC, tgt, "en-to-ko", glossary=self._glossary("flex"))
        self.assertFalse(any(r["id"].startswith("TERM") for r in data["risks"]))

    def test_strict_mixed_variants_warn_but_flex_does_not(self):
        tgt = "우리는 대규모 언어 모델을 쓴다. LLM은 빠르다. 프롬프트가 중요하다."
        strict = translation_audit.audit_data(self.SRC, tgt, "en-to-ko", glossary=self._glossary("strict"))
        flex = translation_audit.audit_data(self.SRC, tgt, "en-to-ko", glossary=self._glossary("flex"))
        self.assertTrue(any(r["id"] == "TERM-3" and r["severity"] == "minor" for r in strict["risks"]))
        self.assertFalse(any(r["id"] == "TERM-3" for r in flex["risks"]))
        self.assertEqual(len(flex["glossary"]["variations"]), 1)

    def test_glossary_tsv_reads_mode_and_context(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as f:
            f.write("source\ttarget\tforbid\tmode\tcontext\nprompt\t프롬프트|질문문\t\tstrict\t본문\n")
            path = f.name
        try:
            entries = translation_audit.load_glossary(path)
        finally:
            os.unlink(path)
        self.assertEqual(entries[0]["mode"], "strict")
        self.assertEqual(entries[0]["preferred"], "프롬프트")
        self.assertEqual(entries[0]["context"], "본문")

    def test_risks_carry_basis_and_state(self):
        data = translation_audit.audit_data("예산은 1,348억 원이다.", "예산은 1,300억 원이다.", direction="same")
        for r in data["risks"]:
            self.assertEqual(r["state"], "검토 후보")
        self.assertEqual([r["basis"] for r in data["risks"] if r["id"] == "FID-6"], ["mechanical-check"])
        self.assertIn("MQM", data["severity_note"])

    def test_baseline_delta_fixed_and_introduced(self):
        src = "The user opened the file."
        bad = "파일이 사용자에 의해 열려졌다."
        good = "사용자가 파일을 열었다."
        fixed = translation_audit.audit_data(src, good, "en-to-ko", baseline=bad)
        self.assertTrue(fixed["baseline_delta"]["translationese"]["fixed"])
        self.assertFalse(any(r["id"] == "EDIT-4" for r in fixed["risks"]))
        worse = translation_audit.audit_data(src, bad, "en-to-ko", baseline=good)
        self.assertTrue(worse["baseline_delta"]["translationese"]["introduced"])
        self.assertTrue(any(r["id"] == "EDIT-4" for r in worse["risks"]))

    def test_baseline_register_change_flags_edit3(self):
        src = "Please confirm the items. Please check the file. Please send the report."
        base = "항목을 확인해 주세요. 파일을 점검해 주세요. 보고서를 보내 주세요."
        final = "항목을 확인해. 파일을 점검해. 보고서를 보내."
        data = translation_audit.audit_data(src, final, "en-to-ko", baseline=base)
        self.assertTrue(any(r["id"] == "EDIT-3" for r in data["risks"]))

    def test_baseline_surface_lock_regression(self):
        src = "요금은 1,348원이다."
        base = "요금은 1,348원이다."
        final = "요금은 1,300원이다."
        data = translation_audit.audit_data(src, final, "same", baseline=base)
        self.assertTrue(data["baseline_delta"]["surface_lock"]["introduced_missing"])


class TestV92NumericUnitPreservation(unittest.TestCase):
    """Avoid unit-translation false positives without losing numeric safeguards."""

    def test_equivalent_unit_aliases_and_thousands_grouping(self):
        pairs = [
            ("Budget is 1,348 won.", "예산은 1,348원이다."),
            ("Budget is 1348 KRW.", "예산은 1,348 원이다."),
            ("Growth is 2.5 percent.", "성장률은 2.5퍼센트다."),
            ("Growth is 2.5 per cent.", "성장률은 2.5%다."),
            ("Length is 10 meters.", "길이는 10미터다."),
            ("Weight is 0.5 kilograms.", "무게는 0.5킬로그램이다."),
            ("손실은 −5%다.", "손실은 -5퍼센트다."),
        ]
        for source, target in pairs:
            with self.subTest(source=source):
                data = translation_audit.audit_data(source, target, "en-to-ko")
                self.assertTrue(data["surface_lock"]["pass"], data["surface_lock"])
                self.assertEqual(data["surface_lock"]["extra"], [])

    def test_changed_value_or_unit_still_holds(self):
        pairs = [
            ("Budget is 1,348 won.", "예산은 1,300원이다."),
            ("Length is 10 m.", "길이는 10cm다."),
            ("Growth is 5 percent.", "성장률은 5다."),
            ("Loss is -5%.", "손실은 5%다."),
            ("예산은 2억 원이다.", "예산은 2만 원이다."),
        ]
        for source, target in pairs:
            with self.subTest(source=source):
                data = translation_audit.audit_data(source, target, "en-to-ko")
                self.assertFalse(data["surface_lock"]["pass"])
                self.assertTrue(any(r["id"] == "FID-6" for r in data["risks"]))

    def test_repeated_amount_omission_is_not_hidden_by_normalization(self):
        data = translation_audit.audit_data("Pay 1,348 won twice: 1,348 won.", "1,348원을 내세요.", "en-to-ko")
        missing = [m for m in data["surface_lock"]["missing"] if m["kind"] == "number"]
        self.assertEqual(missing, [{"kind": "number", "value": "1348원", "count": 1}])

    def test_no_automatic_amount_or_decimal_locale_conversion(self):
        for source, target in [("10 km", "10000 m"), ("1,5", "1.5"), ("1,000", "1.000")]:
            with self.subTest(source=source):
                self.assertNotEqual(translation_audit.shared_locks(source)["number"],
                                    translation_audit.shared_locks(target)["number"])

    def test_sentence_punctuation_is_not_part_of_number(self):
        self.assertEqual(translation_audit.shared_locks("It is 12. Next is 0.5.")["number"], ["12", "0.5"])

    def test_unit_name_must_not_match_prefix_of_other_english_word(self):
        self.assertEqual(translation_audit.shared_locks("10 models and 5 growth events")["number"], ["10", "5"])

    def test_numeric_unit_does_not_erase_standalone_acronyms(self):
        self.assertEqual(translation_audit.shared_locks("1348 KRW; KRW and BERT use API")["acronym"],
                         ["KRW", "BERT", "API"])

    def test_baseline_delta_distinguishes_alias_change_from_numeric_regression(self):
        source = "Budget is 1,348 won."
        baseline = "예산은 1,348원이다."
        same = translation_audit.audit_data(source, "예산은 1348 원이다.", "en-to-ko", baseline=baseline)
        changed = translation_audit.audit_data(source, "예산은 1,300원이다.", "en-to-ko", baseline=baseline)
        self.assertEqual(same["baseline_delta"]["surface_lock"]["introduced_missing"], [])
        self.assertTrue(changed["baseline_delta"]["surface_lock"]["introduced_missing"])


if __name__ == "__main__":
    unittest.main()
