# 10월 번역 고도화 v10.7: 링크·구간 재검토·독자 질문

세 기능은 서로 다른 문제를 검사한다. 기계 상태, 의미 대조, 독자 응답을 하나의 “번역 정확도”로 합산하지 않는다. 추가 API·모델 설치 없이 현재 에이전트와 표준 라이브러리로 사용할 수 있다.

## 번역 후 링크

`translation-audit`는 Markdown 인라인·참조형 링크와 이미지의 목적지를 추출한다. 같은 문서 안의 fragment는 ATX/setext 제목과 HTML `id`/`a name`에 대조한다. 순서·단계가 같은 제목끼리의 앵커 변경을 허용하고 `allowed_changes`에 근거를 남긴다. 이것은 제목의 의미가 같은지 판정하는 기능이 아니다. 제목을 이동·병합했다면 명시적 매핑과 사람 검토가 필요하다.

```text
python scripts/korean_writing.py translation-audit source.md target.md --json
python scripts/korean_writing.py translation-audit source.md ko/target.md --link-root . --link-map link-map.json --json
```

`link-map.json` 예: `{"intro.md#guide": "ko/intro.md#안내", "images/a.png": "ko/images/a.png"}`.
현재 디렉터리가 아니라 `--link-root` 아래에서만 링크 파일을 읽는다. target 파일도 root 안에 있어야 한다. root 밖으로 나가는 경로·심볼릭 링크는 거부한다. 상대 파일·이미지의 존재, 연결된 Markdown 파일의 fragment를 확인한다. 외부 URL은 네트워크로 열지 않으며 변경 잠금을 유지한다. 외부 URL을 매핑으로 예외 처리할 수 없다.

`LINK-1`은 존재하지 않는 앵커·파일 등의 기계적 보류다. `checked`·`unchecked`로 검사 범위를 밝힌다. root를 주지 않은 상대 파일, 외부 URL, 비 Markdown 파일 내부 fragment는 미검사다. HTML의 href 보호는 기존 형식 검사대로 유지되며 Markdown과 섞인 HTML 앵커도 링크 검사에 사용한다. ICU·XML은 이 레인의 대상이 아니다.

GFM의 기본 제목 규칙(소문자, 공백, 서식 제거, 중복 접미사)을 적용한다. 모든 Markdown 확장·자동 생성 목차·수식·MDX·사이트별 slug 플러그인과 브라우저 렌더링을 보증하지 않는다. 정규 표현식 한 번으로 대괄호 링크를 추출하던 방식을 바꾸되 완전한 CommonMark 파서를 구현했다고 주장하지 않는다.

## 용어 변경의 구간별 영향

`templates/translation-segments.json`에 실제 원문·번역 구간을 명시한다. 구간 파일을 별도로 둘 수 있고, 한 파일 안에서는 `source_paragraph`·`target_paragraph`로 빈 줄 기준 1부터 시작하는 문단 번호를 선택할 수 있다. 문단 대응은 사람이 정한다. 문단 개수가 같다고 자동으로 의미 대응을 확정하지 않는다.

```text
python scripts/korean_writing.py translation-impact snapshot segments.json --output baseline.json
python scripts/korean_writing.py translation-impact plan segments.json --baseline baseline.json --json
```

snapshot은 현재 파일·관련 용어의 기준 기록이며 검수·승인이 아니다. 기존 파일을 덮어쓰지 않는다. 계획 명령은 읽기 전용이며 번역·파일 수정·자동 재승인을 하지 않는다.

- 명시한 분야·구간으로 선택된 용어가 해당 원문에 등장하는지 기록한다. 이것은 관련 용어 목록이며 모델이 실제 사용했다고 입증한 기록이 아니다.
- 원문·번역·경로·문단 선택·분야·의존성·관련 용어가 바뀐 구간을 추린다. 새로 추가되거나 삭제된 용어도 검사한다. 미사용 용어 변경만으로 모든 구간을 무효화하지 않는다.
- 직접 변경된 구간의 앞뒤 구간은 접경 문맥 검토에 넣는다. 인접 확장을 다시 인접 확장해 문서 전체로 번지게 하지는 않는다.
- `depends_on`으로 명시한 의존성은 전이적으로 반영한다. 인물 별칭·정의·먼 곳의 지시 대상 등은 독자가 의존 구간을 등록해야 한다. 자동 의미 의존 그래프가 아니다.
- 기록 없는 구간, 번역 누락·빈 번역, 용어 범위 미정은 유지로 처리하지 않는다. 삭제·재정렬도 보고한다.

수정된 문단은 기존 윤문·의미 대조를 다시 수행하고, 변하지 않은 승인 문단은 보존한다. 단순한 용어 검색으로 모든 생략·지시 관계를 찾았다고 하지 않는다. 선택한 문단 번호가 삽입으로 밀리면 해시 변경을 통해 재검토하지만 논리적인 구간 ID를 자동 복원하지는 않는다.

## 독자 질문: 번역문만으로 이해되는가

`prompts/translation-reader-review.md`를 사용한다. 의미 감사는 원문과 번역을 함께 비교하고, 이 검토는 번역문과 질문만으로 읽을 수 있는지 살핀다. 짧은 문자·한 문단에 이 절차를 강제하지 않는다. 원고의 목적과 독자에 필요한 질문만 선택한다.

```text
python scripts/korean_writing.py translation-reader packet target.md --questions questions.json --output reader-packet.json
python scripts/korean_writing.py translation-reader check target.md --report reader-report.json --json
python scripts/korean_writing.py translation-audit source.md target.md --reader-review reader-report.json --require-reader-review --json
```

`questions.json`은 `[{"id":"condition","question":"어떤 조건을 충족해야 다음 단계로 진행하나요?"}]` 형식이다. 패킷에는 원문·정답이 없고 현재 번역과 질문, 빈 보고서 틀만 있다. CLI는 모델을 호출하거나 질문에 자동으로 답하지 않는다. 현재 에이전트 또는 사람이 실제 읽고 보고서를 작성해야 한다.

각 응답은 `id`, `status`, `answer`, `evidence`(번역문에 실제 있는 구절 배열), `reason`을 갖는다. 상태는 `answered`, `ambiguous`, `missing`, `out_of_scope`다. 답한 경우 근거를 요구한다. 질문을 문서가 답할 필요가 없는 경우와 설명이 부족한 경우를 구분한다. 전체가 범위 밖이면 필요한 질문을 정하지 못한 상태로 처리한다.

`reader`에는 `kind`(human/model), `name`, `context`(fresh/author_context), `independent`를 기록한다. 작성 대화나 원문을 이미 본 현재 모델은 `author_context / false`다. 다른 역할 이름만 붙여 독립 독자로 바꾸지 않는다. 독립성은 선언 기록이지 도구가 증명한 사실이 아니다. 독립 검토가 실제 제공되었을 때만 fresh로 기록하고 연결한다.

`responses_recorded`는 모든 질문의 응답이 기록됐다는 뜻이다. `reviewed_with_gaps`, `partial`, `no_in_scope_answers`, `stale`을 별도로 표시한다. 번역이 바뀐 보고서는 재사용하지 않는다. `--require-reader-review`는 누락·부분·검토 공백을 보류하며, READ 항목은 MQM 휴리스틱 점수에 합산하지 않는다.

근거가 문서에 있다는 것만으로 답의 논리적 정확성을 검증할 수 없다. 응답이 질문에 맞는지 실제 독자/편집자가 확인한다. 정보 부족이 원문에도 있으면 번역을 고쳐 꾸며내지 말고 원문 문제로 보고한다. 독자 질문 기록은 원문 전체 대조·분야 전문가 검수·출판 승인을 대체하지 않는다.

## 적용 근거

새 코드·예문은 별도로 작성했다. 외부 코드나 번역 본문을 복사하지 않았다.

- [GitHub의 제목·상대 링크·사용자 앵커 규칙](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax): 기본 앵커 규칙의 근거.
- [Anthropic doc-coauthoring](https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/doc-coauthoring/SKILL.md): 작성 맥락 없이 독자가 질문에 답하도록 하는 검토 방식.
- [translate-book 구간 기록](https://github.com/deusyu/translate-book/blob/a663b1b4f1e625b286cd2a81dffd16571e6f2aa2/scripts/run_state.py): 구간·용어 변경의 영향만 다시 검토하는 발상.
- [Co-op Translator 링크 검사](https://github.com/Azure/co-op-translator/blob/298323f650836fe90cb754297627b28a39c4eab0/src/co_op_translator/review/checks/links.py): 실제 상대 경로 검사의 비교 자료. 이 구현이 건너뛰는 문서 내부 fragment는 이번에 별도로 검사했다.

[회귀·사용 검증 기록](../benchmarks/october-upgrade.md)을 함께 확인한다.

