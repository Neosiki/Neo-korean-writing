# korean-humanize

한국어 텍스트와 문서를 사람이 쓴 글처럼 다듬는 통합 윤문 스킬이다. AI 티, 번역투, 관공서체, 기계 리듬을 걷어내면서 표면 잠금(숫자, 직접 인용, 영문 용어)은 기계로 검증하고 의미 동등성(부정, 가능성, 인과)은 경고 휴리스틱과 육안 검토로 지킨다.

> 동작 원칙 한 줄: "문체는 사람처럼, 사실은 원문 그대로."

Claude Cowork, Claude Code, Codex에서 동작하는 Agent Skill이다. 별도 API 키나 외부 서비스가 필요 없고, 정량 도구는 Python 표준 라이브러리만 쓴다. 규칙의 단일 원천은 `scripts/patterns.json`이고 `tests/`의 회귀 테스트와 GitHub Actions가 규칙과 구현의 일치를 지킨다. 새 글을 처음부터 쓰는 write-content 스킬도 같은 저장소에 있다.

현재 본체는 8차 고도화(v8)다. v7까지의 확장 taxonomy·quick rules·장문 무손실 청킹·번역 충실성 감사·문학 번역 검토 모드 위에, v8은 `epoko77-ai/im-not-ai` v2.2~v2.3을 이식해 세 가지를 더했다. 수렴 판정을 문자 변경률 하나에서 4축 구조 게이트(`scripts/verify_gates.py`: 문자율·진단 목표달성·C-8 대구 전멸 방지·golden 검사)로 넓혔고, 진단이 taxonomy 전량(~75KB) 대신 읽는 슬림 인덱스(`references/diagnosis-rules.md`, 71패턴 × 2줄, ~13KB)를 빌드 생성물로 추가했으며, 대조 코퍼스 실측(`references/empirical-validation.md`)으로 규칙 심각도를 승격·강등했다(C-8 부정 대구 S1 승격, A-2 "~를 통해"·I-1 "~것이다"는 반복 남발일 때만 수술).

## 설치

Cowork에서는 [dist/korean-humanize.skill](dist/korean-humanize.skill)을 내려받아 대화창에 올리고 "Save skill"을 누른다.

Claude Code에서는 저장소를 스킬 폴더로 복제한다.

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/Neosiki/korean-humanize.git ~/.claude/skills/korean-humanize
```

함께 담긴 write-content까지 쓰려면 하위 폴더를 한 번 더 복사한다.

```bash
cp -r ~/.claude/skills/korean-humanize/write-content ~/.claude/skills/write-content
```

설치가 됐는지 보려면 아무 글이나 붙여넣고 "윤문해줘"라고 말하면 된다.

## 무엇을 하나

두 축으로 동작한다. 동작 축은 윤문(기본), 진단만, 파일 직접 수정 세 가지다. 강도 축은 일반 윤문(S1~S3), 최강 윤문, 8,000자 이상 장편 윤문으로 나뉜다. 파일 직접 수정은 진단, 수정안 diff 미리보기, 사용자 승인을 거친 뒤에만 반영하고 원본을 백업한다.

| 이렇게 말하면 | 이렇게 동작한다 |
|---|---|
| "윤문해줘", "다듬어줘", "번역투 고쳐줘" | 일반 윤문 |
| "최강 윤문 해줘" | S1 강도, AI 흔적 지수 전후 비교, 8축 루브릭(32/40), 보존 게이트 |
| "장문 윤문", 원고 8,000자 이상 | 섹션 분할 후 1패스 윤문, 2패스 통합, 일관성 진단 |
| "진단만 해줘", "AI 티 검사해줘" | 재작성 없이 문제와 심각도(P0~P2)만 보고 |
| "내 문체로 고쳐줘" + 내 글 샘플 2~3문단 | 문체 캘리브레이션: 샘플의 문장 길이, 종결어미, 어휘 온도로 윤문 |

진단 결과는 문법 오류, AI 문체 후보, 장르 부적합 후보, 구조 문제, 작성자 문체 보존 경고의 다섯 범주로 나눠 보고한다. 서로 다른 문제를 한 목록에 섞으면 과윤문이 생기기 때문이다.

## 검출 체계

거시 레이어는 번역투부터 신선함 인플레까지 14개 패턴(A~N)을 잡고, 패턴마다 유지 조건이 붙어 과잉교정을 막는다. 미시 레이어(Sunny-7)는 것, 의, 들, -적, 있다 계열 7개 규칙의 밀도를 점검한다. 구조 진단은 문단 셔플 테스트와 트레드밀 테스트로 글 전체를 보고, 구조 자체가 AI면 윤문 대신 재작성을 권고한다. 사람 결 레이어는 원문에 이미 있는 의견과 체험을 앞세우되 없는 감정이나 일화를 만들어 넣지 않는다.

컨텍스트 프로파일(칼럼·에세이, 보도자료·기사, SNS, 기술문서, 공문서)이 장르별 강도를 조절한다. 이모지 제거나 목록 해체 같은 규칙은 SNS·기술문서에서 오판할 수 있어 프로파일별 완화가 코드에 반영돼 있다. 접속 부사는 별도 진단기로 반복과 문장 위치를 확인한다. 한 번 등장한 `그러나`나 `따라서`를 AI 흔적으로 단정하지 않으며 실제 대조·인과·추가 관계가 필요하면 유지한다.

이 모든 규칙의 정의, 정규식, 심각도, 유지 조건, 프로파일 완화는 `scripts/patterns.json` 한 파일에 있다. 문서 표는 `krh.py taxonomy`로 생성하고 `--check`로 무결성을 검사한다.

## 정량 도구 scripts/krh.py

탐지 전용이며 자동 수정은 하지 않는다. 모든 명령이 `--json`을 지원하고, 파일 인자를 생략하면 stdin을 읽는다.

```bash
python3 scripts/krh.py diagnose  원문.md [--profile official]  # AI 흔적 지수, 등급 A~D, 리듬
python3 scripts/krh.py sunny     원문.md                       # Sunny-7 밀도
python3 scripts/krh.py preserve  원문.md 윤문본.md [--strict]   # 표면 잠금 + 의미 동등성 경고
python3 scripts/krh.py diffrate  원문.md 윤문본.md              # 문자·문장 단위 변경률
python3 scripts/krh.py consistency draft.md                    # 장편 절별 일관성
python3 scripts/krh.py format    기본본.txt                     # SNS·카톡 평문 포맷 검사
python3 scripts/krh.py connectives 원문.md [--remove-redundant]     # 접속 부사 후보 진단·선택적 축약
python3 scripts/krh.py taxonomy --check                        # 규칙 무결성 검사
python3 scripts/krh.py translation-audit 원문.md 번역문.md --direction en-to-ko --literary --json

python3 scripts/verify_gates.py --before 원문.md --after final.md --genre essay  # v8 4축 수렴 게이트
python3 scripts/build_quick_rules.py --check                                    # 생성물 drift 검사
python3 scripts/build_diagnosis_rules.py --check
```

번역문 감수에서는 원문에 없는 주어·감정·강도 부사·설명을 넣지 않고, 숫자·약어·구조·부정·양태·인과를 따로 대조한다. 문학 모드는 데보라 스미스의 독자 지향성·맥락 재방문·분위기 중시를 대비 기준으로 참고하되, 그의 추가·삭제 논쟁이나 영어 문체를 모방하지 않는다.

`connectives`는 후보만 제시하며 자동 삭제를 기본값으로 삼지 않는다. `--remove-redundant`를 지정하면 같은 접속 표지가 문장 시작에서 반복되는 경우에만 축약한 `rewritten` 결과를 함께 출력한다. 서로 다른 접속사는 대조·인과·추가처럼 서로 다른 관계를 표시할 수 있으므로 밀집했다는 이유만으로 함께 삭제하지 않는다. 결과를 채택하기 전에 반전·인과·양보·범위가 유지되는지 사람이 확인한다.

예를 들어 `처음에는 별생각 없었다. 그러나 며칠 뒤 다시 읽었다.`의 `그러나`는 한 번 등장하고 대조 관계를 표시하므로 삭제 후보가 아니다. 반면 같은 접속 부사가 반복되면 문장을 나누거나 문맥이 이미 전달되는지 검토할 후보가 된다.

### 재현 예시

다음 파일을 저장한다.

```text
처음에는 자료가 충분하지 않았다. 그러나 팀은 조사를 계속했다.
그러나 공개 데이터가 추가되면서 방향이 달라졌다. 또한 인터뷰 기록도 확인했다.
따라서 초안은 다시 작성해야 했다. 그러므로 최종 문서에는 검증 과정을 넣었다.
한편 독자는 모든 관계를 설명하지 않아도 앞뒤의 흐름을 따라갈 수 있다.
```

진단 명령은 다음과 같다.

```bash
python3 scripts/krh.py connectives examples/connectives-sample.md --json
```

실행 결과의 핵심은 다음과 같다.

```json
{
  "counts": {"그러나": 2, "따라서": 1, "또한": 1, "그러므로": 1, "한편": 1},
  "total": 6,
  "candidate_words": ["그러나", "그러나"]
}
```

선택적 축약 결과는 다음 명령으로 확인한다.

```bash
python3 scripts/krh.py connectives examples/connectives-sample.md --remove-redundant --json
```

이 경우 반복된 `그러나`만 축약 후보가 되고 `또한` `따라서` `그러므로` `한편`은 서로 다른 논리 관계를 보존하기 위해 유지된다. 도구는 의미 판단을 대신하지 않으므로 축약 결과를 최종 원고로 바로 덮어쓰지 않는다.

diagnose 출력 예시:

```
AI 흔적 지수: 58.04 /1000자  등급 D(심함)  (신호 13개 / 224자)
  [P1] B 관공서·보도 상투구: 3
  [P1] G 상투·과장 수사: 3
  [P1] M 거짓 양보·헤지 스택: 2
리듬: 문장 9개, 평균 23자, 변동계수 0.40
```

회귀 테스트는 `python3 -m unittest discover -s tests`로 돌린다. push마다 GitHub Actions가 같은 테스트를 실행한다. 접속 부사 기능은 단일 표지 유지·반복 표지 후보·문장 시작 위치 보존을 별도로 검증한다.

## 한계

이 스킬은 품질 도구이지 판정기가 아니다. AI 탐지기에서 "100% 인간 작성" 판정을 보장하지 않고, 사람이 급하게 쓴 글도 같은 패턴을 보인다. 스크립트는 표면 신호만 잡으므로 최종 판단은 항상 정성 점검이 한다. Sunny 기준값은 소규모 관찰 기반 임시값이라 장르별 말뭉치 보정이 남은 과제다. 자세한 발전 방향은 [ROADMAP.md](ROADMAP.md)에 있다.

## 파일 구성

```
korean-humanize/
├── SKILL.md                 # 스킬 본체 (윤문 규칙과 워크플로 전체)
├── README.md                # 이 문서
├── CHANGELOG.md             # 1~8차 고도화 이력
├── ROADMAP.md               # 중장기 발전 방향
├── dist/
│   └── korean-humanize.skill # Cowork 설치 파일
├── agents/
│   └── openai.yaml          # Codex 표시명과 기본 프롬프트
├── references/
│   ├── ai-tell-taxonomy.md  # AI 흔적·한국번역학계 유형 확장 분류 (SSOT)
│   ├── quick-rules.md       # span 단위 국소 수술 규칙 (빌드 생성물)
│   ├── diagnosis-rules.md   # v8 진단 전용 슬림 인덱스 (빌드 생성물, 71패턴)
│   ├── empirical-validation.md # v8 대조 코퍼스 실증 결과 (심각도 승격·강등 근거)
│   ├── rewriting-playbook.md # 장르·강도별 실행 플레이북
│   ├── translation-fidelity.md # v7 FID/LIT 감사·데보라 스미스 대비 기준
│   ├── translation-benchmarks.md # 서비스·논문·GitHub benchmark 지도
│   ├── scholarship.md       # 학술·논문 윤문 원칙
│   ├── metrics.py           # v1 정량 지표
│   ├── metrics_v2.py        # v2 지표·장문 청킹 보조
│   ├── baseline*.json       # 기준선 데이터
│   └── examples.md          # 패턴 전후 대조 예시
├── scripts/
│   ├── patterns.json        # 규칙 단일 원천 (A~N + Sunny-7 + 의미 가드)
│   ├── krh.py               # 정량 측정과 보존 검증 통합 도구
│   │                         # connectives: 접속 부사 후보·선택적 축약
│   ├── translation_audit.py # 번역 전후 표면·구조·위험 감사
│   ├── prepare_monolith_input.py # 장문 입력·진단 준비
│   ├── reassemble_chunks.py      # 장문 청크 무손실 재조립
│   ├── verify_change_rate.py     # 변경률 상한 게이트 (하위 호환)
│   ├── verify_gates.py           # v8 4축 구조 수렴 게이트
│   ├── build_quick_rules.py      # quick-rules 생성기
│   └── build_diagnosis_rules.py  # 진단 슬림 인덱스 생성기
├── tests/
│   ├── test_krh.py          # 기존 회귀 테스트
│   ├── test_translation_audit.py # v7 번역 감사 회귀 테스트
│   └── golden/checks.py     # v8 결정적 golden 검사기 (수치 주입·구조 손실)
└── write-content/
    └── SKILL.md             # 글쓰기 스킬 (5단계 워크플로우)
```

## 만든이

NextAI 윤영식(osiki999@gmail.com)이 만들었다. 4차 고도화는 blader/humanizer, hardikpandya/stop-slop, stephenturner/skill-deslop, conorbronsdon/avoid-ai-writing, theclaymethod/unslop, jpeggdev/humanize-writing 여섯 저장소를 대조해 한국어에 맞게 이식했고, 5차 고도화는 외부 코드 리뷰를 반영해 규칙·구현·평가를 일치시키는 데 집중했다. 6차 고도화는 `epoko77-ai/im-not-ai`의 유형 분류와 윤문 스킬업 자료를 참고해 한국어 윤문 taxonomy, 장문 처리, 정량 게이트를 확장했고, 7차는 번역 후편집 충실성 레인과 문학 번역 검토 모드를, 8차는 같은 저장소의 v2.2~v2.3(4축 구조 수렴 게이트, 진단 슬림 인덱스, 대조 코퍼스 실증 검증)을 이식했다. 이 README도 스킬 자신의 기준으로 윤문했다.
