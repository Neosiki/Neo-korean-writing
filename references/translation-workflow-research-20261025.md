# GitHub 글쓰기 스킬 대조와 적용 — 2026-10-25

원본 SKILL.md와 관련 문서를 읽고 네오코리안라이팅 v10.3과 비교했다. 아래는 접근을 참고한 기록이다. 외부 스킬·스크립트를 설치하거나 실행하지 않았고 문구·코드를 복사하지 않았다. 새 기록 helper·프롬프트·테스트는 별도로 작성했다.

- [baoyu-translate](https://github.com/JimLiu/baoyu-skills/blob/1567581c26ec29f4216c6e6835415bf30343b0e3/skills/baoyu-translate/SKILL.md)와 [정밀 번역 절차](https://github.com/JimLiu/baoyu-skills/blob/1567581c26ec29f4216c6e6835415bf30343b0e3/skills/baoyu-translate/references/refined-workflow.md): 초안·비평·수정·완성본을 저장하고 기존 번역을 이어가는 방법을 참고했다. 전체 공유 정보와 마지막 병합 검토를 기존 인계서·청킹 계약에 연결했다. 최초 설정 완료까지 번역을 막는 절차, storytelling 기본값, 임의의 설명 추가, 공유 프롬프트만으로 일관성이 보장된다는 주장은 채택하지 않았다. 병렬 에이전트는 필수 조건이 아니다.
- [humanizer-kr](https://github.com/hjongc/humanizer-kr/blob/a1a7069a32f669afe4b10e35e9522ff504a13263/skills/humanizer-kr/SKILL.md): 한국어의 독자 관계·대상·행동을 읽는 기준을 참고했다. 기존 레지스터·문체 보존 기능을 중복 추가하지 않고 최종 한국어 읽기의 장르별 질문을 보강했다. 자연스러움을 이유로 가능성·의무·인과를 바꾸지 않는다.
- [WRITING.md의 문체 표본](https://github.com/Anbeeld/WRITING.md/blob/0c127ca4a4e51debec5adf4816f2bf464d83438b/skills/writing/references/voice-calibration.md)과 [출력 정리](https://github.com/Anbeeld/WRITING.md/blob/0c127ca4a4e51debec5adf4816f2bf464d83438b/skills/writing/references/editing-integrity.md): 말투의 근거와 표본의 내용을 분리하고 최종 원고에 도구·초안 메모가 남지 않게 하는 접근을 참고했다. 영어 구두점 규칙을 한국어 금칙어로 이식하지 않았다.
- [patina](https://github.com/devswha/patina/blob/9ad44bcf45c675914c254c1839eaf4d3acf49f7e/SKILL.md): 발견 위치에 한정한 수정과 검토·재시도 분리를 대조했다. 이미 있는 충실성·자연스러움·과편집 검사를 유지하고 바뀐 파일의 후속 기록만 무효화하는 동작을 보완했다. MPS·자체 점수나 의심 구간 임계값을 품질 인증으로 도입하지 않았다.

Andrew Ng translation-agent와 blader/humanizer는 [기존 조사](github-writing-research-20261021.md)에서 이미 다뤘으므로 신규 기능으로 세지 않았다. 별 개수는 저장소 관심도이며 한국어 번역 성능·독자 선호의 근거가 아니다.

실제 변경: 초안 프롬프트의 일률적인 분량 예산과 전역 역어 강제를 정리했다. 숫자·형식은 점검기 9.6 정책으로 연결했다. 기존 Writer–Editor JSON에 선택적 translation_workflow를 두어 원문·용어집·설정·산출물 해시와 판단의 적용 범위를 기록한다. 단계 기록은 검수 완료의 증거가 아니다.

검증은 자체 예문의 진행 상태·해시 변경·보류 판단·재개 동작 회귀다. 외부 번역 전문·유료 기사 본문은 포함하지 않았다. 언어 품질 향상의 크기나 다른 스킬보다 낫다는 주장은 실제 원고의 사람 평가 없이는 하지 않는다.
