#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
화면이 밖으로 나가는 호출을 가려내는 규칙 — `collect.py` 와 `index.py` 공용.

왜 한 파일에 모았나
-------------------
같은 규칙을 두 스크립트가 씁니다. 한쪽만 고치면 수집과 인덱싱이 어긋나서,
가져오지도 않은 것을 「정의 없음」이라고 보고하는 식의 오탐이 납니다.
**팀 관례가 바뀌면 아래 `KIND_*` 세 줄만** 고치면 둘 다 따라옵니다.

이 코드베이스가 밖으로 나가는 길
--------------------------------
전부 TibRV 로 나갑니다. **첫 번째 인자가 무엇을 하는 호출인지 말해 줍니다.**

    SendMessageWithJSON(SQLEXEC, …, _sql.GetSql(), 60)
      → 화면이 `_sql` 에 조립해 둔 SQL. **ID 가 없습니다.** 화면 안에서 읽습니다

    SendMessageWithJSON(DPICALL, …, "mat.selectTrimMatId", _appName, _param)
      → mapper 의 SQL ID. `matMapper.xml` 에 본문이 있습니다

    SendMessage("LOTCOMMENT", …, m_StrAppname, Params, 30)
      → Rule 시스템 메시지. **로직이 백엔드에 있습니다**

    SendMessageWithJSONToTextResult(SET_SIMAXDATA, …, "legacy_semis.updateSemisDelivery", …)
      → 이것도 Rule 시스템 메시지. 뒤의 문자열이 SQL ID 처럼 생겼지만
        **mapper 에 없습니다.** 찾으러 가면 영원히 「정의 없음」이 됩니다

그래서 종류를 **화이트리스트로** 가릅니다. Rule 메시지 이름은 `LOTCOMMENT` ·
`TKIN` · `TKOUT` · `ISSUE` … 로 열려 있어 열거할 수 없습니다. 대신
**SQL 을 가진 종류만 적어 두고, 나머지는 전부 Rule 로 봅니다.** 새 메시지가
생겨도 저절로 맞습니다 — 반대로 했다면 새 메시지마다 오탐이 납니다.

표준 라이브러리만 씁니다.
"""

import re

# ── 팀 관례가 바뀌면 여기만 고치세요 ────────────────────────────────────
#
# **SQL 을 가진 종류는 이 둘뿐입니다.** 새 종류를 여기 적기 전에
# 실제 코드에 그런 호출이 있는지 먼저 확인하세요 — 없는 이름을 적어 두면
# 아무 일도 안 하지만, 있는 이름을 빠뜨리면 그 SQL ID 가 Rule 로 분류되어
# **mapper 를 아예 안 가져옵니다.**
KIND_MAPPER = ("DPICALL",)             # 인자 중 `ns.id` 가 mapper 의 SQL ID
KIND_INLINE = ("SQLEXEC",)             # 화면이 조립한 SQL. ID 가 없습니다
KIND_RULE = ("SET_SIMAXDATA",)         # 이름이 알려진 Rule 메시지 (문서용)
# 그 밖에 RV 로 나가는 것은 **전부** Rule 시스템 메시지로 봅니다.

# TibRV 보내는 메서드. `SendMessage` · `SendMessageWithJSON` ·
# `SendMessageWithJSONToTextResult` … 이름이 계속 늘어서 접두사로 잡습니다.
RE_RV_SEND = re.compile(r"\bSendMessage\w*\s*\(")

# DPI/iBATIS 관례상 SQL ID 는 `lot.selectMcLot` 처럼 **양쪽 모두 소문자로 시작**합니다.
# 이 조건이 `System.Data` · `YOEDSMOV.Common` 같은 .NET 이름을 걸러 줍니다.
RE_SQL_ID = re.compile(r"\"([a-z][A-Za-z0-9_]*\.[a-z][A-Za-z0-9_]*)\"")

# 첫 인자 — 맨몸 상수(`DPICALL`) 이거나 문자열(`"LOTCOMMENT"`) 입니다
RE_FIRST_ARG = re.compile(r"^\s*(?:\"([A-Za-z_]\w*)\"|([A-Za-z_]\w*))\s*(?:,|$)")

# 얇은 래퍼를 거치는 형태도 있습니다: `_sqlManager.DPICALL("lot.selectMcLot")`
RE_WRAPPER = re.compile(
    r"\b(%s)\s*\(" % "|".join(KIND_MAPPER + KIND_INLINE + KIND_RULE))

MAX_ARGS_CHARS = 4000      # 인자 목록이 이보다 길면 호출이 아닙니다


def _balanced_args(text, open_idx):
    """`(` 위치에서 시작해 짝이 맞는 `)` 까지의 인자 텍스트를 돌려줍니다.

    호출이 여러 줄에 걸쳐 있어도 됩니다 — 실제 코드가 그렇습니다.
    문자열 안의 괄호에 속지 않도록 따옴표를 건너뜁니다.
    """
    depth = 0
    i = open_idx
    n = min(len(text), open_idx + MAX_ARGS_CHARS)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == '"':
                    break
                i += 1
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:i]
        i += 1
    return None


def _kind_of(args):
    """인자 목록의 첫 인자를 호출 종류로 읽습니다."""
    m = RE_FIRST_ARG.match(args)
    if not m:
        return None
    return m.group(1) or m.group(2)


def classify(text):
    """C# 원문에서 밖으로 나가는 호출을 가려냅니다.

    돌려주는 것 — (sqlIds, ruleIds, inlineCalls, claimed)

        sqlIds       mapper 에서 본문을 찾아야 하는 SQL ID
        ruleIds      Rule 시스템으로 나간 것. **찾지 않습니다**
        inlineCalls  화면이 조립한 SQL 을 보낸 자리 (문자 오프셋)
        claimed      위에서 이미 성격이 정해진 리터럴 (중복 집계 방지용)

    호출 밖에 홀로 있는 `ns.id` 리터럴은 여기서 판단하지 않습니다.
    부르는 쪽이 안 보이면 성격을 알 수 없어서, 부르는 쪽이 `sqlIds` 로
    넉넉히 잡습니다 (변수에 담아 넘기는 코드가 있습니다).
    """
    sql_ids, rule_ids, inline_at, claimed = set(), set(), [], set()

    for m in RE_RV_SEND.finditer(text):
        args = _balanced_args(text, m.end() - 1)
        if args is None:
            continue
        kind = _kind_of(args)
        found = set(RE_SQL_ID.findall(args))
        claimed |= found
        if kind in KIND_MAPPER:
            sql_ids |= found
        elif kind in KIND_INLINE:
            inline_at.append(m.start())
        else:
            # SET_SIMAXDATA · LOTCOMMENT · TKIN · TKOUT · ISSUE …
            # 이름을 열거하지 않습니다. RV 로 나가는데 SQL 종류가 아니면 Rule 입니다.
            rule_ids |= found

    # 얇은 래퍼 형태: `_sqlManager.DPICALL("lot.selectMcLot")`
    for m in RE_WRAPPER.finditer(text):
        args = _balanced_args(text, m.end() - 1)
        if args is None:
            continue
        kind = m.group(1)
        found = set(RE_SQL_ID.findall(args))
        claimed |= found
        if kind in KIND_MAPPER:
            sql_ids |= found
        elif kind in KIND_INLINE:
            inline_at.append(m.start())
        else:
            rule_ids |= found

    # 같은 리터럴이 양쪽에 잡히면 **Rule 쪽을 믿습니다.**
    # 틀렸을 때 더 싼 쪽이 그쪽입니다 — 못 찾은 것을 「확인 못 함」으로 남기는 것이,
    # 멀쩡한 백엔드 호출을 「실행하면 터진다」로 싣는 것보다 낫습니다.
    sql_ids -= rule_ids
    return sorted(sql_ids), sorted(rule_ids), inline_at, claimed


def namespaces_of(sql_ids):
    """SQL ID 들의 네임스페이스를 모읍니다."""
    return {i.split(".")[0] for i in sql_ids}
