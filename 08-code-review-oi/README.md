# 08 · 실전 · PR 코드리뷰 → 팀 오프라인 리뷰용 HTML

> **한 줄로**: 앞의 패턴들을 **실제 업무 하나**에 조립한 샘플. 결과물이 채팅이 아니라 **파일**입니다.

01~07 이 패턴을 하나씩 보여줬다면, 이건 그 패턴들을 **하나의 실무**에 붙인 것입니다.
PR 하나를 세 관점이 동시에 리뷰하고, 확인사항을 검증으로 걸러낸 뒤,
팀원들이 **모여 앉아 같이 보는 단일 HTML 파일**을 만듭니다.

> 📖 **동작 원리를 알고 싶거나 남에게 설명해야 한다면 → [docs/how-it-works.md](docs/how-it-works.md)**
> 흐름도, Phase 별 상세, 설계 결정 여섯 가지, 처음 쓰는 사람 가이드, 치트시트가 있습니다.

## 바로 실행하기

```bash
cd 08-code-review-oi

# gh 없이 도는 오프라인 데모 — 여기부터 권합니다
opencode run "/review-sample"

# 실제 PR 전체 사이클
opencode run "/review-pr 1234"

# Phase 1 만 — 변경단위 분류가 맞는지 먼저 확인
opencode run "/scope-only 1234"

# HTML 만 다시 생성 / 진행 중인 모든 리뷰 상태
opencode run "/report-only 1234"
opencode run "/status"
```

**PR 두 개를 동시에 리뷰할 수 있습니다.** 터미널 두 개에서 각각 돌리면 됩니다.

```bash
# 터미널 1                          # 터미널 2
opencode run "/review-pr 1234"      opencode run "/review-pr 5678"
#   → _workspace/pr-1234/               → _workspace/pr-5678/
```

**LLM 없이 렌더링만 먼저 보고 싶다면** 빌드 스크립트를 단독으로 돌릴 수 있습니다.

```bash
python .opencode/skills/code-review-oi-pr/assets/build-report.py \
     sample/expected-findings.json /tmp/out.html sample/pr-sample.patch
# → /tmp/out.html 을 브라우저로 열어 보세요
```

## 무엇을 보여주는 샘플인가

C# WPF(MES 화면) PR 을 리뷰합니다. 등장인물은 여섯입니다.

| Phase | 담당 | 패턴 | 하는 일 | 모델 |
|---|---|---|---|---|
| 1 | `diff-scoper` | 파이프라인 | `collect.py` 로 수집 → **변경단위(L1, L2 …) 확정** | **고가** |
| 2 | `review-refactor` | **팬아웃** | 명명 규칙 (`naming-rules.md`) | 무난 |
| 2 | `review-feature` | **팬아웃** | 로직·예외·Manager 규범 (`manager-patterns.md`) | 무난 |
| 2 | `review-sql` | **팬아웃** | DPICALL 본문 조회, 바인딩·인덱스 (`read-sql.md`) | **고가** |
| 3 | `review-verifier` | **생성-검증** | 확인사항을 원문과 대조해 오탐 반려 | **고가** |
| 4 | `report-builder` | 파이프라인 | findings.json → 스크립트 → HTML | 무난 |

**이 하네스만 저렴 등급을 쓰지 않습니다.** 01~07 은 기계적인 자리에 저렴 모델을 배치해
비용 계층을 보여주는 것이 목적이지만, 08 은 실제 PR 을 보고 팀 회의 자료를 만듭니다.
**틀린 리포트의 비용이 모델 비용보다 훨씬 큽니다.**

고가를 준 세 자리는 각각 이유가 있습니다.

| 자리 | 틀리면 |
|---|---|
| `diff-scoper` | 변경 유형(신규/변경/이름변경)을 여기서 확정합니다. 틀리면 **뒤의 세 리뷰어가 전부 틀린 것을 봅니다** |
| `review-sql` | 운영 DB 로 나가는 쿼리입니다. 잘못 통과시키는 비용이 가장 큽니다 |
| `review-verifier` | 오탐을 놓치면 **회의 시간이 통째로 날아갑니다** |

`sample/` 의 변경분에는 **세 관점에 각각 걸리는 결함**이 일부러 심어져 있습니다.
그리고 검증 단계에서 반려되도록 만든 **틀린 확인사항 3건**도 `sample/expected-findings.json` 에 들어 있습니다.

## 패턴이 보이는 지점

### ① 변경단위 ID 가 팬인의 접합면이다

`diff-scoper` 가 diff 를 논리 단위로 쪼개고 `L1`, `L2` … 로 번호를 매깁니다.
세 리뷰어는 전부 **같은 ID 를 참조해** 확인사항합니다.

```markdown
| ID | 파일 | 변경 유형 | after 라인 | before 라인 | 요약 |
|---|---|---|---|---|---|
| L5 | YOEDSMOV.xaml.cs | 변경 | 82–126 | 78–110 | Confirm() 단건 → 다건 반복 확정 |
| L6 | YOEDSMOV.xaml.cs | 신규 | 127–139 | — | 반출 가능 상태 검사 함수 추가 |
```

이게 없으면 세 사람이 같은 곳을 다른 이름으로 부릅니다. 취합할 때 중복인지 아닌지 알 수 없습니다.
**팬인은 형식 합의에서 시작합니다** — 04 에서 형식을 맞췄다면, 여기서는 **좌표까지** 맞춥니다.

### ② 부탁이던 두 줄이 장치가 됐다

원래 스킬에는 이런 문장이 있었습니다.

> 기존 기능(변경이 없는 코드)은 리뷰하지 않는다.
> 변경 전의 코드를 신규 기능으로 오인하지 않는다.

문장만 있으면 모델은 급할 때 무시합니다. 여기서는 세 곳에 걸었습니다.

1. `1-hunks.md` 의 **변경 유형 칸** — 리네이밍·이동·삭제를 Phase 1 에서 못 박습니다
2. 리뷰어 프롬프트 — "**표에 없는 라인은 리뷰 대상이 아닙니다**"
3. **검증관의 V-1** — 변경단위 밖 라인을 인용하면 `REJECTED`

3번이 핵심입니다. 지키라고 부탁하는 대신 **안 지키면 걸러냅니다.**

### ③ 생성-검증이 회의 시간을 지킨다

03 은 게임을 실행해서 검증했습니다. 여기서 검증 대상은 **확인사항 그 자체**입니다.

| 검사 | 반려 사유 |
|---|---|
| V-1 | 인용한 라인이 변경단위 밖 → 기존 코드에 대한 확인사항 |
| V-2 | 인용 코드가 `src/after/` 원문과 불일치 → 존재하지 않는 코드 |
| V-3 | 근거로 든 규칙이 참조 문서에 없음 → 지어낸 규칙 |
| V-4 | 꼭 확인 인데 결과 시나리오 없음 → **확인 권장 로 강등** |

팀원들이 모여서 보는 자료입니다. **"이거 원래 그랬는데요"가 나오면 30분이 날아갑니다.**

반려된 확인사항은 **지우지 않고** HTML 맨 아래 접이식 절에 남습니다. 감사 흔적입니다.

### ④ 판정이 아니라 "같이 봐 주세요"

이 리포트는 **개발자가 자기 변경을 팀원에게 보여주는 자료**입니다. AI 가 합격/불합격을
매기는 문서가 아닙니다. 그래서 화면 어디에도 `PASS`/`FAIL` 이 없고, 확인사항은
**주의 등급 세 가지**로만 표시합니다.

| 등급 | 뜻 |
|---|---|
| **꼭 확인** | 실행하면 바로 드러날 문제. "그래서 무슨 일이 생기는지"를 쓸 수 있을 때만 |
| **확인 권장** | 지금 안 터지지만 같이 봐 두는 게 좋은 것 |
| **참고** | 알아 두면 좋은 것 |

프롬프트도 같은 자세로 씁니다. 종합 평가는 `이대로 병합하면 안 됩니다` 가 아니라
**`같이 봐야 할 지점이 몇 군데 생겼습니다`** 로 시작합니다.

### ⑤ 리포트가 요약부터 보여준다

코드 순서대로 늘어놓으면 "뭘 봐야 하는지" 알려고 전부 읽어야 합니다. 그래서 페이지 맨 위가
**전체 변경사항 요약**(이 PR 이 무엇을 하는지)과 **종합 평가**(어디를 같이 봐야 하는지)이고,
그다음이 **변경 요약**, 코드 블록은 **기본으로 접혀** 있습니다.

그래서 `units[].summary` 와 `findings[].title` 을 **한 줄로 읽히게 쓰는 것**이 중요합니다.

### ⑥ 문법 하이라이트를 직접 넣었다

폐쇄망에서 열려야 하므로 CDN 을 못 씁니다(외부 요청 0). 그래서 C# 과 SQL 토크나이저를
템플릿 안에 작게 넣었습니다. diff 는 줄 단위로 그려지는데, **여러 줄에 걸친 블록 주석과
축자 문자열(`@"…"`)이 끊기지 않도록 줄 사이에 상태를 들고 갑니다.**

덕분에 이 팀에서 가장 많이 보는 코드가 제대로 읽힙니다.

```csharp
_sql.AddSql($@"
    SELECT /*QR220728-023-01*/           ← 주석
           l.lot_id, m.mat_id            ← 문자열 안이지만 SQL 키워드로 물듦
      FROM mc_lot l, mc_mat m
     WHERE l.lot_id = {_sql.Bind("lotId")}
");
```

`$@"…"` 안이 SQL 로 보이면 문자열 색을 유지한 채 SQL 키워드만 강조합니다.
SqlManager 의 인라인 쿼리를 리뷰할 때 이게 가장 크게 체감됩니다.

### ⑦ LLM 이 HTML 을 쓰지 않는다

`report-builder` 가 만드는 것은 `4-findings.json` 하나입니다.
HTML 은 `build-report.py` 가 만듭니다. 그리고 **코드는 JSON 에 들어가지 않습니다.**

```
1-diff.patch  ─┐
src/after/…   ─┼→ build-report.py → 라인별 add/del 계산 → HTML
4-findings.json ┘   (확인사항 내용 + 좌표만)
```

리뷰 코멘트를 LLM 이 쓰는 건 당연합니다. 하지만 **코드를 옮겨 적게 하면 반드시 뭉개집니다.**
그래서 좌표(`unitId`, `line`)만 받고 실제 코드는 원문에서 잘라 씁니다.

스크립트는 스키마를 **검증**하고, 어긋나면 무엇이 틀렸는지 출력하며 exit 1 합니다.

```
✗ findings.json 검증 실패 — 2건
  · findings[3] (F004): unitId "L99" 가 units 에 없습니다
  · sql[0]: 필수 항목 "body" 이 없습니다
```

### ⑧ 스킬은 얇고, 규칙은 참조 문서에 있다

`.opencode/skills/code-review-oi-pr/SKILL.md` 는 **진입점**입니다.
"언제 쓰는가 · 무슨 커맨드를 치는가 · 규칙은 어느 파일에 있는가"만 담습니다.

규칙 전문은 `references/` 에 있고 **각 리뷰어가 자기 문서 하나만** 읽습니다.

| 문서 | 읽는 사람 |
|---|---|
| `naming-rules.md` | 리팩토링 리뷰어만 |
| `manager-patterns.md` | 기능 리뷰어만 |
| `read-sql.md` | SQL 리뷰어만 |

세 명이 전부를 읽으면 컨텍스트가 3배로 낭비되고, 남의 영역까지 확인사항하기 시작합니다.

### ⑨ SQL 리뷰어만 저장소 밖을 본다

DPICALL SQL 은 화면 코드에 **ID 만** 있고 본문은 별도 저장소(DPImgr)에 있습니다.
본문을 안 보면 파라미터가 맞는지, 인덱스를 타는지 알 수 없습니다.

`grep`·`glob` 툴은 프로젝트 안만 봅니다. 그래서 SQL 리뷰어에게만 bash 검색을 열었습니다.

```yaml
bash:
  "*": deny
  "rg*": allow
  "findstr*": allow    # Windows
  "dir*": allow
  "ls*": allow
```

경로 매핑은 `dpimgr-dir.txt` 에 있고, **이 파일이 팀 환경에 맞게 고쳐 쓰는 자리**입니다.

### ⑩ 작업 폴더가 PR 별로 갈린다

산출물은 `_workspace/` 에 평평하게 쌓이지 않고 **`_workspace/pr-<번호>/`** 로 나뉩니다.

```
_workspace/
├── README.md          규약 (유일하게 커밋되는 파일)
├── pr-1234/           세션 A — STATUS.md · 1-*.md · src/ · 2-*.md · 3-*.md · review-1234.html
└── pr-5678/           세션 B — 위와 같은 구성, 완전히 독립
```

폴더를 안 나누면 파일 이름이 전부 같아 서로를 덮어씁니다. 특히 `src/after/` 에 두 PR 의 원문이
섞이면 **리포트에 엉뚱한 PR 의 코드가 실립니다.** 눈에 잘 안 띄는 사고입니다.

세 가지 규칙이 이 격리를 지탱합니다.

1. **오케스트레이터가 Phase 0 에서 작업 폴더를 확정**하고, 모든 `task` 프롬프트에
   `_workspace/pr-1234/…` **전체 경로**를 적습니다. 서브에이전트는 대화를 못 보기 때문입니다.
2. **`_workspace/` 루트에 공유 파일을 만들지 않습니다.** 진행 인덱스 하나를 두면 그 파일이
   다시 경합 지점이 됩니다. `/status` 는 각 폴더의 `STATUS.md` 를 **읽기만** 합니다.
3. **아무도 지우지 않습니다.** 같은 PR 을 새로 돌릴 때도 `mv _workspace/pr-1234
   _workspace/pr-1234.prev-<시각>` 으로 밀어냅니다. bash 권한은 명령 문자열 글롭이라
   `rm -rf _workspace/pr-*` 같은 와일드카드를 패턴만으로 막을 수 없어서,
   **`rm` 권한 자체를 주지 않았습니다.** 정리는 사람이 합니다.

빌드 스크립트는 이 구조를 **모릅니다.** `dirname(findings.json)` 을 기준으로 패치와 원문을
찾을 뿐이라, 작업 폴더가 어디로 바뀌어도 인자만 맞으면 그대로 동작합니다.

### ⑪ 아무도 소스를 못 고친다

`opencode.jsonc` 의 전역 기본값부터 `"edit": "deny"` 입니다. 04 와 같은 입장입니다.
각 에이전트는 `*_workspace/*` 만 열려 있어 **자기 보고서만** 씁니다.

## HTML 리포트가 회의에서 하는 일

`_workspace/pr-<번호>/review-<번호>.html` — 브라우저로 그냥 열면 됩니다. **외부 요청 0건**, 폐쇄망에서 동작합니다.

**요약이 먼저, 코드는 나중입니다.**

| 순서 | 무엇 | 쓰임 |
|---|---|---|
| 1 | **전체 변경사항 요약** | 이 PR 이 무엇을 하는지. 한 줄 전체 폭 |
| 2 | **종합 평가** | 그래서 어디를 같이 봐야 하는지 |
| 3 | **변경 요약** (+ 유형 범례) | 변경단위별 "무엇이 바뀌었나" + 확인사항 건수 |
| 4 | 파일 → 변경단위 → 확인사항 카드 | **코드 블록은 기본으로 접혀 있습니다** |

화면을 일부러 얇게 뒀습니다. 필터·대시보드·체크리스트·회의 진행 장치를 걷어내고
**보여주는 데 필요한 것만** 남겼습니다.

| 기능 | 쓰임 |
|---|---|
| **C# · SQL 문법 하이라이트** | 외부 라이브러리 없이 내장. `$@"…"` 안의 여러 줄 SQL 도 SQL 로 물듦 |
| **변경 유형 범례** | `신규·변경·삭제·이름변경·이동` 다섯 가지와, 유형이 아닌 `단순` 표시를 접이식으로 |
| **보기 전환** (`위아래` ↔ `좌우`) | 통합 diff 로 흐름을 보다가, 좌우로 놓고 변경 전후를 나란히 |
| 검색 | 확인사항 내용·파일·근거를 한 번에 |
| **⚙ 설정 메뉴** | 마크다운 복사 · 코드 펼치기 · 보기 · 테마 · 인쇄. 자주 안 쓰는 것을 한 곳에 |
| 인쇄 (`Ctrl+P`) | 검색·메뉴가 사라지고 전부 펼쳐진 상태로 출력. 화면이 다크여도 종이는 밝게 |

테마는 기본이 시스템 설정이고, 설정 메뉴에서 라이트·다크를 고정할 수 있습니다.

> `findings[].title` 과 `units[].summary` 가 이 리포트의 얼굴입니다.

테마는 기본이 시스템 설정이고, 버튼으로 라이트·다크를 고정할 수 있습니다.
고른 값은 `localStorage` 에 남되 **결정 저장소와는 다른 키**라 `결정 초기화` 로 지워지지 않습니다.

## 직접 바꿔 보기

- **`/review-sample` 을 먼저 돌리세요.** `_workspace/` 에 무엇이 순서대로 쌓이는지 보입니다.
  그다음 HTML 을 열어 필터를 눌러 보세요.
- **`/scope-only` 로 실 PR 을 걸어 보세요.** `1-hunks.md` 의 변경 유형 분류만 확인하는 커맨드입니다.
  **여기가 틀리면 뒤가 전부 틀어지므로** 실 적용은 이것부터 하는 게 안전합니다.
- **리뷰어를 하나 빼 보세요.** `review-sql.md` 를 `.bak` 으로 바꾸면 SQL 결함이 리포트에서 통째로 사라집니다.
- **검증관을 빼 보세요.** `review-verifier` 없이 돌리면 오탐이 그대로 회의 자료에 실립니다.
  `sample/expected-findings.json` 의 `rejected` 3건이 본문에 섞이는 것과 같은 상태입니다.
- **`4-findings.json` 을 일부러 망가뜨려 보세요.** `unitId` 를 없는 값으로 바꾸고 스크립트를 돌리면
  검증에서 걸립니다. LLM 이 스키마를 어겼을 때 무엇이 막아 주는지 볼 수 있습니다.
- **네 번째 관점을 추가해 보세요.** 예: `review-ui`(XAML 바인딩·리소스). 에이전트 파일 하나와
  오케스트레이터의 호출 목록 한 줄, 그리고 `html-report.md` 의 `perspective` 목록에 한 줄이면 됩니다.
- **두 PR 을 동시에 돌려 보세요.** 터미널 두 개로 `/review-pr 1234`, `/review-pr 5678` 을 띄우고
  `_workspace/` 를 보면 폴더가 둘로 갈립니다. `/status` 로 둘 다 한눈에 확인하세요.
- **작업 폴더 격리를 깨 보세요.** `review-lead.md` 의 `task` 프롬프트에서 작업 폴더 경로를 빼고
  `1-hunks.md` 로만 적으면, 서브에이전트가 어느 폴더인지 몰라 엉뚱한 곳을 찾거나 루트에 씁니다.
  경로를 전체로 적어야 하는 이유가 바로 보입니다.
- **자기 팀 규칙으로 바꿔 보세요.** `references/naming-rules.md` 를 팀 컨벤션으로 갈아 끼우면
  리팩토링 리뷰어의 판정 기준이 통째로 바뀝니다. 에이전트는 손대지 않습니다.

## Windows · PowerShell 에서 돌릴 때

이 하네스는 **PowerShell 을 기본 환경으로 가정하고** 만들었습니다. 팀 개발 환경이 Windows 이기 때문입니다.

### 셸에 의존하지 않게 만든 이유

에이전트가 셸 명령을 조합하면 환경마다 다르게 깨집니다.

| Unix 에서 쓰던 것 | PowerShell 에서 |
|---|---|
| `ls -la` | `-la` 라는 파라미터가 없어 **오류** |
| `mkdir -p foo/bar` | `-p` 가 없어 **오류** |
| `$(dirname …)` · `$(date +%Y%m%d)` | 그런 명령이 **없음** |
| `rm -rf` · `cp -r` | `-rf` 는 오류, `-r` 은 우연히 동작 |
| `wc -l` · `basename` | **없음** |
| **`명령 > 파일`** | Windows PowerShell 5.1 은 **UTF-16LE** 로 씁니다 |

마지막 줄이 가장 위험합니다. **오류가 나지 않습니다.** `gh pr diff 1234 > 1-diff.patch` 가
멀쩡히 끝나고, 리포트에는 diff 색칠이 통째로 빠진 채 나옵니다. 아무도 모릅니다.

### 그래서 수집을 스크립트로 옮겼습니다

```bash
python .opencode/skills/code-review-oi-pr/assets/collect.py --pr 1234 --ws _workspace/pr-1234
```

`collect.py` 가 `gh`·`git` 을 직접 부르고 출력을 **바이트 그대로** 씁니다.
폴더 생성, 이전 실행 밀어내기, 파일별 상태 판별까지 여기서 합니다.
PowerShell 이든 bash 든 **결과가 바이트까지 같습니다.**

> 스크립트를 **Python 으로 쓴 이유**도 같습니다 — 팀 PC 에 대부분 깔려 있고,
> Windows·리눅스·맥에서 같은 파일이 그대로 돕니다. `pip install` 은 필요 없습니다.

에이전트에게 남은 bash 권한도 그래서 짧습니다.

| 에이전트 | 열린 명령 |
|---|---|
| `diff-scoper` | `python` · `gh pr view` · `git log` · `git rev-parse` |
| `report-builder` | `python` |
| `review-lead` | `git status` · `git rev-parse` |
| 리뷰어 3인 | `git show` · `git diff` · `git log` |
| `review-sql` | 위 + 검색기 (`rg` · `findstr` · `Select-String` · `grep`) |

파일 목록·내용 확인은 전부 **`list` · `read` · `grep` · `glob` 도구**로 합니다.
셸을 거치지 않으므로 환경 차이가 없습니다.

`build-report.py` 도 방어선을 하나 갖고 있습니다. 읽는 파일이 UTF-16 이면
**감지해서 디코딩하고 경고**합니다. 다른 경로로 만든 파일이 섞여 들어와도 조용히 깨지지 않습니다.

### 필요한 것

| | |
|---|---|
| **Python 3.8+** | `collect.py` · `build-report.py` 가 씁니다. `python --version` 으로 확인. **pip 설치는 필요 없습니다** — 표준 라이브러리만 씁니다 |
| **gh CLI** | `gh auth login` 이 되어 있어야 합니다 |
| **git** | PR 원문을 받습니다 (체크아웃은 하지 않습니다) |
| ripgrep (선택) | DPImgr SQL 검색이 빨라집니다. 없으면 `findstr`·`Select-String` 을 씁니다 |

경로는 `_workspace/pr-1234` 처럼 **슬래시로 적어도 됩니다.** Python 의 `pathlib` 과 git 이 알아서 처리합니다.

인터프리터 이름은 환경마다 다릅니다. `python` 이 안 되면 `py`(Windows) 또는 `python3`(리눅스·맥)를 쓰세요.

## 실제 저장소에 적용하려면

이 폴더는 샘플이라 `sample/` 로 시연하지만, 실무 저장소에서는 **`.opencode/` 만 복사**하면 됩니다.

```powershell
# PowerShell
Copy-Item -Recurse 08-code-review-oi\.opencode  D:\Git\OY_SWP\
Copy-Item -Recurse 08-code-review-oi\_workspace D:\Git\OY_SWP\
```

```bash
# bash / zsh
cp -r 08-code-review-oi/.opencode  /path/to/OY_SWP/
cp -r 08-code-review-oi/_workspace /path/to/OY_SWP/
```

그다음 고칠 곳은 세 군데입니다.

| 파일 | 고칠 것 |
|---|---|
| `.opencode/skills/code-review-oi-pr/dpimgr-dir.txt` | 팀의 DPImgr 경로 매핑 |
| `.opencode/agents/*.md` 의 `model:` | 쓰는 프로바이더의 모델 이름 |
| `.gitignore` | `_workspace/*` 를 무시하도록 (`!_workspace/README.md` 예외). `*` 가 `/` 를 넘으므로 `pr-*/` 하위까지 함께 잡힙니다 |

기본 브랜치가 `develop` 이 아니면 `diff-scoper` 가 그 사실을 `1-scope.md` 에 적고 알려 줍니다.
임의로 바꾸지 않습니다.

## 파일 구조

```
08-code-review-oi/
├── opencode.jsonc                       전역 edit: deny · 저렴 등급 미사용 (무난/고가만)
├── .opencode/
│   ├── agents/
│   │   ├── review-lead.md               오케스트레이터 (primary) ← 게이트·동시 호출 지시
│   │   ├── diff-scoper.md               Phase 1 · 변경단위 확정 (고가) ← 틀리면 뒤가 전부 틀어짐
│   │   ├── review-refactor.md           Phase 2 · 명명 규칙 (무난)
│   │   ├── review-feature.md            Phase 2 · 로직·Manager 규범 (무난)
│   │   ├── review-sql.md                Phase 2 · SQL (고가) ← 유일하게 저장소 밖을 봄
│   │   ├── review-verifier.md           Phase 3 · 확인사항 검증 (고가)
│   │   └── report-builder.md            Phase 4 · findings.json (무난)
│   ├── commands/
│   │   ├── review-pr.md                 /review-pr <번호>   전체 사이클
│   │   ├── scope-only.md                /scope-only <번호>  Phase 1 만
│   │   ├── report-only.md               /report-only <번호> HTML 만 재생성
│   │   ├── review-sample.md             /review-sample      gh 없는 오프라인 데모
│   │   └── status.md                    /status             진행 중인 모든 PR 리뷰
│   └── skills/code-review-oi-pr/
│       ├── SKILL.md                     진입점 (얇게 유지)
│       ├── dpimgr-dir.txt               ★ 팀 환경에 맞게 고치는 파일
│       ├── references/
│       │   ├── naming-rules.md          명명 규칙 8종 + 판정 예시
│       │   ├── manager-patterns.md      SqlManager·RuleManager 규범 + 체크리스트 M-1~M-9
│       │   ├── read-sql.md              DPICALL 본문 조회 절차
│       │   ├── review-format.md         3인 공통 출력 형식 · 주의 등급 기준
│       │   └── html-report.md           findings.json 스키마
│       └── assets/
│           ├── collect.py              gh·git 호출 + 원문 수집 (셸 비의존, UTF-8 고정)
│           ├── report-template.html     단일 파일 HTML 골격 (인라인 CSS/JS)
│           └── build-report.py         스키마 검증 + diff 계산 + 렌더 (표준 라이브러리만)
├── docs/
│   └── how-it-works.md                  ★ 동작 원리 · 발표용 · 입문용
├── _workspace/
│   ├── README.md                        단계 사이 우편함 규약 (PR 별 폴더 구조 설명)
│   └── pr-<번호>/                        실행할 때 생김 — PR 하나에 폴더 하나 (.gitignore)
└── sample/
    ├── pr-sample.patch                  세 관점에 각각 걸리는 결함을 심은 C# 변경분
    ├── before/ · after/                 그 패치가 가리키는 파일 원문
    ├── dpimgr/lot/lot.xml               가짜 DPImgr 트리 (본문 조회 시연용)
    └── expected-findings.json           스크립트 단독 테스트용 고정 입력 (반려 3건 포함)
```
