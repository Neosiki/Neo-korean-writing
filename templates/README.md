# 작업 템플릿

템플릿은 한글 글쓰기(윤문) 작업의 요청, 보존 검수, 결과 전달을 같은 형식으로 남기기 위한 문서입니다. 특정 AI 도구에 종속되지 않으며, 사람이 직접 편집하는 작업에도 사용할 수 있습니다.

| 단계 | 파일 | 목적 |
|---|---|---|
| 시작 | [`editing-brief.md`](editing-brief.md) | 목적·독자·장르·허용 변경 범위·원하는 납품물을 정리합니다. |
| 윤문 전후 검수 | [`lock-register.md`](lock-register.md) | 사실·수치·인용·링크·표 등 바뀌면 안 되는 정보를 LOCK으로 관리합니다. |
| 번역 용어집 | [`translation-glossary.tsv`](translation-glossary.tsv) | 번역 감사의 `--glossary`에 넣는 원어·역어·금지 역어 목록입니다. |
| 분야별 용어집 | [`translation-glossary-scoped.json`](translation-glossary-scoped.json) | 같은 원어의 뜻을 domains·segments로 나눠 선택하는 예시입니다. |
| 결과 검토 | [`editing-delivery.md`](editing-delivery.md) | 윤문본, 변경 근거, 보존 확인, 미확정 항목과 승인 상태를 함께 전달합니다. |

## 권장 순서

1. `editing-brief.md`에 독자와 목적, 장르, 윤문 강도를 적습니다.
2. 원고에서 보호해야 할 정보를 찾아 `lock-register.md`에 기록합니다.
3. 상황에 맞는 [`../prompts/`](../prompts/README.md) 프롬프트로 초안 또는 윤문본을 만듭니다.
4. `editing-delivery.md`에 수정 이유와 확인이 필요한 항목을 남기고 최종 승인자가 검토합니다.

> 템플릿의 빈 칸은 AI가 추정해 채우는 정보가 아닙니다. 확인할 수 없다면 `미정` 또는 `[확인 필요]`로 유지해야 합니다.
# 문서 간 맥락 감사 추가

번역을 파일로 이어갈 때는 `writer-editor-handoff.json`에 `translation-session`이 선택적 진행 기록을 추가한다. 원문·용어집·초안이 바뀌면 재검토할 단계를 표시한다. delivery의 copy는 납품 본문만, review는 별도 검토 보고를 포함한다. [실행 방법](../references/translation-continuation.md)을 참고한다.

- `context-manifest.json`: 대상·참조 문서, 권장 용어, 개체 별칭, 시점과 근거가 있는 주장. 예시 경로·가상 데이터는 실제 작업 자료로 바꾼다.
