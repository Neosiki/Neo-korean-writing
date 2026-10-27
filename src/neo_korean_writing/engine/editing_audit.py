"""Evidence-bound Korean editing checks. No network or model calls.

Signals are review candidates, not a proof of semantic equivalence.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import sys

VERSION = "1.0.0"
NOTE = "기계 검사에서 찾은 후보입니다. 통과는 의미 정확성 인증이 아닙니다."
_PROTECTED = re.compile(
    r"\A---[ \t]*\n.*?\n---[ \t]*(?:\n|\Z)|\x60{3}.*?\x60{3}|~~~.*?~~~|"
    r"\x60[^\x60\n]*\x60|(?m:^[ \t]*>[^\n]*$)|"
    r"(?m:^[ \t]*#{1,6}[ \t]+[^\n]*$)|(?m:^[ \t]*\|[^\n]*$)|"
    r'“[^”]*”|「[^」]*」|『[^』]*』|"[^"\n]*"', re.S)
_BOUNDARY = re.compile(r"(?<=[.!?。！？])\s+|\n+")
_BINDING = re.compile(
    r"(?P<entity>[A-Za-z가-힣][A-Za-z가-힣0-9·_-]{0,30})의\s*"
    r"(?P<metric>매출|지원금|가격|비용|예산|수익|인원|판매량|수량|교육시간)"
    r"(?:은|는|이|가|:|=)?\s*"
    r"(?P<number>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(?P<scale>억|만|천)?\s*"
    r"(?P<unit>원|명|개|건|회|시간|분|%|퍼센트)")
_NEGATION = re.compile(r"않|못|아니|없|금지|불가")
_TOKEN = re.compile(r"[가-힣]{2,}|[A-Za-z][A-Za-z0-9_-]+")


def normalized(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def text_hash(text):
    return hashlib.sha256(normalized(text).encode("utf-8")).hexdigest()


def prose(text):
    """Mask protected text without moving offsets; its fidelity is checked elsewhere."""
    return _PROTECTED.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), text)


def sentences(text):
    start = 0
    for end in [m.start() for m in _BOUNDARY.finditer(text)] + [len(text)]:
        chunk = text[start:end]
        value = chunk.strip()
        if value:
            pos = start + len(chunk) - len(chunk.lstrip())
            yield {"text": value, "start": pos, "end": pos + len(value)}
        # Boundaries contain only whitespace, so trimming on the next pass is safe.
        start = end


def location(text, start, end):
    return {"start": start, "end": end, "line": text.count("\n", 0, start) + 1}


def register_profile(text):
    counts = Counter()
    samples = []
    for row in sentences(prose(text)):
        tail = row["text"].rstrip(".!?。！？… \t")
        if re.search(r"(?:습니다|입니다|습니까|니다|십시오)$", tail):
            kind = "합쇼체"
        elif tail.endswith("요"):
            kind = "해요체"
        elif re.search(r"(?:음|함|됨|임)$", tail):
            kind = "음슴체"
        elif tail.endswith("다"):
            kind = "한다체"
        else:
            continue
        counts[kind] += 1
        samples.append({"register": kind, "text": text[row["start"]:row["end"]],
                        "location": location(text, row["start"], row["end"])})
    total = sum(counts.values())
    dominant, share = None, 0.0
    if total:
        dominant, count = counts.most_common(1)[0]
        share = count / total
    confident = total >= 3 and share >= 0.8
    return {"counts": dict(counts), "classified_sentences": total,
            "dominant": dominant, "share": round(share, 3),
            "samples": [x for x in samples if x["register"] == dominant][:3],
            "status": "confident" if confident else "insufficient_or_mixed"}


def _finding(code, message, before, after, bspan=None, aspan=None, hold=False):
    item = {"code": code, "basis": "heuristic-candidate", "state": "검토 후보",
            "action": "hold_for_review" if hold else "review",
            "message": message, "before_quote": before, "after_quote": after}
    if bspan is not None:
        item["before_location"] = bspan
    if aspan is not None:
        item["after_location"] = aspan
    return item


def _bindings(text):
    result = {}
    for match in _BINDING.finditer(prose(text)):
        scale = {"억": Decimal(10**8), "만": Decimal(10**4), "천": Decimal(1000)}
        value = Decimal(match["number"].replace(",", "")) * scale.get(match["scale"], 1)
        unit = "%" if match["unit"] == "퍼센트" else match["unit"]
        key = (match["entity"], match["metric"])
        result.setdefault(key, []).append(
            {"value": str(value.normalize()), "unit": unit,
             "quote": text[match.start():match.end()],
             "location": location(text, match.start(), match.end())})
    return result


def review_signals(before, after):
    a, b = register_profile(before), register_profile(after)
    findings = []
    if a["status"] == b["status"] == "confident" and a["dominant"] != b["dominant"]:
        x, y = a["samples"][0], b["samples"][0]
        findings.append(_finding(
            "EDIT-REGISTER", f"우세 문체가 {a['dominant']}에서 {b['dominant']}로 바뀌었습니다. 의도한 변경인지 검토합니다.",
            x["text"], y["text"], x["location"], y["location"], hold=True))
    left, right = list(sentences(prose(before))), list(sentences(prose(after)))
    used_left, used_right = set(), set()
    pairs = []
    alignment = SequenceMatcher(None, [x["text"] for x in left], [y["text"] for y in right], autojunk=False)
    for tag, i0, i1, j0, j1 in alignment.get_opcodes():
        if tag == "equal":
            used_left.update(range(i0, i1))
            used_right.update(range(j0, j1))
        else:
            for j in range(j0, j1):
                center = i0 + min(j - j0, max(0, i1 - i0 - 1))
                for i in range(max(i0, center - 4), min(i1, center + 5)):
                    ratio = SequenceMatcher(None, left[i]["text"], right[j]["text"], autojunk=False).ratio()
                    pairs.append((ratio, i, j))
    pairs.sort(reverse=True)
    for ratio, i, j in pairs:
        if ratio < 0.65 or i in used_left or j in used_right:
            continue
        used_left.add(i)
        used_right.add(j)
        x, y = left[i], right[j]
        if len(_NEGATION.findall(x["text"])) != len(_NEGATION.findall(y["text"])):
            findings.append(_finding(
                "EDIT-NEGATION", "대응 후보 문장의 부정 표지가 달라졌습니다. 긍정·부정 관계를 실제로 대조합니다.",
                x["text"], y["text"], location(before, x["start"], x["end"]),
                location(after, y["start"], y["end"])))
    ba, bb = _bindings(before), _bindings(after)
    for key in sorted(ba.keys() & bb.keys()):
        old, new = ba[key], bb[key]
        if len(old) == len(new) == 1 and (old[0]["value"], old[0]["unit"]) != (new[0]["value"], new[0]["unit"]):
            findings.append(_finding(
                "EDIT-BINDING", f"{key[0]}의 {key[1]} 값·단위가 달라졌습니다. 귀속 관계를 확인합니다.",
                old[0]["quote"], new[0]["quote"], old[0]["location"], new[0]["location"]))
    known = set(_TOKEN.findall(prose(before)))
    new_terms = []
    for token in _TOKEN.finditer(prose(after)):
        if token.group() not in known:
            new_terms.append({"text": token.group(),
                              "location": location(after, token.start(), token.end())})
    for j, row in enumerate(right):
        if j in used_right:
            continue
        unknown = set(_TOKEN.findall(row["text"])) - known
        if len(unknown) >= 4:
            findings.append(_finding(
                "EDIT-CONTENT", "원문과 쉽게 대응되지 않는 문장입니다. 유의어 교체인지 새 주장인지 확인합니다.",
                "", row["text"], aspan=location(after, row["start"], row["end"])))
    return {"register": {"before": a, "after": b}, "findings": findings,
            "new_terms": new_terms[:40], "new_terms_truncated": len(new_terms) > 40,
            "note": NOTE}


def delivery_template(before, after):
    a, b = normalized(before), normalized(after)
    edits = []
    for tag, i, j, k, l in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != "equal":
            edits.append({"before_start": i, "before_end": j, "after_start": k, "after_end": l,
                          "before": a[i:j], "after": b[k:l], "reason": ""})
    return {"schema_version": 1, "original_sha256": text_hash(a),
            "final_sha256": text_hash(b), "edits": edits}


def delivery_review(before, after, report=None):
    if report is None:
        return {"status": "not_checked", "note": "최종 diff 기반 전달 기록을 연결하지 않았습니다."}
    if not isinstance(report, dict) or type(report.get("schema_version")) is not int or report["schema_version"] != 1:
        raise ValueError("전달 기록 schema_version 오류")
    for key in ("original_sha256", "final_sha256"):
        if not isinstance(report.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", report[key]):
            raise ValueError("전달 기록 해시 형식 오류: " + key)
    if report["original_sha256"] != text_hash(before) or report["final_sha256"] != text_hash(after):
        return {"status": "stale", "note": "원문 또는 최종본이 달라졌습니다. 기록을 다시 생성합니다."}
    edits = report.get("edits")
    if not isinstance(edits, list):
        raise ValueError("전달 기록 edits는 배열이어야 합니다")
    expected = delivery_template(before, after)["edits"]
    actual, reasons_missing = [], False
    for edit in edits:
        if not isinstance(edit, dict):
            raise ValueError("전달 기록 edit 형식 오류")
        item = {}
        for key in ("before_start", "before_end", "after_start", "after_end"):
            if type(edit.get(key)) is not int or edit[key] < 0:
                raise ValueError("전달 기록 위치 형식 오류: " + key)
            item[key] = edit[key]
        for key in ("before", "after", "reason"):
            if not isinstance(edit.get(key), str):
                raise ValueError("전달 기록 문자열 형식 오류: " + key)
            item[key] = edit[key]
        reasons_missing |= not item["reason"].strip()
        actual.append({k: v for k, v in item.items() if k != "reason"})
    canonical = [{k: v for k, v in e.items() if k != "reason"} for e in expected]
    if actual != canonical:
        return {"status": "mismatch", "note": "적용되지 않은 수정·빠진 수정·위치 불일치가 있습니다."}
    return {"status": "needs_reasons" if reasons_missing else "verified",
            "edit_count": len(edits),
            "note": "diff·해시·이유 존재를 확인했습니다. 이유의 진실성·내용 정확성을 인증하지 않습니다."}


def solar_record_review(before, after, record=None):
    if record is None:
        return {"status": "not_used"}
    allowed = {"schema_version", "original_sha256", "final_sha256", "provider", "model", "calls", "tokens"}
    if (not isinstance(record, dict) or set(record) != allowed
            or type(record.get("schema_version")) is not int or record["schema_version"] != 1):
        raise ValueError("Solar 기록 형식 오류. 키·헤더·원시 응답을 포함하지 않습니다")
    for key in ("provider", "model"):
        if not isinstance(record[key], str) or not record[key].strip() or len(record[key]) > 160:
            raise ValueError("Solar 기록 문자열 오류: " + key)
    for key in ("calls", "tokens"):
        if record[key] is not None and (type(record[key]) is not int or record[key] < 0):
            raise ValueError("Solar 호출·토큰은 음이 아닌 정수 또는 미확인 null입니다")
    for key in ("original_sha256", "final_sha256"):
        if not isinstance(record[key], str) or not re.fullmatch(r"[0-9a-f]{64}", record[key]):
            raise ValueError("Solar 기록 해시 형식 오류: " + key)
    if record["original_sha256"] != text_hash(before) or record["final_sha256"] != text_hash(after):
        return {"status": "stale", "note": "다른 원고 버전의 Solar 기록입니다"}
    return {"status": "recorded", **{k: record[k] for k in ("provider", "model", "calls", "tokens")},
            "note": "응답에서 기록한 수치이며 호출·청구 인증이 아닙니다. null은 미확인입니다."}


def audit_data(before, after, *, delivery=None, semantic_review=None, require_semantic=False, solar_record=None):
    if not before.strip() or not after.strip():
        raise ValueError("비어 있지 않은 원문과 최종본이 필요합니다")
    try:
        from . import korean_writing as writing
        from .translation_semantics import review_data
    except ImportError:
        import korean_writing as writing
        from translation_semantics import review_data
    preservation = writing.preserve_data(before, after)
    signals = preservation["editing_review"]
    rate = 1 - SequenceMatcher(None, before, after, autojunk=False).ratio()
    hard = (not preservation["surface_pass"] or not preservation["protected_pass"]
            or bool(preservation["residual_growth"]) or rate >= 0.5
            or any(f["action"] == "hold_for_review" for f in signals["findings"]))
    review = bool(preservation["meaning_warnings"] or signals["findings"]) or rate >= 0.3
    mechanical = "hold" if hard else "review" if review else "pass"
    notes = delivery_review(before, after, delivery)
    meaning = review_data(before, after, semantic_review)
    solar = solar_record_review(before, after, solar_record)
    hold = (hard or notes["status"] in ("stale", "mismatch")
            or meaning["status"] == "stale" or solar["status"] == "stale"
            or require_semantic and meaning["status"] not in ("reviewed_no_findings", "reviewed_with_findings"))
    review |= notes["status"] == "needs_reasons" or meaning["status"] == "reviewed_with_findings"
    status = "hold" if hold else "review" if review else "pass"
    return {"version": VERSION, "status": status, "mechanical_status": mechanical,
            "original_sha256": text_hash(before), "final_sha256": text_hash(after),
            "change_rate": round(rate, 4), "preservation": preservation,
            "delivery": notes, "semantic_review": meaning, "solar_usage": solar, "note": NOTE}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original")
    parser.add_argument("final")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--delivery")
    parser.add_argument("--delivery-template")
    parser.add_argument("--semantic-review")
    parser.add_argument("--solar-record")
    parser.add_argument("--require-semantic-review", action="store_true")
    args = parser.parse_args(argv)
    try:
        before, after = (Path(p).read_text(encoding="utf-8") for p in (args.original, args.final))
        delivery = json.loads(Path(args.delivery).read_text(encoding="utf-8")) if args.delivery else None
        semantic = json.loads(Path(args.semantic_review).read_text(encoding="utf-8")) if args.semantic_review else None
        solar = json.loads(Path(args.solar_record).read_text(encoding="utf-8")) if args.solar_record else None
        result = audit_data(before, after, delivery=delivery, semantic_review=semantic,
                            require_semantic=args.require_semantic_review, solar_record=solar)
        if args.delivery_template:
            with Path(args.delivery_template).open("x", encoding="utf-8") as stream:
                json.dump(delivery_template(before, after), stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"윤문 검토: {result['status']} / 기계 검사: {result['mechanical_status']}")
            for finding in result["preservation"]["editing_review"]["findings"]:
                print(f"- {finding['code']}: {finding['message']}")
            print(f"전달 기록: {result['delivery']['status']} / 의미 검토: {result['semantic_review']['status']}")
            print(NOTE)
        return {"pass": 0, "review": 1, "hold": 2}[result["status"]]
    except (OSError, ValueError, TypeError) as error:
        print("윤문 검토 입력 오류: " + str(error), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
