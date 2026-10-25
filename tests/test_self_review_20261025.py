"""Regression cases found by reviewing invalid inputs after v10.4 shipped."""
import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import translation_audit as audit
import translation_session as session


class FormatSelfReview(unittest.TestCase):
    def test_duplicate_boolean_attribute_is_reported_not_crashed(self):
        for target in ('<input disabled disabled="disabled">', '<input disabled="disabled" disabled>'):
            with self.subTest(target=target):
                data = audit.audit_data('<input disabled>', target, format_profile="html")
                self.assertEqual(data["status"], "hold")
                self.assertFalse(data["format_validation"]["pass"])
                self.assertTrue(any(i["kind"] == "html.syntax" for i in data["format_validation"]["issues"]))

    def test_deep_xml_is_checked_without_python_recursion(self):
        source = '<x>' * 1100 + 'Hello' + '</x>' * 1100
        target = '<x>' * 1100 + '안녕' + '</x>' * 1100
        self.assertTrue(audit.audit_data(source, target, format_profile="xml")["format_validation"]["pass"])
        broken = '<x>' * 1100 + '안녕' + '</x>' * 1099
        self.assertFalse(audit.audit_data(source, broken, format_profile="xml")["format_validation"]["pass"])

    def test_bad_html_cli_keeps_json_error_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 's.html').write_text('<input disabled>', encoding='utf-8')
            (base / 't.html').write_text('<input disabled disabled="disabled">', encoding='utf-8')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = audit.main([str(base/'s.html'), str(base/'t.html'), '--format', 'html', '--json'])
            self.assertEqual(code, 2)
            self.assertFalse(json.loads(out.getvalue())["placeholders"]["pass"])


class GlossarySelfReview(unittest.TestCase):
    def test_malformed_glossaries_are_input_errors(self):
        valid = {"source": "bank", "target": ["은행"]}
        bad = [None, 7, [7], [{"target": "은행"}], [{"source": "bank", "targets": ["은행"]}]]
        bad += [[{**valid, k: v}] for k, v in (
            ("source", 7), ("source", ""), ("target", 7), ("forbid", {}),
            ("allowed", [7]), ("domains", 7), ("segments", [7]),
            ("mode", "strict_typo"), ("mode", False), ("context", {}))]
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base/'s.md').write_text('bank', encoding='utf-8')
            (base/'t.md').write_text('은행', encoding='utf-8')
            for value in bad:
                with self.subTest(value=value):
                    glossary = base/'terms.json'
                    glossary.write_text(json.dumps(value), encoding='utf-8')
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err):
                        code = audit.main([str(base/'s.md'), str(base/'t.md'), '--glossary', str(glossary)])
                    self.assertEqual(code, 3)
                    self.assertNotIn('Traceback', err.getvalue())

    def test_empty_tsv_source_is_not_shifted_into_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'terms.tsv'
            path.write_text('\t은행\t금지\tstrict\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                audit.load_glossary(str(path))

    def test_existing_legacy_and_scoped_glossaries_still_load(self):
        values = [{"bank": "은행"}, {"bank": ["은행", "뱅크"]},
                  [{"source": "bank", "target": ["은행"], "domains": ["finance"], "mode": "strict"}]]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'terms.json'
            for value in values:
                with self.subTest(value=value):
                    path.write_text(json.dumps(value), encoding='utf-8')
                    entry = audit.load_glossary(str(path))[0]
                    self.assertIn('은행', entry['targets'])


class SessionSelfReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.handoff = self.base/'handoff.json'
        self.source = self.base/'source.md'
        self.source.write_text('The bank may reopen.', encoding='utf-8')
        self.data = json.loads((ROOT/'templates/writer-editor-handoff.json').read_text(encoding='utf-8'))
        session.initialize(self.data, self.handoff, str(self.source))
        session.record_decision(self.data, self.handoff, 'bank', 'term', 'bank', '은행', 'adopted', 'model', '금융 문맥')
        artifact = self.base/'analysis.md'
        artifact.write_text('분석 결과', encoding='utf-8')
        session.checkpoint(self.data, self.handoff, 'analysis', str(artifact))

    def test_corrupt_state_rejected_without_overwriting_handoff(self):
        cases = [
            lambda s: s.update(history={}),
            lambda s: s.pop('history'),
            lambda s: s.update(version=True),
            lambda s: s['source'].update(sha256='not-a-hash'),
            lambda s: s['settings'].update(format='not-a-format'),
            lambda s: s['settings'].pop('domain'),
            lambda s: s['stages'].update(analysis=7),
            lambda s: s['stages']['analysis'].update(artifact=None),
            lambda s: s['stages']['analysis'].update(parent_sha256='a'*64),
            lambda s: s['decisions'][0].pop('id'),
            lambda s: s['decisions'][0].update(target=''),
            lambda s: s['decisions'][0].update(owner='someone'),
            lambda s: s['decisions'][0].update(scope='finance'),
            lambda s: s['decisions'].append(deepcopy(s['decisions'][0])),
        ]
        for index, mutate in enumerate(cases):
            with self.subTest(case=index):
                data = deepcopy(self.data)
                mutate(data[session.KEY])
                session.save(self.handoff, data)
                before = self.handoff.read_bytes()
                for action in ('inspect', 'decision'):
                    args = [action, str(self.handoff), '--json']
                    if action == 'decision':
                        args += ['--id', 'bank', '--kind', 'term', '--source-text', 'bank', '--target', '은행', '--reason', '문맥']
                    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                        code = session.main(args)
                    self.assertEqual(code, 3)
                    self.assertEqual(self.handoff.read_bytes(), before)

    def test_history_updates_normally_after_replacing_stage(self):
        artifact = self.base/'new-analysis.md'
        artifact.write_text('새 분석', encoding='utf-8')
        session.checkpoint(self.data, self.handoff, 'analysis', str(artifact))
        self.assertTrue(self.data[session.KEY]['history'])
        self.assertEqual(session.inspect(self.data, self.base)['next_stage'], 'draft')


if __name__ == '__main__':
    unittest.main()
