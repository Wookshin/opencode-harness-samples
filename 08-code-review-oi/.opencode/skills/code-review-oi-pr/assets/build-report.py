#!/usr/bin/env python3
"""build-report.py — findings.json → 팀 오프라인 리뷰용 단일 HTML

    python build-report.py <findings.json> <out.html> [diff.patch]

이 스크립트가 존재하는 이유:
    변경 전/후 코드와 라인 색칠을 LLM 이 옮겨 적지 않게 하려고.
    코드는 patch 와 src/{before,after}/ 원문에서 여기가 직접 계산합니다.

표준 라이브러리만 씁니다. pip 설치 불필요. Python 3.8 이상.
"""
import json
import re
import sys
from pathlib import Path

if sys.version_info < (3, 8):
    sys.exit(f"✗ Python 3.8 이상이 필요합니다 (현재 {sys.version.split()[0]})")

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
    die("사용법: python build-report.py <findings.json> <out.html> [diff.patch]")

findings_path = Path(argv[0]).resolve()
out_path = Path(argv[1]).resolve()
if not findings_path.exists():
    die(f"findings.json 을 찾을 수 없습니다: {findings_path}")
if not TEMPLATE.exists():
    die(f"템플릿을 찾을 수 없습니다: {TEMPLATE}")

WS = findings_path.parent                       # _workspace 기준 폴더
patch_path = Path(argv[2]).resolve() if len(argv) > 2 else WS / "1-diff.patch"


def read_text(p: Path) -> str:
    """텍스트 파일을 인코딩을 가려 읽습니다.

    셸 리디렉션(`>`)의 기본 인코딩은 셸·버전마다 다릅니다. Windows PowerShell 5.1 은
    UTF-16LE 로 씁니다. 그대로 UTF-8 로 읽으면 **오류 없이** 패치가 통째로 안 읽히고,
    diff 색칠만 조용히 사라집니다. 그 사고를 여기서 잡습니다.
    """
    buf = p.read_bytes()
    if buf[:2] == b"\xff\xfe":
        print(f"! {p} 가 UTF-16LE 입니다 — 디코딩해서 읽습니다.", file=sys.stderr)
        print("  (PowerShell 5.1 의 `>` 가 만든 파일입니다. collect.py 를 쓰면 생기지 않습니다)",
              file=sys.stderr)
        return buf[2:].decode("utf-16-le", "replace")
    if buf[:2] == b"\xfe\xff":
        print(f"! {p} 가 UTF-16BE 입니다 — 디코딩해서 읽습니다.", file=sys.stderr)
        return buf[2:].decode("utf-16-be", "replace")
    head = buf[:2048]
    if len(head) > 8 and head.count(0) > len(head) / 4:
        print(f"! {p} 에 NUL 바이트가 많습니다 — UTF-16 을 UTF-8 로 잘못 읽고 있을 수 있습니다.",
              file=sys.stderr)
    return buf.decode("utf-8", "replace").lstrip("\ufeff")


try:
    D = json.loads(read_text(findings_path))
except json.JSONDecodeError as e:
    die(f"findings.json 이 올바른 JSON 이 아닙니다: {e}")

# ── 스키마 검증 ─────────────────────────────────────────────────────────
SEVERITIES = ["BLOCKER", "MAJOR", "MINOR"]
PERSPECTIVES = ["refactor", "feature", "sql"]
# 변경 유형은 KIND_KO 로 정규화합니다 (영문·한글 모두 허용)
VERDICTS = ["CONFIRMED", "NEEDS-INFO"]


def arr(v, name):
    if v is None:
        return []
    if not isinstance(v, list):
        bad(f"{name} 은 배열이어야 합니다")
        return []
    return v


def need(obj, key, where):
    if obj.get(key) in (None, ""):
        bad(f'{where}: 필수 항목 "{key}" 이 없습니다')
        return False
    return True


def one_of(obj, key, options, where):
    if key in obj and obj[key] is not None and obj[key] not in options:
        bad(f'{where}: "{key}" 는 {" | ".join(options)} 중 하나여야 합니다 (받은 값: {obj[key]})')


if not isinstance(D.get("meta"), dict):
    bad("meta 가 없습니다")
    D["meta"] = {}
for k in ("prNumber", "title", "baseRef", "generatedAt", "verdict"):
    need(D["meta"], k, "meta")
one_of(D["meta"], "verdict", ["PASS", "FAIL"], "meta")

for key in ("files", "units", "findings", "simpleChanges", "sql", "rejected", "unknowns"):
    D[key] = arr(D.get(key), key)

if not D["files"]:
    bad("files 가 비어 있습니다 — 변경된 파일이 하나는 있어야 합니다")

# ── 변경 유형 어휘 통일 ─────────────────────────────────────────────
# collect.py 는 git 어휘(영문)로, diff-scoper 는 한글로 씁니다.
# 리포트 표시는 한글 5종으로 고정하고, 정규화는 여기 한 곳에서만 합니다.
KIND_KO = {
    "added": "신규", "modified": "변경", "deleted": "삭제",
    "renamed": "이름변경", "moved": "이동",
    "신규": "신규", "변경": "변경", "삭제": "삭제", "이름변경": "이름변경", "이동": "이동",
}


def kind_label(v, where, field):
    """영문·한글 어느 쪽으로 들어와도 한글 라벨로 돌려줍니다."""
    if not v:
        return ""
    label = KIND_KO.get(str(v).strip())
    if label is None:
        bad(f'{where}: "{field}" 는 신규 | 변경 | 삭제 | 이름변경 | 이동 '
            f"(또는 added/modified/deleted/renamed/moved) 중 하나여야 합니다 (받은 값: {v})")
        return str(v)
    return label


# ── 개요 (전체 변경사항 요약) ───────────────────────────────────────
ov = D.get("overview")
if not isinstance(ov, dict):
    bad("overview 가 없습니다 — 이 PR 이 무엇을 하는지 3~5줄로 적으세요 "
        "(diff-scoper 의 1-scope.md 「이 PR 이 하는 일」 절)")
    D["overview"] = ov = {}
need(ov, "narrative", "overview")
ov["highlights"] = arr(ov.get("highlights"), "overview.highlights")

# ── 종합 평가 ───────────────────────────────────────────────────────
asm = D.get("assessment")
if not isinstance(asm, dict):
    bad("assessment 가 없습니다 — 최종 의견과 재확인 필요사항을 적으세요 "
        "(review-lead 의 3-assessment.md)")
    D["assessment"] = asm = {}
need(asm, "conclusion", "assessment")
for k in ("rechecks", "agenda", "goodPoints"):
    asm[k] = arr(asm.get(k), f"assessment.{k}")


def lang_of(path=""):
    """파일 확장자로 하이라이트 언어를 정합니다.
    HTML 쪽 하이라이터는 'cs' 와 'sql' 만 알고, 그 외는 색을 입히지 않습니다."""
    low = (path or "").lower()
    if low.endswith(".cs") or low.endswith(".csx"):
        return "cs"
    if low.endswith(".sql"):
        return "sql"
    return "text"


file_paths = set()
for i, f in enumerate(D["files"]):
    w = f"files[{i}]"
    need(f, "path", w)
    need(f, "changeType", w)
    f["kindLabel"] = kind_label(f.get("changeType"), w, "changeType")
    if f.get("priority") is None:
        f["priority"] = 1 if (f.get("path") or "").lower().endswith(".xaml.cs") else 2
    if f.get("path"):
        file_paths.add(f["path"])

unit_ids = set()
for i, u in enumerate(D["units"]):
    w = f"units[{i}]"
    for k in ("id", "file", "kind", "summary"):
        need(u, k, w)
    u["kindLabel"] = kind_label(u.get("kind"), w, "kind")
    if u.get("id"):
        if u["id"] in unit_ids:
            bad(f'{w}: 변경단위 ID "{u["id"]}" 가 중복됩니다')
        unit_ids.add(u["id"])
    if u.get("file") and u["file"] not in file_paths:
        bad(f'{w}: file "{u["file"]}" 이 files[].path 에 없습니다 (경로가 글자 그대로 같아야 합니다)')
    for k in ("afterLines", "beforeLines"):
        v = u.get(k)
        if v is None:
            u[k] = None
            continue
        if (not isinstance(v, list) or len(v) != 2
                or not all(isinstance(n, int) and not isinstance(n, bool) and n > 0 for n in v)):
            bad(f"{w}: {k} 는 [시작, 끝] 형태의 양의 정수 배열이어야 합니다")
            u[k] = None
        elif v[0] > v[1]:
            bad(f"{w}: {k} 의 시작({v[0]})이 끝({v[1]})보다 큽니다")
    if not u.get("afterLines") and not u.get("beforeLines"):
        bad(f"{w}: afterLines 와 beforeLines 가 모두 없습니다 — 하나는 있어야 코드를 보여줄 수 있습니다")

seen_ids = set()
for i, f in enumerate(D["findings"]):
    w = f"findings[{i}]" + (f' ({f["id"]})' if f.get("id") else "")
    for k in ("id", "perspective", "severity", "unitId", "file", "line",
              "title", "problem", "basis", "suggestion"):
        need(f, k, w)
    one_of(f, "perspective", PERSPECTIVES, w)
    one_of(f, "severity", SEVERITIES, w)
    if f.get("verdict") is None:
        f["verdict"] = "CONFIRMED"
    one_of(f, "verdict", VERDICTS, w)
    if f.get("verdict") == "REJECTED":
        bad(f"{w}: REJECTED 는 findings 가 아니라 rejected 에 넣으세요")
    if f.get("id"):
        if f["id"] in seen_ids:
            bad(f"{w}: 지적 ID 가 중복됩니다")
        seen_ids.add(f["id"])
    if f.get("unitId") and f["unitId"] not in unit_ids:
        bad(f'{w}: unitId "{f["unitId"]}" 가 units 에 없습니다')
    if f.get("file") and f["file"] not in file_paths:
        bad(f'{w}: file "{f["file"]}" 이 files[].path 에 없습니다')
    if f.get("line") is not None and not (isinstance(f["line"], int) and not isinstance(f["line"], bool)):
        bad(f"{w}: line 은 정수여야 합니다")

for i, a in enumerate(D["assessment"]["agenda"]):
    if a not in seen_ids:
        bad(f'assessment.agenda[{i}]: "{a}" 가 findings[].id 에 없습니다')

for i, s in enumerate(D["sql"]):
    w = f"sql[{i}]"
    for k in ("id", "callType", "body"):
        need(s, k, w)
    one_of(s, "callType", ["DPICALL", "SQLEXEC"], w)
    if s.get("callType") == "DPICALL":
        need(s, "sqlId", w)
    s["tuningPoints"] = arr(s.get("tuningPoints"), f"{w}.tuningPoints")
    if s.get("unitId") and s["unitId"] not in unit_ids:
        bad(f'{w}: unitId "{s["unitId"]}" 가 units 에 없습니다')

for i, r in enumerate(D["rejected"]):
    w = f"rejected[{i}]"
    for k in ("id", "title", "reason"):
        need(r, k, w)

if problems:
    print(f"✗ findings.json 검증 실패 — {len(problems)}건\n", file=sys.stderr)
    for p in problems:
        print("  · " + p, file=sys.stderr)
    print("\n스키마: .opencode/skills/code-review-oi-pr/references/html-report.md", file=sys.stderr)
    print("HTML 을 손으로 고치지 말고 JSON 을 고쳐 다시 실행하세요.", file=sys.stderr)
    raise SystemExit(1)

# 지적 조각에도 파일 언어를 붙입니다 (HTML 이 files 를 되짚지 않도록)
lang_by_file = {f["path"]: lang_of(f["path"]) for f in D["files"]}
for f in D["findings"]:
    f["lang"] = lang_by_file.get(f["file"], "text")


# ── 패치 파싱 ───────────────────────────────────────────────────────────
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
SKIP_PREFIX = ("--- ", "index ", "new file", "deleted file", "similarity ",
               "rename ", "old mode", "new mode", "Binary files")


def parse_patch(text):
    """파일별로 두 가지를 뽑습니다.
      added     : after 기준으로 추가된 라인 번호 집합
      deletions : "after 몇 번째 줄 앞에 지워진 줄이 있었나" 를 앵커로 잡은 맵
    이 둘만 있으면 after 원문 위에 diff 를 정확히 얹을 수 있습니다."""
    by_path = {}
    cur = None
    a = b = 0

    def start(path):
        return by_path.setdefault(path, {"added": set(), "deletions": {}})

    def strip(p):
        return re.sub(r"^[ab]/", "", p).strip('"')

    if not text:
        return by_path

    for raw in text.splitlines():
        g = re.match(r"^diff --git (.+?) (.+)$", raw)
        if g:
            cur = start(strip(g.group(2)))
            continue
        if raw.startswith("+++ "):
            p = raw[4:].strip()
            if p != "/dev/null":
                cur = start(strip(p))
            continue
        if raw.startswith(SKIP_PREFIX):
            continue
        h = HUNK.match(raw)
        if h:
            a, b = int(h.group(1)), int(h.group(3))
            continue
        if cur is None or not raw:
            continue
        op = raw[0]
        if op == "+":
            cur["added"].add(b)
            b += 1
        elif op == "-":
            cur["deletions"].setdefault(b, []).append({"text": raw[1:], "beforeNo": a})
            a += 1
        elif op == " ":
            a += 1
            b += 1
    return by_path


patch_text = read_text(patch_path) if patch_path.exists() else ""
if not patch_text:
    print(f"! 패치를 찾지 못했습니다 ({patch_path}) — 추가/삭제 색칠 없이 원문만 표시합니다.",
          file=sys.stderr)
patch = parse_patch(patch_text)


# ── 원문 읽기 ───────────────────────────────────────────────────────────
def read_source(rel_path):
    if not rel_path:
        return None
    p = (WS / rel_path).resolve()
    if not p.exists():
        return None
    lines = read_text(p).replace("\r\n", "\n").split("\n")
    # 파일 끝 개행 때문에 생기는 빈 줄은 실제 코드 줄이 아닙니다.
    if lines and lines[-1] == "":
        lines.pop()
    return lines


sources = {}
for f in D["files"]:
    after = read_source(f.get("afterFile"))
    before = read_source(f.get("beforeFile"))
    if f.get("afterFile") and after is None:
        print(f'! 원문 없음: {f["afterFile"]}', file=sys.stderr)
    if f.get("beforeFile") and before is None:
        print(f'! 원문 없음: {f["beforeFile"]}', file=sys.stderr)
    sources[f["path"]] = {"after": after, "before": before}


# ── 코드 행 만들기 ──────────────────────────────────────────────────────
def mark_of(path):
    return patch.get(path, {"added": set(), "deletions": {}})


_before_of_cache = {}


def before_of(path, src_len):
    """after 라인번호 → before 라인번호 지도.

    '나란히 보기'에서 왼쪽(변경 전) 열의 줄 번호를 채우려면 컨텍스트 줄도 자기
    before 번호를 알아야 합니다. 추가된 줄은 before 가 없으므로 None 입니다.
    """
    if path in _before_of_cache:
        return _before_of_cache[path]
    mk = mark_of(path)
    m, a = {}, 1
    for n in range(1, src_len + 1):
        a += len(mk["deletions"].get(n, []))      # 이 줄 앞에서 지워진 만큼 before 가 먼저 소모됨
        if n in mk["added"]:
            m[n] = None
        else:
            m[n] = a
            a += 1
    _before_of_cache[path] = m
    return m


def rows_from_after(path, frm, to):
    """after 원문 [frm, to] 구간을 diff 가 얹힌 행 배열로"""
    src = (sources.get(path) or {}).get("after")
    mk = mark_of(path)
    rows = []
    if not src:
        return rows
    bmap = before_of(path, len(src))
    end = min(to, len(src))
    for n in range(frm, end + 1):
        for d in mk["deletions"].get(n, []):
            rows.append({"type": "del", "beforeNo": d["beforeNo"], "afterNo": None, "text": d["text"]})
        rows.append({"type": "add" if n in mk["added"] else "ctx",
                     "afterNo": n, "beforeNo": bmap.get(n), "text": src[n - 1]})
    # 파일 끝에서 지워진 코드는 앵커가 마지막 줄 다음이라 위 반복에 안 잡힙니다.
    # 파일 끝일 때만 붙입니다 — 중간이면 다음 변경단위가 자기 시작 줄에서 보여 줍니다.
    if end == len(src):
        for d in mk["deletions"].get(end + 1, []):
            rows.append({"type": "del", "beforeNo": d["beforeNo"], "afterNo": None, "text": d["text"]})
    return rows


def rows_from_before(path, frm, to):
    """삭제만 있는 변경단위 — before 원문 구간을 전부 del 로"""
    src = (sources.get(path) or {}).get("before")
    rows = []
    if not src:
        return rows
    for n in range(frm, min(to, len(src)) + 1):
        rows.append({"type": "del", "beforeNo": n, "afterNo": None, "text": src[n - 1]})
    return rows


def rows_from_patch_only(path, frm, to):
    """패치 hunk 만으로 행을 만든다 (원문이 없을 때의 대체 경로)"""
    mk = mark_of(path)
    rows = []
    anchors = [n for n in (set(mk["added"]) | set(mk["deletions"])) if frm <= n <= to + 1]
    if not anchors:
        return rows
    for n in range(frm, to + 1):
        for d in mk["deletions"].get(n, []):
            rows.append({"type": "del", "beforeNo": d["beforeNo"], "afterNo": None, "text": d["text"]})
        if n in mk["added"]:
            rows.append({"type": "add", "afterNo": n, "beforeNo": None, "text": "(원문 없음)"})
    return rows


units_with_code = 0
for u in D["units"]:
    u["lang"] = lang_by_file.get(u["file"], "text")
    rows = []
    if u.get("afterLines"):
        rows = rows_from_after(u["file"], u["afterLines"][0], u["afterLines"][1])
    if not rows and u.get("beforeLines"):
        rows = rows_from_before(u["file"], u["beforeLines"][0], u["beforeLines"][1])
    if not rows and u.get("afterLines"):
        rows = rows_from_patch_only(u["file"], u["afterLines"][0], u["afterLines"][1])
    u["rows"] = rows
    if rows:
        units_with_code += 1

# 파일 원문 임베드 (접이식) + 하이라이트 언어
for f in D["files"]:
    f["lang"] = lang_of(f["path"])
    src = (sources.get(f["path"]) or {}).get("after")
    if not src:
        f["lines"] = []
        continue
    mk = mark_of(f["path"])
    f["lines"] = [{"type": "add" if i + 1 in mk["added"] else "ctx",
                   "afterNo": i + 1, "beforeNo": None, "text": t}
                  for i, t in enumerate(src)]


# ── 렌더 ────────────────────────────────────────────────────────────────
def html_escape(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# JSON 안의 <, >, & 를 이스케이프해 </script> 로 태그가 닫히는 것을 막습니다.
payload = (json.dumps(D, ensure_ascii=False, separators=(",", ":"))
           .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
           .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))

title = f'코드리뷰 #{D["meta"]["prNumber"]} · {D["meta"]["title"]}'

html = (read_text(TEMPLATE)
        .replace("__TITLE__", html_escape(title), 1)
        .replace("__PAYLOAD__", payload, 1))

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(html, encoding="utf-8", newline="")

# ── 보고 ────────────────────────────────────────────────────────────────
by_sev = " · ".join(f'{s} {sum(1 for f in D["findings"] if f["severity"] == s)}' for s in SEVERITIES)
kb = round(len(html.encode("utf-8")) / 1024)
print(f"✓ {out_path}")
print(f'  판정 {D["meta"]["verdict"]} · 지적 {len(D["findings"])}건 ({by_sev})')
print(f'  파일 {len(D["files"])} · 변경단위 {len(D["units"])} (코드 표시 {units_with_code}) · '
      f'SQL {len(D["sql"])} · 반려 {len(D["rejected"])}')
print(f"  {kb} KB · 외부 요청 없음")
if units_with_code < len(D["units"]):
    print(f"  ! 변경단위 {len(D['units']) - units_with_code}개는 코드를 표시하지 못했습니다 "
          "— src/after 원문과 라인 범위를 확인하세요.")
