# 한글 글쓰기(윤문)

**한글 글쓰기(윤문)**는 메모와 주제를 목적에 맞는 한국어 초안으로 발전시키고, 기존 원고는 사실·수치·인용·화자·문서 구조를 지키면서 읽기 좋은 문장으로 다듬는 에이전트 스킬 프로젝트입니다. 칼럼, 기사, 보도자료, 보고서, 기술 문서, SNS 글, 강의 원고, 번역문 후편집을 대상으로 **쓰기와 윤문을 하나의 검증 가능한 흐름**으로 연결합니다.

> **글은 더 분명하게, 문체는 더 자연스럽게, 사실은 원문 그대로.**

이 프로젝트는 특정 탐지기의 판정을 목표로 하지 않습니다. 문장의 번역투·반복·관공서식 표현·과장·리듬 문제를 진단하되, 원문에 없던 경험·감정·주장·근거를 만들어 내지 않는 것을 가장 중요한 원칙으로 둡니다.

## v10 핵심

- **Detect 2.0:** 범주 횟수뿐 아니라 실제 원문 문구, 행·문단 위치, 이유, 유지 조건과 조치를 JSON과 평문으로 제공합니다.
- **문맥·문체 분리:** 장르별 허용도(context)와 필자 voice를 독립 적용하며 기본 voice는 `preserve`입니다.
- **Writer–Editor 인계:** 작성 의도, 출처가 있는 주장, 작성자 해석, 미확인 항목, LOCK과 변경 예산을 JSON 계약으로 전달합니다.
- **정밀 보호 검증:** 숫자·인용 외에도 코드, YAML, 표, URL, 각주를 대조하고 수정 후 새 P0/P1 패턴 증가를 막습니다.
- **구조·오탐 검증:** 고정 슬롯 누출과 공식적인 골격을 진단하고 장르별 false-positive fixture, 자체 문서 self-scan, 배포 무결성 CI를 제공합니다.

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

## 윤문 프롬프트와 작업 템플릿

반복 가능한 작업을 시작하려면 [`prompts/`](prompts/README.md)와 [`templates/`](templates/README.md)를 함께 사용합니다. 프롬프트는 원고를 어떻게 다룰지 지시하고, 템플릿은 목적·독자·LOCK 항목·변경 근거·최종 승인 상태를 기록합니다.

| 필요 상황 | 추천 자산 |
|---|---|
| 일반 원고의 윤문 | [`prompts/standard-editing.md`](prompts/standard-editing.md) + [`templates/editing-brief.md`](templates/editing-brief.md) |
| 보도자료·공식 안내문 | [`prompts/press-release-editing.md`](prompts/press-release-editing.md) |
| 보고서·칼럼·강의 원고 | [`prompts/longform-editing.md`](prompts/longform-editing.md) |
| 번역문 후편집 | [`prompts/translation-postediting.md`](prompts/translation-postediting.md) |
| 사실·인용·수치 확인 | [`templates/lock-register.md`](templates/lock-register.md) |
| 검토·승인 전달 | [`templates/editing-delivery.md`](templates/editing-delivery.md) |

## 설치형 CLI

프롬프트·템플릿을 작업 폴더로 복사하고, 원고의 진단·보존 대조를 명령으로 수행하려면 CLI를 설치합니다.

```bash
python3 -m pip install .
neo-korean-writing assets
neo-korean-writing init writing-workspace --profile general
neo-korean-writing diagnose 원문.md --profile official --json
neo-korean-writing verify 원문.md 수정본.md --strict
neo-korean-writing structure 원문.md --json
neo-korean-writing handoff-validate templates/writer-editor-handoff.json
neo-korean-writing morphology 원문.md --json  # 선택형 kiwipiepy
```

`init`은 선택한 장르의 프롬프트와 공통 작업 의뢰서·LOCK 대조표·결과 전달서를 생성합니다. 설치, 모든 명령, 배포본 빌드 절차는 [`docs/cli.md`](docs/cli.md)를 참고하세요.

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

# 공식적 골격·슬롯 누출과 Writer–Editor 계약 검사
python3 scripts/korean_writing.py structure 원문.md --json
python3 scripts/korean_writing.py handoff-validate templates/writer-editor-handoff.json --json

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
│   ├── validate_repo.py        # 버전·참조·배포 자산 drift 차단
│   ├── self_scan.py            # 저장소 자체 문체 회귀 검사
│   ├── build_skill_package.py  # 검증 후 .skill 재현 빌드
│   ├── translation_audit.py    # 번역문 표면·구조 감사
│   └── verify_gates.py         # 4축 검증 게이트
├── src/neo_korean_writing/     # 설치형 CLI 패키지와 내장 자산
├── pyproject.toml              # Python 패키지·명령 메타데이터
├── docs/cli.md                 # CLI 설치·사용·배포 가이드
├── references/                 # 규칙, 장르별 윤문 처방, 번역 충실성 자료
├── prompts/                    # 상황별 윤문·후편집 프롬프트
├── templates/                  # 의뢰·LOCK·결과 전달 템플릿
├── tests/                      # 회귀·golden·장르별 오탐 fixture
├── paper/                      # 재현 가능한 연구·벤치마크 산출물
└── dist/
    └── neo-korean-writing.skill
```

## 한계와 책임 있는 사용

이 프로젝트는 사람처럼 보이는 문장을 보장하거나 AI 작성 여부를 판정하지 않습니다. 진단 결과는 수정 후보이며, 모든 후보를 반영할 필요가 없습니다. 법률, 의료, 세무, 투자, 공적 발표, 인용문과 통계가 포함된 문서는 원문 근거와 최종 사실 확인을 우선해야 합니다.

## 자료와 이력

정밀 규칙과 장르별 처방은 [`references/`](references/)에, 바로 쓸 수 있는 프롬프트는 [`prompts/`](prompts/README.md)에, 작업 기록 템플릿은 [`templates/`](templates/README.md)에, 설치형 CLI 안내는 [`docs/cli.md`](docs/cli.md)에, 재현 가능한 연구 자료는 [`paper/`](paper/README.md)에, 변경 이력은 [`CHANGELOG.md`](CHANGELOG.md)에 정리했습니다. 프로젝트는 NextAI 윤영식이 개발·유지보수합니다.
