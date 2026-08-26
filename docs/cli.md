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
| `neo-korean-writing translation-audit 원문.md 번역문.md --direction en-to-ko --literary --json` | 번역문 충실성·문학적 위험을 확인합니다. |

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
python3 -m pip install /tmp/neo-korean-writing-dist/neo_korean_writing-0.1.0-py3-none-any.whl
neo-korean-writing assets
```

패키지 공개 배포 전에는 빌드본의 메타데이터, 자산 포함 여부, 격리 환경에서의 `init`·`diagnose`·`verify` 동작을 확인해야 합니다. PyPI 등 외부 패키지 저장소에 실제로 게시하는 작업은 별도의 계정·권한·버전 승인 절차가 필요합니다.
