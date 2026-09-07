#!/usr/bin/env node
/**
 * build-report.mjs — findings.json → 팀 오프라인 리뷰용 단일 HTML
 *
 *   node build-report.mjs <findings.json> <out.html> [diff.patch]
 *
 * 이 스크립트가 존재하는 이유:
 *   변경 전/후 코드와 라인 색칠을 LLM 이 옮겨 적지 않게 하려고.
 *   코드는 patch 와 src/{before,after}/ 원문에서 여기가 직접 계산합니다.
 *
 * Node 내장 모듈만 씁니다. 외부 의존 없음.
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const TEMPLATE = join(HERE, 'report-template.html');

/* ── 종료 ────────────────────────────────────────────────────────────── */
const problems = [];
function bad(msg) { problems.push(msg); }
function die(msg) { console.error('✗ ' + msg); process.exit(1); }

/* ── 인자 ────────────────────────────────────────────────────────────── */
const [, , findingsArg, outArg, patchArg] = process.argv;
if (!findingsArg || !outArg) {
  die('사용법: node build-report.mjs <findings.json> <out.html> [diff.patch]');
}
const findingsPath = resolve(findingsArg);
const outPath = resolve(outArg);
if (!existsSync(findingsPath)) die(`findings.json 을 찾을 수 없습니다: ${findingsPath}`);
if (!existsSync(TEMPLATE)) die(`템플릿을 찾을 수 없습니다: ${TEMPLATE}`);

const WS = dirname(findingsPath);                        // _workspace 기준 폴더
const patchPath = patchArg ? resolve(patchArg) : join(WS, '1-diff.patch');

let D;
try {
  D = JSON.parse(readFileSync(findingsPath, 'utf8'));
} catch (e) {
  die(`findings.json 이 올바른 JSON 이 아닙니다: ${e.message}`);
}

/* ── 스키마 검증 ─────────────────────────────────────────────────────── */
const SEVERITIES = ['BLOCKER', 'MAJOR', 'MINOR'];
const PERSPECTIVES = ['refactor', 'feature', 'sql'];
const CHANGE_TYPES = ['added', 'modified', 'renamed', 'moved', 'deleted'];
const VERDICTS = ['CONFIRMED', 'NEEDS-INFO'];

function arr(v, name) {
  if (v === undefined || v === null) return [];
  if (!Array.isArray(v)) { bad(`${name} 은 배열이어야 합니다`); return []; }
  return v;
}
function need(obj, key, where) {
  if (obj[key] === undefined || obj[key] === null || obj[key] === '') {
    bad(`${where}: 필수 항목 "${key}" 이 없습니다`);
    return false;
  }
  return true;
}
function oneOf(obj, key, list, where) {
  if (obj[key] !== undefined && !list.includes(obj[key])) {
    bad(`${where}: "${key}" 는 ${list.join(' | ')} 중 하나여야 합니다 (받은 값: ${obj[key]})`);
  }
}

if (!D.meta || typeof D.meta !== 'object') { bad('meta 가 없습니다'); D.meta = {}; }
['prNumber', 'title', 'baseRef', 'generatedAt', 'verdict'].forEach(k => need(D.meta, k, 'meta'));
oneOf(D.meta, 'verdict', ['PASS', 'FAIL'], 'meta');

D.files         = arr(D.files, 'files');
D.units         = arr(D.units, 'units');
D.findings      = arr(D.findings, 'findings');
D.simpleChanges = arr(D.simpleChanges, 'simpleChanges');
D.sql           = arr(D.sql, 'sql');
D.rejected      = arr(D.rejected, 'rejected');
D.unknowns      = arr(D.unknowns, 'unknowns');

if (!D.files.length) bad('files 가 비어 있습니다 — 변경된 파일이 하나는 있어야 합니다');

const filePaths = new Set();
D.files.forEach((f, i) => {
  const w = `files[${i}]`;
  need(f, 'path', w); need(f, 'changeType', w);
  oneOf(f, 'changeType', CHANGE_TYPES, w);
  if (f.priority === undefined) f.priority = /\.xaml\.cs$/i.test(f.path || '') ? 1 : 2;
  if (f.path) filePaths.add(f.path);
});

const unitIds = new Set();
D.units.forEach((u, i) => {
  const w = `units[${i}]`;
  need(u, 'id', w); need(u, 'file', w); need(u, 'kind', w); need(u, 'summary', w);
  if (u.id) {
    if (unitIds.has(u.id)) bad(`${w}: 변경단위 ID "${u.id}" 가 중복됩니다`);
    unitIds.add(u.id);
  }
  if (u.file && !filePaths.has(u.file)) {
    bad(`${w}: file "${u.file}" 이 files[].path 에 없습니다 (경로가 글자 그대로 같아야 합니다)`);
  }
  ['afterLines', 'beforeLines'].forEach(k => {
    const v = u[k];
    if (v === undefined || v === null) { u[k] = null; return; }
    if (!Array.isArray(v) || v.length !== 2 || !v.every(n => Number.isInteger(n) && n > 0)) {
      bad(`${w}: ${k} 는 [시작, 끝] 형태의 양의 정수 배열이어야 합니다`);
      u[k] = null;
    } else if (v[0] > v[1]) {
      bad(`${w}: ${k} 의 시작(${v[0]})이 끝(${v[1]})보다 큽니다`);
    }
  });
  if (!u.afterLines && !u.beforeLines) {
    bad(`${w}: afterLines 와 beforeLines 가 모두 없습니다 — 하나는 있어야 코드를 보여줄 수 있습니다`);
  }
});

const seenFindingIds = new Set();
D.findings.forEach((f, i) => {
  const w = `findings[${i}]${f.id ? ' (' + f.id + ')' : ''}`;
  ['id', 'perspective', 'severity', 'unitId', 'file', 'line', 'title', 'problem', 'basis', 'suggestion']
    .forEach(k => need(f, k, w));
  oneOf(f, 'perspective', PERSPECTIVES, w);
  oneOf(f, 'severity', SEVERITIES, w);
  if (f.verdict === undefined) f.verdict = 'CONFIRMED';
  oneOf(f, 'verdict', VERDICTS, w);
  if (f.verdict === 'REJECTED') bad(`${w}: REJECTED 는 findings 가 아니라 rejected 에 넣으세요`);
  if (f.id) {
    if (seenFindingIds.has(f.id)) bad(`${w}: 지적 ID 가 중복됩니다`);
    seenFindingIds.add(f.id);
  }
  if (f.unitId && !unitIds.has(f.unitId)) bad(`${w}: unitId "${f.unitId}" 가 units 에 없습니다`);
  if (f.file && !filePaths.has(f.file)) bad(`${w}: file "${f.file}" 이 files[].path 에 없습니다`);
  if (f.line !== undefined && !Number.isInteger(f.line)) bad(`${w}: line 은 정수여야 합니다`);
});

D.sql.forEach((s, i) => {
  const w = `sql[${i}]`;
  need(s, 'id', w); need(s, 'callType', w); need(s, 'body', w);
  oneOf(s, 'callType', ['DPICALL', 'SQLEXEC'], w);
  if (s.callType === 'DPICALL') need(s, 'sqlId', w);
  s.tuningPoints = arr(s.tuningPoints, `${w}.tuningPoints`);
  if (s.unitId && !unitIds.has(s.unitId)) bad(`${w}: unitId "${s.unitId}" 가 units 에 없습니다`);
});

D.rejected.forEach((r, i) => {
  const w = `rejected[${i}]`;
  need(r, 'id', w); need(r, 'title', w); need(r, 'reason', w);
});

if (problems.length) {
  console.error(`✗ findings.json 검증 실패 — ${problems.length}건\n`);
  problems.forEach(p => console.error('  · ' + p));
  console.error('\n스키마: .opencode/skills/code-review-oi-pr/references/html-report.md');
  console.error('HTML 을 손으로 고치지 말고 JSON 을 고쳐 다시 실행하세요.');
  process.exit(1);
}

/* 지적 조각에도 파일 언어를 붙입니다 (HTML 이 files 를 되짚지 않도록) */
{
  const byPath = new Map(D.files.map(f => [f.path, langOf(f.path)]));
  D.findings.forEach(f => { f.lang = byPath.get(f.file) || 'text'; });
}

/* ── 패치 파싱 ───────────────────────────────────────────────────────── */
/**
 * 파일별로 두 가지를 뽑습니다.
 *   added      : after 기준으로 추가된 라인 번호 집합
 *   deletions  : "after 몇 번째 줄 앞에 지워진 줄이 있었나" 를 앵커로 잡은 맵
 * 이 둘만 있으면 after 원문 위에 diff 를 정확히 얹을 수 있습니다.
 */
function parsePatch(text) {
  const byPath = new Map();
  if (!text) return byPath;

  const lines = text.split(/\r?\n/);
  let cur = null, a = 0, b = 0;

  const start = (path) => {
    if (!byPath.has(path)) byPath.set(path, { added: new Set(), deletions: new Map() });
    return byPath.get(path);
  };
  const strip = (p) => p.replace(/^[ab]\//, '').replace(/^"|"$/g, '');

  for (const raw of lines) {
    if (raw.startsWith('diff --git ')) {
      const m = raw.match(/^diff --git (.+?) (.+)$/);
      cur = m ? start(strip(m[2])) : null;
      continue;
    }
    if (raw.startsWith('+++ ')) {
      const p = raw.slice(4).trim();
      if (p !== '/dev/null') cur = start(strip(p));
      continue;
    }
    if (raw.startsWith('--- ') || raw.startsWith('index ') ||
        raw.startsWith('new file') || raw.startsWith('deleted file') ||
        raw.startsWith('similarity ') || raw.startsWith('rename ') ||
        raw.startsWith('old mode') || raw.startsWith('new mode') ||
        raw.startsWith('Binary files')) continue;

    const hunk = raw.match(/^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/);
    if (hunk) { a = +hunk[1]; b = +hunk[3]; continue; }
    if (!cur) continue;

    const op = raw[0];
    if (op === '+')      { cur.added.add(b); b++; }
    else if (op === '-') {
      if (!cur.deletions.has(b)) cur.deletions.set(b, []);
      cur.deletions.get(b).push({ text: raw.slice(1), beforeNo: a });
      a++;
    }
    else if (op === ' ') { a++; b++; }
    else if (op === '\\') { /* \ No newline at end of file */ }
  }
  return byPath;
}

const patchText = existsSync(patchPath) ? readFileSync(patchPath, 'utf8') : '';
if (!patchText) {
  console.warn(`! 패치를 찾지 못했습니다 (${patchPath}) — 추가/삭제 색칠 없이 원문만 표시합니다.`);
}
const patch = parsePatch(patchText);

/* ── 원문 읽기 ───────────────────────────────────────────────────────── */
function readSource(relPath) {
  if (!relPath) return null;
  const p = resolve(WS, relPath);
  if (!existsSync(p)) return null;
  const lines = readFileSync(p, 'utf8').replace(/\r\n/g, '\n').split('\n');
  // 파일 끝 개행 때문에 생기는 빈 줄은 실제 코드 줄이 아닙니다.
  if (lines.length && lines[lines.length - 1] === '') lines.pop();
  return lines;
}

/**
 * 파일 확장자로 하이라이트 언어를 정합니다.
 * HTML 쪽 하이라이터는 'cs' 와 'sql' 만 알고, 그 외는 색을 입히지 않습니다.
 */
function langOf(path = '') {
  if (/\.(cs|csx)$/i.test(path)) return 'cs';
  if (/\.sql$/i.test(path)) return 'sql';
  return 'text';
}

const sources = new Map();   // path → { after: string[]|null, before: string[]|null }
D.files.forEach(f => {
  const after  = readSource(f.afterFile);
  const before = readSource(f.beforeFile);
  if (f.afterFile  && !after)  console.warn(`! 원문 없음: ${f.afterFile}`);
  if (f.beforeFile && !before) console.warn(`! 원문 없음: ${f.beforeFile}`);
  sources.set(f.path, { after, before });
});

/* ── 코드 행 만들기 ──────────────────────────────────────────────────── */
function markOf(path) {
  return patch.get(path) || { added: new Set(), deletions: new Map() };
}

/** after 원문 [from, to] 구간을 diff 가 얹힌 행 배열로 */
function rowsFromAfter(path, from, to) {
  const src = (sources.get(path) || {}).after;
  const mk = markOf(path);
  const rows = [];
  if (!src) return rows;
  const end = Math.min(to, src.length);
  for (let n = from; n <= end; n++) {
    (mk.deletions.get(n) || []).forEach(d =>
      rows.push({ type: 'del', beforeNo: d.beforeNo, afterNo: null, text: d.text }));
    rows.push({ type: mk.added.has(n) ? 'add' : 'ctx', afterNo: n, beforeNo: null, text: src[n - 1] });
  }
  // 파일 끝에서 지워진 코드는 앵커가 마지막 줄 다음이라 위 반복에 안 잡힙니다.
  // 파일 끝일 때만 붙입니다 — 중간이면 다음 변경단위가 자기 시작 줄에서 보여 줍니다.
  if (end === src.length) {
    (mk.deletions.get(end + 1) || []).forEach(d =>
      rows.push({ type: 'del', beforeNo: d.beforeNo, afterNo: null, text: d.text }));
  }
  return rows;
}

/** 삭제만 있는 변경단위 — before 원문 구간을 전부 del 로 */
function rowsFromBefore(path, from, to) {
  const src = (sources.get(path) || {}).before;
  const rows = [];
  if (!src) return rows;
  for (let n = from; n <= Math.min(to, src.length); n++) {
    rows.push({ type: 'del', beforeNo: n, afterNo: null, text: src[n - 1] });
  }
  return rows;
}

/** 패치 hunk 만으로 행을 만든다 (원문이 없을 때의 대체 경로) */
function rowsFromPatchOnly(path, from, to) {
  const mk = markOf(path);
  const rows = [];
  const anchors = [...mk.added, ...mk.deletions.keys()].filter(n => n >= from && n <= to + 1);
  if (!anchors.length) return rows;
  for (let n = from; n <= to; n++) {
    (mk.deletions.get(n) || []).forEach(d =>
      rows.push({ type: 'del', beforeNo: d.beforeNo, afterNo: null, text: d.text }));
    if (mk.added.has(n)) rows.push({ type: 'add', afterNo: n, beforeNo: null, text: '(원문 없음)' });
  }
  return rows;
}

const langByFile = new Map(D.files.map(f => [f.path, langOf(f.path)]));

let unitsWithCode = 0;
D.units.forEach(u => {
  u.lang = langByFile.get(u.file) || 'text';
  let rows = [];
  if (u.afterLines)       rows = rowsFromAfter(u.file, u.afterLines[0], u.afterLines[1]);
  if (!rows.length && u.beforeLines) rows = rowsFromBefore(u.file, u.beforeLines[0], u.beforeLines[1]);
  if (!rows.length && u.afterLines)  rows = rowsFromPatchOnly(u.file, u.afterLines[0], u.afterLines[1]);
  u.rows = rows;
  if (rows.length) unitsWithCode++;
});

/* 파일 원문 임베드 (접이식) + 하이라이트 언어 */
D.files.forEach(f => {
  f.lang = langOf(f.path);
  const src = (sources.get(f.path) || {}).after;
  if (!src) { f.lines = []; return; }
  const mk = markOf(f.path);
  f.lines = src.map((text, i) => ({
    type: mk.added.has(i + 1) ? 'add' : 'ctx', afterNo: i + 1, beforeNo: null, text
  }));
});

/* ── 렌더 ────────────────────────────────────────────────────────────── */
const htmlEscape = (s) => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// JSON 안의 <, >, & 를 이스케이프해 </script> 로 태그가 닫히는 것을 막습니다.
const payload = JSON.stringify(D)
  .replace(/</g, '\\u003c').replace(/>/g, '\\u003e').replace(/&/g, '\\u0026')
  .replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');

const title = `코드리뷰 #${D.meta.prNumber} · ${D.meta.title}`;

const html = readFileSync(TEMPLATE, 'utf8')
  .replace('__TITLE__', htmlEscape(title))
  .replace('__PAYLOAD__', () => payload);

writeFileSync(outPath, html, 'utf8');

/* ── 보고 ────────────────────────────────────────────────────────────── */
const bySev = SEVERITIES.map(s => `${s} ${D.findings.filter(f => f.severity === s).length}`).join(' · ');
const kb = (Buffer.byteLength(html, 'utf8') / 1024).toFixed(0);
console.log(`✓ ${outPath}`);
console.log(`  판정 ${D.meta.verdict} · 지적 ${D.findings.length}건 (${bySev})`);
console.log(`  파일 ${D.files.length} · 변경단위 ${D.units.length} (코드 표시 ${unitsWithCode}) · SQL ${D.sql.length} · 반려 ${D.rejected.length}`);
console.log(`  ${kb} KB · 외부 요청 없음`);
if (unitsWithCode < D.units.length) {
  console.log(`  ! 변경단위 ${D.units.length - unitsWithCode}개는 코드를 표시하지 못했습니다 — src/after 원문과 라인 범위를 확인하세요.`);
}
