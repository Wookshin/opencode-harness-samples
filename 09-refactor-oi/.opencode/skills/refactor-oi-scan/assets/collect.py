#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
리팩토링 대상 원문 수집기.

    python collect.py --path YOEDSMOV --ws _workspace/scan-YOEDSMOV

하는 일:
  1. 작업 폴더를 만듭니다 (이전 실행은 지우지 않고 밀어냅니다)
  2. 대상 경로의 텍스트 소스를 <WS>/src/ 로 바이트 그대로 복사합니다
  3. 수집한 코드가 **실제로 부르는** SQL ID 를 찾아, 그 mapper XML 만
     <WS>/src-sql/ 로 가져옵니다 (트리 전체를 복사하지 않습니다)
  4. 1-meta.json · 1-files.json 을 씁니다

왜 셸이 아니라 스크립트인가
---------------------------
팀 실행 환경이 PowerShell 입니다. `ls -la` · `mkdir -p` · `dirname` 이 없고,
무엇보다 Windows PowerShell 5.1 의 `>` 는 파일을 **UTF-16LE** 로 씁니다.
오류가 나지 않은 채 파일이 조용히 깨집니다. 그래서 파일을 만드는 일은
전부 여기서 합니다 — PowerShell 이든 bash 든 결과가 바이트까지 같습니다.

왜 mapper 를 통째로 가져오지 않는가
-----------------------------------
DPI mapper 저장소는 전사 공용입니다. dao 폴더 하나에 XML 이 수백 개 있고,
그중 이 화면이 부르는 것은 보통 서너 개입니다. 전부 가져오면 작업 폴더가
수십 MB 가 되고, SQL 리뷰어가 읽을 것을 찾느라 헤맵니다.

그래서 **코드를 먼저 읽고, 거기 나온 SQL ID 의 네임스페이스에 해당하는
파일만** 골라 옵니다. 못 찾은 네임스페이스는 1-meta.json 에 남겨,
리포트의 「확인 못 한 것」으로 이어집니다.

표준 라이브러리만 씁니다. pip 설치가 필요 없습니다.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
MAPPER_DIR_TXT = SKILL / "mapper-dir.txt"

# 수집 대상 확장자. 여기 없는 것은 리팩토링 관점에서 볼 일이 없습니다.
SOURCE_EXT = {".cs", ".csx", ".xaml", ".axaml", ".xml", ".config",
              ".csproj", ".props", ".targets", ".resx", ".sql"}

# 빌드 산출물과 생성 코드. 읽으면 "쓰지 않는 코드"가 잔뜩 잡힙니다.
SKIP_DIRS = {"bin", "obj", ".vs", ".git", "packages", "node_modules",
             "TestResults", ".idea", "_workspace"}
SKIP_FILE_RE = re.compile(r"\.(g|g\.i|designer|generated)\.cs$", re.I)

MAX_FILE_BYTES = 1024 * 1024       # 1MB 넘는 소스는 사람이 읽는 코드가 아닙니다


def die(msg, fix=None):
    print("✗ " + msg)
    if fix:
        print("  → " + fix)
    sys.exit(1)


def slugify(path_str):
    """경로 → 작업 폴더 이름. `.` 은 root, 구분자와 특수문자는 `-` 로."""
    s = path_str.strip().replace("\\", "/").strip("/")
    if s in ("", ".", "./"):
        return "root"
    s = re.sub(r"[^0-9A-Za-z_.-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-.")
    return s or "root"


def read_mapper_dir():
    """mapper-dir.txt 를 {키: 경로} 로 읽습니다."""
    if not MAPPER_DIR_TXT.exists():
        return {}
    out = {}
    for line in MAPPER_DIR_TXT.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        out[key.strip()] = val.strip()
    return out


# DPI/iBATIS 관례상 SQL ID 는 `lot.selectMcLot` 처럼 **양쪽 모두 소문자로 시작**합니다.
# 이 조건이 `System.Data` · `YOEDSMOV.Common` 같은 .NET 이름을 걸러 줍니다.
# 팀 관례가 다르면 이 정규식 하나만 고치면 됩니다.
RE_SQL_ID = re.compile(r"\"([a-z][A-Za-z0-9_]*)\.([a-z][A-Za-z0-9_]*)\"")

# mapper XML 의 namespace 는 파일 앞부분에 있습니다. 통째로 읽지 않습니다.
# 다만 DPI mapper 는 앞에 라이선스 주석과 DOCTYPE 이 길게 붙는 일이 흔해서
# 4KB 로는 선언을 놓칩니다. 놓치면 파일 이름으로만 고르게 되고, 그때부터
# `lotMapper.xml` 같은 파일이 조용히 빠집니다.
RE_NS = re.compile(r"<(?:sqlMap|mapper)\b[^>]*namespace\s*=\s*\"([^\"]+)\"")
NS_PROBE_BYTES = 16384


def scan_sql_ids(src_root: Path):
    """수집한 코드에서 호출하는 SQL ID 를 찾습니다.

    문자열 리터럴만 봅니다. 주석 안이든 밖이든 상관없습니다 — 여기서는
    **후보를 넉넉히 잡는 편이 안전**합니다. 못 가져온 mapper 는 티가 나지만,
    필요 없는 것을 하나 더 가져오는 건 손해가 거의 없습니다.
    """
    ids, namespaces = set(), set()
    for p in src_root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in (".cs", ".csx"):
            continue
        try:
            text = p.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue
        for ns, sid in RE_SQL_ID.findall(text):
            ids.add("%s.%s" % (ns, sid))
            namespaces.add(ns)
    return ids, namespaces


def declared_ns(p: Path):
    """파일 앞부분에서 선언된 namespace 를 읽습니다. 못 읽으면 None."""
    try:
        with p.open("rb") as f:
            head = f.read(NS_PROBE_BYTES).decode("utf-8", "replace")
    except OSError:
        return None
    m = RE_NS.search(head)
    return m.group(1) if m else None


def pick_mapper_files(mapper_src: Path, namespaces):
    """필요한 네임스페이스의 mapper 파일을 **전부** 골라 냅니다.

    **한 네임스페이스가 여러 파일에 나뉘어 있는 것이 DPI 의 기본형입니다.**
    `dao/lot/` 아래에 `lot.xml` 과 `lotMapper.xml` 이 둘 다 `namespace="lot"` 로
    있고, `lot.countLot` 은 뒤쪽 파일에만 있습니다.

    그래서 **이름이 맞는 파일 하나를 찾았다고 멈추면 안 됩니다.** 멈추면
    나머지 파일의 SQL 이 통째로 사라지는데, 못 가져왔다는 표시도 남지 않습니다
    (네임스페이스는 찾았으니까요). 인덱서는 그 ID 를 「정의 없음 = 실행하면
    터진다」로 보고하고, 그 오탐이 그대로 회의 자료에 실립니다.

    그래서 파일 이름이 아니라 **선언된 `namespace` 를 전수로** 봅니다.
    선언을 못 읽은 파일만 이름으로 대조합니다.

    돌려주는 것: (가져올 파일, 파일이 아예 없는 네임스페이스, 크기로 건너뛴 파일)
    """
    picked = {}
    oversized = []

    for p in mapper_src.rglob("*.xml"):
        if not p.is_file():
            continue
        ns = declared_ns(p)
        if ns is None:
            ns = p.stem          # 선언을 못 읽었을 때만 이름으로 대조합니다
        if ns not in namespaces:
            continue
        if p.stat().st_size > MAX_FILE_BYTES:
            # 조용히 넘기지 않습니다 — 이 파일의 SQL 은 아무도 못 읽습니다
            oversized.append(p)
            continue
        picked.setdefault(ns, []).append(p)

    files = sorted({p for paths in picked.values() for p in paths})
    return files, sorted(namespaces - set(picked)), sorted(oversized)


def git(*args, cwd=None):
    try:
        r = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True)
        if r.returncode != 0:
            return None
        return r.stdout.decode("utf-8", errors="replace").strip()
    except FileNotFoundError:
        return None


def prepare_ws(ws: Path, resume: bool):
    """작업 폴더를 준비합니다. **아무것도 지우지 않습니다.**"""
    archived = None
    if ws.exists() and any(ws.iterdir()):
        if resume:
            print("· 이어서 씁니다: %s" % ws)
        else:
            stamp = datetime.now().strftime("%Y%m%d-%H%M")
            archived = ws.parent / ("%s.prev-%s" % (ws.name, stamp))
            n = 2
            while archived.exists():
                archived = ws.parent / ("%s.prev-%s-%d" % (ws.name, stamp, n))
                n += 1
            ws.rename(archived)
            print("· 이전 실행을 밀어냈습니다: %s" % archived.name)
    ws.mkdir(parents=True, exist_ok=True)
    return archived.name if archived else None


def walk_sources(root: Path):
    """대상 경로에서 수집할 파일만 골라 냅니다."""
    picked, skipped = [], []
    if root.is_file():
        return ([root] if root.suffix.lower() in SOURCE_EXT else []), []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if SKIP_FILE_RE.search(p.name):
            skipped.append((p, "생성 코드"))
            continue
        if p.suffix.lower() not in SOURCE_EXT:
            continue
        if p.stat().st_size > MAX_FILE_BYTES:
            skipped.append((p, "1MB 초과"))
            continue
        picked.append(p)
    return picked, skipped


def main():
    ap = argparse.ArgumentParser(description="리팩토링 대상 원문 수집기")
    ap.add_argument("--path", required=True,
                    help="대상 소스 경로 (폴더 또는 파일). 저장소 전체는 `.`")
    ap.add_argument("--ws", required=True, help="작업 폴더 (_workspace/scan-…)")
    ap.add_argument("--resume", action="store_true",
                    help="이전 작업 폴더를 밀어내지 않고 이어서 씁니다")
    ap.add_argument("--mapper", help="mapper XML 폴더를 직접 지정 (mapper-dir.txt 대신)")
    ap.add_argument("--repo", help="mapper-dir.txt 에서 찾을 키. 생략하면 git 저장소 이름")
    ap.add_argument("--all-mappers", action="store_true",
                    help="선별하지 않고 mapper 트리 전체를 가져옵니다 "
                         "(전사 공용 저장소면 수백 개입니다 — 보통 필요 없습니다)")
    args = ap.parse_args()

    target = Path(args.path)
    ws = Path(args.ws)

    if not target.exists():
        die("대상 경로가 없습니다: %s" % target,
            "경로를 확인하세요. 저장소 루트에서 실행해야 합니다.")

    archived = prepare_ws(ws, args.resume)

    # ── 소스 수집 ────────────────────────────────────────────────────
    picked, skipped = walk_sources(target)
    if not picked:
        die("%s 에서 수집할 소스를 찾지 못했습니다." % target,
            "대상 경로에 .cs · .xaml 이 있는지 확인하세요. bin/ · obj/ 는 건너뜁니다.")

    src_root = ws / "src"
    base = target if target.is_dir() else target.parent
    files_meta = []
    total_lines = 0

    for p in picked:
        rel = p.relative_to(base).as_posix()
        dest = src_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        raw = p.read_bytes()
        dest.write_bytes(raw)                      # 바이트 그대로 — 인코딩을 건드리지 않습니다

        lines = raw.count(b"\n") + 1
        total_lines += lines
        kind = ("매퍼" if p.suffix.lower() == ".xml" and "mapper" in rel.lower()
                else "화면" if p.suffix.lower() in (".xaml", ".axaml")
                or rel.lower().endswith(".xaml.cs") else "공통")
        files_meta.append({
            "path": rel,
            "kind": kind,
            "ext": p.suffix.lower(),
            "bytes": len(raw),
            "lines": lines,
        })

    # git 이 있으면 파일별 최종 수정일과 커밋 수를 붙입니다.
    # 오래 안 건드린 코드는 "죽은 코드" 후보의 약한 신호입니다.
    if git("rev-parse", "--git-dir"):
        for fm in files_meta:
            full = (base / fm["path"]).as_posix()
            last = git("log", "-1", "--format=%ad", "--date=short", "--", full)
            count = git("rev-list", "--count", "HEAD", "--", full)
            if last:
                fm["lastCommit"] = last
            if count and count.isdigit():
                fm["commits"] = int(count)
    else:
        print("· git 을 쓸 수 없어 파일별 수정 이력은 넣지 않았습니다 (선택 항목입니다)")

    # ── mapper 수집 ──────────────────────────────────────────────────
    mapper_src = None
    mapper_count = 0
    mapper_note = None

    if args.mapper:
        mapper_src = Path(args.mapper)
    else:
        mapping = read_mapper_dir()
        key = args.repo
        if not key:
            top = git("rev-parse", "--show-toplevel")
            key = Path(top).name if top else None
        if key and key in mapping:
            mapper_src = Path(mapping[key])
        else:
            mapper_note = ("mapper-dir.txt 에 `%s` 매핑이 없습니다" % (key or "(저장소 이름 미상)"))

    # 코드가 실제로 부르는 SQL ID 를 먼저 찾습니다. 이게 있어야 선별할 수 있습니다.
    sql_ids, namespaces = scan_sql_ids(src_root)
    missing_ns = []
    oversized_mappers = []

    if mapper_src is not None:
        if not mapper_src.exists():
            mapper_note = "mapper 경로가 없습니다: %s" % mapper_src
            mapper_src = None
        elif not namespaces and not args.all_mappers:
            mapper_note = ("코드에서 SQL ID 를 찾지 못해 mapper 를 가져오지 않았습니다 "
                           "(전부 가져오려면 --all-mappers)")
            mapper_src = None
        else:
            sql_root = ws / "src-sql"
            if args.all_mappers:
                picked = sorted(p for p in mapper_src.rglob("*.xml")
                                if p.is_file() and p.stat().st_size <= MAX_FILE_BYTES)
            else:
                picked, missing_ns, oversized_mappers = pick_mapper_files(
                    mapper_src, namespaces)

            for p in picked:
                rel = p.relative_to(mapper_src).as_posix()
                dest = sql_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(p.read_bytes())
                mapper_count += 1

            if mapper_count == 0:
                mapper_note = ("필요한 네임스페이스(%s)에 해당하는 mapper 를 찾지 못했습니다: %s"
                               % (", ".join(sorted(namespaces)[:8]) or "없음", mapper_src))

    meta = {
        "target": args.path,
        "slug": slugify(args.path),
        "workspace": ws.as_posix(),
        "sources": {
            "files": len(files_meta),
            "lines": total_lines,
            "mapper": mapper_src.as_posix() if mapper_src else None,
            "mapperFiles": mapper_count,
            "mapperMode": "all" if args.all_mappers else "선별",
            "sqlIdsCalled": sorted(sql_ids),
            "namespacesNeeded": sorted(namespaces),
            # 코드는 부르는데 mapper 파일을 못 찾은 네임스페이스입니다.
            # SQL 리뷰어가 「확인 못 한 것」에 적어야 합니다.
            "namespacesNotFound": missing_ns,
            # 필요한 네임스페이스인데 1MB 를 넘어 가져오지 못한 파일입니다.
            # 네임스페이스는 찾았지만 **그 파일의 SQL 본문은 못 읽었습니다.**
            "mapperFilesTooLarge": [p.as_posix() for p in oversized_mappers],
            "skipped": [{"path": str(p), "why": why} for p, why in skipped[:50]],
        },
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    if archived:
        meta["archivedPrevious"] = archived
    if mapper_note:
        meta["mapperNote"] = mapper_note

    (ws / "1-meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8", newline="")
    (ws / "1-files.json").write_text(
        json.dumps(files_meta, ensure_ascii=False, indent=2), encoding="utf-8", newline="")

    # ── 보고 ─────────────────────────────────────────────────────────
    print("✓ %s" % (ws / "src"))
    print("✓ %s" % (ws / "1-meta.json"))
    print("✓ %s" % (ws / "1-files.json"))
    print()
    print("  대상: %s  (작업 폴더 %s)" % (args.path, ws))
    print("  파일 %d · 줄 %d" % (len(files_meta), total_lines))
    if sql_ids:
        print("  호출하는 SQL ID %d개 · 네임스페이스 %d개 (%s)"
              % (len(sql_ids), len(namespaces), ", ".join(sorted(namespaces)[:6])))
    if mapper_count:
        mode = "전체" if args.all_mappers else "선별"
        print("  mapper %d개 (%s) → %s" % (mapper_count, mode, ws / "src-sql"))
        if missing_ns:
            print("  ! mapper 를 못 찾은 네임스페이스: %s" % ", ".join(missing_ns))
            print("    그 SQL 본문은 읽을 수 없습니다. 리포트의 「확인 못 한 것」에 남습니다.")
        if oversized_mappers:
            print("  ! 1MB 를 넘어 가져오지 못한 mapper: %s"
                  % ", ".join(p.name for p in oversized_mappers))
            print("    그 파일의 SQL 본문은 읽을 수 없습니다. 「확인 못 한 것」에 남습니다.")
    else:
        print("  mapper 없음 — %s" % (mapper_note or "매핑을 찾지 못했습니다"))
        print("    SQL 미사용 판정은 할 수 없습니다. 리포트에 그 사실이 남습니다.")
    if skipped:
        print("  건너뜀 %d개 (생성 코드·대용량)" % len(skipped))
    print()

    if total_lines > 30000 or len(files_meta) > 200:
        print("! 규모가 큽니다 (파일 %d · 줄 %d)." % (len(files_meta), total_lines))
        print("  화면 하나나 폴더 하나로 좁혀 돌리는 편이 리포트가 쓸 만합니다.")
        print()

    print("다음: python index.py --ws %s" % ws)
    return 0


if __name__ == "__main__":
    sys.exit(main())
