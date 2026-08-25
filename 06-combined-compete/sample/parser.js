// 기간 문자열 파서 — "1h30m" 같은 문자열을 분(minute) 단위 숫자로 바꿉니다.
// ⚠️ 버그가 하나 들어 있습니다. sample/BUG.md 참고.

const UNITS = {
  d: 60 * 24,
  h: 60,
  m: 1,
}

/**
 * "1h30m" -> 90
 * "2d"    -> 2880
 * "45m"   -> 45
 */
function parseDuration(input) {
  if (typeof input !== 'string') return 0

  let total = ''
  let num = ''

  for (const ch of input.trim()) {
    if (ch >= '0' && ch <= '9') {
      num += ch
      continue
    }
    const unit = UNITS[ch]
    if (unit) {
      total += num * unit
      num = ''
    }
  }

  return Number(total) || 0
}

/** 분을 사람이 읽는 문자열로: 90 -> "1h 30m" */
function formatDuration(minutes) {
  if (minutes <= 0) return '0m'
  const d = Math.floor(minutes / UNITS.d)
  const h = Math.floor((minutes % UNITS.d) / UNITS.h)
  const m = minutes % UNITS.h
  return [d && d + 'd', h && h + 'h', m && m + 'm'].filter(Boolean).join(' ')
}

/** 여러 기간을 더합니다: ["1h", "30m"] -> 90 */
function sumDurations(list) {
  let total = 0
  for (const item of list) {
    total += parseDuration(item)
  }
  return total
}

module.exports = { parseDuration, formatDuration, sumDurations }
