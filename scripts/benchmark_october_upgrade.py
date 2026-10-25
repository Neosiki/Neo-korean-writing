"""Replay the October link regression and five recorded reader examples.

This is a development replay, not a new model invocation or independent score.
"""
import json
from pathlib import Path
import tempfile
from translation_audit import audit_data
from translation_reader import review_data
from translation_impact import capture, plan

ROOT = Path(__file__).resolve().parents[1]


def evaluate():
    source = "# Guide\n\n[Details](#details)\n\n## Details\n\nRead the steps."
    targets = [
        ("broken_fragment", "# 안내\n\n[세부 안내](#details)\n\n## 세부 안내\n\n절차를 읽으세요.", "hold"),
        ("translated_fragment", "# 안내\n\n[세부 안내](#세부-안내)\n\n## 세부 안내\n\n절차를 읽으세요.", "pass"),
    ]
    links = []
    for ident, target, expected in targets:
        result = audit_data(source, target)
        links.append({"id": ident, "expected": expected, "actual": result["status"],
                      "matched": expected == result["status"],
                      "risk_ids": [r["id"] for r in result["risks"]]})
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        data = {"schema_version": 1, "glossary": "terms.json", "segments": []}
        for n, src in enumerate(("The bank opens.", "The river flows.", "The shop opens.", "The clinic opens.")):
            (base / f"s{n}.md").write_text(src, encoding="utf-8")
            (base / f"t{n}.md").write_text("기존 번역.", encoding="utf-8")
            data["segments"].append({"id": f"p{n}", "source": f"s{n}.md", "target": f"t{n}.md"})
        (base / "terms.json").write_text(json.dumps({"bank": ["은행"]}), encoding="utf-8")
        state = capture(data, base)
        before = [(base / f"t{n}.md").read_bytes() for n in range(4)]
        (base / "terms.json").write_text(json.dumps({"bank": ["금융기관"]}), encoding="utf-8")
        impact = plan(data, base, state)
        impact["targets_unchanged"] = before == [(base / f"t{n}.md").read_bytes() for n in range(4)]
        impact["matched"] = [r["id"] for r in impact["review"]] == ["p0", "p1"] and impact["keep"] == ["p2", "p3"] and impact["targets_unchanged"]
    examples = json.loads((ROOT / "benchmarks/october-reader-records.json").read_text(encoding="utf-8"))
    reading = [{"id": c["id"], "status": review_data(c["target"], c["report"])["status"]}
               for c in examples["cases"]]
    return {"audit_version": "9.9.0", "links": links, "impact": impact,
            "reader_record_replay": reading,
            "note": "자체 작성 예문·같은 세션의 독자 응답 기록을 재생합니다. 독립 정확도 평가나 새 모델 실행이 아닙니다."}


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if all(r["matched"] for r in result["links"]) and result["impact"]["matched"] else 1)

