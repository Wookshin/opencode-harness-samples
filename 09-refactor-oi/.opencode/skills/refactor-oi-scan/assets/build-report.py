#!/usr/bin/env python3
"""build-report.py — findings.json → 팀 리팩토링 회의용 단일 HTML

    python build-report.py <findings.json> <out.html> [1-index.json]

이 스크립트가 존재하는 이유:
    **현재 코드를 LLM 이 옮겨 적지 않게 하려고.**
    리포트에 실리는 코드는 전부 여기가 `src/` 원문에서 직접 잘라 씁니다.
    LLM 은 좌표(unitId · line)와 제안만 씁니다.

    같은 이유로 **기계가 센 숫자**(미참조 N · 중복 N쌍 · 미사용 SQL N)도
    LLM 을 거치지 않습니다. 1-index.json 에서 직접 읽어 싣습니다.

    예외는 `suggestion` 하나입니다. 제안 코드는 본래 원문에 없으므로
    JSON 에 들어올 수밖에 없습니다. 리포트가 그 칸을 「제안」으로 따로 그려
    원문과 섞이지 않게 합니다.

표준 라이브러리만 씁니다. pip 설치 불필요. Python 3.8 이상.
"""
import json
import sys
from pathlib import Path

if sys.version_info < (3, 8):
    sys.exit("✗ Python 3.8 이상이 필요합니다 (현재 %s)" % sys.version.split()[0])

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "report-template.html"

problems = []


def bad(msg):
    problems.append(msg)


def die(msg):
    print("✗ " + msg, file=sys.stderr)
    raise SystemExit(1)


# ── 인자 ────────────────────────────────────────────────────────────────
argv = sys.argv[1:]
if len(argv) < 2:
    die("사용법: python build-report.py <findings.json> <out.html> [1-index.json]")

findings_path = Path(argv[0]).resolve()
out_path = Path(argv[1]).resolve()
if not findings_path.exists():
    die("findings.json 을 찾을 수 없습니다: %s" % findings_path)
if not TEMPLATE.exists():
    die("템플릿을 찾을 수 없습니다: %s" % TEMPLATE)

WS = findings_path.parent                       # 모든 상대 경로의 기준
index_path = Path(argv[2]).resolve() if len(argv) > 2 else WS / "1-index.json"


def read_text(p: Path) -> str:
    """텍스트 파일을 인코딩을 가려 읽습니다.

    셸 리디렉션(`>`)의 기본 인코딩은 셸·버전마다 다릅니다. Windows PowerShell 5.1 은
    UTF-16LE 로 씁니다. 그대로 UTF-8 로 읽으면 **오류 없이** 파일이 통째로 안 읽히고,
    리포트에서 코드만 조용히 사라집니다. 그 사고를 여기서 잡습니다.
    """
    buf = p.read_bytes()
    if buf[:2] == b"\xff\xfe":
        print("! %s 가 UTF-16LE 입니다 — 디코딩해서 읽습니다." % p, file=sys.stderr)
        print("  (PowerShell 5.1 의 `>` 가 만든 파일입니다. collect.py 를 쓰면 생기지 않습니다)",
              file=sys.stderr)
        return buf[2:].decode("utf-16-le", "replace")
    if buf[:2] == b"\xfe\xff":
        print("! %s 가 UTF-16BE 입니다 — 디코딩해서 읽습니다." % p, file=sys.stderr)
        return buf[2:].decode("utf-16-be", "replace")
    head = buf[:2048]
    if len(head) > 8 and head.count(0) > len(head) / 4:
        print("! %s 에 NUL 바이트가 많습니다 — UTF-16 을 UTF-8 로 잘못 읽고 있을 수 있습니다." % p,
              file=sys.stderr)
    return buf.decode("utf-8", "replace").lstrip("\ufeff")


try:
    D = json.loads(read_text(findings_path))
except json.JSONDecodeError as e:
    die("findings.json 이 올바른 JSON 이 아닙니다: %s" % e)

# ── 어휘 ────────────────────────────────────────────────────────────────
# 이 리포트는 합격/불합격을 판정하지 않습니다. 제안이므로 **우선순위**로 부릅니다.
SEV_KO = {
    "먼저": "먼저", "다음": "다음", "참고": "참고",
    "HIGH": "먼저", "MEDIUM": "다음", "LOW": "참고",
}
SEVERITIES = ["먼저", "다음", "참고"]

# 비용은 "어디부터 손댈지"를 정하는 두 번째 축입니다.
EFFORT_KO = {
    "작음": "작음", "보통": "보통", "큼": "큼",
    "S": "작음", "M": "보통", "L": "큼",
}
EFFORTS = ["작음", "보통", "큼"]

PERSPECTIVES = ["convention", "hygiene", "design", "sql"]
VERDICTS = ["CONFIRMED", "NEEDS-INFO"]

# 대상 단위의 유형. 변경 유형(08)이 아니라 **무엇인지**를 말합니다.
UNIT_KINDS = ["클래스", "메서드", "프로퍼티", "필드", "이벤트 핸들러", "XAML", "SQL"]
UNIT_KIND_KO = {
    "class": "클래스", "method": "메서드", "property": "프로퍼티",
    "field": "필드", "handler": "이벤트 핸들러", "xaml": "XAML", "sql": "SQL",
    "constructor": "메서드", "event": "이벤트 핸들러",
}
UNIT_KIND_KO.update({k: k for k in UNIT_KINDS})

FILE_KINDS = ["화면", "공통", "매퍼"]


def arr(v, name):
    if v is None:
        return []
    if not isinstance(v, list):
        bad("%s 은 배열이어야 합니다" % name)
        return []
    return v


def need(obj, key, where):
    if obj.get(key) in (None, ""):
        bad('%s: 필수 항목 "%s" 이 없습니다' % (where, key))
        return False
    return True


def one_of(obj, key, options, where):
    if key in obj and obj[key] is not None and obj[key] not in options:
        bad('%s: "%s" 는 %s 중 하나여야 합니다 (받은 값: %s)'
            % (where, key, " | ".join(options), obj[key]))


# ── meta ────────────────────────────────────────────────────────────────
if not isinstance(D.get("meta"), dict):
    bad("meta 가 없습니다")
    D["meta"] = {}
for k in ("target", "slug", "title", "generatedAt"):
    need(D["meta"], k, "meta")

for key in ("files", "units", "findings", "quickWins", "sql", "rejected", "unknowns"):
    D[key] = arr(D.get(key), key)

if not D["files"]:
    bad("files 가 비어 있습니다 — 분석한 파일이 하나는 있어야 합니다")

# ── overview (이 코드가 하는 일) ────────────────────────────────────────
ov = D.get("overview")
if not isinstance(ov, dict):
    bad("overview 가 없습니다 — 이 코드가 무엇을 하는지와 규모를 3~5줄로 적으세요 "
        "(code-scoper 의 1-scope.md 「이 코드가 하는 일」 절)")
    D["overview"] = ov = {}
need(ov, "narrative", "overview")
ov["highlights"] = arr(ov.get("highlights"), "overview.highlights")

# ── roadmap (개선 로드맵) ───────────────────────────────────────────────
rm = D.get("roadmap")
if not isinstance(rm, dict):
    bad("roadmap 이 없습니다 — 어디부터 손댈지 순서를 적으세요 "
        "(refactor-lead 의 3-roadmap.md)")
    D["roadmap"] = rm = {}
need(rm, "diagnosis", "roadmap")
for k in ("order", "batches", "leaveAlone"):
    rm[k] = arr(rm.get(k), "roadmap.%s" % k)
if not rm["leaveAlone"]:
    # 「지금은 두는 게 나은 것」이 비면 리포트가 "전부 고치라"는 문서로 읽힙니다.
    print("! roadmap.leaveAlone 이 비어 있습니다 — 손대지 않는 편이 나은 것을 "
          "한 줄이라도 적으면 리포트의 신뢰가 올라갑니다.", file=sys.stderr)

# ── files ───────────────────────────────────────────────────────────────
XAML_EXT = (".xaml", ".axaml", ".xml", ".config", ".csproj", ".props", ".targets", ".resx")


def lang_of(path=""):
    """파일 확장자로 하이라이트 언어를 정합니다.
    HTML 쪽 하이라이터는 'cs' · 'sql' · 'xaml' 만 알고, 그 외는 색을 입히지 않습니다.
    .cs 검사가 먼저 와야 YOEDSMOV.xaml.cs 가 cs 로 남습니다 — 순서를 바꾸지 마세요."""
    low = (path or "").lower()
    if low.endswith(".cs") or low.endswith(".csx"):
        return "cs"
    if low.endswith(".sql"):
        return "sql"
    if low.endswith(XAML_EXT):
        return "xaml"
    return "text"


file_paths = set()
for i, f in enumerate(D["files"]):
    w = "files[%d]" % i
    need(f, "path", w)
    if f.get("kind") is None:
        low = (f.get("path") or "").lower()
        f["kind"] = ("매퍼" if low.endswith(".xml") and "mapper" in low
                     else "화면" if low.endswith((".xaml", ".xaml.cs"))
                     else "공통")
    one_of(f, "kind", FILE_KINDS, w)
    if f.get("priority") is None:
        # 화면 파일(.xaml)과 그 코드비하인드(.xaml.cs)는 같은 급으로 먼저 봅니다
        f["priority"] = 1 if (f.get("path") or "").lower().endswith((".xaml", ".xaml.cs")) else 2
    if f.get("path"):
        file_paths.add(f["path"])

# ── units ───────────────────────────────────────────────────────────────
unit_ids = set()
for i, u in enumerate(D["units"]):
    w = "units[%d]" % i
    for k in ("id", "file", "kind", "summary"):
        need(u, k, w)
    label = UNIT_KIND_KO.get(str(u.get("kind", "")).strip())
    if label is None:
        bad('%s: "kind" 는 %s 중 하나여야 합니다 (받은 값: %s)'
            % (w, " | ".join(UNIT_KINDS), u.get("kind")))
        u["kindLabel"] = str(u.get("kind"))
    else:
        u["kindLabel"] = label
    if u.get("id"):
        if u["id"] in unit_ids:
            bad('%s: 대상 단위 ID "%s" 가 중복됩니다' % (w, u["id"]))
        unit_ids.add(u["id"])
    if u.get("file") and u["file"] not in file_paths:
        bad('%s: file "%s" 이 files[].path 에 없습니다 (경로가 글자 그대로 같아야 합니다)'
            % (w, u["file"]))
    v = u.get("lines")
    if (not isinstance(v, list) or len(v) != 2
            or not all(isinstance(n, int) and not isinstance(n, bool) and n > 0 for n in v)):
        bad("%s: lines 는 [시작, 끝] 형태의 양의 정수 배열이어야 합니다" % w)
        u["lines"] = None
    elif v[0] > v[1]:
        bad("%s: lines 의 시작(%d)이 끝(%d)보다 큽니다" % (w, v[0], v[1]))

# ── findings ────────────────────────────────────────────────────────────
seen_ids = set()
for i, f in enumerate(D["findings"]):
    w = "findings[%d]%s" % (i, (" (%s)" % f["id"]) if f.get("id") else "")
    for k in ("id", "perspective", "severity", "effort", "unitId", "file", "line",
              "title", "problem", "basis", "suggestion"):
        need(f, k, w)
    one_of(f, "perspective", PERSPECTIVES, w)

    sev = SEV_KO.get(str(f.get("severity", "")).strip())
    if sev is None:
        bad('%s: "severity" 는 먼저 | 다음 | 참고 중 하나여야 합니다 (받은 값: %s)'
            % (w, f.get("severity")))
    else:
        f["severity"] = sev

    eff = EFFORT_KO.get(str(f.get("effort", "")).strip())
    if eff is None:
        bad('%s: "effort" 는 작음 | 보통 | 큼 중 하나여야 합니다 (받은 값: %s)'
            % (w, f.get("effort")))
    else:
        f["effort"] = eff

    if f.get("verdict") is None:
        f["verdict"] = "CONFIRMED"
    one_of(f, "verdict", VERDICTS, w)
    if f.get("verdict") == "REJECTED":
        bad("%s: REJECTED 는 findings 가 아니라 rejected 에 넣으세요" % w)
    if f.get("id"):
        if f["id"] in seen_ids:
            bad("%s: 제안 ID 가 중복됩니다" % w)
        seen_ids.add(f["id"])
    if f.get("unitId") and f["unitId"] not in unit_ids:
        bad('%s: unitId "%s" 가 units 에 없습니다' % (w, f["unitId"]))
    if f.get("file") and f["file"] not in file_paths:
        bad('%s: file "%s" 이 files[].path 에 없습니다' % (w, f["file"]))
    if f.get("line") is not None and not (isinstance(f["line"], int)
                                          and not isinstance(f["line"], bool)):
        bad("%s: line 은 정수여야 합니다" % w)

# ── sql ─────────────────────────────────────────────────────────────────
for i, s in enumerate(D["sql"]):
    w = "sql[%d]" % i
    for k in ("id", "callType", "body"):
        need(s, k, w)
    one_of(s, "callType", ["DPICALL", "SQLEXEC", "MAPPER"], w)
    if s.get("callType") in ("DPICALL", "MAPPER"):
        need(s, "sqlId", w)
    s["tuningPoints"] = arr(s.get("tuningPoints"), "%s.tuningPoints" % w)
    if s.get("unitId") and s["unitId"] not in unit_ids:
        bad('%s: unitId "%s" 가 units 에 없습니다' % (w, s["unitId"]))

for i, r in enumerate(D["rejected"]):
    w = "rejected[%d]" % i
    for k in ("id", "title", "reason"):
        need(r, k, w)

for i, q in enumerate(D["quickWins"]):
    w = "quickWins[%d]" % i
    for k in ("unitId", "content"):
        need(q, k, w)
    if q.get("unitId") and q["unitId"] not in unit_ids:
        bad('%s: unitId "%s" 가 units 에 없습니다' % (w, q["unitId"]))

if problems:
    print("✗ findings.json 검증 실패 — %d건\n" % len(problems), file=sys.stderr)
    for p in problems:
        print("  · " + p, file=sys.stderr)
    print("\n스키마: .opencode/skills/refactor-oi-scan/references/html-report.md",
          file=sys.stderr)
    print("HTML 을 손으로 고치지 말고 JSON 을 고쳐 다시 실행하세요.", file=sys.stderr)
    raise SystemExit(1)

lang_by_file = {f["path"]: lang_of(f["path"]) for f in D["files"]}
for f in D["findings"]:
    f["lang"] = lang_by_file.get(f["file"], "text")


# ── 원문 읽기 ───────────────────────────────────────────────────────────
def read_source(rel_path):
    if not rel_path:
        return None
    p = (WS / rel_path)
    if not p.exists():
        return None
    lines = read_text(p).replace("\r\n", "\n").split("\n")
    # 파일 끝 개행 때문에 생기는 빈 줄은 실제 코드 줄이 아닙니다.
    if lines and lines[-1] == "":
        lines.pop()
    return lines


sources = {}
missing = []
for f in D["files"]:
    rel = f.get("sourceFile") or ("src/" + f["path"])
    f["sourceFile"] = rel
    src = read_source(rel)
    if src is None:
        missing.append(rel)
    sources[f["path"]] = src

for m in missing:
    print("! 원문 없음: %s" % m, file=sys.stderr)


# ── 코드 행 만들기 ──────────────────────────────────────────────────────
# 08 과 달리 diff 가 없습니다. 원문을 그대로 싣고, 제안이 가리키는 줄만 표시합니다.
def rows_from_source(path, frm, to):
    src = sources.get(path)
    if not src:
        return []
    frm = max(1, frm)
    end = min(to, len(src))
    return [{"no": n, "text": src[n - 1]} for n in range(frm, end + 1)]


units_with_code = 0
for u in D["units"]:
    u["lang"] = lang_by_file.get(u["file"], "text")
    rows = rows_from_source(u["file"], u["lines"][0], u["lines"][1]) if u.get("lines") else []
    u["rows"] = rows
    if rows:
        units_with_code += 1

# 파일 원문 임베드 (접이식)
for f in D["files"]:
    f["lang"] = lang_of(f["path"])
    src = sources.get(f["path"])
    f["lines"] = [{"no": i + 1, "text": t} for i, t in enumerate(src)] if src else []


# ── 기계가 센 것 — LLM 을 거치지 않습니다 ───────────────────────────────
index_summary = None
if index_path.exists():
    try:
        ix = json.loads(read_text(index_path))
        st = ix.get("stats", {})
        sq = ix.get("sql", {})
        unref = ix.get("unreferenced", [])
        index_summary = {
            "symbols": st.get("symbols", 0),
            "files": st.get("files", 0),
            "lines": st.get("lines", 0),
            "unreferenced": len(unref),
            "unreferencedHigh": sum(1 for u in unref if u.get("confidence") == "높음"),
            "duplicatePairs": len(ix.get("duplicateCandidates", [])),
            "xamlRepeats": len(ix.get("xamlRepeats", [])),
            "sqlDefined": st.get("sqlDefined", 0),
            "sqlUnused": len(sq.get("unusedIds", [])),
            "sqlMissing": len(sq.get("missingIds", [])),
            "inlineSql": len(sq.get("inline", [])),
        }
    except (json.JSONDecodeError, OSError) as e:
        print("! 1-index.json 을 읽지 못했습니다 (%s) — 「기계가 센 것」 절을 비웁니다." % e,
              file=sys.stderr)
else:
    print("! 1-index.json 이 없습니다 (%s) — 「기계가 센 것」 절을 비웁니다." % index_path,
          file=sys.stderr)
D["indexSummary"] = index_summary


# ── 렌더 ────────────────────────────────────────────────────────────────
def html_escape(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# JSON 안의 <, >, & 를 이스케이프해 </script> 로 태그가 닫히는 것을 막습니다.
payload = (json.dumps(D, ensure_ascii=False, separators=(",", ":"))
           .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
           .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))

title = "리팩토링 제안 · %s" % D["meta"]["title"]

html = (read_text(TEMPLATE)
        .replace("__TITLE__", html_escape(title), 1)
        .replace("__PAYLOAD__", payload, 1))

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(html, encoding="utf-8", newline="")

# ── 보고 ────────────────────────────────────────────────────────────────
by_sev = " · ".join("%s %d" % (s, sum(1 for f in D["findings"] if f["severity"] == s))
                    for s in SEVERITIES)
by_eff = " · ".join("%s %d" % (e, sum(1 for f in D["findings"] if f["effort"] == e))
                    for e in EFFORTS)
now = sum(1 for f in D["findings"] if f["severity"] == "먼저" and f["effort"] == "작음")
kb = round(len(html.encode("utf-8")) / 1024)

print("✓ %s" % out_path)
print("  제안 %d건 (%s)" % (len(D["findings"]), by_sev))
print("  비용 (%s)" % by_eff)
print("  즉시 착수 후보 (먼저 · 작음) %d건" % now)
print("  파일 %d · 대상 단위 %d (코드 표시 %d) · SQL %d · 반려 %d"
      % (len(D["files"]), len(D["units"]), units_with_code, len(D["sql"]), len(D["rejected"])))
print("  %d KB · 외부 요청 없음" % kb)
if units_with_code < len(D["units"]):
    print("  ! 대상 단위 %d개는 코드를 표시하지 못했습니다 "
          "— src/ 원문과 라인 범위를 확인하세요." % (len(D["units"]) - units_with_code))
if index_summary is None:
    print("  ! 「기계가 센 것」 절이 비었습니다 — 1-index.json 경로를 확인하세요.")
