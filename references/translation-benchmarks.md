# v7 한국어 번역 서비스·벤치마크 참고 지도

아래 목록은 “항상 1위인 서비스”를 선언하는 순위표가 아니다. 언어 방향·장르·평가 방식에 따라 결과가 달라지므로, v7은 서비스 이름보다 **번역 전후 대조와 사람 검수**를 우선한다. 목록은 GitHub, 논문, 블로그·보고서에서 반복적으로 확인되는 서비스·모델·평가 도구를 윤문 스킬의 검토 대상으로 묶은 것이다.

## v7 참고 Top 10

| 참고 순서 | 서비스·모델 | 근거와 강점 | v7에서의 사용 |
|---:|---|---|---|
| 1 | DeepL | 독립 IT 텍스트 시험에서 영↔한이 강하게 평가됨. 공식 파일 번역 평가도 언어쌍별 평가를 제공함. | 문장 자연성 후보, 단 도메인 의존성 확인 |
| 2 | Papago | 한국어·영어·중국어 등 네이버 언어쌍과 텍스트·이미지·문서·음성·웹 번역을 제공함. | 한국어 관용·고유어 후보, 문맥 대조 |
| 3 | Google Translate | 넓은 언어 범위와 범용 서비스. 한국어 문화어 연구의 비교 기준으로 자주 사용됨. | 범용 baseline, 직역·문화어 누락 점검 |
| 4 | ChatGPT 계열 | SemEval-2025 영한 평가에서 o1·o1-mini·GPT-4o가 자동 지표 상위권에 포함됨. | 문맥 설명·대안 생성, 사실 잠금 필수 |
| 5 | Gemini 계열 | COLING 2025 문맥 담화 평가에서 GPT-4o와 함께 비교되었고, 자막 보고서에서도 한국어 후보로 평가됨. | 문맥·화용 대조, 자동 점수 단독 사용 금지 |
| 6 | Claude 계열 | WMT25 영한 인적 평가에 포함된 범용 LLM 계열. | 문학·문맥 후보, 인과·양태 재검수 |
| 7 | TranslateGemma | Google의 번역 특화 공개 모델군(4B·12B·27B), 한국어 포함 55개 언어. | 로컬·재현 가능한 번역 baseline |
| 8 | Hunyuan-MT / Shy-Hunyuan | Tencent Hunyuan-MT GitHub와 WMT25 관련 연구. 번역 특화 모델과 앙상블 접근. | 공개 모델 비교, 모델 주장과 독립 평가 분리 |
| 9 | Yanolja Rosetta | 한국어 호텔·카탈로그·구조화 JSON에 맞춘 모델. 공개 WMT24++ 영한 수치 제공. | 구조화 문서·관광 도메인 후보, 비정형 문장에는 제한 |
| 10 | Microsoft Translator | Azure의 공식 한국어 지원과 기업용 API·문서 워크플로. | 엔터프라이즈 baseline, 제품·용어집 보존 검토 |

## 벤치마크와 GitHub 자산

- [WMT25 General MT](https://github.com/wmt-conference/wmt25-general-mt) 및 [WMT25 보고서](https://steinst.is/files/2025_wmt_sharedtask.pdf): 인적 평가가 자동 지표와 다른 순서를 만들 수 있음을 확인하는 최신 비교 기준.
- [SemEval-2025 Team ACK 논문](https://aclanthology.org/2025.semeval-1.309.pdf): 5,082 영한 문장쌍, 13개 모델, 자동 평가와 이중언어 사람 평가를 함께 사용. 개체명·직역·음역·word-for-word 실패가 중요 오류로 보고됨.
- [COLING 2025 문맥 인식 한영 담화 평가](https://aclanthology.org/2025.coling-main.110.pdf): 문맥과 단계별 프롬프트가 사람 선호에 영향을 주며 자동 지표만으로 충분하지 않음을 보임.
- [KorT](https://github.com/deveworld/KorT): 모호성·관용어·문화 참조를 포함한 한국어 번역 benchmark와 LLM-as-a-judge 흐름.
- [Iris Translation](https://github.com/davidkim205/translation): 한국어→영어 모델 비교와 BLEU·round-trip 평가 예시.
- [Roundtrip translation benchmark](https://github.com/lechmazur/translation): 의미·톤·register 보존을 0~10으로 평가하는 다국어 비교 자산.
- [TranslateGemma 공식 소개](https://blog.google/innovation-and-ai/technology/developers-tools/translategemma/), [한국어 소개](https://blog.google/intl/ko-kr/company-news/technology/translategemma/).
- [Hunyuan-MT GitHub](https://github.com/Tencent-Hunyuan/Hunyuan-MT), [Shy-Hunyuan 논문](https://aclanthology.org/2025.wmt-1.36/).
- [YanoljaNEXT-Rosetta-12B](https://huggingface.co/yanolja/YanoljaNEXT-Rosetta-12B-2510): 구조화 관광 도메인 특화 설명과 제한.

## 스킬에 반영한 결론

1. 자동 BLEU·COMET·유창성 점수는 후보 선별용으로만 사용한다.
2. 번역문에는 `FID-1~7`을 적용해 주체·부정·양태·인과·구조·숫자·번역투를 분리 검토한다.
3. 문학 번역에는 `LIT-1~3`을 추가해 정조·모호성·반복·감정 부사 삽입을 확인한다.
4. 서비스 간 “Top” 비교는 원문·장르·언어 방향·평가자·날짜를 함께 기록한다.
