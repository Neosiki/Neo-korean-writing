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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import translation_audit as audit
import translation_semantics as meaning
import benchmark_semantic_retry as benchmark


class SemanticReview(unittest.TestCase):
    def setUp(self):
        self.source='The clinic may reopen.'
        self.target='병원이 다시 문을 연다.'
        records=json.loads((ROOT/'benchmarks/semantic-retry-model-reviews.json').read_text(encoding='utf-8'))
        self.report=next(r['report'] for r in records['reviews'] if r['id']=='poss-original')

    def test_missing_review_is_visible_not_certified(self):
        result=audit.audit_data(self.source,self.target)
        self.assertEqual(result['mechanical_status'],'pass')
        self.assertEqual(result['semantic_review']['status'],'not_checked')
        self.assertTrue(result['human_review_required'])

    def test_required_review_blocks_without_report(self):
        result=audit.audit_data(self.source,self.target,require_semantic_review=True)
        self.assertEqual(result['status'],'hold')
        self.assertIn('SEM-0',[r['id'] for r in result['risks']])

    def test_model_finding_does_not_relabel_mechanical_result(self):
        result=audit.audit_data(self.source,self.target,semantic_review=self.report)
        self.assertEqual(result['mechanical_status'],'pass')
        self.assertEqual(result['status'],'warn')
        self.assertEqual(result['semantic_review']['status'],'reviewed_with_findings')
        issue=next(r for r in result['risks'] if r['id']=='SEM-1')
        self.assertEqual(issue['state'],'검토 후보')
        self.assertEqual(issue['basis'],'model-or-human-review')
        self.assertEqual(result['mqm_heuristic']['penalty'],0)

    def test_strict_holds_reviewed_major_candidate(self):
        result=audit._apply_strict(audit.audit_data(self.source,self.target,semantic_review=self.report))
        self.assertEqual(result['status'],'hold')

    def test_changed_target_makes_report_stale(self):
        result=audit.audit_data(self.source,'병원이 다시 문을 열 가능성이 있다.',semantic_review=self.report)
        self.assertEqual(result['semantic_review']['status'],'stale')
        self.assertEqual(result['semantic_review']['findings'],[])
        self.assertEqual(result['status'],'hold')

    def test_changed_source_makes_report_stale(self):
        result=audit.audit_data('The clinic will reopen.',self.target,semantic_review=self.report)
        self.assertEqual(result['semantic_review']['status'],'stale')

    def test_partial_review_is_not_complete(self):
        report=deepcopy(self.report)
        report['dimensions_reviewed']=['modality']
        result=audit.audit_data(self.source,self.target,semantic_review=report,require_semantic_review=True)
        self.assertEqual(result['semantic_review']['status'],'partial')
        self.assertEqual(result['status'],'hold')

    def test_unmatched_evidence_is_rejected(self):
        report=deepcopy(self.report)
        report['findings'][0]['target_quote']='없는 인용'
        with self.assertRaises(ValueError):
            meaning.review_data(self.source,self.target,report)

    def test_corrupt_reports_are_rejected(self):
        mutations=[lambda r:r.update(schema_version=True),lambda r:r.update(dimensions_reviewed=['modality','modality']),
                   lambda r:r.update(source_sha256='bad'),lambda r:r['reviewer'].update(name=''),
                   lambda r:r.update(coverage='unknown'),lambda r:r.update(findings={}),
                   lambda r:r.update(summary=''),lambda r:r['findings'][0].update(dimension='unknown')]
        for mutate in mutations:
            report=deepcopy(self.report); mutate(report)
            with self.subTest(report=report),self.assertRaises(ValueError):
                meaning.review_data(self.source,self.target,report)

    def test_line_ending_normalization_keeps_valid_quotes(self):
        source='First.\nThe clinic may reopen.'
        target='첫 문장.\n병원이 다시 문을 연다.'
        report=deepcopy(self.report)
        report.update(source_sha256=meaning.text_hash(source),target_sha256=meaning.text_hash(target))
        report['findings'][0].update(source_quote=source,target_quote=target)
        result=meaning.review_data(source.replace('\n','\r\n'),target.replace('\n','\r\n'),report)
        self.assertEqual(result['status'],'reviewed_with_findings')

    def test_packet_is_unreviewed_template_not_fake_findings(self):
        packet=meaning.packet(self.source,self.target)
        template=packet['report_template']
        self.assertEqual(template['dimensions_reviewed'],[])
        self.assertEqual(template['findings'],[])
        with self.assertRaises(ValueError):
            meaning.review_data(self.source,self.target,template)

    def test_cli_packet_export_and_report_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'s.md').write_text(self.source,encoding='utf-8')
            (p/'t.md').write_text(self.target,encoding='utf-8')
            (p/'review.json').write_text(json.dumps(self.report),encoding='utf-8')
            base=[str(p/'s.md'),str(p/'t.md')]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(audit.main(base+['--semantic-packet',str(p/'packet.json')]),0)
            packet=json.loads((p/'packet.json').read_text(encoding='utf-8'))
            self.assertEqual(packet['source'],self.source)
            original=(p/'packet.json').read_bytes()
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(audit.main(base+['--semantic-packet',str(p/'packet.json')]),3)
            self.assertEqual((p/'packet.json').read_bytes(),original)
            args=base+['--semantic-review',str(p/'review.json'),'--require-semantic-review','--strict','--json']
            proc=subprocess.run([sys.executable,'-m','neo_korean_writing.cli','translation-audit',*args],
                                cwd=p,env={**os.environ,'PYTHONPATH':str(ROOT/'src')},capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(proc.returncode,2,proc.stderr)
            result=json.loads(proc.stdout)
            self.assertEqual(result['semantic_review']['status'],'reviewed_with_findings')

    def test_null_report_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            for name,text in [('s',self.source),('t',self.target),('r','null')]:
                (p/name).write_text(text,encoding='utf-8')
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(audit.main([str(p/'s'),str(p/'t'),'--semantic-review',str(p/'r')]),3)

    def test_recorded_model_reviews_and_limits_are_reproducible(self):
        report=benchmark.evaluate()
        self.assertEqual(report['original_six']['review_flags'],6)
        self.assertEqual(report['error_pairs']['flagged_by_recorded_review'],12)
        self.assertEqual(report['correct_pairs']['false_flags_by_recorded_review'],0)
        self.assertEqual(report['external_api_calls'],0)
        self.assertIn('not hidden',report['independence'])


if __name__=='__main__':
    unittest.main()
