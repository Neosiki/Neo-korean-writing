# 의미 검토 연결 — 점검기 9.8

기계 검사는 숫자·태그·일부 표현을 비교한다. 원문 명제의 주체·범위·귀속을 전부 해석하지 않는다. 이 레인은 현재 글쓰기 에이전트 또는 사람이 실제 대조한 결과를 파일에 묶는다. Python CLI 자체가 LLM을 자동 호출하는 기능은 아니다. 새 API·모델 다운로드 없이 스킬을 읽는 에이전트가 `prompts/translation-semantic-review.md`를 실행할 수 있다.

## 파일 작업

```sh
python scripts/translation_audit.py source.md target.md --semantic-packet packet.json --json
# 현재 언어모델/검토자가 packet의 원문·번역문을 읽고 report_template을 review.json으로 채운 뒤:
python scripts/translation_audit.py source.md target.md --semantic-review review.json --require-semantic-review --json
```

설치형 CLI `neo-korean-writing translation-audit`에도 같은 옵션이 있다. packet은 입력 두 파일의 전체 텍스트와 해시를 로컬 JSON에 담는다. 기존 packet 파일은 덮어쓰지 않는다. 보고서 틀의 빈 이름·summary·검토 차원은 실제 검토 뒤 채워야 한다. 틀 내보내기는 모델 검토 실행이 아니다.

보고서 형식:

```json
{
  "schema_version": 1,
  "source_sha256": "packet에 제공된 해시",
  "target_sha256": "packet에 제공된 해시",
  "reviewer": {"kind": "model", "name": "실제 사용한 모델/세션", "independent": false},
  "coverage": "full_pair",
  "dimensions_reviewed": ["modality", "actor", "quantifier", "negation", "causality", "attribution"],
  "summary": "실제로 대조한 범위와 판단",
  "findings": [
    {"dimension": "modality", "source_quote": "원문에 있는 구절", "target_quote": "번역문에 있는 구절", "reason": "의미가 달라진 이유"}
  ]
}
```

이 JSON은 설명용이며 해시·인용을 실제 입력으로 바꿔야 한다. 발견 사항이 없으면 findings=[]로 둔다. 일부만 읽으면 coverage=selected_spans이고 차원도 실제 확인한 것만 기록한다. 모델 이름·독립성은 보고자의 선언이지 코드가 인증하는 사실이 아니다. 같은 작성자·같은 세션 검토를 독립 심사로 쓰지 않는다.

## 상태와 적용

| 상태 | 뜻 |
|---|---|
| not_checked | 의미 검토 보고서가 연결되지 않음 |
| partial | 일부 범위 또는 일부 차원만 검토 |
| stale | 원문/번역문 해시가 보고서와 달라 재사용 불가 |
| reviewed_with_findings | 전체·6개 차원을 검토했다고 보고했으며 후보가 있음 |
| reviewed_no_findings | 같은 범위를 검토했다고 보고했으며 후보를 못 찾음 |

`mechanical_status`는 원래 기계 검사 결과다. `semantic_review`는 별도 검토 상태와 판단 주체·근거를 담는다. 전체 `status`에는 연결된 후보도 반영한다. `--require-semantic-review`는 미검토·부분 검토를 보류한다. stale은 옵션과 무관하게 보류하며 이전 findings를 채택하지 않는다. 잘못된 JSON·근거·형식은 입력 오류 3으로 종료한다.

모델/사람의 후보는 SEM-1~6, 범위·버전 미확인은 SEM-0이다. 모델 판단을 기계가 확정한 오류로 표기하지 않는다. SEM은 기존 MQM 휴리스틱 점수에 합산하지 않는다. --strict를 쓰면 주요 후보에서 보류하지만 후보가 진짜 오류인지 최종 판단하는 책임을 대신하지 않는다. 기존 status=pass만으로 의미 검토 완료를 주장하지 않는다.

보고서는 UTF-8 텍스트의 줄바꿈을 LF로 정규화한 SHA-256에 묶이며, 근거 구절도 현재 입력에서 확인한다. 파일이 바뀌면 새로 대조해야 한다. 인용이 여러 곳에 반복되면 관계를 해석하는 일은 검토자에게 남는다. 검토 내용의 진실성·완전성을 해시 검사로 인증할 수는 없다.

## 이번 재시도의 근거

[의미 재검토 기록](../benchmarks/semantic-retry.md)은 원래 6개 오류, 새 오류 6개, 정상·반례 18개를 다룬다. 현재 세션 모델이 직접 쓴 판정과 이유를 보존했다. 평가 스크립트는 그 기록을 연결·재현하며 새 추론이나 외부 API 호출을 하지 않는다. 같은 세션이 사례 작성과 검토를 함께 했고 라벨도 가리지 않았으므로 독립 정확도·일반화 성능이 아니다.
