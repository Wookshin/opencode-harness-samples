# 08 · 실전 · PR 코드리뷰 → 팀 오프라인 리뷰용 HTML

> **한 줄로**: 앞의 패턴들을 **실제 업무 하나**에 조립한 샘플. 결과물이 채팅이 아니라 **파일**입니다.

01~07 이 패턴을 하나씩 보여줬다면, 이건 그 패턴들을 **하나의 실무**에 붙인 것입니다.
PR 하나를 세 관점이 동시에 리뷰하고, 지적을 검증으로 걸러낸 뒤,
팀원들이 **모여 앉아 같이 보는 단일 HTML 파일**을 만듭니다.

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
node .opencode/skills/code-review-oi-pr/assets/build-report.mjs \
     sample/expected-findings.json /tmp/out.html sample/pr-sample.patch
# → /tmp/out.html 을 브라우저로 열어 보세요
```

## 무엇을 보여주는 샘플인가

C# WPF(MES 화면) PR 을 리뷰합니다. 등장인물은 여섯입니다.

| Phase | 담당 | 패턴 | 하는 일 | 모델 |
|---|---|---|---|---|
| 1 | `diff-scoper` | 파이프라인 | 변경분·원문 수집, **변경단위(L1, L2 …) 확정** | **고가** |
| 2 | `review-refactor` | **팬아웃** | 명명 규칙 (`naming-rules.md`) | 무난 |
| 2 | `review-feature` | **팬아웃** | 로직·예외·Manager 규범 (`manager-patterns.md`) | 무난 |
| 2 | `review-sql` | **팬아웃** | DPICALL 본문 조회, 바인딩·인덱스 (`read-sql.md`) | **고가** |
| 3 | `review-verifier` | **생성-검증** | 지적을 원문과 대조해 오탐 반려 | **고가** |
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
그리고 검증 단계에서 반려되도록 만든 **틀린 지적 3건**도 `sample/expected-findings.json` 에 들어 있습니다.

## 패턴이 보이는 지점

### ① 변경단위 ID 가 팬인의 접합면이다

`diff-scoper` 가 diff 를 논리 단위로 쪼개고 `L1`, `L2` … 로 번호를 매깁니다.
세 리뷰어는 전부 **같은 ID 를 참조해** 지적합니다.

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

03 은 게임을 실행해서 검증했습니다. 여기서 검증 대상은 **지적 그 자체**입니다.

| 검사 | 반려 사유 |
|---|---|
| V-1 | 인용한 라인이 변경단위 밖 → 기존 코드에 대한 지적 |
| V-2 | 인용 코드가 `src/after/` 원문과 불일치 → 존재하지 않는 코드 |
| V-3 | 근거로 든 규칙이 참조 문서에 없음 → 지어낸 규칙 |
| V-4 | BLOCKER 인데 결과 시나리오 없음 → **MAJOR 로 강등** |

팀원들이 모여서 보는 자료입니다. **"이거 원래 그랬는데요"가 나오면 30분이 날아갑니다.**

반려된 지적은 **지우지 않고** HTML 맨 아래 접이식 절에 남습니다. 감사 흔적입니다.

### ④ LLM 이 HTML 을 쓰지 않는다

`report-builder` 가 만드는 것은 `4-findings.json` 하나입니다.
HTML 은 `build-report.mjs` 가 만듭니다. 그리고 **코드는 JSON 에 들어가지 않습니다.**

```
1-diff.patch  ─┐
src/after/…   ─┼→ build-report.mjs → 라인별 add/del 계산 → HTML
4-findings.json ┘   (지적 내용 + 좌표만)
```

리뷰 코멘트를 LLM 이 쓰는 건 당연합니다. 하지만 **코드를 옮겨 적게 하면 반드시 뭉개집니다.**
그래서 좌표(`unitId`, `line`)만 받고 실제 코드는 원문에서 잘라 씁니다.

스크립트는 스키마를 **검증**하고, 어긋나면 무엇이 틀렸는지 출력하며 exit 1 합니다.

```
✗ findings.json 검증 실패 — 2건
  · findings[3] (F004): unitId "L99" 가 units 에 없습니다
  · sql[0]: 필수 항목 "body" 이 없습니다
```

### ⑤ 스킬은 얇고, 규칙은 참조 문서에 있다

`.opencode/skills/code-review-oi-pr/SKILL.md` 는 **진입점**입니다.
"언제 쓰는가 · 무슨 커맨드를 치는가 · 규칙은 어느 파일에 있는가"만 담습니다.

규칙 전문은 `references/` 에 있고 **각 리뷰어가 자기 문서 하나만** 읽습니다.

| 문서 | 읽는 사람 |
|---|---|
| `naming-rules.md` | 리팩토링 리뷰어만 |
| `manager-patterns.md` | 기능 리뷰어만 |
| `read-sql.md` | SQL 리뷰어만 |

세 명이 전부를 읽으면 컨텍스트가 3배로 낭비되고, 남의 영역까지 지적하기 시작합니다.

### ⑥ SQL 리뷰어만 저장소 밖을 본다

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

### ⑦ 작업 폴더가 PR 별로 갈린다

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

### ⑧ 아무도 소스를 못 고친다

`opencode.jsonc` 의 전역 기본값부터 `"edit": "deny"` 입니다. 04 와 같은 입장입니다.
각 에이전트는 `*_workspace/*` 만 열려 있어 **자기 보고서만** 씁니다.

## HTML 리포트가 회의에서 하는 일

`_workspace/pr-<번호>/review-<번호>.html` — 브라우저로 그냥 열면 됩니다. **외부 요청 0건**, 폐쇄망에서 동작합니다.

| 기능 | 쓰임 |
|---|---|
| 관점 3종 · 심각도 3종 토글, 전체 검색 | "일단 BLOCKER 만 봅시다" |
| 변경단위별 before/after 코드 (추가=초록, 삭제=빨강) | 화면에 띄워 놓고 같이 봄 |
| 지적된 라인에 앵커 마커 | 어디 얘기 중인지 헷갈리지 않음 |
| 파일 원문 접이식 임베드 | 저장소 없이도 앞뒤 맥락 확인 |
| 지적마다 **[합의] [보류] [반려]** + 메모 | 회의 중에 바로 기록 (`localStorage` 에 저장) |
| "결정 12 / 27" 진행 표시, **미결정만** 필터 | 남은 것부터 |
| 회의 결과 마크다운 복사 / JSON 저장 | 그대로 회의록에 붙여넣기 |
| SQL 본문 절 (경로 포함) | 회의 중에 DPImgr 파일을 직접 열어봄 |
| 인쇄 (`Ctrl+P`) | 필터·버튼이 사라지고 전부 펼쳐진 상태로 출력 |

다크 모드도 브라우저 설정을 따릅니다.

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

## 실제 저장소에 적용하려면

이 폴더는 샘플이라 `sample/` 로 시연하지만, 실무 저장소에서는 **`.opencode/` 만 복사**하면 됩니다.

```bash
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
│   │   ├── review-verifier.md           Phase 3 · 지적 검증 (고가)
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
│       │   ├── review-format.md         3인 공통 출력 형식 · 심각도 기준
│       │   └── html-report.md           findings.json 스키마
│       └── assets/
│           ├── report-template.html     단일 파일 HTML 골격 (인라인 CSS/JS)
│           └── build-report.mjs         스키마 검증 + diff 계산 + 렌더 (Node 내장 모듈만)
├── _workspace/
│   ├── README.md                        단계 사이 우편함 규약 (PR 별 폴더 구조 설명)
│   └── pr-<번호>/                        실행할 때 생김 — PR 하나에 폴더 하나 (.gitignore)
└── sample/
    ├── pr-sample.patch                  세 관점에 각각 걸리는 결함을 심은 C# 변경분
    ├── before/ · after/                 그 패치가 가리키는 파일 원문
    ├── dpimgr/lot/lot.xml               가짜 DPImgr 트리 (본문 조회 시연용)
    └── expected-findings.json           스크립트 단독 테스트용 고정 입력 (반려 3건 포함)
```
