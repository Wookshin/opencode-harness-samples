---
description: 스킬에 딸린 가짜 WPF 화면으로 전체 사이클을 보여 주는 오프라인 데모 — 네트워크도 mapper 저장소도 필요 없습니다
agent: refactor-lead
---

스킬에 딸린 샘플로 전체 사이클을 돕니다. **네트워크도 실제 mapper 저장소도 쓰지 않습니다.**

- 작업 폴더: `_workspace/scan-sample`
- 샘플 경로: `.opencode/skills/refactor-oi-scan/sample`

Phase 1 에서 `code-scoper` 에게 **이 명령을 그대로** 주세요.

```bash
python .opencode/skills/refactor-oi-scan/assets/collect.py \
    --path .opencode/skills/refactor-oi-scan/sample/src \
    --ws _workspace/scan-sample \
    --mapper .opencode/skills/refactor-oi-scan/sample/mapper
python .opencode/skills/refactor-oi-scan/assets/index.py --ws _workspace/scan-sample
```

나머지는 `/refactor` 와 같습니다. 결과물은 `_workspace/scan-sample/refactor-sample.html`.

## 이 샘플에는 결함이 일부러 심어져 있습니다

네 관점에 각각 걸리는 것이 있고, **미참조로 오인하기 쉬운 WPF 함정**도 함께 있습니다.

| 심어 둔 것 | 어느 관점 |
|---|---|
| 안 쓰는 필드·메서드·`using`, 복사해 만든 조회 메서드 | 중복·미사용 |
| `bool` 인데 `Is` 로 시작하지 않고 이름이 동작과 반대인 함수 | 컨벤션 |
| 64줄짜리 메서드, 반복문 안 DB 왕복 | 구조 |
| 문자열 연결 인라인 SQL, 미사용 SQL ID, 인덱스를 막는 `TRIM()` | SQL |
| **XAML 핸들러·컨버터·바인딩·의존 속성** | **미참조로 지적하면 검증에서 `V-4` 반려** |

**어느 관점이든 "없음" 이라고 하면 그 사실을 사용자에게 알리세요.** 뭔가 잘못된 것입니다.

리포트가 나오면 이렇게 보라고 안내하세요.

1. 맨 위 **개선 로드맵**부터 — "그래서 뭐부터" 가 답이 되는지
2. **`먼저 · 비용 작음`** 칩을 눌러 이번 주에 할 일만 남겨 보기
3. 맨 아래 **반려된 제안** 을 펴서 — WPF 오탐이 어떻게 걸러졌는지

> 모델을 부르지 않고 스크립트만 확인하려면
> `python .opencode/skills/refactor-oi-scan/assets/ws.py --selftest` 를 쓰세요.
