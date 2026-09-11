---
description: 진행 중인 모든 리팩토링 분석의 상태를 한눈에 보여 줍니다
agent: refactor-lead
---

```bash
python .opencode/skills/refactor-oi-scan/assets/ws.py --list
```

출력을 그대로 보여 주세요. 필요하면 각 폴더의 `STATUS.md` 를 `read` 로 열어 덧붙입니다.

폴더마다 **다음에 칠 명령**을 한 줄로 제안하세요.

| 마지막 Phase | 다음 |
|---|---|
| 1 수집·인덱스 | 대상 단위가 아직입니다 — `/scan-only <경로>` 로 이어서 |
| 1 대상 단위 확정 | `/refactor <경로>` 로 제안 단계부터 |
| 2 제안 · 3 검증 · 3 로드맵 | `/refactor <경로>` 로 이어서 |
| 4 리포트 완료 | HTML 을 여세요. 다시 만들려면 `/report-only <경로>` |

**읽기만 합니다.** 서브에이전트를 부르지 말고, 아무것도 만들거나 지우지 마세요.
