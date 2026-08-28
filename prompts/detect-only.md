# 위치 기반 진단 전용 프롬프트

```text
다음 한국어 원고를 수정하지 말고 진단만 한다.

1. 각 finding에 실제 원문 span, 행·문단 위치, layer, 심각도, 이유, 유지 조건, 권고 조치를 적는다.
2. 명백한 문제(clear)와 문맥 판단(contextual/judgment_call)을 분리한다.
3. AI 작성 여부를 판정하거나 “사람 글”이라고 인증하지 않는다.
4. 인용·코드·YAML·표·URL·각주의 예시는 저자 문체 신호에서 제외한다.
5. 장르 context와 필자 voice를 구분한다.
6. 가장 중요한 5건을 먼저 보여주고, 같은 문장에 겹친 신호는 한 편집 대상으로 묶는다.

[context]
{{column | article | press | official | technical | blog | sns | email}}

[원고]
{{원고}}
```
