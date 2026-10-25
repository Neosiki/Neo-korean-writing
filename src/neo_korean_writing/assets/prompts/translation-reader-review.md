# 번역문 독자 이해 검토

대상 독자와 문서 목적에 필요한 질문을 고른다. 문서가 다루지 않는 일을 억지로 묻지 않는다. 간단한 단문에는 별도 파일을 강제하지 않는다.

1. 파일 작업이면 translation-reader packet으로 번역문·질문·현재 해시가 담긴 패킷을 만든다. 질문에 정답·원문·작성 과정의 힌트를 넣지 않는다.
2. 실제로 번역문을 읽고 질문에 답한다. 인물·조건·순서·지시 대상을 찾을 수 있는지 살피고 문서의 짧은 근거 구절을 적는다. 없는 정보는 추측하지 않는다.
3. 답할 수 있으면 answered, 해석이 갈리면 ambiguous, 필요한 설명이 없으면 missing, 문서 범위 밖의 질문이면 out_of_scope로 기록한다. 두려움·감동·긴장 같은 독자의 반응을 지어내지 않는다.
4. 현재 작성 대화 또는 원문을 이미 보았다면 reader.context=author_context, independent=false로 밝힌다. 역할을 바꿔 부르는 것만으로 독립 검토라고 하지 않는다. 실제 별도 독자의 결과가 주어진 경우만 그 독자와 범위를 기록한다. 이 프롬프트 자체가 외부 전송·새 세션·서브에이전트 생성을 승인하지 않는다.
5. packet의 report_template을 별도 JSON에 채운다. summary에 실제 읽은 범위와 질문 수, 남은 공백을 적는다. 답마다 id/status/answer/evidence/reason을 기록한다. answered에는 번역문에서 찾은 evidence가 필요하다.
6. translation-reader check 또는 translation-audit --reader-review로 현재 원고와 근거를 묶는다. 도구는 답의 진위를 평가하지 않는다. responses_recorded를 이해도 합격 점수로 쓰지 않는다.
7. 문제를 고치기 전 원문에도 정보가 있는지 대조한다. 원문에 없는 이유·설명·주체를 만들지 않는다. 필요한 구간만 수정한 후 질문과 의미 대조를 다시 한다. 본문이 바뀌면 이전 해시의 보고서를 재사용하지 않는다.

최종 납품 본문은 깨끗하게 제공하고 질문·응답·문맥·검사 상태는 별도 보고서에 보관한다. 정책과 CLI 예시는 references/october-translation-upgrade.md를 따른다.

