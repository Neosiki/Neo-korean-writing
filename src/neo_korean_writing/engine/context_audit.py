#!/usr/bin/env python3
"""Explicit-file document context audit. No network, rewriting or inferred identity."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys


def prose(text):
    """Mask non-prose while retaining offsets, newlines and link labels."""
    def blank(match):
        return re.sub(r"[^\n]", " ", match.group())
    text = re.sub(r"\A---\r?\n.*?\r?\n---(?:\r?\n|$)", blank, text, flags=re.S)
    text = re.sub(r"(?m)^ {0,3}(`{3,}|~{3,})[^\n]*\n[\s\S]*?^ {0,3}\1[^\n]*(?:\n|$)", blank, text)
    text = re.sub(r"`+[^`\n]*`+|<!--.*?-->|https?://[^\s)>]+", blank, text, flags=re.S)
    text = re.sub(r"(?m)^\s*>[^\n]*", blank, text)
    text = re.sub(r"(?<=\]\()[^)]+(?=\))", blank, text)
    return text


def occurrences(text, term):
    # Latin tokens need word boundaries. Korean terms can carry particles.
    left = r"(?<![A-Za-z0-9_])" if term[:1].isascii() and term[:1].isalnum() else ""
    right = r"(?![A-Za-z0-9_])" if term[-1:].isascii() and term[-1:].isalnum() else ""
    return re.finditer(left + re.escape(term) + right, text)


def evidence(doc, offset, term):
    line = doc["text"].count("\n", 0, offset) + 1
    section = []
    for heading in re.finditer(r"(?m)^(#{1,6})\s+(.+)$", doc["prose"][:offset]):
        depth = len(heading[1])
        section = [x for x in section if x[0] < depth] + [(depth, heading[2].strip())]
    return {"document": doc["id"], "line": line,
            "section": [x[1] for x in section], "text": term}


def load_documents(manifest, base):
    if not isinstance(manifest, dict):
        raise ValueError("manifest는 JSON 객체여야 합니다")
    if manifest.get("version") != 1:
        raise ValueError("manifest.version은 1이어야 합니다")
    entries = manifest.get("documents")
    if not isinstance(entries, list) or not entries:
        raise ValueError("documents에 검사할 파일을 명시하세요")
    docs = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("documents 항목은 객체여야 합니다")
        id_ = entry["id"]
        if not isinstance(id_, str) or not id_ or id_ in docs:
            raise ValueError("중복되거나 빈 문서 ID")
        role = entry.get("role", "target")
        if role not in ("target", "reference"):
            raise ValueError("role은 target 또는 reference")
        path = (base / entry["path"]).resolve()
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        docs[id_] = {"id": id_, "path": str(path), "role": role,
                     "sha256": hashlib.sha256(raw).hexdigest(), "text": text,
                     "prose": prose(text)}
    return docs


def audit(manifest, base=Path("."), strict=False):
    docs = load_documents(manifest, Path(base))
    for collection in ("terms", "entities", "claims"):
        items = manifest.get(collection, [])
        if not isinstance(items, list) or any(not isinstance(x, dict) for x in items):
            raise ValueError(collection + "는 객체 목록이어야 합니다")
    for item in manifest.get("terms", []):
        for key in ("variants", "documents"):
            if key in item and (not isinstance(item[key], list) or
                               any(not isinstance(x, str) for x in item[key])):
                raise ValueError(key + "는 문자열 목록이어야 합니다")
    for item in manifest.get("entities", []):
        if not isinstance(item.get("aliases", []), list):
            raise ValueError("aliases는 목록이어야 합니다")
    findings, mentions, claims = [], {}, []

    def finding(id_, severity, message, proof):
        findings.append({"id": id_, "severity": severity, "message": message, "evidence": proof})

    for rule in manifest.get("terms", []):
        preferred = rule["preferred"]
        if not isinstance(preferred, str) or not preferred:
            raise ValueError("preferred는 빈 문자열일 수 없습니다")
        for doc_id in rule.get("documents", list(docs)):
            if doc_id not in docs:
                raise ValueError("알 수 없는 용어 범위 문서: " + doc_id)
            doc = docs[doc_id]
            if doc["role"] == "reference":
                continue  # references are evidence, not replacement targets
            for variant in rule.get("variants", []):
                if not isinstance(variant, str) or not variant or variant == preferred:
                    raise ValueError("variant는 preferred와 다른 비어 있지 않은 문자열")
                for match in occurrences(doc["prose"], variant):
                    proof = evidence(doc, match.start(), variant)
                    proof["preferred"] = preferred
                    finding("CTX-TERM", "minor", "지정 표기와 다른 용어 후보. 문맥 확인 후 수정", proof)

    owners = defaultdict(set)
    entity_ids = set()
    for entity in manifest.get("entities", []):
        id_ = entity["id"]
        if not isinstance(id_, str) or not id_ or id_ in entity_ids:
            raise ValueError("중복되거나 빈 개체 ID")
        entity_ids.add(id_)
        mentions[id_] = []
        for name in dict.fromkeys([entity["name"]] + entity.get("aliases", [])):
            if not isinstance(name, str) or not name:
                raise ValueError("개체명과 별칭은 비어 있지 않은 문자열")
            owners[name].add(id_)
            for doc in docs.values():
                for match in occurrences(doc["prose"], name):
                    mentions[id_].append(evidence(doc, match.start(), name))
    for name, ids in owners.items():
        if len(ids) > 1:
            finding("CTX-IDENTITY", "major", "같은 표기를 여러 개체가 사용함. 자동 병합 금지",
                    {"alias": name, "entities": sorted(ids)})

    groups = defaultdict(list)
    for claim in manifest.get("claims", []):
        for field in ("subject", "predicate", "value"):
            if not isinstance(claim.get(field), str) or not claim[field].strip():
                raise ValueError("claim의 subject/predicate/value는 비어 있지 않은 문자열")
        proof = claim["evidence"]
        if not isinstance(proof, dict):
            raise ValueError("evidence는 문서와 인용을 담은 객체여야 합니다")
        doc_id, quote = proof["document"], proof["quote"]
        if doc_id not in docs or not isinstance(quote, str) or not quote:
            raise ValueError("주장의 근거 문서/인용을 확인하세요")
        doc = docs[doc_id]
        offset = doc["text"].find(quote)
        item = dict(claim)
        item["evidence"] = dict(proof)
        item["evidence"]["verified_literal"] = offset >= 0
        claims.append(item)
        if offset < 0:
            finding("CTX-EVIDENCE", "major", "인용문을 지정 파일에서 찾지 못함", item)
            continue
        item["evidence"].update(evidence(doc, offset, quote))
        # Matching quotation only proves its presence, not semantic entailment.
        key = tuple(claim.get(k, "") for k in ("subject", "predicate", "scope", "as_of"))
        groups[key].append(item)
    for key, items in groups.items():
        if len({x["value"] for x in items}) > 1:
            finding("CTX-CLAIM", "major", "동일 주체·속성·범위·기준일에서 값이 다름. 원문 대조 필요",
                    {"key": list(key), "claims": items})

    findings.sort(key=lambda x: (x["severity"] != "major", x["id"]))
    status = "hold" if strict and any(x["severity"] == "major" for x in findings) else "warn" if findings else "pass"
    return {"version": 1, "status": status,
            "limitations": "문자열·명시한 주장 대조이며 사실 판정, 자동 개체 병합, 의미 추론을 하지 않습니다.",
            "documents": [{k: d[k] for k in ("id", "path", "role", "sha256")} for d in docs.values()],
            "entity_mentions": mentions, "claims": claims, "findings": findings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        result = audit(manifest, args.manifest.resolve().parent, args.strict)
    except (ValueError, KeyError, TypeError, OSError) as error:
        if args.json:
            print(json.dumps({"status": "invalid", "error": str(error)}, ensure_ascii=False))
        else:
            print("입력 오류: " + str(error), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"문서 맥락 감사: {result['status']} / {len(result['findings'])}건")
        for item in result["findings"]:
            print(f"[{item['severity']}] {item['id']}: {item['message']}")
            print(json.dumps(item["evidence"], ensure_ascii=False))
        print(result["limitations"])
    return 1 if result["status"] == "hold" else 0


if __name__ == "__main__":
    raise SystemExit(main())
