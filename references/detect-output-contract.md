# Detect 2.0 출력 계약

진단은 AI 작성 여부를 판정하지 않는다. 편집 후보를 재현 가능하게 전달한다.

각 finding은 `id`, `layer`, `severity`, `location`, `span`, `assessment`, `reason`, `keep_if`, `action`, `context`를 포함한다.

- `layer`: `authorship_signal`, `clarity`, `structure`, `rhythm`, `reasoning`, `context` 중 하나다.
- `assessment`: 바로 고칠 명백한 문제는 `clear`, 장르에 따라 판단할 항목은 `contextual` 또는 `judgment_call`이다.
- `location`: 1부터 시작하는 행·문단과 원문 문자 오프셋을 기록한다.
- `span`: 원문에서 실제로 탐지된 문자열이다. 범주만 보고하지 않는다.
- `keep_if`: 유지 조건을 먼저 보여 과잉교정을 막는다.
- `action`: `revise`, `verify`, `keep` 중 하나다.

사용자용 보고에서는 `clear`를 먼저, 판단 항목을 뒤에 배치한다. “사람 글”, “AI 글” 같은 저자 판정은 출력하지 않는다. 지수는 경로 선택용 편집 신호 밀도로만 해석한다.
