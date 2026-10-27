"""Regressions from real MCP comparison plus valid rewrites and stale notes."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import editing_audit as audit
import korean_writing as writing

CONTEXT = "다음 내용은 가상의 매장을 위한 안내문이다. 실제 고객 자료는 포함하지 않았다. 담당자는 내용을 확인한다.\n\n"
PLAIN = "오늘 안내문을 확인했다. 잘못된 주소를 고쳤다. 대표가 결과를 검토했다. 내일 다시 확인한다."
FORMAL = "오늘 안내문을 확인했습니다. 잘못된 주소를 고쳤습니다. 대표가 결과를 검토했습니다. 내일 다시 확인합니다."


def codes(before, after):
    return {f["code"] for f in audit.review_signals(before, after)["findings"]}


class EditingSignalTests(unittest.TestCase):
    def test_register_candidate_has_exact_original_and_final_evidence(self):
        result = audit.review_signals(PLAIN, FORMAL)
        hit = next(f for f in result["findings"] if f["code"] == "EDIT-REGISTER")
        for prefix, text in (("before", PLAIN), ("after", FORMAL)):
            span = hit[prefix+"_location"]
            self.assertTrue(hit[prefix+"_quote"])
            self.assertEqual(text[span["start"]:span["end"]], hit[prefix+"_quote"])

    def test_plain_to_formal_is_held_in_both_entrypoints(self):
        result = audit.audit_data(PLAIN, FORMAL)
        self.assertEqual(result["status"], "hold")
        self.assertIn("EDIT-REGISTER", codes(PLAIN, FORMAL))
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            b, a = Path(tmp)/"b.txt", Path(tmp)/"a.txt"
            b.write_text(PLAIN, encoding="utf-8")
            a.write_text(FORMAL, encoding="utf-8")
            with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as caught:
                writing.cmd_preserve([str(b), str(a), "--json"])
            self.assertEqual(caught.exception.code, 1)

    def test_register_detection_works_in_both_directions(self):
        forms = [PLAIN, FORMAL,
                 "오늘 확인했어요. 주소를 고쳤어요. 결과를 검토했어요. 내일 확인해요.",
                 "오늘 확인함. 주소 수정함. 결과 검토함. 내일 확인함."]
        for i, before in enumerate(forms):
            for j, after in enumerate(forms):
                with self.subTest(i=i, j=j):
                    self.assertEqual("EDIT-REGISTER" in codes(before, after), i != j)

    def test_short_or_mixed_text_is_not_force_classified(self):
        self.assertEqual(audit.register_profile("확인했다.")["status"], "insufficient_or_mixed")
        self.assertNotIn("EDIT-REGISTER", codes("확인했다.", "확인했습니다."))
        mixed = "확인했다. 검토했어요. 발송했습니다. 저장함."
        self.assertEqual(audit.register_profile(mixed)["status"], "insufficient_or_mixed")

    def test_polite_imperatives_keep_their_register(self):
        hayo = "자료를 읽으세요. 주소를 고치세요. 결과를 검토하세요."
        formal = "자료를 읽으십시오. 주소를 고치십시오. 결과를 검토하십시오."
        self.assertEqual(audit.register_profile(hayo)["dominant"], "해요체")
        self.assertEqual(audit.register_profile(formal)["dominant"], "합쇼체")

    def test_quotes_code_frontmatter_and_headings_do_not_set_voice(self):
        bt = chr(96)
        protected = '“전송합니다. 확인합니다. 저장합니다.”\n'
        protected += bt*3 + "\n전송합니다. 확인합니다. 저장합니다.\n" + bt*3 + "\n"
        protected += "> 전송합니다. 확인합니다. 저장합니다.\n"
        protected += "# 확인합니다.\n| 확인합니다. 저장합니다. 전송합니다. |\n"
        self.assertEqual(audit.register_profile(protected)["classified_sentences"], 0)
        self.assertEqual(audit.register_profile(protected+PLAIN)["dominant"], "한다체")
        self.assertEqual(audit.register_profile("---\n말투: 합니다.\n---\n"+PLAIN)["dominant"], "한다체")

    def test_blockquote_mask_does_not_hide_following_prose(self):
        profile = audit.register_profile("> 인용입니다.\n"+PLAIN)
        self.assertEqual(profile["classified_sentences"], 4)

    def test_long_document_negation_flip_has_local_evidence(self):
        prefix = CONTEXT * 6
        before = prefix + "이 서비스는 고객 동의 없이 메시지를 보내지 않는다."
        after = prefix + "이 서비스는 고객 동의 없이 메시지를 보낸다."
        findings = audit.review_signals(before, after)["findings"]
        hit = next(f for f in findings if f["code"] == "EDIT-NEGATION")
        self.assertIn("보내지 않는다", hit["before_quote"])
        span = hit["after_location"]
        self.assertEqual(after[span["start"]:span["end"]], hit["after_quote"])
        self.assertEqual(audit.audit_data(before, after)["status"], "review")

    def test_existing_numbers_swapped_between_stores_are_candidates(self):
        before = "A매장의 매출은 100만 원이고 B매장의 매출은 200만 원이다."
        after = "A매장의 매출은 200만 원이고 B매장의 매출은 100만 원이다."
        result = audit.audit_data(before, after)
        findings = result["preservation"]["editing_review"]["findings"]
        hits = [f for f in findings if f["code"] == "EDIT-BINDING"]
        self.assertEqual(len(hits), 2)
        self.assertEqual(result["status"], "review")
        self.assertTrue(all(f["basis"] == "heuristic-candidate" for f in hits))

    def test_binding_spacing_and_equivalent_units_do_not_make_candidates(self):
        self.assertNotIn("EDIT-BINDING", codes("A매장의 매출은 100만원이다.", "A매장의 매출은 100만 원이다."))
        self.assertNotIn("EDIT-BINDING", codes("A매장의 매출은 100만 원이다.", "A매장의 매출은 1,000,000원이다."))
        self.assertNotIn("EDIT-BINDING", codes("A매장의 수익은 10퍼센트다.", "A매장의 수익은 10%다."))

    def test_repeated_subject_metrics_are_not_forcibly_paired(self):
        before = "A매장의 매출은 100만원이다. A매장의 매출은 200만원이다."
        after = "A매장의 매출은 200만원이다. A매장의 매출은 100만원이다."
        self.assertNotIn("EDIT-BINDING", codes(before, after))

    def test_injected_sentence_is_review_not_an_error_certification(self):
        before = CONTEXT + "운영자는 문의 내용을 확인한다."
        after = before + " 전국 판매망 계약과 해외 수출 협상을 이미 마쳤다."
        result = audit.audit_data(before, after)
        self.assertEqual(result["status"], "review")
        self.assertIn("EDIT-CONTENT", codes(before, after))

    def test_synonyms_are_not_hard_blocked_as_fabrication(self):
        before = CONTEXT + "대표는 손님이 줄어 가게 운영을 걱정한다."
        after = CONTEXT + "점주는 방문객 감소로 매장 경영을 고민한다."
        result = audit.audit_data(before, after)
        self.assertNotEqual(result["status"], "hold")
        self.assertTrue(result["preservation"]["editing_review"]["new_terms"])

    def test_valid_sentence_split_remains_acceptable(self):
        before = CONTEXT + "담당자는 자료를 읽고 오류를 표시한다."
        after = CONTEXT + "담당자는 자료를 읽는다. 오류를 표시한다."
        self.assertEqual(audit.audit_data(before, after)["status"], "pass")

    def test_repeated_number_loss_uses_existing_preserve_contract(self):
        before = CONTEXT + "첫 회차는 3시간, 다음 회차도 3시간이다."
        after = CONTEXT + "첫 회차는 3시간, 다음 회차는 시간 미정이다."
        self.assertEqual(audit.audit_data(before, after)["status"], "hold")

    def test_code_change_still_blocks(self):
        bt = chr(96)
        before = CONTEXT + bt + "python report.py --dry-run" + bt
        after = CONTEXT + bt + "python report.py --force" + bt
        self.assertEqual(audit.audit_data(before, after)["status"], "hold")

    def test_decimal_is_not_split_into_multiple_sentences(self):
        self.assertEqual(len(list(audit.sentences("매출은 1.5억 원이다. 다음에 확인한다."))), 2)

    def test_large_unchanged_document_does_not_create_review_candidates(self):
        text = "\n".join(f"매장{n}의 자료를 확인했다." for n in range(800))
        self.assertEqual(audit.review_signals(text, text)["findings"], [])


class DeliveryTests(unittest.TestCase):
    def pair(self):
        return CONTEXT+"확인하고 전달한다.", CONTEXT+"확인한 뒤 전달한다."

    def filled(self, before, after):
        result = audit.delivery_template(before, after)
        for edit in result["edits"]:
            edit["reason"] = "행동 순서를 더 분명하게 표현"
        return result

    def test_final_diff_and_reason_are_bound_to_current_pair(self):
        before, after = self.pair()
        self.assertEqual(audit.delivery_review(before, after, self.filled(before, after))["status"], "verified")

    def test_discarded_notes_on_unchanged_final_are_rejected(self):
        before, after = self.pair()
        report = self.filled(before, after)
        report["final_sha256"] = audit.text_hash(before)
        self.assertEqual(audit.delivery_review(before, before, report)["status"], "mismatch")
        self.assertEqual(audit.audit_data(before, before, delivery=report)["status"], "hold")

    def test_stale_report_is_rejected_without_trusting_notes(self):
        before, after = self.pair()
        report = self.filled(before, after)
        self.assertEqual(audit.delivery_review(before, after+" ", report)["status"], "stale")

    def test_missing_edit_or_wrong_coordinate_is_mismatch(self):
        before, after = self.pair()
        for mutate in ("missing", "coordinate", "text"):
            report = self.filled(before, after)
            if mutate == "missing":
                report["edits"].pop()
            elif mutate == "coordinate":
                report["edits"][0]["after_start"] += 1
            else:
                report["edits"][0]["after"] = "적용 안 된 내용"
            self.assertEqual(audit.delivery_review(before, after, report)["status"], "mismatch")

    def test_blank_reasons_are_not_reported_verified(self):
        before, after = self.pair()
        report = audit.delivery_template(before, after)
        self.assertEqual(audit.delivery_review(before, after, report)["status"], "needs_reasons")
        self.assertEqual(audit.audit_data(before, after, delivery=report)["status"], "review")

    def test_zero_edits_and_line_endings(self):
        before = "확인했다.\r\n저장했다."
        after = "확인했다.\n저장했다."
        report = audit.delivery_template(before, after)
        self.assertEqual(report["edits"], [])
        self.assertEqual(audit.delivery_review(before, after, report)["status"], "verified")

    def test_addition_and_deletion_use_exact_empty_spans(self):
        for before, after in [("확인했다.", "확인하고 전달했다."), ("확인하고 전달했다.", "확인했다.")]:
            report = self.filled(before, after)
            self.assertEqual(audit.delivery_review(before, after, report)["status"], "verified")

    def test_bad_records_are_input_errors(self):
        before, after = self.pair()
        for bad in (None, [], {"schema_version": True}, {"schema_version": 1, "original_sha256": "bad"}):
            if bad is None:
                self.assertEqual(audit.delivery_review(before, after, bad)["status"], "not_checked")
            else:
                with self.assertRaises(ValueError):
                    audit.delivery_review(before, after, bad)
        report = self.filled(before, after)
        report["edits"][0]["before_start"] = True
        with self.assertRaises(ValueError):
            audit.delivery_review(before, after, report)

    def test_unchanged_text_has_no_false_improvement_claim(self):
        result = audit.audit_data(PLAIN, PLAIN)
        self.assertEqual(result["change_rate"], 0)
        self.assertEqual(result["delivery"]["status"], "not_checked")
        self.assertEqual(result["semantic_review"]["status"], "not_checked")

    def test_required_semantic_review_is_not_silently_skipped(self):
        result = audit.audit_data(PLAIN, PLAIN, require_semantic=True)
        self.assertEqual(result["mechanical_status"], "pass")
        self.assertEqual(result["status"], "hold")

    def test_semantic_report_uses_existing_hash_and_evidence_contract(self):
        from translation_semantics import packet, DIMENSIONS
        report = packet(PLAIN, PLAIN)["report_template"]
        report.update(reviewer={"kind": "human", "name": "가상 검토자", "independent": False},
                      summary="회귀 시험용 형식 기록", dimensions_reviewed=list(DIMENSIONS))
        result = audit.audit_data(PLAIN, PLAIN, semantic_review=report, require_semantic=True)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["semantic_review"]["status"], "reviewed_no_findings")
        self.assertEqual(audit.audit_data(PLAIN, PLAIN+" ", semantic_review=report)["status"], "hold")


class EntryPointTests(unittest.TestCase):
    def solar_record(self):
        return {"schema_version": 1, "original_sha256": audit.text_hash(PLAIN),
                "final_sha256": audit.text_hash(PLAIN), "provider": "Upstage 직접 (BYOK)",
                "model": "solar-pro4", "calls": 3, "tokens": 4679}

    def test_solar_record_retains_actual_counts_and_unknowns(self):
        record = self.solar_record()
        result = audit.audit_data(PLAIN, PLAIN, solar_record=record)
        self.assertEqual(result["solar_usage"]["calls"], 3)
        self.assertEqual(result["solar_usage"]["tokens"], 4679)
        record.update(calls=None, tokens=None)
        self.assertIsNone(audit.solar_record_review(PLAIN, PLAIN, record)["calls"])

    def test_solar_stale_record_is_not_reused(self):
        result = audit.audit_data(PLAIN, PLAIN+" ", solar_record=self.solar_record())
        self.assertEqual(result["solar_usage"]["status"], "stale")
        self.assertEqual(result["status"], "hold")

    def test_solar_record_rejects_keys_raw_payload_and_invalid_counts(self):
        for key, value in [("api_key", "not-a-real-key"), ("headers", {}), ("calls", True), ("tokens", -1)]:
            record = self.solar_record()
            record[key] = value
            with self.assertRaises(ValueError):
                audit.solar_record_review(PLAIN, PLAIN, record)

    def test_cli_writes_template_without_overwriting_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            b, a, notes = (Path(tmp)/n for n in ("b.txt", "a.txt", "notes.json"))
            b.write_text(PLAIN, encoding="utf-8")
            a.write_text(PLAIN, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(audit.main([str(b), str(a), "--delivery-template", str(notes)]), 0)
            original = notes.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(audit.main([str(b), str(a), "--delivery-template", str(notes)]), 3)
            self.assertEqual(notes.read_bytes(), original)

    def test_invalid_inputs_and_empty_final_are_exit_three(self):
        with tempfile.TemporaryDirectory() as tmp:
            b, a, notes = (Path(tmp)/n for n in ("b.txt", "a.txt", "notes.json"))
            b.write_text(PLAIN, encoding="utf-8")
            a.write_text("", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(audit.main([str(b), str(a)]), 3)
            a.write_text(PLAIN, encoding="utf-8")
            notes.write_text("{bad", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(audit.main([str(b), str(a), "--delivery", str(notes)]), 3)

    def test_installed_cli_path_dispatches_real_audit(self):
        sys.path.insert(0, str(ROOT/"src"))
        from neo_korean_writing import cli
        with tempfile.TemporaryDirectory() as tmp:
            b, a = Path(tmp)/"b.txt", Path(tmp)/"a.txt"
            b.write_text(PLAIN, encoding="utf-8")
            a.write_text(FORMAL, encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli.main(["editing-audit", str(b), str(a), "--json"])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(out.getvalue())["status"], "hold")

    def test_verify_gates_integrates_protected_and_style_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            b, a = Path(tmp)/"b.txt", Path(tmp)/"a.txt"
            for before, after in [(PLAIN, FORMAL), ("실행은 "+chr(96)+"--dry-run"+chr(96), "실행은 "+chr(96)+"--force"+chr(96))]:
                b.write_text(before, encoding="utf-8")
                a.write_text(after, encoding="utf-8")
                run = subprocess.run([sys.executable, str(ROOT/"scripts/verify_gates.py"),
                                      "--before", str(b), "--after", str(a)],
                                     capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertIn("P6 보존 통합", run.stdout)


if __name__ == "__main__":
    unittest.main()
