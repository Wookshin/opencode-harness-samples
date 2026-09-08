#!/usr/bin/env python3
"""ws.py — 작업 폴더 목록과 환경 점검 (에이전트가 헤매지 않게 하는 스크립트)

    python ws.py --list      _workspace/ 의 작업 폴더와 진행 상황
    python ws.py --doctor    python·git·gh·경로·쓰기 권한 점검

왜 스크립트인가:
    폴더 목록을 보는 도구가 환경마다 다릅니다. `list` 도구가 없는 곳이 있고,
    `grep`·`glob` 은 기본적으로 숨김 경로(`.opencode/`)를 건너뜁니다.
    셸도 팀마다 다릅니다(PowerShell 에 `ls -la` 가 없습니다).
    그래서 에이전트가 "확인"하려 들면 있는 것도 없다고 나옵니다.
    답을 여기서 한 번에 만들어 줍니다.

    마지막 Phase 는 STATUS.md 가 아니라 **파일 존재로** 판정합니다.
    STATUS.md 가 없어도 정확하고, 사람이 폴더를 손대도 어긋나지 않습니다.

표준 라이브러리만 씁니다. pip 설치 불필요. Python 3.8 이상.
"""
import argparse
import subprocess
import unicodedata
import sys
from pathlib import Path

if sys.version_info < (3, 8):
    sys.exit(f"✗ Python 3.8 이상이 필요합니다 (현재 {sys.version.split()[0]})")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ASSETS = Path(".opencode/skills/code-review-oi-pr/assets")
REFS = Path(".opencode/skills/code-review-oi-pr/references")


def run(cmd):
    """명령을 돌리고 (성공?, 첫 줄) 을 돌려줍니다. 없으면 (False, '')."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        out = (r.stdout or r.stderr or "").strip().splitlines()
        return r.returncode == 0, (out[0] if out else "")
    except Exception:
        return False, ""


# ── --list ──────────────────────────────────────────────────────────────
# Phase 는 산출물이 있는 데까지로 봅니다. 순서대로 확인합니다.
PHASES = [
    ("1-hunks.md",   "1 수집·변경단위"),
    ("2-review-*.md", "2 리뷰"),
    ("3-verify.md",  "3 검증"),
    ("4-findings.json", "4 정리"),
    ("*.html",       "4 리포트 완료"),
]


def phase_of(d):
    done = "—"
    for pat, label in PHASES:
        if list(d.glob(pat)):
            done = label
    return done


def list_ws():
    ws = Path("_workspace")
    if not ws.is_dir():
        print("작업 폴더 없음 — _workspace/ 가 아직 없습니다.")
        print("정상입니다. collect.py 가 만듭니다. 직접 만들지 마세요.")
        return 0

    dirs = sorted(d for d in ws.iterdir() if d.is_dir() and d.name.startswith("pr-")
                  and ".prev-" not in d.name)
    prev = sorted(d for d in ws.iterdir() if d.is_dir() and ".prev-" in d.name)

    if not dirs:
        print("작업 폴더 없음 — 진행 중인 리뷰가 없습니다.")
        if prev:
            print(f"(밀어 둔 이전 실행 {len(prev)}개: " + ", ".join(p.name for p in prev) + ")")
        return 0

    rows = []
    for d in dirs:
        reports = [p.name for p in d.glob("*.html")]
        rows.append((
            d.name,
            phase_of(d),
            str(len(list(d.glob("2-review-*.md")))),
            reports[0] if reports else "—",
            str(len([p for p in prev if p.name.startswith(d.name + ".prev-")])),
        ))

    head = ("작업 폴더", "마지막 Phase", "리뷰", "리포트", "이전본")
    # 한글은 폭이 2 라 len() 으로 맞추면 표가 어긋납니다.
    def wide(t):
        return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in t)
    def pad(t, n):
        return t + " " * max(0, n - wide(t))
    w = [max(wide(head[i]), max(wide(r[i]) for r in rows)) for i in range(5)]
    line = lambda c: "  ".join(pad(c[i], w[i]) for i in range(5)).rstrip()
    print(line(head))
    print("  ".join("-" * w[i] for i in range(5)))
    for r in rows:
        print(line(r))
    print()
    print(f"작업 폴더 {len(dirs)}개. 이어서 하려면 /review-pr <번호>, "
          "HTML 만 다시 만들려면 /report-only <번호>.")
    return 0


# ── --doctor ────────────────────────────────────────────────────────────
def doctor():
    bad = 0

    def ok(label, detail=""):
        print(f"  ✓ {label}" + (f"  {detail}" if detail else ""))

    def no(label, *fix):
        nonlocal bad
        bad += 1
        print(f"  ✗ {label}")
        for f in fix:
            print(f"      → {f}")

    print("환경 점검")
    ok(f"python {sys.version.split()[0]}", f"({sys.executable})")

    good, ver = run(["git", "--version"])
    ok(ver) if good else no("git 을 찾을 수 없습니다", "git 을 설치하세요.")

    good, ver = run(["gh", "--version"])
    if not good:
        no("gh 를 찾을 수 없습니다",
           "gh 를 설치하고 `gh auth login` 을 하세요.",
           "gh 없이 지금 점검만 하려면: /review-sample")
    else:
        ok(ver)
        authed, _ = run(["gh", "auth", "status"])
        ok("gh 인증됨") if authed else no(
            "gh 인증이 안 돼 있습니다", "`gh auth login` 을 실행하세요.")

    print("\n하네스 파일 (.opencode/ 는 숨김 폴더라 검색 도구에는 안 잡힙니다)")
    need = [ASSETS / "collect.py", ASSETS / "build-report.py",
            ASSETS / "ws.py", ASSETS / "report-template.html",
            Path(".opencode/skills/code-review-oi-pr/dpimgr-dir.txt"),
            REFS / "review-format.md", REFS / "html-report.md"]
    for p in need:
        ok(str(p)) if p.is_file() else no(f"{p} 가 없습니다",
            ".opencode/ 를 저장소 루트에 통째로 복사했는지 확인하세요.")

    cfg = Path("opencode.jsonc")
    if cfg.is_file():
        ok("opencode.jsonc")
    else:
        no("opencode.jsonc 가 저장소 루트에 없습니다",
           "복사를 빠뜨리면 subagent_depth 가 없어 3인 동시 리뷰가 막힙니다.")

    print("\n쓰기")
    ws = Path("_workspace")
    made = not ws.exists()                                     # 점검이 흔적을 남기지 않게
    try:
        ws.mkdir(parents=True, exist_ok=True)
        t = ws / ".probe"
        t.write_text("ok", encoding="utf-8")
        t.unlink()
        ok("_workspace/ 에 쓸 수 있습니다")
    except Exception as e:
        no(f"_workspace/ 에 쓸 수 없습니다 ({e})", "폴더 권한을 확인하세요.")
    finally:
        if made:
            try:
                ws.rmdir()                                     # 비어 있을 때만 지워집니다
            except OSError:
                pass

    good, br = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if good:
        print(f"\n현재 브랜치: {br}")

    print()
    if bad:
        print(f"✗ {bad}건이 준비되지 않았습니다. 위의 → 를 먼저 처리하세요.")
    else:
        print("✓ 전부 준비됐습니다. /review-pr <번호> 로 시작하세요.")
    return 1 if bad else 0


ap = argparse.ArgumentParser(description="작업 폴더 목록과 환경 점검")
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument("--list", action="store_true", help="_workspace/ 의 작업 폴더와 진행 상황")
g.add_argument("--doctor", action="store_true", help="python·git·gh·경로·쓰기 권한 점검")
a = ap.parse_args()

raise SystemExit(list_ws() if a.list else doctor())
