#!/usr/bin/env python3
"""Validate v10 version, references, mirrored assets, and executable SSOTs."""
from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "10.0.0"
LEGACY_KO = "\ud64d\uc791\uac00"
LEGACY_ASCII = "".join(chr(code) for code in (104, 111, 110, 103))
LEGACY_EXTERNAL_OWNER = "".join(chr(code) for code in (101, 112, 111, 107, 111, 55, 55, 45, 97, 105))
LEGACY_EXTERNAL_REPO = "".join(chr(code) for code in (105, 109, 45, 110, 111, 116, 45, 97, 105))
LEGACY_MARKERS = re.compile(
    rf"{re.escape(LEGACY_KO)}|{LEGACY_ASCII}style|(?<![A-Za-z]){LEGACY_ASCII}(?![A-Za-z])|"
    rf"{re.escape(LEGACY_EXTERNAL_OWNER)}|{re.escape(LEGACY_EXTERNAL_REPO)}",
    re.IGNORECASE,
)
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt"}


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def markdown_targets(path: Path):
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = target.strip().split("#", 1)[0]
        if not target or re.match(r"(?:https?://|mailto:)", target):
            continue
        yield target
    for target in re.findall(r"`((?:\.\./)?(?:references|scripts|templates)/[^`\s]+\.(?:md|py|json))`", text):
        yield target


def main() -> int:
    errors: list[str] = []
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    if project["project"]["version"] != EXPECTED:
        fail(f"pyproject version {project['project']['version']} != {EXPECTED}", errors)
    init = (ROOT / "src/neo_korean_writing/__init__.py").read_text(encoding="utf-8")
    if f'__version__ = "{EXPECTED}"' not in init:
        fail("package __version__ mismatch", errors)
    patterns = json.loads((ROOT / "scripts/patterns.json").read_text(encoding="utf-8"))
    if patterns.get("version") != EXPECTED:
        fail("patterns.json version mismatch", errors)
    for path in (ROOT / "SKILL.md", ROOT / "korean-writing/SKILL.md", ROOT / "agents/openai.yaml"):
        text = path.read_text(encoding="utf-8")
        if "v10" not in text:
            fail(f"current-version marker missing: {path.relative_to(ROOT)}", errors)

    for skill in (ROOT / "SKILL.md", ROOT / "korean-writing/SKILL.md"):
        for target in markdown_targets(skill):
            resolved = (skill.parent / target).resolve()
            if not resolved.exists():
                fail(f"broken reference: {skill.relative_to(ROOT)} -> {target}", errors)

    mirrors = [
        (ROOT / "scripts/korean_writing.py", ROOT / "src/neo_korean_writing/engine/korean_writing.py"),
        (ROOT / "scripts/translation_audit.py", ROOT / "src/neo_korean_writing/engine/translation_audit.py"),
        (ROOT / "scripts/patterns.json", ROOT / "src/neo_korean_writing/engine/patterns.json"),
    ]
    for source, packaged in mirrors:
        a = source.read_text(encoding="utf-8")
        b = packaged.read_text(encoding="utf-8")
        if source.name == "korean_writing.py":
            b = b.replace("from .translation_audit import main", "from translation_audit import main")
        if a != b:
            fail(f"packaged engine drift: {source.name}", errors)

    for directory in ("prompts", "templates"):
        for source in (ROOT / directory).iterdir():
            if not source.is_file():
                continue
            packaged = ROOT / "src/neo_korean_writing/assets" / directory / source.name
            if not packaged.exists() or source.read_bytes() != packaged.read_bytes():
                fail(f"packaged asset drift: {directory}/{source.name}", errors)

    for path in ROOT.rglob("*"):
        if ".git" in path.parts or "dist" in path.parts:
            continue
        relative = path.relative_to(ROOT)
        if LEGACY_MARKERS.search(path.name):
            fail(f"legacy identity in path: {relative}", errors)
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8")
            if LEGACY_MARKERS.search(text):
                fail(f"legacy identity in content: {relative}", errors)

    if errors:
        print("repository validation failed:")
        for item in errors:
            print(" -", item)
        return 1
    print("repository validation passed: v10 references, versions, engines, assets, and identity are aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
