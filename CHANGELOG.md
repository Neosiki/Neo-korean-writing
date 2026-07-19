# Changelog: korean-humanize

## 7.0.0 (2026-07-19) 7차 고도화: "번역 충실성·문학 번역 검토 레인"

깃허브 benchmark, WMT·SemEval·COLING 논문, 한국어 번역 연구, 번역 서비스 평가와 데보라 스미스 인터뷰·비평을 v6 윤문 워크플로에 연결했다.

**핵심 변경**

- `scripts/translation_audit.py` 추가: 원문–번역문 사이의 숫자·URL·코드·약어·링크 대상 표면 잠금, 제목·불릿·표·코드 구조 대조, 번역투·주어 복원·강도 부사 위험 플래그
- `krh.py translation-audit` 명령 추가 및 `tests/test_translation_audit.py` 회귀 테스트 추가
- `references/translation-fidelity.md` 추가: FID-1~7·LIT-1~3 감사 차원, 번역 후편집 절차, 문학 모드와 데보라 스미스의 기법·방법·문체·주요 판단 어휘·비평 쟁점
- `references/translation-benchmarks.md` 추가: DeepL·Papago·Google Translate·ChatGPT·Gemini·Claude·TranslateGemma·Hunyuan-MT·Yanolja Rosetta·Microsoft Translator와 GitHub·논문·보고서 근거 지도
- SKILL.md·README·에이전트 메타데이터를 v7로 갱신. 문학 모드는 데보라 스미스의 문체를 복제하지 않고 대비 기준으로만 사용

**보존 원칙**

- 번역되어야 할 산문 전체를 기계적으로 잠그지 않고, 양쪽에 그대로 남아야 하는 공유 토큰만 표면 LOCK으로 삼음
- 자동 점수는 후보 선별용이며, 고유명사·문화어·부정·양태·인과·모호성·반복·초점화는 사람 검토 대상으로 유지

## 6.0.0 (2026-07-19) 6차 고도화: "유형 분류·국소 수술·장문 검증의 통합"

`epoko77-ai/im-not-ai`의 윤문 스킬업 자료와 한국번역학계 유형을 참고해 윤문 본체와 재현 도구를 확장했다.

**핵심 변경**

- SKILL.md를 v6 워크플로로 갱신: light/standard/heavy 경로, A~N + Sunny-7, 확장 taxonomy, prompt injection 방어, span 수술, 장문 무손실 청킹, 변경률·보존 게이트를 통합
- `references/ai-tell-taxonomy.md`: AI 흔적·번역투·학술 문체를 아우르는 확장 분류표 추가
- `references/quick-rules.md`, `rewriting-playbook.md`, `scholarship.md`: 국소 규칙, 장르별 실행 절차, 논문 윤문 원칙 추가
- `references/metrics_v2.py`와 기준선 JSON 추가: 진단·장문 청크·경로 판정의 재현성 강화
- `scripts/prepare_monolith_input.py`, `reassemble_chunks.py`, `verify_change_rate.py` 추가: 장문 입력 준비, 무손실 재조립, 변경률 상한 검증
- `agents/openai.yaml` 추가: Codex에서 v6 스킬을 표시하고 호출하는 메타데이터 제공
- 기존 `krh.py`, `patterns.json`, `examples.md`를 v6 규칙과 맞춤

**보존 원칙**

- 원문 사실·숫자·인용·화자·불확실성은 계속 LOCK 대상으로 유지
- 새 규칙은 원문에 없는 감정·사례·주장을 만들지 않으며, 수치 게이트를 통과하지 못하면 윤문을 중단하고 검토를 요구

## 5.0.0 (2026-07-10) 5차 고도화: "규칙·구현·평가의 일치"

외부 코드 리뷰의 P0 다섯 건과 품질 제안을 반영했다.

**P0 수정**

- README가 중간에 잘린 채 배포되던 문제 수정(파일 동기화 사고), 설치 안내를 실제 배포 파일(dist/)과 일치시킴
- Sunny-7이 코드에는 6규칙만 구현돼 있던 불일치 해소: 7번(어색한 있다) 분리 구현
- SKILL.md의 A~N 14패턴과 탐지 코드의 불일치 해소: scripts/patterns.json을 단일 원천으로 통합, `krh.py taxonomy --check`로 무결성 검사
- references/examples.md의 M 예시가 원문에 없던 사실("3년 뒤 재정 부담")을 추가하던 LOCK 위반 교체

**신규**

- LOCK 이원화: 표면 잠금(기계 검증) + 의미 동등성 검토(부정·가능성·인과·구조 요소 경고 휴리스틱). "의미·사실 100% 보존" 표현을 정확한 문구로 교체
- 진단 출력 5범주 분리: 문법 오류 / AI 문체 후보 / 장르 부적합 후보 / 구조 문제 / 작성자 문체 보존 경고
- 프로파일 완화를 코드에 반영: 공문서(B), SNS(I 이모지), 기술문서(E 서식)를 `diagnose --profile`로 지원
- 파일 직접 수정 안전 흐름: 진단 → diff 미리보기 → 사용자 승인 → 반영, 원본 .bak 백업
- diffrate에 문장 단위 변경률 추가(재배열·재작성 감지 보강)
- 전 명령 `--json` 출력 지원
- tests/ 회귀 테스트 15건 + GitHub Actions CI
- ROADMAP.md: 말뭉치 보정, 구조 기반 장문 분할, 형태소 분석 선택 의존성, write-content 분리, 배포 체계
- dist/korean-humanize.skill을 저장소에 동봉

## 4.0.1 (2026-07-10)

- README 전면 윤문: em-dash·볼드 라벨 등 부호·서식 티를 스킬 자신의 기준(거시 D·E 패턴)으로 걷어내고 산문 중심으로 재작성
- write-content 5단계 글쓰기 스킬 동봉 (write-content/SKILL.md)

## 4.0.0 (2026-07-10) 4차 고도화: "사람이 처음부터 끝까지 쓴 글처럼"

GitHub 윤문 스킬 6종(blader/humanizer, stop-slop, skill-deslop, avoid-ai-writing, unslop, humanize-writing)을 대조 분석해 한국어에 맞게 이식.

**신규**

- 문체 캘리브레이션: 사용자 글 샘플 2~3문단에서 문장 길이 분포·종결어미 습관·어휘 온도를 추출해 윤문 기준으로 사용. 어휘 업그레이드 금지 원칙
- 동작 모드 2축 분리: 윤문(기본) / 진단만(detect) / 파일 직접 수정(edit)
- 거시 패턴 A~J → A~N 확장: K 감정 표방 상투, L 사고사슬·챗봇 흔적, M 거짓 양보·헤지 스택, N 신선함·자기 라벨링 인플레
- 거시 표에 유지 조건(keep-condition) 열 추가: 미시 레이어에만 있던 과잉교정 방지 장치를 거시로 확대
- 구조 진단 2종: 문단 셔플 테스트, 트레드밀(정보 밀도) 테스트 + 전면 재작성 권고 기준(플래그 5+ & 범주 3+ & 리듬 균일)
- 사람 결 레이어: 원문에 이미 있는 의견·체험을 문장 앞으로. 없는 감정·일화 삽입 금지. 소리 내어 읽기 테스트 4문항
- 8축 정량 루브릭(40점, 통과선 32)을 최강 윤문 게이트에 추가
- 2차 검수 패스: 윤문본을 "그래도 AI 티 나는가" 관점으로 재감사, 수렴 반복 상한 2회
- 심각도 P0(신뢰 파괴)~P2(다듬기) 분류
- 컨텍스트 프로파일 5종(칼럼·에세이/보도자료·기사/SNS/기술문서/공문서) + 자동 감지
- 변경률 상한: S3 ≤ 10%, S2 ≤ 25%
- 변경 요약 표 형식(레이어별, 실제 바꾼 것만, 8행 상한)
- 패턴 스태킹 통합 보고(같은 문장에 겹친 패턴은 하나의 강한 티로)
- references/examples.md: 신규 패턴 전후 대조 예시

**복원·통합**

- scripts/ 7개 스크립트가 배포본에서 유실돼 정량 게이트가 전부 건너뛰기로 동작하던 문제를 krh.py 단일 도구(diagnose/sunny/preserve/diffrate/consistency/format)로 복원. 표준 라이브러리만 사용
- 검증: AI 티 샘플 지수 58.0(D) → 윤문 후 0.0(A), 숫자 변조 시 보존 게이트 exit 1 확인

## 3.x — 3차 고도화

- 일반·최강·장편(8,000자 이상) 통합. 장편은 섹션 분할 2패스 리라이팅·통합 윤문
- 정량 진단(AI 흔적 지수 전/후)·보존 검증 게이트를 최강 윤문에 도입
- .hwp/.hwpx kordoc 입출력(변환·서식 보존 패치·공문서 생성), SNS 요약, docx 변환
- 외부 문서(PDF·HWP) 숨김 지시문 안전 메모

## 2.x — 2차 고도화

- 2계층 모델 정립: 거시 A~J 패턴 +
