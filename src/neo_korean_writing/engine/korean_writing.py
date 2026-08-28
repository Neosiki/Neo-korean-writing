#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""korean_writing.py v3 — neo-korean-writing 정량 도구 (6.1: 문장 단위 이진 가드·방향 표지·영문 2자 약어) (표준 라이브러리만, 탐지 전용·자동 수정 없음)

사용법:
  python3 korean_writing.py diagnose  원문.md [--profile sns|official|technical] [--heavy] [--remove-redundant] [--json]
  python3 korean_writing.py sunny     원문.md [--json]           # 미시 Sunny-7 밀도
  python3 korean_writing.py preserve  원문.md 윤문본.md [--strict] [--json]
                                                      # 표면 잠금(실패=exit 1) + 의미 동등성 경고
  python3 korean_writing.py diffrate  원문.md 윤문본.md [--json]  # 문자 변경률 + 문장 단위 변경률
  python3 korean_writing.py consistency draft.md                 # 장편 절별 일관성
  python3 korean_writing.py format    기본본.txt                  # SNS/카톡 평문 포맷 검사
  python3 korean_writing.py connectives 원문.md [--remove-redundant] [--json]
                                                      # 접속 부사 후보 진단·선택적 축약
  python3 korean_writing.py taxonomy [--check]                   # patterns.json → 마크다운 표 / 무결성 검사
  python3 korean_writing.py translation-audit 원문.md 번역문.md   # v7 번역 충실성·문학 위험 감사

규칙의 단일 원천은 같은 폴더의 patterns.json이다. 파일 인자를 생략하면 stdin을 읽는다.
"""
import sys, re, io, os, json, itertools
from collections import Counter
from difflib import SequenceMatcher

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️]")

PROFILE_ALIASES = {
    "column": "column", "칼럼": "column",
    "article": "article", "기사": "article",
    "press": "press", "press-release": "press", "보도자료": "press",
    "official": "official", "공문서": "official", "report": "official",
    "technical": "technical", "기술문서": "technical", "docs": "technical",
    "blog": "blog", "블로그": "blog",
    "sns": "sns", "social": "sns",
    "email": "email", "이메일": "email",
    "translation": "translation", "번역": "translation",
}

CONTEXT_RELAXED = {
    "press": {"B"},
    "official": {"B", "E"},
    "technical": {"E"},
    "sns": {"E", "I"},
    "email": {"B"},
}

LAYER_BY_ID = {
    "A": "clarity", "B": "context", "C": "clarity", "D": "style",
    "E": "structure", "F": "rhythm", "G": "clarity", "H": "clarity",
    "I": "context", "J": "structure", "K": "clarity",
    "L": "authorship_signal", "M": "reasoning", "N": "structure",
}

PROTECTED_REGEX = {
    "yaml_frontmatter": re.compile(r"\A---\s*\n.*?\n---\s*(?:\n|\Z)", re.S),
    "fenced_code": re.compile(r"```.*?```", re.S),
    "blockquote": re.compile(r"(?m)^\s*>.*$"),
    "table_row": re.compile(r"(?m)^\s*\|.*\|\s*$"),
    "inline_code": re.compile(r"`[^`\n]+`"),
    "url": re.compile(r"https?://[^\s<>)\]}]+"),
    "file_path": re.compile(r"(?<![\w:/])(?:[A-Za-z]:\\(?:[^\\\s]+\\)*[^\\\s]+|(?:\.{0,2}/)?(?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]+)"),
    "heading": re.compile(r"(?m)^#{1,6}\s+.+$"),
    "footnote": re.compile(r"(?m)^\[\^[^\]]+\]:.*$|\[\^[^\]]+\]"),
    "direct_quote": re.compile(r"\"[^\"\n]{2,}\"|“[^”\n]{2,}”|『[^』\n]{2,}』|「[^」\n]{2,}」"),
}

VALID_VOICES = {"preserve", "yoon-reporter", "professional", "warm", "blunt", "technical"}

def load_patterns():
    with io.open(os.path.join(HERE, "patterns.json"), encoding="utf-8") as f:
        return json.load(f)

def read(args, n=1):
    files, skip_next = [], False
    value_options = {"--profile", "--voice", "--direction"}
    for a in args:
        if skip_next:
            skip_next = False
            continue
        if a in value_options:
            skip_next = True
            continue
        if a.startswith("--"):
            continue
        files.append(a)
    if len(files) >= n:
        contents = []
        for path in files[:n]:
            with io.open(path, encoding="utf-8") as stream:
                contents.append(stream.read())
        return contents
    if n == 1:
        return [sys.stdin.read()]
    sys.exit("파일 인자가 부족합니다")

def opt(args, name, with_value=False):
    for i, a in enumerate(args):
        if a == name:
            return args[i+1] if with_value and i+1 < len(args) else True
    return None

def normalize_profile(profile):
    if not profile:
        return None
    return PROFILE_ALIASES.get(profile, profile)

def protected_spans(t):
    """Return exact protected fragments grouped by kind."""
    return {name: [m.group(0) for m in rx.finditer(t)] for name, rx in PROTECTED_REGEX.items()}

def mask_protected(t):
    """Blank protected prose while retaining offsets and newlines for location reports."""
    chars = list(t)
    spans = []
    for rx in PROTECTED_REGEX.values():
        spans.extend((m.start(), m.end()) for m in rx.finditer(t))
    for start, end in spans:
        for i in range(start, end):
            if chars[i] not in "\r\n":
                chars[i] = " "
    return "".join(chars)

def _location(t, start):
    line = t.count("\n", 0, start) + 1
    before = t[:start]
    blocks = list(re.finditer(r"(?:\A|\n\s*\n)(\s*\S)", before + "X"))
    paragraph = max(len(blocks), 1)
    return {"line": line, "paragraph": paragraph, "start": start}

def _finding(t, pat, match, profile=None, assessment=None):
    pid = pat["id"]
    return {
        "id": pid,
        "layer": LAYER_BY_ID.get(pid, "style"),
        "severity": pat["severity"],
        "location": _location(t, match.start()),
        "span": match.group(0),
        "assessment": assessment or ("clear" if pid == "L" or pat.get("keep") == "없음" else "contextual"),
        "reason": pat["name"],
        "keep_if": pat.get("keep", "문맥상 필요한 경우"),
        "action": "verify" if pid in {"B", "I", "M"} else "revise",
        "context": profile or "general",
    }

def _apply_empirical_guards(pid, matches, scan, profile):
    """Narrow high-FP surface rules using the repository's measured keep conditions."""
    kept = []
    through_count = len(re.findall(r"[를을]\s*통해", scan))
    geosida_count = len(re.findall(r"것이다[.\s]", scan))
    connective_counts = {w: len(re.findall(rf"(?<![가-힣]){w}(?![가-힣])", scan))
                         for w in ("또한", "아울러", "한편")}
    connective_total = sum(connective_counts.values())
    for match in matches:
        span = match.group(0)
        if pid == "A" and re.fullmatch(r"[를을]\s*통해", span) and through_count < 3:
            continue
        if pid == "A" and span in {"그것은", "이들은", "그들은"} and profile != "translation":
            continue
        if pid == "C" and span.startswith("것이다") and geosida_count < 3:
            continue
        if pid == "J" and span.strip(" ,\n") in connective_counts and connective_counts[span.strip(" ,\n")] < 2 and connective_total < 2:
            continue
        kept.append(match)
    return kept

def sentences(t):
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = re.sub(r"^#+ .*$", " ", t, flags=re.M)
    return [s.strip() for s in re.split(r"(?<=[.!?다요임함])\s+", t) if len(s.strip()) >= 5]

def ending(s):
    m = re.search(r"([가-힣]{1,3})[.!?]?$", s)
    return m.group(1)[-2:] if m else ""

# ---------------- diagnose ----------------
def diagnose_data(t, profile=None):
    P = load_patterns()
    profile = normalize_profile(profile)
    scan = mask_protected(t)
    n = max(len(t), 1)
    total, rows, relaxed, findings = 0, [], [], []
    for pat in P["macro"]:
        if pat.get("computed") == "emoji":
            matches = list(EMOJI.finditer(scan))
            c = len(matches)
        elif pat.get("computed"):
            continue
        else:
            matches = []
            for rx in pat["regex"]:
                matches.extend(re.finditer(rx, scan, re.M))
            unique = {(m.start(), m.end(), m.group(0)): m for m in matches}
            matches = [unique[k] for k in sorted(unique)]
            matches = _apply_empirical_guards(pat["id"], matches, scan, profile)
            c = len(matches)
        if not c:
            continue
        entry = {"id": pat["id"], "name": pat["name"], "severity": pat["severity"], "count": c}
        is_relaxed = bool(profile and (pat.get("profiles", {}).get(profile) == "relaxed" or pat["id"] in CONTEXT_RELAXED.get(profile, set())))
        if is_relaxed:
            relaxed.append(entry)
        else:
            rows.append(entry); total += c
        for m in matches:
            findings.append(_finding(t, pat, m, profile, "judgment_call" if is_relaxed else None))
    sents = sentences(scan)
    lens = [len(s) for s in sents] or [0]
    mean = sum(lens) / len(lens)
    cv = ((sum((x - mean) ** 2 for x in lens) / len(lens)) ** 0.5 / mean) if mean else 0
    rep = max((sum(1 for _ in g) for _, g in itertools.groupby(ending(s) for s in sents)), default=0)
    if cv < 0.35 and len(sents) >= 5:
        rhythm_pat = next(p for p in P["macro"] if p["id"] == "F")
        findings.append({
            "id": "F", "layer": "rhythm", "severity": rhythm_pat["severity"],
            "location": {"line": 1, "paragraph": 1, "start": 0},
            "span": "문서 전체", "assessment": "judgment_call",
            "reason": "문장 길이 변동이 낮아 리듬이 균일함",
            "keep_if": rhythm_pat["keep"], "action": "verify", "context": profile or "general",
        })
    idx = total / n * 1000
    grade = "A" if idx < 1.5 else "B" if idx < 4 else "C" if idx < 8 else "D"
    return {"index": round(idx, 2), "grade": grade, "signals": total, "chars": n,
            "patterns": sorted(rows, key=lambda x: -x["count"]), "relaxed": relaxed,
            "findings": sorted(findings, key=lambda x: (x["location"]["start"], x["id"])),
            "profile": profile or "general",
            "rhythm": {"sentences": len(sents), "mean_len": round(mean), "cv": round(cv, 2),
                       "monotone": cv < 0.35 and len(sents) >= 5, "max_same_ending": rep},
            "structure": structure_data(scan)}

def cmd_diagnose(args):
    (t,) = read(args)
    profile = opt(args, "--profile", True)
    d = diagnose_data(t, profile)
    heavy = bool(opt(args, "--heavy"))
    if heavy:
        d["connectives"] = connectives_data(t)
        if opt(args, "--remove-redundant"):
            d["connectives"]["rewritten"] = remove_redundant_connectives(t)
    if opt(args, "--morphology"):
        d["morphology"] = morphology_data(t)
    if opt(args, "--json"):
        print(json.dumps(d, ensure_ascii=False, indent=1)); return
    g = {"A": "A(낮음)", "B": "B(경미)", "C": "C(뚜렷)", "D": "D(높음)"}[d["grade"]]
    print(f"편집 신호 밀도: {d['index']:.2f} /1000자  등급 {g}  (신호 {d['signals']}개 / {d['chars']}자)")
    for p in d["patterns"]:
        print(f"  [{p['severity']}] {p['id']} {p['name']}: {p['count']}")
    for p in d["relaxed"]:
        print(f"  (프로파일 완화) {p['id']} {p['name']}: {p['count']}")
    if d["findings"]:
        print("진단 위치:")
        for f in d["findings"][:30]:
            print(f"  [{f['severity']}/{f['assessment']}] {f['id']} {f['location']['line']}행 "
                  f"\"{f['span'][:60]}\" — {f['reason']} (유지: {f['keep_if']})")
    if heavy:
        c = d["connectives"]
        print("[접속 부사] 최강 윤문 통합 진단 — 자동 삭제하지 않고 후보만 제시")
        print("  " + (", ".join(f"{k} {v}회" for k, v in c["counts"].items()) or "탐지 없음"))
        for row in c["candidates"]:
            label = "축약 후보" if row["candidate"] else "유지 검토"
            print(f"  [{label}] {row['word']} {row['count']}회")
        if "rewritten" in c:
            print("  선택적 축약 결과가 함께 계산됨 — 의미 검토 후 채택")
    r = d["rhythm"]
    print(f"리듬: 문장 {r['sentences']}개, 평균 {r['mean_len']}자, 변동계수 {r['cv']}"
          + ("  ← 균일(단조 의심)" if r["monotone"] else ""))
    if r["max_same_ending"] >= 4:
        print(f"종결어미 동일 연속 최대 {r['max_same_ending']}회 ← 변주 필요")

# ---------------- structure / optional morphology ----------------
def structure_data(t):
    findings = []
    chars = max(len(t), 1)
    headings = re.findall(r"(?m)^#{1,6}\s+.+$", t)
    if len(headings) >= 5 and chars < 3000:
        findings.append({"id": "S-1", "severity": "P1", "type": "excessive_structure",
                         "count": len(headings), "assessment": "contextual",
                         "reason": "짧은 글에 헤딩이 과도하게 많음"})
    slot_hits = re.findall(r"(?m)^\s*\[(?:도입|전환|기준|마무리|서론|본론\d*|결론)\]\s*", t)
    if slot_hits:
        findings.append({"id": "S-2", "severity": "P0", "type": "template_leak",
                         "count": len(slot_hits), "assessment": "clear",
                         "reason": "작성 슬롯 표지가 최종 원고에 남음"})
    formulaic = re.findall(r"(?:오늘은|이번 글에서는|하나씩 살펴보자|정리하면 다음과 같다)", t)
    if formulaic:
        findings.append({"id": "S-3", "severity": "P1", "type": "formulaic_frame",
                         "count": len(formulaic), "assessment": "contextual",
                         "reason": "공식적인 도입·진행 문구가 반복됨"})
    generic_closers = re.findall(r"(?:앞으로가 기대된다|미래는 밝다|도움이 되었기를|귀추가 주목된다)", t)
    if generic_closers:
        findings.append({"id": "S-4", "severity": "P1", "type": "generic_conclusion",
                         "count": len(generic_closers), "assessment": "clear",
                         "reason": "구체적 판단이 없는 상투적 결론"})
    paras = [p.strip() for p in re.split(r"\n\s*\n", t) if len(p.strip()) >= 20]
    if len(paras) >= 4:
        lengths = [len(p) for p in paras]
        mean = sum(lengths) / len(lengths)
        cv = (sum((x - mean) ** 2 for x in lengths) / len(lengths)) ** 0.5 / mean if mean else 0
        if cv < 0.18:
            findings.append({"id": "S-5", "severity": "P2", "type": "uniform_paragraphs",
                             "count": len(paras), "assessment": "judgment_call",
                             "reason": "문단 길이가 지나치게 균일함"})
    return {"findings": findings, "headings": len(headings), "paragraphs": len(paras)}

def cmd_structure(args):
    (t,) = read(args)
    d = structure_data(mask_protected(t))
    if opt(args, "--json"):
        print(json.dumps(d, ensure_ascii=False, indent=1)); return
    if not d["findings"]:
        print("구조 진단 후보 없음"); return
    for f in d["findings"]:
        print(f"[{f['severity']}/{f['assessment']}] {f['id']} {f['reason']} ({f['count']}건)")

def morphology_data(t):
    try:
        from kiwipiepy import Kiwi
    except ImportError:
        return {"available": False, "analyzer": "kiwipiepy",
                "note": "선택 의존성 미설치. 기본 정규식 진단 결과는 그대로 유효함"}
    kiwi = Kiwi(num_workers=0)
    tokens = kiwi.tokenize(mask_protected(t))
    endings = Counter(tok.form for tok in tokens if tok.tag.startswith("E"))
    particles = Counter(tok.form for tok in tokens if tok.tag.startswith("J"))
    return {"available": True, "analyzer": "kiwipiepy", "token_count": len(tokens),
            "top_endings": endings.most_common(10), "top_particles": particles.most_common(10),
            "note": "형태소 결과는 표면 진단 보조 신호이며 LOCK·사실 판정을 변경하지 않음"}

def cmd_morphology(args):
    (t,) = read(args)
    d = morphology_data(t)
    if opt(args, "--json"):
        print(json.dumps(d, ensure_ascii=False, indent=1)); return
    if not d["available"]:
        print(d["note"]); return
    print(f"형태소 {d['token_count']}개 / 종결 {d['top_endings']} / 조사 {d['top_particles']}")

def handoff_data(t):
    try:
        data = json.loads(t)
    except json.JSONDecodeError as error:
        return {"pass": False, "errors": [f"JSON 구문 오류: {error.msg} ({error.lineno}행)"], "warnings": []}
    errors, warnings = [], []
    required = {
        "schema_version": str, "context": dict, "voice": dict,
        "provenance": dict, "locks": dict, "editorial": dict,
    }
    for key, kind in required.items():
        if key not in data:
            errors.append(f"필수 항목 누락: {key}")
        elif not isinstance(data[key], kind):
            errors.append(f"형식 오류: {key}는 {kind.__name__}이어야 함")
    if errors:
        return {"pass": False, "errors": errors, "warnings": warnings}
    for key in ("genre", "channel", "audience", "purpose"):
        value = str(data["context"].get(key, "")).strip()
        if not value or value == "미정" or value.startswith("이 글이 바꾸려는"):
            warnings.append(f"context.{key}가 비어 있음")
    voice = data["voice"].get("profile", "preserve")
    if voice not in VALID_VOICES:
        errors.append(f"지원하지 않는 voice.profile: {voice}")
    for key in ("sourced_claims", "author_interpretations", "unresolved"):
        if key not in data["provenance"] or not isinstance(data["provenance"].get(key), list):
            errors.append(f"provenance.{key}는 배열이어야 함")
    if not isinstance(data["voice"].get("intentional_devices", []), list):
        errors.append("voice.intentional_devices는 배열이어야 함")
    budget = data["editorial"].get("change_budget_pct", 25)
    if not isinstance(budget, (int, float)) or not 0 <= budget <= 50:
        errors.append("editorial.change_budget_pct는 0~50 숫자여야 함")
    return {"pass": not errors, "errors": errors, "warnings": warnings,
            "summary": {"genre": data["context"].get("genre"), "voice": voice,
                        "sourced_claims": len(data["provenance"].get("sourced_claims", [])),
                        "locks": sum(len(v) for v in data["locks"].values() if isinstance(v, list))}}

def cmd_handoff_validate(args):
    (t,) = read(args)
    d = handoff_data(t)
    if opt(args, "--json"):
        print(json.dumps(d, ensure_ascii=False, indent=1))
    else:
        print("Writer–Editor 인계 계약 " + ("통과" if d["pass"] else "실패"))
        for item in d["errors"]:
            print("  오류:", item)
        for item in d["warnings"]:
            print("  경고:", item)
    if not d["pass"]:
        sys.exit(1)

# ---------------- sunny ----------------
def sunny_data(t):
    P = load_patterns(); n = max(len(t), 1); out = []
    for r in P["sunny"]:
        d = len(re.findall(r["regex"], t)) / n * 1000
        out.append({"no": r["no"], "name": r["name"], "density": round(d, 1),
                    "baseline": r["baseline"], "over": d > r["baseline"] * 1.8, "keep": r["keep"]})
    return out

def cmd_sunny(args):
    (t,) = read(args)
    rows = sunny_data(t)
    if opt(args, "--json"):
        print(json.dumps(rows, ensure_ascii=False, indent=1)); return
    print("Sunny-7 밀도 (/1000자, 기준 대비):")
    for r in rows:
        flag = f"  ← 과다 후보(유지 조건: {r['keep']})" if r["over"] else ""
        print(f"  {r['no']} {r['name']}: {r['density']} (기준 {r['baseline']}){flag}")
    print("주의: 밀도는 후보 탐지일 뿐이다. 유지 조건에 해당하면 남긴다.")

# ---------------- connectives (접속 부사 후보·선택적 축약) ----------------
CONNECTIVES = ("그러나", "따라서", "또한", "그러므로", "한편", "아울러", "게다가", "더욱이", "즉")
CONNECTIVE_RE = re.compile(r"(?m)(^|(?<=[.!?])\s+)(" + "|".join(CONNECTIVES) + r")(?:[,:，、]\s*)?")


def connectives_data(t):
    rows = []
    counts = {word: len(re.findall(r"(?<![가-힣])" + re.escape(word) + r"(?![가-힣])", t)) for word in CONNECTIVES}
    total = sum(counts.values())
    for m in CONNECTIVE_RE.finditer(t):
        word = m.group(2)
        before = t[max(0, m.start() - 80):m.start()].strip().replace("\n", " ")
        after = t[m.end():m.end() + 100].strip().replace("\n", " ")
        # 서로 다른 접속사는 각각 다른 논리 관계를 가질 수 있으므로 동일 표지 반복만 후보로 삼는다.
        redundant = counts[word] >= 2
        rows.append({"word": word, "start": m.start(2), "count": counts[word],
                     "candidate": redundant, "before": before[-60:], "after": after[:80]})
    return {"counts": {k: v for k, v in counts.items() if v}, "total": total,
            "candidates": rows, "policy": "필요한 대조·인과·추가 관계는 보존하고 반복되거나 문맥 없이 관계를 이름 붙이는 표지만 후보로 제시"}


def remove_redundant_connectives(t):
    d = connectives_data(t)
    allowed = {r["start"] for r in d["candidates"] if r["candidate"]}
    def repl(m):
        return m.group(1) if m.start(2) in allowed else m.group(0)
    return CONNECTIVE_RE.sub(repl, t)


def cmd_connectives(args):
    (t,) = read(args)
    d = connectives_data(t)
    if opt(args, "--remove-redundant"):
        d["rewritten"] = remove_redundant_connectives(t)
    if opt(args, "--json"):
        print(json.dumps(d, ensure_ascii=False, indent=1)); return
    print("접속 부사 진단: 무조건 삭제하지 않고 반복 후보만 제시")
    print("  " + (", ".join(f"{k} {v}회" for k, v in d["counts"].items()) or "탐지 없음"))
    for r in d["candidates"]:
        flag = "후보" if r["candidate"] else "유지 검토"
        print(f"  [{flag}] {r['word']} ({r['count']}회) ← 앞: {r['before'] or '문단 시작'}")
    if opt(args, "--remove-redundant"):
        print("선택적 축약 결과를 rewritten 필드로 출력했습니다.")

# ---------------- preserve (표면 잠금 + 의미 동등성 경고) ----------------
def _facts(t):
    nums = [x.strip() for x in re.findall(
        r"\d[\d,.]*\s*(?:%|퍼센트|억|만|천|원|명|개|년|월|일|시|분|배|건|회|km|m|cm|kg|g)?", t) if x.strip()]
    quotes = re.findall(r"[\"“]([^\"”]{2,})[\"”]", t)
    eng = re.findall(r"[A-Za-z][A-Za-z0-9.\-]{1,}", t)
    return nums, quotes, eng

def _structure(t):
    return {"불릿 항목": len(re.findall(r"^\s*[-*+] ", t, re.M)),
            "표 행": len(re.findall(r"^\|", t, re.M)),
            "코드 블록": t.count("```") // 2,
            "각주·링크": len(re.findall(r"\[[^\]]+\]\(", t)),
            "직접 인용 개수": len(re.findall(r"[\"“][^\"”]{2,}[\"”]", t))}

def _compare_protected(a, b):
    before, after = protected_spans(a), protected_spans(b)
    changes = []
    for kind in before:
        left, right = Counter(before[kind]), Counter(after[kind])
        missing = list((left - right).elements())
        added = list((right - left).elements())
        if missing or added:
            changes.append({"type": kind, "missing": missing[:10], "added": added[:10]})
    return {"pass": not changes, "changes": changes}

def _residual_growth(a, b):
    before = {p["id"]: p for p in diagnose_data(a)["patterns"]}
    after = {p["id"]: p for p in diagnose_data(b)["patterns"]}
    out = []
    for pid, row in after.items():
        old = before.get(pid, {}).get("count", 0)
        if row["severity"] in {"P0", "P1"} and row["count"] > old:
            out.append({"id": pid, "severity": row["severity"], "before": old, "after": row["count"]})
    return out

def preserve_data(a, b):
    n1, q1, e1 = _facts(a)
    miss = []
    for x in set(n1):
        if b.count(x) < a.count(x): miss.append({"type": "숫자", "value": x})
    for q in q1:
        if q not in b: miss.append({"type": "직접 인용", "value": q[:40]})
    for w in set(e1):
        if w not in b: miss.append({"type": "영문 용어", "value": w})
    warns = []
    G = load_patterns()["meaning_guards"]
    la, lb = max(len(a), 1), max(len(b), 1)
    # 6.1: 짧은 텍스트(문장 단위)는 밀도 허용 오차 대신 표지 개수 이진 비교.
    # 근거: paper/ 본실험 실측 — 문장 단위 단일 변형 96건이 전부 무신호였다.
    short = max(len(a), len(b)) <= G.get("binary_max_chars", 200)
    for key in ("negation", "hedge", "causal"):
        ca, cb = len(re.findall(G[key]["regex"], a)), len(re.findall(G[key]["regex"], b))
        if short:
            if ca != cb:
                warns.append({"type": G[key]["label"], "before": ca, "after": cb,
                              "note": "문장 단위 이진 검사: 표지 개수 변화 — 주장 강도·논리 확인"})
            continue
        da, db = ca / la * 1000, cb / lb * 1000
        if abs(ca - cb) > G["tolerance_abs"] and abs(da - db) > max(da, db, 0.001) * G["tolerance_ratio"]:
            warns.append({"type": G[key]["label"], "before": ca, "after": cb,
                          "note": "주장 강도·논리가 변형됐는지 육안 확인"})
    if short and "direction" in G:
        ta = sorted(re.findall(G["direction"]["regex"], a))
        tb = sorted(re.findall(G["direction"]["regex"], b))
        if ta != tb:
            warns.append({"type": G["direction"]["label"],
                          "before": " ".join(ta) or "없음", "after": " ".join(tb) or "없음",
                          "note": "비교·범위 방향이 바뀌었는지 확인"})
    sa, sb = _structure(a), _structure(b)
    for k in sa:
        if sa[k] != sb[k]:
            warns.append({"type": k, "before": sa[k], "after": sb[k], "note": "구조 요소 개수 변화"})
    protected = _compare_protected(a, b)
    residual = _residual_growth(a, b)
    return {"surface_pass": not miss, "missing": miss, "meaning_warnings": warns,
            "protected_pass": protected["pass"], "protected_changes": protected["changes"],
            "residual_growth": residual}

def cmd_preserve(args):
    a, b = read(args, 2)
    d = preserve_data(a, b)
    strict = opt(args, "--strict")
    if opt(args, "--json"):
        print(json.dumps(d, ensure_ascii=False, indent=1))
    else:
        if d["missing"]:
            print(f"표면 잠금 실패 {len(d['missing'])}건:")
            for m in d["missing"][:30]: print(f"  [{m['type']}] {m['value']}")
        else:
            print("표면 잠금 통과 (숫자·직접 인용·영문 용어).")
        if d["protected_changes"]:
            print(f"보호 구간 변경 {len(d['protected_changes'])}종:")
            for item in d["protected_changes"]:
                print(f"  [{item['type']}] 누락 {len(item['missing'])} / 추가 {len(item['added'])}")
        else:
            print("보호 구간 통과 (코드·YAML·인용·표·URL·경로·헤딩·각주).")
        if d["residual_growth"]:
            print("새 P0/P1 패턴 증가:")
            for item in d["residual_growth"]:
                print(f"  [{item['severity']}] {item['id']} {item['before']} → {item['after']}")
        for w in d["meaning_warnings"]:
            print(f"  경고 [{w['type']}] {w['before']} → {w['after']}: {w['note']}")
        if not d["meaning_warnings"] and not d["missing"]:
            print("의미 동등성 휴리스틱 경고 없음. 인과·주체·비교 조건은 육안 검토를 병행할 것.")
    if d["missing"] or not d["protected_pass"] or d["residual_growth"] or (strict and d["meaning_warnings"]):
        sys.exit(1)

# ---------------- diffrate ----------------
def diffrate_data(a, b):
    char_change = (1 - SequenceMatcher(None, a, b).ratio()) * 100
    sa, sb = sentences(a), sentences(b)
    moved_or_changed = 0
    for s in sa:
        best = max((SequenceMatcher(None, s, t).ratio() for t in sb), default=0)
        if best < 0.6: moved_or_changed += 1
    sent_change = moved_or_changed / max(len(sa), 1) * 100
    return {"char_change_pct": round(char_change, 1), "sentence_change_pct": round(sent_change, 1),
            "sentences_before": len(sa), "sentences_changed": moved_or_changed}

def cmd_diffrate(args):
    a, b = read(args, 2)
    d = diffrate_data(a, b)
    if opt(args, "--json"):
        print(json.dumps(d, ensure_ascii=False)); return
    print(f"문자 변경률: {d['char_change_pct']}%  (S3 상한 10% / S2 상한 25% / S1 상한 없음)")
    print(f"문장 변경률: {d['sentence_change_pct']}%  ({d['sentences_before']}문장 중 {d['sentences_changed']}개가 원문과 60% 미만 일치)")
    if d["char_change_pct"] > 25: print("S2 상한 초과 — S1 요청이었는지 확인")
    elif d["char_change_pct"] > 10: print("S3 상한 초과 — S2 이상에서만 허용")

# ---------------- consistency ----------------
def cmd_consistency(args):
    (t,) = read(args)
    parts = re.split(r"^#{1,3} ", t, flags=re.M)
    heads = [""] + re.findall(r"^#{1,3} (.+)$", t, flags=re.M)
    secs = [(heads[i][:20] or f"절{i}", p) for i, p in enumerate(parts) if len(p.strip()) > 200]
    for name, body in secs:
        formal = len(re.findall(r"습니다|입니다", body)); plain = len(re.findall(r"[가-힣]다[.\s]", body))
        mixed = "  ← 혼용 의심" if formal and plain and min(formal, plain) / max(formal, plain) > 0.3 else ""
        d = diagnose_data(body)
        print(f"[{name}] 지수 {d['index']} ({d['grade']}) / 종결: ~습니다 {formal} vs ~다 {plain}{mixed}")
    seen, dup = set(), 0
    for s in sentences(t):
        key = re.sub(r"\s", "", s)[:30]
        if key in seen: dup += 1
        seen.add(key)
    print(f"중복(유사 시작) 문장: {dup}개")

# ---------------- format ----------------
def format_data(t):
    bad = []
    if re.search(r"[*_#>|`]", t): bad.append("마크다운 기호 잔존(*, #, |, ` 등)")
    if EMOJI.search(t): bad.append("이모지 잔존")
    first = sentences(t)[:1]
    if first and len(first[0]) > 60: bad.append(f"첫 문장 {len(first[0])}자 — 60자 이내 권장")
    if re.search(r"^\s*[-•]\s", t, re.M): bad.append("불릿 잔존 — '첫째, 둘째'로 서술")
    return bad

def cmd_format(args):
    (t,) = read(args)
    bad = format_data(t)
    if bad:
        print("포맷 위반:"); [print("  -", x) for x in bad]; sys.exit(1)
    print("평문 포맷 통과")

# ---------------- taxonomy ----------------
def cmd_taxonomy(args):
    P = load_patterns()
    if opt(args, "--check"):
        ids = [p["id"] for p in P["macro"]]
        ok = ids == [chr(c) for c in range(ord("A"), ord("N") + 1)] and len(P["sunny"]) == 7
        for p in P["macro"]:
            for rx in p["regex"]: re.compile(rx)
        for r in P["sunny"]: re.compile(r["regex"])
        print(f"macro {len(ids)}개({','.join(ids)}), sunny {len(P['sunny'])}개, 정규식 컴파일 OK")
        sys.exit(0 if ok else 1)
    print("| 코드 | 범주 | 심각도 | 신호 수 | 유지 조건 |")
    print("|---|---|---|---|---|")
    for p in P["macro"]:
        src = p.get("computed", f"{len(p['regex'])}개 정규식")
        print(f"| {p['id']} | {p['name']} | {p['severity']} | {src} | {p['keep']} |")
    print()
    print("| # | Sunny | 기준(/1000자) | 유지 조건 |")
    print("|---|---|---|---|")
    for r in P["sunny"]:
        print(f"| {r['no']} | {r['name']} | {r['baseline']} | {r['keep']} |")

def cmd_translation_audit(args):
    from .translation_audit import main
    sys.exit(main(args))

CMDS = {"diagnose": cmd_diagnose, "sunny": cmd_sunny, "connectives": cmd_connectives, "preserve": cmd_preserve,
        "diffrate": cmd_diffrate, "consistency": cmd_consistency, "format": cmd_format,
        "structure": cmd_structure, "morphology": cmd_morphology,
        "handoff-validate": cmd_handoff_validate,
        "taxonomy": cmd_taxonomy, "translation-audit": cmd_translation_audit}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__); sys.exit(2)
    CMDS[sys.argv[1]](sys.argv[2:])
