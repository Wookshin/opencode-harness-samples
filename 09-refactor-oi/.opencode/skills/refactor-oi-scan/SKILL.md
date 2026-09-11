---
name: refactor-oi-scan
description: 소스 경로를 받아 컨벤션·중복과 미사용 코드·구조·SQL 네 관점에서 개선할 곳을 찾아 제안하고, 팀이 모여서 볼 수 있는 단일 HTML 리포트를 만듭니다. 코드는 고치지 않습니다. 리팩토링할 곳을 찾아 달라는 요청을 받았을 때, 기술 부채를 정리할 순서를 정해야 할 때 이 스킬을 먼저 검토하세요.
---

# OI 리팩토링 제안 (소스 경로 단위)

기존 코드를 **네 관점이 동시에** 훑고, 제안을 **검증으로 걸러낸 뒤**,
팀이 "그래서 뭐부터 할까"를 정할 때 쓰는 **단일 HTML 파일**을 만듭니다.

**코드를 고치지 않습니다.** 제안만 합니다.

## 언제 쓰나

- 오래된 화면을 손봐야 하는데 **어디부터 손댈지** 정해야 할 때 (이 스킬의 본래 목적)
- 스프린트에 리팩토링 시간을 잡아 두고 **무엇을 넣을지** 고를 때
- 인수인계받은 코드의 **상태를 파악**해야 할 때

당장 고칠 한 곳을 아는 상태라면 이 하네스는 과합니다. **순서를 정해야 할 때** 쓰세요.

## 어떻게 실행하나

이 스킬은 혼자 동작하지 않습니다. **`.opencode/commands/` 의 커맨드로 실행**합니다.
`.opencode/` 가 놓인 **저장소 루트에서** 실행하세요 — 모든 경로가 그 기준입니다.

```bash
opencode run "/refactor YOEDSMOV"     # 전체 사이클 → _workspace/scan-YOEDSMOV/refactor-YOEDSMOV.html
opencode run "/scan-only YOEDSMOV"    # Phase 1 만 — 무엇을 볼지가 맞는지 먼저 확인
opencode run "/report-only YOEDSMOV"  # 제안은 그대로 두고 HTML 만 다시 생성
opencode run "/refactor-sample"       # 딸린 샘플로 도는 오프라인 데모
opencode run "/status"                # 진행 중인 모든 분석
opencode run "/doctor"                # 돌 준비가 됐는지 점검 (막히면 여기부터)
```

**하네스 파일을 찾지 마세요.** `.opencode/` 는 숨김 폴더라 `grep`·`glob` 에 안 잡힙니다.
경로는 고정이니 확인하지 말고 그대로 쓰세요. 정말 없으면 `/doctor` 가 알려 줍니다.

실제 코드에 처음 적용할 때는 **`/scan-only` 부터** 돌리세요.
무엇을 볼지가 틀리면 뒤의 네 제안자가 전부 틀린 것을 봅니다.

> 모델을 한 번도 부르지 않고 스크립트만 확인하려면
> `python .opencode/skills/refactor-oi-scan/assets/ws.py --selftest` 를 쓰세요.

## 무엇이 만들어지나

**대상 하나에 폴더 하나**입니다. 그래서 두 화면을 동시에 분석해도 섞이지 않습니다.

```
_workspace/scan-YOEDSMOV/
├── STATUS.md                 진행판
├── 1-meta.json               대상·규모·mapper 수집 결과
├── 1-files.json              파일별 종류·줄 수·최종 수정일
├── src/…                     대상 소스 원문 (바이트 그대로)
├── src-sql/…                 mapper XML (매핑이 있을 때만)
├── 1-index.json              ★ 심볼·참조·미참조·중복·SQL 대조 (기계가 센 것)
├── 1-index.md                위의 사람이 읽는 요약
├── 1-scope.md                이 코드가 하는 일 · 파일 목록
├── 1-units.md                대상 단위 표 (U1, U2 … ← 네 제안자가 공유하는 ID)
├── 2-suggest-convention.md   컨벤션 관점
├── 2-suggest-hygiene.md      중복·미사용 관점
├── 2-suggest-design.md       구조 관점
├── 2-suggest-sql.md          SQL 관점
├── 3-verify.md               제안별 CONFIRMED / NEEDS-INFO / REJECTED
├── 3-roadmap.md              개선 로드맵 (오케스트레이터가 직접)
├── 4-findings.json           HTML 입력 (스키마 고정)
└── refactor-YOEDSMOV.html    ★ 회의에서 여는 파일
```

터미널 두 개로 `/refactor YOEDSMOV` 와 `/refactor YOSTKMGR` 를 동시에 돌리면
폴더가 각각 채워집니다. `/status` 로 둘 다 한눈에 봅니다.

## 이 하네스의 전제 (네 관점 공통)

- **기계가 먼저 세고, 모델은 판정만 합니다.** `index.py` 가 심볼·참조·중복·SQL 을
  전수 조사해 `1-index.json` 에 올립니다. **인덱스에 없는 것을 미참조·중복이라고
  말하면 검증에서 반려됩니다.**
- **WPF 는 참조를 숨깁니다.** XAML 핸들러·바인딩·리소스 키·의존 속성·문자열 참조로
  불리는 코드는 **C# 에 호출부가 없는 것이 정상**입니다. 인덱서가 그 경로를 전부 봅니다.
- **대상 경로만 봅니다.** `public` 멤버와 공유 mapper 에 대해서는
  "이 경로 안에서는 안 쓰입니다" 까지만 말할 수 있습니다. 그 선을 넘지 않습니다.
- **추측으로 제안하지 않습니다.** 원문을 읽고 규칙 번호를 답니다.
- **코드를 고치지 않습니다.** 권한으로도 막혀 있습니다.

## 두 축으로 말합니다

리팩토링 제안에서 팀이 실제로 묻는 것은 하나입니다 — **"그래서 뭐부터 해요?"**

| 우선순위 | 뜻 |
|---|---|
| **먼저** | 지금 손대면 효과가 크거나, 이것 때문에 다른 개선이 막혀 있는 것 |
| **다음** | 해두면 좋지만 급하지 않은 것 |
| **참고** | 알아 두면 좋은 것, 지금은 두는 게 나은 것 |

| 비용 | 뜻 |
|---|---|
| **작음** | 한 파일 안에서 끝나고 되돌리기 쉬움 |
| **보통** | 여러 곳을 고치지만 대상 경로 안 |
| **큼** | 공개 시그니처·화면 동작이 바뀌거나 경로 밖 영향 조사가 필요 |

리포트는 **`먼저 · 비용 작음`** 을 한 번에 모아 보여 줍니다. 그게 이번 주에 할 일입니다.

## 참조 문서 (필요할 때만 읽으세요)

| 문서 | 누가 읽나 | 내용 |
|---|---|---|
| [references/naming-rules.md](references/naming-rules.md) | 컨벤션 제안자 | 함수·VO·변수·상수·`this` 명명 규칙 8종 |
| [references/hygiene-rules.md](references/hygiene-rules.md) | 중복·미사용 제안자 | 죽은 코드 판정 `K-*` · 중복·공통화 `P-*` · **WPF 참조 경로 표** |
| [references/design-rules.md](references/design-rules.md) | 구조 제안자 | 가독성·성능 체크리스트 `A-1`~`A-11` |
| [references/read-sql.md](references/read-sql.md) | SQL 제안자 | mapper 본문 읽는 절차와 판정 규칙 `Q-1`~`Q-9` |
| [references/suggest-format.md](references/suggest-format.md) | 네 제안자 전원 | 공통 출력 형식 · 우선순위·비용 기준 |
| [references/html-report.md](references/html-report.md) | 리포트 담당 | findings.json 스키마와 빌드 스크립트 사용법 |
| [mapper-dir.txt](mapper-dir.txt) | SQL 제안자 · `collect.py` | 저장소 → mapper 경로 매핑. **팀 환경에 맞게 고쳐 쓰는 파일** |

전문을 한꺼번에 읽지 마세요. 각 제안자는 **자기 문서 하나만** 읽습니다.
