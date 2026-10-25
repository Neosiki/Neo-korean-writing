"""Plan segment-level re-review without rewriting accepted translations.

A manifest explicitly registers source/target segment files, a normal audit
glossary and dependencies. Snapshots record hashes, not linguistic approval.
"""
import argparse
import json
import re
import sys
from pathlib import Path
if __package__:
    from .translation_audit import load_glossary, select_glossary, _term_in
    from .translation_semantics import text_hash
    from .translation_session import object_digest
else:
    from translation_audit import load_glossary, select_glossary, _term_in
    from translation_semantics import text_hash
    from translation_session import object_digest

NOTE = "재검토 범위 제안입니다. 번역·승인·원고 덮어쓰기를 실행하지 않습니다."


def nonempty(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("구간 검토 문자열 필요: " + field)


def manifest_data(data):
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("구간 manifest schema_version 오류")
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("구간을 한 개 이상 명시하세요")
    ids = set()
    for row in segments:
        if not isinstance(row, dict):
            raise ValueError("구간은 객체여야 합니다")
        for key in ("id", "source", "target"):
            nonempty(row.get(key), key)
        if row["id"] in ids:
            raise ValueError("중복 구간 ID")
        ids.add(row["id"])
        if row.get("domain") is not None:
            nonempty(row["domain"], "domain")
        for selector in ("source_paragraph", "target_paragraph"):
            if selector in row and (type(row[selector]) is not int or row[selector] < 1):
                raise ValueError("문단 번호는 1 이상의 정수여야 합니다")
        deps = row.get("depends_on", [])
        if not isinstance(deps, list) or any(not isinstance(d, str) or not d for d in deps) or len(set(deps)) != len(deps):
            raise ValueError("depends_on은 중복 없는 구간 ID 배열이어야 합니다")
    for row in segments:
        if row["id"] in row.get("depends_on", []) or not set(row.get("depends_on", [])).issubset(ids):
            raise ValueError("존재하지 않거나 자기 자신인 의존 구간")
    if data.get("glossary") is not None:
        nonempty(data["glossary"], "glossary")
    return segments


def capture(data, base):
    segments = manifest_data(data)
    glossary = load_glossary(str(base / data["glossary"])) if data.get("glossary") else []
    records = {}
    for row in segments:
        source_path, target_path = (base / row["source"]).resolve(), (base / row["target"]).resolve()
        def read_segment(path, selector):
            value = path.read_text(encoding="utf-8-sig")
            if selector is not None:
                paragraphs = [p for p in re.split(r"\n\s*\n", value) if p.strip()]
                if selector > len(paragraphs):
                    raise ValueError("문단 번호가 파일 범위를 벗어났습니다: " + str(path))
                value = paragraphs[selector - 1]
            return value
        source = read_segment(source_path, row.get("source_paragraph"))
        target = read_segment(target_path, row.get("target_paragraph")) if target_path.is_file() else None
        if not source.strip():
            raise ValueError("빈 원문 구간: " + row["id"])
        selected, deferred = select_glossary(glossary, row.get("domain"), row["id"])
        terms = {}
        for term in selected:
            if _term_in(source, term["source"]):
                identity = object_digest({k: term.get(k) for k in ("source", "domains", "segments")})
                terms[identity] = {"source": term["source"], "sha256": object_digest(term)}
        records[row["id"]] = {
            "source_path": str(source_path), "target_path": str(target_path),
            "source_paragraph": row.get("source_paragraph"), "target_paragraph": row.get("target_paragraph"),
            "source_sha256": text_hash(source),
            "target_sha256": text_hash(target) if target is not None and target.strip() else None,
            "terms": terms, "domain": row.get("domain"),
            "deferred": [d for d in deferred if _term_in(source, d["term"])],
            "depends_on": row.get("depends_on", []),
        }
    return {"schema_version": 1, "order": [r["id"] for r in segments],
            "records": records, "note": NOTE}


def validate_snapshot(state):
    if not isinstance(state, dict) or type(state.get("schema_version")) is not int or state["schema_version"] != 1:
        raise ValueError("구간 snapshot schema_version 오류")
    order, records = state.get("order"), state.get("records")
    if (not isinstance(order, list) or any(not isinstance(k, str) for k in order)
            or len(set(order)) != len(order) or not isinstance(records, dict) or set(order) != set(records)):
        raise ValueError("구간 snapshot ID·순서 오류")
    for ident, row in records.items():
        if not isinstance(row, dict):
            raise ValueError("구간 snapshot 기록 오류")
        for key in ("source_path", "target_path", "source_sha256"):
            nonempty(row.get(key), key)
        for key in ("source_sha256", "target_sha256"):
            value = row.get(key)
            if value is None and key == "target_sha256":
                continue
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("구간 snapshot 해시 오류")
        if not isinstance(row.get("terms"), dict) or not isinstance(row.get("deferred"), list):
            raise ValueError("구간 snapshot 용어 기록 오류")
        for term in row["terms"].values():
            if (not isinstance(term, dict) or not isinstance(term.get("source"), str)
                    or not isinstance(term.get("sha256"), str) or len(term["sha256"]) != 64
                    or any(c not in "0123456789abcdef" for c in term["sha256"])):
                raise ValueError("구간 snapshot 용어 항목 오류")
        deps = row.get("depends_on")
        if not isinstance(deps, list) or any(not isinstance(d, str) or d not in records for d in deps):
            raise ValueError("구간 snapshot 의존 기록 오류")


def plan(data, base, baseline=None):
    now = capture(data, base)
    if baseline is not None:
        validate_snapshot(baseline)
    old = baseline["records"] if baseline else {}
    reasons = {ident: [] for ident in now["order"]}
    changed_terms = {}
    for ident, row in now["records"].items():
        why, previous = reasons[ident], old.get(ident)
        if previous is None:
            why.append("untracked")
        else:
            for key in ("source_sha256", "target_sha256", "source_path", "target_path", "source_paragraph", "target_paragraph", "domain", "depends_on"):
                if row.get(key) != previous.get(key):
                    why.append(key + "_changed")
            if row["terms"] != previous["terms"]:
                why.append("relevant_terms_changed")
                changed_terms[ident] = sorted({v["source"] for k, v in {**previous["terms"], **row["terms"]}.items()
                                              if previous["terms"].get(k) != row["terms"].get(k)})
            if previous["deferred"] and previous["deferred"] != row["deferred"]:
                why.append("previous_glossary_scope_unresolved")
            if baseline["order"] != now["order"]:
                # Order affects boundary context. Compare actual neighbors, not all records.
                def neighbors(order, key):
                    n = order.index(key)
                    return order[max(0, n - 1):n] + order[n + 1:n + 2]
                if neighbors(baseline["order"], ident) != neighbors(now["order"], ident):
                    why.append("neighbor_order_changed")
        if row["target_sha256"] is None:
            why.append("missing_or_empty_target")
        if row["deferred"]:
            why.append("glossary_scope_unresolved")
    seeds = {k for k, why in reasons.items() if why}
    for i, ident in enumerate(now["order"]):
        if ident in seeds:
            for adjacent in now["order"][max(0, i - 1):i] + now["order"][i + 1:i + 2]:
                reason = "adjacent_context:" + ident
                if reason not in reasons[adjacent]:
                    reasons[adjacent].append(reason)
    # Explicit dependencies propagate transitively; adjacency expands only once.
    progress = True
    while progress:
        progress = False
        for ident, row in now["records"].items():
            for dep in row["depends_on"]:
                reason = "depends_on:" + dep
                if reasons[dep] and reason not in reasons[ident]:
                    reasons[ident].append(reason)
                    progress = True
    review = [{"id": ident, "reasons": reasons[ident], "changed_terms": changed_terms.get(ident, [])}
              for ident in now["order"] if reasons[ident]]
    return {"status": "review_required" if review or set(old) - set(now["records"]) else "unchanged",
            "review": review, "keep": [ident for ident in now["order"] if not reasons[ident]],
            "removed": [ident for ident in old if ident not in now["records"]],
            "note": NOTE}


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("snapshot")
    p.add_argument("manifest", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("plan")
    p.add_argument("manifest", type=Path)
    p.add_argument("--baseline", type=Path)
    p.add_argument("--json", action="store_true")
    try:
        ns = parser.parse_args(args)
        manifest = ns.manifest.resolve()
        data = json.loads(manifest.read_text(encoding="utf-8-sig"))
        if ns.action == "snapshot":
            if ns.output.exists():
                raise ValueError("기준 기록을 덮어쓰지 않습니다. 새 출력 경로를 지정하세요")
            state = capture(data, manifest.parent)
            if any(r["target_sha256"] is None for r in state["records"].values()):
                raise ValueError("기준 기록에는 비어 있지 않은 번역 구간이 필요합니다")
            with ns.output.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(state, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            print("구간 기준 기록: " + str(ns.output) + " — " + NOTE)
            return 0
        baseline = json.loads(ns.baseline.read_text(encoding="utf-8-sig")) if ns.baseline else None
        result = plan(data, manifest.parent, baseline)
        print(json.dumps(result, ensure_ascii=False, indent=2) if ns.json else
              "재검토 " + str(len(result["review"])) + "개 / 유지 " + str(len(result["keep"])) + "개 — " + NOTE)
        return 2 if result["review"] or result["removed"] else 0
    except SystemExit as exc:
        return 0 if exc.code == 0 else 3
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print("구간 검토 오류: " + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

