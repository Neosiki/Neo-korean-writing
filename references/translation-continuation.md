# 번역·감수·윤문을 이어가는 방법

반복되는 파일 작업이나 긴 번역에서 사용한다. 짧은 번역에는 이 절차를 강제하지 않는다. 목표 품질과 편집 강도는 별개다. 중요 문서는 충실하게 검토하되 잘 옮긴 문장을 불필요하게 다시 쓰지 않는다.

## 기존 인계서에 기록

작업 폴더에서 독자·장르·보존 정책을 채운 `templates/writer-editor-handoff.json`을 인계서로 사용한다. helper는 명시된 인계서만 수정하며 `translation_workflow` 필드를 추가한다. 다른 문서·설정을 찾아 선호를 추정하지 않는다. 기존 context·voice·locks·provenance·editorial·delivery 필드는 유지한다.

아래 명령은 작업 폴더에서 실행하는 예시다. `scripts/translation_session.py`는 설치된 스킬 또는 저장소 안의 실제 경로로 바꾼다. 설치형 CLI에서는 `neo-korean-writing translation-session` 뒤에 같은 인자를 쓴다.

```sh
python /path/to/skill/scripts/translation_session.py init handoff.json --source source.md --glossary terms.tsv --domain finance --format plain
python /path/to/skill/scripts/translation_session.py inspect handoff.json --json
```

source·glossary·artifact 명령 인자는 현재 작업 폴더 기준이다. 기록 안에는 인계서 폴더 기준 상대 경로를 저장하므로 inspect는 다른 폴더에서도 사용할 수 있다. 원문·용어집·산출물은 읽기만 한다. 인계서는 JSON 파일이며 인터넷 요청·모델 호출은 하지 않는다.

### 단계와 이어가기

순서는 `analysis → draft → review → revision → polish → check`다. 예를 들어 초안까지 끝났다면 다음은 review이며 번역을 새로 시작하지 않는다. 해당 파일을 실제로 만든 뒤에만 기록한다.

```sh
python /path/to/skill/scripts/translation_session.py checkpoint handoff.json --stage analysis --artifact analysis.md
python /path/to/skill/scripts/translation_session.py checkpoint handoff.json --stage draft --artifact draft.md
python /path/to/skill/scripts/translation_session.py inspect handoff.json --json
```

모든 단계를 기록해도 `recorded`일 뿐 품질 합격·사람 승인·출판 준비 완료를 뜻하지 않는다. 파일 순서·해시 확인과 번역의 의미 검토를 구별한다. check에는 실제 원문 대조·기계 검사 결과와 남은 쟁점이 있는 보고서 경로를 기록한다. 검사를 실행하지 않았다면 그 사실을 적는다. 자동 감사에 `hold`가 있거나 중요한 미해결 쟁점이 있으면 원고 채택을 보류한다. checkpoint 도구가 보고서 내용을 자동 판정하지는 않는다.

원문·용어집·독자나 문체 설정이 바뀌면 `stale`로 표시한다. 변경 내용을 확인하고 다시 등록한다. 이전 단계 기록과 표현 결정을 삭제하지 않고 이력으로 보관한다. 달라진 입력에 묶인 결정은 다시 채택하기 전까지 자동 재사용 목록에서 빠진다.

```sh
python /path/to/skill/scripts/translation_session.py init handoff.json --refresh
```

이미 검토한 draft.md가 바뀌었으면 draft와 그 뒤 단계는 다시 확인한다. 입력이 그대로라면 바뀐 초안 파일을 checkpoint로 재등록하고 review부터 이어간다. 파일을 자동 재작성하거나 오래된 최종본을 삭제하지 않는다. 새 번역본이 필요하면 새 인계서·출력 폴더를 쓴다.

종료 코드: 정상 기록·재개 가능 0, 입력/산출물 변경으로 재검토 필요 2, 입력·사용법 오류 3. 정상 종료는 번역 정확성 인증이 아니다.

불완전한 판단·중복 ID·알 수 없는 설정·손상된 해시와 단계 구조도 입력 오류로 거부한다. 잘못된 인계서를 자동으로 고쳐 저장하지 않는다. 이전 파일을 보존한 채 오류 필드를 확인한 뒤 다시 실행한다.

### 표현 결정

```sh
python /path/to/skill/scripts/translation_session.py decision handoff.json --id bank-finance --kind term --source-text bank --target 은행 --state adopted --owner model --reason "이 구간은 금융 기관을 설명함"
```

`kind`는 term·voice·interpretation·first_mention, `state`는 provisional·adopted·deferred·rejected다. `owner` 기본값은 model이며 user·editor도 명시할 수 있다. adopted는 이 작업에서 선택한 표현이라는 뜻이다. 사용자의 승인이 실제로 없었다면 owner=user로 쓰지 않는다. 비유·용어·첫 등장 원문 구절은 등록 원문에 실제로 있어야 한다. 문체 결정은 표본의 말투만 기록하며 표본의 사실·경험은 원고에 옮기지 않는다.

표현 선택은 현재 분야·구간에 묶인다. 새 선택이 추가되거나 기존 선택이 바뀌면 draft 이후 단계는 다시 확인한다. 모델 잠정안이나 보류안은 `usable_decisions`에 나오지 않는다. 분야와 구간이 섞인 글은 구간별 인계서로 다루고 기존 chunk_manifest로 원문 구간·해시·순서를 연결한다. 이 helper가 문서 안의 분야를 자동 분류하지 않는다.

## 자연스러움 확인과 납품

polish는 한국어만 읽으며 아래 질문을 실제 장르에 맞게 쓴다. 모든 문서에 모든 질문을 강제하지 않는다.

| 장르 | 읽을 때 확인할 것 | 유지할 것 |
|---|---|---|
| 안내·응대 | 대상·다음 행동·시점을 알 수 있는가 | 원문에 있는 예외·제약·독자와의 예의 |
| 기사·보고서 | 주장 주체와 조건·근거가 연결되는가 | 불확실성·반박·확인 상태 |
| 기술·UI | 지시 대상과 실제 화면·용어가 일치하는가 | 식별자·변수·코드·공식 기능명 |
| 에세이·칼럼 | 문장이 앞 문장의 생각을 이어받는가 | 필자의 태도·의도된 반복·열린 판단 |

자체 작성 대조 예문:

- `The bank may reopen.` → `은행이 다시 문을 열 수도 있다.`는 가능성을 보존한다. 더 단정적인 `은행이 다시 문을 연다.`로 다듬지 않는다.
- `검토 결과를 확인하시어 신청 여부를 결정해 주시기 바랍니다.` → `검토 결과를 확인한 뒤 신청 여부를 결정해 주세요.`는 원래 행동과 순서를 유지한다. 신청이 필수라고 바꾸지 않는다.
- 앞에서 풀어 쓴 약어는 독자에게 필요하지 않으면 구간마다 다시 설명하지 않는다. 첫 등장 여부가 불확실하면 이미 설명했다고 추정하지 않는다.
- `bank`가 금융 기관과 지형을 각각 가리키면 분야·문맥에 따라 은행과 강둑을 구별한다. 형태가 같다는 이유로 일괄 치환하지 않는다.

이 예문은 편집 판단을 설명하며 한국어 품질 벤치마크가 아니다. 자연스러움 때문에 바꾼 부분은 원문과 이웃 문맥에 다시 대조한다. 새 변경이 숫자·부정·조건·인과·주장 귀속을 바꾸지 않았는지 확인하고 영향받은 검사를 다시 실행한다. 개선 근거가 없으면 더 고치지 않는다.

납품 모드는 인계서의 delivery 또는 사용자 요청으로 정한다. `copy`는 final.md에 본문만, `review`는 본문과 별도 검토 보고서를 제공한다. 작업이 끝났다는 문구·변경률·등급·도구 표식은 본문에 넣지 않는다. 인용·각주·필수 고지는 유지한다. 미해결 내용을 숨기려고 없애지 말고 중요한 쟁점이 남으면 초안 상태임을 별도로 알린다.

설계 근거와 채택하지 않은 부분은 [GitHub 조사 기록](translation-workflow-research-20261025.md)에 있다.
