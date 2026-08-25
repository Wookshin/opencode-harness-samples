#!/usr/bin/env node
// noteq — 아주 작은 메모 큐 CLI.
// 07-combined-refine 샘플의 문서화 대상입니다.

const { loadConfig } = require('./lib/config')
const { Store } = require('./lib/store')

const HELP = `noteq — 메모 큐

사용법:
  noteq add <내용>      메모를 큐에 넣습니다
  noteq pop             가장 오래된 메모를 꺼내 지웁니다
  noteq peek            꺼내지 않고 다음 메모만 봅니다
  noteq list            전체를 봅니다
  noteq clear           전부 지웁니다
`

function main(argv) {
  const [cmd, ...rest] = argv
  const cfg = loadConfig()
  const store = new Store(cfg.file, cfg.max)

  switch (cmd) {
    case 'add': {
      const text = rest.join(' ').trim()
      if (!text) return fail('내용이 비어 있습니다')
      const r = store.push(text)
      if (r.dropped) console.log(`(가장 오래된 메모를 밀어냈습니다: ${r.dropped})`)
      console.log(`추가: ${text}`)
      return 0
    }
    case 'pop': {
      const item = store.shift()
      if (!item) return fail('큐가 비어 있습니다')
      console.log(item)
      return 0
    }
    case 'peek': {
      const item = store.head()
      if (!item) return fail('큐가 비어 있습니다')
      console.log(item)
      return 0
    }
    case 'list': {
      const all = store.all()
      if (all.length === 0) return fail('큐가 비어 있습니다')
      all.forEach((t, i) => console.log(`${i + 1}. ${t}`))
      return 0
    }
    case 'clear':
      store.clear()
      console.log('비웠습니다')
      return 0
    default:
      console.log(HELP)
      return cmd ? 1 : 0
  }
}

function fail(msg) {
  console.error(`오류: ${msg}`)
  return 1
}

if (require.main === module) process.exit(main(process.argv.slice(2)))

module.exports = { main }
