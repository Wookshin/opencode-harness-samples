# `_workspace` — 단계 사이의 우편함

이 폴더는 **Phase 간 산출물이 오가는 곳**입니다.
에이전트끼리 직접 대화할 수 없으므로(각자 별도 세션에서 일합니다), **파일로 주고받습니다.**

## PR 하나에 폴더 하나

산출물은 `_workspace/` 에 평평하게 쌓이지 않고 **PR 번호별 폴더**로 나뉩니다.

```
_workspace/
├── README.md                    ← 이 파일. 유일하게 커밋되는 파일입니다
├── pr-1234/                     ← 세션 A 가 쓰는 곳
│   ├── STATUS.md
│   ├── 1-diff.patch
│   ├── 1-scope.md
│   ├── 1-hunks.md
│   ├── src/after/<경로>  ·  src/before/<경로>
│   ├── 2-review-refactor.md · 2-review-feature.md · 2-review-sql.md
│   ├── 3-verify.md
│   ├── 4-findings.json
│   └── review-1234.html         ★ 회의에서 여는 파일
├── pr-5678/                     ← 세션 B 가 쓰는 곳. A 와 절대 섞이지 않습니다
└── pr-1234.prev-20260907-1403/  ← 같은 PR 을 새로 돌릴 때 밀어 둔 이전 실행
```

**왜 나누나** — PR 두 개를 동시에 리뷰할 수 있어야 하기 때문입니다.
터미널 두 개에서 각각 `/review-pr 1234`, `/review-pr 5678` 을 돌리면 두 세션이 같이 돕니다.
폴더를 안 나누면 파일 이름이 전부 같아서 서로를 덮어쓰고, 최악의 경우
**`src/after/` 에 두 PR 의 원문이 섞여 리포트에 엉뚱한 코드가 실립니다.**

**`_workspace/` 루트에는 공유 파일을 만들지 않습니다.** 진행 상황 인덱스 같은 것을 하나 두면
그 파일이 다시 충돌 지점이 됩니다. `/status` 는 각 폴더의 `STATUS.md` 를 **읽기만** 해서
목록을 만듭니다.

## 누가 무엇을 쓰나

| 파일 | 누가 쓰나 | 내용 |
|---|---|---|
| `STATUS.md` | 오케스트레이터 | 진행판. 다른 사람은 손대지 않습니다 |
| `1-diff.patch` | collect.mjs | `gh pr diff` 원본 (UTF-8) |
| `1-meta.json` · `1-files.json` | collect.mjs | PR 메타데이터 · 파일별 상태(신규/변경/이름변경/이동/삭제) |
| `1-scope.md` | diff-scoper | 파일별 변경 유형·우선순위·SQL 변경 여부 |
| `1-hunks.md` | diff-scoper | **변경단위 표 (L1, L2 …)** — 세 리뷰어가 공유하는 ID |
| `src/after/<경로>` · `src/before/<경로>` | collect.mjs | 변경 파일 원문. HTML 이 이걸 읽어 코드를 그립니다 |
| `2-review-refactor.md` | review-refactor | 리팩토링 관점 지적 (`R###`) |
| `2-review-feature.md` | review-feature | 기능 관점 지적 (`F###`) |
| `2-review-sql.md` | review-sql | SQL 관점 지적 (`S###`) + SQL 본문 (`Q###`) |
| `3-verify.md` | review-verifier | 지적별 CONFIRMED / NEEDS-INFO / REJECTED |
| `4-findings.json` | report-builder | HTML 입력 (스키마 고정) |
| `review-<PR번호>.html` | 빌드 스크립트 | ★ **회의에서 여는 파일** |

## 규약

| 규칙 | 내용 |
|---|---|
| 작업 폴더 | `_workspace/pr-<번호>/` — 오케스트레이터가 Phase 0 에서 정해 프롬프트로 알려줍니다 |
| 경계 | 각 에이전트는 **받은 작업 폴더 안에서만** 읽고 씁니다. 옆 폴더는 남의 리뷰입니다 |
| 파일명 | `<Phase 번호>-<단계>[-<식별자>].<확장자>` |
| 쓰기 | 각 에이전트는 **자기 파일만** 씁니다. 남의 파일을 고치지 않습니다 |
| 읽기 | 다음 단계는 앞 단계 **파일을 직접 읽습니다.** 내용을 프롬프트로 받지 않습니다 |
| 진행판 | `STATUS.md` 는 오케스트레이터만 갱신합니다 |

## 왜 이렇게 하나

1. **컨텍스트 절약** — 패치 전문을 프롬프트에 붙이는 대신 경로 한 줄만 넘깁니다.
2. **감사 흔적** — 무슨 일이 있었는지 파일로 남습니다. 반려된 지적까지 남아 회의에서 확인됩니다.
3. **재개 가능** — 중간에 끊겨도 `/status` 로 어느 PR 이 어디까지 갔는지 보고 이어서 할 수 있습니다.
4. **병렬 안전** — 폴더가 PR 별로 갈리고, 한 폴더 안에서도 세 리뷰어가 각자 다른 파일에 씁니다.
5. **코드가 안 뭉개짐** — 원문이 `src/` 에 실물로 있으므로, HTML 을 만들 때 LLM 이
   코드를 옮겨 적지 않습니다. 스크립트가 이 파일들을 직접 읽습니다.

빌드 스크립트는 **`4-findings.json` 이 있는 폴더를 기준으로** 패치와 원문을 찾습니다.
그래서 작업 폴더가 어디로 바뀌든 인자만 맞으면 그대로 동작합니다.

## 권한과의 관계

이 하네스는 **아무도 소스를 못 고칩니다.** 하지만 자기 보고서는 써야 합니다.

```yaml
permission:
  edit:
    "*": deny              # 소스 코드는 못 고침
    "*_workspace/*": allow # 자기 보고서는 쓸 수 있음
```

> 패턴은 **git 저장소 루트 기준 상대 경로**와 매칭되고, `*` 는 `/` 를 넘어갑니다.
> 그래서 `_workspace/*` 가 아니라 `*_workspace/*` 로 써야 `08-code-review-oi/_workspace/...` 도 잡히고,
> `*` 가 `/` 를 넘으므로 `pr-1234/src/after/…` 같은 **하위 폴더까지 이 한 줄로 함께 열립니다.**

## 지우는 것은 사람이 합니다

에이전트에게는 `rm` 권한이 없습니다. 같은 PR 을 새로 돌릴 때도 **지우지 않고 옆으로 밀어냅니다.**

```
_workspace/pr-1234  →  _workspace/pr-1234.prev-20260907-1403
```

`collect.mjs` 가 해 줍니다. 동시에 도는 다른 세션의 폴더를 실수로 날릴 수 없게 하기 위해서입니다.
쌓인 것을 정리하려면 **사람이** 직접 지우세요.

```powershell
# PowerShell
Remove-Item -Recurse -Force _workspace\pr-1234           # 특정 PR 만
Remove-Item -Recurse -Force _workspace\pr-*.prev-*       # 밀어 둔 이전 실행만
Remove-Item -Recurse -Force _workspace\pr-*              # 전부 (다른 세션 확인하고!)
```

```bash
# bash / zsh
rm -rf _workspace/pr-1234
rm -rf _workspace/pr-*.prev-*
rm -rf _workspace/pr-*
```

산출물은 `.gitignore` 되어 커밋되지 않습니다. 이 README.md 는 규약 설명이라 유지됩니다.
