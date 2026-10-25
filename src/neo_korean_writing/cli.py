from __future__ import annotations

import argparse
import shutil
import sys
from importlib import resources
from pathlib import Path
from typing import Iterable

from . import __version__
from .engine import korean_writing

PROMPTS = {
    "standard-editing": "standard-editing.md",
    "press-release-editing": "press-release-editing.md",
    "longform-editing": "longform-editing.md",
    "translation-postediting": "translation-postediting.md",
    "translation-continuation": "translation-continuation.md",
    "translation-semantic-review": "translation-semantic-review.md",
    "translation-reader-review": "translation-reader-review.md",
    "translation-draft-critique-edit": "translation-draft-critique-edit.md",
    "translation-craft-review": "translation-craft-review.md",
    "news-translation-review": "news-translation-review.md",
    "cross-document-editing": "cross-document-editing.md",
    "detect-only": "detect-only.md",
}
TEMPLATES = {
    "editing-brief": "editing-brief.md",
    "lock-register": "lock-register.md",
    "editing-delivery": "editing-delivery.md",
    "writer-editor-handoff": "writer-editor-handoff.json",
    "translation-glossary": "translation-glossary.tsv",
    "translation-glossary-scoped": "translation-glossary-scoped.json",
    "translation-review-brief": "translation-review-brief.md",
    "translation-segments": "translation-segments.json",
    "translation-reader-questions": "translation-reader-questions.json",
    "context-manifest": "context-manifest.json",
}
PROFILES = {
    "general": ("standard-editing",),
    "press-release": ("press-release-editing",),
    "longform": ("longform-editing",),
    "translation": ("translation-postediting", "translation-draft-critique-edit", "translation-craft-review", "translation-continuation", "translation-semantic-review", "translation-reader-review"),
    "news-translation": ("translation-postediting", "translation-draft-critique-edit", "news-translation-review", "translation-continuation", "translation-semantic-review", "translation-reader-review"),
    "context": ("cross-document-editing",),
    "detect": ("detect-only",),
}


def _asset(kind: str, filename: str):
    return resources.files("neo_korean_writing").joinpath("assets", kind, filename)


def _read_asset(kind: str, filename: str) -> str:
    return _asset(kind, filename).read_text(encoding="utf-8")


def _write_asset(kind: str, filename: str, destination: Path, force: bool) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        raise FileExistsError(f"이미 존재합니다: {destination} (덮어쓰려면 --force 사용)")
    destination.write_text(_read_asset(kind, filename), encoding="utf-8")
    return destination


def _print_assets() -> None:
    print("프롬프트:")
    for name, filename in PROMPTS.items():
        print(f"  {name:<24} prompts/{filename}")
    print("템플릿:")
    for name, filename in TEMPLATES.items():
        print(f"  {name:<24} templates/{filename}")
    print("작업공간 프로필:")
    for name, prompt_names in PROFILES.items():
        print(f"  {name:<24} {', '.join(prompt_names)} + 공통 템플릿")


def cmd_assets(_: argparse.Namespace) -> int:
    _print_assets()
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    catalog = PROMPTS if args.kind == "prompt" else TEMPLATES
    filename = catalog.get(args.name)
    if filename is None:
        choices = ", ".join(catalog)
        raise SystemExit(f"알 수 없는 {args.kind}: {args.name}. 선택 가능: {choices}")
    directory = "prompts" if args.kind == "prompt" else "templates"
    sys.stdout.write(_read_asset(directory, filename))
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.directory).expanduser().resolve()
    prompt_names = PROFILES[args.profile]
    destinations = [
        target / "prompts" / PROMPTS[name] for name in prompt_names
    ] + [
        target / "templates" / filename for filename in TEMPLATES.values()
    ] + [target / "README.md"]
    if not args.force:
        existing = next((path for path in destinations if path.exists()), None)
        if existing is not None:
            raise SystemExit(f"이미 존재합니다: {existing} (덮어쓰려면 --force 사용)")

    created: list[Path] = []
    try:
        for name in prompt_names:
            created.append(_write_asset("prompts", PROMPTS[name], target / "prompts" / PROMPTS[name], args.force))
        for filename in TEMPLATES.values():
            created.append(_write_asset("templates", filename, target / "templates" / filename, args.force))
        readme = target / "README.md"
        readme.write_text(
            "# Neo-korean-writing 작업공간\n\n"
            f"- 선택한 프로필: `{args.profile}`\n"
            "- `templates/editing-brief.md`를 먼저 채우고, 숫자·인용·고유명사는 "
            "`templates/lock-register.md`에 기록합니다.\n"
            "- 프롬프트로 작업한 뒤 `templates/editing-delivery.md`에 변경 근거와 "
            "[확인 필요] 항목을 남깁니다.\n\n"
            "## 진단 예시\n\n"
            "```bash\n"
            "neo-korean-writing diagnose original.md --profile official --json\n"
            "neo-korean-writing verify original.md revised.md --strict\n"
            "```\n",
            encoding="utf-8",
        )
        created.append(readme)
    except FileExistsError as error:
        raise SystemExit(str(error)) from error

    print(f"작업공간을 만들었습니다: {target}")
    for path in created:
        print(f"  + {path.relative_to(target)}")
    return 0


def _engine_call(command: str, arguments: Iterable[str]) -> int:
    handler = korean_writing.CMDS[command]
    try:
        result = handler(list(arguments))
    except SystemExit as error:
        return int(error.code) if isinstance(error.code, int) else 1
    return int(result) if isinstance(result, int) else 0


def cmd_diagnose(args: argparse.Namespace) -> int:
    return _engine_call("diagnose", args.arguments)


def cmd_verify(args: argparse.Namespace) -> int:
    arguments = [args.original, args.revised]
    if args.strict:
        arguments.append("--strict")
    if args.json:
        arguments.append("--json")
    return _engine_call("preserve", arguments)


def cmd_translation_audit(args: argparse.Namespace) -> int:
    arguments = [args.source, args.target, "--direction", args.direction]
    for key in ("reader_review", "link_root", "link_map"):
        if getattr(args, key):
            arguments.extend(["--" + key.replace("_", "-"), getattr(args, key)])
    if args.require_reader_review:
        arguments.append("--require-reader-review")
    if args.semantic_review:
        arguments.extend(["--semantic-review", args.semantic_review])
    if args.semantic_packet:
        arguments.extend(["--semantic-packet", args.semantic_packet])
    if args.require_semantic_review:
        arguments.append("--require-semantic-review")
    arguments.extend(["--format", args.format_profile])
    if args.domain:
        arguments.extend(["--domain", args.domain])
    if args.segment_id:
        arguments.extend(["--segment-id", args.segment_id])
    if args.literary:
        arguments.append("--literary")
    if args.json:
        arguments.append("--json")
    if args.glossary:
        arguments.extend(["--glossary", args.glossary])
    if args.strict:
        arguments.append("--strict")
    if args.baseline:
        arguments.extend(["--baseline", args.baseline])
    arguments.extend(["--intensity", args.intensity])
    return _engine_call("translation-audit", arguments)


def cmd_translation_session(args: argparse.Namespace) -> int:
    return _engine_call("translation-session", args.arguments)

def cmd_translation_impact(args: argparse.Namespace) -> int:
    return _engine_call("translation-impact", args.arguments)

def cmd_translation_reader(args: argparse.Namespace) -> int:
    return _engine_call("translation-reader", args.arguments)


def cmd_context_audit(args: argparse.Namespace) -> int:
    arguments = [args.manifest]
    if args.json:
        arguments.append("--json")
    if args.strict:
        arguments.append("--strict")
    return _engine_call("context-audit", arguments)


def cmd_structure(args: argparse.Namespace) -> int:
    arguments = [args.file]
    if args.json:
        arguments.append("--json")
    return _engine_call("structure", arguments)


def cmd_morphology(args: argparse.Namespace) -> int:
    arguments = [args.file]
    if args.json:
        arguments.append("--json")
    return _engine_call("morphology", arguments)


def cmd_handoff_validate(args: argparse.Namespace) -> int:
    arguments = [args.file]
    if args.json:
        arguments.append("--json")
    return _engine_call("handoff-validate", arguments)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="neo-korean-writing",
        description="한글 글쓰기(윤문) 프롬프트·템플릿·진단 CLI",
    )
    parser.add_argument("--version", action="version", version=f"neo-korean-writing {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    assets = subparsers.add_parser("assets", help="내장 프롬프트·템플릿 목록")
    assets.set_defaults(handler=cmd_assets)

    show = subparsers.add_parser("show", help="내장 프롬프트 또는 템플릿 출력")
    show.add_argument("kind", choices=("prompt", "template"))
    show.add_argument("name")
    show.set_defaults(handler=cmd_show)

    init = subparsers.add_parser("init", help="작업공간에 프롬프트·템플릿 복사")
    init.add_argument("directory", nargs="?", default="neo-korean-writing-workspace")
    init.add_argument("--profile", choices=tuple(PROFILES), default="general")
    init.add_argument("--force", action="store_true", help="기존 파일 덮어쓰기")
    init.set_defaults(handler=cmd_init)

    diagnose = subparsers.add_parser("diagnose", help="원고의 문체·리듬 후보 진단")
    diagnose.add_argument("arguments", nargs=argparse.REMAINDER, help="원본 scripts/korean_writing.py diagnose 인자")
    diagnose.set_defaults(handler=cmd_diagnose)

    verify = subparsers.add_parser("verify", help="원문과 수정본의 보존 항목 대조")
    verify.add_argument("original")
    verify.add_argument("revised")
    verify.add_argument("--strict", action="store_true")
    verify.add_argument("--json", action="store_true")
    verify.set_defaults(handler=cmd_verify)

    audit = subparsers.add_parser("translation-audit", help="원문·번역문 충실성 및 위험 감사")
    audit.add_argument("source")
    audit.add_argument("target")
    audit.add_argument("--direction", default="auto")
    audit.add_argument("--literary", action="store_true")
    audit.add_argument("--json", action="store_true")
    audit.add_argument("--glossary")
    audit.add_argument("--semantic-review")
    audit.add_argument("--semantic-packet")
    audit.add_argument("--require-semantic-review", action="store_true")
    audit.add_argument("--reader-review")
    audit.add_argument("--require-reader-review", action="store_true")
    audit.add_argument("--link-root")
    audit.add_argument("--link-map")
    audit.add_argument("--format", dest="format_profile", choices=("auto", "plain", "html", "xml", "icu"), default="auto")
    audit.add_argument("--domain")
    audit.add_argument("--segment-id")
    audit.add_argument("--strict", action="store_true")
    audit.add_argument("--baseline")
    audit.add_argument("--intensity", choices=("보수", "기본", "적극"), default="기본")
    audit.set_defaults(handler=cmd_translation_audit)

    session = subparsers.add_parser("translation-session", help="번역 인계서의 단계·표현 선택을 기록하고 이어가기")
    session.add_argument("arguments", nargs=argparse.REMAINDER)
    session.set_defaults(handler=cmd_translation_session)
    for command, handler in (("translation-impact", cmd_translation_impact), ("translation-reader", cmd_translation_reader)):
        sub = subparsers.add_parser(command, help="번역 구간 재검토 / 독자 질문 증거 기록")
        sub.add_argument("arguments", nargs=argparse.REMAINDER)
        sub.set_defaults(handler=handler)

    context = subparsers.add_parser("context-audit", help="명시한 문서 간 용어·개체·주장 근거 대조")
    context.add_argument("manifest")
    context.add_argument("--json", action="store_true")
    context.add_argument("--strict", action="store_true")
    context.set_defaults(handler=cmd_context_audit)

    structure = subparsers.add_parser("structure", help="공식적 골격·과도한 구조 후보 진단")
    structure.add_argument("file")
    structure.add_argument("--json", action="store_true")
    structure.set_defaults(handler=cmd_structure)

    morphology = subparsers.add_parser("morphology", help="선택형 Kiwi 형태소 보조 진단")
    morphology.add_argument("file")
    morphology.add_argument("--json", action="store_true")
    morphology.set_defaults(handler=cmd_morphology)

    handoff = subparsers.add_parser("handoff-validate", help="Writer–Editor JSON 인계 계약 검사")
    handoff.add_argument("file")
    handoff.add_argument("--json", action="store_true")
    handoff.set_defaults(handler=cmd_handoff_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
