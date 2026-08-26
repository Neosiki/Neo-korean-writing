# Changelog: korean-writing-polish

## Unreleased

## 9.0.0 (2026-08-26) 한글 글쓰기(윤문) 전환

- 프로젝트명과 공개 저장소 URL을 `korean-writing-polish`로 전환하고, 서비스 표기를 **한글 글쓰기(윤문)**로 통일했습니다.
- 새 글 작성 경로를 `korean-writing/`으로 정리하고, 루트 윤문 스킬에서 주제·메모 기반 요청을 이 워크플로우로 연결했습니다.
- 통합 정량 도구를 `scripts/korean_writing.py`로, 회귀 테스트를 `tests/test_korean_writing.py`로 바꿨습니다.
- Cowork 패키지, 연구 산출물, 문서, 자동화 워크플로우의 경로·설치 안내·식별자를 새 이름으로 갱신했습니다.
- 최종 윤문본 메타 블록 식별자를 `KOREAN-WRITING-SUMMARY`로 변경해 새 프로젝트의 산출물 계약을 명확히 했습니다.

- `korean_writing.py connectives` 명령을 추가해 그러나·따라서·또한·그러므로·한편 등의 문장 시작 접속 부사를 반복량과 위치 기준으로 진단합니다.
- 접속 부사를 AI 글의 확정 증거로 취급하지 않고 실제 대조·인과·양보 관계가 필요한 경우 유지하도록 후보와 유지 검토를 구분합니다.
- `--remove-redundant` 선택형 축약 옵션과 `references/connective-adverbs.md` 실전 가이드를 추가했습니다.
- 단일 표지 유지·반복 표지 후보·문장 시작 위치 보존 회귀 테스트를 추가했습니다.


## 8.0.0 (2026-07-23) 8차 고도화: "4축 수렴 게이트·진단 슬림 인덱스·실측 승격강등"

`epoko77-ai/im-not-ai`의 최근 업데이트(v2.2 route_hint 재편, v2.3 구조 수렴 게이트·슬림 진단·대조 코퍼스 실증 백포트)를 이식했다.

**핵심 변경**

- `scripts/verify_gates.py` 추가: 문자 변경률 단일 게이트를 4축(P0 문자율 / P1 진단 목표달성 z-score / P2 C-8 대구 전멸 방지 / P3 golden·수치 주입 차단)으로 확장, P4 문장 터치율은 보고 전용. `tests/golden/checks.py` 결정적 검사기 동반. `verify_change_rate.py`는 하위 호환 보존
- `references/diagnosis-rules.md` 추가: 진단 전용 슬림 인덱스(71패턴 전수 × 2줄, ~13KB). 진단 시 taxonomy 전량(~75KB) 로드를 대체해 토큰 35~50% 절감. `scripts/build_diagnosis_rules.py`·`build_quick_rules.py`가 SSOT에서 결정적으로 생성하고 `--check`로 drift 차단
- `references/empirical-validation.md` 추가 및 taxonomy 실측 백포트: C-8 부정 대구 S1 승격(AI 5.8 vs 인간 0.6, 9.2배 — 실측 최강 신호, 단 전멸 금지) / A-2 "~를 통해" S2 강등(비번역 한국어가 2배 더 씀, 문단 3회+만) / I-1 "~것이다" 완화(인간이 2배, 연속 3회+만) / A-16 대명사 직역 번역 맥락 전용화 / E-1 "장문 부재" 재정의(100자+ 문장 11배 차이)
- `references/metrics_v2.py`에 `antithesis_count`(C-8 대구 카운터, 전멸 판정 전용) 추가
- SKILL.md v8 갱신: light 조기 종료("이미 좋습니다"), 진단은 슬림 인덱스 우선, 수렴 판정 SSOT를 verify_gates 4축으로 교체, 자체검증 항목의 심각도 개편 반영

**보존 원칙**

- 실측 강등 규칙(A-2·I-1)은 과잉교정 가드다. 반복 남발이 아니면 보존이 기본값
- C-8 전멸 게이트: 원문의 수사 구조(대구 5회 이상)를 윤문이 0으로 만들면 FAIL — 필자 목소리 보호
- taxonomy는 SSOT 유지, 생성물(quick-rules·diagnosis-rules)은 직접 편집 금지

## 7.0.0 (2026-07-19) 7차 고도화: "번역 충실성·문학 번역 검토 레인"

깃허브 benchmark, WMT·SemEval·COLING 논문, 한국어 번역 연구, 번역 서비스 평가와 데보라 스미스 인터뷰·비평을 v6 윤문 워크플로에 연결했다.

**핵심 변경**

- `scripts/translation_audit.py` 추가: 원문–번역문 사이의 숫자·URL·코드·약어·링크 대상 표면 잠금, 제목·불릿·표·코드 구조 대조, 번역투·주어 복원·강도 부사 위험 플래그
- `korean_writing.py translation-audit` 명령 추가 및 `tests/test_translation_audit.py` 회귀 테스트 추가
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
- 기존 `korean_writing.py`, `patterns.json`, `examples.md`를 v6 규칙과 맞춤

**보존 원칙**

- 원문 사실·숫자·인용·화자·불확실성은 계속 LOCK 대상으로 유지
- 새 규칙은 원문에 없는 감정·사례·주장을 만들지 않으며, 수치 게이트를 통과하지 못하면 윤문을 중단하고 검토를 요구

## 5.0.0 (2026-07-10) 5차 고도화: "규칙·구현·평가의 일치"

외부 코드 리뷰의 P0 다섯 건과 품질 제안을 반영했다.

**P0 수정**

- README가 중간에 잘린 채 배포되던 문제 수정(파일 동기화 사고), 설치 안내를 실제 배포 파일(dist/)과 일치시킴
- Sunny-7이 코드에는 6규칙만 구현돼 있던 불일치 해소: 7번(어색한 있다) 분리 구현
- SKILL.md의 A~N 14패턴과 탐지 코드의 불일치 해소: scripts/patterns.json을 단일 원천으로 통합, `korean_writing.py taxonomy --check`로 무결성 검사
- references/examples.md의 M 예시가 원문에 없던 사실("3년 뒤 재정 부담")을 추가하던 LOCK 위반 교체

**신규**

- LOCK 이원화: 표면 잠금(기계 검증) + 의미 동등성 검토(부정·가능성·인과·구조 요소 경고 휴리스틱). "의미·사실 100% 보존" 표현을 정확한 문구로 교체
- 진단 출력 5범주 분리: 문법 오류 / AI 문체 후보 / 장르 부적합 후보 / 구조 문제 / 작성자 문체 보존 경고
- 프로파일 완화를 코드에 반영: 공문서(B), SNS(I 이모지), 기술문서(E 서식)를 `diagnose --profile`로 지원
- 파일 직접 수정 안전 흐름: 진단 → diff 미리보기 → 사용자 승인 → 반영, 원본 .bak 백업
- diffrate에 문장 단위 변경률 추가(재배열·재작성 감지 보강)
- 전 명령 `--json` 출력 지원
- tests/ 회귀 테스트 15건 + GitHub Actions CI
- ROADMAP.md: 말뭉치 보정, 구조 기반 장문 분할, 형태소 분석 선택 의존성, korean-writing 분리, 배포 체계
- dist/korean-writing-polish.skill을 저장소에 동봉

## 4.0.1 (2026-07-10)

- README 전면 윤문: em-dash·볼드 라벨 등 부호·서식 티를 스킬 자신의 기준(거시 D·E 패턴)으로 걷어내고 산문 중심으로 재작성
- korean-writing 5단계 글쓰기 스킬 동봉 (korean-writing/SKILL.md)

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

- scripts/ 7개 스크립트가 배포본에서 유실돼 정량 게이트가 전부 건너뛰기로 동작하던 문제를 korean_writing.py 단일 도구(diagnose/sunny/preserve/diffrate/consistency/format)로 복원. 표준 라이브러리만 사용
- 검증: AI 티 샘플 지수 58.0(D) → 윤문 후 0.0(A), 숫자 변조 시 보존 게이트 exit 1 확인

## 3.x — 3차 고도화

- 일반·최강·장편(8,000자 이상) 통합. 장편은 섹션 분할 2패스 리라이팅·통합 윤문
- 정량 진단(AI 흔적 지수 전/후)·보존 검증 게이트를 최강 윤문에 도입
- .hwp/.hwpx kordoc 입출력(변환·서식 보존 패치·공문서 생성), SNS 요약, docx 변환
- 외부 문서(PDF·HWP) 숨김 지시문 안전 메모

## 2.x — 2차 고도화

- 2계층 모델 정립: 거시 A~J 패턴 +
