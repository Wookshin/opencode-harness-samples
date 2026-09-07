#!/usr/bin/env node
/**
 * collect.mjs — PR 변경분과 원문을 작업 폴더로 수집합니다 (Phase 1 의 기계적인 부분)
 *
 *   node collect.mjs --pr 1234 --ws _workspace/pr-1234
 *   node collect.mjs --pr sample --ws _workspace/pr-sample \
 *                    --patch sample/pr-sample.patch --after sample/after --before sample/before
 *
 * 왜 스크립트인가:
 *   셸마다 문법이 다릅니다. `mkdir -p`, `$(dirname …)`, `$(date …)` 는 PowerShell 에 없고,
 *   무엇보다 `>` 리디렉션의 기본 인코딩이 셸·버전마다 다릅니다
 *   (Windows PowerShell 5.1 은 UTF-16LE — 오류 없이 패치와 원문이 통째로 깨집니다).
 *   그래서 gh/git 을 여기서 직접 부르고 출력을 **버퍼 그대로** 파일에 씁니다.
 *   bash 든 PowerShell 이든 결과가 같습니다.
 *
 * Node 내장 모듈만 씁니다. 외부 의존 없음.
 */
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, writeFileSync, readFileSync, renameSync, readdirSync, cpSync } from 'node:fs';
import { dirname, join, resolve, basename } from 'node:path';

/* ── 인자 ────────────────────────────────────────────────────────────── */
const args = {};
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  if (a.startsWith('--')) args[a.slice(2)] = (process.argv[i + 1] || '').startsWith('--') ? true : process.argv[++i];
}
function die(msg) { console.error('✗ ' + msg); process.exit(1); }

if (!args.pr || !args.ws) {
  die('사용법: node collect.mjs --pr <번호> --ws <작업폴더> [--resume]\n' +
      '        node collect.mjs --pr sample --ws <작업폴더> --patch <파일> --after <폴더> --before <폴더>');
}
const PR = String(args.pr);
const WS = resolve(args.ws);
const OFFLINE = !!args.patch;

/* ── 실행 도우미 — 출력은 버퍼로 받습니다 ────────────────────────────── */
function run(cmd, cmdArgs, { allowFail = false } = {}) {
  try {
    return execFileSync(cmd, cmdArgs, { maxBuffer: 512 * 1024 * 1024, encoding: 'buffer', stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (e) {
    if (allowFail) return null;
    const err = e.stderr ? e.stderr.toString('utf8').trim() : e.message;
    die(`명령 실패: ${cmd} ${cmdArgs.join(' ')}\n  ${err}`);
  }
}
const text = (buf) => (buf ? buf.toString('utf8').replace(/^﻿/, '') : '');

function writeOut(relPath, data) {
  const p = join(WS, relPath);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, data);           // Buffer 면 그대로, 문자열이면 UTF-8 (BOM 없음)
  return p;
}

/* ── 작업 폴더 준비 ──────────────────────────────────────────────────── */
function stamp() {
  const d = new Date(), z = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${z(d.getMonth() + 1)}${z(d.getDate())}-${z(d.getHours())}${z(d.getMinutes())}`;
}
let archived = null;
if (existsSync(WS) && readdirSync(WS).length > 0) {
  if (args.resume) {
    console.log(`· 기존 작업 폴더에 이어서 씁니다: ${args.ws}`);
  } else {
    archived = `${WS}.prev-${stamp()}`;
    renameSync(WS, archived);       // 지우지 않고 밀어냅니다
    console.log(`· 이전 실행을 밀어냈습니다: ${basename(archived)}`);
  }
}
mkdirSync(WS, { recursive: true });

/* ── 패치 파싱 — 파일별 상태를 결정적으로 뽑습니다 ───────────────────── */
function flagSql(f, line) {
  if (f.hasSql) return;
  if (/(AddSql|_sql\.|\.Bind\(|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|DPICALL|SQLEXEC)/i.test(line)) f.hasSql = true;
}
function parseFiles(patch) {
  const out = [];
  let cur = null;
  const strip = (p) => p.replace(/^[ab]\//, '').replace(/^"|"$/g, '');
  const push = () => { if (cur) out.push(cur); };

  for (const line of patch.split(/\r?\n/)) {
    const g = line.match(/^diff --git (.+?) (.+)$/);
    if (g) {
      push();
      cur = { path: strip(g[2]), oldPath: strip(g[1]), status: 'modified',
              additions: 0, deletions: 0, hunks: 0, hasSql: false };
      continue;
    }
    if (!cur) continue;
    if (line.startsWith('new file mode'))          cur.status = 'added';
    else if (line.startsWith('deleted file mode')) cur.status = 'deleted';
    else if (line.startsWith('rename from') || line.startsWith('rename to'))
      cur.status = dirname(cur.oldPath) === dirname(cur.path) ? 'renamed' : 'moved';
    else if (line.startsWith('@@')) cur.hunks++;
    else if (line.startsWith('+') && !line.startsWith('+++')) { cur.additions++; flagSql(cur, line); }
    else if (line.startsWith('-') && !line.startsWith('---')) { cur.deletions++; flagSql(cur, line); }
  }
  push();
  return out.map(f => ({
    ...f,
    oldPath: f.oldPath === f.path ? null : f.oldPath,
    priority: /\.xaml\.cs$/i.test(f.path) ? 1 : 2
  }));
}

/* ── 수집 ────────────────────────────────────────────────────────────── */
let meta, files;

if (OFFLINE) {
  /* 오프라인 데모 — gh 도 네트워크도 쓰지 않습니다 */
  if (!existsSync(args.patch)) die(`패치를 찾을 수 없습니다: ${args.patch}`);
  const patchBuf = readFileSync(args.patch);
  writeOut('1-diff.patch', patchBuf);
  files = parseFiles(text(patchBuf));

  for (const [side, dir] of [['after', args.after], ['before', args.before]]) {
    if (!dir) continue;
    if (!existsSync(dir)) { console.log(`! 원문 폴더 없음: ${dir}`); continue; }
    cpSync(dir, join(WS, 'src', side), { recursive: true });
  }
  meta = {
    prNumber: PR, title: args.title || '오프라인 데모 (sample)', author: args.author || '',
    url: '', baseRef: args.base || 'develop', headRef: args.head || 'feature/sample',
    headSha: '', mode: 'offline'
  };
} else {
  /* 실제 PR — 체크아웃하지 않습니다 */
  run('git', ['rev-parse', '--git-dir']);

  const view = JSON.parse(text(run('gh', ['pr', 'view', PR, '--json',
    'number,title,author,url,baseRefName,headRefName,headRefOid'])));
  const base = view.baseRefName;

  const patchBuf = run('gh', ['pr', 'diff', PR]);
  writeOut('1-diff.patch', patchBuf);
  files = parseFiles(text(patchBuf));

  console.log('· 원격 참조를 가져옵니다 (체크아웃하지 않습니다)…');
  run('git', ['fetch', 'origin', `pull/${PR}/head:refs/remotes/pr/${PR}`, '--force']);
  run('git', ['fetch', 'origin', base], { allowFail: true });

  let okAfter = 0, okBefore = 0; const missed = [];
  for (const f of files) {
    if (f.status !== 'deleted') {
      const buf = run('git', ['show', `refs/remotes/pr/${PR}:${f.path}`], { allowFail: true });
      if (buf) { writeOut(join('src/after', f.path), buf); okAfter++; }
      else missed.push(`src/after/${f.path}`);
    }
    if (f.status !== 'added') {
      const src = f.oldPath || f.path;
      const buf = run('git', ['show', `origin/${base}:${src}`], { allowFail: true });
      if (buf) { writeOut(join('src/before', f.path), buf); okBefore++; }
      else missed.push(`src/before/${f.path}`);
    }
  }
  if (missed.length) console.log(`! 원문을 못 받은 것 ${missed.length}건:\n  ${missed.join('\n  ')}`);

  meta = {
    prNumber: String(view.number), title: view.title,
    author: (view.author && view.author.login) || '',
    url: view.url, baseRef: base, headRef: view.headRefName,
    headSha: view.headRefOid, mode: 'gh',
    sources: { after: okAfter, before: okBefore, missing: missed }
  };
}

meta.generatedAt = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
meta.workspace = args.ws;
if (archived) meta.archivedPrevious = basename(archived);

writeOut('1-meta.json',  JSON.stringify(meta, null, 2) + '\n');
writeOut('1-files.json', JSON.stringify(files, null, 2) + '\n');

/* ── 보고 ────────────────────────────────────────────────────────────── */
const byStatus = files.reduce((a, f) => (a[f.status] = (a[f.status] || 0) + 1, a), {});
console.log(`\n✓ 수집 완료 — ${args.ws}`);
console.log(`  PR #${meta.prNumber} «${meta.title}»`);
console.log(`  ${meta.baseRef} ← ${meta.headRef}${meta.headSha ? ' (' + meta.headSha.slice(0, 7) + ')' : ''}`);
console.log(`  파일 ${files.length}개 — ` + Object.entries(byStatus).map(([k, v]) => `${k} ${v}`).join(' · '));
console.log(`  SQL 변경 ${files.filter(f => f.hasSql).length}개 · 우선순위 1 ${files.filter(f => f.priority === 1).length}개`);
console.log('\n  파일 목록 (1-files.json 에 같은 내용이 있습니다)');
for (const f of files.sort((a, b) => a.priority - b.priority || a.path.localeCompare(b.path))) {
  console.log(`  ${f.priority === 1 ? '★' : ' '} ${f.status.padEnd(8)} ${f.hasSql ? 'SQL ' : '    '}` +
              `헝크 ${String(f.hunks).padStart(2)} +${f.additions}/-${f.deletions}  ${f.path}` +
              (f.oldPath ? `  ← ${f.oldPath}` : ''));
}
console.log('\n  다음: 1-scope.md 와 1-hunks.md 를 작성하세요.');
