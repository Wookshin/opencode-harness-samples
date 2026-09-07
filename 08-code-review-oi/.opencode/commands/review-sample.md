---
description: gh 없이 도는 오프라인 데모 — sample/ 의 가짜 PR 로 전체 사이클을 보여줍니다
agent: review-lead
---

**오프라인 데모입니다.** `gh` 를 부르지 마세요. 네트워크도 쓰지 않습니다.

`sample/` 에 실제 PR 대신 쓸 재료가 들어 있습니다.

- 변경분: `sample/pr-sample.patch`
- 변경 후 원문: `sample/after/` · 변경 전 원문: `sample/before/`
- 가짜 DPImgr 트리: `sample/dpimgr/` (`dpimgr-dir.txt` 의 `SAMPLE` 매핑)

Phase 1 에서 `diff-scoper` 에게 이렇게 시키세요.

> `gh` 를 부르지 말고 `sample/pr-sample.patch` 를 `_workspace/1-diff.patch` 로 복사하고,
> `sample/after/` 와 `sample/before/` 를 각각 `_workspace/src/after/` · `_workspace/src/before/` 로
> 복사한 뒤 `1-scope.md` 와 `1-hunks.md` 를 작성하세요.
> PR 번호는 `sample`, base 는 `develop`, head 는 `feature/YOEDSMOV-multi-confirm` 으로 적으세요.

SQL 리뷰어에게는 DPImgr 경로로 **`sample/dpimgr/`** 를 쓰라고 알려 주세요
(실환경이라면 `dpimgr-dir.txt` 의 저장소 매핑을 따릅니다).

나머지 Phase 2~4 는 평소대로 진행합니다. 결과는 `_workspace/review-sample.html` 입니다.

이 샘플의 변경분에는 **세 관점에 각각 걸리는 결함이 일부러 심어져 있습니다.**
셋 중 하나라도 "없음"이 나오면 그 리뷰어가 자기 관점을 놓친 것입니다. 그 사실을 보고에 적으세요.
