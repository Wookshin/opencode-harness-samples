#!/usr/bin/env python3
"""ws.py — 작업 폴더 목록과 환경 점검 (에이전트가 헤매지 않게 하는 스크립트)

    python ws.py --list      _workspace/ 의 작업 폴더와 진행 상황
    python ws.py --doctor    python·git·경로·쓰기 권한 점검
    python ws.py --selftest  샘플로 파이프라인 전체를 모델 없이 돌려 봅니다

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
    sys.exit("✗ Python 3.8 이상이 필요합니다 (현재 %s)" % sys.version.split()[0])

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SKILL = Path(".opencode/skills/refactor-oi-scan")
ASSETS = SKILL / "assets"
REFS = SKILL / "references"


def run(cmd, timeout=20):
    """명령을 돌리고 (성공?, 첫 줄) 을 돌려줍니다. 없으면 (False, '')."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or r.stderr or "").strip().splitlines()
        return r.returncode == 0, (out[0] if out else "")
    except Exception:
        return False, ""


# ── --list ──────────────────────────────────────────────────────────────
# Phase 는 산출물이 있는 데까지로 봅니다. 순서대로 확인합니다.
PHASES = [
    ("1-index.json",     "1 수집·인덱스"),
    ("1-units.md",       "1 대상 단위 확정"),
    ("2-suggest-*.md",   "2 제안"),
    ("3-verify.md",      "3 검증"),
    ("3-roadmap.md",     "3 로드맵"),
    ("4-findings.json",  "4 정리"),
    ("*.html",           "4 리포트 완료"),
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

    dirs = sorted(d for d in ws.iterdir() if d.is_dir() and d.name.startswith("scan-")
                  and ".prev-" not in d.name)
    prev = sorted(d for d in ws.iterdir() if d.is_dir() and ".prev-" in d.name)

    if not dirs:
        print("작업 폴더 없음 — 진행 중인 분석이 없습니다.")
        if prev:
            print("(밀어 둔 이전 실행 %d개: %s)" % (len(prev), ", ".join(p.name for p in prev)))
        return 0

    rows = []
    for d in dirs:
        reports = [p.name for p in d.glob("*.html")]
        rows.append((
            d.name,
            phase_of(d),
            str(len(list(d.glob("2-suggest-*.md")))),
            reports[0] if reports else "—",
            str(len([p for p in prev if p.name.startswith(d.name + ".prev-")])),
        ))

    head = ("작업 폴더", "마지막 Phase", "제안", "리포트", "이전본")

    # 한글은 폭이 2 라 len() 으로 맞추면 표가 어긋납니다.
    def wide(t):
        return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in t)

    def pad(t, n):
        return t + " " * max(0, n - wide(t))

    w = [max(wide(head[i]), max(wide(r[i]) for r in rows)) for i in range(5)]

    def line(c):
        return "  ".join(pad(c[i], w[i]) for i in range(5)).rstrip()

    print(line(head))
    print("  ".join("-" * w[i] for i in range(5)))
    for r in rows:
        print(line(r))
    print()
    print("작업 폴더 %d개. 이어서 하려면 /refactor <경로>, "
          "HTML 만 다시 만들려면 /report-only <경로>." % len(dirs))
    return 0


# ── --doctor ────────────────────────────────────────────────────────────
def doctor():
    bad = 0

    def ok(label, detail=""):
        print("  ✓ %s%s" % (label, ("  " + detail) if detail else ""))

    def no(label, *fix):
        nonlocal bad
        bad += 1
        print("  ✗ %s" % label)
        for f in fix:
            print("      → %s" % f)

    print("환경 점검")
    ok("python %s" % sys.version.split()[0], "(%s)" % sys.executable)

    good, ver = run(["git", "--version"])
    if good:
        ok(ver)
    else:
        print("  · git 이 없습니다 — 선택 항목입니다 "
              "(파일별 최종 수정일을 못 넣을 뿐, 분석은 됩니다)")

    # gh 는 쓰지 않습니다. 이 하네스는 PR 이 아니라 소스 경로를 봅니다.

    print("\n하네스 파일 (.opencode/ 는 숨김 폴더라 검색 도구에는 안 잡힙니다)")
    need = [ASSETS / "collect.py", ASSETS / "index.py",
            ASSETS / "build-report.py", ASSETS / "ws.py",
            ASSETS / "report-template.html",
            SKILL / "mapper-dir.txt",
            REFS / "suggest-format.md", REFS / "html-report.md",
            REFS / "naming-rules.md", REFS / "hygiene-rules.md",
            REFS / "design-rules.md", REFS / "read-sql.md"]
    for p in need:
        if p.is_file():
            ok(str(p))
        else:
            no("%s 가 없습니다" % p,
               ".opencode/ 를 저장소 루트에 통째로 복사했는지 확인하세요.")

    cfg = Path("opencode.jsonc")
    if cfg.is_file():
        ok("opencode.jsonc")
    else:
        no("opencode.jsonc 가 저장소 루트에 없습니다",
           "복사를 빠뜨리면 subagent_depth 가 없어 4인 동시 제안이 막힙니다.")

    mapper = SKILL / "mapper-dir.txt"
    if mapper.is_file():
        keys = [l.split(":", 1)[0].strip()
                for l in mapper.read_text(encoding="utf-8-sig").splitlines()
                if l.strip() and not l.strip().startswith("#") and ":" in l]
        print("\nmapper 매핑: %s" % (", ".join(keys) or "(비어 있음)"))
        good, top = run(["git", "rev-parse", "--show-toplevel"])
        if good:
            name = Path(top).name
            if name in keys:
                ok("현재 저장소 `%s` 매핑 있음" % name)
            else:
                print("  · 현재 저장소 `%s` 매핑이 없습니다 — "
                      "SQL 미사용 판정은 건너뜁니다" % name)
                print("      → mapper-dir.txt 에 `%s: <mapper 폴더 경로>` 를 추가하세요." % name)

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
        no("_workspace/ 에 쓸 수 없습니다 (%s)" % e, "폴더 권한을 확인하세요.")
    finally:
        if made:
            try:
                ws.rmdir()                                     # 비어 있을 때만 지워집니다
            except OSError:
                pass

    good, br = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if good:
        print("\n현재 브랜치: %s" % br)

    print()
    if bad:
        print("✗ %d건이 준비되지 않았습니다. 위의 → 를 먼저 처리하세요." % bad)
    else:
        print("✓ 전부 준비됐습니다.")
        print("  파이프라인이 실제로 도는지까지 보려면: python %s --selftest" % (ASSETS / "ws.py"))
        print("  그다음 /refactor <경로> 로 시작하세요.")
    return 1 if bad else 0


# ── --selftest ──────────────────────────────────────────────────────────
def selftest():
    """모델을 한 번도 부르지 않고 스크립트 파이프라인 전체를 돌려 봅니다.

    스킬에 딸린 샘플에는 **일부러 심어 둔 결함**과, 미참조로 오인하기 쉬운
    **WPF 함정**이 함께 들어 있습니다. 둘 다 기대대로 나오는지 확인합니다.
    """
    import json
    import tempfile

    sample = SKILL / "sample"
    expected_path = sample / "expected-index.json"
    if not sample.is_dir() or not expected_path.is_file():
        print("✗ 샘플을 찾을 수 없습니다: %s" % sample)
        print("  → .opencode/ 를 통째로 복사했는지 확인하세요.")
        return 1

    exp = json.loads(expected_path.read_text(encoding="utf-8"))
    fails = []

    def check(cond, msg):
        if cond:
            print("  ✓ %s" % msg)
        else:
            fails.append(msg)
            print("  ✗ %s" % msg)

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "scan-selftest"

        print("1. 수집")
        good, _ = run([sys.executable, str(ASSETS / "collect.py"),
                       "--path", str(sample / "src"), "--ws", str(ws),
                       "--mapper", str(sample / "mapper")], timeout=120)
        check(good and (ws / "src").is_dir(), "collect.py 가 원문을 수집했습니다")
        check((ws / "src-sql").is_dir(), "mapper 를 가져왔습니다")
        if fails:
            return report(fails)

        print("\n2. 인덱싱")
        good, _ = run([sys.executable, str(ASSETS / "index.py"), "--ws", str(ws)],
                      timeout=120)
        check(good and (ws / "1-index.json").is_file(), "index.py 가 인덱스를 만들었습니다")
        if fails:
            return report(fails)

        ix = json.loads((ws / "1-index.json").read_text(encoding="utf-8"))
        unref = {u["name"]: u["confidence"] for u in ix["unreferenced"]}

        print("\n3. 죽은 코드를 잡았나")
        for item in exp["mustBeUnreferenced"]:
            name, conf = item["name"], item["confidence"]
            check(unref.get(name) == conf,
                  "`%s` 가 미참조(확신 %s)로 잡혔습니다%s"
                  % (name, conf, "" if unref.get(name) == conf
                     else "  ← 실제: %s" % (unref.get(name) or "잡히지 않음")))

        print("\n4. WPF 함정을 피했나  ← 이 하네스의 핵심")
        for name in exp["mustNotBeUnreferenced"]:
            check(name not in unref,
                  "`%s` 를 죽은 코드로 오인하지 않았습니다%s"
                  % (name, "" if name not in unref else "  ← 오탐!"))

        print("\n5. 중복을 잡았나")
        pairs = {frozenset([d["a"]["name"], d["b"]["name"]])
                 for d in ix["duplicateCandidates"]}
        for a, b in exp["mustBeDuplicatePair"]:
            check(frozenset([a, b]) in pairs, "`%s` ↔ `%s` 가 중복 후보입니다" % (a, b))

        print("\n6. SQL 대조")
        check(sorted(ix["sql"]["unusedIds"]) == sorted(exp["sql"]["unusedIds"]),
              "미사용 SQL ID: %s" % ", ".join(ix["sql"]["unusedIds"]))
        check(sorted(ix["sql"]["missingIds"]) == sorted(exp["sql"]["missingIds"]),
              "정의 없는 SQL ID: %s" % ", ".join(ix["sql"]["missingIds"]))

        print("\n7. 리포트 렌더")
        out = ws / "selftest.html"
        # 고정 입력은 샘플 폴더 기준이라 원문은 sample/src · sample/mapper 에서 찾습니다.
        # 인덱스만 방금 만든 작업 폴더 것을 씁니다.
        good, msg = run([sys.executable, str(ASSETS / "build-report.py"),
                         str(sample / "expected-findings.json"), str(out),
                         str(ws / "1-index.json")],
                        timeout=120)
        check(good and out.is_file() and out.stat().st_size > 10000,
              "build-report.py 가 HTML 을 만들었습니다%s" % ("" if good else "  ← " + msg))
        if out.is_file():
            html = out.read_text(encoding="utf-8")
            # 본문에 실린 코드에는 URI 가 얼마든지 나옵니다 (XAML 의 xmlns 가 대표적).
            # 그건 글자일 뿐이라 요청이 아닙니다. **실제로 받아 오는 형태**만 봅니다.
            import re as _re
            fetchers = _re.findall(
                r"""<script[^>]+src\s*=\s*["']https?:|"""
                r"""<link[^>]+href\s*=\s*["']https?:|"""
                r"""<(?:img|iframe|video|audio|source|embed)[^>]+src\s*=\s*["']https?:|"""
                r"""@import\s+["']?https?:|url\(\s*["']?https?:""",
                html, _re.I)
            check(not fetchers,
                  "외부에서 받아 오는 리소스가 없습니다 (폐쇄망에서 열립니다)%s"
                  % ("" if not fetchers else "  ← %s" % fetchers[:3]))

    return report(fails)


def report(fails):
    print()
    if fails:
        print("✗ 자체 점검 %d건 실패." % len(fails))
        print("  스크립트를 고친 뒤 다시 돌리세요. 샘플 기대값은 "
              "%s 에 있습니다." % (SKILL / "sample/expected-index.json"))
        return 1
    print("✓ 자체 점검 통과 — 스크립트 파이프라인이 살아 있습니다.")
    print("  (에이전트 프롬프트는 여기서 확인되지 않습니다. "
          "모델을 부르는 /refactor-sample 로 보세요.)")
    return 0


ap = argparse.ArgumentParser(description="작업 폴더 목록과 환경 점검")
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument("--list", action="store_true", help="_workspace/ 의 작업 폴더와 진행 상황")
g.add_argument("--doctor", action="store_true", help="python·git·경로·쓰기 권한 점검")
g.add_argument("--selftest", action="store_true",
               help="샘플로 스크립트 파이프라인 전체를 모델 없이 돌려 봅니다")
a = ap.parse_args()

raise SystemExit(list_ws() if a.list else (doctor() if a.doctor else selftest()))
