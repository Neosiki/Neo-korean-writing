# Neo-korean-writing CLI

`neo-korean-writing`은 저장소의 프롬프트·템플릿·진단 도구를 설치형 명령으로 묶은 CLI입니다. 외부 모델 API를 호출하거나 원고를 자동으로 덮어쓰지 않습니다. 작업공간을 만들고, 윤문 전후 원고의 보존 항목을 대조하며, 번역문 대조와 문체 진단을 실행하는 로컬 도구입니다.

## 설치

저장소를 내려받은 뒤 현재 프로젝트를 설치합니다.

```bash
python3 -m pip install .
neo-korean-writing --version
```

개발 중에는 변경 사항을 바로 반영하는 편집 가능 설치를 사용할 수 있습니다.

```bash
python3 -m pip install -e .
```

## 핵심 명령

| 명령 | 용도 |
|---|---|
| `neo-korean-writing assets` | 내장 프롬프트·템플릿과 작업공간 프로필을 확인합니다. |
| `neo-korean-writing show prompt standard-editing` | 범용 윤문 프롬프트를 표준 출력으로 확인합니다. |
| `neo-korean-writing show template editing-brief` | 작업 의뢰 템플릿을 표준 출력으로 확인합니다. |
| `neo-korean-writing init 경로 --profile general` | 프롬프트·LOCK·결과 전달 템플릿이 포함된 작업공간을 만듭니다. |
| `neo-korean-writing diagnose 원문.md --profile official --json` | 문체·리듬·반복 후보를 진단합니다. |
| `neo-korean-writing verify 원문.md 수정본.md --strict` | 숫자·직접 인용·영문 용어·구조 변화와 의미 경고를 대조합니다. |
| `neo-korean-writing structure 원문.md --json` | 고정 슬롯 누출·과도한 헤딩·공식적 도입과 결론을 진단합니다. |
| `neo-korean-writing handoff-validate 인계.json --json` | 작성 의도·출처·LOCK·변경 예산 인계 계약을 검사합니다. |
| `neo-korean-writing morphology 원문.md --json` | `kiwipiepy` 설치 시 형태소·종결·조사 분포를 보조 진단합니다. |
| `neo-korean-writing translation-audit 원문.md 번역문.md --direction en-to-ko --literary --json` | 번역문 충실성·문학적 위험을 확인합니다. |
| `neo-korean-writing translation-audit 원문.md 후편집본.md --baseline 초벌번역.md --intensity 기본` | 번역투 유형(T1~T7·P1~P4·J1)별 진단과 원천 힌트, 어체 혼용·목록 마침표·완충 표현, 초벌 대비 후편집 범위와 과편집 경고(EDIT-1·EDIT-2)를 출력합니다. |
| `neo-korean-writing translation-audit 원문.md 번역문.md --glossary 용어집.tsv --strict` | 용어집 일관성(권장어·허용 변형·strict 혼용, 사용 현황)을 검사하고 치명·주요 위험이 있으면 멈춥니다. 위험마다 심각도와 `fix_order`를 출력합니다. |

## 작업공간 시작 예시

보도자료를 다듬는 작업공간은 다음처럼 만듭니다.

```bash
neo-korean-writing init newsroom-release --profile press-release
cd newsroom-release
```

생성되는 파일은 다음과 같습니다.

```text
newsroom-release/
├── README.md
├── prompts/
│   └── press-release-editing.md
└── templates/
    ├── editing-brief.md
    ├── lock-register.md
    └── editing-delivery.md
```

먼저 `templates/editing-brief.md`에 목적, 독자, 매체, 장르, 윤문 강도를 기록합니다. 이후 숫자·날짜·인명·직접 인용·링크·표 항목은 `templates/lock-register.md`에 LOCK으로 기록하고, 알맞은 프롬프트와 원고를 함께 전달합니다. 결과를 채택하기 전에는 `editing-delivery.md`에 수정 근거와 `[확인 필요]` 항목을 남깁니다.

## 배포 산출물 만들기

표준 Python source distribution과 wheel을 빌드합니다. 저장소의 기존 `.skill` 배포물과 달리, 이 명령은 `pip install` 가능한 Python 패키지를 만듭니다.

```bash
python3 -m build --outdir /tmp/neo-korean-writing-dist
python3 -m twine check /tmp/neo-korean-writing-dist/*
```

생성된 wheel은 네트워크 없이 설치해 검증할 수 있습니다.

```bash
python3 -m pip install /tmp/neo-korean-writing-dist/neo_korean_writing-10.0.0-py3-none-any.whl
neo-korean-writing assets
```

선택형 형태소 계층은 `python3 -m pip install '.[morphology]'`로 설치합니다. 설치하지 않아도 기본 진단·보존 결과는 동일하게 작동합니다.

패키지 공개 배포 전에는 빌드본의 메타데이터, 자산 포함 여부, 격리 환경에서의 `init`·`diagnose`·`verify` 동작을 확인해야 합니다. PyPI 등 외부 패키지 저장소에 실제로 게시하는 작업은 별도의 계정·권한·버전 승인 절차가 필요합니다.
# 문서 맥락 감사와 번역 v8 옵션

Claude 설정에 올릴 때는 단일 `SKILL.md` 형식으로 패키징한다. 하위 글쓰기 경로는 참고 문서로 보존된다.

```text
python scripts/build_skill_package.py --target claude --output dist/neo-korean-writing-claude.skill
```

```text
neo-korean-writing translation-audit source.md target.md --glossary glossary.tsv --strict --json
neo-korean-writing context-audit context-manifest.json --strict --json
neo-korean-writing init work --profile context
neo-korean-writing show template translation-glossary
neo-korean-writing show prompt translation-draft-critique-edit
```

`context-manifest.json`은 실제 대상 파일·용어·별칭·주장과 정확한 근거로 채운다. 상대 경로는 manifest 폴더 기준이다. 자세한 범위와 종료 코드는 `references/document-context.md`를 참고한다. 기본 용어집과 manifest는 예시이며 자동으로 사실을 승인하는 기준이 아니다.
