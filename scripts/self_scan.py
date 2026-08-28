#!/usr/bin/env python3
"""Scan the project's own prose with protected-span exemptions and fixed budgets."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import korean_writing  # noqa: E402

DOCS = ("README.md", "SKILL.md", "korean-writing/SKILL.md", "ROADMAP.md")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    budgets = json.loads((ROOT / "references/self-scan-budgets.json").read_text(encoding="utf-8"))
    failed = False
    print("| document | P0/P1 signals | budget | verdict |")
    print("|---|---:|---:|---|")
    for name in DOCS:
        text = (ROOT / name).read_text(encoding="utf-8")
        data = korean_writing.diagnose_data(text, "technical" if name.endswith("SKILL.md") else "blog")
        score = sum(p["count"] for p in data["patterns"] if p["severity"] in {"P0", "P1"})
        budget = budgets[name]
        verdict = "OK" if score <= budget else "FAIL"
        failed = failed or verdict == "FAIL"
        print(f"| {name} | {score} | {budget} | {verdict} |")
    return 1 if args.check and failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
