# 외신 자료 인계 검토 — Grok v10.2 제안과 재검증

검토일: 2026-10-22. Grok 작업본은 2026-10-19~21 BBC 영·한 기사 9쌍과 뉴시스의 NYT 사설 요약 1건을 분석했다고 보고했다. 기사 본문·추출 결과·실행 로그는 전달되지 않았다. 아래 목록은 **인계받은 후보**이며 검증된 병렬 코퍼스가 아니다.

## 출처 확인 범위

- BBC 영·한 첫 후보 URL을 직접 열었으나 두 페이지 모두 열람에 실패했다. 나머지 BBC 후보도 본문·날짜·대응 관계를 독립 확인하지 않았다.
- [뉴시스 기사](https://www.newsis.com/view/NISX20261021_0003834207)는 직접 열어 제목, 2026-10-21 게재일과 NYT 사설 요약 보도임을 확인했다. NYT 원문 URL은 없어 번역 짝으로 검증하지 못했다.
- 인계문에 적힌 누락 134→20건, hold 10→5건, 쉼표 중앙값 1.7회 등은 재현하지 못해 성능 근거에서 제외했다.
- 기사 원문 전문은 저장하지 않는다. 테스트 문장은 직접 쓴 예문이며 전문 번역가의 실제 문장을 평가한 결과가 아니다.

## 인계받은 후보 목록

아래 제목·시각·비고는 원 인계문 표기를 보관한 것이다. 위 확인 범위를 넘어선 사실로 인용하지 않는다.

| # | 매체 | 한국어판 (게재 KST) | 영문 원문 | 비고 |
|---|---|---|---|---|
| 1 | BBC News 코리아 ← BBC News | AI 붐에 수출 증대 … 중국 경제 성장세 가속화 (10/19 17:56) https://www.bbc.com/korean/articles/crgj9yq1g9vqo | China's growth accelerates as AI boom helps boost exports (10/19 11:03 KST) https://www.bbc.com/news/articles/cm5yn098xz8lo | 전문 번역에 가까움 |
| 2 | BBC News 코리아 ← BBC News | 캐나다 군 기지에 대규모 화재... 사상자 다수 발생 (10/19 12:58) https://www.bbc.com/korean/articles/cmlyljpy1rnpo | Major fire at Canada military base leaves four dead, dozens injured https://www.bbc.com/news/articles/cxj0ly1m3q81o | 영문은 BBC 색인상 10/18(영국 기준) |
| 3 | BBC News 코리아 ← BBC News | '전례 없는' 폭력 시위에 충격에 빠진 프랑스… 마크롱, '평정과 질서' 촉구 (10/19 12:53) https://www.bbc.com/korean/articles/cq9vzdlymd8jo | Macron calls for calm in France and warns rioting must not escalate https://www.bbc.com/news/articles/cw240zl08dm5o | 영문 게재일 미확인 |
| 4 | BBC News 코리아 ← BBC News | 러시아에서 '반푸틴 공작'을 벌이는 사람들 (10/19 17:10) https://www.bbc.com/korean/articles/cq4g1jykw7plo | Inside the shadowy world of anti-Putin sabotage from within Russia https://www.bbc.com/news/articles/c6pwgzkj8zzgo | 장문 탐사 기사, 축약 번역 |
| 5 | BBC News 코리아 ← BBC News | 프랑스 폭동 이후…파리 일부 지역 등에 내려진 '통행금지령' (10/20 11:42) https://www.bbc.com/korean/articles/cm1j3zp370y7o | Curfew imposed in parts of central Paris and other cities after rioting across France (10/19) https://www.bbc.com/news/articles/cx30ez03djyqo | |
| 6 | BBC News 코리아 ← BBC News | 일본 탐사선 발사 성공…'화성의 위성' 포보스서 시료 채취 도전 (10/20 14:55) https://www.bbc.com/korean/articles/cwdd8m24pjj3o | Japan's MMX mission set to grab a piece of Mars's moon Phobos https://www.bbc.com/news/articles/cmvgxvkv54w1o | 영문은 발사 전 판(10/18)이라 부분 대응. 발사 후 영문 판 미확인 |
| 7 | BBC News 코리아 ← BBC Verify | 트럼프 대통령 집권 하에 미국 경제는 실제로 어떤 상황인가? (10/20 19:18) https://www.bbc.com/korean/articles/cqly3d45x9leo | How is the US economy really doing under President Trump? (10/20 14:00 KST) https://www.bbc.com/news/articles/cv98ze40jz18o | 원문의 약 절반 분량으로 축약 |
| 8 | BBC News 코리아 ← BBC News | 젤렌스키, '미국과 정보 공유 잘 되고 있어' … 위트코프 미 특사, 러시아서 푸틴과 회담 예정 (10/21 16:05) https://www.bbc.com/korean/articles/c3n04xle2eqvo | Zelensky says intelligence sharing 'works now' as US envoy to meet Putin in Russia https://www.bbc.com/news/articles/cq5ynkx3xy11o | |
| 9 | BBC News 코리아 ← BBC News | 호주 하원의원에 '고의 추정' 차량 돌진... '두 다리 모두 절단했다' (10/21 18:19) https://www.bbc.com/korean/articles/c69wzd9kjwq1o | What we know about Australian MP hit by car in alleged deliberate attack https://www.bbc.com/news/articles/cm5ynk1g88kwo | 한국어판 기자명(해리 세쿨리치·제이콥 필립스)으로 대응 확인 |
| 10 | 뉴시스 ← The New York Times 사설 | "트럼프는 민주국가와 전쟁하는 독재자를 돕는다"-NYT (10/21 07:41) https://www.newsis.com/view/NISX20261021_0003834207 | Trump's Betrayal of Ukraine (NYT 사설, 10/20) — NYT 원문 URL 미확인(유료 구독). 비교는 제3자 전재본으로만 했다 | 번역이 아니라 요약 보도형. 문단 대응 비교 불가 |

## 채택·수정·제외

- 채택: 수량 표기와 현지화 약어를 조정 목록에 기록한다. 약어 대응은 사람 검토 후보다. PM·MP는 정치 문맥을 요구한다. 초벌 대비 비교에도 같은 정책을 적용한다.
- 수정: 24시 표기와 오전·오후 표기를 시각 하나로 비교한다. 자정·정오를 구분하고 시와 분을 다른 시각에서 가져와 맞추지 않는다. 모호한 `11시`는 임의로 오후로 해석하지 않는다.
- 제외: 괄호 안의 마일·통화·GMT를 무조건 생략 허용하던 규칙. 다른 정보까지 지워도 통과할 수 있어 기존 누락 검사로 보류한다. 검증 가능한 단위 환산에는 v9.4.1의 계산·반올림 오차 정책을 유지한다.
- 보류: 요일을 날짜로 환산하는 자동 검사. 기사 시각과 시간대가 필요하다.
- 선택형 편집 규칙: 기사·번역 프로필의 희소한 연결어미 뒤 쉼표를 후보에서 제외한다(1,000자당 3회 미만). 이 수치는 실증된 언론 규범이 아니라 제안받은 편집 휴리스틱이다. 기본 프로필과 줄표 검사는 유지한다.
- 용어집: 기사 용어는 수정 가능한 예시다. `Victoria` 띄어쓰기나 `inflation` 역어를 보편적인 정답으로 강제하지 않는다.

## 바로잡은 의미 오류

인계문은 `trade surplus` 풀이 예에 `재정적자(세입과 지출 간의 차이)`를 붙였다. 서로 다른 개념이다. `trade surplus`는 **무역흑자**이며, 수출액이 수입액보다 많은 차이를 말한다. 잘못된 예는 번역 기법 지침에서 제외했다. 전달 동사 said도 근거 없이 주장 강도를 높이는 `강조했다·비난했다`로 변주하지 않는다.

## 재검증 방법과 한계

`tests/test_v102.py`의 자체 예문으로 표기 차이, 실제 누락, 오전·오후 반전, 분 교차, 괄호 누락, 현지화 후 초벌 비교를 검사한다. 기존 기사 6구간 회귀와 의미 변형 시험은 유지한다. 자동 통과는 의미 정확성 인증이 아니며, 동일 숫자의 주체가 뒤바뀌는 등의 의미 사각지대는 사람 대조가 필요하다.
