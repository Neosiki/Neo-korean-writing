#!/usr/bin/env python3
"""Validate attributed news fixtures; separate surface checks from semantic review."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlsplit

import translation_audit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "tests/fixtures/news_translation_20261019_21.json"


def validate(data):
    errors = []
    cases = data.get("cases", [])
    expected_dates = {"2026-10-19", "2026-10-20", "2026-10-21"}
    if len(cases) != 6 or Counter(c.get("published_date") for c in cases) != Counter({d: 2 for d in expected_dates}):
        errors.append("Expected two excerpts per publication-page date, six in total")
    if len({c.get("id") for c in cases}) != len(cases):
        errors.append("Duplicate fixture ids")
    words_by_url = Counter()
    for case in cases:
        label = case.get("id", "?")
        for key in ("publisher", "host", "author", "published_date", "display_time", "access_scope",
                    "source", "translation", "review_focus", "review_decision"):
            if not case.get(key):
                errors.append(f"{label}: missing {key}")
        url = case.get("url", "")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"{label}: invalid source URL")
        words_by_url[url] += len(case.get("source", "").split())
        try:
            if date.fromisoformat(case["published_date"]) > date.fromisoformat(data["checked_on"]):
                errors.append(f"{label}: publication is after checked_on")
        except (KeyError, ValueError, TypeError):
            errors.append(f"{label}: invalid date")
        mutations = case.get("mutations", [])
        if len(mutations) != 2:
            errors.append(f"{label}: expected two authored mutations")
        for mutation in mutations:
            if mutation.get("synthetic") is not True or not mutation.get("error"):
                errors.append(f"{label}: mutation must be explicitly synthetic and labelled")
            if not mutation.get("text") or mutation["text"] == case.get("translation"):
                errors.append(f"{label}: mutation is empty or unchanged")
    if any(count > 25 for count in words_by_url.values()):
        errors.append("A source URL exceeds the fixture's 25-word quotation ceiling")
    return errors


def evaluate(data):
    errors = validate(data)
    if errors:
        return {"valid": False, "errors": errors}
    rows = []
    for case in data["cases"]:
        good = translation_audit.audit_data(case["source"], case["translation"], "en-to-ko")
        mutations = []
        for mutation in case["mutations"]:
            result = translation_audit.audit_data(case["source"], mutation["text"], "en-to-ko")
            mutations.append({"authored_error": mutation["error"], "status": result["status"],
                              "surface_pass": result["surface_lock"]["pass"],
                              "risk_ids": [r["id"] for r in result["risks"]]})
        rows.append({"id": case["id"], "published_date": case["published_date"],
                     "surface_pass": good["surface_lock"]["pass"],
                     "surface_missing": good["surface_lock"]["missing"],
                     "status": good["status"], "mutations": mutations})
    return {"valid": True, "tool_version": translation_audit.VERSION,
            "reviewed_excerpt_count": len(rows),
            "surface_false_positive_candidates": sum(not row["surface_pass"] for row in rows),
            "synthetic_mutations": sum(len(row["mutations"]) for row in rows),
            "mutations_passing_all_automatic_checks": sum(m["status"] == "pass" for row in rows for m in row["mutations"]),
            "interpretation": "Development fixtures with ChatGPT self-review, not independent translation-quality evaluation. Automatic pass can miss semantic errors; a block is not proof of their cause.",
            "cases": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    data = json.loads(args.fixtures.read_text(encoding="utf-8"))
    report = evaluate(data)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not report["valid"]:
        print("News fixture validation failed: " + "; ".join(report["errors"]))
    else:
        print(f"News excerpts {report['reviewed_excerpt_count']}; surface false-positive candidates {report['surface_false_positive_candidates']}")
        print(f"Synthetic mutations {report['synthetic_mutations']}; automatic-pass blind spots {report['mutations_passing_all_automatic_checks']}")
        print(report["interpretation"])
    return 0 if report["valid"] and report["surface_false_positive_candidates"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
