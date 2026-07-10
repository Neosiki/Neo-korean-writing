#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""krh.py — korean-humanize v4 정량 도구 (표준 라이브러리만, 탐지 전용·자동 수정 없음)

사용법:
  python3 krh.py diagnose  원문.md            # AI 흔적 지수 (거시 A~N + 리듬)
  python3 krh.py sunny     원문.md            # 미시 Sunny-7 밀도
  python3 krh.py preserve  원문.md 윤문본.md   # 보존 게이트 (exit 0=보존, 1=누락)
  python3 krh.py diffrate  원문.md 윤문본.md   # 변경률 (S2<=25%, S3<=10%)
  python3 krh.py consistency draft.md         # 장편 절별 일관성
  python3 krh.py format    기본본.txt          # SNS/카톡 평문 포맷 검사
파일 인자를 생략하면 stdin에서 읽는다.
"""
import sys, re, io, unicodedata
from difflib import SequenceMatcher

def read(args, n=1):
    if len(args) >= n:
        return [io.open(a, encoding="utf-8").read() for a in args[:n]]
    if n == 1:
        return [sys.stdin.read()]
    sys.exit("파일 인자가 부족합니다")

# ---------------- 거시 A~N 신호 ----------------
MACRO = {
 "A 번역투":      [r"에\s*의해", r"를\s*통해", r"을\s*통해", r"에\s*다름\s*아니", r"그것은", r"이들은", r"그들은"],
 "B 관공서 상투": [r"위해\s*마련", r"제고하", r"추진할\s*예정", r"기대된다", r"전망이다", r"도모하", r"의미가\s*있다"],
 "C 명사화 종결": [r"것이다[.\s]", r"라는\s*점이다", r"수\s*있다는\s*점"],
 "D 부호 티":     [r"—", r"[가-힣]고,\s", r"[가-힣]며,\s", r"[가-힣]지만,\s"],
 "E 서식 티":     [r"^\s*[-*]\s*\*\*[^*]+\*\*\s*[:：]", r"\*\*[^*]+[:：]\*\*"],
 "G 과장 수사":   [r"주목할\s*만한", r"혁신적", r"획기적", r"새로운\s*지평", r"괄목할", r"눈부신"],
 "H 수동·익명":   [r"평가받고\s*있", r"알려져\s*있", r"되어지", r"여겨지고\s*있"],
 "J 접속 군더더기":[r"또한[,\s]", r"아울러", r"한편[,\s]", r"뿐만\s*아니라"],
 "K 감정 상투":   [r"흥미로운\s*(점|사실)", r"주목할\s*만한\s*(점|사실)", r"놀랍게도", r"인상적인\s*(점|부분)"],
 "L 챗봇 흔적":   [r"하나씩\s*(살펴|짚어)", r"단계별로\s*(살펴|짚어)", r"정리하면\s*다음과\s*같", r"도움이\s*되셨", r"궁금한\s*점이?\s*있"],
 "M 헤지 스택":   [r"물론\s.{0,30}(수\s*있다|있지만)", r"가능성도?\s*배제할\s*수\s*없", r"일\s*수도\s*있고", r"어느\s*정도는"],
 "N 신선함 인플레":[r"아무도\s*말하지\s*않", r"모두가\s*놓치", r"핵심은\s*단\s*하나", r"진짜\s*문제는\s*따로"],
}
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️]")

def sentences(t):
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = re.sub(r"^#+ .*$", " ", t, flags=re.M)
    return [s.strip() for s in re.split(r"(?<=[.!?다요임함])\s+", t) if len(s.strip()) >= 5]

def ending(s):
    m = re.search(r"([가-힣]{1,3})[.!?]?$", s)
    return m.group(1)[-2:] if m else ""

def diagnose_text(t, label=""):
    n = max(len(t), 1)
    total, rows = 0, []
    for cat, pats in MACRO.items():
        c = sum(len(re.findall(p, t, re.M)) for p in pats)
        if c: rows.append((cat, c))
        total += c
    emo = len(EMOJI.findall(t))
    if emo: rows.append(("I 이모지", emo)); total += emo
    sents = sentences(t)
    lens = [len(s) for s in sents] or [0]
    mean = sum(lens)/len(lens)
    var = (sum((x-mean)**2 for x in lens)/len(lens))**0.5
    cv = var/mean if mean else 0
    ends = [ending(s) for s in sents]
    rep = max((sum(1 for _ in g) for _, g in _groups(ends)), default=0)
    idx = total/n*1000
    grade = "A(사람 결)" if idx < 1.5 else "B(경미)" if idx < 4 else "C(뚜렷)" if idx < 8 else "D(심함)"
    if label: print(f"== {label} ==")
    print(f"AI 흔적 지수: {idx:.2f} /1000자  등급 {grade}  (신호 {total}개 / {n}자)")
    for cat, c in sorted(rows, key=lambda x: -x[1]):
        print(f"  {cat}: {c}")
    print(f"리듬: 문장 {len(sents)}개, 평균 {mean:.0f}자, 변동계수 {cv:.2f}" + ("  ← 균일(단조 의심)" if cv < 0.35 and len(sents) >= 5 else ""))
    if rep >= 4: print(f"종결어미 동일 연속 최대 {rep}회 ← 변주 필요")
    return idx

def _groups(seq):
    import itertools
    return itertools.groupby(seq)

def cmd_diagnose(args):
    (t,) = read(args); diagnose_text(t)

# ---------------- Sunny-7 밀도 ----------------
SUNNY = {"것": r"것[이은을에]", "의 연쇄": r"의\s[가-힣]+의\s", "들": r"[가-힣]들[이은을의과와도]",
         "-적": r"[가-힣]적[인으]", "있다는/있어": r"있다는|에\s*있어", "있었다": r"있었다"}
BASE = {"것": 8.0, "의 연쇄": 0.5, "들": 3.0, "-적": 4.0, "있다는/있어": 1.5, "있었다": 1.0}  # 비번역 한국어 대략 기준(/1000자)

def cmd_sunny(args):
    (t,) = read(args); n = max(len(t), 1)
    print("Sunny-7 밀도 (/1000자, 기준 대비):")
    for k, p in SUNNY.items():
        d = len(re.findall(p, t))/n*1000
        flag = "  ← 과다 후보(keep-condition 점검)" if d > BASE[k]*1.8 else ""
        print(f"  {k}: {d:.1f} (기준 {BASE[k]}){flag}")
    print("주의: 밀도는 후보 탐지일 뿐이다. 유지 조건에 해당하면 남긴다.")

# ---------------- 보존 게이트 ----------------
def _facts(t):
    nums = re.findall(r"\d[\d,.]*\s*(?:%|퍼센트|억|만|천|원|명|개|년|월|일|시|분|배|건|회|km|m|cm|kg|g)?", t)
    quotes = re.findall(r"[\"“]([^\"”]{2,})[\"”]", t)
    eng = re.findall(r"[A-Za-z][A-Za-z0-9.\-]{2,}", t)
    return [x.strip() for x in nums if x.strip()], quotes, eng

def cmd_preserve(args):
    a, b = read(args, 2)
    n1, q1, e1 = _facts(a)
    miss = []
    for x in set(n1):
        if b.count(x) < a.count(x): miss.append(("숫자", x))
    for q in q1:
        if q not in b: miss.append(("직접 인용", q[:40]))
    for w in set(e1):
        if w not in b: miss.append(("영문 용어", w))
    if miss:
        print(f"보존 실패 {len(miss)}건:")
        for k, v in miss[:30]: print(f"  [{k}] {v}")
        sys.exit(1)
    print("보존 검증 통과 (숫자·직접 인용·영문 용어). 한글 수사·고유명사는 육안 대조 병행.")

# ---------------- 변경률 ----------------
def cmd_diffrate(args):
    a, b = read(args, 2)
    ratio = SequenceMatcher(None, a, b).ratio()
    ch = (1-ratio)*100
    print(f"변경률: {ch:.1f}%  (S3 상한 10% / S2 상한 25% / S1 상한 없음)")
    if ch > 25: print("S2 상한 초과 — S1 요청이었는지 확인")
    elif ch > 10: print("S3 상한 초과 — S2 이상에서만 허용")

# ---------------- 장편 일관성 ----------------
def cmd_consistency(args):
    (t,) = read(args)
    parts = re.split(r"^#{1,3} ", t, flags=re.M)
    heads = [""] + re.findall(r"^#{1,3} (.+)$", t, flags=re.M)
    secs = [(heads[i][:20] or f"절{i}", p) for i, p in enumerate(parts) if len(p.strip()) > 200]
    for name, body in secs:
        formal = len(re.findall(r"습니다|입니다", body)); plain = len(re.findall(r"[가-힣]다[.\s]", body))
        print(f"\n[{name}] 종결: ~습니다 {formal} / ~다 {plain}" + ("  ← 혼용 의심" if formal and plain and min(formal,plain)/max(formal,plain) > 0.3 else ""))
        diagnose_text(body)
    seen, dup = {}, 0
    for s in sentences(t):
        key = re.sub(r"\s", "", s)[:30]
        if key in seen: dup += 1
        seen[key] = 1
    print(f"\n중복(유사 시작) 문장: {dup}개")

# ---------------- 평문 포맷 ----------------
def cmd_format(args):
    (t,) = read(args); bad = []
    if re.search(r"[*_#>|`]", t): bad.append("마크다운 기호 잔존(*, #, |, ` 등)")
    if EMOJI.search(t): bad.append("이모지 잔존")
    first = sentences(t)[:1]
    if first and len(first[0]) > 60: bad.append(f"첫 문장 {len(first[0])}자 — 60자 이내 권장")
    if re.search(r"^\s*[-•]\s", t, re.M): bad.append("불릿 잔존 — '첫째, 둘째'로 서술")
    if bad:
        print("포맷 위반:"); [print("  -", x) for x in bad]; sys.exit(1)
    print("평문 포맷 통과")

CMDS = {"diagnose": cmd_diagnose, "sunny": cmd_sunny, "preserve": cmd_preserve,
        "diffrate": cmd_diffrate, "consistency": cmd_consistency, "format": cmd_format}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__); sys.exit(2)
    CMDS[sys.argv[1]](sys.argv[2:])
