"""Offline Markdown links: no network requests or document writes.

Inline/reference links, images, ATX/setext headings and explicit HTML anchors.
Heading correspondence is structural, not semantic. Linked files are read only
under an explicit root; symlink escapes are refused.
"""
import html
import re
import unicodedata
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


def mask_code(text, inline=True):
    lines, fence = [], None
    for line in text.splitlines(keepends=True):
        m = re.match(r"^ {0,3}(\x60{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if fence:
            close = m and m[1][0] == fence[0] and len(m[1]) >= len(fence) and not m[2].strip()
            lines.append("\n" if line.endswith("\n") else "")
            if close:
                fence = None
        elif m:
            fence = m[1]
            lines.append("\n" if line.endswith("\n") else "")
        elif line.startswith("    ") or line.startswith("\t"):
            lines.append("\n" if line.endswith("\n") else "")
        else:
            lines.append(line)
    clean = re.sub(r"<!--[\s\S]*?(?:-->|$)", "", "".join(lines))
    if inline:
        clean = re.sub(r"(?<!\\)(\x60+)(?!\x60)[\s\S]*?(?<!\x60)\1(?!\x60)", "", clean)
    return clean


def _unescape(value):
    return html.unescape(re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]^_\x60{|}~\\])", r"\1", value))


def _destination(text, pos, closing=False):
    while pos < len(text) and text[pos].isspace():
        pos += 1
    start = pos
    if pos < len(text) and text[pos] == "<":
        end = text.find(">", pos + 1)
        if end < 0:
            return None
        dest, pos = text[pos + 1:end], end + 1
    else:
        depth = 0
        while pos < len(text):
            ch = text[pos]
            if ch == "\\" and pos + 1 < len(text):
                pos += 2
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    break
                depth -= 1
            elif ch.isspace() and depth == 0:
                break
            pos += 1
        if depth:
            return None
        dest = text[start:pos]
    if closing:
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos < len(text) and text[pos] in "\"'":
            quote = text[pos]
            pos += 1
            while pos < len(text) and (text[pos] != quote or text[pos - 1] == "\\"):
                pos += 1
            if pos == len(text):
                return None
            pos += 1
            while pos < len(text) and text[pos].isspace():
                pos += 1
        if pos >= len(text) or text[pos] != ")":
            return None
        pos += 1
    return _unescape(dest), pos


def links(text):
    clean = mask_code(text)
    definitions = {}
    for m in re.finditer(r"(?m)^ {0,3}\[([^\]\n]+)\]:[ \t]*(.*)$", clean):
        parsed = _destination(m[2], 0)
        if parsed:
            definitions.setdefault(" ".join(m[1].split()).casefold(), parsed[0])
    clean = re.sub(r"(?m)^ {0,3}\[[^\]\n]+\]:[^\n]*", "", clean)
    result, i = [], 0
    while i < len(clean):
        if clean[i] != "[" or (i and clean[i - 1] == "\\"):
            i += 1
            continue
        start, j, depth = i, i + 1, 1
        while j < len(clean) and depth:
            if clean[j] == "\\":
                j += 2
                continue
            depth += (clean[j] == "[") - (clean[j] == "]")
            j += 1
        if depth:
            i += 1
            continue
        label, dest, end = clean[i + 1:j - 1], None, j
        if j < len(clean) and clean[j] == "(":
            parsed = _destination(clean, j + 1, True)
            if parsed:
                dest, end = parsed
        else:
            ref = label
            if j < len(clean) and clean[j] == "[":
                k = clean.find("]", j + 1)
                if k >= 0:
                    ref, end = clean[j + 1:k] or label, k + 1
            dest = definitions.get(" ".join(ref.split()).casefold())
        if dest is not None:
            result.append({"destination": dest, "image": bool(start and clean[start - 1] == "!")})
        i = max(j, end)
    return result


class _Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if value and (key == "id" or (tag == "a" and key == "name")):
                self.ids.add(value)


def slug(text):
    text = re.sub(r"<[^>]*>", "", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = html.unescape(re.sub(r"\\(.)", r"\1", text))
    text = re.sub(r"(\*+|~+|\x60+)", "", text)
    text = re.sub(r"(?<!\w)_+|_+(?!\w)", "", text).strip().lower()
    return "".join("-" if c == " " else c for c in text
                   if c in " -_" or unicodedata.category(c)[0] in "LNM")


def anchors(text):
    clean = mask_code(text, inline=False)
    parser = _Anchors()
    parser.feed(clean)
    headings, used = [], set()
    lines = clean.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^ {0,3}(#{1,6})(?:[ \t]+|$)(.*)$", line)
        if m:
            level, title = len(m[1]), re.sub(r"[ \t]+#+[ \t]*$", "", m[2])
        elif i + 1 < len(lines) and line.strip() and re.fullmatch(r" {0,3}(?:=+|-+)[ \t]*", lines[i + 1]):
            level, title = (1 if lines[i + 1].lstrip().startswith("=") else 2), line.strip()
        else:
            continue
        base, n = slug(title), 0
        ident = base
        while ident in used:
            n += 1
            ident = base + "-" + str(n)
        used.add(ident)
        headings.append({"id": ident, "level": level})
    return {"ids": used | parser.ids, "headings": headings}


def _local(dest):
    parsed = urlsplit(dest)
    return not parsed.scheme and not parsed.netloc


def _file(root, current, dest):
    raw = unquote(urlsplit(dest).path)
    if "\\" in raw or "\x00" in raw or re.match(r"^[A-Za-z]:", raw):
        raise ValueError("unsupported local path")
    path = (root / raw.lstrip("/")).resolve() if raw.startswith("/") else (current.parent / raw).resolve()
    if not path.is_relative_to(root):
        raise ValueError("link escapes explicit root")
    return path


def compare_links(source, target, source_path=None, target_path=None, root=None, mapping=None):
    if mapping is None:
        mapping = {}
    if not isinstance(mapping, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in mapping.items()):
        raise ValueError("link mapping must be a source destination -> target destination object")
    if any(not _local(k) or not _local(v) for k, v in mapping.items()):
        raise ValueError("link mapping cannot change an external URL")
    src, tgt = links(source), links(target)
    sa, ta = anchors(source), anchors(target)
    structural = {}
    if [h["level"] for h in sa["headings"]] == [h["level"] for h in ta["headings"]]:
        structural = {a["id"]: b["id"] for a, b in zip(sa["headings"], ta["headings"])}
    issues, unchecked, checked, allowed = [], [], [], []
    root = Path(root).resolve() if root is not None else None
    current = Path(target_path).resolve() if target_path is not None else None
    if root is not None and (current is None or not current.is_relative_to(root)):
        raise ValueError("target file must be within link root")
    for row in tgt:
        dest = row["destination"]
        if not _local(dest):
            unchecked.append({"destination": dest, "reason": "external_not_fetched"})
            continue
        part = urlsplit(dest)
        frag = unquote(part.fragment)
        if not part.path:
            if row["image"]:
                unchecked.append({"destination": dest, "reason": "image_fragment_not_checked"})
            elif frag and frag not in ta["ids"]:
                issues.append({"destination": dest, "kind": "missing_fragment"})
            else:
                checked.append(dest)
            continue
        if root is None:
            unchecked.append({"destination": dest, "reason": "local_root_not_provided"})
            continue
        try:
            path = _file(root, current, dest)
        except ValueError as exc:
            issues.append({"destination": dest, "kind": "outside_root", "reason": str(exc)})
            continue
        if not path.is_file():
            issues.append({"destination": dest, "kind": "missing_file"})
        elif frag and not row["image"]:
            if path.suffix.lower() in (".md", ".markdown"):
                if frag not in anchors(path.read_text(encoding="utf-8"))["ids"]:
                    issues.append({"destination": dest, "kind": "missing_fragment"})
                else:
                    checked.append(dest)
            else:
                unchecked.append({"destination": dest, "reason": "non_markdown_fragment"})
        else:
            checked.append(dest)
    normalized_source = []
    available = Counter(r["destination"] for r in tgt)
    valid = set(checked)
    for row in src:
        old = row["destination"]
        new = old
        if _local(old) and not row["image"]:
            part = urlsplit(old)
            if old in mapping:
                candidate = mapping[old]
                if candidate in valid and available[candidate]:
                    new = candidate
            elif not part.path and part.fragment:
                old_id = unquote(part.fragment)
                new_id = structural.get(old_id, old_id if old_id in sa["ids"] else None)
                candidates = [d for d in available if _local(d) and not urlsplit(d).path
                              and unquote(urlsplit(d).fragment) == new_id]
                candidate = next((d for d in candidates if d in valid and available[d]), None)
                if candidate is not None:
                    new = candidate
        elif row["image"] and old in mapping and mapping[old] in valid and available[mapping[old]]:
            new = mapping[old]
        if new != old:
            allowed.append({"source": old, "target": new, "basis": "explicit_map" if old in mapping else "heading_order"})
        normalized_source.append(new)
        if available[new]:
            available[new] -= 1
    return {"profile": "gfm-basic", "pass": not issues, "issues": issues,
            "checked": checked, "unchecked": unchecked, "allowed_changes": allowed,
            "source_targets": normalized_source, "target_targets": [r["destination"] for r in tgt],
            "note": "오프라인 목적지·구조 검사입니다. 제목 대응의 의미, 외부 URL 응답, 모든 Markdown 확장 문법은 검증하지 않습니다."}

