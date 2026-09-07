# HTML 리포트 — findings.json 스키마와 빌드

**HTML 을 직접 쓰지 마세요.** `4-findings.json` 만 만들면 스크립트가 렌더링합니다.

이렇게 나눈 이유는 하나입니다. **코드가 뭉개지지 않게 하려고.**
변경 전/후 코드와 라인 색칠은 스크립트가 `1-diff.patch` 와 `src/{before,after}/` 원문에서
직접 계산합니다. LLM 이 코드를 JSON 에 옮겨 적지 않으므로 틀릴 여지가 없습니다.

## 빌드

```bash
node .opencode/skills/code-review-oi-pr/assets/build-report.mjs \
     _workspace/pr-1234/4-findings.json \
     _workspace/pr-1234/review-1234.html
```

| 인자 | 필수 | 설명 |
|---|---|---|
| 1 | ● | findings.json 경로 |
| 2 | ● | 출력 HTML 경로 |
| 3 | | 패치 경로. 생략하면 findings.json 과 같은 폴더의 `1-diff.patch` |

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

  "files": [                            // 필수. 변경된 파일. priority 오름차순으로 표시됩니다
    {
      "path":       "YOEDSMOV/YOEDSMOV.xaml.cs",   // 필수. 저장소 기준 경로
      "changeType": "modified",         // 필수. added | modified | renamed | moved | deleted
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
      "kind":        "신규",             // 필수. 신규 | 변경 | 삭제 | 이름변경 | 이동
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
| `REJECTED` 는 `findings` 에 넣지 않고 `rejected` 로 뺀다 | 본문에 실리면 회의에서 시간을 낭비합니다 |
| `unitId` 는 `units[].id` 에 실재해야 한다 | 없으면 스크립트가 exit 1 |
| `file` 은 `files[].path` 와 **글자 그대로** 같아야 한다 | 목차 연결이 끊어집니다 |
| 코드 원문을 `problem` 에 길게 붙이지 않는다 | 원문은 스크립트가 임베드합니다 |
| `severity` 는 검증 결과(강등 포함)를 반영한 **최종값** | 3-verify.md 가 강등한 것을 그대로 씁니다 |

## HTML 이 제공하는 것 (회의에서 쓰는 기능)

**요약이 먼저, 코드는 나중입니다.** 페이지를 열면 위에서부터 이 순서입니다.

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
- 관점 3종 · 심각도 3종 토글 필터, 전체 검색 — 체크리스트와 본문에 **동시에** 걸립니다
- 지적마다 **[합의] [보류] [반려]** 선택과 메모 → 브라우저에 저장
  (`localStorage`, 키 = `oi-review-<PR번호>`. **PR 별로 갈리므로 두 리포트를 같이 열어도 안 섞입니다**)
- 상단에 "결정 12 / 27" 진행 표시, 체크리스트에도 결정 상태가 실시간 반영
- 회의 결과를 마크다운 / JSON 으로 복사·저장
- 지적 카드의 **[코드 보기]** 로 해당 변경단위 코드만 펼치기, 상단 버튼으로 전부 펼치기/접기
- 인쇄(`Ctrl+P`) 시 필터·버튼이 사라지고 전부 펼쳐진 상태로 출력
- **외부 요청 0** — 폐쇄망에서 그냥 열립니다
