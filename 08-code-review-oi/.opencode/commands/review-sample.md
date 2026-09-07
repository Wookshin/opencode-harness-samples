---
description: gh 없이 도는 오프라인 데모 — sample/ 의 가짜 PR 로 전체 사이클을 보여줍니다
agent: review-lead
---

**오프라인 데모입니다.** `gh` 를 부르지 마세요. 네트워크도 쓰지 않습니다.

**작업 폴더는 `_workspace/pr-sample` 입니다.**

`sample/` 에 실제 PR 대신 쓸 재료가 들어 있습니다.

- 변경분: `sample/pr-sample.patch`
- 변경 후 원문: `sample/after/` · 변경 전 원문: `sample/before/`
- 가짜 DPImgr 트리: `sample/dpimgr/` (`dpimgr-dir.txt` 의 `SAMPLE` 매핑)

Phase 1 에서 `diff-scoper` 에게 이렇게 시키세요.

> 작업 폴더는 `_workspace/pr-sample` 입니다. `gh` 를 부르지 말고 아래 명령으로 수집하세요.
>
> ```
> node .opencode/skills/code-review-oi-pr/assets/collect.mjs --pr sample --ws _workspace/pr-sample \
>      --patch sample/pr-sample.patch --after sample/after --before sample/before \
>      --head feature/YOEDSMOV-multi-confirm --title "EDS 반출 다건 확정 + Lot 상태 검증 추가"
> ```
>
> 그다음 `_workspace/pr-sample/1-files.json` 을 읽고 `1-scope.md` 와 `1-hunks.md` 를 작성하세요.

SQL 리뷰어에게는 DPImgr 경로로 **`sample/dpimgr/`** 를 쓰라고 알려 주세요
(실환경이라면 `dpimgr-dir.txt` 의 저장소 매핑을 따릅니다).

나머지 Phase 2~4 는 평소대로 진행합니다. 결과는 `_workspace/pr-sample/review-sample.html` 입니다.

이 샘플의 변경분에는 **세 관점에 각각 걸리는 결함이 일부러 심어져 있습니다.**
셋 중 하나라도 "없음"이 나오면 그 리뷰어가 자기 관점을 놓친 것입니다. 그 사실을 보고에 적으세요.
