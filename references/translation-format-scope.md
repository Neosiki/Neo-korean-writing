# 번역 형식과 용어집 범위 — 점검기 9.6

UI 문구, 마크업, ICU 메시지와 다의어 용어집을 감수할 때 읽는다. 자동 검사는 의미의 정확성이나 누락 없는 번역을 인증하지 않는다.

## 형식 선택

```sh
python scripts/translation_audit.py source.html target.html --format html --json
python scripts/translation_audit.py source.xml target.xml --format xml --strict
python scripts/translation_audit.py source.txt target.txt --format icu --json
```

`--format`은 `auto`(기본), `plain`, `html`, `xml`, `icu` 중 하나다. 설치형 CLI의 `translation-audit`에도 같은 옵션이 있다. 자동 선택은 원문의 코드 구간을 제외하고 ICU plural/select/selectordinal 구문, HTML 태그 순으로 확인한다. XML은 명시적으로 선택한다. `<Example>` 같은 산문 표기라면 `plain`을 지정한다. 코드 원문 보존 규칙은 모든 모드에서 유지한다.

- `plain`: 기존 `{name}`, `${name}`, `{{name}}`, printf 변수 등의 개수 대조를 유지한다.
- `html`: 명시적으로 균형 있게 닫힌 조각의 태그 계층·개수·보호 속성을 대조한다. void 요소는 닫지 않아도 된다. 속성 순서와 따옴표 차이는 허용한다. 브라우저의 전체 HTML5 오류 복구나 선택적 닫는 태그 규칙을 재현하지 않는다.
- `xml`: 이름의 대소문자와 네임스페이스를 유지하며 ElementTree로 문법을 확인한다. DTD·ENTITY는 지원하지 않는다.
- `icu`: ICU MessageFormat 1 파서로 문법, 변수 이름·타입·스타일, 필수 `other`, 중복 선택자, 명시 값(`=0` 등), offset, `#` 수량 참조를 확인한다. 한국어에 맞게 `one`·`few` 등의 언어별 복수 분기를 줄일 수 있다. `select`의 의미 분기와 명시 값 분기는 보존한다. MF2·프레임워크별 확장·ICU 안의 rich-text 태그 검증은 포함하지 않는다. 반복된 변수나 제어문의 모든 발생 횟수를 의미 단위로 대응시키는 검사는 아니다.

HTML·XML에서 `alt`, `title`, `aria-label`, `aria-description`, `placeholder`는 번역할 수 있다. 속성 자체의 존재와 그 안의 단순 자리표시자는 보존한다. `src`, `href`, `id`, `class`, `style`, `data-*` 등 나머지 속성은 보호한다. 이 정책에 맞지 않는 문서는 별도 편집 방침으로 검토한다. 숫자·URL·코드 잠금은 별도로 적용되므로 텍스트 속성을 번역할 수 있다는 것이 잠금 전체의 해제를 뜻하지 않는다.

결과의 `format_validation`에 실제 형식, 검사 범위와 문제 목록이 나온다. 원문 자체의 문법 문제도 `side: source`로 구분한다. 형식 손상은 FID-10으로 보류한다. `baseline_delta`의 표면 토큰 비교에도 같은 형식을 사용한다. 이 출력은 브라우저 렌더링 검사나 XSS 보안 검사가 아니다.

## 용어집: 설명과 선택 조건 구분

기존 5열 TSV와 JSON은 그대로 사용할 수 있다. `context`는 사람이 읽는 설명이다. 문장을 추측해 분야를 자동 결정하지 않는다. 실제 선택에는 `domains`와 `segments`를 쓴다. 새 TSV의 6·7열이며 여러 값은 `|`로 구분한다. JSON에서는 문자열 또는 배열을 받는다.

```json
[
  {"source": "bank", "target": ["은행"], "domains": ["finance"]},
  {"source": "bank", "target": ["강둑"], "domains": ["geography"]}
]
```

```sh
python scripts/translation_audit.py source.md target.md --glossary terms.json --domain finance --segment-id intro
```

분야와 구간 조건을 함께 둔 항목은 둘 다 일치해야 한다. 조건이 일치하는 구체 항목이 있으면 같은 원어의 범용 항목보다 우선한다. 서로 다른 역어가 여전히 충돌하거나 필요한 범위를 지정하지 않으면 `glossary.deferred`와 TERM-4(review)로 남긴다. 다른 분야의 역어를 동시에 요구하지 않는다. `strict`·`flex`의 기존 혼용 검사와 금지 역어 검사는 선택된 항목에만 적용한다.

한 파일에 금융과 지리 문단이 함께 있다면 구간별 입력 파일로 나누어 각각 `--domain`·`--segment-id`를 지정한다. 이 옵션이 전체 파일 안의 문단 경계를 자동 찾아 나누지는 않는다. 미지정 항목의 `review`는 `--strict`에서도 치명·주요 오류로 승격하지 않는다. 범위가 확인되지 않은 용어집을 검수 완료로 보고하지 않는다.

## 근거와 재사용 범위

- [Weblate ICU 검사 구현](https://github.com/WeblateOrg/weblate/blob/0c658610756a7f5d9dac5ab84c6a231c17e7d333/weblate/checks/icu.py): 문법과 변수의 구조 검사를 구분하는 접근을 참고했다. Weblate 코드는 포함하지 않았다.
- [pyicumessageformat](https://github.com/SirStendec/pyicumessageformat/tree/770de136b9b526c0baaf889d023c115999962430): MIT 파서 1.0.0을 수정 없이 포함했다. 출처·라이선스는 [제3자 고지](../THIRD_PARTY_NOTICES.md)에 기록했다. 별도 패키지 설치나 모델 호출은 필요 없다.

회귀 테스트는 자체 작성 예문으로 오탐과 미탐을 함께 확인한다. 외부 번역 전문이나 유료 기사 본문을 배포하지 않는다.
