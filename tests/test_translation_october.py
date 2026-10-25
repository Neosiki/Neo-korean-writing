import contextlib
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import translation_audit as audit
import translation_links as link
import translation_impact as impact
import translation_reader as reader


class MarkdownDestinations(unittest.TestCase):
    source = "# Guide\n\n[Details](#details)\n\n## Details\n\nRead the steps."
    broken = "# 안내\n\n[세부 안내](#details)\n\n## 세부 안내\n\n절차를 읽으세요."
    fixed = "# 안내\n\n[세부 안내](#세부-안내)\n\n## 세부 안내\n\n절차를 읽으세요."

    def test_broken_anchor_now_holds(self):
        result = audit.audit_data(self.source, self.broken)
        self.assertEqual(result["status"], "hold")
        self.assertIn("LINK-1", [r["id"] for r in result["risks"]])

    def test_translated_anchor_no_longer_loses_surface_lock(self):
        result = audit.audit_data(self.source, self.fixed)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["surface_lock"]["pass"])
        self.assertEqual(result["link_validation"]["allowed_changes"][0]["basis"], "heading_order")

    def test_automatic_mapping_does_not_allow_wrong_heading(self):
        result = audit.audit_data(self.source, self.fixed.replace("#세부-안내)", "#안내)"))
        self.assertEqual(result["status"], "hold")

    def test_duplicate_and_percent_encoded_headings(self):
        source = "# A\n# A\n[x](#a-1)"
        target = "# 안내\n# 안내\n[x](#%EC%95%88%EB%82%B4-1)"
        result = audit.audit_data(source, target)
        self.assertTrue(result["surface_lock"]["pass"])
        self.assertTrue(result["link_validation"]["pass"])

    def test_explicit_anchor(self):
        text = '<a id="fixed"></a>\n[x](#fixed)'
        self.assertTrue(link.compare_links(text, text)["pass"])
        self.assertTrue(audit.audit_data(text, text)["link_validation"]["pass"])
        self.assertEqual(audit.audit_data(text, text.replace("#fixed)", "#absent)"))["status"], "hold")

    def test_setext_heading(self):
        self.assertTrue(link.compare_links("Title\n===\n[x](#title)", "제목\n===\n[x](#제목)")["pass"])

    def test_markup_unicode_and_collision(self):
        ids = link.anchors("# *안내* \x60코드\x60!\n# 안내 코드\n# 안내 코드-1")["ids"]
        self.assertEqual(ids, {"안내-코드", "안내-코드-1", "안내-코드-1-1"})

    def test_inline_code_fence_comments_not_links_or_anchors(self):
        sample = "\x60[x](#none)\x60\n\x60\x60\x60md\n# Fake\n[x](#none)\n\x60\x60\x60\n<!-- [x](#none) -->"
        self.assertEqual(link.links(sample), [])
        self.assertEqual(link.anchors(sample)["ids"], set())

    def test_reference_links_and_balanced_destinations(self):
        sample = '[one][r] [r][] ![photo](img(a).png "title")\n\n[r]: #title\n\n# Title'
        self.assertEqual([r["destination"] for r in link.links(sample)], ["#title", "#title", "img(a).png"])

    def test_unclosed_bracket_does_not_hide_later_link(self):
        self.assertEqual(link.links("[unfinished [x](#missing)")[0]["destination"], "#missing")

    def test_external_url_cannot_be_mapped(self):
        with self.assertRaises(ValueError):
            link.compare_links("[x](https://a.test)", "[x](https://b.test)",
                               mapping={"https://a.test": "https://b.test"})

    def test_external_url_stays_locked(self):
        self.assertEqual(audit.audit_data("[x](https://a.test)", "[x](https://b.test)")["status"], "hold")

    def test_missing_target_and_escaped_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for dest, expected in (("missing.png", "missing_file"), ("../private.md", "outside_root")):
                with self.subTest(dest=dest):
                    r = link.compare_links("", f"![x]({dest})", target_path=root / "ko.md", root=root)
                    self.assertEqual(r["issues"][0]["kind"], expected)

    def test_linked_file_fragment_and_explicit_map(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "ko.md").write_text("# 안내", encoding="utf-8")
            opts = {"root": root, "target_path": root / "index.md", "mapping": {"en.md#guide": "ko.md#안내"}}
            result = audit.audit_data("[guide](en.md#guide)", "[안내](ko.md#안내)", link_options=opts)
            self.assertTrue(result["surface_lock"]["pass"])
            self.assertTrue(result["link_validation"]["pass"])
            (root / "ko.md").write_text("# 다른 제목", encoding="utf-8")
            result = audit.audit_data("[guide](en.md#guide)", "[안내](ko.md#안내)", link_options=opts)
            self.assertEqual(result["status"], "hold")

    def test_images_with_mapping_need_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "번역.png").write_bytes(b"image")
            r = link.compare_links("![x](original.png)", "![x](번역.png)",
                                   root=root, target_path=root / "index.md",
                                   mapping={"original.png": "번역.png"})
            self.assertEqual(r["source_targets"], r["target_targets"])

    def test_no_root_discloses_unchecked_local_files(self):
        r = link.compare_links("[x](missing.md)", "[x](missing.md)")
        self.assertEqual(r["unchecked"][0]["reason"], "local_root_not_provided")

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as outside:
            root = Path(td)
            secret = Path(outside) / "other.md"
            secret.write_text("# Other", encoding="utf-8")
            try:
                (root / "linked.md").symlink_to(secret)
            except OSError:
                self.skipTest("symlinks unavailable")
            r = link.compare_links("", "[x](linked.md)", root=root, target_path=root / "index.md")
            self.assertEqual(r["issues"][0]["kind"], "outside_root")

    def test_baseline_does_not_introduce_false_missing(self):
        r = audit.audit_data(self.source, self.fixed, baseline=self.broken)
        self.assertFalse(r["baseline_delta"]["surface_lock"]["introduced_missing"])


class SegmentImpact(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.data = {"schema_version": 1, "glossary": "terms.json", "segments": []}
        for i, source in enumerate(["A bank opens.", "A river flows.", "A shop opens.", "A cafe opens.", "A clinic opens."]):
            ident = "s" + str(i)
            (self.base / (ident + ".src")).write_text(source, encoding="utf-8")
            (self.base / (ident + ".ko")).write_text("번역 문장입니다.", encoding="utf-8")
            self.data["segments"].append({"id": ident, "source": ident + ".src", "target": ident + ".ko"})
        self.terms = {"bank": ["은행"], "river": ["강"]}
        self.write_terms()
        self.snapshot = impact.capture(self.data, self.base)

    def tearDown(self):
        self.temp.cleanup()

    def write_terms(self):
        (self.base / "terms.json").write_text(json.dumps(self.terms), encoding="utf-8")

    def test_unchanged_keeps_all(self):
        r = impact.plan(self.data, self.base, self.snapshot)
        self.assertEqual(r["keep"], ["s0", "s1", "s2", "s3", "s4"])
        self.assertEqual(r["review"], [])

    def test_one_term_changes_only_segment_and_neighbor(self):
        original_targets = [(self.base / ("s" + str(i) + ".ko")).read_bytes() for i in range(5)]
        self.terms["bank"] = ["금융 기관"]
        self.write_terms()
        r = impact.plan(self.data, self.base, self.snapshot)
        self.assertEqual([x["id"] for x in r["review"]], ["s0", "s1"])
        self.assertEqual(r["keep"], ["s2", "s3", "s4"])
        self.assertEqual(original_targets, [(self.base / ("s" + str(i) + ".ko")).read_bytes() for i in range(5)])

    def test_unused_term_change_has_no_effect(self):
        self.terms["unused"] = ["미사용"]
        self.write_terms()
        self.assertEqual(impact.plan(self.data, self.base, self.snapshot)["review"], [])

    def test_new_relevant_term_detected(self):
        self.terms["clinic"] = ["의원"]
        self.write_terms()
        self.assertEqual([x["id"] for x in impact.plan(self.data, self.base, self.snapshot)["review"]], ["s3", "s4"])

    def test_removed_relevant_term_detected(self):
        del self.terms["bank"]
        self.write_terms()
        self.assertIn("relevant_terms_changed", impact.plan(self.data, self.base, self.snapshot)["review"][0]["reasons"])

    def test_transitive_dependencies(self):
        self.data["segments"][3]["depends_on"] = ["s1"]
        self.data["segments"][4]["depends_on"] = ["s3"]
        snapshot = impact.capture(self.data, self.base)
        self.terms["bank"] = ["은행업체"]
        self.write_terms()
        r = impact.plan(self.data, self.base, snapshot)
        self.assertEqual([x["id"] for x in r["review"]], ["s0", "s1", "s3", "s4"])

    def test_changed_translation_and_source(self):
        (self.base / "s2.ko").write_text("수정한 번역.", encoding="utf-8")
        r = impact.plan(self.data, self.base, self.snapshot)
        self.assertEqual([x["id"] for x in r["review"]], ["s1", "s2", "s3"])
        self.assertIn("target_sha256_changed", r["review"][1]["reasons"])

    def test_missing_translation(self):
        (self.base / "s0.ko").unlink()
        r = impact.plan(self.data, self.base, self.snapshot)
        self.assertIn("missing_or_empty_target", r["review"][0]["reasons"])

    def test_unresolved_scope_never_kept(self):
        self.terms = [{"source": "bank", "target": ["은행"], "domains": ["finance"]}]
        self.write_terms()
        r = impact.plan(self.data, self.base, self.snapshot)
        self.assertIn("glossary_scope_unresolved", r["review"][0]["reasons"])

    def test_scope_change_and_reorder(self):
        self.data["segments"][0]["domain"] = "finance"
        self.assertTrue(impact.plan(self.data, self.base, self.snapshot)["review"])
        self.data["segments"].reverse()
        self.assertTrue(any("neighbor_order_changed" in r["reasons"] for r in impact.plan(self.data, self.base, self.snapshot)["review"]))

    def test_no_baseline_and_removed_segments_disclosed(self):
        self.assertEqual(len(impact.plan(self.data, self.base)["review"]), 5)
        self.data["segments"].pop()
        self.assertEqual(impact.plan(self.data, self.base, self.snapshot)["removed"], ["s4"])

    def test_paragraphs_in_single_file_have_local_impact(self):
        (self.base / "book.src").write_text("A bank opens.\n\nA river flows.\n\nA shop opens.\n\nA cafe opens.\n\nA clinic opens.", encoding="utf-8")
        (self.base / "book.ko").write_text("은행 문단.\n\n강 문단.\n\n가게 문단.\n\n카페 문단.\n\n병원 문단.", encoding="utf-8")
        for i, row in enumerate(self.data["segments"]):
            row.update(source="book.src", target="book.ko", source_paragraph=i + 1, target_paragraph=i + 1)
        snapshot = impact.capture(self.data, self.base)
        self.terms["bank"] = ["금융기관"]
        self.write_terms()
        self.assertEqual([r["id"] for r in impact.plan(self.data, self.base, snapshot)["review"]], ["s0", "s1"])

    def test_snapshot_cli_never_overwrites_existing_file(self):
        path = self.base / "manifest.json"
        path.write_text(json.dumps(self.data), encoding="utf-8")
        out = self.base / "baseline.json"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(impact.main(["snapshot", str(path), "--output", str(out)]), 0)
            self.assertEqual(impact.main(["plan", str(path), "--baseline", str(out), "--json"]), 0)
        old = out.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(impact.main(["snapshot", str(path), "--output", str(out)]), 3)
        self.assertEqual(out.read_bytes(), old)

    def test_corrupt_inputs_rejected(self):
        for field, value in (("segments", []), ("schema_version", True), ("segments", [{"id": "x"}])):
            data = deepcopy(self.data)
            data[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                impact.plan(data, self.base, self.snapshot)
        snap = deepcopy(self.snapshot)
        snap["records"]["s0"]["terms"] = []
        with self.assertRaises(ValueError):
            impact.plan(self.data, self.base, snap)

    def test_invalid_paragraph_selectors_rejected(self):
        for value in (True, 0, "1", 999):
            data = deepcopy(self.data)
            data["segments"][0]["source_paragraph"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                impact.capture(data, self.base)


class ReaderEvidence(unittest.TestCase):
    target = "김 담당자가 주문서를 확인합니다. 발송은 승인 후 진행합니다."
    qs = [{"id": "who", "question": "누가 주문서를 확인하나요?"},
          {"id": "when", "question": "언제 발송하나요?"}]

    def report(self):
        r = reader.packet(self.target, self.qs)["report_template"]
        r["reader"].update(name="current-agent", context="author_context", independent=False)
        r["summary"] = "작성 문맥을 가진 자체 읽기 기록."
        r["answers"] = [
            {"id": "who", "status": "answered", "answer": "김 담당자", "evidence": ["김 담당자가 주문서를 확인합니다."], "reason": "첫 문장의 주체."},
            {"id": "when", "status": "answered", "answer": "승인 후", "evidence": ["발송은 승인 후 진행합니다."], "reason": "둘째 문장에 조건이 있습니다."}]
        return r

    def test_packet_contains_no_source_or_expected_answers(self):
        p = reader.packet(self.target, self.qs)
        self.assertNotIn("source", p)
        self.assertEqual(p["report_template"]["answers"], [])
        self.assertFalse(p["report_template"]["reader"]["independent"])

    def test_actual_answer_record_is_not_accuracy_certificate(self):
        r = reader.review_data(self.target, self.report())
        self.assertEqual(r["status"], "responses_recorded")
        self.assertFalse(r["reader"]["independent"])
        self.assertIn("인증이 아닙니다", r["note"])

    def test_required_reader_missing_holds(self):
        r = audit.audit_data(self.target, self.target, require_reader_review=True)
        self.assertEqual(r["status"], "hold")
        self.assertEqual(r["mechanical_status"], "pass")
        self.assertIn("READ-0", r["fix_order"])

    def test_reader_integration_separate_from_semantic_review(self):
        r = audit.audit_data(self.target, self.target, reader_review=self.report(), require_reader_review=True)
        self.assertEqual(r["status"], "pass")
        self.assertEqual(r["semantic_review"]["status"], "not_checked")
        self.assertEqual(r["reader_review"]["status"], "responses_recorded")

    def test_stale_report_not_reused(self):
        r = audit.audit_data(self.target, self.target + " 수정.", reader_review=self.report())
        self.assertEqual(r["status"], "hold")
        self.assertEqual(r["reader_review"]["answers"], [])

    def test_partial_and_missing_answers(self):
        r = self.report()
        r["answers"].pop()
        self.assertEqual(reader.review_data(self.target, r)["status"], "partial")
        r = self.report()
        r["answers"][1].update(status="missing", answer="알 수 없습니다", evidence=[], reason="조건을 찾지 못했습니다")
        d = audit.audit_data(self.target, self.target, reader_review=r, require_reader_review=True)
        self.assertEqual(d["status"], "hold")
        self.assertIn("READ-1", d["fix_order"])
        self.assertEqual(d["mqm_heuristic"]["penalty"], 0)

    def test_out_of_scope_is_distinct_from_document_gap(self):
        r = self.report()
        r["answers"][1].update(status="out_of_scope", answer="문서 범위 밖입니다", evidence=[], reason="질문 목적이 다릅니다")
        d = reader.review_data(self.target, r)
        self.assertEqual(d["out_of_scope"], ["when"])
        self.assertEqual(d["gaps"], [])

    def test_all_out_of_scope_does_not_satisfy_required_review(self):
        r = self.report()
        for a in r["answers"]:
            a.update(status="out_of_scope", evidence=[], answer="범위 밖", reason="질문을 다시 정해야 합니다")
        d = audit.audit_data(self.target, self.target, reader_review=r, require_reader_review=True)
        self.assertEqual(d["status"], "hold")
        self.assertEqual(d["reader_review"]["status"], "no_in_scope_answers")

    def test_changed_questions_and_fabricated_evidence_rejected(self):
        for mutate in (
            lambda r: r["questions"][0].update(question="다른 질문"),
            lambda r: r["answers"][0].update(evidence=["문서에 없는 구절"]),
            lambda r: r["reader"].update(independent=True),
            lambda r: r["answers"].append(deepcopy(r["answers"][0])),
            lambda r: r["answers"][0].update(evidence=[]),
            lambda r: r.update(schema_version=True),
        ):
            r = self.report()
            mutate(r)
            with self.subTest(report=r), self.assertRaises(ValueError):
                reader.review_data(self.target, r)

    def test_line_endings(self):
        target = self.target.replace(". ", ".\n")
        r = reader.packet(target, self.qs)["report_template"]
        r.update(reader={"kind": "human", "name": "Reader", "context": "fresh", "independent": True},
                 summary="실제 독자 답변", answers=[])
        r["answers"] = [{"id": q["id"], "status": "answered", "answer": "응답", "reason": "근거", "evidence": [target]} for q in self.qs]
        self.assertEqual(reader.review_data(target.replace("\n", "\r\n"), r)["status"], "responses_recorded")

    def test_reader_cli_packet_then_check(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "target.md").write_text(self.target, encoding="utf-8")
            (root / "qs.json").write_text(json.dumps(self.qs), encoding="utf-8")
            (root / "report.json").write_text(json.dumps(self.report()), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(reader.main(["packet", str(root / "target.md"), "--questions", str(root / "qs.json"), "--output", str(root / "packet.json")]), 0)
                self.assertEqual(reader.main(["check", str(root / "target.md"), "--report", str(root / "report.json"), "--json"]), 0)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(reader.main(["packet", str(root / "target.md"), "--questions", str(root / "qs.json"), "--output", str(root / "packet.json")]), 3)

    def test_packaged_cli_routes_new_features_in_clean_process(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "target.md").write_text(self.target, encoding="utf-8")
            (root / "qs.json").write_text(json.dumps(self.qs), encoding="utf-8")
            (root / "report.json").write_text(json.dumps(self.report()), encoding="utf-8")
            manifest = {"schema_version": 1, "segments": [{"id": "a", "source": "target.md", "target": "target.md"}]}
            (root / "segments.json").write_text(json.dumps(manifest), encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
            commands = [
                ["translation-reader", "packet", "target.md", "--questions", "qs.json", "--output", "packet.json"],
                ["translation-reader", "check", "target.md", "--report", "report.json", "--json"],
                ["translation-impact", "snapshot", "segments.json", "--output", "baseline.json"],
                ["translation-impact", "plan", "segments.json", "--baseline", "baseline.json", "--json"],
                ["translation-audit", "target.md", "target.md", "--reader-review", "report.json", "--require-reader-review", "--json"],
            ]
            for command in commands:
                r = subprocess.run([sys.executable, "-c", "from neo_korean_writing.cli import main; raise SystemExit(main())", *command], cwd=root, env=env,
                                   capture_output=True, encoding="utf-8")
                self.assertEqual(r.returncode, 0, command[0] + "\n" + r.stderr)


if __name__ == "__main__":
    unittest.main()

