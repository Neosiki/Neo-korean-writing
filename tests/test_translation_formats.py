"""Own synthetic cases: no third-party article text or model calls."""
import contextlib
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
from translation_formats import compare_formats, resolve_profile


class Formats(unittest.TestCase):
    def check_format(self, source, target, expected, profile="auto"):
        report = audit.audit_data(source, target, format_profile=profile)
        self.assertEqual(report["placeholders"]["pass"], expected, report)
        if not expected:
            self.assertIn("FID-10", [r["id"] for r in report["risks"]])
        return report

    def test_nesting_not_just_counts(self):
        self.check_format("<b><i>Hello</i></b>", "<b><i>안녕</b></i>", False)

    def test_hierarchy_change(self):
        self.check_format("<b><i>Hello</i></b>", "<b>안녕</b><i>하세요</i>", False)

    def test_alt_translation_allowed(self):
        data = self.check_format('<img src="a.png" alt="Open settings">', '<img src="a.png" alt="설정 열기">', True)
        self.assertTrue(data["surface_lock"]["pass"])

    def test_attribute_order_and_quotes(self):
        self.check_format('<img src="a.png" alt="Open">', "<img alt='열기' src='a.png'/>", True)

    def test_attribute_variable_protected(self):
        self.check_format('<img alt="Hello {name}">', '<img alt="안녕 {user}">', False)

    def test_attribute_presence_protected(self):
        self.check_format('<img alt="Open">', '<img>', False)

    def test_quoted_greater_than(self):
        self.check_format('<span title="More > {n}">Open</span>', '<span title="더 보기 > {n}">열기</span>', True)

    def test_escaped_markup_is_text(self):
        self.check_format('<p>&lt;b&gt; means bold</p>', '<p>&lt;b&gt;는 굵게 표시한다</p>', True)

    def test_src_protected(self):
        self.check_format('<img src="a.png">', '<img src="b.png">', False)

    def test_duplicate_attributes(self):
        self.check_format('<b title="One">Open</b>', '<b title="하나" title="둘">열기</b>', False)

    def test_truncated_tag(self):
        self.check_format('<b>Open</b>', '<b>열기</b', False)

    def test_code_is_not_auto_markup(self):
        self.assertEqual(resolve_profile('`<b>`\n\n```html\n<img>\n```'), "plain")

    def test_code_still_locked(self):
        data = audit.audit_data('```html\n<b>Open</b>\n```', '```html\n<b>열기</b>\n```')
        self.assertFalse(data["surface_lock"]["pass"])

    def test_plain_opt_out(self):
        self.assertEqual(resolve_profile("<Example>", "plain"), "plain")

    def test_xml_namespaces(self):
        self.check_format('<x:r xmlns:x="urn:test"><x:b title="Open"/></x:r>', '<x:r xmlns:x="urn:test"><x:b title="열기"/></x:r>', True, "xml")

    def test_xml_case_sensitive(self):
        self.check_format('<Root><B/></Root>', '<Root><b/></Root>', False, "xml")

    def test_xml_wrapper_name_is_not_exempt(self):
        self.check_format('<audit-root>Hello</audit-root>', '안녕', False, "xml")

    def test_xml_reject_dtd(self):
        self.check_format('<r>Open</r>', '<!DOCTYPE r [<!ENTITY x "bad">]><r>&x;</r>', False, "xml")

    def test_icu_missing_brace(self):
        self.check_format('{n, plural, one {One item} other {# items}}', '{n, plural, one {한 개} other {#개}', False)

    def test_icu_localized_plural(self):
        self.check_format('{n, plural, one {One item} other {# items}}', '{n, plural, other {#개}}', True)

    def test_icu_other_required(self):
        self.check_format('{n, plural, other {# items}}', '{n, plural, one {한 개}}', False)

    def test_icu_duplicate_selector(self):
        self.check_format('{n, plural, other {# items}}', '{n, plural, other {#개} other {항목}}', False)

    def test_icu_variable_type(self):
        self.check_format('Hello {name}', '안녕 {name, number}', False, "icu")

    def test_icu_hash_not_lost(self):
        self.check_format('{n, plural, other {# items}}', '{n, plural, other {항목}}', False)

    def test_icu_number_style_not_changed(self):
        self.check_format('{n, number, integer}', '{n, number, currency}', False, "icu")

    def test_icu_variable_rename(self):
        self.check_format('{n, plural, other {Hello {name}}}', '{n, plural, other {안녕 {user}}}', False)

    def test_icu_select_branch_protected(self):
        self.check_format('{role, select, admin {Admin} other {Guest}}', '{role, select, owner {관리자} other {손님}}', False)

    def test_icu_select_variable_swap(self):
        self.check_format('{r, select, a {{x}} other {{y}}}', '{r, select, a {{y}} other {{x}}}', False)

    def test_icu_exact_value_protected(self):
        self.check_format('{n, plural, =0 {None} other {# items}}', '{n, plural, other {#개}}', False)

    def test_icu_offset_protected(self):
        self.check_format('{n, plural, offset:1 other {# items}}', '{n, plural, offset:2 other {#개}}', False)

    def test_icu_escaped_braces(self):
        self.check_format("Hello '{name}'", "안녕 '{name}'", True, "icu")

    def test_baseline_uses_same_attribute_policy(self):
        src = '<img alt="Open settings">'
        data = audit.audit_data(src, '<img alt="설정 열기">', baseline=src)
        self.assertEqual(data["baseline_delta"]["surface_lock"]["introduced_missing"], [])


class ScopedGlossary(unittest.TestCase):
    def entry(self, target, domains=None, segments=None):
        return audit._glossary_entry("bank", [target], [], domains=domains, segments=segments)

    def test_domain_selects_one_sense(self):
        entries = [self.entry("은행", ["finance"]), self.entry("강둑", ["geography"])]
        report = audit.glossary_check("bank", "은행", entries, domain="finance")
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["applicable"], 1)

    def test_wrong_term_in_selected_domain(self):
        report = audit.glossary_check("bank", "강둑", [self.entry("은행", ["finance"])], domain="finance")
        self.assertEqual(report["issues"][0]["kind"], "missing_target")

    def test_missing_scope_defers(self):
        data = audit.audit_data("bank", "은행", glossary=[self.entry("은행", ["finance"])])
        self.assertEqual(data["glossary"]["issues"], [])
        self.assertEqual(next(r for r in data["risks"] if r["id"] == "TERM-4")["severity"], "review")

    def test_conflicting_unscoped_defers(self):
        report = audit.glossary_check("bank", "은행", [self.entry("은행"), self.entry("강둑")])
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["deferred"][0]["reason"], "ambiguous_sense")

    def test_segment_requires_domain_too(self):
        entry = self.entry("은행", ["finance"], ["intro"])
        self.assertEqual(audit.glossary_check("bank", "은행", [entry], "finance")["applicable"], 0)
        self.assertEqual(audit.glossary_check("bank", "은행", [entry], "finance", "intro")["applicable"], 1)

    def test_scoped_overrides_fallback(self):
        report = audit.glossary_check("bank", "강둑", [self.entry("은행"), self.entry("강둑", ["geography"])], "geography")
        self.assertEqual(report["issues"], [])

    def test_context_note_is_not_selector(self):
        entry = audit._glossary_entry("bank", ["은행"], [], context="finance")
        self.assertEqual(audit.glossary_check("bank", "은행", [entry])["applicable"], 1)

    def test_irrelevant_domain_needs_no_segment(self):
        entry = self.entry("강둑", ["geography"], ["intro"])
        report = audit.glossary_check("bank", "은행", [entry], "finance")
        self.assertEqual(report["deferred"], [])

    def test_json_tsv_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for name, text in {"source.txt": "bank", "target.txt": "은행", "glossary.json": json.dumps([{"source":"bank", "target":["은행"], "domains":["finance"], "segments":["intro"]}]), "glossary.tsv": "bank\t은행\t\tflex\t설명\tfinance\tintro\n"}.items():
                (p / name).write_text(text, encoding="utf-8")
            for filename in ("glossary.tsv", "glossary.json"):
                entry = audit.load_glossary(str(p / filename))[0]
                self.assertEqual((entry["domains"], entry["segments"]), (["finance"], ["intro"]))
            for glossary in ("glossary.json", "glossary.tsv"):
                args = [str(p / "source.txt"), str(p / "target.txt"), "--glossary", str(p / glossary), "--domain", "finance", "--segment-id", "intro", "--format", "plain", "--json"]
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = audit.main(args)
                self.assertIn(code, (0, 1))
                self.assertEqual(json.loads(out.getvalue())["glossary"]["applicable"], 1)
            result = subprocess.run([sys.executable, "-m", "neo_korean_writing.cli", "translation-audit", *args], cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, capture_output=True, text=True, encoding="utf-8")
            self.assertIn(result.returncode, (0, 1), result.stderr)
            self.assertEqual(json.loads(result.stdout)["format_validation"]["profile"], "plain")


if __name__ == "__main__":
    unittest.main()
