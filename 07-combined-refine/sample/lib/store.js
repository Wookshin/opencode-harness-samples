const fs = require('fs')

class Store {
  constructor(file, max) {
    this.file = file
    this.max = max
  }

  _read() {
    try {
      const data = JSON.parse(fs.readFileSync(this.file, 'utf8'))
      return Array.isArray(data) ? data : []
    } catch {
      // 파일이 없거나 깨졌으면 빈 큐로 시작합니다
      return []
    }
  }

  _write(items) {
    fs.writeFileSync(this.file, JSON.stringify(items, null, 2))
  }

  push(text) {
    const items = this._read()
    items.push(text)
    let dropped = null
    while (items.length > this.max) dropped = items.shift()
    this._write(items)
    return { dropped }
  }

  shift() {
    const items = this._read()
    const item = items.shift()
    if (item !== undefined) this._write(items)
    return item
  }

  head() {
    return this._read()[0]
  }

  all() {
    return this._read()
  }

  clear() {
    this._write([])
  }
}

module.exports = { Store }
