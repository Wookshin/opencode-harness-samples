# `_workspace` — 단계 사이의 우편함

이 폴더는 **Phase 간 산출물이 오가는 곳**입니다.
에이전트끼리 직접 대화할 수 없으므로(각자 별도 세션에서 일합니다), **파일로 주고받습니다.**

## 이 하네스가 쌓는 것

| 파일 | 누가 쓰나 | 내용 |
|---|---|---|
| `STATUS.md` | 오케스트레이터 | 진행판. 다른 사람은 손대지 않습니다 |
| `1-diff.patch` | diff-scoper | `gh pr diff` 원본 |
| `1-scope.md` | diff-scoper | 파일별 변경 유형·우선순위·SQL 변경 여부 |
| `1-hunks.md` | diff-scoper | **변경단위 표 (L1, L2 …)** — 세 리뷰어가 공유하는 ID |
| `src/after/<경로>` · `src/before/<경로>` | diff-scoper | 변경 파일 원문. HTML 이 이걸 읽어 코드를 그립니다 |
| `2-review-refactor.md` | review-refactor | 리팩토링 관점 지적 (`R###`) |
| `2-review-feature.md` | review-feature | 기능 관점 지적 (`F###`) |
| `2-review-sql.md` | review-sql | SQL 관점 지적 (`S###`) + SQL 본문 (`Q###`) |
| `3-verify.md` | review-verifier | 지적별 CONFIRMED / NEEDS-INFO / REJECTED |
| `4-findings.json` | report-builder | HTML 입력 (스키마 고정) |
| `review-<PR번호>.html` | 빌드 스크립트 | ★ **회의에서 여는 파일** |

## 규약

| 규칙 | 내용 |
|---|---|
| 파일명 | `<Phase 번호>-<단계>[-<식별자>].<확장자>` |
| 쓰기 | 각 에이전트는 **자기 파일만** 씁니다. 남의 파일을 고치지 않습니다 |
| 읽기 | 다음 단계는 앞 단계 **파일을 직접 읽습니다.** 내용을 프롬프트로 받지 않습니다 |
| 진행판 | `STATUS.md` 는 오케스트레이터만 갱신합니다 |

## 왜 이렇게 하나

1. **컨텍스트 절약** — 패치 전문을 프롬프트에 붙이는 대신 경로 한 줄만 넘깁니다.
2. **감사 흔적** — 무슨 일이 있었는지 파일로 남습니다. 반려된 지적까지 남아 회의에서 확인됩니다.
3. **재개 가능** — 중간에 끊겨도 `/status` 로 이어서 할 수 있습니다.
4. **병렬 안전** — 세 리뷰어가 각자 다른 파일에 쓰므로 충돌하지 않습니다.
5. **코드가 안 뭉개짐** — 원문이 `src/` 에 실물로 있으므로, HTML 을 만들 때 LLM 이
   코드를 옮겨 적지 않습니다. 스크립트가 이 파일들을 직접 읽습니다.

## 권한과의 관계

이 하네스는 **아무도 소스를 못 고칩니다.** 하지만 자기 보고서는 써야 합니다.

```yaml
permission:
  edit:
    "*": deny              # 소스 코드는 못 고침
    "*_workspace/*": allow # 자기 보고서는 쓸 수 있음
```

> 패턴은 **git 저장소 루트 기준 상대 경로**와 매칭되고, `*` 는 `/` 를 넘어갑니다.
> 그래서 `_workspace/*` 가 아니라 `*_workspace/*` 로 써야 `08-code-review-oi/_workspace/...` 도 잡힙니다.
> `src/after/...` 같은 하위 폴더도 이 한 줄로 함께 열립니다.

## 정리하기

산출물은 `.gitignore` 되어 커밋되지 않습니다. 처음 상태로 되돌리려면:

```bash
rm -rf _workspace/src
rm -f  _workspace/*.md _workspace/*.json _workspace/*.patch _workspace/*.html
git checkout -- _workspace/README.md
```

(이 README.md 는 규약 설명이라 유지됩니다)
