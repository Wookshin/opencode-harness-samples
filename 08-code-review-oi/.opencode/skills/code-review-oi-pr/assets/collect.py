#!/usr/bin/env python3
"""collect.py — PR 변경분과 원문을 작업 폴더로 수집합니다 (Phase 1 의 기계적인 부분)

    python collect.py --pr 1234 --ws _workspace/pr-1234
    python collect.py --pr sample --ws _workspace/pr-sample \
                      --patch <스킬>/sample/pr-sample.patch \
                      --after  <스킬>/sample/after \
                      --before <스킬>/sample/before
      (<스킬> = .opencode/skills/code-review-oi-pr)

왜 스크립트인가:
    셸마다 문법이 다릅니다. `mkdir -p`, `$(dirname …)`, `$(date …)` 는 PowerShell 에 없고,
    무엇보다 `>` 리디렉션의 기본 인코딩이 셸·버전마다 다릅니다
    (Windows PowerShell 5.1 은 UTF-16LE — 오류 없이 패치와 원문이 통째로 깨집니다).
    그래서 gh/git 을 여기서 직접 부르고 출력을 **바이트 그대로** 파일에 씁니다.
    PowerShell 이든 bash 든 결과가 같습니다.

표준 라이브러리만 씁니다. pip 설치 불필요. Python 3.8 이상.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

if sys.version_info < (3, 8):
    sys.exit(f"✗ Python 3.8 이상이 필요합니다 (현재 {sys.version.split()[0]})")

# 한글 Windows 콘솔(cp949)에서 기호가 깨지지 않게 출력 스트림을 UTF-8 로 고정합니다.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def die(msg):
    print("✗ " + msg, file=sys.stderr)
    raise SystemExit(1)


# ── 인자 ────────────────────────────────────────────────────────────────
ap = argparse.ArgumentParser(description="PR 변경분과 원문을 작업 폴더로 수집")
ap.add_argument("--pr", required=True, help="PR 번호. 오프라인 데모면 sample 같은 이름")
ap.add_argument("--ws", required=True, help="작업 폴더 (예: _workspace/pr-1234)")
ap.add_argument("--resume", action="store_true", help="기존 폴더를 밀어내지 않고 이어서 씁니다")
ap.add_argument("--patch", help="오프라인 모드: 쓸 패치 파일")
ap.add_argument("--after", help="오프라인 모드: 변경 후 원문 폴더")
ap.add_argument("--before", help="오프라인 모드: 변경 전 원문 폴더")
ap.add_argument("--title")
ap.add_argument("--author")
ap.add_argument("--base")
ap.add_argument("--head")
args = ap.parse_args()

PR = str(args.pr)
WS = Path(args.ws).resolve()
OFFLINE = bool(args.patch)


# ── 실행 도우미 — 출력은 바이트로 받습니다 ──────────────────────────────
def run(cmd, allow_fail=False):
    try:
        r = subprocess.run(cmd, capture_output=True)
    except FileNotFoundError:
        if allow_fail:
            return None
        die(f"명령을 찾을 수 없습니다: {cmd[0]}\n  설치돼 있고 PATH 에 있는지 확인하세요.")
    if r.returncode != 0:
        if allow_fail:
            return None
        err = r.stderr.decode("utf-8", "replace").strip()
        die(f"명령 실패: {' '.join(cmd)}\n  {err}")
    return r.stdout


def text(buf):
    """BOM 을 벗겨 UTF-8 로 읽습니다."""
    if buf is None:
        return ""
    if buf[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return buf.decode("utf-16", "replace")
    return buf.decode("utf-8", "replace").lstrip("﻿")


def write_out(rel_path, data):
    p = WS / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        p.write_bytes(data)                                    # 받은 바이트 그대로
    else:
        p.write_text(data, encoding="utf-8", newline="")       # 항상 UTF-8, BOM 없음
    return p


# ── 작업 폴더 준비 ──────────────────────────────────────────────────────
archived = None
if WS.exists() and any(WS.iterdir()):
    if args.resume:
        print(f"· 기존 작업 폴더에 이어서 씁니다: {args.ws}")
    else:
        archived = WS.with_name(WS.name + ".prev-" + datetime.now().strftime("%Y%m%d-%H%M"))
        WS.rename(archived)                                    # 지우지 않고 밀어냅니다
        print(f"· 이전 실행을 밀어냈습니다: {archived.name}")
WS.mkdir(parents=True, exist_ok=True)


# ── 패치 파싱 — 파일별 상태를 결정적으로 뽑습니다 ───────────────────────
SQL_HINT = re.compile(
    r"(AddSql|_sql\.|\.Bind\(|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|DPICALL|SQLEXEC)",
    re.IGNORECASE,
)
DIFF_GIT = re.compile(r"^diff --git (.+?) (.+)$")


def strip_prefix(p):
    return re.sub(r"^[ab]/", "", p).strip('"')


def parse_files(patch):
    out, cur = [], None
    for line in patch.splitlines():
        g = DIFF_GIT.match(line)
        if g:
            if cur:
                out.append(cur)
            cur = {"path": strip_prefix(g.group(2)), "oldPath": strip_prefix(g.group(1)),
                   "status": "modified", "additions": 0, "deletions": 0,
                   "hunks": 0, "hasSql": False}
            continue
        if cur is None:
            continue
        if line.startswith("new file mode"):
            cur["status"] = "added"
        elif line.startswith("deleted file mode"):
            cur["status"] = "deleted"
        elif line.startswith("rename from") or line.startswith("rename to"):
            same_dir = os.path.dirname(cur["oldPath"]) == os.path.dirname(cur["path"])
            cur["status"] = "renamed" if same_dir else "moved"
        elif line.startswith("@@"):
            cur["hunks"] += 1
        elif line.startswith("+") and not line.startswith("+++"):
            cur["additions"] += 1
            cur["hasSql"] = cur["hasSql"] or bool(SQL_HINT.search(line))
        elif line.startswith("-") and not line.startswith("---"):
            cur["deletions"] += 1
            cur["hasSql"] = cur["hasSql"] or bool(SQL_HINT.search(line))
    if cur:
        out.append(cur)

    for f in out:
        f["oldPath"] = None if f["oldPath"] == f["path"] else f["oldPath"]
        f["priority"] = 1 if f["path"].lower().endswith(".xaml.cs") else 2
    return out


# ── 수집 ────────────────────────────────────────────────────────────────
if OFFLINE:
    # 오프라인 데모 — gh 도 네트워크도 쓰지 않습니다
    patch_path = Path(args.patch)
    if not patch_path.exists():
        die(f"패치를 찾을 수 없습니다: {args.patch}")
    patch_bytes = patch_path.read_bytes()
    write_out("1-diff.patch", patch_bytes)
    files = parse_files(text(patch_bytes))

    for side, src_dir in (("after", args.after), ("before", args.before)):
        if not src_dir:
            continue
        if not Path(src_dir).exists():
            print(f"! 원문 폴더 없음: {src_dir}")
            continue
        shutil.copytree(src_dir, WS / "src" / side, dirs_exist_ok=True)

    meta = {
        "prNumber": PR, "title": args.title or "오프라인 데모 (sample)",
        "author": args.author or "", "url": "",
        "baseRef": args.base or "develop", "headRef": args.head or "feature/sample",
        "headSha": "", "mode": "offline",
    }
else:
    # 실제 PR — 체크아웃하지 않습니다
    run(["git", "rev-parse", "--git-dir"])

    view = json.loads(text(run([
        "gh", "pr", "view", PR, "--json",
        "number,title,author,url,baseRefName,headRefName,headRefOid",
    ])))
    base = view["baseRefName"]

    patch_bytes = run(["gh", "pr", "diff", PR])
    write_out("1-diff.patch", patch_bytes)
    files = parse_files(text(patch_bytes))

    print("· 원격 참조를 가져옵니다 (체크아웃하지 않습니다)…")
    run(["git", "fetch", "origin", f"pull/{PR}/head:refs/remotes/pr/{PR}", "--force"])
    run(["git", "fetch", "origin", base], allow_fail=True)

    ok_after = ok_before = 0
    missed = []
    for f in files:
        if f["status"] != "deleted":
            buf = run(["git", "show", "refs/remotes/pr/%s:%s" % (PR, f["path"])], allow_fail=True)
            if buf is not None:
                write_out(str(Path("src/after") / f["path"]), buf)
                ok_after += 1
            else:
                missed.append("src/after/" + f["path"])
        if f["status"] != "added":
            src = f["oldPath"] or f["path"]
            buf = run(["git", "show", "origin/%s:%s" % (base, src)], allow_fail=True)
            if buf is not None:
                write_out(str(Path("src/before") / f["path"]), buf)
                ok_before += 1
            else:
                missed.append("src/before/" + f["path"])
    if missed:
        print(f"! 원문을 못 받은 것 {len(missed)}건:\n  " + "\n  ".join(missed))

    meta = {
        "prNumber": str(view["number"]), "title": view["title"],
        "author": (view.get("author") or {}).get("login", ""),
        "url": view["url"], "baseRef": base, "headRef": view["headRefName"],
        "headSha": view["headRefOid"], "mode": "gh",
        "sources": {"after": ok_after, "before": ok_before, "missing": missed},
    }

meta["generatedAt"] = datetime.now().astimezone().replace(microsecond=0).isoformat()
meta["workspace"] = args.ws
if archived:
    meta["archivedPrevious"] = archived.name

write_out("1-meta.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
write_out("1-files.json", json.dumps(files, ensure_ascii=False, indent=2) + "\n")


# ── 보고 ────────────────────────────────────────────────────────────────
by_status = {}
for f in files:
    by_status[f["status"]] = by_status.get(f["status"], 0) + 1

sha = meta.get("headSha") or ""
print(f"\n✓ 수집 완료 — {args.ws}")
print("  PR #%s «%s»" % (meta["prNumber"], meta["title"]))
print("  %s ← %s%s" % (meta["baseRef"], meta["headRef"], (" (%s)" % sha[:7]) if sha else ""))
print(f"  파일 {len(files)}개 — " + " · ".join("%s %d" % kv for kv in by_status.items()))
print("  SQL 변경 %d개 · 우선순위 1 %d개"
      % (sum(1 for f in files if f["hasSql"]), sum(1 for f in files if f["priority"] == 1)))
print("\n  파일 목록 (1-files.json 에 같은 내용이 있습니다)")
for f in sorted(files, key=lambda x: (x["priority"], x["path"])):
    print("  %s %-8s %s헝크 %2d +%d/-%d  %s%s" % (
        "★" if f["priority"] == 1 else " ", f["status"],
        "SQL " if f["hasSql"] else "    ",
        f["hunks"], f["additions"], f["deletions"], f["path"],
        ("  ← " + f["oldPath"]) if f["oldPath"] else ""))
print("\n  다음: 1-scope.md 와 1-hunks.md 를 작성하세요.")
