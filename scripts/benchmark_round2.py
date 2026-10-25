#!/usr/bin/env python3
"""Round-2 component benchmark. Does not generate/rate translations or call models."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import translation_audit as audit
import translation_session as session

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'tests/fixtures/benchmark_round2.json'


def session_case(name):
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        handoff, source, glossary = base/'handoff.json', base/'source.md', base/'terms.tsv'
        source.write_text('The vendor may reschedule.', encoding='utf-8')
        glossary.write_text('vendor\t공급사\n', encoding='utf-8')
        data = json.loads((ROOT/'templates/writer-editor-handoff.json').read_text(encoding='utf-8'))
        session.initialize(data, handoff, str(source), str(glossary), {'domain':'commerce'})
        session.record_decision(data, handoff, 'vendor', 'term', 'vendor', '공급사', 'adopted', 'model', '거래 주체')
        for stage in ('analysis', 'draft'):
            artifact = base/(stage+'.md')
            artifact.write_text(stage+' result', encoding='utf-8')
            session.checkpoint(data, handoff, stage, str(artifact))
        if name == 'source_change':
            source.write_text('The vendor will reschedule.', encoding='utf-8')
        elif name == 'glossary_change':
            glossary.write_text('vendor\t판매자\n', encoding='utf-8')
        elif name == 'draft_change':
            (base/'draft.md').write_text('초안 수정', encoding='utf-8')
        elif name == 'brief_change':
            data['context']['audience'] = '첫 거래를 하는 구매자'
        elif name == 'decision_change':
            session.record_decision(data, handoff, 'vendor', 'term', 'vendor', '판매자', 'adopted', 'editor', '소매 문맥')
        elif name != 'resume':
            raise ValueError('알 수 없는 재개 시나리오')
        result = session.inspect(data, base)
        expected_next = ('analysis' if name in ('source_change','glossary_change','brief_change')
                         else 'draft' if name in ('draft_change','decision_change') else 'review')
        okay = result['next_stage'] == expected_next
        if expected_next == 'analysis':
            okay = okay and not result['inputs_current'] and not result['usable_decisions']
        elif name == 'resume':
            okay = okay and result['status'] == 'ready' and len(result['usable_decisions']) == 1
        return {'matched': okay, 'next_stage': result['next_stage'], 'status': result['status']}


def evaluate(path=DEFAULT):
    raw = path.read_bytes()
    data = json.loads(raw)
    cases = data['cases']
    if data.get('schema_version') != 1 or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('벤치마크 스키마·고유 ID 오류')
    families = {'markup','icu','surface','glossary','semantic_review','session'}
    rows = []
    for case in cases:
        if case['family'] not in families or case['split'] not in ('development','verification'):
            raise ValueError('벤치마크 범주·분할 오류')
        row = {'id':case['id'], 'split':case['split'], 'family':case['family']}
        try:
            if case['family'] == 'session':
                row.update(session_case(case['scenario']))
            else:
                entries = [audit._glossary_entry(e['source'], e['target'], e.get('forbid', []),
                           e.get('mode','flex'), e.get('context',''), e.get('domains'), e.get('segments'))
                           for e in case.get('glossary', [])]
                result = audit.audit_data(case['source'], case['target'], format_profile=case['format'],
                                          glossary=entries or None, domain=case.get('domain'))
                row.update(status=result['status'], risk_ids=[r['id'] for r in result['risks']])
                if case['family'] == 'semantic_review':
                    row.update(matched=None, review_reason=case['review_reason'],
                               human_review_required=result['human_review_required'])
                else:
                    if type(case.get('expected_clean')) is not bool:
                        raise ValueError('기계 점검 기대값은 bool이어야 합니다')
                    actual = (result['placeholders']['pass'] if case['family'] in ('markup','icu') else
                              result['surface_lock']['pass'] if case['family'] == 'surface' else
                              not result['glossary']['issues'])
                    row.update(expected_clean=case['expected_clean'], actual_clean=actual,
                               matched=actual == case['expected_clean'])
        except Exception as exc:
            # Keep the failing case in the report; never count crashes as successful blocking.
            row.update(matched=False, error=type(exc).__name__+': '+str(exc))
        rows.append(row)
    scored = [r for r in rows if r['family'] != 'semantic_review']
    summary = {}
    for key in sorted(families - {'semantic_review'}):
        group = [r for r in scored if r['family'] == key]
        summary[key] = {'matched':sum(r['matched'] for r in group), 'total':len(group)}
    splits = {s:{'matched':sum(r['matched'] for r in scored if r['split']==s),
                 'total':sum(r['split']==s for r in scored)} for s in ('development','verification')}
    return {'schema_version':1, 'fixtures_sha256':hashlib.sha256(raw).hexdigest(),
            'fixtures_sha256_lf':hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest(),
            'baseline_commit':data['baseline_commit'], 'tool_version':audit.VERSION,
            'mechanical':{'matched':sum(r['matched'] for r in scored), 'total':len(scored),
                          'crashes':sum('error' in r for r in scored),
                          'false_blocks':sum(r.get('expected_clean') is True and not r['matched'] for r in scored),
                          'missed_damage':sum(r.get('expected_clean') is False and not r['matched'] for r in scored)},
            'by_family':summary, 'by_split':splits,
            'semantic_review':{'total':sum(r['family']=='semantic_review' for r in rows), 'scored':False,
                               'automatic_passes':sum(r['family']=='semantic_review' and r.get('status')=='pass' for r in rows)},
            'interpretation':'Authored development fixtures, not independent translation-quality evaluation. Semantic cases require source comparison and are excluded from the mechanical success rate.',
            'cases':rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=DEFAULT)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check', action='store_true')
    ns = parser.parse_args(argv)
    result = evaluate(ns.fixtures)
    if ns.output:
        ns.output.parent.mkdir(parents=True, exist_ok=True)
        ns.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False,indent=2))
    return 1 if ns.check and result['mechanical']['matched'] != result['mechanical']['total'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
