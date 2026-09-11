# HTML 리포트 — findings.json 스키마와 빌드

**HTML 을 직접 쓰지 마세요.** `4-findings.json` 만 만들면 스크립트가 렌더링합니다.

이렇게 나눈 이유는 하나입니다. **코드가 뭉개지지 않게 하려고.**
리포트에 실리는 현재 코드는 `build-report.py` 가 `src/` 원문에서 직접 잘라 씁니다.
LLM 이 코드를 JSON 에 옮겨 적지 않으므로 틀릴 여지가 없습니다.

같은 이유로 **기계가 센 숫자**(미참조 N · 중복 N쌍 · 미사용 SQL N)도 LLM 을 거치지 않습니다.
`build-report.py` 가 `1-index.json` 에서 직접 읽어 싣습니다. `indexSummary` 를 쓰지 마세요.

> **예외는 `suggestion` 하나입니다.** 제안 코드는 본래 원문에 없으므로 JSON 에 들어올
> 수밖에 없습니다. 리포트가 그 칸을 「제안」으로 따로 표시해 원문과 섞이지 않게 합니다.

## 빌드

```bash
python .opencode/skills/refactor-oi-scan/assets/build-report.py \
     _workspace/scan-YOEDSMOV/4-findings.json \
     _workspace/scan-YOEDSMOV/refactor-YOEDSMOV.html
```

| 인자 | 필수 | 설명 |
|---|---|---|
| 1 | ● | findings.json 경로 |
| 2 | ● | 출력 HTML 경로 |
| 3 | | 인덱스 경로. 생략하면 findings.json 과 같은 폴더의 `1-index.json` |

> **`python` 이 안 먹히면** Windows 는 `py`, 리눅스·맥은 `python3` 로 부르세요.

**기준은 findings.json 이 있는 폴더입니다.** 원문(`src/` · `src-sql/`)도 거기서 찾습니다.
그래서 작업 폴더가 `scan-YOEDSMOV` 든 `scan-YOSTKMGR` 든 인자만 맞으면 그대로 동작합니다 —
스크립트는 작업 폴더 이름을 전혀 모릅니다.

스크립트는 **스키마를 검증**하고, 어긋나면 무엇이 잘못됐는지 출력하며 exit 1 합니다.
실패하면 JSON 을 고쳐 다시 실행하세요. **HTML 을 손으로 고치지 마세요.**

```
✗ findings.json 검증 실패 — 2건
  · findings[3] (H004): unitId "U99" 가 units 에 없습니다
  · findings[7] (D002): "effort" 는 작음 | 보통 | 큼 중 하나여야 합니다 (받은 값: 중간)
```

---

## 스키마

```jsonc
{
  "meta": {
    "target":      "YOEDSMOV",           // 필수. 분석한 경로
    "slug":        "YOEDSMOV",           // 필수. 작업 폴더 이름과 localStorage 키에 쓰입니다
    "title":       "YOEDSMOV — EDS 반출 화면",  // 필수
    "generatedAt": "2026-09-11T14:03:00+09:00"  // 필수
  },

  "overview": {                       // 필수 — 리포트 맨 위에 실립니다
    "narrative": "EDS 반출 화면 한 벌입니다.\n…",
    // ↑ 3~5줄. 줄바꿈(\n)을 그대로 두세요 — 리포트가 문단으로 끊어 렌더합니다.
    //   `**굵게**` 와 `` `백틱` `` 을 쓸 수 있습니다.
    //   출처: 1-scope.md 의 「이 코드가 하는 일」
    "highlights": [                   // 선택 — 2~4개
      "`Confirm()` 하나가 64줄 — 조회·검증·저장·화면 갱신을 모두 합니다 (U5)"
    ]
  },

  "roadmap": {                        // 필수 — 개요 아래에 실립니다
    "diagnosis": "**구조 하나만 손대면 나머지가 따라옵니다.**\n…",  // 필수. 3~5줄
    "order": [                        // 손대는 순서. 번호 목록으로 그려집니다
      "죽은 코드부터 지웁니다 … — H001·H003"
    ],
    "batches": [                      // 묶어서 하면 좋은 것. 없으면 []
      "`tmpList` 이름 정리는 H002 와 같은 커밋에서 하면 리뷰가 한 번으로 끝납니다"
    ],
    "leaveAlone": [                   // ★ 지금은 두는 게 나은 것. 비우지 마세요
      "`Bind()` 는 `public` 이라 다른 화면이 쓸 수 있습니다. 저장소 전체를 훑기 전에는 지우지 마세요"
    ]
  },
  // 출처: 3-roadmap.md (오케스트레이터가 직접 씁니다)

  "files": [                            // 필수. 분석한 파일. priority 오름차순으로 표시
    {
      "path":       "YOEDSMOV/YOEDSMOV.xaml.cs",  // 필수. 대상 경로 기준 상대 경로
      "kind":       "화면",              // 화면 | 공통 | 매퍼 (생략하면 확장자로 정합니다)
      "priority":   1,                  // .xaml · .xaml.cs = 1, 그 외 = 2 (생략 가능)
      "sourceFile": "src/YOEDSMOV/YOEDSMOV.xaml.cs"
      //            ↑ findings.json 이 있는 폴더 기준.
      //              생략하면 "src/" + path 로 봅니다.
      //              mapper 는 "src-sql/lot/lot.xml" 처럼 적으세요.
    }
  ],

  "units": [                            // 필수. 1-units.md 의 대상 단위 표와 1:1
    {
      "id":      "U5",                  // 필수
      "file":    "YOEDSMOV/YOEDSMOV.xaml.cs",  // 필수. files[].path 중 하나
      "kind":    "메서드",               // 필수. 클래스|메서드|프로퍼티|필드|이벤트 핸들러|XAML|SQL
      "lines":   [150, 213],            // 필수. 원문 기준 [시작, 끝]
      "summary": "`Confirm()` — 선택 수집·검증·저장을 한 덩어리로 합니다 (64줄)"  // 필수
    }
  ],

  "findings": [                         // 필수(빈 배열 허용)
    {
      "id":          "N001",            // 필수. N### | H### | D### | S###
      "perspective": "convention",      // 필수. convention | hygiene | design | sql
      "severity":    "먼저",             // 필수. 먼저 | 다음 | 참고
      "effort":      "보통",             // 필수. 작음 | 보통 | 큼
      "verdict":     "CONFIRMED",       // 필수. CONFIRMED | NEEDS-INFO
      "unitId":      "U4",              // 필수. units[].id 중 하나
      "file":        "YOEDSMOV/YOEDSMOV.xaml.cs",  // 필수
      "line":        138,               // 필수. 원문 기준 줄 번호
      "title":       "`bool` 반환 함수가 `Is` 로 시작하지 않는다",  // 필수
      "problem":     "…",               // 필수. `먼저` 면 "그래서 무엇이 나아지는지" 포함
      "basis":       "규칙 1-4",         // 필수. 규칙/체크리스트 번호
      "current":     "private bool CheckLot(string lotId)",  // 필수. 원문과 글자 그대로
      "suggestion":  "private bool IsMovableLot(string lotId)",  // 필수. 코드 또는 문장
      "impact":      "호출부 1곳(`Confirm()` 163줄)",  // 필수. effort 의 근거
      "checkpoints": "이름과 조건을 한 커밋에서 같이 바꾸세요"   // 선택
    }
  ],

  "quickWins": [                        // 손대기 쉬운 것. 없으면 []
    { "unitId": "U7", "content": "미사용 `using System.Web;` 삭제", "note": "없음" }
  ],

  "sql": [                              // SQL 본문 절. 없으면 []
    {
      "id":       "Q001",               // 필수
      "callType": "MAPPER",             // 필수. MAPPER | DPICALL | SQLEXEC
      "sqlId":    "lot.selectMcLot",    // MAPPER·DPICALL 이면 필수
      "sourcePath": "src-sql/lot/lot.xml:8",   // 본문을 찾은 위치
      "unitId":   "U12",
      "body":     "SELECT /*QR…*/ …",   // 필수. 찾은 SQL 본문
      "tuningPoints": ["`TRIM(l.lot_id)` 이 인덱스를 막습니다 (S004)"]   // 없으면 []
    }
  ],

  "rejected": [                         // 검증에서 반려된 제안. 감사 흔적으로 남깁니다
    {
      "id": "H004", "perspective": "hygiene",
      "title": "`btnSearch_Click()` 을 부르는 곳이 없다",
      "reason": "**V-4** — `wpfHints` 에 `xaml-handler` 가 있습니다. XAML 34줄이 부릅니다"
    }
  ],

  "unknowns": [                         // 확인 못 한 것. 없으면 []
    "`Bind()` 가 이 경로 밖에서 쓰이는지 — 대상 경로만 훑었습니다"
  ]

  // indexSummary 는 넣지 마세요. build-report.py 가 1-index.json 에서 직접 채웁니다.
}
```

## 만들 때 주의

| 주의 | 이유 |
|---|---|
| `overview.narrative` · `roadmap.diagnosis` 는 **필수** | 없으면 exit 1. 회의 자료의 첫 화면이 비어 버립니다 |
| **`roadmap.leaveAlone` 을 비우지 않는다** | 비면 리포트가 "전부 고치라"는 문서로 읽힙니다. 손대지 않는 편이 나은 것을 한 줄이라도 적으면 신뢰가 올라갑니다 (비면 경고가 뜹니다) |
| 개요·로드맵의 **줄바꿈을 살린다** | 리포트가 `\n` 을 문단 경계로 씁니다. 한 줄로 합치면 벽처럼 보입니다 |
| **백틱과 `**굵게**` 를 그대로 둔다** | 리포트가 `` `식별자` `` 를 코드 칩으로, `**…**` 를 굵게 렌더합니다. 지우지 마세요 |
| `REJECTED` 는 `findings` 에 넣지 않고 `rejected` 로 뺀다 | 본문에 실리면 회의에서 시간을 낭비합니다 |
| `unitId` 는 `units[].id` 에 실재해야 한다 | 없으면 exit 1 |
| `file` 은 `files[].path` 와 **글자 그대로** 같아야 한다 | 목차 연결이 끊어집니다 |
| mapper 파일은 `sourceFile` 을 **직접** 적는다 | 기본값이 `src/` 라 `src-sql/lot/lot.xml` 은 자동으로 안 잡힙니다 |
| `current` 를 길게 붙이지 않는다 | 원문은 스크립트가 임베드합니다. 어느 자리인지만 가리키면 됩니다 |
| `suggestion` 에 **코드든 문장이든** 자연스럽게 쓴다 | 리포트가 구분해 그립니다. 문장을 코드처럼 쓰면 줄바꿈이 안 돼 한 줄로 늘어납니다 |
| `severity` · `effort` 는 검증 결과(강등·상향 포함)를 반영한 **최종값** | `3-verify.md` 가 조정한 것을 그대로 씁니다 |

## 리포트가 보여 주는 순서

**요약이 먼저, 코드는 나중입니다.** 페이지를 열면 위에서부터 이 순서입니다.

1. **이 코드가 하는 일** — 무엇을 하는 코드이고 규모가 얼마인지
2. **개선 로드맵** — 그래서 뭐부터 할지 (+ 지금은 두는 게 나은 것)
3. **기계가 센 것** — 미참조·중복·미사용 SQL 건수. **모델이 쓴 숫자가 아님을 명시**합니다
4. **대상 요약** — 단위별 "무엇인가"와 제안 건수
5. 파일 → 단위 → 제안 카드. **코드 블록은 기본으로 접혀 있습니다**

그래서 `units[].summary` 와 `findings[].title` 이 이 리포트의 얼굴입니다.
**한 줄로 읽히게 쓰세요.**

## HTML 이 제공하는 것

- **`먼저 · 비용 작음` 한 번 누르기** — 이번 주에 할 일만 남깁니다. 이 리포트의 핵심 장치입니다
- 우선순위 · 비용 · 관점 **3종 필터** (겹쳐 걸 수 있습니다)
- **C# · XAML · SQL 문법 하이라이트** — 외부 라이브러리 없이 내장.
  `$@"…"` 축자 문자열 안의 여러 줄 SQL 도 SQL 키워드로 물듭니다
- 검색 — 제안 내용·파일·근거를 한 번에
- 제안마다 **[하기로] [보류] [안 함]** 선택과 메모 → 브라우저에 저장
  (`localStorage`, 키 = `oi-refactor-<slug>`. **대상별로 갈리므로 두 리포트를 같이 열어도 안 섞입니다**)
- 상단에 "결정 12 / 27" 진행 표시
- 회의 결과를 마크다운 / JSON 으로 복사·저장
- **테마 전환** — `시스템 → 라이트 → 다크`. 고른 값은 브라우저에 남고
  (`oi-refactor-theme`, 결정 저장소와 분리) 시스템 설정을 이깁니다
- 인쇄(`Ctrl+P`) 시 필터·메뉴가 사라지고 전부 펼쳐진 상태로 출력.
  **화면이 다크여도 종이는 항상 밝게** 나갑니다
- **외부 요청 0** — 폐쇄망에서 그냥 열립니다
