# 윤문 프롬프트 모음

이 디렉터리는 대화형 AI에 원고를 전달할 때 사용할 수 있는 **검증 우선 윤문 프롬프트**를 제공합니다. 프롬프트는 원고를 대체하는 지시문이 아니라, 사실·인용·수치·화자성을 먼저 보호한 뒤 필요한 문장만 다듬기 위한 작업 계약입니다.

## 시작 전 준비

먼저 [`../templates/editing-brief.md`](../templates/editing-brief.md)를 복사해 목적, 독자, 장르, 허용 변경 범위와 확인이 필요한 사실을 적습니다. 숫자, 날짜, 고유명사, 직접 인용, URL, 표·목록 항목은 [`../templates/lock-register.md`](../templates/lock-register.md)에 LOCK 항목으로 기록하는 편이 안전합니다.

| 상황 | 권장 파일 | 주요 결과 |
|---|---|---|
| 일반 원고의 문체·호흡 개선 | [`standard-editing.md`](standard-editing.md) | 윤문본, 변경 요약, 보존 확인 |
| 보도자료·공식 안내문 | [`press-release-editing.md`](press-release-editing.md) | 격식 유지 윤문본, 확인 필요 항목 |
| 긴 보고서·칼럼·강의 원고 | [`longform-editing.md`](longform-editing.md) | 섹션별 윤문 계획, 일관성 점검표 |
| 번역문 후편집 | [`translation-postediting.md`](translation-postediting.md) | 수정본, 의미 보존 위험, 원문 대조 기록 |

## 공통 원칙

> **원문에 없는 경험·사실·감정·인용·수치를 만들지 않습니다.** 확인할 수 없는 내용은 더 그럴듯하게 쓰지 말고 `[확인 필요]`로 남깁니다.

최종 결과를 채택하기 전에는 `scripts/korean_writing.py preserve`, `diffrate`, `consistency`를 이용해 원문과 수정본을 대조할 수 있습니다. 전달본은 [`../templates/editing-delivery.md`](../templates/editing-delivery.md)의 형식으로 원고·변경 요약·미확정 항목을 함께 남기는 것을 권장합니다.

## 사용 방법

각 파일의 `{{중괄호}}` 항목을 실제 정보로 바꾼 뒤, 지시문과 원고를 함께 전달합니다. 원고가 길면 섹션별로 나누되, 전체 목적·독자·LOCK 목록은 모든 요청에 반복해 포함합니다. AI가 사실을 확인할 수 없는 경우에는 확정 표현을 추가하지 않고, 사용자 또는 편집자의 검토 대상으로 분리합니다.
