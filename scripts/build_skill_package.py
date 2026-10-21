#!/usr/bin/env python3
"""Build the distributable .skill ZIP from the validated repository state."""
from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE_DIRS = ("agents", "references", "scripts", "tests", "korean-writing", "prompts", "templates")
INCLUDE_FILES = ("SKILL.md", "CHANGELOG.md", "ROADMAP.md")


def package_entry(path: Path, target: str, root: Path = ROOT):
    relative = path.relative_to(root).as_posix()
    data = path.read_bytes()
    if target == "claude":
        # Claude accepts exactly one SKILL.md in an upload. Keep the complete
        # writing workflow as a referenced document instead of a second entrypoint.
        if relative == "korean-writing/SKILL.md":
            relative = "korean-writing/workflow.md"
        if path.suffix.lower() in {".md", ".py", ".json", ".yaml", ".yml", ".txt"}:
            data = data.replace(b"korean-writing/SKILL.md", b"korean-writing/workflow.md")
    return "neo-korean-writing/" + relative, data


def write_package(output: Path, files: list[Path], target: str, root: Path = ROOT):
    entries = [package_entry(path, target, root) for path in sorted(files)]
    if target == "claude" and sum(Path(name).name == "SKILL.md" for name, _ in entries) != 1:
        raise ValueError("Claude package must contain exactly one SKILL.md")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in entries:
            archive.writestr(name, data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="dist/neo-korean-writing.skill")
    parser.add_argument("--target", choices=("codex", "claude"), default="codex")
    args = parser.parse_args()
    check = subprocess.run([sys.executable, str(ROOT / "scripts/validate_repo.py")], cwd=ROOT)
    if check.returncode:
        return check.returncode
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = [ROOT / name for name in INCLUDE_FILES]
    for directory in INCLUDE_DIRS:
        files.extend(path for path in (ROOT / directory).rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    write_package(output, files, args.target)
    print(f"built {output} ({len(files)} files; target={args.target})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
