# korean-humanize 아티팩트 연구 논문

**한국어 윤문 스킬의 규칙 추적성과 의미 보존 검증**
— Neosiki/korean-humanize v5.0.0에 대한 아티팩트 연구 (작성 기준일 2026-07-17)

## 파일 구성

| 파일 | 내용 |
|---|---|
| `korean-humanize_paper.md` | 논문 전문(마크다운, 부록 A~J 포함) |
| `korean-humanize_최종논문_본실험실행본.docx` | 논문 전문(Word) |
| `benchmark/run_benchmark.py` | 본실험 실행 스크립트(앵커·변형·통제문 전체 수록) |
| `benchmark/korean-humanize_run_log.csv` | 167쌍 사례별 실행 로그 |
| `benchmark/korean-humanize_results_filled.csv` | 변형 유형별 집계 |
| `benchmark/korean-humanize_run_summary.json` | 실행 요약 통계 |

## 핵심 결과 (커밋 ce02da2, 실행일 2026-07-17)

- KLUE NLI/STS/YNAT 앵커 49건 → 단일 위험 변형 118건 + 문체 통제 49건 실행
- 자동 보존 검사: 숫자 17/17 포착(100%), 영문 용어 4/5(80%), 문체 통제 과잉 경고 0%
- 부정·양태·인과·논항·비교·조건 변형 96건 전원 무신호 → **검사 단위 불일치**(문서 밀도 가드 vs 문장 변형)가 핵심 발견

## 판정 방식 주의

의미 변화 판정은 **LLM(Claude) 모의 판정**(번역 전문가 페르소나 2종)이며 **독립 인간 평가가 아닙니다**.
모의 판정 수치(의미 변경 114건, 유보 4건, 무신호 의미 변경률 81.6%)는 잠정 참조값으로,
투고 전 두 명 이상의 독립 한국어 평가자 판정으로 대체되어야 합니다. 상세는 논문 3.7절·부록 J 참조.

## 재현

```bash
python benchmark/run_benchmark.py   # krh.py(ce02da2) 경로를 scripts/에 맞춰 조정
```

원문 텍스트는 KLUE 공개 자료(CC BY-SA 4.0 표시)에서 행 ID로 추출하며, 이 저장소에는 재배포하지 않습니다.
