---
name: code-review-oi-pr
description: PR 번호를 받아 리팩토링·기능·SQL 세 관점으로 동시에 코드리뷰하고, 팀원이 모여서 볼 수 있는 단일 HTML 리포트를 만듭니다. 오프라인 코드리뷰 회의를 준비할 때, PR 번호와 함께 리뷰 요청을 받았을 때 이 스킬을 먼저 검토하세요.
---

# OI 코드리뷰 (PR 단위)

PR 하나를 **세 관점이 동시에** 리뷰하고, 지적을 **검증으로 걸러낸 뒤**,
팀 오프라인 리뷰 회의에서 쓸 **단일 HTML 파일**을 만듭니다.

## 언제 쓰나

- 팀원끼리 모여서 하는 **코드리뷰 회의를 준비**할 때 (이 스킬의 본래 목적)
- PR 번호를 받아 develop 대비 변경분 전체를 훑어야 할 때
- SQL 이 바뀐 PR — DPICALL 본문까지 따라가 튜닝포인트를 봐야 할 때

혼자 잠깐 보는 리뷰라면 이 하네스는 과합니다. **회의 자료가 필요할 때** 쓰세요.

## 어떻게 실행하나

이 스킬은 혼자 동작하지 않습니다. **`08-code-review-oi` 하네스의 커맨드로 실행**합니다.

```bash
cd 08-code-review-oi

opencode run "/review-pr 1234"     # 전체 사이클 → _workspace/pr-1234/review-1234.html
opencode run "/scope-only 1234"    # Phase 1 만 — 변경단위 분류가 맞는지 먼저 확인
opencode run "/report-only 1234"   # 리뷰는 그대로 두고 HTML 만 다시 생성
opencode run "/review-sample"      # gh 없이 도는 오프라인 데모
opencode run "/status"             # 진행 중인 모든 PR 리뷰의 상태
```

실 PR 에 처음 적용할 때는 **`/scope-only` 부터** 돌리세요.
변경단위 분류가 틀리면 뒤의 세 명이 전부 틀린 것을 봅니다.

## 무엇이 만들어지나

**PR 하나에 폴더 하나**입니다. 그래서 두 PR 을 동시에 리뷰해도 섞이지 않습니다.

```
_workspace/pr-1234/
├── STATUS.md                 진행판
├── 1-diff.patch              gh pr diff 원본
├── 1-scope.md                파일별 변경 유형·우선순위·SQL 변경 여부
├── 1-hunks.md                변경단위 표 (L1, L2 … ← 세 리뷰어가 공유하는 ID)
├── src/{before,after}/…      변경 파일 원문 (HTML 임베드용)
├── 2-review-refactor.md      리팩토링 관점
├── 2-review-feature.md       기능 관점
├── 2-review-sql.md           SQL 관점
├── 3-verify.md               지적별 CONFIRMED / NEEDS-INFO / REJECTED
├── 4-findings.json           HTML 입력 (스키마 고정)
└── review-1234.html          ★ 회의에서 여는 파일
```

터미널 두 개로 `/review-pr 1234` 와 `/review-pr 5678` 을 동시에 돌리면
`pr-1234/` 와 `pr-5678/` 이 각각 채워집니다. `/status` 로 둘 다 한눈에 봅니다.

## 리뷰 원칙 (세 관점 공통)

- **변경된 것만 봅니다.** `1-hunks.md` 표에 없는 라인은 리뷰 대상이 아닙니다.
- **변경 전 코드를 신규로 오인하지 않습니다.** 리네이밍·이동·삭제는 `신규`가 아니라 `변경`입니다.
  이 판정은 Phase 1 에서 확정되며, 리뷰어가 다시 판단하지 않습니다.
- **`.xaml.cs` 의 변경 로직이 최우선**입니다.
- **추측으로 지적하지 않습니다.** 원문을 읽고 근거를 답니다. 검증 단계에서 반려됩니다.
- **단순 리팩토링**(변수명 변경, 미사용 코드 삭제)은 한 줄로 요약하되, 이상점이 있으면 지적합니다.

## 참조 문서 (필요할 때만 읽으세요)

| 문서 | 누가 읽나 | 내용 |
|---|---|---|
| [references/naming-rules.md](references/naming-rules.md) | 리팩토링 리뷰어 | 함수·VO·변수·상수·테스트 명명 규칙 8종과 판정 예시 |
| [references/manager-patterns.md](references/manager-patterns.md) | 기능 리뷰어 | SqlManager·RuleManager 사용 규범과 점검 체크리스트 |
| [references/read-sql.md](references/read-sql.md) | SQL 리뷰어 | DPICALL SQL 본문을 DPImgr 저장소에서 찾아 읽는 절차 |
| [references/review-format.md](references/review-format.md) | 세 리뷰어 전원 | 공통 출력 형식과 심각도 기준 |
| [references/html-report.md](references/html-report.md) | 리포트 담당 | findings.json 스키마와 빌드 스크립트 사용법 |
| [dpimgr-dir.txt](dpimgr-dir.txt) | SQL 리뷰어 | 저장소 → DPImgr 경로 매핑. **팀 환경에 맞게 고쳐 쓰는 파일** |

전문을 한꺼번에 읽지 마세요. 각 리뷰어는 **자기 문서 하나만** 읽습니다.
