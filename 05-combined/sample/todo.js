// 아주 작은 할 일 CLI — 05-combined 샘플의 시작 코드입니다.
// 지금은 add / list 만 있습니다. sample/REQUEST.md 의 기능을 추가하는 것이 과제입니다.

const fs = require('fs')
const path = require('path')

const FILE = path.join(__dirname, 'todos.json')

function load() {
  if (!fs.existsSync(FILE)) return []
  try {
    return JSON.parse(fs.readFileSync(FILE, 'utf8'))
  } catch {
    return []
  }
}

function save(todos) {
  fs.writeFileSync(FILE, JSON.stringify(todos, null, 2))
}

function add(text) {
  if (!text || !text.trim()) {
    console.log('할 일 내용을 입력해 주세요.')
    return
  }
  const todos = load()
  todos.push({ text: text.trim(), done: false })
  save(todos)
  console.log(`추가했습니다: ${text.trim()}`)
}

function list() {
  const todos = load()
  if (todos.length === 0) {
    console.log('할 일이 없습니다')
    return
  }
  todos.forEach((t, i) => {
    console.log(`${i + 1}. ${t.text}`)
  })
}

function main() {
  const [cmd, ...rest] = process.argv.slice(2)
  const arg = rest.join(' ')

  switch (cmd) {
    case 'add':
      add(arg)
      break
    case 'list':
      list()
      break
    default:
      console.log('사용법: node todo.js <add|list> [내용]')
  }
}

if (require.main === module) main()

module.exports = { load, save, add, list }
