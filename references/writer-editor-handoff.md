# Writer–Editor 인계 계약

새 글 작성과 윤문 사이에서 작성 의도와 근거를 잃지 않기 위한 JSON 계약이다. 새 글의 초안이 끝나면 `templates/writer-editor-handoff.json`을 채우고, 윤문 전 `handoff-validate`로 검사한다.

## 필드

- `context`: 장르, 채널, 독자, 글의 목적. 편집 강도를 결정한다.
- `voice`: `preserve`가 기본이다. `yoon-reporter`, `professional`, `warm`, `blunt`, `technical`은 명시 선택일 때만 쓴다.
- `intentional_devices`: 의도적 반복, 반문, 파편문, 열린 결말처럼 진단기가 지우면 안 되는 장치를 적는다.
- `provenance.sourced_claims`: 주장과 출처를 묶는다. 출처가 없는 구체적 수치나 사례를 편집기가 만들어서는 안 된다.
- `author_interpretations`: 출처 사실과 구분해야 할 글쓴이의 해석이다.
- `unresolved`: 확인 전까지 단정하면 안 되는 항목이다.
- `locks`: 숫자, 명칭, 직접 인용, URL, 기술 용어, 구조 보호 항목이다.
- `editorial`: 구조 변경 권한과 변경 예산을 기록한다.

## 운영 규칙

인계 계약은 원고를 대신하지 않는다. 편집기는 `intentional_devices`를 무조건 보존하는 대신 문맥상 실제로 작동하는지 판단하고, 수정이 필요하면 자동 삭제하지 말고 보류 항목으로 보고한다. `unresolved`의 빈칸은 추측으로 채우지 않는다.
