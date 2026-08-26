# 한글 글쓰기(윤문)

**한글 글쓰기(윤문)**는 메모와 주제를 목적에 맞는 한국어 초안으로 발전시키고, 기존 원고는 사실·수치·인용·화자·문서 구조를 지키면서 읽기 좋은 문장으로 다듬는 에이전트 스킬 프로젝트입니다. 칼럼, 기사, 보도자료, 보고서, 기술 문서, SNS 글, 강의 원고, 번역문 후편집을 대상으로 **쓰기와 윤문을 하나의 검증 가능한 흐름**으로 연결합니다.

> **글은 더 분명하게, 문체는 더 자연스럽게, 사실은 원문 그대로.**

이 프로젝트는 특정 탐지기의 판정을 목표로 하지 않습니다. 문장의 번역투·반복·관공서식 표현·과장·리듬 문제를 진단하되, 원문에 없던 경험·감정·주장·근거를 만들어 내지 않는 것을 가장 중요한 원칙으로 둡니다.

## 제공 기능

| 작업 | 시작점 | 결과 |
|---|---|---|
| **한글 글쓰기** | 주제, 메모, 자료, 개요 | 목적·독자·매체에 맞는 구조와 초안 |
| **한글 윤문** | 기존 원고 | 문체·호흡·번역투·반복을 다듬은 수정본 |
| **정밀 진단** | 원고 파일 | 문제 유형, 심각도, 수정 우선순위, 보존 경고 |
| **번역문 후편집** | 원문과 번역문 | 구조·공유 토큰·부정·양태·인과를 대조한 검토 결과 |
| **장문 편집** | 8,000자 이상 원고 | 섹션별 일관성 점검, 필요한 경우 무손실 청킹과 재조립 |

## 핵심 원칙

한글 글쓰기(윤문)는 문장을 무조건 많이 바꾸는 도구가 아닙니다. 문제로 확인된 구간만 고치고, 장르와 높임 정도를 유지하며, 수정 후에는 보존 항목과 변경 범위를 확인합니다.

| 원칙 | 적용 방식 |
|---|---|
| **사실 보존** | 숫자·날짜·고유명사·직접 인용·법조문·표와 목록·링크·기술 용어를 LOCK으로 관리합니다. |
| **문체 보존** | 사용자의 종결어미, 어휘 온도, 문장 길이, 의견과 체험을 평준화하지 않습니다. |
| **과윤문 방지** | 확인된 패턴에만 개입하고, 변경률·목표 달성·수사 구조·golden 검사를 함께 봅니다. |
| **장르 적합성** | 칼럼, 보도자료, 공식 문서, 기술 문서, SNS의 정보 구조와 말투를 구분합니다. |
| **사람 검토 경계** | 의미 동등성, 문화어·고유명사, 문학적 정조, 법률·의료·재무 판단은 자동 확정하지 않습니다. |

## 설치

### Agent Skill 설치

Claude Code, Codex 등에서 저장소 전체를 스킬 경로로 연결합니다.

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/Neosiki/neo-korean-writing.git \
  ~/.claude/skills/neo-korean-writing
```

Cowork용 패키지는 [`dist/neo-korean-writing.skill`](dist/neo-korean-writing.skill)입니다. 새 글을 처음부터 작성하는 보조 워크플로우는 [`korean-writing/`](korean-writing/SKILL.md)에 포함되어 있습니다.

### 요청 예시

```text
"이 메모를 독자가 이해하기 쉬운 칼럼으로 써줘"
"이 보도자료를 격식은 유지한 채 한글 윤문해줘"
"이 보고서를 진단만 하고, 고칠 우선순위를 알려줘"
"영문 원문과 번역문을 비교해 번역투와 의미 보존 위험을 검토해줘"
```

## 작업 흐름

```text
주제·메모·기존 원고
        ↓
목적·독자·매체·장르 확인
        ↓
글쓰기 또는 윤문 경로 선택
        ↓
구조 설계·진단·필요 구간 수정
        ↓
보존 검증·변경률·일관성 점검
        ↓
최종 원고와 변경 요약
```

새 글은 `korean-writing/SKILL.md`의 5단계 흐름(목적 정의 → 구조 설계 → 초안 작성 → 리라이팅 → 최종 출력)으로 작성합니다. 기존 원고는 루트 `SKILL.md`의 light·standard·heavy 윤문 경로를 사용합니다. 번역문은 일반 윤문과 분리된 후편집 경로에서 검토합니다.

## 정량 진단과 검증

`scripts/korean_writing.py`는 **진단 전용** 도구입니다. 자동으로 원문을 덮어쓰지 않으며, 윤문 판단을 보조하는 지표와 보존 검사를 제공합니다.

```bash
# 문체·리듬·AI식 표현 후보 진단
python3 scripts/korean_writing.py diagnose 원문.md --profile official --json

# 미시 표현 밀도 확인
python3 scripts/korean_writing.py sunny 원문.md

# 원문과 수정본의 LOCK 항목 대조
python3 scripts/korean_writing.py preserve 원문.md 윤문본.md --strict

# 변경률·섹션 일관성·평문 포맷 점검
python3 scripts/korean_writing.py diffrate 원문.md 윤문본.md
python3 scripts/korean_writing.py consistency 장문초안.md
python3 scripts/korean_writing.py format 게시용.txt

# 번역문 후편집·문학 번역 검토
python3 scripts/korean_writing.py translation-audit 원문.md 번역문.md \
  --direction en-to-ko --literary --json

# 규칙과 테스트 무결성
python3 scripts/korean_writing.py taxonomy --check
python3 -m unittest discover -s tests -v
```

검증 게이트는 문자 변경률, 진단 대상의 개선 여부, 수사 구조의 과잉 삭제, golden 검사라는 네 축을 함께 봅니다. 모든 지표는 보조 신호이며, 최종 채택 전에는 사실·의미·맥락을 사람이 확인해야 합니다.

## 디렉터리 구조

```text
neo-korean-writing/
├── SKILL.md                    # 한글 윤문·진단·번역 후편집 스킬
├── korean-writing/
│   └── SKILL.md                # 주제·메모에서 시작하는 한글 글쓰기 워크플로우
├── scripts/
│   ├── korean_writing.py       # 진단·보존·변경률·일관성 통합 도구
│   ├── translation_audit.py    # 번역문 표면·구조 감사
│   └── verify_gates.py         # 4축 검증 게이트
├── references/                 # 규칙, 장르별 윤문 처방, 번역 충실성 자료
├── tests/                      # 회귀·golden 검사
├── paper/                      # 재현 가능한 연구·벤치마크 산출물
└── dist/
    └── neo-korean-writing.skill
```

## 한계와 책임 있는 사용

이 프로젝트는 사람처럼 보이는 문장을 보장하거나 AI 작성 여부를 판정하지 않습니다. 진단 결과는 수정 후보이며, 모든 후보를 반영할 필요가 없습니다. 법률, 의료, 세무, 투자, 공적 발표, 인용문과 통계가 포함된 문서는 원문 근거와 최종 사실 확인을 우선해야 합니다.

## 자료와 이력

정밀 규칙과 장르별 처방은 [`references/`](references/)에, 재현 가능한 연구 자료는 [`paper/`](paper/README.md)에, 변경 이력은 [`CHANGELOG.md`](CHANGELOG.md)에 정리했습니다. 프로젝트는 NextAI 윤영식이 개발·유지보수합니다.
