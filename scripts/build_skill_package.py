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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="dist/neo-korean-writing.skill")
    args = parser.parse_args()
    check = subprocess.run([sys.executable, str(ROOT / "scripts/validate_repo.py")], cwd=ROOT)
    if check.returncode:
        return check.returncode
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = [ROOT / name for name in INCLUDE_FILES]
    for directory in INCLUDE_DIRS:
        files.extend(path for path in (ROOT / directory).rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(files):
            archive.write(path, Path("neo-korean-writing") / path.relative_to(ROOT))
    print(f"built {output} ({len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
