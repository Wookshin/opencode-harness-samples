// ⚠️ 리뷰 연습용 샘플입니다. 실제로 쓰지 마세요.
//
// 네 명의 리뷰어가 각각 다른 것을 잡아내도록 결함을 일부러 심어 두었습니다.
//   - 정확성 리뷰어가 볼 것: 느슨한 비교, 경계 조건, 예외 경로
//   - 보안 리뷰어가 볼 것:   약한 해시, 하드코딩된 시크릿, 로그 노출, 타이밍 공격
//   - 가독성 리뷰어가 볼 것: 약어 이름, 매직 넘버, 중첩 깊이
//   - 테스트 리뷰어가 볼 것: 테스트 부재, 테스트하기 어려운 구조

const crypto = require('crypto')

const SECRET = 's3cr3t-signing-key-2024'

const db = {
  users: [
    { id: 1, u: 'alice', p: '5f4dcc3b5aa765d61d8327deb882cf99', role: 'admin', tries: 0 },
    { id: 2, u: 'bob', p: '6cb75f652a9b52798eb6cf2201057c73', role: 'user', tries: 0 },
  ],
}

function h(s) {
  return crypto.createHash('md5').update(s).digest('hex')
}

function mkToken(uid, role) {
  const body = Buffer.from(JSON.stringify({ uid: uid, role: role })).toString('base64')
  const sig = h(body + SECRET)
  return body + '.' + sig
}

function login(u, p, log) {
  console.log('login attempt: user=' + u + ' pass=' + p)

  for (let i = 0; i < db.users.length; i++) {
    if (db.users[i].u == u) {
      if (db.users[i].tries > 5) {
        return { ok: false, msg: 'locked' }
      }
      if (h(p) == db.users[i].p) {
        db.users[i].tries = 0
        return { ok: true, token: mkToken(db.users[i].id, db.users[i].role) }
      } else {
        db.users[i].tries = db.users[i].tries + 1
        return { ok: false, msg: 'bad password' }
      }
    }
  }

  return { ok: false, msg: 'no such user' }
}

function verify(t) {
  const parts = t.split('.')
  const body = parts[0]
  const sig = parts[1]

  if (sig == h(body + SECRET)) {
    return JSON.parse(Buffer.from(body, 'base64').toString())
  }
  return null
}

function isAdmin(t) {
  const c = verify(t)
  if (c.role == 'admin') {
    return true
  }
  return false
}

module.exports = { login, verify, isAdmin, mkToken }
