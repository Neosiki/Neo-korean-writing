# 해외 기사로 점검하는 번역 — 2026-10-19~21

Reuters·AP 계열 기사에서 **게재본 날짜별 2편, 총 6편**을 골랐다. 원 매체와 제휴 게재 매체, 날짜·시각의 표시, 열람 범위를 `tests/fixtures/news_translation_20261019_21.json`에 기록했다. 날짜는 페이지·색인에 표시된 게재본의 달력 날짜이며 최초 송고일을 인증한 값이 아니다. 사진 날짜나 검색 수집일은 기사 발행일로 쓰지 않았다. 날짜별 전수 조사나 조회수 순위가 아니다.

## 원문과 번역 자료의 성격

각 기사에서 11~22단어의 짧은 발췌만 남겼다. 한국어는 ChatGPT가 작성하고 원문·주변 문맥으로 자체 검토한 번역이다. 기존 전문 번역가의 번역문, 독립 평가자가 확정한 정답, 기사 전문 번역집이 아니다. 별도 전문·이미지 아카이브는 만들지 않았다. 검색 색인만 확인한 자료는 본문 정독과 구분했다. 일부러 의미를 바꾼 12개 문장은 시험용이며 언론사·번역가의 실제 오류가 아니다.

## 자료와 판단

- **10/19, N19A:** [Reuters Breakingviews](https://www.breakingviews.com/columns/considered-view/oxford-summit-rings-alarm-corporate-ai-2026-10-19/). 공개 요약만 확인한 해설이다. 가능성을 전면적인 확정으로 바꾸는 위험을 점검한다.
- **10/19, N19B:** [Reuters / Yahoo Finance](https://finance.yahoo.com/news/uk-risks-becoming-ai-customer-132523750.html). 기자·시각·본문은 검색 색인으로 확인했다. 즉각 답변이 없었다는 보도와 논평 거부를 구분한다.
- **10/20, N20A:** [Reuters / StreetInsider](https://www.streetinsider.com/Reuters/Exclusive-Qualcomm%2Bto%2Bcut%2Bjobs%2Bworldwide%2Bin%2Bperformance-focused%2Blayoffs,%2Binternal%2Bmemo%2Bshows/27206262.html). 제휴 게재 본문·기자를 확인했다. 메모에 없는 규모를 추정해 채우지 않는다.
- **10/20, N20B:** [Block Club Chicago·AP 제휴 배포 / KRMG](https://krmg.com/2026/10/20/delivery-robots-accused-of-scanning-customers-faces-sharing-biometric-data/). 본문과 원 출처 표시를 확인했다. 소송 당사자의 주장과 회사의 반박을 함께 읽는다. 단순히 AP 독자 취재로 표기하지 않는다.
- **10/21, N21A:** [AP / ClickOnDetroit](https://www.clickondetroit.com/news/politics/2026/10/21/democrats-faith-in-election-results-is-falling-but-still-exceeds-republicans-ap-norc-poll-finds/). AP·제휴사의 검색 색인 본문과 시각을 확인했다. 조사 대상·비교 연도·비율을 함께 보존한다.
- **10/21, N21B:** [AP / ClickOrlando](https://www.clickorlando.com/news/politics/2026/10/21/a-golden-age-vs-were-working-on-it-trump-and-vance-give-different-pitches-on-the-economy/). 제휴사의 검색 색인과 게재일을 확인했다. 말한 사람과 대응 진행 상태를 바꾸지 않는다.

## 실제로 고친 것과 남아 있는 한계

v9.2로 여섯 번역을 실행하면 N21A의 `2022`와 `2022년`을 서로 다른 잠금 토큰으로 보고했다. v9.3은 1000~2999의 연도형 숫자에 붙는 년 접미를 표면 별칭으로 처리한다. 연도 값이 달라지면 계속 검출한다. 이 범위 밖의 연도, 날짜 순서·달력 변환, 수량의 실제 의미를 자동 확정하지 않는다. 날짜가 아닌 네 자리 수를 연도로 바꾼 오역은 사람 검토가 필요하다.

여론조사의 비율·차이를 검토하도록 `%포인트/percentage points/%p` 별칭도 추가했다. `%`와 `%p`는 다른 단위로 남긴다. 다른 수치가 같은 수치로 바뀌거나, 여러 집단의 같은 숫자가 서로 바뀌는 의미 오류는 숫자 목록 비교만으로 잡을 수 없다.

`prompts/news-translation-review.md`는 이러한 빈틈을 원문 위치·화자·주장·조건·대상·시점의 대조로 보완한다. 문서에는 이미 있던 충실성 원칙을 기사 작업 순서로 구체화했다. 사람 검토가 필요한 항목을 자동 위험 점수에 더하지 않는다.

## 재현과 평가 해석

```bash
python scripts/evaluate_news_fixtures.py --json
```

이 명령은 출처 메타데이터·날짜별 구성·짧은 발췌의 총량·시험용 오류 표시를 검사하고, 정상 번역과 변형문을 현재 감사 코드에 넣는다. 정상 번역의 표면 잠금과 의미 검토를 분리해 보고한다. 변형문 중 자동 검사를 통과하는 항목은 **코드의 사각지대**로 보고하며 번역 정답률로 부르지 않는다.

이 여섯 구간은 개발에 사용한 회귀 자료다. 보지 않은 기사에 대한 품질 검증, 기존 스킬과의 독립 블라인드 비교, 전문 번역가 평가를 대체하지 않는다. 스킬의 검토 순서가 실제 번역 품질을 얼마나 올리는지는 별도 보류 평가가 필요하다.
