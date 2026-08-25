const path = require('path')
const os = require('os')

// 설정은 환경변수로만 바꿉니다. 설정 파일은 없습니다.
//   NOTEQ_FILE  저장 위치        (기본: ~/.noteq.json)
//   NOTEQ_MAX   최대 보관 개수   (기본: 50, 넘으면 오래된 것부터 밀어냄)
function loadConfig() {
  const file = process.env.NOTEQ_FILE || path.join(os.homedir(), '.noteq.json')
  const raw = process.env.NOTEQ_MAX
  let max = 50
  if (raw !== undefined) {
    const n = Number(raw)
    if (Number.isInteger(n) && n > 0) max = n
    // 잘못된 값은 조용히 무시하고 기본값을 씁니다
  }
  return { file, max }
}

module.exports = { loadConfig }
