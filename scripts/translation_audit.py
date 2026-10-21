#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""번역 후편집용 충실성·문체 위험 감사 도구 (표준 라이브러리만 사용).

이 도구는 번역 품질을 자동 판정하지 않는다. 공유 표면 토큰과 문서 구조를
기계적으로 대조하고, 한국어 번역에서 자주 생기는 위험을 사람 검토 목록으로
올린다. 문학 모드는 데보라 스미스를 모방하는 기능이 아니라, 독자 친화성·정조·
모호성·반복을 함께 검토하기 위한 대비 기준이다.

v8 고도화(2026-10): MQM식 심각도 등급(치명·주요·경미)과 고칠 순서, 용어집 일관성
검사(--glossary), 문단 단위 누락·추가 후보, 한국어 번역문의 영어 잔류, 자리표시자
({name}, %s, {{x}}, <b>) 손상 검사를 추가했다. 모든 등급은 사람이 MQM으로 평가하기
전에 훑어보는 휴리스틱이며 번역 품질 점수가 아니다.

사용법:
  python3 translation_audit.py 원문.md 번역문.md
  python3 translation_audit.py 원문.md 번역문.md --direction en-to-ko --literary --json
  python3 translation_audit.py 원문.md 번역문.md --glossary 용어집.tsv --strict
"""
import argparse
import json
import os
import re
import statistics
import sys
from collections import Counter

VERSION = "8.0.0"
SEVERITY_RANK = {"critical": 0, "major": 1, "minor": 2, "review": 3}
MQM_WEIGHT = {"critical": 25, "major": 5, "minor": 1, "review": 0}
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

URL_RE = re.compile(r"https?://[^\s)>'\"]+")
NUMBER_RE = re.compile(
    r"(?<![A-Za-z])\d[\d,.]*(?:\s*(?:%|퍼센트|억|만|천|원|명|개|년|월|일|시|분|배|건|회|km|m|cm|kg|g))?"
)
CODE_RE = re.compile(r"`([^`\n]+)`")
ACRONYM_RE = re.compile(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}(?:[-_][A-Z0-9]+)*|GPT-\d+(?:\.\d+)?|BERT|NLLB)(?![A-Za-z0-9])")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PLACEHOLDER_RE = re.compile(
    r"\{\{[^{}\n]+\}\}|\$\{[^{}\n]+\}|\{[A-Za-z_][\w.]*(?:\s*,[^{}\n]*)?\}"
    r"|%\d*\$?[sdif]|%\([A-Za-z_]\w*\)[sdif]"
    r"|</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>\n]*)?/?>"
)
LATIN_RUN_RE = re.compile(
    r"(?<![A-Za-z0-9_/.@-])[A-Za-z][A-Za-z'\u2019-]*(?:\s+[A-Za-z][A-Za-z'\u2019-]*){2,}(?![A-Za-z0-9_/-])"
)
FENCE_RE = re.compile(r"(?m)^ {0,3}(`{3,}|~{3,})[^\n]*\n[\s\S]*?^ {0,3}\1[^\n]*(?:\n|$)")

KOREAN_PRONOUNS = re.compile(r"(?<![가-힣])(?:그녀의|그들의|그녀|그들|그것|그의|그)(?:는|가|를|에게|의|도|만|들이|들도)?(?![가-힣])")
KOREAN_INTENSIFIERS = re.compile(r"(?:매우|정말|대단히|몹시|너무|굉장히|아주|극도로|놀랍게도)")
TRANSLATIONESE_RE = re.compile(
    r"(?:에\s*의해|[를을]\s*통해|에\s*있(?:어|어서)|와\s*관련하여|에\s*기반하여|"
    r"되어진다|지게\s*된다|가지고\s*있다|그녀|그들|그것|그들은|그녀는)"
)


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _counts(pattern, text):
    return Counter(pattern.findall(text))


def _normalized_number(value):
    return re.sub(r"\s+", "", value)


def shared_locks(text):
    """번역되어도 그대로 남아야 하는 표면 토큰만 추출한다."""
    out = {}
    out["url"] = list(URL_RE.findall(text))
    out["number"] = [_normalized_number(x) for x in NUMBER_RE.findall(text)]
    out["code"] = CODE_RE.findall(text)
    out["acronym"] = ACRONYM_RE.findall(text)
    out["link_target"] = MARKDOWN_LINK_RE.findall(text)
    out["placeholder"] = PLACEHOLDER_RE.findall(text)
    return out


def _missing_counts(before, after):
    missing = []
    for kind, values in before.items():
        b = Counter(values)
        a = Counter(after.get(kind, []))
        for value, count in (b - a).items():
            missing.append({"kind": kind, "value": value, "count": count})
    return missing


def _extra_counts(before, after):
    extra = []
    for kind, values in after.items():
        b = Counter(before.get(kind, []))
        a = Counter(values)
        for value, count in (a - b).items():
            extra.append({"kind": kind, "value": value, "count": count})
    return extra


def structure_data(text):
    return {
        "headings": len(re.findall(r"^\s*#{1,6}\s+", text, re.M)),
        "bullet_items": len(re.findall(r"^\s*[-*+]\s+", text, re.M)),
        "table_rows": len(re.findall(r"^\s*\|", text, re.M)),
        "code_blocks": text.count("```") // 2,
        "links": len(MARKDOWN_LINK_RE.findall(text)),
        "paragraphs": len([p for p in re.split(r"\n\s*\n", text) if p.strip()]),
        "sentences": len([s for s in re.split(r"(?<=[.!?다요임함])\s+", text) if len(s.strip()) >= 5]),
    }


def _risk(id_, level, label, evidence, action, severity="minor", mqm="Style", count=1):
    return {
        "id": id_, "level": level, "label": label, "evidence": evidence, "action": action,
        "severity": severity, "mqm": mqm, "count": max(int(count), 1),
    }


def _paragraphs(text):
    text = FENCE_RE.sub("", text)
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def paragraph_alignment(source, target):
    """문단 대응표: 문단 수와 문단별 길이비로 누락·추가 후보를 올린다."""
    sp, tp = _paragraphs(source), _paragraphs(target)
    out = {"source_paragraphs": len(sp), "target_paragraphs": len(tp),
           "count_match": len(sp) == len(tp), "outliers": []}
    if len(sp) == len(tp) and len(sp) >= 3:
        ratios = [len(t) / max(len(s), 1) for s, t in zip(sp, tp)]
        med = statistics.median(ratios)
        if med > 0:
            for i, (r, s, t) in enumerate(zip(ratios, sp, tp), 1):
                rel = r / med
                if rel < 0.35 and len(s) >= 40:
                    kind = "omission_suspect"
                elif rel > 2.5 and len(t) >= 40:
                    kind = "addition_suspect"
                else:
                    continue
                out["outliers"].append({
                    "paragraph": i, "kind": kind, "relative_length": round(rel, 2),
                    "source_excerpt": s[:40], "target_excerpt": t[:40],
                })
    return out


def english_residue(target, allowed=()):
    """한국어 번역문에 번역되지 않은 영어 구절(3단어 이상)이 남았는지 찾는다."""
    text = FENCE_RE.sub(" ", target)
    text = CODE_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    # Link labels remain reader-visible prose; only targets are exempt.
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = PLACEHOLDER_RE.sub(" ", text)
    for term in sorted((a for a in allowed if a), key=len, reverse=True):
        text = re.sub(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", " ", text, flags=re.I)
    runs = []
    for run in LATIN_RUN_RE.findall(text):
        words = run.split()
        if all(w.isupper() for w in words):
            continue
        runs.append(run)
    return runs


def _term_in(text, term):
    if re.search(r"[A-Za-z]", term):
        return re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", text, re.I) is not None
    return term in text


def _term_count(text, term):
    if re.search(r"[A-Za-z]", term):
        return len(re.findall(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", text, re.I))
    return text.count(term)


def _split_alts(value):
    return [x.strip() for x in re.split(r"\s*\|\s*", value or "") if x.strip()]


def load_glossary(path):
    """용어집 읽기. JSON 또는 TSV/CSV/`=>` 텍스트.

    행 형식: 원어 [탭|=>|->|,] 허용역어1|허용역어2 [탭|=>|->|,] 금지역어1|금지역어2
    JSON: {"원어": "역어"} / {"원어": ["역어1", "역어2"]} /
          [{"source": "...", "target": ["..."], "forbid": ["..."]}]
    """
    text = read_text(path)
    entries = []
    if path.lower().endswith(".json"):
        obj = json.loads(text)
        items = obj.items() if isinstance(obj, dict) else [(e["source"], e) for e in obj]
        for src, val in items:
            if isinstance(val, dict):
                targets, forbid = val.get("target", []), val.get("forbid", [])
            else:
                targets, forbid = val, []
            targets = _split_alts(targets) if isinstance(targets, str) else list(targets)
            forbid = _split_alts(forbid) if isinstance(forbid, str) else list(forbid)
            entries.append({"source": src, "targets": targets, "forbid": forbid})
        return entries
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for sep in ("\t", "=>", "->", ","):
            if sep in line:
                cols = [c.strip() for c in line.split(sep)]
                break
        else:
            continue
        if cols[0].lower() in ("source", "원어") and len(entries) == 0:
            continue
        entries.append({"source": cols[0], "targets": _split_alts(cols[1] if len(cols) > 1 else ""),
                        "forbid": _split_alts(cols[2] if len(cols) > 2 else "")})
    return entries


def glossary_check(source, target, entries):
    issues, applicable = [], 0
    for e in entries:
        if not e["source"] or not _term_in(source, e["source"]):
            continue
        applicable += 1
        n_src = _term_count(source, e["source"])
        if e["targets"] and not any(_term_in(target, t) for t in e["targets"]):
            issues.append({"term": e["source"], "kind": "missing_target", "expected": e["targets"],
                           "source_occurrences": n_src})
        elif (re.search(r"[A-Za-z]", e["source"]) and e["source"].lower() not in
              [t.lower() for t in e["targets"]] and _term_in(target, e["source"])):
            issues.append({"term": e["source"], "kind": "untranslated_source_term", "expected": e["targets"],
                           "source_occurrences": n_src})
        for bad in e["forbid"]:
            if _term_in(target, bad):
                issues.append({"term": e["source"], "kind": "forbidden_variant", "found": bad,
                               "expected": e["targets"], "source_occurrences": n_src})
    return {"entries_total": len(entries), "applicable": applicable, "issues": issues}


def audit_data(source, target, direction="auto", literary=False, glossary=None):
    if direction == "auto":
        direction = "en-to-ko" if re.search(r"[A-Za-z]", source) and re.search(r"[가-힣]", target) else "same"

    source_locks = shared_locks(source)
    target_locks = shared_locks(target)
    missing_all = _missing_counts(source_locks, target_locks)
    extra_all = _extra_counts(source_locks, target_locks)
    missing = [m for m in missing_all if m["kind"] != "placeholder"]
    extra = [m for m in extra_all if m["kind"] != "placeholder"]
    ph_missing = [m for m in missing_all if m["kind"] == "placeholder"]
    ph_extra = [m for m in extra_all if m["kind"] == "placeholder"]
    source_structure = structure_data(source)
    target_structure = structure_data(target)
    structure_warnings = []
    for key in ("headings", "bullet_items", "table_rows", "code_blocks", "links"):
        if source_structure[key] != target_structure[key]:
            structure_warnings.append({"kind": key, "source": source_structure[key], "target": target_structure[key]})

    risks = []
    target_pronouns = len(KOREAN_PRONOUNS.findall(target))
    source_pronouns = len(KOREAN_PRONOUNS.findall(source))
    if direction == "en-to-ko" and target_pronouns >= 2 and target_pronouns > source_pronouns + 1:
        risks.append(_risk(
            "FID-1", "warn", "주체 복원 과다", target_pronouns,
            "한국어의 영형 주어로 생략할 수 있는 대명사가 새로 들어갔는지, 화자·시점이 바뀌지 않았는지 확인",
            severity="major" if literary else "minor", mqm="Accuracy/Addition", count=target_pronouns - source_pronouns,
        ))

    target_intensifiers = len(KOREAN_INTENSIFIERS.findall(target))
    if direction == "en-to-ko" and target_intensifiers >= 2:
        risks.append(_risk(
            "LIT-3", "warn", "강도 부사 삽입 후보", target_intensifiers,
            "원문에 없는 감정·강도·평가를 부사로 보강하지 않았는지 확인",
            severity="major", mqm="Accuracy/Addition", count=target_intensifiers,
        ))

    translationese = len(TRANSLATIONESE_RE.findall(target)) if direction in ("en-to-ko", "same") else 0
    if translationese:
        risks.append(_risk(
            "FID-7", "warn", "한국어 번역투 후보", translationese,
            "A-1~A-19 span을 확인하되, 인용·전문 문맥의 합법적 표현은 보존",
            severity="minor", mqm="Fluency/Awkward", count=translationese,
        ))

    source_s = source_structure["sentences"]
    target_s = target_structure["sentences"]
    ratio = target_s / max(source_s, 1)
    if source_s and (ratio < 0.55 or ratio > 1.75):
        risks.append(_risk(
            "FID-2", "warn", "문장 분할·통합 편차", round(ratio, 2),
            "문장 수가 달라진 이유가 리듬 조정인지, 누락·중복인지 원문과 대조",
            severity="minor", mqm="Accuracy/Omission-Addition",
        ))

    alignment = paragraph_alignment(source, target)
    sp_n, tp_n = alignment["source_paragraphs"], alignment["target_paragraphs"]
    if sp_n >= 3 and sp_n != tp_n:
        gap = abs(sp_n - tp_n)
        risks.append(_risk(
            "FID-8", "warn", "문단 수 불일치", {"source": sp_n, "target": tp_n},
            "문단이 통째로 빠졌거나 합쳐졌는지 문단 대응표로 확인",
            severity="major" if gap >= max(2, sp_n // 5) else "minor",
            mqm="Accuracy/Omission-Addition", count=gap,
        ))
    for o in alignment["outliers"]:
        omission = o["kind"] == "omission_suspect"
        risks.append(_risk(
            "FID-8", "warn", "문단 누락 후보" if omission else "문단 추가 후보",
            {"paragraph": o["paragraph"], "relative_length": o["relative_length"],
             "source": o["source_excerpt"], "target": o["target_excerpt"]},
            "해당 문단을 원문과 나란히 읽고 빠진 문장·덧붙인 설명이 없는지 확인",
            severity="major", mqm="Accuracy/Omission" if omission else "Accuracy/Addition",
        ))

    allowed_terms = []
    glossary_report = None
    if glossary:
        for e in glossary:
            allowed_terms.extend(e["targets"] + [e["source"]])
        glossary_report = glossary_check(source, target, glossary)
        for issue in glossary_report["issues"]:
            if issue["kind"] == "forbidden_variant":
                label, act = "금지 역어 사용", f"'{issue['found']}' 대신 {issue['expected'] or '지정 역어'} 사용"
            elif issue["kind"] == "untranslated_source_term":
                label, act = "용어 미번역", f"원어 '{issue['term']}'가 그대로 남음 → {issue['expected']} 확인"
            else:
                label, act = "용어집 역어 누락", f"'{issue['term']}'의 지정 역어 {issue['expected']}가 번역문에 없음"
            risks.append(_risk(
                "TERM-1" if issue["kind"] != "forbidden_variant" else "TERM-2", "warn", label,
                issue["term"], act + " (모호하면 괄호로 원어 병기)",
                severity="major", mqm="Terminology/Inconsistent", count=issue["source_occurrences"],
            ))

    residue = []
    if direction == "en-to-ko":
        residue = english_residue(target, allowed_terms)
        if residue:
            long_run = any(len(r.split()) >= 6 for r in residue)
            risks.append(_risk(
                "FID-9", "warn", "영어 구절 잔류 후보", residue[:5],
                "번역되지 않고 남은 영어 구절인지, 의도적 병기·고유명사인지 확인",
                severity="major" if long_run else "minor", mqm="Accuracy/Untranslated", count=len(residue),
            ))

    if ph_missing or ph_extra:
        risks.append(_risk(
            "FID-10", "hold", "자리표시자·태그 손상",
            {"missing": ph_missing, "extra": ph_extra},
            "{name}, %s, {{x}}, <b> 같은 자리표시자와 태그는 번역하거나 지우지 말고 원문과 같은 개수로 복구",
            severity="critical", mqm="Accuracy/Mistranslation(markup)",
            count=sum(m["count"] for m in ph_missing + ph_extra),
        ))
    if missing:
        risks.append(_risk(
            "FID-6", "hold", "표면 잠금 누락", len(missing),
            "숫자·URL·코드·약어·링크 대상은 번역문을 채택하기 전에 복구",
            severity="critical", mqm="Accuracy/Mistranslation(surface)", count=sum(m["count"] for m in missing),
        ))
    if structure_warnings:
        risks.append(_risk(
            "FID-5", "hold", "문서 구조 변화", structure_warnings,
            "제목·불릿·표·코드·링크 개수가 의도적으로 바뀐 것인지 확인",
            severity="major", mqm="Design/Markup", count=len(structure_warnings),
        ))

    literary_profile = None
    if literary:
        literary_profile = {
            "baseline": "Deborah Smith contrastive baseline — 모방 지시가 아님",
            "preserve": [
                "모호성·반복·생략이 의미를 만드는지 먼저 확인",
                "감각 이미지와 장면의 정조(atmosphere/tone) 보존",
                "화자의 초점화·거리·문장 리듬 보존",
                "번역자의 독자 친화적 재구성은 허용하되 사실·사건·단서는 삭제하지 않음",
            ],
            "guard": [
                "원문에 없는 주어·감정·강도 부사·설명 추가 금지",
                "모호한 비유를 임의의 구체 사물로 확정하지 않음",
                "반복을 자동으로 동의어로 바꾸지 않음",
                "영어권 문체·영국식 어휘를 한국어 윤문 기준으로 이식하지 않음",
                "LLM 심사·자동 지표 점수를 문학 번역의 합격 근거로 쓰지 않음(EAMT 2026)",
            ],
        }
        risks.append(_risk(
            "LIT-1", "review", "문학적 충실성 사람 검토", "모호성·반복·정조·초점화",
            "문장 단위가 아니라 장면·문단 단위로 원문과 번역문을 함께 읽고 확인",
            severity="review", mqm="Style/Literary",
        ))

    risks.sort(key=lambda r: (SEVERITY_RANK[r["severity"]], -r["count"], r["id"]))
    fix_order = []
    for r in risks:
        if r["severity"] != "review" and r["id"] not in fix_order:
            fix_order.append(r["id"])

    penalty = sum(MQM_WEIGHT[r["severity"]] * min(r["count"], 10) for r in risks)
    by_severity = Counter(r["severity"] for r in risks)
    status = "hold" if any(r["level"] == "hold" for r in risks) else ("warn" if risks else "pass")
    return {
        "tool_version": VERSION,
        "direction": direction,
        "source_chars": len(source),
        "target_chars": len(target),
        "surface_lock": {
            "pass": not missing,
            "missing": missing,
            "extra": extra,
        },
        "placeholders": {"pass": not (ph_missing or ph_extra), "missing": ph_missing, "extra": ph_extra},
        "structure": {
            "pass": not structure_warnings,
            "source": source_structure,
            "target": target_structure,
            "warnings": structure_warnings,
        },
        "paragraph_alignment": alignment,
        "english_residue": residue,
        "glossary": glossary_report,
        "translationese_signals": translationese,
        "risks": risks,
        "severity_summary": {k: by_severity.get(k, 0) for k in ("critical", "major", "minor", "review")},
        "fix_order": fix_order,
        "mqm_heuristic": {
            "penalty": penalty,
            "per_1000_chars": round(penalty / max(len(target), 1) * 1000, 1),
            "note": "참고용 휴리스틱(치명 25·주요 5·경미 1). 사람이 하는 MQM 평가의 대체물이 아님",
        },
        "literary_profile": literary_profile,
        "human_review_required": True,
        "status": status,
    }


def _apply_strict(data):
    """--strict: 치명·주요 위험이 하나라도 있으면 hold로 올린다."""
    if data["severity_summary"]["critical"] or data["severity_summary"]["major"]:
        data["status"] = "hold"
    return data


def _print_report(data):
    print(f"번역 충실성 감사: {data['status'].upper()}  방향={data['direction']}")
    lock = data["surface_lock"]
    print(f"표면 잠금: {'통과' if lock['pass'] else '실패'}  누락 {len(lock['missing'])}건 / 추가 토큰 {len(lock['extra'])}건")
    print(f"자리표시자·태그: {'통과' if data['placeholders']['pass'] else '손상'}")
    structure = data["structure"]
    print(f"구조 대조: {'통과' if structure['pass'] else '확인 필요'}")
    gl = data["glossary"]
    if gl is not None:
        print(f"용어집: 적용 {gl['applicable']}/{gl['entries_total']}항목, 문제 {len(gl['issues'])}건")
    sev = data["severity_summary"]
    print(f"심각도: 치명 {sev['critical']} · 주요 {sev['major']} · 경미 {sev['minor']} · 사람검토 {sev['review']}"
          f"  (MQM 휴리스틱 {data['mqm_heuristic']['penalty']}점, 1000자당 {data['mqm_heuristic']['per_1000_chars']})")
    if data["fix_order"]:
        print("고칠 순서: " + " → ".join(data["fix_order"]))
    for risk in data["risks"]:
        print(f"  [{risk['severity']}/{risk['level']}] {risk['id']} {risk['label']}: {risk['evidence']}")
        print(f"      → {risk['action']}")
    print("사람 검토: 의미·누락·추가·주체·부정·조건·문학적 정조를 원문과 대조할 것")


def main(args=None):
    argv = list(sys.argv[1:] if args is None else args)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("source", nargs="?")
    parser.add_argument("target", nargs="?")
    parser.add_argument("--direction", default="auto", choices=["auto", "en-to-ko", "ko-to-en", "same"])
    parser.add_argument("--glossary")
    parser.add_argument("--literary", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.error = lambda msg: (_ for _ in ()).throw(ValueError(msg))
    try:
        ns = parser.parse_args(argv)
    except ValueError as exc:
        print(f"인자 오류: {exc}", file=sys.stderr)
        return 3
    except SystemExit:
        return 3
    if not ns.source or not ns.target:
        print(__doc__)
        return 3
    try:
        source, target = read_text(ns.source), read_text(ns.target)
        glossary = load_glossary(ns.glossary) if ns.glossary else None
    except (OSError, ValueError, KeyError) as exc:
        print(f"입력 읽기 실패: {exc}", file=sys.stderr)
        return 3
    data = audit_data(source, target, ns.direction, ns.literary, glossary)
    if ns.strict:
        data = _apply_strict(data)
    if ns.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
    else:
        _print_report(data)
    return {"pass": 0, "warn": 1, "hold": 2}[data["status"]]


if __name__ == "__main__":
    sys.exit(main())
