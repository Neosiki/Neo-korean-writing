#!/usr/bin/env python3
"""Run genre-aware positive and false-positive fixture expectations."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import korean_writing  # noqa: E402


def main() -> int:
    base = ROOT / "tests/fixtures"
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    failures = []
    for case in manifest["cases"]:
        text = (base / case["path"]).read_text(encoding="utf-8")
        data = korean_writing.diagnose_data(text, case["profile"])
        active = {p["id"] for p in data["patterns"]}
        structure = {p["id"] for p in data["structure"]["findings"]}
        missing = set(case.get("expect_active", [])) - active
        false_hits = set(case.get("forbid_active", [])) & active
        missing_structure = set(case.get("expect_structure", [])) - structure
        verdict = "PASS" if not (missing or false_hits or missing_structure) else "FAIL"
        print(f"{verdict} {case['path']} profile={case['profile']} active={sorted(active)} structure={sorted(structure)}")
        if verdict == "FAIL":
            failures.append({"path": case["path"], "missing": sorted(missing),
                             "false_hits": sorted(false_hits), "missing_structure": sorted(missing_structure)})
    if failures:
        print(json.dumps(failures, ensure_ascii=False, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
