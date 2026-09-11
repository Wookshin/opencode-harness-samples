#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
심볼·참조·중복·SQL 인덱서 — 리팩토링 제안 하네스의 기계적 토대.

    python index.py --ws _workspace/scan-YOEDSMOV

읽는 것:  <WS>/src/**       수집된 C# · XAML · resx 원문
          <WS>/src-sql/**   수집된 iBATIS mapper XML

쓰는 것:  <WS>/1-index.json  전체 인덱스 (검증관이 대조하는 기계적 사실)
          <WS>/1-index.md    사람과 LLM 이 읽는 요약

왜 스크립트가 먼저 세는가
-------------------------
"이 코드는 아무도 안 쓴다"는 말은 **전수 조사로만** 할 수 있습니다.
LLM 에게 grep 을 시키면 WPF 가 참조를 숨겨 두는 경로(XAML 핸들러, 바인딩,
리소스 키, 의존 속성, 문자열 참조, 리플렉션)를 반드시 몇 개 놓칩니다.
그러면 멀쩡히 쓰이는 코드가 "죽은 코드"로 회의 자료에 실립니다.

그래서 여기서 전부 세고, LLM 은 **후보를 판정만** 합니다.

표준 라이브러리만 씁니다. pip 설치가 필요 없습니다.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ── 한계값 ──────────────────────────────────────────────────────────────
MAX_SYMBOLS = 1500          # 이걸 넘으면 중복 비교를 상위만 합니다
DUP_MIN_LINES = 8           # 이보다 짧은 메서드는 중복 후보로 보지 않습니다
DUP_GRAM = 5                # 토큰 5-gram
DUP_THRESHOLD = 0.75        # Jaccard 유사도
XAML_DUP_MIN_LINES = 4      # XAML 반복 블록 최소 줄 수

CS_EXT = (".cs", ".csx")
XAML_EXT = (".xaml", ".axaml")
XMLISH_EXT = (".xml", ".config", ".csproj", ".props", ".targets")
RESX_EXT = (".resx",)


def warn(msg):
    print("! " + msg)


# ────────────────────────────────────────────────────────────────────────
# 1. 읽기 — UTF-16 으로 쓰인 파일을 조용히 넘기지 않습니다
# ────────────────────────────────────────────────────────────────────────
def read_text(p: Path) -> str:
    raw = p.read_bytes()
    if raw.startswith(b"\xff\xfe"):
        warn("%s 이 UTF-16LE 입니다 (PowerShell 5.1 의 `>` 가 이렇게 씁니다). 디코딩해 읽습니다." % p)
        return raw.decode("utf-16-le").lstrip("﻿")
    if raw.startswith(b"\xfe\xff"):
        warn("%s 이 UTF-16BE 입니다. 디코딩해 읽습니다." % p)
        return raw.decode("utf-16-be").lstrip("﻿")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        warn("%s 을 UTF-8 로 읽지 못해 cp949 로 다시 시도합니다." % p)
        return raw.decode("cp949", errors="replace")


# ────────────────────────────────────────────────────────────────────────
# 2. C# 마스킹 — 주석과 문자열을 지우되 길이와 줄 수는 보존합니다
#
#    마스킹한 텍스트 위에서만 중괄호를 세고 선언을 찾습니다.
#    그래야 문자열 안의 `{` 나 주석 안의 `class` 에 속지 않습니다.
#    지운 문자열은 따로 모아 둡니다 — 문자열 참조(W8·W11·SQL ID)의 근거입니다.
# ────────────────────────────────────────────────────────────────────────
def mask_cs(text):
    """(masked, strings) 를 돌려줍니다. strings = [(line_no, content), …]"""
    out = []
    strings = []
    i, n = 0, len(text)
    line = 1

    def push(s, keep_newlines=True):
        nonlocal line
        if keep_newlines:
            out.append(s)
        else:
            out.append(re.sub(r"[^\n]", " ", s))
        line += s.count("\n")

    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        # 줄 주석
        if c == "/" and nxt == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            push(text[i:j], keep_newlines=False)
            i = j
            continue

        # 블록 주석
        if c == "/" and nxt == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            seg = text[i:j]
            out.append(re.sub(r"[^\n]", " ", seg))
            line += seg.count("\n")
            i = j
            continue

        # 축자 문자열  @"…"  ·  $@"…"  ·  @$"…"   ("" 가 이스케이프)
        m = re.match(r'(?:\$@|@\$|@)"', text[i:])
        if m:
            start_line = line
            j = i + m.end()
            buf = []
            while j < n:
                if text[j] == '"':
                    if j + 1 < n and text[j + 1] == '"':
                        buf.append('"')
                        j += 2
                        continue
                    j += 1
                    break
                buf.append(text[j])
                j += 1
            seg = text[i:j]
            strings.append((start_line, "".join(buf)))
            out.append(re.sub(r"[^\n]", " ", seg))
            line += seg.count("\n")
            i = j
            continue

        # 보통 문자열  "…"  ·  $"…"   (\ 가 이스케이프)
        m = re.match(r'(?:\$)?"', text[i:])
        if m:
            start_line = line
            j = i + m.end()
            buf = []
            while j < n:
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                    continue
                if text[j] == '"':
                    j += 1
                    break
                if text[j] == "\n":
                    break            # 닫히지 않은 문자열 — 줄에서 끊습니다
                buf.append(text[j])
                j += 1
            seg = text[i:j]
            strings.append((start_line, "".join(buf)))
            out.append(re.sub(r"[^\n]", " ", seg))
            line += seg.count("\n")
            i = j
            continue

        # 문자 리터럴  'x'  ·  '\n'
        if c == "'":
            j = i + 1
            while j < n:
                if text[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if text[j] == "'":
                    j += 1
                    break
                if text[j] == "\n":
                    break
                j += 1
            out.append(" " * (j - i))
            i = j
            continue

        out.append(c)
        if c == "\n":
            line += 1
        i += 1

    return "".join(out), strings


# ────────────────────────────────────────────────────────────────────────
# 3. C# 심볼 추출
# ────────────────────────────────────────────────────────────────────────
MODIFIERS = ("public", "private", "protected", "internal", "static", "sealed",
             "abstract", "virtual", "override", "readonly", "const", "async",
             "extern", "partial", "new", "unsafe", "volatile", "required")

TYPE_KINDS = ("class", "struct", "interface", "enum", "record")

RE_NAMESPACE = re.compile(r"^\s*namespace\s+([\w.]+)")
RE_TYPE = re.compile(
    r"^\s*(?P<mods>(?:(?:%s)\s+)*)(?P<kind>%s)\s+(?P<name>\w+)"
    r"(?:\s*<[^>]*>)?(?P<bases>\s*:[^{]*)?"
    % ("|".join(MODIFIERS), "|".join(TYPE_KINDS))
)
# 메서드 — 반환형 + 이름 + 괄호
RE_METHOD = re.compile(
    r"^\s*(?P<mods>(?:(?:%s)\s+)*)"
    r"(?P<ret>[\w<>\[\],.?\s]+?)\s+"
    r"(?P<name>\w+)\s*(?:<[\w,\s]+>\s*)?\((?P<params>[^;{]*)\)\s*(?P<tail>[{;]|=>|$)"
    % "|".join(MODIFIERS)
)
# 생성자 — 반환형 없이 이름 + 괄호
RE_CTOR = re.compile(
    r"^\s*(?P<mods>(?:(?:%s)\s+)*)(?P<name>\w+)\s*\((?P<params>[^;{]*)\)\s*"
    r"(?::\s*(?:base|this)\s*\([^)]*\)\s*)?(?P<tail>[{]|$)"
    % "|".join(MODIFIERS)
)
RE_PROPERTY = re.compile(
    r"^\s*(?P<mods>(?:(?:%s)\s+)*)"
    # 중괄호가 다음 줄에 오는 Allman 스타일이 많아 `$` 도 받습니다.
    # `;` 나 `=` 로 끝나는 줄은 필드라 여기 걸리지 않습니다.
    r"(?P<type>[\w<>\[\],.?\s]+?)\s+(?P<name>\w+)\s*(?P<tail>\{|=>|$)"
    % "|".join(MODIFIERS)
)
RE_FIELD = re.compile(
    r"^\s*(?P<mods>(?:(?:%s)\s+)*)"
    r"(?P<type>[\w<>\[\],.?\s]+?)\s+(?P<name>\w+)\s*(?:=[^;]*)?;"
    % "|".join(MODIFIERS)
)
# `public static readonly DependencyProperty XProperty =` 처럼 `;` 가 다음 줄에 있는 필드
RE_FIELD_OPEN = re.compile(
    r"^\s*(?P<mods>(?:(?:%s)\s+)*)"
    r"(?P<type>[\w<>\[\],.?\s]+?)\s+(?P<name>\w+)\s*=\s*$"
    % "|".join(MODIFIERS)
)
RE_EVENT = re.compile(
    r"^\s*(?P<mods>(?:(?:%s)\s+)*)event\s+(?P<type>[\w<>\[\],.?]+)\s+(?P<name>\w+)"
    % "|".join(MODIFIERS)
)
RE_ATTRIBUTE = re.compile(r"^\s*\[[\w\s(),.\"=:]*\]\s*$")

def last_word(s):
    """`List<string>` · `private static void` 의 마지막 낱말. 비면 "" 를 돌려줍니다."""
    parts = (s or "").strip().split()
    return parts[-1] if parts else ""


KEYWORD_NOT_TYPE = {"return", "if", "for", "foreach", "while", "switch", "using",
                    "lock", "catch", "else", "do", "try", "finally", "yield",
                    "case", "default", "break", "continue", "throw", "get", "set",
                    "add", "remove", "when", "where", "select", "from", "new"}


def find_block_end(masked_lines, start_idx):
    """start_idx 줄부터 `{` 를 찾아 짝이 맞는 `}` 줄 번호(0-based)를 돌려줍니다."""
    depth = 0
    started = False
    for k in range(start_idx, len(masked_lines)):
        for ch in masked_lines[k]:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
                if started and depth == 0:
                    return k
        if started and depth <= 0:
            return k
    return len(masked_lines) - 1


def parse_cs(rel_path, text):
    """C# 파일 하나에서 심볼 목록을 뽑습니다."""
    masked, strings = mask_cs(text)
    mlines = masked.split("\n")
    raw_lines = text.split("\n")
    symbols = []

    depth = 0
    type_stack = []        # [(name, depth_at_open, is_partial)]
    ns = ""
    pending_attrs = []
    i = 0

    while i < len(mlines):
        line = mlines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if RE_ATTRIBUTE.match(line):
            pending_attrs.append(raw_lines[i].strip())
            i += 1
            continue

        m = RE_NAMESPACE.match(line)
        if m:
            ns = m.group(1)
            depth += line.count("{") - line.count("}")
            pending_attrs = []
            i += 1
            continue

        m = RE_TYPE.match(line)
        if m and not stripped.startswith("//"):
            name = m.group("name")
            mods = m.group("mods").split()
            end = find_block_end(mlines, i)
            bases = [b.strip().split("<")[0].split(".")[-1]
                     for b in (m.group("bases") or "").lstrip(" :").split(",") if b.strip()]
            symbols.append({
                "kind": m.group("kind"),
                "name": name,
                "owner": ".".join(t[0] for t in type_stack) or ns,
                "file": rel_path,
                "lines": [i + 1, end + 1],
                "signature": raw_lines[i].strip().rstrip("{").strip(),
                "modifiers": mods,
                "attributes": pending_attrs[:],
                "bases": bases,
            })
            type_stack.append((name, depth, "partial" in mods, bases))
            depth += line.count("{") - line.count("}")
            pending_attrs = []
            i += 1
            continue

        # 타입 안에서만 멤버를 찾습니다
        if type_stack:
            cur_type = type_stack[-1][0]
            cur_bases = type_stack[-1][3]
            member = None

            me = RE_EVENT.match(line)
            mp = RE_PROPERTY.match(line)
            mm = RE_METHOD.match(line)
            mc = RE_CTOR.match(line)
            mf = RE_FIELD.match(line)
            mfo = None if mf else RE_FIELD_OPEN.match(line)

            if me:
                member = ("event", me.group("name"), me.group("mods").split())
            elif mm and last_word(mm.group("ret")) not in KEYWORD_NOT_TYPE \
                    and last_word(mm.group("ret")) \
                    and mm.group("name") not in KEYWORD_NOT_TYPE:
                member = ("method", mm.group("name"), mm.group("mods").split())
            elif mc and mc.group("name") == cur_type:
                member = ("constructor", mc.group("name"), mc.group("mods").split())
            elif mp and last_word(mp.group("type")) not in KEYWORD_NOT_TYPE \
                    and last_word(mp.group("type")) \
                    and mp.group("name") not in KEYWORD_NOT_TYPE:
                member = ("property", mp.group("name"), mp.group("mods").split())
            elif mf and last_word(mf.group("type")) not in KEYWORD_NOT_TYPE \
                    and last_word(mf.group("type")) \
                    and mf.group("name") not in KEYWORD_NOT_TYPE:
                member = ("field", mf.group("name"), mf.group("mods").split())
            elif mfo and last_word(mfo.group("type")) not in KEYWORD_NOT_TYPE \
                    and last_word(mfo.group("type")) \
                    and mfo.group("name") not in KEYWORD_NOT_TYPE:
                member = ("field", mfo.group("name"), mfo.group("mods").split())

            if member:
                kind, name, mods = member
                if kind == "field" and ";" not in line:
                    end = i
                    while end < len(mlines) - 1 and ";" not in mlines[end]:
                        end += 1
                elif "{" in line or (kind in ("method", "constructor", "property") and "=>" not in line and ";" not in line):
                    end = find_block_end(mlines, i)
                elif "=>" in line:
                    end = i
                    while end < len(mlines) and ";" not in mlines[end]:
                        end += 1
                    end = min(end, len(mlines) - 1)
                else:
                    end = i
                symbols.append({
                    "kind": kind,
                    "name": name,
                    "owner": cur_type,
                    "file": rel_path,
                    "lines": [i + 1, end + 1],
                    "signature": raw_lines[i].strip().rstrip("{").strip(),
                    "modifiers": mods,
                    "attributes": pending_attrs[:],
                    "bases": cur_bases,
                })
                depth += sum(l.count("{") - l.count("}") for l in mlines[i:end + 1])
                pending_attrs = []
                i = end + 1
                # 타입 블록이 닫혔으면 스택을 비웁니다
                while type_stack and depth <= type_stack[-1][1]:
                    type_stack.pop()
                continue

        depth += line.count("{") - line.count("}")
        while type_stack and depth <= type_stack[-1][1]:
            type_stack.pop()
        pending_attrs = []
        i += 1

    return symbols, masked, strings


# ────────────────────────────────────────────────────────────────────────
# 4. XAML 스캔 — WPF 가 참조를 숨겨 두는 곳 전부
# ────────────────────────────────────────────────────────────────────────
RE_XAML_COMMENT = re.compile(r"<!--.*?-->", re.S)
RE_ATTR = re.compile(r"([\w:.]+)\s*=\s*\"([^\"]*)\"")
RE_ELEMENT = re.compile(r"<\s*([\w:.]+)")
RE_MARKUP = re.compile(r"\{\s*([\w:]+)\s+([^}]*)\}")
RE_IDENT = re.compile(r"^[A-Za-z_]\w*$")

# WPF 에서 자주 쓰는 이벤트 속성. 여기 있으면 값은 핸들러 이름입니다.
EVENT_ATTRS = {
    "Click", "Loaded", "Unloaded", "Initialized", "SourceInitialized",
    "SelectionChanged", "SelectedItemChanged", "TextChanged", "Checked",
    "Unchecked", "Indeterminate", "GotFocus", "LostFocus", "KeyDown", "KeyUp",
    "PreviewKeyDown", "PreviewKeyUp", "MouseDown", "MouseUp", "MouseMove",
    "MouseDoubleClick", "MouseLeftButtonDown", "MouseLeftButtonUp",
    "MouseRightButtonDown", "MouseRightButtonUp", "MouseEnter", "MouseLeave",
    "MouseWheel", "PreviewMouseDown", "PreviewMouseLeftButtonDown",
    "Closing", "Closed", "Activated", "Deactivated", "StateChanged",
    "SizeChanged", "LayoutUpdated", "DataContextChanged", "Drop", "DragOver",
    "DragEnter", "DragLeave", "Expanded", "Collapsed", "ValueChanged",
    "CurrentCellChanged", "CellEditEnding", "RowEditEnding", "BeginningEdit",
    "AutoGeneratingColumn", "LoadingRow", "Sorting", "Scroll", "Handler",
    "ContextMenuOpening", "ToolTipOpening", "Completed", "Tick", "Error",
}


def parse_xaml(rel_path, text):
    body = RE_XAML_COMMENT.sub(" ", text)
    out = {
        "xNames": set(), "handlers": set(), "bindingPaths": set(),
        "resourceKeys": set(), "resourceRefs": set(), "types": set(),
        "attrNames": set(), "bareValues": set(), "commands": set(),
    }

    for el in RE_ELEMENT.findall(body):
        out["types"].add(el.split(":")[-1].split(".")[0])

    for name, value in RE_ATTR.findall(body):
        local = name.split(":")[-1]
        out["attrNames"].add(local.split(".")[-1])

        if local in ("Name",) or name in ("x:Name",):
            out["xNames"].add(value)
            continue
        if name == "x:Key":
            out["resourceKeys"].add(value)
            continue
        if name == "x:Class":
            out["types"].add(value.split(".")[-1])
            continue
        # 이벤트 속성의 값은 핸들러 이름입니다 (EventSetter Handler= 포함)
        if (local in EVENT_ATTRS or local.startswith("Preview")) and RE_IDENT.match(value):
            out["handlers"].add(value)
            continue

        # {Binding …} · {StaticResource …} · {x:Type …} 같은 마크업 확장
        for ext, arg in RE_MARKUP.findall(value):
            ext_local = ext.split(":")[-1]
            arg = arg.strip()
            if ext_local in ("Binding", "TemplateBinding"):
                path = arg
                mp = re.search(r"Path\s*=\s*([\w.\[\]]+)", arg)
                if mp:
                    path = mp.group(1)
                else:
                    path = arg.split(",")[0].strip()
                path = path.lstrip("(").split(".")[0].split("[")[0].strip()
                if RE_IDENT.match(path):
                    out["bindingPaths"].add(path)
                    if local in ("Command", "CommandParameter") or path.endswith("Command"):
                        out["commands"].add(path)
            elif ext_local in ("StaticResource", "DynamicResource", "ThemeResource"):
                key = arg.split(",")[0].strip()
                if key:
                    out["resourceRefs"].add(key)
            elif ext_local == "Type":
                out["types"].add(arg.split(":")[-1].strip())
            elif ext_local == "Static":
                out["types"].add(arg.split(":")[-1].split(".")[0].strip())

        # 마크업 확장이 아닌 맨몸 식별자. `Auto` · `Center` 같은 열거형 값이 대부분이라
        # 그 자체로는 신호가 약합니다 — 메서드 이름과 맞아떨어질 때만 씁니다.
        if "{" not in value and RE_IDENT.match(value):
            out["bareValues"].add(value)

        # TargetType="Button" · DataType="local:Lot" 같은 맨 타입 이름
        if local in ("TargetType", "DataType", "Type"):
            out["types"].add(value.split(":")[-1].strip())

    return out


RE_RESX_KEY = re.compile(r"<data\s+name\s*=\s*\"([^\"]+)\"")


# ────────────────────────────────────────────────────────────────────────
# 5. iBATIS mapper 스캔
# ────────────────────────────────────────────────────────────────────────
RE_MAPPER_NS = re.compile(r"<(?:sqlMap|mapper)\b[^>]*namespace\s*=\s*\"([^\"]+)\"")
RE_MAPPER_STMT = re.compile(
    r"<(select|insert|update|delete|statement|procedure|sql)\b[^>]*\bid\s*=\s*\"([^\"]+)\"[^>]*>(.*?)</\1>",
    re.S | re.I,
)
RE_SQL_COMMENT = re.compile(r"/\*.*?\*/", re.S)
# DPI/iBATIS 관례상 SQL ID 는 `lot.selectMcLot` 처럼 **양쪽 모두 소문자로 시작**합니다.
# 이 조건이 없으면 `System.Data` · `YOEDSMOV.Common` 같은 .NET 이름이
# "호출하는데 정의 없음"으로 잡혀 리포트에 오탐이 실립니다.
# 팀 관례가 다르면 이 정규식 하나만 고치면 됩니다. (collect.py 의 RE_SQL_ID 와 같은 규칙)
RE_SQL_ID_LITERAL = re.compile(r"^[a-z][A-Za-z0-9_]*\.[a-z][A-Za-z0-9_]*$")
RE_SQL_KEYWORD = re.compile(r"\b(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|MERGE)\b", re.I)


def parse_mapper(rel_path, text):
    ns_m = RE_MAPPER_NS.search(text)
    ns = ns_m.group(1) if ns_m else Path(rel_path).stem
    stmts = []
    for m in RE_MAPPER_STMT.finditer(text):
        sid = m.group(2)
        full = sid if "." in sid else "%s.%s" % (ns, sid)
        line = text.count("\n", 0, m.start()) + 1
        stmts.append({
            "id": full,
            "kind": m.group(1).lower(),
            "file": rel_path,
            "line": line,
            "body": m.group(3).strip(),
        })
    return ns, stmts


def normalize_sql(body):
    s = RE_SQL_COMMENT.sub(" ", body)
    s = re.sub(r"<[^>]+>", " ", s)          # 동적 태그 제거
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


# ────────────────────────────────────────────────────────────────────────
# 6. 중복 탐지 — 토큰 5-gram Jaccard
# ────────────────────────────────────────────────────────────────────────
RE_TOKEN = re.compile(r"[A-Za-z_]\w*|\d+|[^\s\w]")


def tokenize_body(masked_body):
    toks = []
    for t in RE_TOKEN.findall(masked_body):
        if t.isdigit():
            toks.append("NUM")
        else:
            toks.append(t)
    return toks


def grams(tokens, k=DUP_GRAM):
    if len(tokens) < k:
        return set()
    return {" ".join(tokens[i:i + k]) for i in range(len(tokens) - k + 1)}


def find_duplicates(items, threshold=DUP_THRESHOLD):
    """items = [(key, gram_set)] → [(key_a, key_b, similarity, shared)]"""
    inverted = defaultdict(list)
    for idx, (_key, gs) in enumerate(items):
        for g in gs:
            inverted[g].append(idx)

    shared = Counter()
    for idxs in inverted.values():
        if len(idxs) < 2 or len(idxs) > 40:      # 너무 흔한 gram 은 신호가 없습니다
            continue
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                shared[(idxs[a], idxs[b])] += 1

    out = []
    for (a, b), sh in shared.items():
        ga, gb = items[a][1], items[b][1]
        union = len(ga | gb)
        if not union:
            continue
        sim = len(ga & gb) / union
        if sim >= threshold:
            out.append((items[a][0], items[b][0], round(sim, 3), sh))
    out.sort(key=lambda r: -r[2])
    return out


# ────────────────────────────────────────────────────────────────────────
# 7. 본체
# ────────────────────────────────────────────────────────────────────────
def collect_files(root: Path):
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*") if p.is_file())


def main():
    ap = argparse.ArgumentParser(description="심볼·참조·중복·SQL 인덱서")
    ap.add_argument("--ws", required=True, help="작업 폴더 (_workspace/scan-…)")
    args = ap.parse_args()

    ws = Path(args.ws)
    src = ws / "src"
    src_sql = ws / "src-sql"

    if not src.exists():
        print("✗ %s 가 없습니다." % src)
        print("  → 먼저 collect.py 를 돌려 원문을 수집하세요.")
        return 1

    # ---- 읽기 ----------------------------------------------------------
    cs_files, xaml_files, resx_files, mapper_files = [], [], [], []
    for p in collect_files(src):
        rel = p.relative_to(src).as_posix()
        low = p.suffix.lower()
        if low in CS_EXT:
            cs_files.append((rel, p))
        elif low in XAML_EXT:
            xaml_files.append((rel, p))
        elif low in RESX_EXT:
            resx_files.append((rel, p))
        elif low in XMLISH_EXT:
            xaml_files.append((rel, p))      # 같은 스캐너로 봅니다
    for p in collect_files(src_sql):
        mapper_files.append((p.relative_to(src_sql).as_posix(), p))

    total_lines = 0

    # ---- C# ------------------------------------------------------------
    symbols = []
    text_of = {}         # rel → 원문 (문자열 연결 판별에 씁니다)
    cs_masked = {}       # rel → masked text
    cs_strings = []      # (rel, line, content)
    for rel, p in cs_files:
        text = read_text(p)
        total_lines += text.count("\n") + 1
        text_of[rel] = text
        syms, masked, strings = parse_cs(rel, text)
        symbols.extend(syms)
        cs_masked[rel] = masked
        for ln, content in strings:
            cs_strings.append((rel, ln, content))

    # ---- XAML ----------------------------------------------------------
    xaml = {
        "xNames": set(), "handlers": set(), "bindingPaths": set(),
        "resourceKeys": set(), "resourceRefs": set(), "types": set(),
        "attrNames": set(), "bareValues": set(), "commands": set(),
    }
    xaml_texts = {}
    for rel, p in xaml_files:
        text = read_text(p)
        total_lines += text.count("\n") + 1
        xaml_texts[rel] = text
        got = parse_xaml(rel, text)
        for k in xaml:
            xaml[k] |= got[k]

    resx_keys = set()
    for rel, p in resx_files:
        text = read_text(p)
        total_lines += text.count("\n") + 1
        resx_keys |= set(RE_RESX_KEY.findall(text))

    # ---- mapper --------------------------------------------------------
    sql_defined = []
    for rel, p in mapper_files:
        text = read_text(p)
        total_lines += text.count("\n") + 1
        _ns, stmts = parse_mapper(rel, text)
        sql_defined.extend(stmts)

    # ---- 참조 세기 -----------------------------------------------------
    # C# 식별자 출현 횟수 (마스킹된 텍스트 = 주석·문자열 제외)
    cs_ident_count = Counter()
    cs_ident_sites = defaultdict(list)
    for rel, masked in cs_masked.items():
        for ln, line in enumerate(masked.split("\n"), 1):
            for tok in re.findall(r"[A-Za-z_]\w*", line):
                cs_ident_count[tok] += 1
                if len(cs_ident_sites[tok]) < 12:
                    cs_ident_sites[tok].append({"file": rel, "line": ln})

    # 문자열 안 출현 (W8 속성 변경 알림 · W11 리플렉션 · SQL ID)
    string_idents = Counter()
    reflection_names = set()
    inpc_names = set()
    sql_called = []
    inline_sql = []
    for rel, ln, content in cs_strings:
        c = content.strip()
        if RE_IDENT.match(c):
            string_idents[c] += 1
        if RE_SQL_ID_LITERAL.match(c):
            sql_called.append({"id": c, "file": rel, "line": ln})
        if RE_SQL_KEYWORD.search(content):
            raw_line = ""
            inline_sql.append({
                "file": rel, "line": ln,
                "concatenated": False,       # 아래에서 다시 봅니다
                "preview": re.sub(r"\s+", " ", content.strip())[:120],
            })

    # 문자열 참조의 성격을 주변 코드로 판별합니다
    for rel, masked in cs_masked.items():
        lines = masked.split("\n")
        for ln, line in enumerate(lines, 1):
            if re.search(r"(OnPropertyChanged|RaisePropertyChanged|NotifyOfPropertyChange|PropertyChanged)", line):
                for _r, sln, content in cs_strings:
                    if _r == rel and sln == ln and RE_IDENT.match(content.strip()):
                        inpc_names.add(content.strip())
            if re.search(r"(GetMethod|GetProperty|GetField|GetType|InvokeMember|CreateInstance)", line):
                for _r, sln, content in cs_strings:
                    if _r == rel and sln == ln and RE_IDENT.match(content.strip()):
                        reflection_names.add(content.strip())

    # 인라인 SQL 이 문자열 연결로 조립되는지 — 같은 **메서드 전체**를 봅니다.
    # `AddSql("SELECT …")` 와 `+ lineId +` 가 여러 줄 떨어져 있는 것이 보통이라,
    # 한두 줄 창으로 보면 전부 놓칩니다.
    for item in inline_sql:
        owner = None
        for sym in symbols:
            if sym["file"] == item["file"] and sym["kind"] in ("method", "property", "constructor") \
                    and sym["lines"][0] <= item["line"] <= sym["lines"][1]:
                if owner is None or sym["lines"][0] > owner["lines"][0]:
                    owner = sym
        if owner:
            raw = text_of.get(item["file"], "").split("\n")
            body = "\n".join(raw[owner["lines"][0] - 1:owner["lines"][1]])
            item["owner"] = owner["name"]
        else:
            raw = text_of.get(item["file"], "").split("\n")
            body = "\n".join(raw[max(0, item["line"] - 3):item["line"] + 3])
            item["owner"] = None
        item["concatenated"] = bool(re.search(r"\"\s*\+|\+\s*\"", body))

    # 파일이 리플렉션을 쓰는지 (confidence 를 낮추는 신호)
    files_with_reflection = {
        rel for rel, masked in cs_masked.items()
        if re.search(r"(GetMethod|GetProperty|GetField|InvokeMember|Activator\.CreateInstance|Type\.GetType)", masked)
    }

    # ---- 심볼에 참조 붙이기 --------------------------------------------
    dp_backing = {s["name"][:-8] for s in symbols
                  if s["kind"] == "field" and s["name"].endswith("Property")}
    converter_types = {s["name"] for s in symbols
                       if s["kind"] == "class"
                       and re.search(r"IValueConverter|IMultiValueConverter", s["signature"])}

    method_names = {s["name"] for s in symbols if s["kind"] == "method"}
    matched_handlers = sorted(
        xaml["handlers"] | (xaml["bareValues"] & method_names))

    for n, s in enumerate(symbols, 1):
        s["id"] = "SY%03d" % n
        name = s["name"]

        # 선언 자체가 1회로 세어졌으므로 뺍니다
        cs_refs = max(0, cs_ident_count.get(name, 0) - 1)

        hints = []
        if name in xaml["handlers"]:
            hints.append("xaml-handler")
        elif s["kind"] == "method" and name in xaml["bareValues"]:
            hints.append("xaml-handler")
        if name in xaml["xNames"]:
            hints.append("x-name")
        if name in xaml["bindingPaths"]:
            hints.append("binding")
        if name in xaml["commands"]:
            hints.append("binding")
        if name in xaml["resourceKeys"] or name in xaml["resourceRefs"]:
            hints.append("resource-key")
        if name in converter_types and (name in xaml["resourceKeys"] or name in xaml["types"]):
            hints.append("converter")
        if name in dp_backing or (name.endswith("Property") and name[:-8] in {x["name"] for x in symbols}):
            hints.append("dependency-property")
        if name in xaml["attrNames"] and s["kind"] in ("property", "field"):
            hints.append("binding")
        if name in xaml["types"] and s["kind"] in TYPE_KINDS:
            hints.append("xaml-type")
        if name in inpc_names:
            hints.append("inpc-string")
        if name in reflection_names:
            hints.append("reflection")
        if name in resx_keys:
            hints.append("resx")
        if "partial" in s["modifiers"]:
            hints.append("generated")
        # 소속 타입이 인터페이스를 구현하면, 그 타입의 public 멤버는
        # 호출부가 안 보여도 계약상 있어야 하는 것일 수 있습니다.
        # (.NET 관례: 인터페이스 이름은 `I` + 대문자)
        if s["kind"] in ("method", "property", "event") and "public" in s["modifiers"] \
                and any(re.match(r"^I[A-Z]", b) for b in s.get("bases", [])):
            hints.append("interface-member")
        if re.search(r"\b%s\s*\+=" % re.escape(name), "\n".join(cs_masked.values())):
            hints.append("event-subscribe")

        s["wpfHints"] = sorted(set(hints))
        s["refs"] = {
            "cs": cs_refs,
            "xaml": sum(1 for k in ("bareValues", "xNames", "bindingPaths",
                                    "resourceKeys", "resourceRefs", "types",
                                    "attrNames", "handlers", "commands")
                        if name in xaml[k]),
            "string": string_idents.get(name, 0),
        }
        s["refs"]["total"] = s["refs"]["cs"] + s["refs"]["xaml"] + s["refs"]["string"]
        s["refSites"] = cs_ident_sites.get(name, [])[:8]

    # ---- 미참조 판정 ---------------------------------------------------
    LIFECYCLE = {"InitializeComponent", "Main", "Dispose", "ToString", "Equals",
                 "GetHashCode", "Finalize", "OnStartup", "OnExit"}
    LOW_MODS = {"override", "virtual", "abstract", "extern", "partial"}

    unreferenced = []
    for s in symbols:
        if s["refs"]["total"] > 0 or s["wpfHints"]:
            continue
        if s["kind"] == "constructor" or s["name"] in LIFECYCLE:
            continue

        mods = set(s["modifiers"])
        caveats = []
        if mods & LOW_MODS:
            conf = "낮음"
            caveats.append("`%s` 이라 상위 타입·인터페이스 계약일 수 있습니다"
                           % " ".join(sorted(mods & LOW_MODS)))
        elif s["attributes"]:
            conf = "낮음"
            caveats.append("특성(attribute)이 붙어 있어 프레임워크가 부를 수 있습니다: %s"
                           % " ".join(s["attributes"])[:80])
        elif s["file"] in files_with_reflection:
            conf = "낮음"
            caveats.append("같은 파일이 리플렉션을 씁니다 — 이름이 문자열로 조립될 수 있습니다")
        elif s.get("bases") and (mods & {"public", "protected"}):
            conf = "낮음"
            caveats.append("소속 타입이 `%s` 을 상속합니다 — 상위 타입 계약일 수 있습니다"
                           % ", ".join(s["bases"]))
        elif mods & {"public", "protected"}:
            conf = "중간"
            caveats.append("`%s` 이라 이 경로 밖(다른 어셈블리·프로젝트)에서 쓸 수 있습니다"
                           % ("public" if "public" in mods else "protected"))
        else:
            conf = "높음"

        if not mapper_files and s["kind"] in ("class",):
            caveats.append("mapper 를 수집하지 못해 XML 쪽 참조는 보지 못했습니다")

        unreferenced.append({
            "symbolId": s["id"],
            "name": s["name"],
            "kind": s["kind"],
            "file": s["file"],
            "lines": s["lines"],
            "confidence": conf,
            "why": "C#·XAML·문자열 어디서도 참조가 없습니다",
            "caveats": caveats,
        })

    # ---- 중복 후보 -----------------------------------------------------
    dup_items = []
    method_syms = [s for s in symbols if s["kind"] in ("method", "property")]
    if len(method_syms) > MAX_SYMBOLS:
        warn("심볼이 %d개입니다. 중복 비교는 긴 것부터 %d개만 봅니다."
             % (len(method_syms), MAX_SYMBOLS))
        method_syms.sort(key=lambda s: -(s["lines"][1] - s["lines"][0]))
        method_syms = method_syms[:MAX_SYMBOLS]

    for s in method_syms:
        span = s["lines"][1] - s["lines"][0] + 1
        if span < DUP_MIN_LINES:
            continue
        masked = cs_masked.get(s["file"], "")
        body = "\n".join(masked.split("\n")[s["lines"][0] - 1:s["lines"][1]])
        gs = grams(tokenize_body(body))
        if gs:
            dup_items.append((s["id"], gs))

    sym_by_id = {s["id"]: s for s in symbols}
    duplicate_candidates = []
    for n, (a, b, sim, sh) in enumerate(find_duplicates(dup_items), 1):
        sa, sb = sym_by_id[a], sym_by_id[b]
        duplicate_candidates.append({
            "id": "DP%03d" % n,
            "similarity": sim,
            "sharedGrams": sh,
            "a": {"symbolId": a, "name": sa["name"], "file": sa["file"], "lines": sa["lines"]},
            "b": {"symbolId": b, "name": sb["name"], "file": sb["file"], "lines": sb["lines"]},
        })

    # XAML 반복 블록
    xaml_blocks = defaultdict(list)
    for rel, text in xaml_texts.items():
        lines = [re.sub(r"\s+", " ", l.strip()) for l in
                 RE_XAML_COMMENT.sub(" ", text).split("\n")]
        for i in range(len(lines) - XAML_DUP_MIN_LINES + 1):
            chunk = lines[i:i + XAML_DUP_MIN_LINES]
            if sum(1 for c in chunk if c) < XAML_DUP_MIN_LINES:
                continue
            key = "\n".join(chunk)
            xaml_blocks[key].append({"file": rel, "line": i + 1})
    xaml_repeats = []
    for n, (key, sites) in enumerate(
            sorted((kv for kv in xaml_blocks.items() if len(kv[1]) > 1),
                   key=lambda kv: -len(kv[1]))[:20], 1):
        xaml_repeats.append({
            "id": "XD%03d" % n,
            "count": len(sites),
            "lines": XAML_DUP_MIN_LINES,
            "sites": sites[:6],
            "preview": key.split("\n")[0][:100],
        })

    # ---- SQL 대조 ------------------------------------------------------
    defined_ids = {d["id"] for d in sql_defined}
    called_ids = {c["id"] for c in sql_called}
    unused_ids = sorted(defined_ids - called_ids)
    missing_ids = sorted(i for i in called_ids - defined_ids)

    sql_dup_items = [(d["id"], grams(normalize_sql(d["body"]).split(), 5))
                     for d in sql_defined]
    sql_dup_items = [(k, g) for k, g in sql_dup_items if g]
    sql_duplicates = [
        {"ids": [a, b], "similarity": sim}
        for a, b, sim, _sh in find_duplicates(sql_dup_items, threshold=0.8)
    ]

    # ---- 쓰기 ----------------------------------------------------------
    index = {
        "_comment": "index.py 가 기계적으로 센 것입니다. LLM 이 쓰지 않습니다. "
                    "검증관은 미참조·중복 지적을 이 파일과 대조합니다.",
        "stats": {
            "files": len(cs_files) + len(xaml_files) + len(resx_files),
            "mapperFiles": len(mapper_files),
            "lines": total_lines,
            "symbols": len(symbols),
            "sqlDefined": len(defined_ids),
            "sqlCalled": len(called_ids),
        },
        "symbols": symbols,
        "unreferenced": unreferenced,
        "duplicateCandidates": duplicate_candidates,
        "xamlRepeats": xaml_repeats,
        "sql": {
            "defined": [{"id": d["id"], "kind": d["kind"], "file": d["file"], "line": d["line"]}
                        for d in sql_defined],
            "called": sql_called,
            "unusedIds": unused_ids,
            "missingIds": missing_ids,
            "duplicateBodies": sql_duplicates,
            "inline": inline_sql,
        },
        "wpf": {
            "xNames": sorted(xaml["xNames"]),
            "handlers": matched_handlers,
            "bindingPaths": sorted(xaml["bindingPaths"]),
            "resourceKeys": sorted(xaml["resourceKeys"]),
            "resourceRefs": sorted(xaml["resourceRefs"]),
            "converters": sorted(converter_types),
            "dependencyProperties": sorted(dp_backing),
            "commands": sorted(xaml["commands"]),
            "resxKeys": sorted(resx_keys),
            "interfaceMembers": sorted(
                {"%s.%s" % (s["owner"], s["name"]) for s in symbols
                 if "interface-member" in s["wpfHints"]}),
        },
    }

    (ws / "1-index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8", newline="")
    (ws / "1-index.md").write_text(render_md(index), encoding="utf-8", newline="")

    # ---- 보고 ----------------------------------------------------------
    st = index["stats"]
    print("✓ %s" % (ws / "1-index.json"))
    print("✓ %s" % (ws / "1-index.md"))
    print()
    print("  파일 %d · 줄 %d · 심볼 %d" % (st["files"], st["lines"], st["symbols"]))
    hi = sum(1 for u in unreferenced if u["confidence"] == "높음")
    print("  미참조 후보 %d건 (확신 높음 %d)" % (len(unreferenced), hi))
    print("  중복 후보 %d쌍 · XAML 반복 블록 %d종" % (len(duplicate_candidates), len(xaml_repeats)))
    if mapper_files:
        print("  SQL 정의 %d · 호출 %d · 미사용 %d · 정의없음 %d"
              % (st["sqlDefined"], st["sqlCalled"], len(unused_ids), len(missing_ids)))
    else:
        print("  mapper 를 수집하지 못했습니다 — SQL 미사용 판정은 하지 않았습니다")
    print()
    print("다음: 1-scope.md 와 1-units.md 를 작성하세요.")
    return 0


# ────────────────────────────────────────────────────────────────────────
# 8. 사람과 LLM 이 읽는 요약
# ────────────────────────────────────────────────────────────────────────
def render_md(ix):
    st = ix["stats"]
    L = []
    a = L.append
    a("# 코드 인덱스")
    a("")
    a("`index.py` 가 기계적으로 센 것입니다. **여기 숫자는 판단이 아니라 사실입니다.**")
    a("리뷰어는 이 후보를 *판정*하고, 검증관은 지적을 이 표와 대조합니다.")
    a("")
    a("| | |")
    a("|---|---|")
    a("| 파일 | %d (mapper %d) |" % (st["files"], st["mapperFiles"]))
    a("| 줄 | %d |" % st["lines"])
    a("| 심볼 | %d |" % st["symbols"])
    a("| SQL 정의 / 호출 | %d / %d |" % (st["sqlDefined"], st["sqlCalled"]))
    a("")

    a("## 미참조 후보")
    a("")
    if not ix["unreferenced"]:
        a("없습니다.")
    else:
        a("**`확신` 은 기계가 본 것까지입니다.** `중간`·`낮음` 은 리뷰어가 근거를 더 찾아야 합니다.")
        a("")
        a("| 심볼 | 유형 | 파일:줄 | 확신 | 참고 |")
        a("|---|---|---|---|---|")
        for u in ix["unreferenced"]:
            a("| `%s` | %s | %s:%d | %s | %s |" % (
                u["name"], u["kind"], u["file"], u["lines"][0], u["confidence"],
                " / ".join(u["caveats"]) or "—"))
    a("")

    a("## 중복 후보")
    a("")
    if not ix["duplicateCandidates"]:
        a("없습니다.")
    else:
        a("| ID | 유사도 | A | B |")
        a("|---|---|---|---|")
        for d in ix["duplicateCandidates"]:
            a("| %s | %.2f | `%s` %s:%d | `%s` %s:%d |" % (
                d["id"], d["similarity"],
                d["a"]["name"], d["a"]["file"], d["a"]["lines"][0],
                d["b"]["name"], d["b"]["file"], d["b"]["lines"][0]))
    a("")

    if ix["xamlRepeats"]:
        a("## XAML 반복 블록")
        a("")
        a("| ID | 반복 | 첫 줄 |")
        a("|---|---|---|")
        for x in ix["xamlRepeats"]:
            a("| %s | %d회 | `%s` |" % (x["id"], x["count"], x["preview"]))
        a("")

    sq = ix["sql"]
    a("## SQL")
    a("")
    a("| | |")
    a("|---|---|")
    a("| 정의됐지만 호출 없음 | %s |" % (", ".join("`%s`" % i for i in sq["unusedIds"]) or "없음"))
    a("| 호출하는데 정의 없음 | %s |" % (", ".join("`%s`" % i for i in sq["missingIds"]) or "없음"))
    a("| 본문이 거의 같은 쌍 | %s |" % (", ".join("`%s` ↔ `%s`" % (d["ids"][0], d["ids"][1])
                                            for d in sq["duplicateBodies"]) or "없음"))
    a("| 인라인 SQL | %d곳 (문자열 연결 %d곳) |" % (
        len(sq["inline"]), sum(1 for i in sq["inline"] if i["concatenated"])))
    a("")

    w = ix["wpf"]
    a("## WPF 참조 경로 (미참조 판정의 근거)")
    a("")
    a("아래에 이름이 있으면 **C# 에서 호출이 안 보여도 쓰이고 있는 것**입니다.")
    a("")
    a("| 경로 | 개수 | 예 |")
    a("|---|---|---|")
    for label, key in (("XAML 핸들러", "handlers"), ("x:Name", "xNames"),
                       ("바인딩 경로", "bindingPaths"), ("리소스 키", "resourceKeys"),
                       ("컨버터", "converters"), ("의존 속성", "dependencyProperties"),
                       ("명령", "commands"), ("resx 키", "resxKeys"),
                       ("인터페이스 계약 멤버", "interfaceMembers")):
        vals = w.get(key, [])
        a("| %s | %d | %s |" % (label, len(vals),
                                ", ".join("`%s`" % v for v in vals[:6]) or "—"))
    a("")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
