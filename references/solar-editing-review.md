# Solar 보조 교정과 최종본 대조 — v10.8

Solar 요청, 교차 검토가 필요한 원고, 최종 수정 내역 검수에서 읽는다. 기본 로컬 검사에는 모델·네트워크·키가 필요 없다.

## 검사와 판정 범위

`editing-audit`는 `preserve`의 보호 구간·숫자·잔존 패턴과 새 후보를 모은다. `verify_gates.py`에도 P6 보존 통합을 연결해 코드·반복 숫자 손상이나 말투 전환을 다른 축의 통과로 덮지 않는다. 기존 목표 달성·분량·리듬 검사는 계속 함께 확인한다.

- `EDIT-REGISTER`: 인용·코드·제목·표를 뺀 본문의 한다체·해요체·합쇼체·음슴체를 비교한다. 양쪽 모두 분류 문장 3개 이상, 우세 문체 비율 80% 이상일 때 전환을 검토 보류한다. 짧거나 혼합된 글은 `insufficient_or_mixed`이며 어체를 강제하지 않는다.
- `EDIT-NEGATION`: 유사 대응 문장의 부정 표지 변화를 위치와 함께 보고한다. 같은 뜻의 부정 표현 교체를 오류로 확정하지 않는다.
- `EDIT-BINDING`: 'A매장의 매출은 100만 원' 같은 명시한 개체–항목–값·단위 변화를 보고한다. 동일 개체·항목이 양쪽에 한 번씩 있을 때만 대응한다. 여러 시점·복수 값·대명사·생략은 임의 정렬하지 않으며 놓치는 경우가 있다.
- `EDIT-CONTENT`: 쉽게 대응되지 않는 문장에 새 낱말이 다수 나타나면 검토 후보로 둔다. 유의어·활용형은 사실 추가로 확정하지 않는다. `new_terms`는 관찰 목록이며 그 자체로 차단하지 않는다.

`pass`는 실행한 검사에서 이상 후보를 못 찾음, `review`는 대조 필요, `hold`는 보존 손상·분명한 문체 전환 후보·오래된 증적 때문에 자동 채택 보류다. 기계 통과를 의미 정확성 인증으로 쓰지 않는다. 사용자가 말투 변경 자체를 요청했다면 별도 개작으로 구분하고 원래 말투 보존을 달성했다고 보고하지 않는다.

## 최종본과 교정 내역

파일 기반 납품이나 실제 수정 내역 검수 요청에 사용한다. 짧은 대화형 윤문마다 파일을 만들지는 않는다.

```sh
python scripts/korean_writing.py editing-audit original.md final.md --json
python scripts/editing_audit.py original.md final.md --delivery-template delivery.json --json
# 각 실제 diff에 편집자가 확인한 reason을 채운다.
python scripts/editing_audit.py original.md final.md --delivery delivery.json --json
```

설치형 CLI는 `neo-korean-writing editing-audit`다. 템플릿은 기존 파일을 덮어쓰지 않는다. 원문과 최종본의 LF 정규화 SHA-256, 실제 문자 diff·위치가 맞고 이유가 비어 있지 않을 때 `verified`다. 이유의 타당성을 인증하지 않는다.
원고가 바뀌면 `stale`, 실제 diff와 기록이 다르면 `mismatch`로 보류한다. 이유가 비면 `needs_reasons`, 기록이 없으면 `not_checked`다. 되돌린 제안은 적용 내역에서 분리한다. 최종 변경 0건이면 유지했다고 보고하며 수정·가독성 개선을 만들지 않는다.

## 실제 의미 검토 연결

[기존 의미 검토 계약](translation-semantic-review.md)의 source/target을 원문/윤문본으로 삼아 실제 명제 대조 기록을 연결할 수 있다.

```sh
python scripts/editing_audit.py original.md final.md --semantic-review review.json --require-semantic-review --json
```

실제 검토 전에는 `not_checked`를 유지한다. 검토자가 주체·부정·양태·인과·범위·귀속을 실제 대조하고 해시·근거를 채운다. 전체 범위를 못 읽거나 증적이 오래됐으면 완료로 쓰지 않는다. 검사 통과 수나 점수 평균으로 채택하지 않는다.

## 선택형 Solar 경로

연결된 `human-proofreader`가 실제 제공되고 사용자가 요청했거나 작업 범위에서 외부 교정이 필요한 경우에만 쓴다. 원고의 외부 전송 허용 범위와 API 비용 조건을 지킨다. 키를 원고·도구 인자·기록·GitHub에 넣지 않는다. 없는 MCP를 필수 의존성으로 요구하거나 임의 설치하지 않는다.

1. 원문·작성 의도·LOCK·원하는 말투를 네오에서 정한다.
2. 진단은 `read_through`, 교정은 `proofread`, 짧은 대안은 `suggest`를 선택한다. 강도와 깊이는 별개다. 보수·light를 먼저 검토하고 실제 위험도에 맞춘다.
3. `preserve`에 실제 보호 문장을 넣는다. 외부 도구의 2만 자 한도를 지키되 장문 문맥·재조립은 네오 계약을 따른다.
4. Solar의 원고 대조 결과도 함께 확인한다. 채택 불가 응답은 납품본으로 쓰지 않는다. 통과 표시는 기계 검사 범위로 한정해 해석한다.
5. Solar 결과를 원문과 네오 `verify_gates`·`editing-audit`로 다시 대조한다. 후보는 실제 문맥에서 확인한다. 자동 보정은 최대 1회로 제한하고 남은 문제는 보고한다.
6. 최종본 확정 뒤 실제 diff에서 수정 내역을 생성한다. Solar 중간 교정 노트를 그대로 복사하지 않는다.

선택적 `--solar-record solar-usage.json`은 아래 필드만 받는다. 실제 원문/최종본 해시와 응답에서 확인한 제공자·모델을 넣는다.

```json
{"schema_version":1,"original_sha256":"실제 SHA-256","final_sha256":"실제 SHA-256","provider":"응답의 제공자","model":"응답의 모델","calls":null,"tokens":null}
```

호출·토큰이 확인되면 음이 아닌 정수, 안 나오면 null이다. 미확인을 0으로 쓰지 않는다. standard도 보정 때문에 3회가 될 수 있다. 키·헤더·원시 응답 같은 추가 필드는 거부하며 다른 버전의 기록은 stale로 보류한다. 응답 메타데이터 기록은 호출·청구 인증이 아니다.

## 채택하지 않은 처방과 근거

일률적인 접속사·헤지 삭제, 새 내용어에 따른 즉시 차단, 가독성 점수로 정확성 판정은 도입하지 않았다. 원문 불확실성과 네오의 유지 조건을 우선한다.
2026-10-27 가상 예문 9쌍의 compare와 실제 교정 1건에서 정상 유의어 오탐, 부정·수치 귀속·코드 변경 미검출, 최종본과 중간 노트 불일치를 확인했다. 독립 품질 순위가 아닌 개발 회귀의 출발점이다.
참고: [Solar 대조 구현](https://github.com/SolarLLM/human-proofreader-mcp/blob/main/lib/fidelity.ts), 파일 SHA `acc99c6997d69bb3fb5281645f206bb0fa487909`; [처리 흐름](https://github.com/SolarLLM/human-proofreader-mcp/blob/main/lib/pipeline.ts), SHA `2d98debcee96af576944c54452edbbfe10519e93`.
새 코드는 별도 구현했으며 Solar 소스나 모델을 내장하지 않았다. MCP가 없어도 로컬 검사는 작동한다.
