#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
리팩토링 대상 원문 수집기.

    python collect.py --path YOEDSMOV --ws _workspace/scan-YOEDSMOV

하는 일:
  1. 작업 폴더를 만듭니다 (이전 실행은 지우지 않고 밀어냅니다)
  2. 대상 경로의 텍스트 소스를 <WS>/src/ 로 바이트 그대로 복사합니다
  3. mapper-dir.txt 매핑을 따라 iBATIS mapper XML 을 <WS>/src-sql/ 로 가져옵니다
  4. 1-meta.json · 1-files.json 을 씁니다

왜 셸이 아니라 스크립트인가
---------------------------
팀 실행 환경이 PowerShell 입니다. `ls -la` · `mkdir -p` · `dirname` 이 없고,
무엇보다 Windows PowerShell 5.1 의 `>` 는 파일을 **UTF-16LE** 로 씁니다.
오류가 나지 않은 채 파일이 조용히 깨집니다. 그래서 파일을 만드는 일은
전부 여기서 합니다 — PowerShell 이든 bash 든 결과가 바이트까지 같습니다.

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

    if mapper_src is not None:
        if not mapper_src.exists():
            mapper_note = "mapper 경로가 없습니다: %s" % mapper_src
            mapper_src = None
        else:
            sql_root = ws / "src-sql"
            for p in sorted(mapper_src.rglob("*.xml")):
                if p.stat().st_size > MAX_FILE_BYTES:
                    continue
                rel = p.relative_to(mapper_src).as_posix()
                dest = sql_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(p.read_bytes())
                mapper_count += 1
            if mapper_count == 0:
                mapper_note = "mapper 경로에 .xml 이 없습니다: %s" % mapper_src

    meta = {
        "target": args.path,
        "slug": slugify(args.path),
        "workspace": ws.as_posix(),
        "sources": {
            "files": len(files_meta),
            "lines": total_lines,
            "mapper": mapper_src.as_posix() if mapper_src else None,
            "mapperFiles": mapper_count,
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
    if mapper_count:
        print("  mapper %d개 → %s" % (mapper_count, ws / "src-sql"))
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
