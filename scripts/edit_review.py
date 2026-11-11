"""Proposal-and-approval editing helpers. No network or model calls.

Two commands share this module:

* ``review-signals``: review candidates that the general diagnosis does not
  report (unmeasured quantity claims, a first-person text that names its own
  author in the third person, repeated sentence openings, and mixed endings
  that include the casual 어체 used on Threads).
* ``apply-edits``: replace only the approved sentences, exactly as shown to
  the author, in a copy of the manuscript. Nothing is written unless every
  replacement is unambiguous.

Signals are review candidates, not defects. A pass is not a proof of meaning.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

VERSION = "1.0.0"
NOTE = "기계 검사에서 찾은 후보입니다. 위반 판정은 문맥을 읽고 사람이 합니다."
LONG_SENTENCE = 90
VOLUME_LIMIT = 1.2

# Text that must not be rewritten: code, inline code, and direct quotations.
_LOCKED = re.compile(
    r"\x60{3}.*?\x60{3}|~~~.*?~~~|\x60[^\x60\n]*\x60|“[^”]*”|「[^」]*」|『[^』]*』|\"[^\"\n]*\"",
    re.S)
_FRONT = re.compile(r"\A\ufeff?---[ \t]*\n.*?\n---[ \t]*(?:\n|\Z)", re.S)
_BOUNDARY = re.compile(r"(?<=[.!?。！？…])\s+|\n+")
_NUMBER = re.compile(
    r"\d[\d,.]*\s*(?:%|퍼센트|배|명|개|년|월|일|시간|분|초|원|만|억|권|편|회|쪽|장|자|위|건|차시|기|주|살)?")
_QUANTIFIERS = ("대부분", "대다수", "모두", "전부", "항상", "언제나", "누구나", "아무도",
                "하루 종일", "절반", "거의")
_ALWAYS = re.compile(r"(?<![가-힣])늘(?![가-힣])")
_FIRST_PERSON = re.compile(
    r"(?<![가-힣])(?:저는|제가|저도|나는|내가|나도|우리는|우리가)(?![가-힣])")
_THIRD_SELF = ("작가는", "작가가", "저자는", "저자가", "필자는", "필자가", "사용자는", "사용자가")
_FORMAL = re.compile(r"(?:습니다|입니다|습니까|니다|니까|십시오)$")
_POLITE = re.compile(r"[가-힣](?:요|죠)$")
_PLAIN = re.compile(r"[가-힣]다$")
_CASUAL = re.compile(
    r"(?:거든|잖아|더라|더라고|는데|았어|었어|했어|같아|있어|없어|이야|야|어|아|지|네|군|걸|래|해|봐|줘|돼)$")
_RUN = ("합니다체", "해요체", "다체", "어체")


def normalized(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def strip_front(text):
    return _FRONT.sub("", normalized(text), count=1)


def mask_locked(text):
    """Blank locked fragments while keeping offsets and newlines."""
    return _LOCKED.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), text)


def paragraphs(text):
    """Paragraphs after front matter, split at blank lines. Headings are kept."""
    return [p.strip() for p in re.split(r"\n\s*\n", strip_front(text).strip()) if p.strip()]


def _body_units(text):
    """(paragraph index, text) for prose paragraphs; headings, tables, lists, quotes skipped."""
    out = []
    # Mask first: a code fence can contain blank lines that would split it apart.
    # Paragraph numbering must stay the same as paragraphs(), so empty ones are kept.
    masked = mask_locked(strip_front(text).strip())
    for index, para in enumerate(re.split(r"\n\s*\n", masked)):
        lines = [ln for ln in para.splitlines()
                 if not re.match(r"^\s*(#|>|\||[-*]\s|\d+\.\s|!\[)", ln)]
        body = " ".join(ln.strip() for ln in lines).strip()
        if body:
            out.append((index, body))
    return out


def _sentences(par):
    return [s.strip() for s in _BOUNDARY.split(par) if len(s.strip()) >= 2]


def register(sentence):
    tail = re.sub(r"[\s.!?。！？…\"'”’)\]」』]+$", "", sentence)
    if not tail:
        return None
    if _FORMAL.search(tail):
        return "합니다체"
    if _POLITE.search(tail):
        return "해요체"
    if _PLAIN.search(tail):
        return "다체"
    if _CASUAL.search(tail):
        return "어체"
    return None


def classified_sentences(text):
    """(sentence, register or None) for prose in ``text``; quotes and code are masked first."""
    return [(s, register(s)) for s in _sentences(mask_locked(normalized(text)))]


def _item(code, message, location, quote, action="review"):
    return {"code": code, "basis": "heuristic-candidate", "action": action,
            "message": message, "paragraph": location, "quote": quote[:60]}


def signals_data(text):
    units = _body_units(text)
    findings = []
    all_body = " ".join(body for _, body in units)

    for index, body in units:
        for sentence in _sentences(body):
            hit = [q for q in _QUANTIFIERS if q in sentence]
            if _ALWAYS.search(sentence):
                hit.append("늘")
            if hit and not _NUMBER.search(sentence):
                findings.append(_item(
                    "SIG-1", "숫자 없이 양·빈도를 단정했습니다(" + "·".join(hit)
                    + "). 잰 값이면 숫자를 쓰고, 아니면 범위를 좁히거나 저자에게 확인합니다.",
                    index, sentence))

    if len(_FIRST_PERSON.findall(all_body)) >= 2:
        for index, body in units:
            for sentence in _sentences(body):
                hit = [w for w in _THIRD_SELF if w in sentence]
                if hit:
                    findings.append(_item(
                        "SIG-2", "1인칭 글에서 저자를 남처럼 부른 곳일 수 있습니다(" + "·".join(hit)
                        + "). 글이 다루는 대상이면 그대로 둡니다.", index, sentence))

    flat = [(index, s) for index, body in units for s in _sentences(body)]
    for i in range(len(flat) - 2):
        opens = {flat[k][1].split()[0] for k in range(i, i + 3) if flat[k][1].split()}
        if len(opens) == 1 and flat[i][1].split():
            findings.append(_item("SIG-3", "같은 말로 시작하는 문장이 3연속입니다("
                                  + next(iter(opens)) + ").", flat[i][0], flat[i][1]))
    first_words = [(index, body.split()[0]) for index, body in units if body.split()]
    for i in range(len(first_words) - 1):
        if first_words[i][1] == first_words[i + 1][1]:
            findings.append(_item("SIG-3", "연속한 두 문단이 같은 말로 시작합니다("
                                  + first_words[i][1] + ").", first_words[i + 1][0],
                                  first_words[i + 1][1]))
    for i in range(len(flat) - 2):
        a, b, c = (len(flat[k][1]) for k in range(i, i + 3))
        if flat[i][0] == flat[i + 2][0] and max(a, b, c) - min(a, b, c) <= 3 and min(a, b, c) >= 8:
            findings.append(_item("SIG-3", f"길이가 비슷한 문장이 3연속입니다({a}·{b}·{c}자).",
                                  flat[i][0], flat[i][1]))

    counts = Counter()
    per_par = {}
    for index, body in units:
        local = Counter()
        for sentence in _sentences(body):
            kind = register(sentence)
            if kind:
                local[kind] += 1
                counts[kind] += 1
        if local:
            per_par[index] = local
    dominant = counts.most_common(1)[0][0] if counts else None
    if dominant:
        for index, local in per_par.items():
            others = [f"{kind} {local[kind]}" for kind in _RUN
                      if kind != dominant and local.get(kind, 0) >= max(local.get(dominant, 0), 1)]
            if others:
                findings.append(_item(
                    "SIG-4", f"주 종결({dominant})과 다른 종결이 문단 안에서 같거나 더 많습니다("
                    + ", ".join(others) + ").", index, ""))

    return {"version": VERSION, "note": NOTE,
            "register": {"counts": dict(counts), "dominant": dominant,
                         "classified_sentences": sum(counts.values())},
            "sentences": len(flat), "findings": findings}


def _locked_spans(text):
    return [(m.start(), m.end()) for m in _LOCKED.finditer(text)]


def _numbers(text):
    return Counter(x.strip() for x in _NUMBER.findall(strip_front(text)))


def apply_data(pairs, source, allow_locked=False):
    """Return (new_text, rows, errors). The text is None unless every pair is valid."""
    errors, rows, spans = [], [], []
    text = normalized(source)
    locked = _locked_spans(text)
    for number, pair in enumerate(pairs, 1):
        label = str(pair.get("id") or f"치환 {number}")
        old, new = pair.get("old"), pair.get("new")
        if not isinstance(old, str) or not isinstance(new, str) or not old:
            errors.append(f"{label}: old와 new는 비어 있지 않은 문자열이어야 합니다")
            continue
        normalized_old = normalized(old)
        if normalized_old == normalized(new):
            errors.append(f"{label}: 수정 전·후가 같습니다")
            continue
        count = text.count(normalized_old)
        if count != 1:
            errors.append(f"{label}: 원문에 {count}회 나옵니다. 정확히 1회여야 합니다")
            continue
        start = text.index(normalized_old)
        end = start + len(normalized_old)
        if not allow_locked and any(start < b and a < end for a, b in locked):
            errors.append(f"{label}: 인용·코드 같은 보호 구간과 겹칩니다")
            continue
        spans.append((start, end, label, normalized(new)))
        rows.append({"id": label, "status": "원문 1회 확인", "start": start, "end": end})
    ordered = sorted(spans)
    for (s1, e1, l1, _), (s2, e2, l2, _) in zip(ordered, ordered[1:]):
        if s2 < e1:
            errors.append(f"{l1}·{l2}: 바꿀 구간이 겹칩니다. 한 쌍으로 합칩니다")
    if errors:
        return None, rows, errors
    out = text
    for start, end, _, new in sorted(spans, reverse=True):
        out = out[:start] + new + out[end:]
    return out, rows, []


def compare_data(before, after):
    pa, pb = paragraphs(before), paragraphs(after)
    la, lb = sum(map(len, pa)), sum(map(len, pb))
    ratio = round(lb / la, 3) if la else 0
    changed = sum(1 for x, y in zip(pa, pb) if x != y) + abs(len(pa) - len(pb))
    na, nb = _numbers(before), _numbers(after)
    old_sentences = {s for _, body in _body_units(before) for s in _sentences(body)}
    new_long = [s[:30] for _, body in _body_units(after) for s in _sentences(body)
                if len(s) >= LONG_SENTENCE and s not in old_sentences]
    return {"paragraphs": [len(pa), len(pb)], "changed_paragraphs": changed,
            "chars": [la, lb], "volume_ratio": ratio, "volume_exceeded": ratio > VOLUME_LIMIT,
            "numbers_lost": dict(na - nb), "numbers_new": dict(nb - na),
            "new_long_sentences": new_long}


def _load_pairs(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"치환 파일을 읽지 못했습니다: {error}")
    if not isinstance(data, list) or not data:
        raise SystemExit('치환 파일은 [{"id": ..., "old": ..., "new": ...}] 목록이어야 합니다')
    return data


def signals_main(argv=None):
    parser = argparse.ArgumentParser(prog="review-signals", description=signals_main.__doc__)
    parser.add_argument("manuscript")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = signals_data(Path(args.manuscript).read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        reg = result["register"]
        print(f"문장 {result['sentences']}개 · 종결 {reg['counts'] or '분류 없음'}"
              f" · 주 종결 {reg['dominant'] or '-'}")
        if not result["findings"]:
            print("검토 후보 없음")
        for item in result["findings"]:
            where = f"[{item['paragraph']}]" if item["paragraph"] is not None else ""
            quote = f' "{item["quote"]}"' if item["quote"] else ""
            print(f"{item['code']} {where} {item['message']}{quote}")
        print(NOTE)
    return 0


def apply_main(argv=None):
    parser = argparse.ArgumentParser(prog="apply-edits", description=apply_main.__doc__)
    parser.add_argument("pairs")
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--allow-locked", action="store_true",
                        help="인용·코드 구간 안의 치환을 허용합니다. 기본은 거절합니다")
    parser.add_argument("--overwrite", action="store_true", help="이미 있는 출력 파일을 덮어씁니다")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    source_path, out_path = Path(args.source), Path(args.output)
    if source_path.resolve() == out_path.resolve():
        print("원본과 반영본 경로가 같습니다. 원본은 덮어쓰지 않습니다.", file=sys.stderr)
        return 1
    if out_path.exists() and not args.overwrite:
        print(f"{out_path} 파일이 이미 있습니다. 덮어쓰려면 --overwrite를 붙입니다.", file=sys.stderr)
        return 1
    source = source_path.read_text(encoding="utf-8")
    result, rows, errors = apply_data(_load_pairs(args.pairs), source, args.allow_locked)
    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        print("치환하지 않았습니다. 파일을 쓰지 않았습니다.", file=sys.stderr)
        return 1
    out_path.write_text(result, encoding="utf-8")
    report = compare_data(source, result)
    flagged = bool(report["volume_exceeded"] or report["numbers_lost"] or report["numbers_new"]
                   or report["new_long_sentences"])
    summary = {"status": "applied_with_flags" if flagged else "applied", "applied": len(rows),
               "output": str(out_path), "report": report, "note": NOTE}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(f"{row['id']}: {row['status']}")
        print(f"치환 {len(rows)}건 → {out_path}")
        print(f"분량 {report['chars'][0]} → {report['chars'][1]}자 ({report['volume_ratio'] * 100:.1f}%)"
              + (" 120% 초과: 먼저 작가 확인" if report["volume_exceeded"] else ""))
        print(f"바뀐 문단 {report['changed_paragraphs']}")
        if report["numbers_lost"] or report["numbers_new"]:
            print(f"숫자 변화: 빠짐 {report['numbers_lost'] or '-'} / 새로 생김 {report['numbers_new'] or '-'}"
                  " — 승인한 수정으로 설명되지 않으면 되돌립니다")
        else:
            print("숫자 보존: 일치")
        if report["new_long_sentences"]:
            print(f"{LONG_SENTENCE}자 이상 문장이 새로 생겼습니다: {report['new_long_sentences']}"
                  " — 남기는 이유를 적습니다")
        print("다음: preserve와 verify_gates로 원문 대조를 이어갑니다.")
    return 0


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    raise SystemExit({"review-signals": signals_main, "apply-edits": apply_main}
                     .get(command, lambda _: print(__doc__) or 2)(sys.argv[2:]))
