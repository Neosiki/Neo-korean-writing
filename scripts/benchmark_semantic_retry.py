#!/usr/bin/env python3
"""Replay explicit session-authored model reviews. Does not call a model.

The figures compare recorded self-review decisions with same-author labels;
they are not blind inference accuracy, an API evaluation, or independent QA.
"""
import argparse
import hashlib
import json
from pathlib import Path

import translation_audit as audit

ROOT=Path(__file__).resolve().parents[1]
FIXTURES=ROOT/'tests/fixtures/semantic_retry.json'
REVIEWS=ROOT/'benchmarks/semantic-retry-model-reviews.json'


def evaluate(fixtures=FIXTURES,reviews=REVIEWS):
    source=json.loads(fixtures.read_text(encoding='utf-8'))
    decisions=json.loads(reviews.read_text(encoding='utf-8'))
    cases=source['cases']
    records={r['id']:r['report'] for r in decisions['reviews']}
    if len(records)!=len(decisions['reviews']) or set(records)!={c['id'] for c in cases}:
        raise ValueError('사례와 검토 기록의 고유 ID가 맞지 않습니다')
    rows=[]
    for case in cases:
        raw=audit.audit_data(case['source'],case['target'])
        reviewed=audit.audit_data(case['source'],case['target'],semantic_review=records[case['id']],require_semantic_review=True)
        meaning=reviewed['semantic_review']
        findings=meaning['findings']
        predicted=bool(findings)
        expected=case['expected_issue']
        covered=meaning['status'] in ('reviewed_with_findings','reviewed_no_findings')
        correct_dimension=not expected or case['dimension'] in {f['dimension'] for f in findings}
        rows.append({'id':case['id'],'origin':case['origin'],'expected_issue':expected,
                     'mechanical_status':raw['mechanical_status'],'without_review':raw['semantic_review']['status'],
                     'with_review':meaning['status'],'combined_status':reviewed['status'],
                     'findings':findings,'matched':covered and predicted==expected and correct_dimension})
    wrong=[r for r in rows if r['expected_issue']]
    good=[r for r in rows if not r['expected_issue']]
    old=[r for r in wrong if r['origin']=='round2']
    return {'schema_version':1,'tool_version':audit.VERSION,
            'fixture_sha256_lf':hashlib.sha256(fixtures.read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
            'review_sha256_lf':hashlib.sha256(reviews.read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
            'method':decisions['method'],'independence':decisions['independence'],
            'external_api_calls':0,'case_count':len(rows),'report_label_agreement':sum(r['matched'] for r in rows),
            'error_pairs':{'total':len(wrong),'flagged_by_recorded_review':sum(bool(r['findings']) for r in wrong)},
            'correct_pairs':{'total':len(good),'false_flags_by_recorded_review':sum(bool(r['findings']) for r in good)},
            'original_six':{'total':len(old),'mechanical_passes':sum(r['mechanical_status']=='pass' for r in old),
                            'review_flags':sum(bool(r['findings']) for r in old)},
            'note':'Recorded current-session self-review, not an independently measured semantic detector. A fresh input needs a fresh model/human review.',
            'cases':rows}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--check',action='store_true')
    ns=parser.parse_args(argv)
    report=evaluate()
    if ns.output:
        ns.output.parent.mkdir(parents=True,exist_ok=True)
        ns.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},ensure_ascii=False,indent=2))
    return 1 if ns.check and report['report_label_agreement']!=report['case_count'] else 0


if __name__=='__main__':
    raise SystemExit(main())
