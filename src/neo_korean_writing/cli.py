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
}
TEMPLATES = {
    "editing-brief": "editing-brief.md",
    "lock-register": "lock-register.md",
    "editing-delivery": "editing-delivery.md",
}
PROFILES = {
    "general": ("standard-editing",),
    "press-release": ("press-release-editing",),
    "longform": ("longform-editing",),
    "translation": ("translation-postediting",),
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
    if args.literary:
        arguments.append("--literary")
    if args.json:
        arguments.append("--json")
    return _engine_call("translation-audit", arguments)


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
    audit.set_defaults(handler=cmd_translation_audit)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
