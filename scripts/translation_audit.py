#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""번역 후편집용 충실성·문체 위험 감사 도구 (표준 라이브러리 + 내장 MIT ICU 파서).

이 도구는 번역 품질을 자동 판정하지 않는다. 공유 표면 토큰과 문서 구조를
기계적으로 대조하고, 한국어 번역에서 자주 생기는 위험을 사람 검토 목록으로
올린다. 문학 모드는 데보라 스미스를 모방하는 기능이 아니라, 독자 친화성·정조·
모호성·반복을 함께 검토하기 위한 대비 기준이다.

v8 고도화(2026-10): MQM식 심각도 등급(치명·주요·경미)과 고칠 순서, 용어집 일관성
검사(--glossary), 문단 단위 누락·추가 후보, 한국어 번역문의 영어 잔류, 자리표시자
({name}, %s, {{x}}, <b>) 손상 검사를 추가했다. 모든 등급은 사람이 MQM으로 평가하기
전에 훑어보는 휴리스틱이며 번역 품질 점수가 아니다.

v9 고도화(2026-10): 번역투를 유형(T1~T7·P1~P4·J1)별로 세고 빈도에 따라 경미/주요로 나누며,
같은 문단에 몰린 군집(hot 문단)과 영어·일본어 원천형 힌트를 보고한다. 서술 어체 혼용(FID-11),
목록 마침표 불일치(FID-12), 원문에 없는 완충 표현 증가(FID-13)를 추가했고, --baseline으로
초벌 번역 대비 후편집 범위(가벼움·보통·많음)와 과편집 경고(EDIT-1·EDIT-2)를 낸다.
유형별 보고 시작 횟수는 정상 한국어에도 흔한 표현(1~2회)을 위험으로 올리지 않기 위한 값이다.

v9.1 보강(2026-10): 용어집에 권장어·허용 변형·고정 모드(strict)·사용 문맥을 두어 타당한
약칭·동의 표현을 오류로 몰지 않고, 고정 용어만 혼용을 경고한다(TERM-3). --baseline에서는
초벌 대비 어체·높임말 변화(EDIT-3), 후편집으로 새로 생긴 번역투(EDIT-4), 사라진 번역투와
새 표면 잠금 누락을 `baseline_delta`로 따로 보고한다. 모든 위험에 `basis`(기계 점검/휴리스틱
후보/사람 검토)와 `state`(검토 후보)를 붙여, 기계적 차단(critical)이 MQM Critical 확정이
아님을 출력에서 구분한다.

v9.2 보강(2026-10): 숫자에 붙은 명시적 단위 별칭(won/원 등)과 천 단위 쉼표를
정규화한다. 값·부호·단위·반복 횟수는 보존하며 통화·배율·소수점 로캘 환산은 하지 않는다.

v9.3 보강(2026-10): 기사 회귀로 확인한 연도형 년 접미 오탐을 보완하고,
percentage points/%포인트/%p를 대조한다. %와 %p, 바뀐 연도는 구분한다.

v9.5 보강(2026-10): 외부 작업본의 제안을 자체 예문으로 검증해 현지화 약어와 시각 표기를
보완했다. 현지화 조정에는 근거를 남기며 괄호 안 수치 생략은 자동 면제하지 않는다.
범위 하이픈(4.5%-5%)의 음수 오추출도 고쳤다. 외부 기사 집계는 독립 재현 결과가 아니다.

v9.4 보강(2026-10): 값이 같은 표기(날짜, 천·만·억↔thousand·million·billion, 기간 단위, 범위,
영하)를 같은 토큰으로 맞춘다. 마일·파운드 등은 번역문이 환산했을 때 계산이 맞으면 review로
알리고 어긋나면 hold한다. 통화·소수점 로캘은 변환하지 않는다.

사용법:
  python3 translation_audit.py 원문.md 번역문.md
  python3 translation_audit.py 원문.md 번역문.md --baseline 초벌번역.md --intensity 기본
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
from datetime import date
from decimal import Decimal, InvalidOperation

VERSION = "9.6.1"
SEVERITY_RANK = {"critical": 0, "major": 1, "minor": 2, "review": 3}
MQM_WEIGHT = {"critical": 25, "major": 5, "minor": 1, "review": 0}
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from translation_formats import PROFILES, compare_formats, legacy_placeholder_text, resolve_profile

URL_RE = re.compile(r"https?://[^\s)>'\"]+")
# Canonicalize only explicit unit aliases; never erase units or convert amounts.
# Decimal commas and dates are not interpreted as locale-specific numbers.
UNIT_ALIASES = {
    "won": "원", "KRW": "원", "원": "원",
    "percent": "%", "per cent": "%", "퍼센트": "%", "%": "%",
    "percentage points": "%p", "percentage point": "%p", "퍼센트포인트": "%p",
    "퍼센트 포인트": "%p", "%포인트": "%p", "%p": "%p",
    "years": "년", "year": "년",
    "kilometers": "km", "kilometres": "km", "kilometer": "km", "kilometre": "km", "킬로미터": "km", "km": "km",
    "centimeters": "cm", "centimetres": "cm", "centimeter": "cm", "centimetre": "cm", "센티미터": "cm", "cm": "cm",
    "meters": "m", "metres": "m", "meter": "m", "metre": "m", "미터": "m", "m": "m",
    "kilograms": "kg", "kilogram": "kg", "킬로그램": "kg", "kg": "kg",
    "grams": "g", "gram": "g", "그램": "g", "g": "g",
    # 기간·연령: 영어 years와 한국어 년은 같은 단위로 본다.
    "years old": "세", "year old": "세", "세": "세", "살": "세",
    "years": "년", "year": "년", "년": "년",
    "months": "개월", "month": "개월", "개월": "개월",
    "weeks": "주", "week": "주", "주": "주",
    "days": "일", "day": "일", "일": "일",
    "hours": "시간", "hour": "시간", "시간": "시간",
    "minutes": "분", "minute": "분", "분": "분",
    "seconds": "초", "second": "초", "초": "초",
    # 온도: -150 °C와 영하 150도는 같은 값이다. 화씨는 따로 둔다.
    "°C": "°", "℃": "°", "degrees": "°", "degree": "°", "도": "°",
    "°F": "°F", "℉": "°F",
    # 야드파운드법: 환산은 하지 않고 단위만 정규화한다. 환산 여부는 아래에서 따로 검증한다.
    "miles": "mi", "mile": "mi", "마일": "mi",
    "nautical miles": "nmi", "nautical mile": "nmi", "해리": "nmi",
    "pounds": "lb", "pound": "lb", "lbs": "lb", "lb": "lb", "파운드": "lb",
    "pounds sterling": "GBP", "pound sterling": "GBP", "파운드 스털링": "GBP",
    "feet": "ft", "foot": "ft", "ft": "ft", "피트": "ft",
    "inches": "in", "inch": "in", "인치": "in",
    "ounces": "oz", "ounce": "oz", "oz": "oz", "온스": "oz",
}
COUNTER_UNITS = {"명", "개", "건", "회"}  # 영어에는 대응 단위가 없어 값만 비교한다.
MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4, "apr": 4,
    "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9, "october": 10, "oct": 10, "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}
_UNIT_PATTERN = "|".join(
    re.escape(unit) + (r"(?![A-Za-z])" if unit.isascii() and unit[-1].isalpha() else "")
    for unit in sorted(UNIT_ALIASES, key=len, reverse=True)
)
NUMBER_RE = re.compile(
    r"(?:(?<![A-Za-z0-9_%])[-+−])?(?<![A-Za-z0-9_])\d+(?:[,.]\d+)*"
    r"(?:[ \t]*(?:(?:억|만|천)(?:[ \t]*(?:원|명|개|건|회))?|"
    + _UNIT_PATTERN + r"|명|개|년|월|일|시|분|배|건|회))?"
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
    match = re.fullmatch(r"([-+−]?\d+(?:[,.]\d+)*)(.*)", value)
    number, unit = match.groups()
    # A comma is removed only for an unambiguous three-digit grouping.
    if re.fullmatch(r"[-+−]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", number):
        number = number.replace(",", "")
    number = number.replace("−", "-")
    unit = unit.strip()
    canonical_unit = UNIT_ALIASES.get(unit, re.sub(r"\s+", "", unit))
    # Four-digit calendar-form years commonly gain a Korean 년 suffix.
    # This is a surface alias only, not proof that the number denotes a date.
    if canonical_unit in COUNTER_UNITS or (canonical_unit == "년" and re.fullmatch(r"[12]\d{3}", number)):
        canonical_unit = ""
    return number + canonical_unit


_MONTH_PAT = "|".join(sorted(MONTHS, key=len, reverse=True))
_NUM = r"[-+−]?\d+(?:[,.]\d+)*"
_TAIL = r"(?:[ \t]*(?:" + _UNIT_PATTERN + r"|명|개|년|월|일|시|분|배|건|회))?"
_UNIT_ONLY = r"(?:[ \t]*(?:" + _UNIT_PATTERN + r"))?"
_NEGATIVE_KO_RE = re.compile(r"(?:영하|마이너스)\s*(?=\d)")
_RANGE_RE = re.compile(
    r"(?<![\w.])(?P<a>" + _NUM + r")(?P<ua>" + _TAIL + r")\s*(?:\bto\b|[–—~〜]|에서)\s*(?P<b>" + _NUM + r")(?P<ub>" + _TAIL + r")"
)
_HYPHEN_RANGE_RE = re.compile(
    r"(?<![\w.-])(?P<a>\d+(?:\.\d+)?)-(?P<b>\d+(?:\.\d+)?)(?P<ub>" + _TAIL + r")(?![A-Za-z0-9_-])"
)
_DATE_PATTERNS = [
    ("en_dmy", re.compile(r"(?<![A-Za-z0-9])(?P<d>\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?P<m>" + _MONTH_PAT + r")\b\.?(?:\s*,?\s*(?P<y>\d{4})(?!\d))?", re.I)),
    ("en_mdy", re.compile(r"(?<![A-Za-z])(?P<m>" + _MONTH_PAT + r")\b\.?\s+(?P<d>\d{1,2})(?:st|nd|rd|th)?(?!\d)(?:\s*,?\s*(?P<y>\d{4})(?!\d))?", re.I)),
    ("en_my", re.compile(r"(?<![A-Za-z])(?P<m>" + _MONTH_PAT + r")\b\.?\s+(?P<y>\d{4})(?!\d)", re.I)),
    ("iso", re.compile(r"(?<![\d.])(?P<y>\d{4})[-/.](?P<m>\d{1,2})[-/.](?P<d>\d{1,2})(?![\d])")),
    ("ko_ymd", re.compile(r"(?:(?P<y>\d{4})\s*년\s*)?(?P<m>\d{1,2})\s*월\s*(?P<d>\d{1,2})\s*일")),
    ("ko_ym", re.compile(r"(?P<y>\d{4})\s*년\s*(?P<m>\d{1,2})\s*월(?!\s*\d)")),
]
_EN_MAG = {"thousand": Decimal(10) ** 3, "million": Decimal(10) ** 6, "billion": Decimal(10) ** 9, "trillion": Decimal(10) ** 12}
_EN_MAG_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?P<n>[-+−]?\d+(?:[,.]\d+)*)\s*(?P<w>thousand|million|billion|trillion)(?![A-Za-z])(?P<u>" + _UNIT_ONLY + r")"
)
_KO_MAG = {"천": Decimal(10) ** 3, "만": Decimal(10) ** 4, "억": Decimal(10) ** 8, "조": Decimal(10) ** 12}
_KO_SEG = r"\d+(?:,\d{3})*(?:\.\d+)?"
_KO_MAG_RE = re.compile(
    r"(?<![\d.,])(?P<span>[-+−]?" + _KO_SEG + r"\s*[조억만천]+(?:\s*" + _KO_SEG + r"\s*[조억만천]*)*)(?P<u>[ \t]*(?:" + _UNIT_PATTERN + r"|명|개|건|회))?"
)
_KO_SEG_RE = re.compile(r"(" + _KO_SEG + r")\s*([조억만천]*)")


def _decimal(text):
    text = text.replace("−", "-").strip()
    if re.fullmatch(r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", text):
        text = text.replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _decimal_text(value):
    text = format(value.normalize(), "f")
    return text[:-2] if text.endswith(".0") else text


def _mask(text, regex, make_token, items):
    out, last = [], 0
    for m in regex.finditer(text):
        token = make_token(m)
        if token is None:
            continue
        for one in (token if isinstance(token, list) else [token]):
            items.append((m.start(), one))
        out.append(text[last:m.start()])
        out.append(" " * (m.end() - m.start()))
        last = m.end()
    out.append(text[last:])
    return "".join(out)


def _date_token(m):
    g = m.groupdict()
    month = g.get("m")
    month = MONTHS.get(month.lower().rstrip(".")) if month and not month.isdigit() else (int(month) if month else None)
    if not month or not 1 <= month <= 12:
        return None
    day = g.get("d")
    if day is not None and not 1 <= int(day) <= 31:
        return None
    if day is not None:
        try:
            date(int(g.get("y") or 2000), month, int(day))
        except ValueError:
            return None
    # 연도는 날짜에 붙이지 않고 따로 센다: "March 3 to April 7, 2026"의 연도는 뒤 날짜에만 붙어 있기 때문이다.
    tokens = [f"date:{month:02d}-{int(day):02d}" if day is not None else f"month:{month:02d}"]
    if g.get("y"):
        tokens.append(f"y:{g['y']}")
    return tokens


def _unit_suffix(raw):
    raw = (raw or "").strip()
    if not raw:
        return ""
    unit = UNIT_ALIASES.get(raw, raw)
    return "" if unit in COUNTER_UNITS else unit


def _en_magnitude_token(m):
    value = _decimal(m.group("n"))
    if value is None:
        return None
    return _decimal_text(value * _EN_MAG[m.group("w").lower()]) + _unit_suffix(m.group("u"))


def _ko_magnitude_token(m):
    total = Decimal(0)
    for number, suffix in _KO_SEG_RE.findall(m.group("span")):
        value = _decimal(number)
        if value is None:
            return None
        for ch in suffix:
            value *= _KO_MAG[ch]
        total += value
    if m.group("span").startswith(("-", "−")):
        total = -total
    return _decimal_text(total) + _unit_suffix(m.group("u"))


def explicit_date_bindings(text):
    """Bind year to month/day only if every recognized date has an explicit year.

    Partial shared-year ranges retain the existing independent year count. This
    avoids inventing which endpoint inherits a year while protecting fully dated
    pairs from year swaps. Reordering complete dates remains allowed.
    """
    bindings = []
    incomplete = False
    def collect(match):
        nonlocal incomplete
        tokens = _date_token(match)
        if tokens is None:
            return None
        if not match.groupdict().get("y"):
            incomplete = True
        else:
            bindings.append(match.group("y") + ":" + tokens[0])
        return tokens
    for _name, regex in _DATE_PATTERNS:
        text = _mask(text, regex, collect, [])
    return [] if incomplete else bindings


def _range_sub(m):
    a, b = m.group("a"), m.group("b")
    ua, ub = m.group("ua") or "", m.group("ub") or ""
    if not ua.strip() and re.fullmatch(r"[12]\d{3}", a):
        return m.group(0)  # "in 2022 to 55%"의 연도는 범위의 시작값이 아니다
    unit = ub if ub.strip() else ua
    return f"{a}{ua if ua.strip() else unit} {b}{ub if ub.strip() else unit}"


def _hyphen_range_sub(m):
    ub = m.group("ub") or ""
    return f"{m.group('a')}{ub} {m.group('b')}{ub}"


_CLOCK_COLON_RE = re.compile(r"(?<![\d:.])(?P<h>[01]?\d|2[0-3]):(?P<m>[0-5]\d)(?![\d:]|\s*[AP]M\b)", re.I)
_CLOCK_KO_RE = re.compile(r"(?<![가-힣])(?P<period>오전|오후)\s*(?P<h>\d{1,2})\s*시(?:\s*(?P<m>\d{1,2})\s*분)?")


def _clock_token(match):
    hour, minute = int(match.group("h")), int(match.group("m") or 0)
    period = match.groupdict().get("period")
    if period:
        if not 1 <= hour <= 12 or minute > 59:
            return None
        hour = hour % 12 + (12 if period == "오후" else 0)
    return f"time:{hour:02d}:{minute:02d}"


def number_tokens(text):
    """값이 같은 표기 차이를 같은 토큰으로 맞춘 숫자 토큰 목록.

    날짜(October 15, 2026 = 2026년 10월 15일), 크기 단어(1.5 billion = 15억), 기간 단위(years = 년),
    범위(24 to 36 = 24~36), 영하 표기, 연도는 같은 값으로 묶는다. 금액·단위의 환산은 하지 않는다.
    """
    text = FENCE_RE.sub(lambda m: " " * len(m.group()), text)
    text = _NEGATIVE_KO_RE.sub("-", text)
    text = _RANGE_RE.sub(_range_sub, text)
    text = _HYPHEN_RANGE_RE.sub(_hyphen_range_sub, text)
    items = []
    # Keep each clock as one value: do not pair an hour with another clock's
    # minutes or accept a missing/reversed 오전/오후 marker.
    text = _mask(text, _CLOCK_KO_RE, _clock_token, items)
    text = _mask(text, _CLOCK_COLON_RE, _clock_token, items)
    for _name, regex in _DATE_PATTERNS:
        text = _mask(text, regex, _date_token, items)
    text = _mask(text, _EN_MAG_RE, _en_magnitude_token, items)
    text = _mask(text, _KO_MAG_RE, _ko_magnitude_token, items)
    for m in NUMBER_RE.finditer(text):
        token = _normalized_number(m.group())
        year = re.fullmatch(r"([12]\d{3})(년)?", token)
        items.append((m.start(), f"y:{year.group(1)}" if year else token))
    return [token for _pos, token in sorted(items, key=lambda x: x[0])]


# 환산은 자동으로 하지 않는다. 다만 번역가가 단위를 환산한 경우 값이 맞는지는 계산해서 알려 준다.
_CONVERSIONS = {
    "mi": ("km", Decimal("1.609344")),
    "lb": ("kg", Decimal("0.45359237")),
    "ft": ("m", Decimal("0.3048")),
    "in": ("cm", Decimal("2.54")),
    "oz": ("g", Decimal("28.349523125")),
}
_QTY_RE = re.compile(r"(-?\d+(?:\.\d+)?)(mi|lb|ft|in|oz|km|kg|cm|m|g|°F|°)")


def _qty(token):
    m = _QTY_RE.fullmatch(token)
    return (Decimal(m.group(1)), m.group(2)) if m else None


def _decimals(token):
    m = re.match(r"-?\d+\.(\d+)", token)
    return len(m.group(1)) if m else 0


def reconcile_conversions(missing_all, extra_all):
    """누락으로 잡힌 야드파운드법 값이 추가 토큰의 미터법 값과 환산 일치하면 '환산 확인'으로 옮긴다."""
    miss = [dict(m) for m in missing_all]
    extra = [dict(e) for e in extra_all]
    converted = []
    for ms in miss:
        if ms["kind"] != "number":
            continue
        src = _qty(ms["value"])
        if not src or (src[1] not in _CONVERSIONS and src[1] != "°F"):
            continue
        value, unit = src
        if unit == "°F":
            target_unit, expected = "°", (value - 32) * 5 / 9
        else:
            target_unit, factor = _CONVERSIONS[unit]
            expected = value * factor
        for ex in extra:
            if ms["count"] <= 0:
                break
            if ex["kind"] != "number" or ex["count"] <= 0:
                continue
            tgt = _qty(ex["value"])
            if not tgt or tgt[1] != target_unit:
                continue
            # Only the target's displayed rounding precision is allowed. A broad
            # percentage tolerance would approve materially wrong conversions.
            tol = Decimal("0.5") * (Decimal(10) ** -_decimals(ex["value"]))
            if abs(tgt[0] - expected) <= tol:
                n = min(ms["count"], ex["count"])
                ms["count"] -= n
                ex["count"] -= n
                converted.append({"source": ms["value"], "target": ex["value"],
                                  "expected": _decimal_text(expected) + target_unit,
                                  "difference": _decimal_text(abs(tgt[0] - expected)),
                                  "tolerance": _decimal_text(tol),
                                  "basis": "target-displayed-rounding-precision", "count": n})
    return ([m for m in miss if m["count"] > 0], [e for e in extra if e["count"] > 0], converted)


def surface_diff(source_locks, other_locks):
    missing = _missing_counts(source_locks, other_locks)
    extra = _extra_counts(source_locks, other_locks)
    return reconcile_conversions(missing, extra)


def shared_locks(text, format_profile="plain"):
    """번역되어도 그대로 남아야 하는 표면 토큰만 추출한다."""
    out = {}
    out["url"] = list(URL_RE.findall(text))
    number_matches = list(NUMBER_RE.finditer(text))
    out["number"] = number_tokens(text)
    out["code"] = CODE_RE.findall(text) + [m.group() for m in FENCE_RE.finditer(text)]
    out["date_binding"] = explicit_date_bindings(FENCE_RE.sub(" ", text))
    # A recognized numeric unit such as KRW is already protected with its amount.
    # A standalone KRW or an acronym spanning beyond a number stays locked.
    out["acronym"] = [m.group() for m in ACRONYM_RE.finditer(text)
                      if not any(n.start() <= m.start() and m.end() <= n.end() for n in number_matches)]
    out["link_target"] = MARKDOWN_LINK_RE.findall(text)
    out["placeholder"] = PLACEHOLDER_RE.findall(legacy_placeholder_text(text, format_profile))
    return out


def _missing_counts(before, after):
    missing = []
    for kind, values in before.items():
        if kind == "date_binding" and not (values and after.get(kind)):
            continue
        b = Counter(values)
        a = Counter(after.get(kind, []))
        for value, count in (b - a).items():
            missing.append({"kind": kind, "value": value, "count": count})
    return missing


# Grok v10.2 handoff: proposed exceptions, checked with synthetic regressions.
# The article corpus and its aggregate measurements were not independently reproduced.
KOREAN_COUNTERS = ("명", "년", "개", "건", "회", "월", "일")
LOCALIZED_ACRONYMS = {
    "US": ("미국", r"(?<![가-힣])미(?= ?(?:정부|당국|관리|특사|대통령|국무부|국방부|연준|의회|중간선거))"), "UK": ("영국",), "EU": ("유럽연합",), "UN": ("유엔", "국제연합"),
    "MP": ("의원",), "PM": ("총리",), "NATO": ("나토", "북대서양조약기구"),
}


def _korean_scale(number_text):
    """정수를 '55만'·'3억' 같은 한국어 만/억 표기로 바꾼 후보를 만든다(정확히 나누어떨어질 때만)."""
    if not re.fullmatch(r"\d+", number_text):
        return []
    n = int(number_text)
    out = []
    for unit, size in (("억", 10 ** 8), ("만", 10 ** 4)):
        if n >= size and n % size == 0:
            out.append(f"{n // size}{unit}")
    return out


def _acronym_context(acronym, source):
    if acronym == "PM":
        return len(re.findall(r"\b(?:UK|British|Australian|Canadian|Japanese|Indian)\s+PM\b|\bprime minister\s*\(PM\)", source, re.I))
    if acronym == "MP":
        return len(re.findall(r"\b(?:UK|British|Australian|Canadian|independent|Labour|Conservative)\s+MP\b|\bmember of parliament\s*\(MP\)", source, re.I))
    return None


def reconcile_locks(missing, extra, target, source=""):
    """수량 표기와 문맥이 있는 약어 대응만 분리한다. 괄호 생략은 면제하지 않는다."""
    pool = Counter()
    for m in extra:
        if m["kind"] == "number":
            pool[m["value"]] += m["count"]
    kept, reconciled = [], []
    for m in missing:
        left = m["count"]
        reason = None
        if m["kind"] == "number":
            value = m["value"]
            candidates = [value + c for c in KOREAN_COUNTERS]
            for scaled in _korean_scale(value):
                candidates += [scaled] + [scaled + c for c in KOREAN_COUNTERS]
            for cand in candidates:
                take = min(left, pool[cand])
                if take:
                    pool[cand] -= take
                    left -= take
                    reason = f"한국어 단위·만 단위 표기 {cand}"
        elif m["kind"] == "acronym" and m["value"] in LOCALIZED_ACRONYMS:
            hits = sum(len(re.findall(k, target)) for k in LOCALIZED_ACRONYMS[m["value"]])
            context_count = _acronym_context(m["value"], source)
            if context_count is not None:
                hits = min(hits, context_count)
            take = min(left, hits)
            if take:
                left -= take
                reason = "현지화 역어 " + LOCALIZED_ACRONYMS[m["value"]][0]
        if left < m["count"]:
            reconciled.append({**m, "count": m["count"] - left, "reason": reason,
                               "basis": "heuristic-candidate", "state": "검토 후보"})
        if left:
            kept.append({**m, "count": left})
    remaining_extra = [
        {**m, "count": pool[m["value"]]} if m["kind"] == "number" else m
        for m in extra if m["kind"] != "number" or pool[m["value"]] > 0
    ]
    return kept, reconciled, remaining_extra


def _extra_counts(before, after):
    extra = []
    for kind, values in after.items():
        if kind == "date_binding" and not (values and before.get(kind)):
            continue
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


def _glossary_values(value, field):
    if value is None:
        return []
    if isinstance(value, str):
        return _split_alts(value)
    if not isinstance(value, (list, tuple)) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValueError("용어집 " + field + "는 문자열 또는 문자열 배열이어야 합니다")
    return [v.strip() for v in value]


def load_glossary(path):
    """용어집 읽기. JSON 또는 TSV/CSV/`=>` 텍스트.

    행 형식: 원어 [탭|=>|->|,] 권장역어|허용변형2 [탭|=>|->|,] 금지역어1|금지역어2 [탭] strict|flex [탭] 사용 문맥
    (첫 역어가 권장어, 나머지는 허용 변형. 4열이 strict(고정)일 때만 변형 혼용을 경고)
    JSON: {"원어": "역어"} / {"원어": ["역어1", "역어2"]} /
          [{"source": "...", "target": ["..."], "forbid": ["..."]}]
    """
    text = read_text(path)
    entries = []
    if path.lower().endswith(".json"):
        obj = json.loads(text)
        if not isinstance(obj, (dict, list)):
            raise ValueError("용어집 JSON은 객체 또는 항목 배열이어야 합니다")
        if isinstance(obj, list) and any(not isinstance(e, dict) or "source" not in e for e in obj):
            raise ValueError("용어집 배열 항목에는 source가 필요합니다")
        items = obj.items() if isinstance(obj, dict) else [(e["source"], e) for e in obj]
        for src, val in items:
            mode, context, allowed, domains, segments = "flex", "", [], [], []
            if isinstance(val, dict):
                if not {"target", "allowed", "forbid"}.intersection(val):
                    raise ValueError("용어집 항목에는 target·allowed·forbid 중 하나가 필요합니다")
                targets, forbid = val.get("target", []), val.get("forbid", [])
                allowed = val.get("allowed", [])
                mode = val.get("mode", "flex")
                context = val.get("context", "")
                domains, segments = val.get("domains", []), val.get("segments", [])
            else:
                targets, forbid = val, []
            targets = _glossary_values(targets, "target")
            forbid = _glossary_values(forbid, "forbid")
            allowed = _glossary_values(allowed, "allowed")
            entries.append(_glossary_entry(src, targets + [a for a in allowed if a not in targets], forbid, mode, context, domains, segments))
        return entries
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        for sep in ("\t", "=>", "->", ","):
            if sep in line:
                cols = [c.strip() for c in line.split(sep)]
                break
        else:
            continue
        if cols[0].lower() in ("source", "원어") and len(entries) == 0:
            continue
        entries.append(_glossary_entry(
            cols[0], _split_alts(cols[1] if len(cols) > 1 else ""), _split_alts(cols[2] if len(cols) > 2 else ""),
            cols[3] if len(cols) > 3 else "flex", cols[4] if len(cols) > 4 else "",
            cols[5] if len(cols) > 5 else [], cols[6] if len(cols) > 6 else []))
    return entries


def _glossary_entry(source, targets, forbid, mode="flex", context="", domains=None, segments=None):
    """첫 역어는 권장어, 나머지는 허용 변형이다. mode=strict이면 한 문서에서 변형을 섞어 쓰면 경고한다."""
    if not isinstance(source, str) or not source.strip():
        raise ValueError("용어집 source는 비어 있지 않은 문자열이어야 합니다")
    if not isinstance(mode, str) or mode.strip().lower() not in ("", "flex", "strict", "고정"):
        raise ValueError("용어집 mode는 flex 또는 strict이어야 합니다")
    if not isinstance(context, str):
        raise ValueError("용어집 context는 설명 문자열이어야 합니다")
    source = source.strip()
    targets, forbid = _glossary_values(targets, "target"), _glossary_values(forbid, "forbid")
    mode = "strict" if mode.strip().lower() in ("strict", "고정") else "flex"
    return {"source": source, "targets": targets, "forbid": forbid, "mode": mode, "context": str(context).strip(),
            "preferred": targets[0] if targets else "", "domains": _scope_values(domains), "segments": _scope_values(segments)}


def _scope_values(value):
    return sorted(set(_glossary_values(value, "domains/segments")))


def select_glossary(entries, domain=None, segment_id=None):
    """Explicit scope only: context prose never acts as a semantic classifier."""
    grouped, deferred, selected = {}, [], []
    for entry in entries:
        domains, segments = entry.get("domains", []), entry.get("segments", [])
        if (domains and domain and domain not in domains) or (segments and segment_id and segment_id not in segments):
            continue
        if (domains and not domain) or (segments and not segment_id):
            deferred.append({"term": entry["source"], "reason": "scope_required", "domains": domains, "segments": segments})
            continue
        grouped.setdefault(entry["source"].casefold(), []).append(entry)
    for group in grouped.values():
        # An explicitly selected scoped sense supersedes a general fallback.
        scoped = [e for e in group if e.get("domains") or e.get("segments")]
        candidates = scoped or group
        signatures = {(tuple(e["targets"]), tuple(e["forbid"]), e.get("mode", "flex")) for e in candidates}
        if len(signatures) > 1:
            deferred.append({"term": group[0]["source"], "reason": "ambiguous_sense"})
        else:
            selected.append(candidates[0])
    return selected, deferred


def glossary_check(source, target, entries, domain=None, segment_id=None):
    issues, applicable, usage = [], 0, []
    selected, deferred = select_glossary(entries, domain, segment_id)
    deferred = [d for d in deferred if _term_in(source, d["term"])]
    for e in selected:
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
        used = {t: _term_count(target, t) for t in e["targets"] if _term_in(target, t)}
        if used:
            usage.append({"term": e["source"], "preferred": e.get("preferred", ""), "mode": e.get("mode", "flex"),
                          "context": e.get("context", ""), "used": used})
            if e.get("mode") == "strict" and len(used) >= 2:
                issues.append({"term": e["source"], "kind": "mixed_variants", "found": sorted(used),
                               "expected": e["targets"], "source_occurrences": n_src})
    variations = [u for u in usage if len(u["used"]) >= 2]
    return {"entries_total": len(entries), "applicable": applicable, "issues": issues,
            "selection": {"domain": domain, "segment_id": segment_id}, "deferred": deferred,
            "usage": usage, "variations": variations,
            "note": "허용 변형은 오류가 아니다. 고정(strict) 용어의 혼용만 경고한다"}


# ---------------------------------------------------------------------------
# v9: 번역투 유형 프로파일 · 문체 혼용 · 목록 마침표 · 완충 표현 · 후편집 범위
# ---------------------------------------------------------------------------
# (유형 ID, 라벨, taxonomy ID, 정규식, 보고 시작 횟수, 주요 격상 횟수, 원천 계통, 교정 방향)
# 보고 시작 횟수 미만은 위험으로 올리지 않는다: 1~2회는 정상 한국어에도 흔하다
# (references/empirical-validation.md — A-2·I-1 강등 근거와 같은 원리).
TRANSLATIONESE_TYPES = [
    ("T1", "무생물 주어 + 능동 만능동사", "A-15",
     re.compile(r"(?:연구|보고서|결과|데이터|기술|시스템|도구|그림|표|사건|상황|경험|제도|정책|변화)(?:은|는|이|가)\s+[^.\n]{0,25}?"
                r"(?:보여\s*준다|보여\s*주었|보여\s*줍니다|말해\s*준다|알려\s*준다|가능하게\s*(?:한다|했|합니다)|허용한다|이끈다|이끌었|가져온다|가져왔)"),
     2, 4, "en", "추상 주어를 사람·수단으로 바꾸거나 '~ 덕분에/~ 때문에' 부사구로 낮춘다"),
    ("T2", "이중 피동", "A-8",
     re.compile(r"(?:되어|보여|쓰여|불려|나뉘어|잊혀|읽혀|놓여|닫혀|열려|바뀌어)\s*(?:지[는고며도]|진다|집니다|졌|질)|지게\s*(?:된다|되었|됐|됩니다)"),
     1, 2, "shared", "보여진다→보인다, 쓰여진→쓰인, 되어진다→된다처럼 한 겹으로 줄인다"),
    ("T2", "행위자 피동 '에 의해'", "A-9",
     re.compile(r"에\s*의(?:해서?|하여|한)(?![가-힣])"),
     2, 4, "en", "행위자를 주어로 올려 능동문으로 바꾼다('연구팀이 발표했다')"),
    ("T3", "대명사 직역", "A-16",
     KOREAN_PRONOUNS, 3, 6, "en", "문맥으로 알 수 있는 주어는 생략하고, 필요하면 이름·호칭으로 복원한다"),
    ("T4", "복수 '들' 과다", "A-17(보류)",
     re.compile(r"(?<=[가-힣])들(?=[은는이가을를의에도과와로])"),
     8, 14, "en", "무정물·이미 복수가 드러난 명사의 '들'을 지운다(사람 명사의 '들'은 보존)"),
    ("T5", "긴 좌향 수식(관형절 중첩)", "A-18", None, 1, 3, "en",
     "관형절을 문장으로 끊고 접속어미로 잇는다. 한 문장에 수식 하나만 남긴다"),
    ("T6", "'가지고 있다' 소유 직역", "A-7",
     re.compile(r"(?:가지고|갖고)\s*(?:있|계)(?:다|는|으며|습니다|었)"),
     1, 3, "en", "있다/갖췄다/지녔다 중 문맥에 맞는 말로, 또는 주어를 바꿔 '~에는 …이 있다'로"),
    ("T7", "이중 조사 결합", "A-19",
     re.compile(r"(?:에서의|에로의|으로의|에의|(?:으)?로부터의)"),
     2, 4, "ja", "'에서의 경험'→'에서 겪은 경험'처럼 서술어를 복원해 조사 연쇄를 푼다"),
    ("P1", "'~에 대해(서)/대한' 남발", "A-1",
     re.compile(r"에\s*대(?:해서?|하여|한)(?![가-힣])"),
     4, 8, "shared", "목적격('을/를')이나 '~에게', '~ 관해'로 바꾸고, 문단당 1회 이하로"),
    ("P2", "'~를 통해' 남발", "A-2",
     re.compile(r"[를을]\s*통(?:해서?|하여|한)(?![가-힣])"),
     3, 5, "en", "'~로', '~해서', 능동문으로 분산한다(1~2회는 보존)"),
    ("P3", "'~에 있어(서)'", "A-3",
     re.compile(r"에\s*있어(?:서의|서는|서도|서)?(?![가-힣])"),
     1, 3, "shared", "'~에서', '~할 때', '~로는'으로 바꾼다"),
    ("P4", "'~와 관련하여/에 기반하여'", "A-5/A-6",
     re.compile(r"(?:와|과)\s*관련(?:하여|해서|된)(?![가-힣])|에\s*기반(?:하여|해서|한)(?![가-힣])"),
     2, 4, "en", "'~ 때문에', '~에 따라', '~를 바탕으로'처럼 관계가 드러나는 말로 바꾼다"),
    ("J1", "일본어식 구문(로서의·라고 하는 등)", "A-3/A-19 보강",
     re.compile(r"(?:으)?로서의(?![가-힣])|라고\s*하는(?![가-힣])|에\s*다름\s*아니|하지\s*않으면\s*안\s*(?:된다|됩니다|되)|(?:으)?로\s*되어\s*있"),
     1, 3, "ja", "'로서의'→'로서', '라고 하는'→'라는', '하지 않으면 안 된다'→'해야 한다'"),
]

LONG_MODIFIER_RE = re.compile(r"(?:하는|되는|있는|없는|하던|되던|받은|가진|한|된|할|될)\s+(?=[가-힣])")
OF_CHAIN_RE = re.compile(r"[가-힣]+의\s+[가-힣]+의\s+[가-힣]+의")
SENT_SPLIT_RE = re.compile(r"(?<=[.!?。])\s+|\n+")
QUOTE_SPAN_RE = re.compile(r"“[^”\n]*”|\"[^\"\n]*\"|「[^」\n]*」|『[^』\n]*』|‘[^’\n]*’")
REG_FORMAL_RE = re.compile(r"(?:니다|니까|십시오|십시요)$")
REG_POLITE_RE = re.compile(r"요$")
REG_PLAIN_RE = re.compile(r"다$")
HEDGE_KO_RE = re.compile(
    r"수\s*도?\s*있(?:다|습니다|으며|고|지만|는데|을)|것으로\s*(?:보인다|보입니다|보이며|보여|추정|판단|예상|전망|생각)|"
    r"가능성이\s*(?:있|높|큽|크)|듯\s*하|보인다|보입니다|추정된다|여겨진다"
)
HEDGE_EN_RE = re.compile(
    r"\b(?:may|might|could|can|would|seems?|seemed|appears?|appeared|likely|possibly|perhaps|probably|suggests?|suggested|tends?\s+to)\b",
    re.I,
)
SCOPE_INTENSITY = {"보수": (0.20, 0.35), "기본": (0.40, 0.55), "적극": (0.55, 0.70)}


def _sentences(text):
    text = FENCE_RE.sub("", text)
    return [p.strip() for p in SENT_SPLIT_RE.split(text) if len(p.strip()) >= 3]


def _excerpt(text, limit=60):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit] + "…"


def _type_hits(spec, text):
    code, _label, _tax, regex, _minr, _majr, _fam, _fix = spec
    if code == "T5":
        hits = []
        for s in _sentences(text):
            if len(s) >= 100 and len(LONG_MODIFIER_RE.findall(s)) >= 4:
                hits.append(s)
        return hits
    out = []
    for m in regex.finditer(text):
        lo, hi = max(0, m.start() - 14), min(len(text), m.end() + 8)
        out.append(text[lo:hi].replace("\n", " "))
    return out


def translationese_profile(text):
    """한국어 번역문의 번역투를 유형별로 세고, 빈도에 따라 경미/주요로 나눈다.

    1~2회는 정상 한국어에도 흔하므로 유형마다 보고 시작 횟수를 둔다. 같은 문단에 서로 다른
    유형이 모이면 hot 문단으로 묶어 문단 단위 윤문을 권한다. 원천 언어 추정은 힌트일 뿐이다.
    """
    body = FENCE_RE.sub("", text)
    chars = max(len(body), 1)
    types, below, total = [], [], 0
    for spec in TRANSLATIONESE_TYPES:
        code, label, tax, _rx, min_report, major_at, family, fix = spec
        hits = _type_hits(spec, body)
        n = len(hits)
        if not n:
            continue
        entry = {
            "id": code, "label": label, "taxonomy": tax, "count": n, "family": family,
            "samples": [_excerpt(h, 48) for h in hits[:3]], "fix": fix,
        }
        if code == "T4" and n / chars * 1000 < 6:
            entry["note"] = "밀도가 낮아 보고하지 않음"
            below.append(entry)
            continue
        if n < min_report:
            below.append(entry)
            continue
        entry["severity"] = "major" if n >= major_at else "minor"
        types.append(entry)
        total += n

    reported = {t["id"] + t["label"] for t in types}
    hot = []
    for i, para in enumerate(_paragraphs(body), 1):
        kinds, hits = set(), 0
        for spec in TRANSLATIONESE_TYPES:
            if spec[0] + spec[1] not in reported:
                continue
            n = len(_type_hits(spec, para))
            if n:
                kinds.add(spec[0])
                hits += n
        if len(kinds) >= 3 or hits >= 5:
            hot.append({"paragraph": i, "types": sorted(kinds), "hits": hits, "excerpt": _excerpt(para)})

    en_types = [t for t in types if t["family"] == "en"]
    ja_types = [t for t in types if t["family"] == "ja"]
    of_chain = len(OF_CHAIN_RE.findall(body))
    en_score = sum(t["count"] for t in en_types)
    ja_score = sum(t["count"] for t in ja_types) + of_chain
    if en_types and (ja_types or of_chain >= 2):
        inferred, hint = "mixed", "영어·일본어형 신호가 섞임 → 심각도가 높은 유형부터"
    elif en_types:
        inferred, hint = "english-like", "영어 원천형 신호 우세 → 피동의 능동화, 주어·대명사 생략, 무생물 주어 낮추기부터"
    elif ja_types or of_chain >= 2:
        inferred, hint = "japanese-like", "일본어 원천형 신호 우세 → 조사·'의' 연쇄, '로서의/라고 하는' 구문부터 정리"
    else:
        inferred, hint = "unclear", "원천 언어를 가를 만한 신호가 부족함(공통형 번역투만 있거나 신호 없음)"
    return {
        "total_hits": total,
        "per_1000_chars": round(total / chars * 1000, 1),
        "types": types,
        "below_threshold": below,
        "hot_paragraphs": hot,
        "source_influence": {"inferred": inferred, "english_score": en_score, "japanese_score": ja_score,
                             "hint": hint, "note": "문체 신호에서 추정한 힌트이며 원천 언어 판정이 아님"},
    }


def _register_of(sentence):
    s = sentence.strip().rstrip(".!?…。 ")
    s = s.rstrip("\"”’)」』 ")
    if REG_FORMAL_RE.search(s):
        return "formal"
    if REG_POLITE_RE.search(s):
        return "polite"
    if REG_PLAIN_RE.search(s):
        return "plain"
    return None


def register_profile(text):
    """따옴표·제목·표·코드 밖의 서술문 어체(합쇼/해요/한다)를 세어 혼용을 찾는다."""
    body = FENCE_RE.sub("", text)
    counts = Counter()
    samples = {"formal": [], "polite": [], "plain": []}
    for para in _paragraphs(body):
        if re.match(r"^\s*(?:#|\||>)", para):
            continue
        para = QUOTE_SPAN_RE.sub("", para)
        for s in _sentences(para):
            reg = _register_of(re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", s))
            if reg:
                counts[reg] += 1
                if len(samples[reg]) < 3:
                    samples[reg].append(_excerpt(s, 40))
    total = sum(counts.values())
    ranked = counts.most_common()
    mixed = False
    minority = None
    if len(ranked) >= 2 and total:
        minority = ranked[1][0]
        mixed = ranked[1][1] >= 2 and ranked[1][1] / total >= 0.15
    return {"counts": dict(counts), "total": total, "mixed": mixed, "minority": minority if mixed else None,
            "samples": samples if mixed else {}}


def list_punctuation_check(text):
    """같은 목록 안에서 항목 끝 마침표가 섞였는지 본다(항목 3개 이상 목록만)."""
    lists, cur = [], []
    for line in FENCE_RE.sub("", text).splitlines():
        m = re.match(r"^\s*(?:[-*+]|\d+[.)])\s+(.+?)\s*$", line)
        if m:
            cur.append(m.group(1))
        elif cur:
            lists.append(cur)
            cur = []
    if cur:
        lists.append(cur)
    issues = []
    for idx, items in enumerate(lists, 1):
        if len(items) < 3:
            continue
        with_p = sum(1 for it in items if it.rstrip()[-1:] in ".。")
        if 0 < with_p < len(items):
            issues.append({"list": idx, "items": len(items), "with_period": with_p})
    return {"lists": len(lists), "inconsistent": issues}


def hedge_profile(source, target, direction):
    ko = [len(HEDGE_KO_RE.findall(p)) for p in _paragraphs(target)]
    dense = [i for i, n in enumerate(ko, 1) if n >= 3]
    out = {"target_hedges": sum(ko), "dense_paragraphs": dense, "source_hedges": None}
    if direction == "en-to-ko":
        out["source_hedges"] = len(HEDGE_EN_RE.findall(source))
    return out


def edit_scope(baseline, final, intensity="기본"):
    """초벌 번역 대비 후편집이 얼마나 문장을 바꿨는지 센다(범위 보고 + 과편집 경고)."""
    import difflib
    warn_at, hold_at = SCOPE_INTENSITY.get(intensity, SCOPE_INTENSITY["기본"])
    b, f = _sentences(baseline), _sentences(final)
    matcher = difflib.SequenceMatcher(None, b, f, autojunk=False)
    kept = sum(blk.size for blk in matcher.get_matching_blocks())
    touched = len(b) - kept
    ratio = touched / max(len(b), 1)
    if ratio < 0.15:
        tier = "가벼움"
    elif ratio < 0.40:
        tier = "보통"
    else:
        tier = "많음"
    size_delta = (len(final) - len(baseline)) / max(len(baseline), 1)
    return {
        "baseline_sentences": len(b), "final_sentences": len(f), "touched_sentences": touched,
        "touched_ratio": round(ratio, 3), "tier": tier, "intensity": intensity,
        "warn_at": warn_at, "hold_at": hold_at, "size_delta": round(size_delta, 3),
        "note": "초벌의 절반가량이 바뀌면 후편집이 아니라 재번역일 수 있음(과교정·post-editese 점검)",
    }


HONORIFIC_RE = re.compile(r"으?시(?=[었겠며고는오])|십니다|십시오|세요|께서|드립니다|드려요|드리겠|주십시오|주세요")


def _translationese_counts(text):
    """유형별 원시 횟수(보고 기준 미만 포함)와 보고 시작 횟수."""
    body = FENCE_RE.sub("", text)
    return {spec[0] + " " + spec[1]: (len(_type_hits(spec, body)), spec[4]) for spec in TRANSLATIONESE_TYPES}


def baseline_delta(source, baseline, target, direction="en-to-ko", format_profile="plain"):
    """초벌 → 후편집본에서 무엇이 사라지고 무엇이 새로 생겼는지. 점수가 아니라 검토 단서다."""
    out = {"translationese": {"fixed": [], "introduced": [], "remaining": []}}
    if direction in ("en-to-ko", "same"):
        before, after = _translationese_counts(baseline), _translationese_counts(target)
        for key, (n_after, min_report) in after.items():
            n_before = before[key][0]
            row = {"type": key, "before": n_before, "after": n_after}
            if n_before >= min_report and n_after < min_report:
                out["translationese"]["fixed"].append(row)
            elif n_after >= min_report and n_after > n_before:
                out["translationese"]["introduced"].append(row)
            elif n_after >= min_report:
                out["translationese"]["remaining"].append(row)
    reg_b, reg_a = register_profile(baseline), register_profile(target)
    dom = lambda r: max(r["counts"], key=r["counts"].get) if r["counts"] else None
    hon_b, hon_a = len(HONORIFIC_RE.findall(baseline)), len(HONORIFIC_RE.findall(target))
    out["register"] = {"baseline_dominant": dom(reg_b), "final_dominant": dom(reg_a),
                       "dominant_changed": bool(dom(reg_b) and dom(reg_a) and dom(reg_b) != dom(reg_a)),
                       "honorific_markers": {"baseline": hon_b, "final": hon_a}}
    src_locks = shared_locks(source, format_profile)
    def missing_keys(text):
        missing, extra, _ = surface_diff(src_locks, shared_locks(text, format_profile))
        if direction == "en-to-ko":
            missing, _, _ = reconcile_locks(missing, extra, text, source)
        return {(m["kind"], m["value"]) for m in missing}
    miss_b, miss_a = missing_keys(baseline), missing_keys(target)
    out["surface_lock"] = {"introduced_missing": sorted(miss_a - miss_b), "fixed": sorted(miss_b - miss_a)}
    return out


BASIS_BY_ID = {"FID-5": "mechanical-check", "FID-6": "mechanical-check", "FID-10": "mechanical-check",
               "LIT-1": "human-review"}


def _label_risks(risks):
    """기계적 차단은 MQM Critical 확정이 아니다. 근거 종류와 확정 상태를 위험마다 밝힌다."""
    for r in risks:
        r["basis"] = BASIS_BY_ID.get(r["id"], "heuristic-candidate")
        r["state"] = "검토 후보"
    return risks


def audit_data(source, target, direction="auto", literary=False, glossary=None,
               baseline=None, intensity="기본", format_profile="auto", domain=None, segment_id=None):
    if direction == "auto":
        direction = "en-to-ko" if re.search(r"[A-Za-z]", source) and re.search(r"[가-힣]", target) else "same"

    profile = resolve_profile(source, format_profile)
    format_report = compare_formats(source, target, profile)
    source_locks = shared_locks(source, profile)
    target_locks = shared_locks(target, profile)
    missing_all, extra_all, converted = surface_diff(source_locks, target_locks)
    missing = [m for m in missing_all if m["kind"] != "placeholder"]
    extra = [m for m in extra_all if m["kind"] != "placeholder"]
    ph_missing = [m for m in missing_all if m["kind"] == "placeholder"]
    ph_extra = [m for m in extra_all if m["kind"] == "placeholder"]
    reconciled = []
    if direction == "en-to-ko":
        missing, reconciled, extra = reconcile_locks(missing, extra, target, source)
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

    translationese = 0
    translationese_data = register_data = list_data = hedge_data = None
    if direction in ("en-to-ko", "same"):
        translationese_data = translationese_profile(target)
        translationese = translationese_data["total_hits"]
        for t in translationese_data["types"]:
            risks.append(_risk(
                "FID-7", "warn", f"한국어 번역투 {t['id']} {t['label']}",
                {"taxonomy": t["taxonomy"], "samples": t["samples"]},
                f"{t['fix']} (taxonomy {t['taxonomy']}; 인용·전문 문맥의 합법적 표현은 보존)",
                severity=t["severity"], mqm="Fluency/Awkward", count=t["count"],
            ))
        for h in translationese_data["hot_paragraphs"]:
            risks.append(_risk(
                "FID-7", "warn", "번역투 군집 문단",
                {"paragraph": h["paragraph"], "types": h["types"], "excerpt": h["excerpt"]},
                "문장별 패치보다 문단 단위로 다시 읽고 윤문(주어·피동·조사 연쇄를 한꺼번에 정리)",
                severity="major", mqm="Fluency/Awkward", count=1,
            ))
        register_data = register_profile(target)
        if register_data["mixed"]:
            minority = register_data["minority"]
            risks.append(_risk(
                "FID-11", "warn", "서술 어체 혼용",
                {"counts": register_data["counts"], "samples": register_data["samples"].get(minority, [])},
                "합쇼체·해요체·한다체 중 문서 전체의 어체를 하나로 통일(따옴표 안 말투와 제목은 예외)",
                severity="minor", mqm="Style/Register", count=register_data["counts"].get(minority, 1),
            ))
        list_data = list_punctuation_check(target)
        if list_data["inconsistent"]:
            risks.append(_risk(
                "FID-12", "warn", "목록 마침표 불일치", list_data["inconsistent"],
                "같은 목록 안에서는 항목 끝 마침표를 모두 붙이거나 모두 뺀다",
                severity="minor", mqm="Style/Punctuation", count=len(list_data["inconsistent"]),
            ))
        hedge_data = hedge_profile(source, target, direction)
        src_h, tgt_h = hedge_data["source_hedges"], hedge_data["target_hedges"]
        if src_h is not None and tgt_h >= src_h + 3 and tgt_h >= 1.5 * max(src_h, 1):
            risks.append(_risk(
                "FID-13", "warn", "완충 표현 증가", {"source": src_h, "target": tgt_h},
                "원문에 없는 '~일 수 있다·~로 보인다·가능성이 있다'로 단정을 흐리지 않았는지 대조",
                severity="major" if literary or tgt_h >= src_h + 6 else "minor",
                mqm="Accuracy/Addition(modality)", count=tgt_h - src_h,
            ))
        if hedge_data["dense_paragraphs"]:
            risks.append(_risk(
                "FID-13", "warn", "완충 표현 밀집 문단", hedge_data["dense_paragraphs"],
                "한 문단에 완충 표현이 3회 이상: 원문이 실제로 유보하는 곳만 남기고 나머지는 단정형으로",
                severity="minor", mqm="Fluency/Awkward", count=len(hedge_data["dense_paragraphs"]),
            ))

    scope = None
    delta = None
    if baseline is not None:
        scope = edit_scope(baseline, target, intensity)
        pct = round(scope["touched_ratio"] * 100)
        if scope["touched_ratio"] >= scope["hold_at"]:
            risks.append(_risk(
                "EDIT-1", "hold", f"후편집 범위 과다(초벌 문장의 {pct}% 수정)",
                {k: scope[k] for k in ("touched_sentences", "baseline_sentences", "touched_ratio", "intensity")},
                "재번역 수준의 변경: 원문 대조(FID)를 다시 하고, 국소 수술이 가능한 곳은 초벌로 되돌릴 것",
                severity="major", mqm="Style/Over-editing", count=scope["touched_sentences"],
            ))
        elif scope["touched_ratio"] >= scope["warn_at"]:
            risks.append(_risk(
                "EDIT-1", "warn", f"후편집 범위 큼(초벌 문장의 {pct}% 수정)",
                {k: scope[k] for k in ("touched_sentences", "baseline_sentences", "touched_ratio", "intensity")},
                "바꾼 문장이 모두 번역투·오역 교정인지 확인하고, 취향 수정은 되돌릴 것",
                severity="minor", mqm="Style/Over-editing", count=scope["touched_sentences"],
            ))
        if abs(scope["size_delta"]) >= 0.25:
            risks.append(_risk(
                "EDIT-2", "warn", "초벌 대비 분량 변화", {"size_delta": scope["size_delta"]},
                "분량이 25% 이상 달라짐: 누락·덧붙임이 없는지 원문과 대조",
                severity="major" if abs(scope["size_delta"]) >= 0.4 else "minor",
                mqm="Accuracy/Omission-Addition", count=1,
            ))
        delta = baseline_delta(source, baseline, target, direction, profile)
        reg = delta["register"]
        hb, ha = reg["honorific_markers"]["baseline"], reg["honorific_markers"]["final"]
        if reg["dominant_changed"] or (abs(ha - hb) >= 3 and abs(ha - hb) >= 0.5 * max(hb, 1)):
            risks.append(_risk(
                "EDIT-3", "warn", "초벌 대비 어체·높임말 변화",
                {"dominant": [reg["baseline_dominant"], reg["final_dominant"]], "honorific_markers": [hb, ha]},
                "후편집이 화자·청자 관계와 높임 수준을 바꾸지 않았는지 확인. 같은 뜻이라도 `확인해`와 `확인해 주세요`는 같지 않다",
                severity="major" if reg["dominant_changed"] else "minor", mqm="Style/Register", count=1,
            ))
        if delta["translationese"]["introduced"]:
            risks.append(_risk(
                "EDIT-4", "warn", "후편집으로 새로 생긴 번역투", delta["translationese"]["introduced"],
                "초벌에 없던 번역투가 수정 과정에서 들어왔다: 해당 문장을 초벌 표현으로 되돌리거나 다시 고칠 것",
                severity="minor", mqm="Fluency/Awkward", count=len(delta["translationese"]["introduced"]),
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
        for e in select_glossary(glossary, domain, segment_id)[0]:
            allowed_terms.extend(e["targets"] + [e["source"]])
        glossary_report = glossary_check(source, target, glossary, domain, segment_id)
        if glossary_report["deferred"]:
            risks.append(_risk("TERM-4", "review", "용어집 적용 범위 확인", glossary_report["deferred"],
                               "분야(--domain)·구간(--segment-id)을 지정하거나 같은 원어의 뜻을 구분한다. 문맥 설명은 자동 분류하지 않는다",
                               severity="review", mqm="Terminology", count=len(glossary_report["deferred"])))
        for issue in glossary_report["issues"]:
            if issue["kind"] == "mixed_variants":
                label, act = "고정 용어 변형 혼용", f"{issue['found']}를 섞어 썼음 → 문서 안에서 하나로 통일(권장어 {issue['expected'][:1]})"
            elif issue["kind"] == "forbidden_variant":
                label, act = "금지 역어 사용", f"'{issue['found']}' 대신 {issue['expected'] or '지정 역어'} 사용"
            elif issue["kind"] == "untranslated_source_term":
                label, act = "용어 미번역", f"원어 '{issue['term']}'가 그대로 남음 → {issue['expected']} 확인"
            else:
                label, act = "용어집 역어 누락", f"'{issue['term']}'의 지정 역어 {issue['expected']}가 번역문에 없음"
            risks.append(_risk(
                {"forbidden_variant": "TERM-2", "mixed_variants": "TERM-3"}.get(issue["kind"], "TERM-1"), "warn", label,
                issue["term"], act + " (모호하면 괄호로 원어 병기)",
                severity="minor" if issue["kind"] == "mixed_variants" else "major",
                mqm="Terminology/Inconsistent", count=issue["source_occurrences"],
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

    if ph_missing or ph_extra or not format_report["pass"]:
        risks.append(_risk(
            "FID-10", "hold", "자리표시자·태그 손상",
            {"missing": ph_missing, "extra": ph_extra, "format_issues": format_report["issues"]},
            "선택한 형식의 문법·태그 계층·보호 속성·변수를 대조한다. alt 등 텍스트 속성은 번역하되 내부 변수는 보존한다",
            severity="critical", mqm="Accuracy/Mistranslation(markup)",
            count=sum(m["count"] for m in ph_missing + ph_extra) + len(format_report["issues"]),
        ))
    if missing:
        risks.append(_risk(
            "FID-6", "hold", "표면 잠금 누락", len(missing),
            "숫자·URL·코드·약어·링크 대상은 번역문을 채택하기 전에 복구",
            severity="critical", mqm="Accuracy/Mistranslation(surface)", count=sum(m["count"] for m in missing),
        ))
    if converted:
        risks.append(_risk(
            "FID-6", "review", "단위 환산 값 확인", converted,
            "야드파운드법 값을 미터법으로 환산한 번역이다. 환산 값은 계산으로 맞았지만 원문 병기 여부는 편집 방침으로 정한다",
            severity="review", mqm="Locale convention", count=len(converted),
        ))
    if reconciled:
        risks.append(_risk(
            "FID-14", "review", "현지화 대응 확인", reconciled,
            "약어의 역어와 수량 표기가 같은 대상을 가리키는지 원문 문맥과 대조한다. 괄호 안 수치 생략은 자동 면제하지 않는다",
            severity="review", mqm="Locale convention", count=len(reconciled),
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

    _label_risks(risks)
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
            "verified_conversions": converted,
            "reconciled": reconciled,
            "number_policy": "값이 같은 표기만 같은 토큰으로 본다(단위 별칭, 천 단위 쉼표, 연도형 년 접미, %와 %p 구분, 날짜, 천·만·억·million·billion, 기간 단위, 범위, 영하, 명시적인 오전·오후 시각). 괄호 수치 생략은 면제하지 않는다. 통화·소수점 로캘은 변환하지 않는다. 마일·파운드·피트·인치·온스·화씨는 계산이 맞을 때만 환산 확인(review)으로 두고, 값이 어긋나면 FID-6 hold로 둔다",
        },
        "placeholders": {"pass": not (ph_missing or ph_extra) and format_report["pass"], "missing": ph_missing, "extra": ph_extra},
        "format_validation": format_report,
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
        "translationese": translationese_data,
        "register": register_data,
        "list_punctuation": list_data,
        "hedges": hedge_data,
        "post_edit_scope": scope,
        "baseline_delta": delta,
        "severity_note": "critical은 기계적 차단 조건이고 사람이 확정하는 MQM Critical과 다르다. 모든 항목은 검토 후보이며 자동 검사 통과는 번역의 정확성 인증이 아니다",
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
    print(f"형식 프로필: {data['format_validation']['profile']} · 형식 문제 {len(data['format_validation']['issues'])}건")
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
    te = data.get("translationese")
    if te and te["types"]:
        kinds = ", ".join(f"{t['id']} {t['label']} {t['count']}" for t in te["types"])
        print(f"번역투 유형: {kinds}  (1000자당 {te['per_1000_chars']})")
        print(f"  원천 힌트: {te['source_influence']['hint']}")
    bd = data.get("baseline_delta")
    if bd:
        tr = bd["translationese"]
        print(f"초벌 대비: 사라진 번역투 {len(tr['fixed'])}종 · 새로 생긴 번역투 {len(tr['introduced'])}종 · 남은 번역투 {len(tr['remaining'])}종"
              f" · 새 표면 잠금 누락 {len(bd['surface_lock']['introduced_missing'])}건")
    scope = data.get("post_edit_scope")
    if scope:
        print(f"후편집 범위: {scope['tier']} — 초벌 문장 {round(scope['touched_ratio'] * 100)}% 수정"
              f"({scope['touched_sentences']}/{scope['baseline_sentences']}), 분량 {scope['size_delta']:+.0%}, 강도 {scope['intensity']}")
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
    parser.add_argument("--format", dest="format_profile", choices=PROFILES, default="auto")
    parser.add_argument("--domain")
    parser.add_argument("--segment-id")
    parser.add_argument("--literary", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--baseline")
    parser.add_argument("--intensity", default="기본", choices=list(SCOPE_INTENSITY))
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
        baseline = read_text(ns.baseline) if ns.baseline else None
    except (OSError, ValueError, KeyError) as exc:
        print(f"입력 읽기 실패: {exc}", file=sys.stderr)
        return 3
    data = audit_data(source, target, ns.direction, ns.literary, glossary, baseline, ns.intensity,
                      ns.format_profile, ns.domain, ns.segment_id)
    if ns.strict:
        data = _apply_strict(data)
    if ns.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
    else:
        _print_report(data)
    return {"pass": 0, "warn": 1, "hold": 2}[data["status"]]


if __name__ == "__main__":
    sys.exit(main())
