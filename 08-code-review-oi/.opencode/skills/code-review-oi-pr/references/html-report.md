# HTML 리포트 — findings.json 스키마와 빌드

**HTML 을 직접 쓰지 마세요.** `4-findings.json` 만 만들면 스크립트가 렌더링합니다.

이렇게 나눈 이유는 하나입니다. **코드가 뭉개지지 않게 하려고.**
변경 전/후 코드와 라인 색칠은 스크립트가 `1-diff.patch` 와 `src/{before,after}/` 원문에서
직접 계산합니다. LLM 이 코드를 JSON 에 옮겨 적지 않으므로 틀릴 여지가 없습니다.

## 빌드

```bash
python .opencode/skills/code-review-oi-pr/assets/build-report.py \
     _workspace/pr-1234/4-findings.json \
     _workspace/pr-1234/review-1234.html
```

| 인자 | 필수 | 설명 |
|---|---|---|
| 1 | ● | findings.json 경로 |
| 2 | ● | 출력 HTML 경로 |
| 3 | | 패치 경로. 생략하면 findings.json 과 같은 폴더의 `1-diff.patch` |

> **`python` 이 안 먹히면** Windows 는 `py`, 리눅스·맥은 `python3` 로 부르세요.
> 셋 중 하나는 됩니다. 한 번 확인해 두면 그다음부터는 그것만 쓰면 됩니다.


**기준은 findings.json 이 있는 폴더입니다.** 패치도 `src/before/`·`src/after/` 도 거기서 찾습니다.
그래서 작업 폴더가 `pr-1234` 든 `pr-5678` 이든 인자만 맞으면 그대로 동작합니다 —
스크립트는 작업 폴더 이름을 전혀 모릅니다.
스크립트는 **스키마를 검증**하고, 어긋나면 무엇이 잘못됐는지 출력하며 exit 1 합니다.
실패하면 JSON 을 고쳐 다시 실행하세요. **HTML 을 손으로 고치지 마세요.**

---

## 스키마

```jsonc
{
  "meta": {
    "prNumber":    "1234",              // 필수. 출력 파일명·localStorage 키에 쓰입니다
    "title":       "EDS 반출 확정 시 Lot 상태 검증 추가",   // 필수
    "author":      "sw1027.chae",
    "url":         "https://github.com/…/pull/1234",
    "baseRef":     "develop",           // 필수
    "headRef":     "feature/YOEDSMOV-lot-validate",
    "headSha":     "a1b2c3d",
    "generatedAt": "2026-09-07T14:03:00+09:00",  // 필수
    "verdict":     "FAIL",              // 필수. PASS | FAIL
    "reviewers": { "refactor": "PASS", "feature": "FAIL", "sql": "FAIL" }
  },

  "overview": {                       // 필수 — 리포트 맨 위에 실립니다
    "narrative": "이 PR 은 EDS 반출 확정을 단건에서 다건으로 바꿉니다.\n확정 전에 …",
    // ↑ 3~5줄. 줄바꿈(\n)을 그대로 두세요 — 리포트가 문단으로 끊어 렌더합니다.
    //   `**굵게**` 를 쓸 수 있습니다. 출처: 1-scope.md 의 「이 PR 이 하는 일」
    "highlights": [                   // 선택 — 2~4개
      "Confirm() 이 선택 목록 반복 처리로 전면 재작성됨 (L5)"
    ]
  },

  "assessment": {                     // 필수 — 판정 배지 옆, 개요 오른쪽에 실립니다
    "conclusion": "**이대로 병합하면 안 됩니다.**\n가장 큰 문제는 …",  // 필수. 3~5줄
    "rechecks":   ["lot.selectMcLotWithLine 등록 여부와 배포 순서 (S003)"],  // 없으면 []
    "agenda":     ["R001", "F001", "S003"],   // 회의에서 볼 순서. findings[].id 여야 합니다
    "goodPoints": ["선택 행 수집을 별도 함수로 분리한 것"]                  // 선택
  },
  // 출처: 3-assessment.md (오케스트레이터가 씁니다)

  "files": [                            // 필수. 변경된 파일. priority 오름차순으로 표시됩니다
    {
      "path":       "YOEDSMOV/YOEDSMOV.xaml.cs",   // 필수. 저장소 기준 경로
      "changeType": "변경",              // 필수. 신규 | 변경 | 삭제 | 이름변경 | 이동
                                        //   (added/modified/deleted/renamed/moved 도 받아 한글로 바꿉니다)
      "priority":   1,                  // 필수. .xaml.cs = 1, 그 외 = 2
      "hasSql":     false,
      "renamedFrom": null,              // renamed / moved 일 때만
      "beforeFile": "src/before/YOEDSMOV/YOEDSMOV.xaml.cs",  // findings.json 이 있는 폴더 기준
      "afterFile":  "src/after/YOEDSMOV/YOEDSMOV.xaml.cs"    // 없으면 원문 임베드 생략
    }
  ],

  "units": [                            // 필수. 1-hunks.md 의 변경단위 표와 1:1
    {
      "id":          "L1",              // 필수
      "file":        "YOEDSMOV/YOEDSMOV.xaml.cs",  // 필수. files[].path 중 하나
      "kind":        "신규",             // 필수. 신규 | 변경 | 삭제 | 이름변경 | 이동 (영문도 허용)
      "afterLines":  [210, 248],        // after 원문 기준 [시작, 끝]. 삭제면 null
      "beforeLines": null,              // before 원문 기준. 신규면 null
      "summary":     "반출 확정 전 Lot 상태 검사 추가"   // 필수
    }
  ],

  "findings": [                         // 필수(빈 배열 허용)
    {
      "id":          "R001",            // 필수. R### | F### | S###
      "perspective": "refactor",        // 필수. refactor | feature | sql
      "severity":    "BLOCKER",         // 필수. BLOCKER | MAJOR | MINOR
      "verdict":     "CONFIRMED",       // 필수. CONFIRMED | NEEDS-INFO
      "unitId":      "L2",              // 필수. units[].id 중 하나
      "file":        "YOEDSMOV/YOEDSMOV.xaml.cs",  // 필수
      "line":        96,                // 필수. after 기준 라인 (삭제 지적이면 before 기준)
      "title":       "bool 반환 함수가 Is 로 시작하지 않는다",   // 필수
      "problem":     "…",               // 필수. BLOCKER 면 결과 시나리오 포함
      "basis":       "규칙 1-4",         // 필수. 규칙/체크리스트 번호
      "before":      "private bool CheckLot(string lotId)",
      "after":       "private bool CheckLot(string lotId)",
      "suggestion":  "private bool IsValidLotStatus(string lotId)",  // 필수
      "checkpoints": "호출부 3곳(96,142,208) 조건이 모두 뒤집혀야 합니다"
    }
  ],

  "simpleChanges": [                    // 단순 리팩토링 요약. 없으면 []
    { "unitId": "L7", "content": "tmpList → lotIdList (3곳)", "issue": "없음" }
  ],

  "sql": [                              // SQL 절. 없으면 []
    {
      "id":       "S001",               // 필수
      "callType": "DPICALL",            // 필수. DPICALL | SQLEXEC
      "sqlId":    "lot.selectMcLot",    // DPICALL 이면 필수
      "sourcePath": "D:\\Git\\DPImgr\\…\\lot\\lot.xml:142",   // 본문을 찾은 위치
      "unitId":   "L3",
      "body":     "SELECT /*QR…*/ …",   // 필수. 찾은 SQL 본문
      "tuningPoints": [                 // 없으면 []
        "lot_id 는 인덱스 선두 컬럼이지만 TRIM() 으로 감싸 인덱스를 타지 못합니다"
      ]
    }
  ],

  "rejected": [                         // 검증에서 반려된 지적. 감사 흔적으로 남깁니다
    {
      "id": "F009", "perspective": "feature",
      "title": "…",
      "reason": "인용한 라인 312 는 변경단위 표에 없습니다 (기존 코드)"
    }
  ],

  "unknowns": [                         // 확인 못 한 것. 없으면 []
    "lot.selectMcLot 본문 — dpimgr-dir.txt 에 ZZ_SWP 매핑 없음"
  ]
}
```

## 만들 때 주의

| 주의 | 이유 |
|---|---|
| `overview.narrative` · `assessment.conclusion` 은 **필수** | 없으면 exit 1. 회의 자료의 첫 화면이 비어 버립니다 |
| 개요·평가의 **줄바꿈을 살린다** | 리포트가 `\n` 을 문단 경계로 씁니다. 한 줄로 합치면 벽처럼 보입니다 |
| **백틱과 `**굵게**` 를 그대로 둔다** | 리포트가 `` `식별자` `` 를 코드 칩으로, `**…**` 를 굵게 렌더합니다. 지우지 마세요 |
| `assessment.agenda` 는 실재하는 지적 ID | 없는 ID 면 exit 1. 클릭 시 이동하는 링크가 됩니다 |
| `REJECTED` 는 `findings` 에 넣지 않고 `rejected` 로 뺀다 | 본문에 실리면 회의에서 시간을 낭비합니다 |
| `unitId` 는 `units[].id` 에 실재해야 한다 | 없으면 스크립트가 exit 1 |
| `file` 은 `files[].path` 와 **글자 그대로** 같아야 한다 | 목차 연결이 끊어집니다 |
| 코드 원문을 `problem` 에 길게 붙이지 않는다 | 원문은 스크립트가 임베드합니다 |
| `severity` 는 검증 결과(강등 포함)를 반영한 **최종값** | 3-verify.md 가 강등한 것을 그대로 씁니다 |

## 변경 유형 어휘

표시는 **한글 다섯 가지**로 고정입니다. 영문(git 어휘)으로 넣어도 `build-report.py` 가 바꿔 줍니다.

| 한글 | 영문 | 뜻 |
|---|---|---|
| `신규` | `added` | before 원문에 없던 코드 |
| `변경` | `modified` | 있던 것이 고쳐짐 — **리네이밍·시그니처 변경도 여기** |
| `삭제` | `deleted` | after 에 없어짐 |
| `이름변경` | `renamed` | 이름만 바뀌고 내용은 같음 |
| `이동` | `moved` | 위치만 바뀜 |

`단순`(simpleChanges)은 **유형이 아닙니다.** "판단이 필요 없는 변경"이라는 표시라
리포트에서 점선 칩으로 다르게 그려집니다. 리포트 안에 이 표와 같은 범례가 접이식으로 들어갑니다.

## HTML 이 제공하는 것 (회의에서 쓰는 기능)

**요약이 먼저, 코드는 나중입니다.** 페이지를 열면 위에서부터 이 순서입니다.

0. **전체 변경사항 요약 · 종합 평가** — 결론부터. 이 PR 이 뭘 하는지와, 그래서 어떤지
1. **리뷰 체크리스트** — 지적 전체를 심각도 순으로 한 줄씩. BLOCKER 부터 묶여 나오고,
   각 행에 지적 한 줄 · 근거 · 위치 · 결정 상태가 있습니다. **행을 누르면 상세로 이동합니다.**
2. **변경 요약** — 변경단위별로 "무엇이 바뀌었나"(`units[].summary`)와 지적 건수.
   코드를 안 읽어도 이 PR 이 뭘 했는지 파악됩니다.
3. 그 아래에 파일 → 변경단위 → 지적 카드. **코드 블록은 기본으로 접혀 있습니다.**

그래서 `units[].summary` 와 `findings[].title` 이 이 리포트의 얼굴입니다.
**한 줄로 읽히게 쓰세요.** 요약이 부실하면 팀원이 결국 코드를 다 읽어야 합니다.

그 밖에:

- **C# · SQL 문법 하이라이트** — 외부 라이브러리 없이 내장. `$@"…"` 축자 문자열 안의
  여러 줄 SQL 도 SQL 키워드로 물듭니다 (SqlManager 의 인라인 쿼리가 그대로 읽힙니다)
- 검색 — 지적 내용·파일·근거. 체크리스트와 본문에 **동시에** 걸립니다
- **보기 전환** — 코드 변경을 `위아래`(통합) 로 볼지 `좌우`(나란히) 로 볼지. 선택은 브라우저에 남습니다
- 지적마다 **[합의] [보류] [반려]** 선택과 메모 → 브라우저에 저장
  (`localStorage`, 키 = `oi-review-<PR번호>`. **PR 별로 갈리므로 두 리포트를 같이 열어도 안 섞입니다**)
- 상단에 "결정 12 / 27" 진행 표시, 체크리스트에도 결정 상태가 실시간 반영
- 상단 `리뷰 범위` 한 줄에 변경 파일·변경단위·지적·심각도별 건수
- 회의 결과를 마크다운 / JSON 으로 복사·저장
- 지적 카드의 **[코드 보기]** 로 해당 변경단위 코드만 펼치기, 상단 버튼으로 전부 펼치기/접기
- **테마 전환** — `테마: 시스템 → 라이트 → 다크` 버튼. 고른 값은 브라우저에 남고
  (`oi-review-theme`, 결정 저장소와 분리) 시스템 설정을 이깁니다
- 인쇄(`Ctrl+P`) 시 필터·버튼이 사라지고 전부 펼쳐진 상태로 출력.
  **화면이 다크여도 종이는 항상 밝게** 나갑니다
- **외부 요청 0** — 폐쇄망에서 그냥 열립니다
