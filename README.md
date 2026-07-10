# korean-humanize v4

한국어 텍스트·문서를 사람이 쓴 글처럼 다듬는 통합 윤문 스킬. AI 티·번역투·관공서체·기계 리듬을 걷어내되, 보존 잠금(LOCK)으로 사실·숫자·고유명사·직접 인용·출처는 한 글자도 바꾸지 않는다.

> 동작 원칙 한 줄: **"문체는 사람처럼, 사실은 원문 그대로."**

Claude Cowork / Claude Code용 Agent Skill이다. 별도 API 키나 외부 서비스가 필요 없고, 정량 도구는 Python 표준 라이브러리만 쓴다.

## 설치

**Cowork:** `korean-humanize-v4.skill` 파일을 대화창에 올리거나 카드에서 "Save skill"을 누른다.

**Claude Code:**

```bash
mkdir -p ~/.claude/skills
cp -r korean-humanize ~/.claude/skills/korean-humanize
```

설치 확인: 아무 글이나 붙여넣고 "윤문해줘"라고 하면 발동한다.

## 무엇을 하나

두 축으로 동작한다.

**동작 축** — 윤문(기본) / 진단만("AI 티 검사해줘", 재작성 없이 심각도 P0~P2 보고) / 파일 직접 수정("이 파일 직접 고쳐줘", 플래그 구간만 최소 수정)

**강도 축** — 일반 윤문(S1~S3) / 최강 윤문(정량 게이트 포함) / 장편 윤문(8,000자 이상, 섹션 분할 2패스)

| 이렇게 말하면 | 이렇게 동작한다 |
|---|---|
| "윤문해줘", "다듬어줘", "번역투 고쳐줘" | 일반 윤문 |
| "최강 윤문 해줘" | S1 강도 + AI 흔적 지수 전/후 + 8축 루브릭(32/40) + 보존 게이트 |
| "장문 윤문", 원고 8,000자 이상 | 섹션 분할 → 1패스 윤문 → 2패스 통합 → 일관성 진단 |
| "진단만 해줘", "AI 티 검사해줘" | 재작성 없이 티와 심각도만 보고 |
| "내 문체로 고쳐줘" + 내 글 샘플 2~3문단 | 문체 캘리브레이션: 샘플의 문장 길이·종결어미·어휘 온도로 윤문 |

## 검출 체계 (2계층 + 구조)

- **거시 A~N (14패턴):** 번역투, 관공서 상투구, 명사화 종결, 부호 티(em-dash), 서식 티(볼드 라벨·기계적 3종), 리듬 단조, 과장 수사, 수동·익명화, 이모지, 접속 군더더기, 감정 표방 상투, 사고사슬·챗봇 흔적, 거짓 양보·헤지 스택, 신선함 인플레. 패턴마다 **유지 조건**이 있어 과잉교정을 막는다.
- **미시 Sunny-7:** 것/의/들/-적/있다 계열의 밀도·중복·잉여를 keep-condition과 짝지어 점검.
- **구조 진단:** 문단 셔플 테스트(순서를 바꿔도 안 깨지면 나열), 트레드밀 테스트(40~60% 잘라도 정보 손실이 없으면 반복). 구조 자체가 AI면 "윤문 불가, 재작성 권고"를 판정한다.
- **사람 결 레이어:** 티를 지우기만 하면 무균실 글이 된다. 원문에 이미 있는 의견·체험·감정을 문장 앞으로 세운다. 없는 감정·일화 삽입은 금지(날조 방지).

컨텍스트 프로파일(칼럼·에세이 / 보도자료·기사 / SNS / 기술문서 / 공문서)이 장르별 강도를 자동 조절한다.

## 정량 도구 — scripts/krh.py

탐지 전용이며 자동 수정은 하지 않는다. 파일 인자를 생략하면 stdin을 읽는다.

```bash
python3 scripts/krh.py diagnose  원문.md          # AI 흔적 지수(/1000자)·등급 A~D·리듬 진단
python3 scripts/krh.py sunny     원문.md          # Sunny-7 밀도 (기준 대비 과다 후보)
python3 scripts/krh.py preserve  원문.md 윤문본.md  # 보존 게이트: 숫자·인용·영문 용어 대조 (exit 0=보존)
python3 scripts/krh.py diffrate  원문.md 윤문본.md  # 변경률 (S3≤10%, S2≤25% 상한 점검)
python3 scripts/krh.py consistency draft.md       # 장편 절별 지수·종결어미 혼용·중복 문장
python3 scripts/krh.py format    기본본.txt        # SNS/카톡 평문 포맷 검사
```

## 부가 기능

- 페북/스레드 SNS 요약(평문, 스레드 ≤ 500자)
- docx 변환(pandoc), 한국 공문서 .hwp/.hwpx 입출력(kordoc — 변환·서식 보존 패치·공문서 생성)
- 5인 전문가 비평(기사화·고도화 요청 시)

## 한계 (정직하게)

이 스킬은 품질 도구이지 판정기가 아니다. AI 탐지기에서 "100% 인간 작성"을 보장하지 않으며, 사람이 급하게 쓴 글도 같은 패턴을 보인다. 스크립트는 표면 신호만 잡으므로 최종 판단은 항상 정성 점검이 한다.

## 파일 구성

```
korean-humanize/
├── SKILL.md                # 스킬 본체 (윤문 규칙·워크플로 전체)
├── README.md               # 이 문서
├── CHANGELOG.md            # 1~4차 고도화 이력
├── references/
│   └── examples.md         # 신규 패턴 전후 대조 예시
└── scripts/
    └── krh.py              # 정량 측정·보존 검증 통합 도구
```

## 관련 스킬

새 글을 처음부터 쓰는 작업(주제·메모 → 완성 글)은 **write-content**를 사용한다. 이 스킬은 이미 쓴 글을 다듬는 용도다.

## 만든이

NextAI 윤영식 (osiki999@gmail.com)

4차 고도화는 blader/humanizer, hardikpandya/stop-slop, stephenturner/skill-deslop, conorbronsdon/avoid-ai-writing, theclaymethod/unslop, jpeggdev/humanize-writing 여섯 저장소를 대조해 한국어에 맞게 이식했다.
