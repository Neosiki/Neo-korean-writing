#!/usr/bin/env python3
"""Local continuation records inside a Writer–Editor handoff. No model calls.

Checkpoints attest to file identity and ordering, never translation quality.
Only explicitly registered source, glossary and artifact files are read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import sys
import tempfile

if __package__:
    from .korean_writing import handoff_data
else:
    from korean_writing import handoff_data

KEY = "translation_workflow"
STAGES = ("analysis", "draft", "review", "revision", "polish", "check")
KINDS = ("term", "voice", "interpretation", "first_mention")
STATES = ("provisional", "adopted", "deferred", "rejected")
OWNERS = ("user", "editor", "model")
FORMATS = ("auto", "plain", "html", "xml", "icu")
DIRECTIONS = ("auto", "en-to-ko", "ko-to-en", "same")
NOTE = "단계 기록은 파일·순서 확인이며 의미 정확성·사람 검수·출판 승인 증명이 아닙니다"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def object_digest(value):
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def resolve(base, name):
    return (base / name).resolve()


def file_record(path, base):
    path = path.resolve()
    if not path.is_file():
        raise ValueError("파일을 찾을 수 없습니다: " + str(path))
    try:
        name = os.path.relpath(path, base)
    except ValueError:  # Windows: source and handoff may be on different drives.
        name = str(path)
    return {"path": name, "sha256": digest(path.read_bytes())}


def read_handoff(path):
    text = path.read_text(encoding="utf-8-sig")
    report = handoff_data(text)
    if not report["pass"]:
        raise ValueError("인계서 오류: " + "; ".join(report["errors"]))
    return json.loads(text)


def brief_digest(data):
    return object_digest({k: v for k, v in data.items() if k != KEY})


def require_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("비어 있지 않은 문자열이 필요합니다: " + field)


def require_hash(value, field):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("SHA-256 기록 형식 오류: " + field)


def validate_file(rec, field):
    if not isinstance(rec, dict):
        raise ValueError("파일 기록 형식 오류: " + field)
    require_text(rec.get("path"), field + ".path")
    require_hash(rec.get("sha256"), field + ".sha256")


def validate_scope(scope):
    if not isinstance(scope, dict) or set(scope) != {"domain", "segment_id"}:
        raise ValueError("분야·구간 기록 형식 오류")
    for name, value in scope.items():
        if value is not None:
            require_text(value, name)


def validate_settings(settings):
    if not isinstance(settings, dict) or set(settings) != {"direction", "format", "domain", "segment_id"}:
        raise ValueError("작업 설정 필드 형식 오류")
    if settings["direction"] not in DIRECTIONS or settings["format"] not in FORMATS:
        raise ValueError("지원하지 않는 번역 방향·형식입니다")
    validate_scope({k: settings[k] for k in ("domain", "segment_id")})


def load_state(data):
    state = data.get(KEY)
    if not isinstance(state, dict) or type(state.get("version")) is not int or state["version"] != 1:
        raise ValueError("먼저 translation-session init으로 작업을 등록하세요")
    if not isinstance(state.get("stages"), dict) or not isinstance(state.get("decisions"), list):
        raise ValueError("진행 단계·판단 기록 형식이 잘못되었습니다")
    if set(state["stages"]) - set(STAGES):
        raise ValueError("알 수 없는 진행 단계가 있습니다")
    validate_settings(state.get("settings"))
    validate_file(state.get("source"), "source")
    if state.get("glossary") is not None:
        validate_file(state["glossary"], "glossary")
    require_hash(state.get("brief_sha256"), "brief_sha256")
    require_hash(state.get("context_sha256"), "context_sha256")
    if not isinstance(state.get("history"), list) or any(not isinstance(h, dict) for h in state["history"]):
        raise ValueError("이력은 객체 배열이어야 합니다")
    identifiers = set()
    for row in state["decisions"]:
        if not isinstance(row, dict) or row.get("state") not in STATES or row.get("kind") not in KINDS:
            raise ValueError("판단 기록 형식이 잘못되었습니다")
        for field in ("id", "target", "reason"):
            require_text(row.get(field), "decision." + field)
        if row["id"] in identifiers:
            raise ValueError("중복 판단 ID: " + row["id"])
        identifiers.add(row["id"])
        if row.get("owner") not in OWNERS or not isinstance(row.get("source_text"), str):
            raise ValueError("판단 주체·원문 구절 형식 오류")
        if row["kind"] != "voice":
            require_text(row["source_text"], "decision.source_text")
        require_hash(row.get("context_sha256"), "decision.context_sha256")
        validate_scope(row.get("scope"))
    for name, rec in state["stages"].items():
        if not isinstance(rec, dict):
            raise ValueError("진행 단계 기록 형식 오류: " + name)
        validate_file(rec.get("artifact"), name + ".artifact")
        for field in ("context_sha256", "decisions_sha256"):
            require_hash(rec.get(field), name + "." + field)
        if name == "analysis":
            if rec.get("parent_sha256") is not None:
                raise ValueError("analysis에는 앞 단계가 없습니다")
        else:
            require_hash(rec.get("parent_sha256"), name + ".parent_sha256")
    return state


def binding(state):
    return object_digest({k: state.get(k) for k in ("source", "glossary", "settings", "brief_sha256")})


def current_inputs(data, state, base):
    reasons = []
    for key in ("source", "glossary"):
        rec = state.get(key)
        if rec is None and key == "glossary":
            continue
        if not isinstance(rec, dict) or not isinstance(rec.get("path"), str) or not rec["path"]:
            raise ValueError("등록 파일 형식 오류: " + key)
        try:
            if digest(resolve(base, rec["path"]).read_bytes()) != rec.get("sha256"):
                reasons.append(key + "_changed")
        except OSError:
            reasons.append(key + "_unavailable")
    if brief_digest(data) != state.get("brief_sha256"):
        reasons.append("brief_changed")
    if binding(state) != state.get("context_sha256"):
        reasons.append("settings_or_binding_changed")
    return reasons


def decisions_digest(state):
    return object_digest([d for d in state["decisions"] if d.get("context_sha256") == state["context_sha256"]])


def inspect(data, base):
    state = load_state(data)
    reasons = current_inputs(data, state, base)
    rows, parent, blocked = [], None, bool(reasons)
    for name in STAGES:
        rec = state["stages"].get(name)
        why = []
        if not isinstance(rec, dict):
            why.append("not_recorded")
        else:
            if reasons:
                why.append("inputs_stale")
            if rec.get("context_sha256") != state["context_sha256"]:
                why.append("context_changed")
            if rec.get("parent_sha256") != parent:
                why.append("preceding_artifact_changed")
            if name != "analysis" and rec.get("decisions_sha256") != decisions_digest(state):
                why.append("decisions_changed")
            artifact = rec.get("artifact", {})
            if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
                raise ValueError("산출물 기록 형식 오류: " + name)
            try:
                if digest(resolve(base, artifact["path"]).read_bytes()) != artifact.get("sha256"):
                    why.append("artifact_changed")
            except OSError:
                why.append("artifact_unavailable")
        if blocked:
            why.append("preceding_stage_or_input_stale")
        valid = not why
        rows.append({"stage": name, "recorded": rec is not None, "valid": valid, "reasons": why})
        blocked = blocked or not valid
        parent = rec.get("artifact", {}).get("sha256") if isinstance(rec, dict) else None
    next_stage = next((r["stage"] for r in rows if not r["valid"]), None)
    usable, reconsider = [], []
    for row in state["decisions"]:
        if reasons or row.get("context_sha256") != state["context_sha256"]:
            reconsider.append(row)
        elif row["state"] == "adopted":
            usable.append(row)
    stale = bool(reasons) or any(r["recorded"] and not r["valid"] for r in rows)
    return {"status": "stale" if stale else ("recorded" if next_stage is None else "ready"),
            "inputs_current": not reasons, "input_changes": reasons, "stages": rows,
            "next_stage": next_stage, "usable_decisions": usable, "reconsider_decisions": reconsider,
            "note": NOTE, "human_review_required": True}


def initialize(data, path, source=None, glossary=None, settings=None, refresh=False):
    old = data.get(KEY)
    if old is not None and not refresh:
        raise ValueError("작업이 이미 있습니다. inspect로 이어가거나 --refresh로 입력을 다시 등록하세요")
    if old is not None:
        load_state(data)
    base = path.parent
    source_path = Path(source).resolve() if source else resolve(base, old["source"]["path"]) if old else None
    if source_path is None:
        raise ValueError("새 작업에는 --source가 필요합니다")
    if source_path == path.resolve():
        raise ValueError("인계서를 원문 파일로 등록할 수 없습니다")
    glossary_path = Path(glossary).resolve() if glossary else resolve(base, old["glossary"]["path"]) if old and old.get("glossary") else None
    if glossary_path == path.resolve():
        raise ValueError("인계서를 용어집으로 등록할 수 없습니다")
    resolved = dict(old["settings"] if old else {"direction": "en-to-ko", "format": "auto", "domain": None, "segment_id": None})
    resolved.update({k: v for k, v in (settings or {}).items() if v is not None})
    for key in ("domain", "segment_id"):
        if resolved.get(key) == "":
            resolved[key] = None
    validate_settings(resolved)
    history = list(old.get("history", [])) if old else []
    if old:
        history.append({"event": "inputs_refreshed", "context_sha256": old["context_sha256"], "stages": old["stages"]})
    state = {"version": 1, "source": file_record(source_path, base),
             "glossary": file_record(glossary_path, base) if glossary_path else None,
             "settings": resolved, "brief_sha256": brief_digest(data),
             "decisions": list(old["decisions"]) if old else [], "stages": {}, "history": history}
    state["context_sha256"] = binding(state)
    data[KEY] = state


def invalidate(state, start, event):
    removed = {n: state["stages"].pop(n) for n in STAGES[start:] if n in state["stages"]}
    if removed:
        state["history"].append({"event": event, "stages": removed})


def checkpoint(data, path, stage, artifact):
    state = load_state(data)
    report = inspect(data, path.parent)
    if not report["inputs_current"]:
        raise ValueError("입력이 바뀌었습니다. 원문·설정을 확인하고 init --refresh를 실행하세요")
    index = STAGES.index(stage)
    if any(not row["valid"] for row in report["stages"][:index]):
        raise ValueError("앞 단계를 먼저 다시 확인하고 기록하세요")
    artifact_path = Path(artifact).resolve()
    if artifact_path == path.resolve():
        raise ValueError("인계서 자체를 산출물로 등록할 수 없습니다")
    record = file_record(artifact_path, path.parent)
    if not artifact_path.read_bytes().strip():
        raise ValueError("빈 산출물을 완료 단계로 기록할 수 없습니다")
    invalidate(state, index, "checkpoint_replaced")
    state["stages"][stage] = {"artifact": record, "context_sha256": state["context_sha256"],
                              "parent_sha256": state["stages"][STAGES[index-1]]["artifact"]["sha256"] if index else None,
                              "decisions_sha256": decisions_digest(state)}


def record_decision(data, path, identifier, kind, source_text, target, state_name, owner, reason):
    state = load_state(data)
    if current_inputs(data, state, path.parent):
        raise ValueError("변경된 입력을 먼저 다시 등록하세요")
    if kind not in KINDS or state_name not in STATES or owner not in OWNERS:
        raise ValueError("지원하지 않는 판단 종류·상태·주체입니다")
    if not identifier.strip() or not target.strip() or not reason.strip():
        raise ValueError("판단 ID·선택 표현·근거는 비울 수 없습니다")
    if kind != "voice":
        source = resolve(path.parent, state["source"]["path"]).read_text(encoding="utf-8-sig")
        if not source_text or source_text not in source:
            raise ValueError("판단의 원문 구절이 등록 원문에 없습니다")
    row = {"id": identifier, "kind": kind, "source_text": source_text, "target": target,
           "state": state_name, "owner": owner, "reason": reason,
           "scope": {k: state["settings"].get(k) for k in ("domain", "segment_id")},
           "context_sha256": state["context_sha256"]}
    before = next((d for d in state["decisions"] if d["id"] == identifier), None)
    if before == row:
        return
    if before:
        state["history"].append({"event": "decision_replaced", "decision": before})
    state["decisions"] = [d for d in state["decisions"] if d["id"] != identifier] + [row]
    invalidate(state, 1, "decision_changed")


def save(path, data):
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
            temp = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp, path)
    finally:
        if temp and temp.exists():
            temp.unlink()


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("init", "inspect", "checkpoint", "decision"):
        p = sub.add_parser(name)
        p.add_argument("handoff", type=Path)
        p.add_argument("--json", action="store_true")
        if name == "init":
            p.add_argument("--source")
            p.add_argument("--glossary")
            p.add_argument("--refresh", action="store_true")
            p.add_argument("--format", choices=FORMATS)
            p.add_argument("--direction", choices=DIRECTIONS)
            p.add_argument("--domain")
            p.add_argument("--segment-id")
        elif name == "checkpoint":
            p.add_argument("--stage", required=True, choices=STAGES)
            p.add_argument("--artifact", required=True)
        elif name == "decision":
            p.add_argument("--id", required=True)
            p.add_argument("--kind", choices=KINDS, required=True)
            p.add_argument("--source-text", default="")
            p.add_argument("--target", required=True)
            p.add_argument("--state", choices=STATES, default="provisional")
            p.add_argument("--owner", choices=OWNERS, default="model")
            p.add_argument("--reason", required=True)
    try:
        ns = parser.parse_args(args)
        path = ns.handoff.resolve()
        original = path.read_bytes()
        data = read_handoff(path)
        if ns.action == "init":
            initialize(data, path, ns.source, ns.glossary, {"direction": ns.direction, "format": ns.format, "domain": ns.domain, "segment_id": ns.segment_id}, ns.refresh)
        elif ns.action == "checkpoint":
            checkpoint(data, path, ns.stage, ns.artifact)
        elif ns.action == "decision":
            record_decision(data, path, ns.id, ns.kind, ns.source_text, ns.target, ns.state, ns.owner, ns.reason)
        result = inspect(data, path.parent)
        if ns.action != "inspect":
            if path.read_bytes() != original:
                raise ValueError("인계서가 작업 중 변경됐습니다. 다시 읽고 재시도하세요")
            save(path, data)
        if ns.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"작업 기록: {result['status']} / 다음 단계: {result['next_stage'] or '없음'}")
            print(f"채택 표현 {len(result['usable_decisions'])}건 / 재검토 판단 {len(result['reconsider_decisions'])}건")
            for row in result["stages"]:
                if row["recorded"] and not row["valid"]:
                    print(row["stage"] + ": " + ", ".join(row["reasons"]))
            print(NOTE)
        return 2 if result["status"] == "stale" else 0
    except SystemExit as exc:
        return 0 if exc.code == 0 else 3
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        print("작업 기록 오류: " + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
