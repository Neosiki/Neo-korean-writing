"""Keep the frozen benchmark and its reporting boundary reproducible."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import benchmark_round2 as bench
import translation_audit as audit


class Round2Benchmark(unittest.TestCase):
    def test_reports_compare_identical_frozen_cases(self):
        before = json.loads((ROOT/'benchmarks/round2-baseline.json').read_text(encoding='utf-8'))
        after = json.loads((ROOT/'benchmarks/round2-after.json').read_text(encoding='utf-8'))
        digest = hashlib.sha256(bench.DEFAULT.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        self.assertEqual(before['fixtures_sha256_lf'], digest)
        self.assertEqual(after['fixtures_sha256_lf'], digest)
        self.assertEqual({r['id'] for r in before['cases']}, {r['id'] for r in after['cases']})
        self.assertEqual(before['mechanical']['total'], after['mechanical']['total'])

    def test_live_benchmark_and_unscored_semantic_cases(self):
        report = bench.evaluate()
        failed = [r['id'] for r in report['cases'] if r['matched'] is False]
        self.assertEqual(failed, [])
        self.assertEqual(report['mechanical']['total'], 60)
        self.assertEqual(report['mechanical']['crashes'], 0)
        semantic = [r for r in report['cases'] if r['family']=='semantic_review']
        self.assertEqual(len(semantic), 6)
        self.assertTrue(all(r['matched'] is None for r in semantic))
        self.assertFalse(report['semantic_review']['scored'])

    def test_repeated_root_control_cannot_disappear(self):
        part = '{n, plural, other {# rows}}'
        result = audit.audit_data(part+' '+part, part, format_profile='icu')
        self.assertFalse(result['placeholders']['pass'])

    def test_attribute_binding_allows_sibling_reordering(self):
        source = '<a href="/one">{one}</a><a href="/two">{two}</a>'
        target = '<a href="/two">{two}</a><a href="/one">{one}</a>'
        self.assertTrue(audit.audit_data(source,target,format_profile='html')['placeholders']['pass'])


if __name__ == '__main__':
    unittest.main()
