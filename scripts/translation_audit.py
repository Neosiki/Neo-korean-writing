#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""번역 후편집용 충실성·문체 위험 감사 도구 (표준 라이브러리만 사용).

이 도구는 번역 품질을 자동 판정하지 않는다. 공유 표면 토큰과 문서 구조를
기계적으로 대조하고, 한국어 번역에서 자주 생기는 위험을 사람 검토 목록으로
올린다. 문학 모드는 데보라 스미스를 모방하는 기능이 아니라, 독자 친화성·정조·
모호성·반복을 함께 검토하기 위한 대비 기준이다.

사용법:
  python3 translation_audit.py 원문.md 번역문.md
  python3 translation_audit.py 원문.md 번역문.md --direction en-to-ko --literary --json
"""
import json
import os
import re
import sys
from collections import Counter

VERSION = "7.0.0"
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


def _risk(id_, level, label, evidence, action):
    return {"id": id_, "level": level, "label": label, "evidence": evidence, "action": action}


def audit_data(source, target, direction="auto", literary=False):
    if direction == "auto":
        direction = "en-to-ko" if re.search(r"[A-Za-z]", source) and re.search(r"[가-힣]", target) else "same"

    source_locks = shared_locks(source)
    target_locks = shared_locks(target)
    missing = _missing_counts(source_locks, target_locks)
    extra = _extra_counts(source_locks, target_locks)
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
            "한국어의 영형 주어로 생략할 수 있는 대명사가 새로 들어갔는지, 화자·시점이 바뀌지 않았는지 확인"
        ))

    target_intensifiers = len(KOREAN_INTENSIFIERS.findall(target))
    if direction == "en-to-ko" and target_intensifiers >= 2:
        risks.append(_risk(
            "LIT-3", "warn", "강도 부사 삽입 후보", target_intensifiers,
            "원문에 없는 감정·강도·평가를 부사로 보강하지 않았는지 확인"
        ))

    translationese = len(TRANSLATIONESE_RE.findall(target)) if direction in ("en-to-ko", "same") else 0
    if translationese:
        risks.append(_risk(
            "FID-7", "warn", "한국어 번역투 후보", translationese,
            "A-1~A-19 span을 확인하되, 인용·전문 문맥의 합법적 표현은 보존"
        ))

    source_s = source_structure["sentences"]
    target_s = target_structure["sentences"]
    ratio = target_s / max(source_s, 1)
    if source_s and (ratio < 0.55 or ratio > 1.75):
        risks.append(_risk(
            "FID-2", "warn", "문장 분할·통합 편차", round(ratio, 2),
            "문장 수가 달라진 이유가 리듬 조정인지, 누락·중복인지 원문과 대조"
        ))

    if missing:
        risks.append(_risk(
            "FID-6", "hold", "표면 잠금 누락", len(missing),
            "숫자·URL·코드·약어·링크 대상은 번역문을 채택하기 전에 복구"
        ))
    if structure_warnings:
        risks.append(_risk(
            "FID-5", "hold", "문서 구조 변화", structure_warnings,
            "제목·불릿·표·코드·링크 개수가 의도적으로 바뀐 것인지 확인"
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
            ],
        }
        risks.append(_risk(
            "LIT-1", "review", "문학적 충실성 사람 검토", "모호성·반복·정조·초점화",
            "문장 단위가 아니라 장면·문단 단위로 원문과 번역문을 함께 읽고 확인"
        ))

    status = "hold" if missing or structure_warnings else ("warn" if risks else "pass")
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
        "structure": {
            "pass": not structure_warnings,
            "source": source_structure,
            "target": target_structure,
            "warnings": structure_warnings,
        },
        "translationese_signals": translationese,
        "risks": risks,
        "literary_profile": literary_profile,
        "human_review_required": True,
        "status": status,
    }


def _print_report(data):
    print(f"번역 충실성 감사: {data['status'].upper()}  방향={data['direction']}")
    lock = data["surface_lock"]
    print(f"표면 잠금: {'통과' if lock['pass'] else '실패'}  누락 {len(lock['missing'])}건 / 추가 토큰 {len(lock['extra'])}건")
    structure = data["structure"]
    print(f"구조 대조: {'통과' if structure['pass'] else '확인 필요'}")
    for risk in data["risks"]:
        print(f"  [{risk['level']}] {risk['id']} {risk['label']}: {risk['evidence']}")
        print(f"      → {risk['action']}")
    print("사람 검토: 의미·누락·추가·주체·부정·조건·문학적 정조를 원문과 대조할 것")


def main(args=None):
    args = list(sys.argv[1:] if args is None else args)
    positional = [a for a in args if not a.startswith("--") and a not in {
        "auto", "en-to-ko", "ko-to-en", "same"
    }]
    if len(positional) < 2:
        print(__doc__)
        return 3
    direction = "auto"
    if "--direction" in args:
        i = args.index("--direction")
        if i + 1 >= len(args):
            print("--direction 값이 없습니다", file=sys.stderr)
            return 3
        direction = args[i + 1]
    if direction not in {"auto", "en-to-ko", "ko-to-en", "same"}:
        print("direction은 auto|en-to-ko|ko-to-en|same 중 하나여야 합니다", file=sys.stderr)
        return 3
    try:
        source, target = read_text(positional[0]), read_text(positional[1])
    except OSError as exc:
        print(f"입력 읽기 실패: {exc}", file=sys.stderr)
        return 3
    data = audit_data(source, target, direction, "--literary" in args)
    if "--json" in args:
        print(json.dumps(data, ensure_ascii=False, indent=1))
    else:
        _print_report(data)
    return {"pass": 0, "warn": 1, "hold": 2}[data["status"]]


if __name__ == "__main__":
    sys.exit(main())
