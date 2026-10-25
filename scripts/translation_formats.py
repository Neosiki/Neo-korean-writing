"""Format-aware translation checks. No rendering, evaluation, network or model calls.

HTML checks explicitly balanced fragments, not the whole HTML5 parsing algorithm.
XML uses ElementTree without DTDs. ICU MessageFormat 1 uses a pinned MIT parser.
Ordinary prose keeps the existing lightweight placeholder policy.
"""
from collections import Counter, defaultdict
from html.parser import HTMLParser
import re
import xml.etree.ElementTree as ET

from _vendor.pyicumessageformat import Parser

PROFILES = ("auto", "plain", "html", "xml", "icu")
TEXT_ATTRIBUTES = frozenset({"alt", "title", "aria-label", "aria-description", "placeholder"})
VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())
FENCES = re.compile(r"(?m)^ {0,3}(`{3,}|~{3,})[^\n]*\n[\s\S]*?^ {0,3}\1[^\n]*(?:\n|$)")
INLINE = re.compile(r"(`+)[^`\n]+\1")
ICU_SIGNAL = re.compile(r"\{\s*[\w.]+\s*,\s*(?:plural|select|selectordinal)\s*,")
VARIABLE = re.compile(r"\{\{[^{}\n]+\}\}|\$\{[^{}\n]+\}|\{[A-Za-z_][\w.]*\}|%\d*\$?[sdif]|%\([A-Za-z_]\w*\)[sdif]")


def protected_attributes(attrs):
    return tuple(sorted((key, ("text", tuple(sorted(VARIABLE.findall(value or "")))))
                        if key in TEXT_ATTRIBUTES else (key, ("locked", value))
                        for key, value in attrs))


def prose(text):
    return INLINE.sub(" ", FENCES.sub(" ", text))


def resolve_profile(source, requested="auto"):
    if requested not in PROFILES:
        raise ValueError("알 수 없는 형식 프로필: " + str(requested))
    if requested != "auto":
        return requested
    body = prose(source)
    if ICU_SIGNAL.search(body):
        return "icu"
    return "html" if re.search(r"</?[A-Za-z][\w:-]*(?:\s[^<>]*|/?)>", body) else "plain"


def legacy_placeholder_text(text, profile):
    """Markup is checked structurally; ICU arguments are checked in the parsed AST."""
    if profile == "icu":
        return ""
    if profile in ("html", "xml"):
        reader = Markup()
        reader.feed(text)
        reader.close()
        return " ".join(reader.text)
    return text


class Markup(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack = []
        self.nodes = []
        self.errors = []
        self.text = []

    def opening(self, tag, attrs, closed=False):
        names = [key for key, _ in attrs]
        if len(names) != len(set(names)):
            self.errors.append("중복 속성: " + tag)
        protected = protected_attributes(attrs)
        self.text.extend(value for _, value in attrs if value)
        self.nodes.append((tuple(self.stack), tag, protected))
        if not closed and tag not in VOID:
            self.stack.append(tag)

    def handle_starttag(self, tag, attrs):
        self.opening(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        self.opening(tag, attrs, True)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append("태그 닫힘 순서 불일치: " + tag)
        else:
            self.stack.pop()

    def handle_data(self, data):
        self.text.append(data)
        if re.search(r"</?[A-Za-z]", data):
            self.errors.append("해석되지 않은 태그 형태의 텍스트")

    def handle_entityref(self, name):
        self.text.append("&" + name + ";")

    def handle_charref(self, name):
        self.text.append("&#" + name + ";")


def markup_data(text, xml=False):
    if xml:
        if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I):
            return [], ["DTD·ENTITY는 이 로컬 검사에서 지원하지 않습니다"]
        wrapped = not text.lstrip().startswith("<?xml")
        try:
            root = ET.fromstring("<audit-root>" + text + "</audit-root>" if wrapped else text)
        except ET.ParseError as exc:
            return [], [str(exc)]
        nodes = []
        def walk(node, parents, wrapper=False):
            if not wrapper:
                attrs = protected_attributes(node.attrib.items())
                nodes.append((parents, node.tag, attrs))
                parents = parents + (node.tag,)
            for child in node:
                walk(child, parents)
        walk(root, (), wrapped)
        return nodes, []
    reader = Markup()
    try:
        reader.feed(text)
        reader.close()
    except (ValueError, AssertionError) as exc:
        reader.errors.append(str(exc))
    if reader.stack:
        reader.errors.append("명시적으로 닫히지 않은 태그: " + ", ".join(reader.stack))
    return reader.nodes, reader.errors


def icu_data(text):
    tokens = []
    try:
        ast = Parser({"maximum_depth": 30, "include_indices": True, "require_other": True}).parse(text, tokens)
    except (SyntaxError, ValueError, TypeError, RecursionError) as exc:
        return None, [str(exc) or "ICU MessageFormat 문법 오류"]
    errors, stack = [], []
    for token in tokens:
        if token["type"] == "syntax" and token["text"] == "{":
            stack.append(set())
        elif token["type"] == "syntax" and token["text"] == "}" and stack:
            stack.pop()
        elif token["type"] == "selector" and stack:
            if token["text"] in stack[-1]:
                errors.append("중복 ICU 분기: " + token["text"])
            stack[-1].add(token["text"])
    arguments, controls = defaultdict(set), []
    def walk(nodes, route=()):
        for node in nodes:
            if isinstance(node, str):
                continue
            name, kind = node["name"], node.get("type", "string")
            signature = ("#" if node.get("hash") else kind, repr(node.get("format")))
            arguments[(route, name)].add(signature)
            if kind in ("plural", "selectordinal", "select"):
                options = node["options"]
                if kind != "select" and any(not (k in {"zero", "one", "two", "few", "many", "other"} or re.fullmatch(r"=-?\d+(?:\.\d+)?", k)) for k in options):
                    errors.append("잘못된 ICU plural 선택자: " + name)
                if node.get("offset", 0) < 0:
                    errors.append("음수 ICU offset: " + name)
                # Locale plural names may differ; exact-value and select branches encode meaning.
                required = sorted(k for k in options if kind == "select" or k.startswith("="))
                controls.append((route, name, kind, node.get("offset", 0), tuple(required)))
                for selector, children in options.items():
                    # A dropped locale-only plural branch is allowed, including its repeated variables.
                    walk(children, route + ((name, selector if kind == "select" or selector.startswith("=") else "locale"),))
    walk(ast)
    return {"arguments": dict(arguments), "controls": controls}, errors


def compare_formats(source, target, requested="auto"):
    profile = resolve_profile(source, requested)
    report = {"profile": profile, "complete": True, "pass": True, "issues": [],
              "scope": "형식·공유 변수 검사이며 의미·보안·렌더 결과의 인증이 아닙니다"}
    if profile == "plain":
        return report
    source_body, target_body = (source, target) if profile == "icu" else (prose(source), prose(target))
    parse = icu_data if profile == "icu" else lambda t: markup_data(t, profile == "xml")
    before, source_errors = parse(source_body)
    after, target_errors = parse(target_body)
    for side, errors in (("source", source_errors), ("target", target_errors)):
        for message in errors:
            report["issues"].append({"kind": profile + ".syntax", "side": side, "message": message})
    if not source_errors and not target_errors:
        if profile == "icu":
            if before["arguments"] != after["arguments"]:
                report["issues"].append({"kind": "icu.arguments", "message": "ICU 변수 이름 또는 타입이 달라졌습니다"})
            # Locale plural alternatives may collapse; select/exact branches remain distinct.
            if set(before["controls"]) != set(after["controls"]):
                report["issues"].append({"kind": "icu.controls", "message": "ICU 선택 분기·명시 값·offset이 달라졌습니다"})
        elif Counter(before) != Counter(after):
            report["issues"].append({"kind": profile + ".structure", "message": "태그 계층·개수 또는 보호 속성이 달라졌습니다"})
    report["pass"] = not report["issues"]
    return report
