// 장바구니 합계 계산 — 연습용 샘플입니다.
// 일부러 테스트도 주석도 없고, 구조도 조금 지저분합니다.

function calc(items, c, isVip) {
  let t = 0
  for (let i = 0; i < items.length; i++) {
    if (items[i].qty > 0) {
      if (items[i].price > 0) {
        t = t + items[i].price * items[i].qty
      }
    }
  }

  if (c) {
    if (c.type == 'percent') {
      t = t - t * (c.value / 100)
    } else if (c.type == 'fixed') {
      t = t - c.value
    }
  }

  if (isVip) {
    t = t - t * 0.05
  }

  if (t < 3000) {
    t = t + 2500
  }

  return Math.round(t)
}

function fmt(n) {
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',') + '원'
}

module.exports = { calc, fmt }
