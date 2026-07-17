**한국어 윤문 스킬의 규칙 추적성과 의미 보존 검증**

Neosiki/korean-humanize v5.0.0에 대한 탐색적 아티팩트 연구

**저자:** 윤영식 (尹永植, Young-Shig Yoon)  
**직함·소속:** NextAI 대표 · 아이피플래닛 대표  
**이메일:** osiki999@gmail.com  
**교신저자:** 해당 없음  
**영문 제목:** *Verifying Rule Traceability and Meaning Preservation in a Korean Text Humanization Skill: An Exploratory Artifact Study of Neosiki/korean-humanize v5.0.0*

**저자 위치 및 이해상충 진술:** 저자는 분석 대상인 `Neosiki/korean-humanize`의 개발·유지보수자다. 따라서 본 연구는 독립적인 제3자 성능평가가 아니라, 개발자가 자신의 소프트웨어 아티팩트를 대상으로 수행한 탐색적 사례 연구로 해석해야 한다. 자동 검사 결과와 LLM 모의 판정 결과를 구분해 제시했으며, 독립 인간 평가가 완료되기 전까지 의미 보존 성능에 대한 일반화 주장을 하지 않는다.

문서 유형: 최종 논문 원고(본실험 자동 검사 실행본) | 작성 기준일: 2026-07-17 | 연구 상태: 자동 검사 실측
완료·인간 평가 미수행

**자료 사용 주의:** 본 원고의 자동 보존 검사 결과(변형 118건, 문체 통제 49건)는 KLUE 공개 원자료를 추출해
preserve 검사를 실제로 실행한 실측치다. 반면 의미 변화 판정은 독립 인간 평가자가 아니라 LLM(Claude)이 번역
전문가 페르소나 2종을 적용해 수행한 모의 판정이며, 본문과 부록에 이를 명시한다. 모의 판정 수치를 인간 평가 결과로
인용해서는 안 된다.

초록

생성형 인공지능을 이용한 한국어 윤문에서는 문장을 자연스럽게 바꾸는 능력만큼 원문의 사실과 주장 구조를 보존하는 능력이 중요하다.
본 연구는 공개 저장소 Neosiki/korean-humanize v5.0.0을 소프트웨어 아티팩트로 보고
문서–규칙–구현–테스트의 추적성을 분석하고, KLUE NLI·STS·YNAT 공개
자료에서 추출한 49개 앵커 문장에 대해 통제 변형 벤치마크를 실제로 실행했다. 계획된 250건 중 원문에 해당 단서가
존재하는 118건의 단일 위험 변형과 49건의 문체 통제 사례를 생성해 보존 검사에 투입했다. 저장소 스냅샷 분석
결과, 14개 거시 패턴과 7개 Sunny-7 규칙은 진단 체계와 회귀 테스트에 대체로 연결되어 있었다. 자동 보존 검사는
숫자 변형 17건을 전부(100%), 영문 용어 변형 5건 중 4건(80%)을 표면 실패로 포착했고, 문체 통제
49건에서는 과잉 경고가 없었다. 반면 부정·양태·인과·논항·비교·조건 변형 96건은 모두 무신호로 통과했다. 이는
의미 가드가 문서 단위 밀도 변화를 전제로 설계되어(허용 오차 2건·40%), 문장 단위의 단일 표지 변형에서는 발화하지 않기
때문이다. 10건 파일럿에서 문서 수준 텍스트의 부정·양태·인과 변형이 경고를 발생시킨 것과 대비되는 결과다. 의미 변화
판정은 번역 전문가 페르소나 2종을 적용한 LLM 모의 판정으로 수행했으며(일치율 92.4%, 전체 카파 0.879), 판정
확정 기준 무신호 의미 변경률은 81.6%였다. 이 수치는 독립 인간 평가로 검증되기 전까지 잠정치다. 본 연구는 해당 스킬이
모든 한국어 윤문 품질이나 생성 텍스트 탐지 성능을 제공한다고 주장하지 않는다. 대신 규칙·구현·검증의 추적성, 통제 변형
커버리지, 검사 단위 불일치, 인간 검토가 필요한 경계를 명시하는 평가 틀을 제안한다.

**주제어:** 한국어 윤문, 생성형 AI, 의미 보존, 소프트웨어 아티팩트, 통제 변형, 추적성

1\. 서론

생성형 AI 기반 윤문은 맞춤법 수정이나 문장 다듬기를 넘어 문체, 문단 구조, 인용 형식, 용어 선택을 함께 바꾸는 작업으로
확장되고 있다. 결과 문장이 더 유창해졌다는 사실만으로 윤문이 성공했다고 판단하기 어려운 이유가 여기에 있다. 숫자,
단위, 영문 제품명, 직접 인용, 부정 표현, 가능성 표현은 표면적으로는 작은 요소지만 문장의 사실성, 확정성, 책임
소재를 바꿀 수 있다. 주어와 목적어의 관계, 비교 방향, 조건 범위와 시간 순서가 달라져도 문장은 자연스럽게 읽힐 수
있다.

이 문제는 생성형 AI 윤문을 단순한 재생성 과정이 아니라 검증 가능한 수정 과정으로 다룰 것을 요구한다. 윤문 도구가 어떤
변화는 허용하고 어떤 변화는 막는지, 그 원칙이 설명 문서·규칙 원천·실행 코드·테스트에 실제로 반영되어 있는지를
확인해야 한다. 특히 '의미 보존'이라는 표현은 범위가 넓기 때문에, 자동 검사가 실제로 다루는 단서와 다루지 않는
관계 구조를 구분해 보고해야 한다.

본 연구는 공개 저장소 Neosiki/korean-humanize를 사례로 삼는다. 이 저장소는 한국어 윤문을 위한 작업 모드와
문체 패턴, 의미 보존 규칙, 실행 스크립트, 회귀 테스트를 함께 제공한다. 따라서 프롬프트나 사용 설명서만 분석하는 대신,
윤문 스킬을 여러 설계 층이 결합된 아티팩트로 검토할 수 있다. 분석 대상은 2026년 7월에 확인한 v5.0.0 스냅샷이며,
커밋은 ce02da2로 고정했다.

본 연구의 목적은 이 스킬이 글을 얼마나 '사람답게' 만드는지 일반적으로 판정하는 데 있지 않다. 또한 사람의 글과 생성 모델의
글을 구별하는 AI 탐지기 연구도 아니다. 한국어 생성 텍스트 탐지 연구는 한국어의 띄어쓰기, 형태·품사 분포, 쉼표 사용 등
언어 특성을 별도로 다뤄야 함을 보여준다. 그러나 탐지의 목적은 생성 출처를 판별하는 것이고, 본 연구의 목적은 윤문 과정에서
원문의 사실과 관계가 유지되는지를 점검하는 것이다.

연구 질문은 다음과 같다.

1\. korean-humanize v5.0.0의 문서, 규칙, 구현, 테스트는 어떤 추적성 관계를 갖는가?

2\. 보존 검사는 숫자·인용·용어·구조·일부 의미 단서의 통제 변형을 어느 범위에서 포착하는가?

3\. 자동 검사가 포착하지 못하는 변형은 무엇이며, 그 결과는 인간 검토 절차에 어떤 요구를 제기하는가?

2\. 관련 연구

생성 텍스트의 출처를 판별하는 연구는 언어모델 출력의 통계적 특성이나 생성 흔적을 분석해 왔다. GLTR은 토큰 예측 확률을
시각화해 사람이 생성 텍스트의 의심스러운 부분을 검토하도록 했고(Gehrmann, Strobelt, & Rush,
2019), DetectGPT는 생성 모델의 로그 확률 변화와 곡률을 이용한 영샷 탐지 접근을 제안했다(Mitchell et
al., 2023). 이 연구들은 텍스트의 생성 출처를 판별하는 데 초점을 둔다는 점에서, 윤문 결과가 원문의 의미를 보존했는지를
평가하는 본 연구와 구분된다.

탐지기의 공정성 문제도 중요한 배경이다. 비원어민 영어 글이 AI 생성물로 오인될 가능성이 더 높을 수 있다는 분석은 언어와
집단에 따른 평가 편향을 지적한다(Liang et al., 2023). 한국어에 대해서는 KatFishNet이 한국어
자료와 장르를 포함한 데이터셋을 만들고 띄어쓰기, 품사 다양성, 쉼표 사용과 같은 언어학적 특징을 활용했다(Park et
al., 2025). 최근 한국어 생성 텍스트 탐지 연구도 뉴스·초록·에세이 자료에서 의미·통사 정보를 활용하고 있다. 이러한
연구는 본 연구의 직접 비교 대상이 아니라, 한국어 자료에 맞춘 평가 설계가 필요하다는 방법론적 배경이다.

텍스트 단순화와 재작성 연구는 자연스러움과 의미 보존 사이의 긴장을 다뤄 왔다. Agrawal과 Carpuat(2024)은 의미
보존을 자동 지표 하나로 환원하기 어렵고 인간 판단과 벤치마크의 정렬을 따로 살펴야 함을 보였다. 생성형 AI가 만든 문장을
변형했을 때 탐지기가 약해질 수 있다는 연구도 변형과 평가 기준의 관계를 문제 삼는다(Masrour, Emi, & Spero,
2025). 본 연구는 이 논의와 연결되지만, 문장 유창성 점수나 탐지 점수 대신 윤문 아티팩트 내부의 보존 게이트가 어떤 변형을
검사하는지를 분석한다.

3\. 연구 대상과 방법

3.1 아티팩트와 분석 자료

분석 자료는 다음 다섯 층으로 나누었다.

|        |                          |                             |
| ------ | ------------------------ | --------------------------- |
| **층위** | **자료**                   | **분석 내용**                   |
| 문서     | README.md, SKILL.md      | 작업 모드, 사용 절차, 보존 원칙         |
| 규칙     | scripts/patterns.json    | 거시 패턴 A–N, Sunny-7, 의미 가드   |
| 구현     | scripts/krh.py           | 진단, 보존 사실 추출, 경고, 엄격 모드     |
| 테스트    | tests/test\_krh.py       | 패턴 발화, 보존 실패, 구조 경고, 차이율 검사 |
| 변경 이력  | CHANGELOG.md, ROADMAP.md | 버전 범위와 향후 확장 계획             |

저장소의 주장을 규칙 파일, 실행 코드, 테스트에서 다시 확인했다. 각 항목은 설명된 개념이 규칙·구현·테스트에 모두 연결되면
'완전 일치', 일부 층에서만 확인되면 '부분 일치', 명시적 모순이 있으면 '불일치', 자료만으로 판단할 수 없으면 '확인
불가'로 분류했다.

3.2 유사 GitHub 프로젝트 비교

유사 프로젝트를 목적과 검증 구조에 따라 비교했다.
blader/humanizer(https://github.com/blader/humanizer)와
avoid-ai-writing(https://github.com/conorbronsdon/avoid-ai-writing)은 AI
문체 패턴을 감사하고 직접 재작성하는 에이전트 스킬이다. 전자는 33개 패턴, 음성 조정, 2차 감사와 재작성을 제공하고
MIT 라이선스를 표시한다. 후자는 Rewrite·Detect·Edit 모드, 음성 프로필, 2단계 탐지와
detector·scripts 구조를 제공하며 MIT 라이선스를 표시한다. 두 프로젝트는 문체 변화의 탐지와 재작성 과정의
가시화라는 점에서 본 연구와 가깝지만, 본 연구가 다루는 숫자·인용·논항·비교 관계의 보존 커버리지를 직접 평가하지는
않는다.

textlint(https://github.com/textlint/textlint)는 자연어를 위한 플러그인형 린터로, 규칙을
기본 내장하지 않고 외부 규칙·플러그인·포맷터를 조합한다. --fix와 dry-run을 제공하는 구조는 규칙 실행과 수정
전후 비교를 설계할 때 참고할 수 있다.
TextFlint(https://github.com/textflint/textflint)는
변형·하위집단·공격·Validator·Report 계층을 갖춘 NLP 견고성 평가 도구다.
특히 변형 샘플을 생성하고 품질을 검증한 뒤 분석 보고서를 만드는 구조는 본 연구의 통제 변형–보존 검사–결과 보고 설계와
방법론적으로 가깝다.

한국어 처리 인프라로는 Korector(https://github.com/movemin03/korector)와
Kiwi(https://github.com/bab2min/kiwi)를 확인했다. Korector는 외부 한국어 맞춤법 검사기를
호출하면서 긴 텍스트 청킹, 병렬 처리, 오류 통계와 CLI를 제공한다. Kiwi는 한국어 형태소 분석, 문장 분리, 오타
교정과 평가 실행기를 제공한다. 이들은 korean-humanize와 동일 목적의 윤문 스킬이라기보다, 향후 형태·논항·문장 경계
기반 보존 게이트를 확장할 수 있는 기반 계층이다.
LanguageTool(https://github.com/languagetool-org/languagetool)은 다국어
문법·스타일 검사와 규칙 개발 체계를 제공하는 대규모 비교 배경이다.

이 비교에서 중요한 점은 외부 프로젝트의 규모나 별점이 성능 우위를 뜻하지 않는다는 것이다. 프로젝트마다 입력 단위, 언어, 모델
의존성, 라이선스, 평가 목적이 다르다. 따라서 본 연구는 프로젝트 간 정확도 순위를 만들지 않고, 재작성형 스킬–규칙형
린터–변형 기반 평가–한국어 분석 인프라라는 설계 계열을 구분해 korean-humanize의 위치를 설명한다.
세부 비교표와 라이선스 기록은 부록 G에 수록했다.

3.3 추적성 분석

먼저 규칙 분류 검사를 실행했다. 그 결과 거시 패턴은 A부터 N까지 14개, Sunny-7은 7개로 인식되었고 정규식 컴파일이
완료되었다. 테스트 모음은 각 거시 패턴과 Sunny 규칙의 발화, 깨끗한 입력의 높은 등급 판정, 공식 프로필의 완화, 숫자
변경 실패, 부정 표현 경고, 불릿 병합 경고, 동일 문장의 차이율 0을 확인한다. 이 범위에서는 문서에 설명된 핵심 분류와 실행
규칙, 최소한의 회귀 검증이 연결되어 있다고 판단했다.

추적성은 의미 보존 전체의 포괄성과 같지 않다. 규칙 파일에 의미 가드가 존재하더라도 대상은 부정, 가능성·확률, 인과 표지 등
특정 단서로 제한된다. 주어와 논항의 관계, 비교 방향, 조건 범위, 시간 순서처럼 문장 전체의 관계 구조에 해당하는 의미는
별도 분석이나 인간 검토를 필요로 한다.

3.4 보존 게이트

보존 검사는 원문과 변형문을 비교해 표면 사실, 문서 구조, 일부 의미 표지의 변화를 확인한다. 표면 사실에는 숫자, 직접 인용,
영문 용어가 포함된다. 구조 점검에는 불릿, 표 행, 코드 블록, 링크, 직접 인용 개수가 포함된다. 의미 경고는 부정 표현,
가능성·확률 표현, 인과 표지에 대해 작동한다.

따라서 보존 검사는 '모든 의미가 동등한가'를 증명하는 장치가 아니라, 미리 지정된 위험 단서가 바뀌었는지를 검사하는 규칙 기반
게이트로 정의했다. 자동 검사의 통과는 의미 보존의 증명이 아니며, 경고가 없더라도 사람이 확인해야 하는 영역이 남는다.

3.5 통제 변형 파일럿

예비 실험은 10개 원문–변형문 쌍으로 구성했다. 변형 사례는 숫자 변경, 직접 인용 표지 변경, 영문 용어 삭제, 부정 표현
제거, 가능성 표현 제거, 인과 표지 제거, 불릿 병합, 주어 교체, 비교 관계 역전으로 나누었다. 별도로 숫자·인용·핵심
용어를 유지하면서 문체만 바꾼 통제 사례를 두었다. 각 변형은 원문에서 한 가지 위험만 바꾸도록 만들었으며, 변형문에는 변형 외의
불필요한 맞춤법 오류나 문체 변화가 들어가지 않게 했다.

각 쌍에서 다음을 기록했다.

  - 표면 보존 실패: 보존해야 할 사실이 사라졌는가.

  - 경고 발생: 의미 또는 구조 위험 경고가 생성되었는가.

  - 무신호 통과: 변형이 있었지만 표면 실패와 경고가 모두 없었는가.

이 실험은 실제 사용자의 윤문 결과를 대표하는 대규모 벤치마크가 아니다. 연구자가 특정 위험 단서를 의도적으로 바꿔 넣고 검사
범위를 확인하는 통제 변형 커버리지 실험이다. 그러므로 결과를 정확도, 재현율, 인간 수준의 의미 보존 성능으로 해석하지
않는다.

3.6 본실험 설계: 자료·장르·변형 유형

본실험의 자료 후보는 공개 KLUE 자료군의 NLI, STS, YNAT이다. NLI에서는 premise, STS에서는 독립적으로
사용할 수 있는 sentence1, YNAT에서는 title을 사용한다. 원자료의 NLI·STS 레이블은 본 연구의 의미 보존
정답으로 사용하지 않는다. 원래 레이블은 자료 성격을 설명하는 메타데이터로만 보존하고, 변형 후 의미 변화는 별도 인간 평가자가
판정한다. 자료군별 배분과 역할은 다음과 같다.

|                |                              |           |                      |
| -------------- | ---------------------------- | --------- | -------------------- |
| **자료**         | **사용할 필드**                   | **표본 목표** | **역할**               |
| KLUE NLI v1.1  | premise                      | 20        | 부정·인과·논항·조건 변형 후보    |
| KLUE STS v1.1  | sentence1, sentence2 중 독립 문장 | 20        | 의미 관계·비교·양태 변형 후보    |
| KLUE YNAT v1.1 | title                        | 10        | 숫자·영문 용어·표면 구조 변형 후보 |

행 ID 매핑은 korean-humanize\_verified\_anchor\_ids.csv에 기록했으며 전체 목록은 부록 C에
수록했다. 원문 전체를 논문 부록에 복사하지 않고 실행 시 원자료 ID로 추출하도록 설계했다. 본실험 실행에서는 2026년
7월 17일 Hugging Face 공개 데이터 뷰어 API에서 50개 앵커의 원문을 추출했다. 이 과정에서
A030(klue-nli-v1\_train\_00071)은 A029와 premise 텍스트가 동일해 중복 제거 규칙에 따라
제외되었고, 최종 앵커는 49개가 되었다. 계획된 245건(49개 앵커 × 5개 변형) 중 원문에 해당 단서가
실제로 존재하는 118건에만 변형을 적용했고, 나머지 127건은 단서 부재(직접 인용·불릿 구조 전무, 일부 앵커의
숫자·비교·인과 표지 부재)를 사유로 제외 기록했다. 문체 통제 사례는 앵커당 1건씩 49건을 생성했다. 원문에 없는
인용이나 불릿을 억지로 삽입하지 않는다는 원칙을 그대로 적용했으며, 그 결과 직접 인용과 불릿 구조 범주는 적용 사례가
0건이 되어 NA로 보고한다.

변형 유형은 다음 열 가지로 정의한다. 각 변형은 원문에서 한 가지 위험만 바꾸도록 만든다.

1\. 숫자·단위·범위 변경

2\. 직접 인용의 시작·끝 또는 인용 개수 변경

3\. 영문 고유 용어·제품명 삭제 또는 치환

4\. 부정 표현 삭제·추가

5\. 가능성·확률·추정 표현의 확정화 또는 약화

6\. 인과 표지 삭제·반전

7\. 불릿·표·문단 구조 병합

8\. 주어·목적어·논항 관계 교체

9\. 비교 방향 또는 비교 대상 교체

10\. 조건·시간 순서·범위 관계 변경

1–7은 현재 구현이 이미 일부 다루는 범주이고, 8–10은 파일럿에서 무신호 가능성이 확인된 확장 범주다.

자료 선정과 제외 규칙은 다음과 같다. 텍스트 필드가 비어 있거나 문장 경계가 깨진 사례는 제외한다. URL, 개인정보, 지나치게
짧은 단편, 중복 문장은 제외한다. 앵커 하나에는 최소 두 가지 보존 단서(예: 숫자+인과, 영문 용어+양태, 인용+부정)가
포함되도록 우선순위를 둔다. 특정 변형에 필요한 단서가 없는 앵커에는 변형을 억지로 적용하지 않고 동일 자료군의 다음
후보로 대체한다. 원문은 원자료의 ID와 함께 보관하고, 분석 공개본에는 재배포 조건에 따라 원문 전체 또는 해시·식별자만
포함한다.

장르 다양성 관점에서 본실험은 학술 초록, 정책·업무 보고서, 뉴스·설명문, 에세이·칼럼, 사용 안내·교육문의 다섯 장르에서 각
10개 안팎의 앵커를 확보하는 것을 권장 설계로 둔다. 장르 다양성을 보완할 때는 국립국어원 '모두의 말뭉치'를 우선 검토한다.
이 시스템에는 신문, 글쓰기, 요약 등 여러 한국어 자료가 공개되어 있으며, 신문 말뭉치의 경우 매체 사용 허가를 받아
정제했다는 설명이 제공된다. 논문에는 실제로 사용한 자료명, 버전, 신청·이용 조건, 재배포 가능 범위를 개별적으로
기록한다.

3.7 판정 절차: 설계와 이번 실행의 차이

프로토콜 설계상 의미 변화의 정답은 자동 결과만으로 정하지 않는다. 한국어 모어 화자이면서 편집 또는 언어 연구 경험이 있는
평가자 2명이 원문–변형문 쌍을 독립적으로 판정하고, 판정 범주는 의미 유지, 의미 변경, 판정 유보의 세 가지로
둔다. 평가자는 자동 검사 결과를 보지 않으며, 불일치 사례는 제3 검토자 또는 합의 회의로 확정하고 평가자 간 일치도와
유보율을 보고한다.

**이번 실행에서는 독립 인간 평가자를 확보하지 못해, 위 절차를 LLM 모의 판정으로 대체했다.** LLM(Claude)이 서로
다른 판정 기준을 가진 번역 전문가 페르소나 2종을 적용해 각 쌍을 2회 판정했다. 평가자 R1은 엄격 기준으로 진리조건 변화뿐
아니라 확신도·화행 강도의 변화도 의미 변경으로 판정하고, 평가자 R2는 관대 기준으로 명제 핵심의 유지 여부를 기준으로
판정한다. 불일치 사례는 판정 근거를 대조하는 합의 규칙으로 확정했다. 이 방식은 변형 생성자와 판정자가 동일
모델이라는 구조적 한계를 가지며, 평가자 간 독립성이 성립하지 않는다. 따라서 모의 판정 수치는 인간 평가를
대신하는 결과가 아니라 자동 검사와 대조하기 위한 잠정 참조값이며, 본문 전체에서 이를 구분해 표기한다. 실제 인간 평가를
수행할 때는 소속 기관의 연구윤리 기준, 참여자 동의, 보상, 자료 보안 방침을 먼저 확인해야 한다.

3.8 보고 지표와 산출 규칙

정확도라는 단일 수치 대신 변형 유형별로 다음을 보고한다.

  - 포착 커버리지: 의미 변경 사례 중 표면 실패 또는 경고가 발생한 비율

  - 무신호 의미 변경률: 인간 평가에서 의미가 바뀌었으나 자동 검사에 아무 신호가 없었던 비율

  - 통제 무경고율: 의미를 유지한 문체 통제 사례에서 경고가 발생하지 않은 비율

  - 경고 유형 분포: 숫자·부정·양태·인과·구조 등 경고 종류별 빈도

  - 판정 유보율: 인간 평가자가 자동화만으로 판단하기 어렵다고 본 비율

산출 규칙은 다음과 같이 고정한다. 한 행은 하나의 앵커–변형 쌍이다. automated\_signal = 1은 표면 보존 실패,
의미 경고, 구조 경고 중 하나가 발생한 경우이며, 아무 결과도 없으면 automated\_signal = 0이다. 지표는
coverage = automated\_signal\_count / human\_meaning\_changed\_count,
silent\_change\_rate = silent\_change\_count /
human\_meaning\_changed\_count, control\_false\_warning\_rate =
control\_warning\_count / control\_case\_count로 계산한다. 분모가 0인 범주는 수치를 0으로
채우지 않고 NA로 기록한다. 인간 평가자가 판정 유보로 표시한 사례는 주 분석의 분모와 별도로 유보율을 보고하고, 민감도
분석에서는 보존/변경 양쪽으로 계산한다. 이 지표들은 특정 저장소와 평가 세트에 대한 커버리지를 나타낼 뿐, 모든
한국어 윤문 시스템의 성능이나 모든 의미 보존을 보장하지 않는다.

4\. 결과

4.1 규칙·구현·검증의 추적성

저장소 내부 분류 검사에서 14개 거시 패턴과 7개 Sunny-7 규칙이 확인되었고, 테스트 모음은 이 분류의 발화와 핵심 보존
경계를 다룬다. 따라서 문서–규칙–구현–테스트 사이에는 핵심 기능 범위에서 추적성이 있었다. 특히 문체 진단과 의미 보존
검사를 분리한 점은 윤문 과정에서 '문장이 어색하다'와 '사실이 바뀌었다'를 다른 종류의 위험으로 다루게 한다.

그러나 의미 보존 게이트의 적용 범위는 부분적이다. 표면 사실과 특정 표지의 변화는 자동화되지만, 논항 구조나 비교 관계처럼 문장
전체의 관계를 해석해야 하는 변화는 자동 검사에서 확인되지 않는다. 본 연구에서는 이를 '부분 일치'로 분류했다. 규칙이 있다는
사실만으로 의미 보존 전체가 구현되었다고 판단하지 않았다.

4.2 통제 변형 파일럿

**표 1. 통제 변형 파일럿의 유형별 자동 결과**

|             |           |                   |
| ----------- | --------- | ----------------- |
| **변형 유형**   | **자동 결과** | **해석**            |
| 숫자 변경       | 표면 보존 실패  | 숫자 사실의 변경을 포착     |
| 직접 인용 표지 변경 | 구조 경고     | 인용 개수 변화를 포착      |
| 영문 용어 삭제    | 표면 보존 실패  | 영문 용어 소실을 포착      |
| 부정 표현 제거    | 의미 경고     | 부정 단서 변화 경고       |
| 가능성 표현 제거   | 의미 경고     | 확정성 변화 위험 경고      |
| 인과 표지 제거    | 의미 경고     | 인과 연결 변화 경고       |
| 불릿 병합       | 구조 경고     | 문서 구조 축약을 포착      |
| 주어 교체       | 무신호 통과    | 논항 관계 변화는 포착하지 못함 |
| 비교 관계 역전    | 무신호 통과    | 비교 방향 변화는 포착하지 못함 |
| 문체만 변경한 통제  | 무신호 통과    | 과잉 경고 없음          |

변형 사례 9개 중 7개에서 표면 실패 또는 경고가 발생했고, 2개는 무신호로 통과했다. 문체 통제 사례에는 경고가 발생하지
않았다. 이 결과는 자동 검사가 숫자와 용어 같은 표면 사실뿐 아니라 일부 의미·구조 표지를 다룬다는 점을 보여준다.
동시에 주어 교체와 비교 관계 역전처럼 문장 내 관계 구조가 바뀌는 경우에는 검사가 침묵할 수 있음을 보여준다. 사례별
원자료는 부록 F에 수록했다.

4.3 본실험 자동 검사 실측 결과

본실험의 자동 검사는 저장소 커밋 ce02da2의 preserve 검사를 사용해 실제로 실행했다(실행일 2026-07-17).
대상은 49개 앵커에서 생성한 변형 118건과 문체 통제 49건, 총 167쌍이다. 변형 118건 중 21건에서 표면 보존
실패가 발생했고, 의미·구조 경고는 0건, 무신호 통과는 97건이었다. 문체 통제 49건은 전부 무신호로, 과잉 경고율은
0%였다.

**표 2. 본실험 변형 유형별 자동 검사 결과(실측)**

|                      |               |            |                 |               |               |          |
| -------------------- | ------------- | ---------- | --------------- | ------------- | ------------- | -------- |
| **범주**               | **적용**        | **자동 신호**  | **판정 확정 의미 변경** | **무신호 의미 변경** | **커버리지**      | **무신호율** |
| number               | 17            | 17 (표면 실패) | 17              | 0             | 1.000         | 0.000    |
| direct\_quote        | 0 (단서 부재로 제외) | —          | —               | —             | NA            | NA       |
| english\_term        | 5             | 4 (표면 실패)  | 5               | 1             | 0.800         | 0.200    |
| negation             | 27            | 0          | 27              | 27            | 0.000         | 1.000    |
| hedge                | 27            | 0          | 23 (유보 4)       | 23            | 0.000         | 1.000    |
| causal               | 6             | 0          | 6               | 6             | 0.000         | 1.000    |
| structure\_bullet    | 0 (단서 부재로 제외) | —          | —               | —             | NA            | NA       |
| argument\_role       | 14            | 0          | 14              | 14            | 0.000         | 1.000    |
| comparison           | 8             | 0          | 8               | 8             | 0.000         | 1.000    |
| condition\_temporal  | 14            | 0          | 14              | 14            | 0.000         | 1.000    |
| style\_only\_control | 49            | 0 경고       | 0               | 0             | NA(과잉 경고율 0%) | NA       |

숫자 변형은 17건 전부 표면 실패로 포착되었다. 영문 용어 변형은 5건 중 4건이 포착되었으나, 2자 약어 RD의
삭제(A012)는 표면 사실 추출 정규식이 3자 이상 라틴 토큰만 인식하기 때문에 무신호로 통과했다. 반면 부정, 양태,
인과, 논항, 비교, 조건·시간 변형 96건은 전부 무신호였다. 파일럿에서 경고가 발생했던 부정·양태·인과 범주까지 침묵한
원인은 검사 단위에 있다. 의미 가드는 전후 텍스트의 표지 밀도 차이가 허용 오차(절대 2건, 비율 40%)를 함께 넘을
때만 경고하는데, 문장 단위 벤치마크에서는 표지 개수 변화가 1건에 그쳐 문턱에 도달하지 않는다. 또한 이번 변형에 사용된
양태 표현(것 같다, 듯, 보인다)과 인과·연결 표지(매개로, 으로, 면서, 참고해)는 가드의 정규식 어휘(수 있다,
가능성, 때문, 그래서 등)에 포함되어 있지 않았다.

모의 판정(3.7절)에서는 R1이 118건 전부를 의미 변경으로, R2가 109건을 의미 변경, 5건을 의미 유지, 4건을 판정
유보로 판정했다. 불일치 9건은 모두 양태(hedge) 범주의 완화 변형에 집중되었고, 합의 규칙 적용 후 의미 변경
114건, 판정 유보 4건으로 확정했다. 변형 사례의 단순 일치율은 92.4%, 통제 포함 전체 일치율은 94.6%, 전체
카파는 0.879였다. 변형 사례만의 카파는 R1의 판정이 한 범주에 몰리는 유병률 효과로 0에 수렴하므로 해석에서
제외한다. 판정 확정 기준의 종합 커버리지는 21/114(18.4%), 무신호 의미 변경률은
93/114(81.6%)다. 이 판정 수치는 LLM 모의 판정에 근거한 잠정치이며, 독립 인간 평가로 대체·검증되어야 한다.

5\. 논의

5.1 추적성은 품질 보증의 필요조건이지 충분조건이 아니다

이 사례에서 확인되는 가장 중요한 특성은 규칙 목록의 크기보다 여러 설계 층 사이의 연결이다. 설명된 패턴이 규칙 파일에
존재하고, 실행 코드가 이를 읽으며, 테스트가 발화를 확인하는 구조는 변경 이후 기능이 사라지는 위험을 줄인다.
그러나 추적성은 '무엇을 구현했는가'를 알려줄 뿐 '구현되지 않은 의미 변화가 무엇인가'를 자동으로 해결하지 않는다.

따라서 아티팩트 평가에서는 기능 목록과 커버리지 주장을 분리해야 한다. 14개 거시 패턴과 7개 Sunny-7 규칙이 있다는
사실은 문체 진단 체계의 범위를 설명한다. 그것이 모든 한국어 문체 문제를 포착한다거나 모든 의미 변화를 보존한다는
뜻은 아니다. 본 연구는 이 구분을 추적성 분석의 핵심 기준으로 삼았다.

5.2 보존 게이트는 종결 판정기가 아니라 검토 우선순위 생성기다

숫자나 영문 용어의 변경은 비교적 명확한 표면 사실로 확인할 수 있다. 부정, 양태, 인과 표지는 특정 표현의 변화로 위험 신호를
만들 수 있다. 반면 주어 교체나 비교 방향 역전은 문법적으로 자연스러운 문장을 만들면서도 주장 관계를 바꾼다. 이 변화를
포착하려면 문장 성분과 관계를 해석해야 하며, 단순한 문자열 보존만으로는 부족하다.

따라서 보존 게이트의 안전한 해석은 '통과했으니 의미가 보존되었다'가 아니라 '경고가 없으므로 지정된 규칙에서 추가 신호가
확인되지 않았다'이다. 자동 게이트는 위험 신호를 빠르게 선별하고, 무신호 영역을 인간 검토 대상으로 남기는 장치로
이해해야 한다.

5.3 검사 단위 불일치: 문서 밀도 가드와 문장 변형

본실험의 가장 중요한 실측 발견은 파일럿과 본실험의 결과 차이 자체다. 파일럿에서는 문서 수준 텍스트의 부정·양태·인과 변형이
경고를 발생시켰지만(9건 중 7건 포착), 문장 수준 벤치마크에서는 동일 범주 변형이 전부 무신호였다(96건 중 0건).
이는 구현 결함이라기보다 설계 전제의 문제다. 의미 가드는 여러 문단으로 이루어진 문서에서 표지 밀도가 크게 달라지는 경우를
겨냥해 허용 오차를 두었고, 그 허용 오차가 문장 단위에서는 모든 단일 변형을 통과시키는 크기다. 결과적으로 동일한 게이트가
검사 대상의 길이에 따라 사실상 다른 검사기가 된다.

이 발견은 보존 게이트를 평가할 때 커버리지 수치만이 아니라 검사 단위와 문턱 설계를 함께 보고해야 함을 보여준다. 짧은 문장에
대해 부정·양태 변화를 잡으려면 밀도 기준이 아니라 표지 유무의 이진 비교, 또는 형태소 분석 기반의 극성 비교가 필요하다.
정규식 어휘의 확장(것 같다, 듯하다, 보인다 등 양태 표현과 매개로, 면서 등 연결 표지)도 같은 방향의 개선이다. 이는
6절의 확장 계획과 부록 J의 실행 로그에 구체적으로 기록했다.

5.4 한국어 윤문과 AI 탐지를 혼동하지 말아야 한다

한국어 생성 텍스트 탐지 연구는 텍스트의 생성 출처를 판별하기 위해 한국어의 형태·띄어쓰기·구두점·통사 특성을 분석한다. 본
연구의 아티팩트는 생성 출처를 판정하지 않으며, 출력이 사람의 글처럼 보이는지를 단일 점수로 만들지도 않는다. 만약 두
문제를 'AI 티 제거'라는 표현으로 합치면 평가 목표가 모호해진다.

실제 논문에서 이 구분은 윤리적 의미도 갖는다. 탐지기를 통과한다는 사실은 글의 사실성이나 저자 책임을 보장하지 않는다. 반대로
윤문 도구가 자연스러운 표현을 만든다는 사실도 AI 사용 여부를 판정하지 않는다. 본 연구는 이 두 목표를 분리함으로써 윤문
도구의 평가를 의미 보존과 검토 가능성의 문제로 제한한다.

6\. 한계와 재현성

첫째, 본실험 자료는 KLUE 세 자료군의 문장 단위 텍스트로 한정된다. 결과 수치는 이 통제 변형 세트와 저장소 커밋
ce02da2에 대한 커버리지이며, 실제 사용 문서나 모든 한국어 문장을 대표하지 않는다. 특히 직접 인용과 불릿 구조 범주는
원문 단서 부재로 적용 사례가 0건이어서 이번 실행에서는 평가되지 않았다. 문서 단위 텍스트에 대한 파일럿 결과(9건 중
7건 포착)와 문장 단위 본실험 결과(96건 중 0건 포착)는 검사 단위가 다르므로 합산하지 않는다.

둘째, 의미 변화 판정이 독립 인간 평가가 아니다. 이번 실행의 판정은 LLM이 번역 전문가 페르소나 2종을 적용한 모의
판정이며, 변형 생성자와 판정자가 동일 모델이라는 순환성 문제를 갖는다. 페르소나 간 불일치(9건, 전부 양태
범주)와 일치도 수치도 이 구조 안에서 산출된 것이므로 인간 평가자 간 일치도로 해석할 수 없다. 무신호 의미 변경률
81.6%는 판정 근거가 대부분 연구자가 의도한 변형 설계와 일치하는 명백한 사례들이어서 방향은 안정적이라고 보지만, 확정 수치는
두 명 이상의 독립 한국어 평가자 판정으로 대체되어야 한다.

셋째, 변형 생성이 수작업 단일 위험 편집이라는 점도 한계다. 변형은 연구자(모델)가 작성하고 실행 로그로 공개하지만, 편집
과정에서 의도하지 않은 부수 변화가 남아 있을 가능성을 배제하려면 제3자의 변형 검수 절차가 필요하다.

넷째, 실제 생성형 AI 모델을 사용한 윤문 산출물 간 비교도 수행하지 않았다. korean-humanize는 호스트 모델과 실행
환경에 의존하므로, 모델·프롬프트·temperature·반복 횟수를 고정하지 않은 상태에서 모델 성능을 비교하면 재현성이
떨어진다. 이 비교는 본 연구의 핵심 질문을 넘어서는 후속 실험으로 남긴다.

실제 투고 논문으로 확장하려면 다음 절차를 완료해야 한다. 설명문·뉴스·학술 초록·보고서·에세이 등 최소 세 장르의 한국어 원문을
확보하고 숫자·인용·용어·부정·양태·인과·조건·비교·논항·구조 변형을 균형 있게 생성한다. 각 변형에 대해 의미 보존 여부를 두
명 이상의 한국어 검토자가 독립적으로 판정하고 불일치 사례를 조정한다. 보존 게이트의 변형 유형별 커버리지, 문체 통제 사례의
과잉 경고율, 의미 변형의 무신호율을 보고한다. 사용한 원문·변형 규칙·실행 로그·저장소 커밋을 공개해 재현성을 확보한다.

재현을 위해 저장소 커밋, 자료군, 행 ID, 변형 규칙, 실행 로그, 인간 평가 절차를 함께 기록해야 한다. 세부 절차와 중단
조건은 부록 B에 정리했다. 원문 전체는 자료 이용 조건을 확인한 뒤 필요한 범위에서만 보관·공개한다.

7\. 결론

본 연구는 Neosiki/korean-humanize v5.0.0을 한국어 윤문을 위한 소프트웨어 아티팩트로 보고
문서·규칙·구현·테스트의 추적성을 분석하고, KLUE 기반 통제 변형 벤치마크의 자동 검사를 실제로
실행했다. 핵심 규칙 분류와 실행·회귀 검증은 연결되어 있었고, 문장 단위 실측에서 보존 게이트는 숫자 변형을 전부, 영문
용어 변형을 대부분 포착했으며 문체 통제에는 과잉 경고를 내지 않았다. 그러나 부정·양태·인과·논항·비교·조건 변형은 전부
무신호로 통과했다. 표면 사실 잠금은 검사 단위와 무관하게 작동하는 반면, 밀도 기반 의미 가드는 문서 단위를
전제로 설계되어 문장 단위 변형에서 침묵한다는 것이 실측의 핵심이다. 현재 보존 게이트는 의미 보존의 종결 판정이
아니라, 표면 사실에 강하고 관계 의미에 침묵하는 위험 선별 장치다.

이 사례의 논문적 기여는 'AI 티를 제거한다'는 포괄적 주장에 있지 않다. 무엇을 규칙으로 잠그고, 무엇을 자동 검증하며,
무엇을 사람에게 남기는지를 추적 가능한 형태로 명세하고 실측했다는 데 있다. 향후 연구는 독립 인간 평가로 모의 판정을
대체해 무신호 의미 변경률을 확정하고, 문장 단위 이진 극성 비교와 가드 어휘 확장을 적용한 개선판을 동일 벤치마크로 재평가해야
한다. 그 결과가 추가되더라도 해당 수치는 특정 저장소 버전과 특정 자료 세트에 한정해 해석되어야 한다.

데이터·코드·윤리 진술

분석 대상 저장소의 버전과 커밋은 본문에 명시했다. 본실험 원문은 KLUE 공개 자료(저장소 라이선스 CC BY-SA 4.0
표시)에서 행 ID 기준으로 추출했으며, 실행 로그(korean-humanize\_run\_log.csv), 범주
집계(korean-humanize\_results\_filled.csv), 실행
요약(korean-humanize\_run\_summary.json), 실행 스크립트(run\_benchmark.py)를
함께 보관·공개한다. 결과물을 재배포할 때는 저장소 라이선스와 원자료 제공자의 개별 조건을 확인하고 원문 공개 범위를 별도로
판단한다. 의미 변화 판정은 LLM 모의 판정이며 독립 인간 평가가 아님을 거듭 명시한다. 향후 인간 평가를 수행할 경우
평가자 동의, 보상, 자료 보안, 연구윤리 심의 또는 면제 여부를 별도로 기록한다. 본 연구는 사람의 글과 AI 글을
판별하거나 개인의 AI 사용 여부를 추론하는 연구가 아니다. 저자는 분석 대상 도구의 개발·유지보수자이므로, 결과 해석에는
개발자 연구자 위치에 따른 확증 편향 가능성이 있다. 이를 완화하기 위해 실행 커밋, 변형 로그, 집계표, 모의 판정 기준과
독립 인간 평가로의 대체 계획을 공개한다.

참고문헌

Agrawal, S., & Carpuat, M. (2024). Do Text Simplification Models
Preserve Meaning? A Comprehensive Evaluation of Existing Benchmarks and
Their Alignment with Human Judgments. Transactions of the ACL.
https://aclanthology.org/2024.tacl-1.24/

bab2min. (2026). Kiwi. GitHub repository.
https://github.com/bab2min/kiwi

blader. (2026). humanizer. GitHub repository.
https://github.com/blader/humanizer

conorbronsdon. (2026). avoid-ai-writing. GitHub repository.
https://github.com/conorbronsdon/avoid-ai-writing

Gehrmann, S., Strobelt, H., & Rush, A. M. (2019). GLTR: Statistical
Detection and Visualization of Generated Text. ACL System
Demonstrations. https://aclanthology.org/P19-3019/

KLUE-benchmark. (2021). KLUE: Korean Language Understanding Evaluation.
GitHub repository and benchmark resources.
https://github.com/KLUE-benchmark/KLUE

LanguageTool Community. (2026). LanguageTool. GitHub repository.
https://github.com/languagetool-org/languagetool

Liang, W., Yuksekgonul, M., Mao, Y., Wu, E., & Zou, J. (2023). GPT
Detectors Are Biased Against Non-Native English Writers. arXiv.
https://arxiv.org/abs/2304.02819

Masrour, T., Emi, B., & Spero, M. (2025). DAMAGE: Detecting
Adversarially Modified AI-Generated Text. GenAIDetect.
https://aclanthology.org/2025.genaidetect-1.9/

Mitchell, E., et al. (2023). DetectGPT: Zero-Shot Machine-Generated Text
Detection using Probability Curvature. ICML.
https://proceedings.mlr.press/v202/mitchell23a.html

movemin03. (2025). Korector. GitHub repository.
https://github.com/movemin03/korector

National Institute of Korean Language. (2026). 모두의 말뭉치.
https://kli.korean.go.kr/corpus/main/requestMain.do?lang=en

Neosiki. (2026). korean-humanize. GitHub repository.
https://github.com/Neosiki/korean-humanize

Park, S., Kim, S., Kim, D.-K., & Han, Y.-S. (2025). KatFishNet:
Detecting LLM-Generated Korean Text through Linguistic Feature Analysis.
ACL. https://aclanthology.org/2025.acl-long.1030/

textlint. (2026). textlint. GitHub repository.
https://github.com/textlint/textlint

Wang, X., Liu, Q., Gui, T., Zhang, Q., et al. (2021). TextFlint: Unified
Multilingual Robustness Evaluation Toolkit for Natural Language
Processing. ACL System Demonstrations.
https://aclanthology.org/2021.acl-demo.41/

부록 A. 평가 프로토콜 요약

이 프로토콜은 Neosiki/korean-humanize의 보존 검사가 어떤 표면·구조·의미 변형을 포착하고, 어떤 변형을
통과시키는지 재현 가능하게 측정하기 위한 것이다. 측정 대상은 윤문 결과의 '자연스러움'이나 AI 생성 여부가
아니라, 지정된 보존 위험에 대한 통제 변형 커버리지다. 본실험은 공개·합법적으로 사용할 수 있는 한국어 자료 또는
연구자가 직접 작성한 자료만 사용하며, 개인정보, 비공개 과제물, 출처를 확인할 수 없는 인터넷 복사문은 제외한다.

**표 A-1. 장르별 권장 앵커 설계**

|           |             |                        |
| --------- | ----------- | ---------------------- |
| **장르**    | **권장 앵커 수** | **예시**                 |
| 학술 초록     | 10          | 연구 목적·방법·결과를 포함한 짧은 초록 |
| 정책·업무 보고서 | 10          | 수치·조건·권고가 포함된 문단       |
| 뉴스·설명문    | 10          | 사실·인용·인과 관계가 포함된 문단    |
| 에세이·칼럼    | 10          | 양태·평가·대조 관계가 포함된 문단    |
| 사용 안내·교육문 | 10          | 순서·조건·불릿 구조가 포함된 문단    |

각 사례에 대해 저장소 커밋, 실행 명령, 원문, 변형문, 표면 보존 결과, 경고 목록, 종료 상태를 함께 저장한다. 판정 결과는
표면 실패(보존 사실의 누락이 확인됨), 경고(사실은 남아 있지만 의미·구조 위험 신호가 발생함), 무신호 통과(변형이 있었으나
표면 실패와 경고가 모두 없음)의 세 단계로 기록한다. 문체 통제 사례는 숫자·인용·용어·핵심 관계를 보존하면서 표현만
바꾸며, 통제 사례에서 경고가 발생하면 과잉 경고로 기록한다.

재현성 체크리스트: 저장소 URL과 커밋 해시, Python 버전과 운영체제, 원문·변형문·정답 판정 파일, 변형 생성 규칙과
무작위 시드, 실행 명령과 표준 출력·오류 로그, 장르별 자료 수와 제외 기준, 인간 평가자 선정·교육·동의·보상 정보,
평가자 간 불일치 처리 규칙.

부록 B. 재현성 절차

**B.1 버전 고정.** 분석 대상 저장소: Neosiki/korean-humanize. 분석 커밋: ce02da2. 데이터
자료군: KLUE NLI v1.1, KLUE STS v1.1, KLUE YNAT v1.1. 데이터 행 매핑:
korean-humanize\_verified\_anchor\_ids.csv. 변형 설계:
korean-humanize\_benchmark\_manifest.csv. 변형 생성 시드: 20260717.

**B.2 실행 순서.**

1\. 원자료 JSON 세 파일을 이용 조건에 맞게 확보한다.

2\. 추출기(extract\_klue\_anchors.py)에 NLI·STS·YNAT 파일 경로를 입력한다.

3\. 생성된 앵커 JSONL의 행 수와 원자료 ID를 매니페스트와 대조한다.

4\. 각 앵커에 적용 가능한 변형만 생성하고, 적용하지 못한 변형은 제외 사유를 기록한다.

5\. 원문·변형문 쌍을 preserve 검사에 입력한다.

6\. 표면 실패, 의미 경고, 구조 경고, 종료 상태를 원자료 ID별로 저장한다.

7\. 인간 평가자가 자동 결과를 보지 않은 상태에서 의미 유지·의미 변경·판정 유보를 판정한다.

8\. 결과표 템플릿(korean-humanize\_results\_template.csv)에 유형별 집계값을 입력한다.

**B.3 실행 전 검증.** 50개 앵커 ID가 모두 원자료에 존재하는가. 각 앵커의 지정 필드가 비어 있지 않은가. 중복
텍스트가 제거되었는가. 변형문에 변형 대상 외의 변경이 들어가지 않았는가. 통제 사례에서 숫자·용어·인용·핵심 관계가
유지되는가. 원자료 레이블을 의미 보존의 정답으로 사용하지 않았는가. 원문 전체를 결과 저장소에 불필요하게 복사하지 않았는가.

**B.4 중단 조건.** 다음 상황에서는 해당 사례의 자동 결과를 보고하지 않고 excluded로 남긴다: 원자료 ID 또는
필드가 확인되지 않음, 원문이 너무 짧거나 문장 경계가 깨짐, 변형 유형을 한 가지 변화로 제한할 수 없음,
저작권·개인정보·이용 조건이 불명확함, 인간 평가자가 의미 변화를 판정할 문맥이 부족함.

**B.5 보고 원칙.** 본 부록의 절차가 완료되기 전에는 파일럿 결과와 본실험 결과를 합산하지 않는다. 본실험의 수치가
확보되더라도 결과는 특정 저장소 커밋과 특정 KLUE 기반 통제 변형 세트에 한정해 해석한다. 이는 한국어 윤문
전체의 품질이나 생성형 AI 탐지 성능을 주장하는 실험이 아니다.

부록 C. 검증된 앵커 ID 목록(50건)

공개 데이터 뷰어에서 확인한 50개 행의 식별자와 필드다. 출처 URL은 자료군별로 동일하다. KLUE-NLI:
https://huggingface.co/datasets/klue/klue/viewer/nli, KLUE-STS:
https://huggingface.co/datasets/klue/klue/viewer/sts, KLUE-YNAT:
https://huggingface.co/datasets/klue/klue/viewer/ynat.

|                |                   |                           |           |                          |
| -------------- | ----------------- | ------------------------- | --------- | ------------------------ |
| **anchor\_id** | **source\_group** | **source\_id**            | **field** | **verification\_status** |
| A001           | KLUE-NLI          | klue-nli-v1\_train\_00007 | premise   | verified                 |
| A002           | KLUE-NLI          | klue-nli-v1\_train\_00010 | premise   | verified                 |
| A003           | KLUE-NLI          | klue-nli-v1\_train\_00013 | premise   | verified                 |
| A004           | KLUE-NLI          | klue-nli-v1\_train\_00016 | premise   | verified                 |
| A005           | KLUE-NLI          | klue-nli-v1\_train\_00022 | premise   | verified                 |
| A006           | KLUE-STS          | klue-sts-v1\_train\_00000 | sentence1 | verified                 |
| A007           | KLUE-STS          | klue-sts-v1\_train\_00001 | sentence1 | verified                 |
| A008           | KLUE-STS          | klue-sts-v1\_train\_00002 | sentence1 | verified                 |
| A009           | KLUE-STS          | klue-sts-v1\_train\_00003 | sentence1 | verified                 |
| A010           | KLUE-STS          | klue-sts-v1\_train\_00004 | sentence1 | verified                 |
| A011           | KLUE-YNAT         | ynat-v1\_train\_00000     | title     | verified                 |
| A012           | KLUE-YNAT         | ynat-v1\_train\_00002     | title     | verified                 |
| A013           | KLUE-YNAT         | ynat-v1\_train\_00005     | title     | verified                 |
| A014           | KLUE-YNAT         | ynat-v1\_train\_00008     | title     | verified                 |
| A015           | KLUE-YNAT         | ynat-v1\_train\_00009     | title     | verified                 |
| A016           | KLUE-NLI          | klue-nli-v1\_train\_00025 | premise   | verified                 |
| A017           | KLUE-NLI          | klue-nli-v1\_train\_00031 | premise   | verified                 |
| A018           | KLUE-NLI          | klue-nli-v1\_train\_00034 | premise   | verified                 |
| A019           | KLUE-NLI          | klue-nli-v1\_train\_00037 | premise   | verified                 |
| A020           | KLUE-NLI          | klue-nli-v1\_train\_00040 | premise   | verified                 |
| A021           | KLUE-NLI          | klue-nli-v1\_train\_00043 | premise   | verified                 |
| A022           | KLUE-NLI          | klue-nli-v1\_train\_00046 | premise   | verified                 |
| A023           | KLUE-NLI          | klue-nli-v1\_train\_00052 | premise   | verified                 |
| A024           | KLUE-NLI          | klue-nli-v1\_train\_00055 | premise   | verified                 |
| A025           | KLUE-NLI          | klue-nli-v1\_train\_00058 | premise   | verified                 |
| A026           | KLUE-NLI          | klue-nli-v1\_train\_00061 | premise   | verified                 |
| A027           | KLUE-NLI          | klue-nli-v1\_train\_00064 | premise   | verified                 |
| A028           | KLUE-NLI          | klue-nli-v1\_train\_00067 | premise   | verified                 |
| A029           | KLUE-NLI          | klue-nli-v1\_train\_00070 | premise   | verified                 |
| A030           | KLUE-NLI          | klue-nli-v1\_train\_00071 | premise   | verified                 |
| A031           | KLUE-STS          | klue-sts-v1\_train\_00006 | sentence1 | verified                 |
| A032           | KLUE-STS          | klue-sts-v1\_train\_00009 | sentence1 | verified                 |
| A033           | KLUE-STS          | klue-sts-v1\_train\_00011 | sentence1 | verified                 |
| A034           | KLUE-STS          | klue-sts-v1\_train\_00015 | sentence1 | verified                 |
| A035           | KLUE-STS          | klue-sts-v1\_train\_00016 | sentence1 | verified                 |
| A036           | KLUE-STS          | klue-sts-v1\_train\_00018 | sentence1 | verified                 |
| A037           | KLUE-STS          | klue-sts-v1\_train\_00020 | sentence1 | verified                 |
| A038           | KLUE-STS          | klue-sts-v1\_train\_00022 | sentence1 | verified                 |
| A039           | KLUE-STS          | klue-sts-v1\_train\_00023 | sentence1 | verified                 |
| A040           | KLUE-STS          | klue-sts-v1\_train\_00026 | sentence1 | verified                 |
| A041           | KLUE-STS          | klue-sts-v1\_train\_00031 | sentence1 | verified                 |
| A042           | KLUE-STS          | klue-sts-v1\_train\_00033 | sentence1 | verified                 |
| A043           | KLUE-STS          | klue-sts-v1\_train\_00035 | sentence1 | verified                 |
| A044           | KLUE-STS          | klue-sts-v1\_train\_00037 | sentence1 | verified                 |
| A045           | KLUE-STS          | klue-sts-v1\_train\_00043 | sentence1 | verified                 |
| A046           | KLUE-YNAT         | ynat-v1\_train\_00015     | title     | verified                 |
| A047           | KLUE-YNAT         | ynat-v1\_train\_00018     | title     | verified                 |
| A048           | KLUE-YNAT         | ynat-v1\_train\_00019     | title     | verified                 |
| A049           | KLUE-YNAT         | ynat-v1\_train\_00023     | title     | verified                 |
| A050           | KLUE-YNAT         | ynat-v1\_train\_00024     | title     | verified                 |

부록 D. 벤치마크 매니페스트(50건)

앵커별 계획 변형(planned\_mutations)과 통제 사례 여부를 담은 실행 전 계획 문서 원본이다(status 열은 계획
수립 시점의 pending 표기를 보존). 원본 파일: klue-nli-v1.1\_train.json(NLI),
klue-sts-v1.1\_train.json(STS), ynat-v1.1\_train.json(YNAT). 실제 실행에서
A030은 원문 중복으로 제외되었고, 계획 변형 중 118건이 적용되었으며 제외 내역과 실측 결과는 부록 E·J에 있다.

|                |                   |                   |                                                |             |            |
| -------------- | ----------------- | ----------------- | ---------------------------------------------- | ----------- | ---------- |
| **anchor\_id** | **source\_group** | **target\_field** | **planned\_mutations**                         | **control** | **status** |
| A001           | KLUE-NLI          | premise           | negation;causal;argument;condition;number      | yes         | pending    |
| A002           | KLUE-NLI          | premise           | negation;causal;argument;comparison;hedge      | yes         | pending    |
| A003           | KLUE-NLI          | premise           | negation;causal;argument;condition;temporal    | yes         | pending    |
| A004           | KLUE-NLI          | premise           | negation;causal;argument;comparison;number     | yes         | pending    |
| A005           | KLUE-NLI          | premise           | negation;causal;argument;condition;hedge       | yes         | pending    |
| A006           | KLUE-STS          | sentence1         | hedge;comparison;argument;causal;temporal      | yes         | pending    |
| A007           | KLUE-STS          | sentence1         | hedge;comparison;argument;condition;number     | yes         | pending    |
| A008           | KLUE-STS          | sentence1         | hedge;comparison;argument;causal;negation      | yes         | pending    |
| A009           | KLUE-STS          | sentence2         | hedge;comparison;argument;condition;temporal   | yes         | pending    |
| A010           | KLUE-STS          | sentence2         | hedge;comparison;argument;causal;number        | yes         | pending    |
| A011           | KLUE-YNAT         | title             | number;english\_term;quote;bullet;causal       | yes         | pending    |
| A012           | KLUE-YNAT         | title             | number;english\_term;quote;structure;negation  | yes         | pending    |
| A013           | KLUE-YNAT         | title             | number;english\_term;quote;structure;hedge     | yes         | pending    |
| A014           | KLUE-YNAT         | title             | number;english\_term;quote;causal;comparison   | yes         | pending    |
| A015           | KLUE-YNAT         | title             | number;english\_term;quote;structure;condition | yes         | pending    |
| A016           | KLUE-NLI          | premise           | negation;causal;argument;comparison;temporal   | yes         | pending    |
| A017           | KLUE-NLI          | premise           | negation;causal;argument;condition;number      | yes         | pending    |
| A018           | KLUE-NLI          | premise           | negation;causal;argument;comparison;hedge      | yes         | pending    |
| A019           | KLUE-NLI          | premise           | negation;causal;argument;condition;temporal    | yes         | pending    |
| A020           | KLUE-NLI          | premise           | negation;causal;argument;comparison;number     | yes         | pending    |
| A021           | KLUE-NLI          | premise           | negation;causal;argument;condition;hedge       | yes         | pending    |
| A022           | KLUE-NLI          | premise           | negation;causal;argument;comparison;temporal   | yes         | pending    |
| A023           | KLUE-NLI          | premise           | negation;causal;argument;condition;number      | yes         | pending    |
| A024           | KLUE-NLI          | premise           | negation;causal;argument;comparison;hedge      | yes         | pending    |
| A025           | KLUE-NLI          | premise           | negation;causal;argument;condition;temporal    | yes         | pending    |
| A026           | KLUE-NLI          | premise           | negation;causal;argument;comparison;number     | yes         | pending    |
| A027           | KLUE-NLI          | premise           | negation;causal;argument;condition;hedge       | yes         | pending    |
| A028           | KLUE-NLI          | premise           | negation;causal;argument;comparison;temporal   | yes         | pending    |
| A029           | KLUE-NLI          | premise           | negation;causal;argument;condition;number      | yes         | pending    |
| A030           | KLUE-NLI          | premise           | negation;causal;argument;comparison;hedge      | yes         | pending    |
| A031           | KLUE-STS          | sentence1         | hedge;comparison;argument;causal;temporal      | yes         | pending    |
| A032           | KLUE-STS          | sentence1         | hedge;comparison;argument;condition;number     | yes         | pending    |
| A033           | KLUE-STS          | sentence1         | hedge;comparison;argument;causal;negation      | yes         | pending    |
| A034           | KLUE-STS          | sentence2         | hedge;comparison;argument;condition;temporal   | yes         | pending    |
| A035           | KLUE-STS          | sentence2         | hedge;comparison;argument;causal;number        | yes         | pending    |
| A036           | KLUE-STS          | sentence1         | hedge;comparison;argument;causal;negation      | yes         | pending    |
| A037           | KLUE-STS          | sentence2         | hedge;comparison;argument;condition;number     | yes         | pending    |
| A038           | KLUE-STS          | sentence1         | hedge;comparison;argument;causal;temporal      | yes         | pending    |
| A039           | KLUE-STS          | sentence2         | hedge;comparison;argument;condition;negation   | yes         | pending    |
| A040           | KLUE-STS          | sentence1         | hedge;comparison;argument;causal;number        | yes         | pending    |
| A041           | KLUE-STS          | sentence2         | hedge;comparison;argument;condition;temporal   | yes         | pending    |
| A042           | KLUE-STS          | sentence1         | hedge;comparison;argument;causal;negation      | yes         | pending    |
| A043           | KLUE-STS          | sentence2         | hedge;comparison;argument;condition;number     | yes         | pending    |
| A044           | KLUE-STS          | sentence1         | hedge;comparison;argument;causal;temporal      | yes         | pending    |
| A045           | KLUE-STS          | sentence2         | hedge;comparison;argument;condition;negation   | yes         | pending    |
| A046           | KLUE-YNAT         | title             | number;english\_term;quote;bullet;causal       | yes         | pending    |
| A047           | KLUE-YNAT         | title             | number;english\_term;quote;structure;negation  | yes         | pending    |
| A048           | KLUE-YNAT         | title             | number;english\_term;quote;structure;hedge     | yes         | pending    |
| A049           | KLUE-YNAT         | title             | number;english\_term;quote;causal;comparison   | yes         | pending    |
| A050           | KLUE-YNAT         | title             | number;english\_term;quote;structure;condition | yes         | pending    |

부록 E. 본실험 결과 집계표(자동 검사 실측·모의 판정)

자동 신호 수는 preserve 실측치, 의미 변경 수는 LLM 모의 판정(합의 확정) 기준이다. 분모가 0인 범주는 NA로
기록한다. 계획 목표는 범주당 25건이었으나 실제 적용 수는 원문 단서 존재 여부에 따라 달라졌다.

|                      |        |        |             |                   |              |              |          |                     |
| -------------------- | ------ | ------ | ----------- | ----------------- | ------------ | ------------ | -------- | ------------------- |
| **category**         | **계획** | **적용** | **자동 신호 수** | **모의 판정 의미 변경 수** | **무신호 변경 수** | **coverage** | **무신호율** | **status**          |
| number               | 25     | 17     | 17          | 17                | 0            | 1.000        | 0.000    | executed            |
| direct\_quote        | 25     | 0      | —           | —                 | —            | NA           | NA       | excluded(단서 부재)     |
| english\_term        | 25     | 5      | 4           | 5                 | 1            | 0.800        | 0.200    | executed            |
| negation             | 25     | 27     | 0           | 27                | 27           | 0.000        | 1.000    | executed            |
| hedge                | 25     | 27     | 0           | 23(유보 4)          | 23           | 0.000        | 1.000    | executed            |
| causal               | 25     | 6      | 0           | 6                 | 6            | 0.000        | 1.000    | executed            |
| structure\_bullet    | 25     | 0      | —           | —                 | —            | NA           | NA       | excluded(단서 부재)     |
| argument\_role       | 25     | 14     | 0           | 14                | 14           | 0.000        | 1.000    | executed            |
| comparison           | 25     | 8      | 0           | 8                 | 8            | 0.000        | 1.000    | executed            |
| condition\_temporal  | 25     | 14     | 0           | 14                | 14           | 0.000        | 1.000    | executed            |
| style\_only\_control | 50     | 49     | 0 경고        | 0                 | 0            | NA           | NA       | executed(과잉 경고율 0%) |

종합: 변형 적용 118건, 자동 신호 21건(전부 표면 실패), 경고 0건, 무신호 97건. 모의 판정 확정 의미 변경
114건, 판정 유보 4건. 종합 커버리지 21/114 = 0.184, 무신호 의미 변경률 93/114 = 0.816. 문체
통제 49건 전부 무경고.

부록 F. 파일럿 결과 원자료(10건)

|              |                      |                      |                   |                          |                          |
| ------------ | -------------------- | -------------------- | ----------------- | ------------------------ | ------------------------ |
| **case\_id** | **category**         | **observed\_result** | **surface\_pass** | **missing\_or\_warning** | **interpretation**       |
| P01          | surface\_number      | fail                 | false             | 숫자                       | 숫자 변경을 표면 사실 누락으로 포착     |
| P02          | surface\_quote       | warning              | true              | 직접 인용 개수                 | 인용 내용이 남아도 인용 구조 변화는 경고  |
| P03          | surface\_english     | fail                 | false             | 영문 용어                    | 영문 용어 삭제를 표면 사실 누락으로 포착  |
| P04          | semantic\_negation   | warning              | true              | 부정 표현                    | 부정 표현 변화 경고              |
| P05          | semantic\_hedge      | warning              | true              | 가능성·확률 표현                | 양태·확정성 변화 경고             |
| P06          | semantic\_causal     | warning              | true              | 인과 표지                    | 인과 연결 변화 경고              |
| P07          | structure\_bullets   | warning              | true              | 불릿 항목                    | 불릿 병합에 따른 구조 변화 경고       |
| P08          | semantic\_subject    | silent               | true              |                          | 주어·논항 관계 변화는 무신호 통과      |
| P09          | semantic\_comparison | silent               | true              |                          | 비교 방향 변화는 무신호 통과         |
| P10          | style\_only\_control | clean                | true              |                          | 보존 사실을 유지한 문체 변화에는 경고 없음 |

부록 G. 유사 GitHub 프로젝트 비교표

확인일: 2026-07-17. 이 비교는 저장소 README·공개 파일 구조·라이선스에 대한 질적 비교이며, 프로젝트 간 정확도
순위를 제시하지 않는다. 서로 다른 목적의 도구를 하나의 점수로 합산하지 않으며, 외부 프로젝트의 공개 설명은 연구 배경과
설계 비교에만 사용한다. 라이선스는 각 저장소의 현재 파일과 배포 조건을 최종 확인한 뒤 재사용 범위를 결정한다.

|                                |               |                                                             |                                               |                   |
| ------------------------------ | ------------- | ----------------------------------------------------------- | --------------------------------------------- | ----------------- |
| **프로젝트**                       | **주된 목적**     | **관찰된 설계**                                                  | **보존·평가 관점**                                  | **라이선스**          |
| Neosiki/korean-humanize        | 한국어 윤문 스킬     | 문체 패턴, 작업 모드, 의미·구조 보존 게이트, 회귀 테스트                          | 표면 사실·일부 의미 표지·구조를 검사하고 인간 검토 경계를 명시          | 저장소 기준 확인 필요      |
| blader/humanizer               | AI 문체 흔적 제거   | 33개 패턴, 음성·문체 조정, 2차 감사와 재작성                                | 의미 보존을 지침으로 두지만, 공개 README의 중심은 패턴 기반 재작성과 감사 | MIT               |
| conorbronsdon/avoid-ai-writing | AI 문체 감사·재작성  | Rewrite·Detect·Edit 모드, 음성 프로필, 2단계 탐지, detector·scripts 폴더 | 구조화된 감사와 변경 보고에 강점. 한국어 사실 보존 게이트와는 평가 목표가 다름 | MIT               |
| textlint/textlint              | 자연어 린팅 프레임워크  | 플러그인·규칙·포맷터 구조, --fix, dry-run                              | 생성형 재작성보다 규칙 실행·수정 가능성·리포팅에 강점                | MIT               |
| textflint/textflint            | NLP 견고성 평가    | 변형, 하위집단, 공격, Validator, Report 계층                          | 통제 변형을 만들고 검증·보고하는 파이프라인의 직접적인 방법론 선례         | GPL-3.0           |
| movemin03/korector             | 한국어 맞춤법·띄어쓰기  | 외부 검사기, 450자 청킹, 병렬 처리, 오류 수·HTML 결과·CLI                    | 한국어 오류 교정과 운영 안정성에 강점. 의미 보존 연구와는 별도          | Apache-2.0        |
| bab2min/Kiwi                   | 한국어 형태소 분석    | 세종 품사 체계, 문장 분리, 오타 교정, 평가 데이터·실행기                          | 한국어 형태·문장 구조를 보강할 수 있는 분석 인프라. 윤문 스킬 자체는 아님   | 저장소 LICENSE 확인 필요 |
| languagetool-org/languagetool  | 다국어 문법·스타일 검사 | 규칙 개발 체계, CLI·서버·API, 언어별 규칙                                | 대규모 규칙형 교정기의 비교 배경. 특정 한국어 윤문 목표와 직접 동일하지 않음  | LGPL-2.1-or-later |

부록 H. 검증 앵커 추출 스크립트(extract\_klue\_anchors.py)

원자료를 재배포하지 않고 검증된 앵커 행만 추출하는 스크립트 전문이다.

"""Extract the verified KLUE anchor rows without redistributing the
source corpus.

Example:

python extract\_klue\_anchors.py \\

\--nli path/to/klue-nli-v1.1\_train.json \\

\--sts path/to/klue-sts-v1.1\_train.json \\

\--ynat path/to/ynat-v1.1\_train.json \\

\--out korean-humanize\_anchors.jsonl

"""

from \_\_future\_\_ import annotations

import argparse

import csv

import json

import re

from pathlib import Path

from typing import Any, Iterable

SOURCE\_ARGS = {

"KLUE-NLI": "nli",

"KLUE-STS": "sts",

"KLUE-YNAT": "ynat",

}

def load\_json\_rows(path: Path) -\> list\[dict\[str, Any\]\]:

with path.open("r", encoding="utf-8") as handle:

data = json.load(handle)

if isinstance(data, list):

return \[row for row in data if isinstance(row, dict)\]

if isinstance(data, dict):

for key in ("data", "rows", "items"):

value = data.get(key)

if isinstance(value, list):

return \[row for row in value if isinstance(row, dict)\]

raise ValueError(f"Unsupported JSON structure: {path}")

def clean\_text(value: Any) -\> str:

return re.sub(r"\\s+", " ", str(value or "")).strip()

def load\_verified\_rows(path: Path) -\> list\[dict\[str, str\]\]:

with path.open("r", encoding="utf-8-sig", newline="") as handle:

return list(csv.DictReader(handle))

def load\_mutation\_plans(path: Path) -\> dict\[str, str\]:

with path.open("r", encoding="utf-8-sig", newline="") as handle:

return {

row\["anchor\_id"\]: row\["planned\_mutations"\]

for row in csv.DictReader(handle)

if row.get("anchor\_id")

}

def build\_index(rows: Iterable\[dict\[str, Any\]\]) -\> dict\[str,
dict\[str, Any\]\]:

index: dict\[str, dict\[str, Any\]\] = {}

for row in rows:

guid = clean\_text(row.get("guid"))

if guid:

index\[guid\] = row

return index

def main() -\> int:

parser = argparse.ArgumentParser(description=\_\_doc\_\_)

parser.add\_argument("--nli", type=Path, required=True)

parser.add\_argument("--sts", type=Path, required=True)

parser.add\_argument("--ynat", type=Path, required=True)

parser.add\_argument(

"--verified",

type=Path,

default=Path("korean-humanize\_verified\_anchor\_ids.csv"),

)

parser.add\_argument(

"--manifest",

type=Path,

default=Path("korean-humanize\_benchmark\_manifest.csv"),

)

parser.add\_argument("--out", type=Path, required=True)

args = parser.parse\_args()

source\_paths = {"nli": args.nli, "sts": args.sts, "ynat": args.ynat}

indexes = {

key: build\_index(load\_json\_rows(path)) for key, path in
source\_paths.items()

}

verified = load\_verified\_rows(args.verified)

plans = load\_mutation\_plans(args.manifest)

output: list\[dict\[str, Any\]\] = \[\]

missing: list\[str\] = \[\]

seen\_text: set\[str\] = set()

for row in verified:

anchor\_id = row\["anchor\_id"\]

source\_group = row\["source\_group"\]

source\_key = SOURCE\_ARGS\[source\_group\]

source\_id = row\["source\_id"\]

field = row\["field"\]

source\_row = indexes\[source\_key\].get(source\_id)

if source\_row is None:

missing.append(source\_id)

continue

text = clean\_text(source\_row.get(field))

if len(text) \< 8 or text in seen\_text:

missing.append(source\_id)

continue

seen\_text.add(text)

output.append(

{

"anchor\_id": anchor\_id,

"source\_group": source\_group,

"source\_id": source\_id,

"field": field,

"text": text,

"planned\_mutations": plans.get(anchor\_id, ""),

"anchor\_type": "original",

"control\_required": True,

}

)

if missing:

raise SystemExit(

"Missing or unusable source rows: " + ", ".join(sorted(set(missing)))

)

args.out.parent.mkdir(parents=True, exist\_ok=True)

with args.out.open("w", encoding="utf-8", newline="\\n") as handle:

for row in output:

handle.write(json.dumps(row, ensure\_ascii=False) + "\\n")

print(f"extracted={len(output)}")

print(f"output={args.out}")

return 0

if \_\_name\_\_ == "\_\_main\_\_":

raise SystemExit(main())

부록 I. 연구 상태와 투고 전 점검표

이 원고는 저장소 분석, 통제 변형 파일럿, 그리고 KLUE 기반 본실험 자동 검사 실측을 반영한 아티팩트 연구 원고다. 의미
변화 판정은 LLM 모의 판정이며 독립 인간 평가가 아니다.

**완료 항목:** 제목·초록·주제어, 연구 질문과 연구 범위, 관련 연구, 유사 GitHub 프로젝트 비교, 저장소 버전·커밋
고정, 추적성 분석, 통제 변형 파일럿, 원자료 추출 실행(49개 앵커, A030 중복 제외), 변형 118건·통제 49건
생성과 제외 132건 사유 기록, preserve 실행 로그와 결과 집계, LLM 모의 판정 2패스와 일치도 계산, 결과표
실측치 반영, 데이터·코드·윤리 진술, 재현성 부록.

**실제 투고 전 필수:** 두 명 이상 독립 인간 평가자의 의미 판정으로 모의 판정 대체, 인간 평가자 간 일치도 계산, 변형문
제3자 검수, 문서 단위 텍스트 벤치마크 추가(직접 인용·불릿 범주 포함), 투고 학술지 양식·분량·인용 스타일 적용, 저자
정보와 연구비·이해상충 진술 입력.

현재 상태는 자동 검사 실측과 모의 판정을 갖춘 시스템 사례 연구 원고다. 독립 인간 판정으로 모의 판정을 대체하면 일반 연구논문
형식의 완결성을 갖춘다.

부록 J. 본실험 실행 기록

**J.1 실행 환경.** 실행일 2026-07-17. 분석 커밋 ce02da2의 scripts/krh.py
preserve\_data 함수를 직접 호출. 원문은 Hugging Face datasets-server
API(klue/klue의 nli·sts·ynat train 분할)에서 행 ID 기준 추출. 변형 생성 시드
20260717(수작업 편집의 사례 배정 기준).

**J.2 사례 구성.** 계획 250건(50 앵커 × 5 변형) 중 A030은 원문 중복으로 앵커째 제외(5건), 127건은
원문 단서 부재로 제외해 변형 118건을 적용했다. 제외 사유 분포: 직접 인용 표지 부재(전 앵커), 불릿·표 구조
부재(전 앵커), 일부 앵커의 숫자·영문 용어·인과·비교·조건 단서 부재. 문체 통제는 49건으로, 각 통제문은 숫자·영문
용어·직접 인용·부정·양태·인과 표지 개수를 원문과 동일하게 유지한 채 어휘·어순만 바꿨다.

**J.3 자동 검사 결과 분포.** 변형 118건: 표면 실패 21건(숫자 17, 영문 용어 4), 의미·구조 경고 0건,
무신호 97건. 통제 49건: 전부 무신호. 영문 용어 무신호 1건은 2자 약어 RD로, 표면 사실 추출 정규식의 3자
이상 조건에 걸리지 않았다.

**J.4 모의 판정 기록.** R1(엄격): 변경 118. R2(관대): 변경 109, 유지 5, 유보 4. 불일치 9건은 전부
양태 완화 변형(A005, A006, A008, A032, A033, A037, A039, A042, A044). 합의 확정:
변경 114, 유보 4(A005, A008, A032, A039의 hedge). 일치율: 변형 92.4%, 전체
94.6%. 카파: 전체 0.879, 변형 한정 0(유병률 효과로 해석 제외). 판정 주체는 LLM(Claude) 페르소나
2종이며 독립 인간 평가가 아님을 기록한다.

**J.5 산출물 파일.** run\_benchmark.py(실행 스크립트·전체 변형문 수록),
korean-humanize\_run\_log.csv(167쌍 사례별 결과),
korean-humanize\_results\_filled.csv(범주 집계),
korean-humanize\_run\_summary.json(요약 통계).
