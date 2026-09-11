# 이 하네스는 어떻게 동작하는가

> `09-refactor-oi` — 기존 소스를 훑어 **리팩토링할 곳을 제안**하고,
> 팀이 "그래서 뭐부터 할까"를 정할 때 쓰는 **단일 HTML 파일**을 만듭니다.
> **코드는 고치지 않습니다.**

이 문서 하나면 됩니다. 발표 자료로 쓰거나 팀에 소개할 때 이것만 보여 주세요.

---

## 1. 한 장 요약

| | |
|---|---|
| **입력** | 소스 경로 하나 (`YOEDSMOV` · `src/Screens/YOEDSMOV` · 저장소 전체는 `.`) |
| **출력** | `_workspace/scan-<slug>/refactor-<slug>.html` — 브라우저로 그냥 여는 파일 |
| **관점** | 컨벤션 · 중복/미사용 · 구조 · SQL |
| **등장인물** | 오케스트레이터 1 + 스코퍼 1 + 제안자 4 + 검증관 1 + 빌더 1 = **8** |
| **한 사이클** | 모델 호출 **8회** |
| **필요한 것** | Python 3.8+ 만. `gh` 불필요, git 은 선택 |
| **네트워크** | **0** — 리포트도 폐쇄망에서 열립니다 |

## 2. 왜 이렇게 만들었나

| 문제 | 이 하네스의 답 |
|---|---|
| "리팩토링 좀 하자" 는 말이 **아무 일도 일으키지 않는다** | 우선순위 × 비용 2축으로 **이번 주에 할 일**을 뽑아 줍니다 |
| LLM 에게 "안 쓰는 코드를 찾아라" 하면 **반드시 놓친다** | 전수 조사는 `index.py` 가 합니다. 모델은 **판정만** |
| WPF 는 **참조를 숨긴다** — XAML·문자열·리플렉션 | 인덱서가 14가지 경로를 보고, 검증관이 `V-4` 로 한 번 더 막습니다 |
| 제안이 너무 많으면 **아무도 안 읽는다** | 규모 게이트 · 검증 반려 · `먼저·작음` 필터 |
| "전부 고치라"는 문서는 **신뢰를 잃는다** | 로드맵에 **「지금은 두는 게 낫습니다」** 가 필수입니다 |

## 3. 전체 흐름

```mermaid
flowchart TD
    U["/refactor YOEDSMOV"] --> L0

    subgraph P0["Phase 0 · 작업 폴더"]
      L0["refactor-lead<br/>_workspace/scan-YOEDSMOV 확정"]
    end

    L0 --> S

    subgraph P1["Phase 1 · 수집과 대상 확정"]
      S["code-scoper"]
      S --> C["collect.py<br/>src/ · src-sql/ · 1-files.json"]
      C --> I["index.py<br/>1-index.json ← 심볼·참조·중복·SQL"]
      I --> U1["1-scope.md · 1-units.md<br/>U1, U2 … 대상 단위"]
    end

    U1 --> G1{"게이트<br/>단위 0개? 규모 초과?"}
    G1 -- "멈춤" --> X1["경로를 좁히라고 요구"]
    G1 -- "통과" --> F

    subgraph P2["Phase 2 · 4인 동시 제안 (한 응답에서)"]
      F[" "]
      F --> A1["refac-convention<br/>N###"]
      F --> A2["refac-hygiene<br/>H###"]
      F --> A3["refac-design<br/>D###"]
      F --> A4["refac-sql<br/>S### · Q###"]
    end

    A1 --> V
    A2 --> V
    A3 --> V
    A4 --> V

    subgraph P3["Phase 3 · 검증"]
      V["refac-verifier<br/>V-1 ~ V-7"]
      V --> VR["3-verify.md<br/>CONFIRMED / NEEDS-INFO / REJECTED"]
    end

    VR --> G2{"반려율 > 1/3?"}
    G2 -- "예 (최대 2회)" --> A2
    G2 -- "아니오" --> RM

    subgraph P35["Phase 3.5 · 로드맵 (위임하지 않음)"]
      RM["refactor-lead 가 직접<br/>3-roadmap.md"]
    end

    RM --> B

    subgraph P4["Phase 4 · 리포트"]
      B["report-builder<br/>4-findings.json"]
      B --> BR["build-report.py"]
      I -. "기계가 센 숫자" .-> BR
      BR --> H["refactor-YOEDSMOV.html"]
    end

    H --> G3{"read 로 실재 확인"}
    G3 --> DONE["완료 보고"]
```

| Phase | 담당 | 읽는 것 | 쓰는 것 |
|---|---|---|---|
| 0 | `refactor-lead` | — | `STATUS.md` |
| 1 | `code-scoper` | 대상 소스 | `src/` · `1-index.json` · `1-scope.md` · `1-units.md` |
| 2 | 제안자 4인 | `1-units.md` · `1-index.md` · `src/` · 자기 참조 문서 | `2-suggest-*.md` |
| 3 | `refac-verifier` | 위 전부 + `1-index.json` | `3-verify.md` |
| 3.5 | `refactor-lead` | `2-*` · `3-verify.md` | `3-roadmap.md` |
| 4 | `report-builder` | 위 전부 | `4-findings.json` → **HTML** |

## 4. Phase 별로 무슨 일이 일어나나

### Phase 0 — 작업 폴더 확정

대상 경로에서 slug 를 만들어 `_workspace/scan-<slug>/` 로 정합니다.

| 대상 경로 | 작업 폴더 |
|---|---|
| `YOEDSMOV` | `scan-YOEDSMOV` |
| `src/Screens/YOEDSMOV` | `scan-src-Screens-YOEDSMOV` |
| `.` | `scan-root` |

폴더를 나누지 않으면 파일 이름이 전부 같아 서로를 덮어씁니다.
특히 `src/` 에 두 대상의 원문이 섞이면 **리포트에 엉뚱한 코드가 실립니다.**

오케스트레이터는 **폴더를 직접 만들지 않습니다.** `collect.py` 가 만듭니다.
**아무것도 지우지 않습니다** — `rm` 권한이 없습니다.

### Phase 1 — 수집 · 인덱싱 · 대상 확정

**여기가 08 과 가장 크게 갈리는 지점입니다.**

08 은 diff 가 "무엇을 볼지"를 공짜로 정해 줬습니다. 09 에는 그런 경계가 없습니다.

```bash
python …/collect.py --path YOEDSMOV --ws _workspace/scan-YOEDSMOV
python …/index.py  --ws _workspace/scan-YOEDSMOV
```

`collect.py` 가 하는 일:

- 텍스트 소스만 골라 `src/` 로 **바이트 그대로** 복사 (`bin/` · `obj/` · 생성 코드 제외)
- `mapper-dir.txt` 매핑을 따라 iBATIS mapper 를 `src-sql/` 로
- git 이 있으면 파일별 최종 수정일·커밋 수 (오래 안 건드린 코드의 약한 신호)
- 이전 실행은 **지우지 않고** `.prev-<시각>` 으로 밀어냄

`index.py` 가 하는 일 — **전수 조사**:

| 산출 | 어떻게 |
|---|---|
| `symbols[]` | C# 을 마스킹(주석·문자열 제거)한 뒤 중괄호 깊이로 심볼 경계를 잡습니다 |
| `refs` | 식별자 출현을 C# · XAML · 문자열 세 갈래로 나눠 셉니다 |
| `wpfHints` | **WPF 가 참조를 숨기는 14가지 경로** (아래 §5-②) |
| `unreferenced[]` | 참조 0 + 힌트 없음. **확신 3등급**을 함께 매깁니다 |
| `duplicateCandidates[]` | 정규화 토큰 5-gram 의 Jaccard ≥ 0.75, 8줄 이상 |
| `sql` | mapper 정의 ID ↔ C# 호출 ID 대조 → 미사용·정의없음·중복 본문 |

그다음 `code-scoper` 가 **무엇을 볼지 고릅니다.**
`symbols[]` 전부를 단위로 만들면 폭발하므로, **제안할 거리가 있을 만한 것만**
`U1` 부터 번호를 매깁니다.

```markdown
| ID | 파일 | 유형 | 줄 | 참조 | 요약 |
|---|---|---|---|---|---|
| U1 | YOEDSMOV.xaml.cs | 필드   | 26–26   | 0 | `MaxRowCount` — 선언만 있고 읽는 곳이 없습니다 |
| U5 | YOEDSMOV.xaml.cs | 메서드 | 150–213 | 1 | `Confirm()` — 선택 수집·검증·저장을 한 덩어리로 (64줄) |
```

### Phase 2 — 4인 동시 제안 (팬아웃)

오케스트레이터가 **한 응답에서 네 개의 `task`** 를 부릅니다.
나눠 부르면 직렬이 되어 느리고 비쌉니다.

네 프롬프트는 **산출물 파일명만 다릅니다.** 각자 읽을 참조 문서는 자기 프롬프트가 압니다.

| 제안자 | 참조 문서 | ID |
|---|---|---|
| `refac-convention` | `naming-rules.md` | `N###` |
| `refac-hygiene` | `hygiene-rules.md` | `H###` |
| `refac-design` | `design-rules.md` | `D###` |
| `refac-sql` | `read-sql.md` | `S###` (본문 `Q###`) |

**넷이 전부를 읽으면 컨텍스트가 4배로 낭비되고, 남의 영역까지 제안하기 시작합니다.**

### Phase 3 — 검증 (생성-검증)

제안 하나마다 일곱 검사를 겁니다.

| 검사 | 대조 대상 | 결과 |
|---|---|---|
| V-1 | `1-units.md` 표 | 범위 밖이면 `REJECTED` |
| V-2 | `src/` 원문 | 인용이 다르면 `REJECTED` |
| V-3 | 참조 문서 | 규칙이 없으면 `REJECTED` |
| **V-4** | **`1-index.json`** | **미참조 오탐이면 `REJECTED`** |
| V-5 | `duplicateCandidates` | 중복 후보가 아니면 `REJECTED` |
| V-6 | 제안 본문 | 효과를 못 쓰면 `먼저` → `다음` **강등** |
| V-7 | `영향` 칸 | 범위를 안 셌으면 `작음` → `보통` **상향** |

한 관점의 반려율이 **1/3 을 넘으면** 그 제안자의 **세션을 다시 열어** 고치게 합니다
(`task_id` 재사용 — 맥락이 남습니다). 고친 뒤엔 **새 검증관**을 돌립니다.
최대 2회.

### Phase 3.5 — 개선 로드맵 (오케스트레이터가 직접)

**위임하지 않습니다.** 네 관점을 전부 본 사람은 오케스트레이터뿐입니다.

제안자들은 각자 자기 것만 봅니다. "그래서 뭐부터 해요?" 에 답할 수 있는 것은
**네 묶음을 한자리에 놓고 순서를 만드는 사람**뿐이고, 그게 이 리포트의 값입니다.

```markdown
## 한 줄 진단         ← 증상이 아니라 원인
## 손대는 순서         ← 번호 목록. 제안 ID 를 답니다
## 묶어서 하면 좋은 것  ← 같은 커밋에서 처리할 것
## 지금은 두는 게 낫습니다   ← ★ 비우면 안 됩니다
```

순서를 만드는 기본형:

| 먼저 놓을 것 | 왜 |
|---|---|
| 죽은 코드 삭제 (`먼저`·`작음`) | 비용이 거의 없고, 지운 뒤 남는 코드가 줄어 다음이 쉬워집니다 |
| 중복 합치기 | 구조를 보기 전에 같은 코드를 하나로 |
| 구조 나누기 (`큼`) | 앞의 둘을 끝낸 뒤면 바뀔 코드가 눈에 보입니다 |
| 이름 정리 | **구조를 나누는 커밋과 같이** 해야 호출부를 두 번 안 건드립니다 |

### Phase 4 — 리포트

`report-builder` 가 만드는 것은 `4-findings.json` **하나**입니다.
HTML 은 `build-report.py` 가 만듭니다.

```
src/…           ─┐
1-index.json    ─┼→ build-report.py → HTML
4-findings.json ─┘   (제안 내용 + 좌표만)
```

스크립트가 **스키마를 검증**하고, 어긋나면 무엇이 틀렸는지 출력하며 exit 1 합니다.

```
✗ findings.json 검증 실패 — 2건
  · findings[3] (H004): unitId "U99" 가 units 에 없습니다
  · findings[7] (D002): "effort" 는 작음 | 보통 | 큼 중 하나여야 합니다 (받은 값: 중간)
```

---

## 5. 설계 결정 일곱 가지

### ① 기계가 먼저 세고, 모델은 판정만 한다

"이 코드는 아무도 안 씁니다" 는 **전수 조사로만** 할 수 있는 말입니다.
LLM 에게 `grep` 을 시키면 반드시 몇 개를 놓칩니다.

그래서 인덱서가 먼저 세고, 제안자는 **후보에 맥락을 붙이는 일**만 합니다.

리포트에도 그 구분이 남습니다 — 「기계가 센 것」 절에
**"모델이 쓴 숫자가 아닙니다"** 라고 적혀 있습니다.

### ② WPF 가 참조를 숨기는 14가지 경로

이 하네스가 가장 크게 틀릴 수 있는 자리입니다.

```csharp
private void btnSearch_Click(object sender, RoutedEventArgs e)  // C# 호출부: 0곳
```
```xml
<Button Click="btnSearch_Click" />                              <!-- 여기서 부릅니다 -->
```

| 경로 | 무엇을 스캔하나 |
|---|---|
| 이벤트 핸들러 | `Click=` · `Loaded=` 등 이벤트 속성, `EventSetter Handler=` |
| `x:Name` | XAML 선언 ↔ C# 의 같은 이름 |
| 데이터 바인딩 | `{Binding Foo}` · `{Binding Path=Foo.Bar}` 의 첫 세그먼트 |
| 명령 | `Command="{Binding SaveCommand}"` |
| 리소스 키 | `x:Key` ↔ `{StaticResource}` · `{DynamicResource}` |
| 컨버터 | `IValueConverter` 구현이 `x:Key` 로 등록됨 |
| 의존 속성 | `FooProperty` ↔ `Foo` ↔ XAML 속성 |
| 속성 변경 알림 | `OnPropertyChanged("Foo")` — **문자열** |
| 타입 참조 | `{x:Type local:Bar}` · `TargetType` · `DataType` · `x:Class` |
| 인터페이스 계약 | `I` 로 시작하는 기반 타입의 public 멤버 |
| 리플렉션 | `GetMethod("Foo")` · `GetProperty` |
| 이벤트 구독 | `foo.Bar += Baz;` |
| resx | `.resx` 키 |
| SQL ID | `DPICALL("lot.selectMcLot")` ↔ mapper `<select id=…>` |

**하나라도 빠지면 그 종류의 코드가 전부 "죽었다"고 나옵니다.**

여기서 한 가지를 배웠습니다 — 초기 버전은 `Height="Auto"` 의 `Auto` 같은
**열거형 값까지 핸들러로 셌습니다.** 그래서 맨몸 식별자는 **메서드 이름과
맞아떨어질 때만** 참조로 인정하도록 좁혔습니다.

### ③ 확신 등급이 우선순위의 상한이다

인덱서는 단정하지 않습니다.

| 확신 | 언제 | 최대 우선순위 |
|---|---|---|
| **높음** | `private`/`internal`, WPF 경로 어디에도 안 걸림 | `먼저` |
| **중간** | `public`/`protected` — 대상 경로 밖에서 쓸 수 있음 | `다음` |
| **낮음** | 상속·특성·리플렉션이 얽힘 | `참고` |

`중간` 은 **"지우세요"가 아니라 "확인하고 지우세요"** 로 씁니다.
이 하네스는 대상 경로만 봤으니, 그 이상을 말하면 거짓말이 됩니다.

### ④ 부탁이던 두 줄이 장치가 됐다

> XAML 에서만 쓰이는 코드를 죽은 코드로 오인하지 않는다.
> 대상 경로 밖의 사용을 단정하지 않는다.

문장만 있으면 모델은 급할 때 무시합니다. 그래서 세 곳에 걸었습니다.

1. **인덱서** — `wpfHints` 가 있으면 `unreferenced[]` 에 **아예 올리지 않습니다**
2. **제안자 프롬프트** — "인덱스에 없는 것을 미참조라고 말하지 마세요"
3. **검증관의 `V-4`** — 그래도 말하면 `REJECTED`

3번이 핵심입니다. **지키라고 부탁하는 대신 안 지키면 걸러냅니다.**

### ⑤ 두 축이 "어디부터"를 결정한다

08 은 주의 등급 하나였습니다. 리팩토링 제안에는 부족합니다.

```
          비용 작음      비용 보통      비용 큼
먼저   │ ★ 이번 주   │  다음 스프린트 │  계획에 넣기
다음   │  틈날 때    │  다음 분기     │  당장은 아님
참고   │  기록만     │  기록만        │  기록만
```

리포트의 **`먼저 · 비용 작음`** 칩 하나가 왼쪽 위 칸만 남깁니다.

### ⑥ 「지금은 두는 게 낫습니다」가 신뢰를 만든다

전부 고치라고 적힌 문서는 아무도 따르지 않습니다.
"이건 두세요" 가 있어야 나머지가 진짜 권고로 읽힙니다.

비어 있으면 `build-report.py` 가 경고합니다.

### ⑦ 모델 없이 하네스를 점검할 수 있다

`ws.py --selftest` 가 수집 → 인덱싱 → 리포트 렌더를 샘플로 돌리고,
심어 둔 결함이 잡히는지와 **WPF 함정이 걸러지는지**를 확인합니다.

```
3. 죽은 코드를 잡았나
  ✓ `MaxRowCount` 가 미참조(확신 높음)로 잡혔습니다
  ✓ `SearchLotByLine` 가 미참조(확신 높음)로 잡혔습니다

4. WPF 함정을 피했나  ← 이 하네스의 핵심
  ✓ `btnSearch_Click` 를 죽은 코드로 오인하지 않았습니다
  ✓ `LotStatusConverter` 를 죽은 코드로 오인하지 않았습니다
```

**토큰이 한 푼도 들지 않습니다.** 복사해 간 저장소에서도 그대로 돕니다.

---

## 6. 무엇이 남나

```
_workspace/scan-YOEDSMOV/
├── STATUS.md                 진행판
├── 1-meta.json               대상·규모·mapper 수집 결과
├── 1-files.json              파일별 종류·줄 수·최종 수정일
├── src/…                     대상 소스 원문
├── src-sql/…                 mapper XML
├── 1-index.json              ★ 기계가 센 것 — 검증관이 대조하는 사실
├── 1-index.md                위의 사람이 읽는 요약
├── 1-scope.md                이 코드가 하는 일
├── 1-units.md                대상 단위 표 (U1, U2 …)
├── 2-suggest-convention.md
├── 2-suggest-hygiene.md
├── 2-suggest-design.md
├── 2-suggest-sql.md
├── 3-verify.md               V-1~V-7 판정
├── 3-roadmap.md              개선 로드맵
├── 4-findings.json           HTML 입력
└── refactor-YOEDSMOV.html    ★ 회의에서 여는 파일
```

**아무도 지우지 않습니다.** 같은 대상을 새로 돌리면 `.prev-<시각>` 으로 밀어냅니다.
정리는 사람이 합니다.

## 7. HTML 리포트 — 회의에서 하는 일

**요약이 먼저, 코드는 나중입니다.**

| 순서 | 무엇 |
|---|---|
| 1 | **이 코드가 하는 일** |
| 2 | **개선 로드맵** (+ 지금은 두는 게 나은 것) |
| 3 | **기계가 센 것** — 모델이 쓴 숫자가 아님을 명시 |
| 4 | **대상 요약** — 단위별 "무엇인가" + 제안 건수 |
| 5 | 파일 → 단위 → 제안 카드 (코드는 기본으로 접힘) |

| 기능 | 쓰임 |
|---|---|
| **`먼저 · 비용 작음` 칩** | 이번 주에 할 일만 남깁니다 |
| 3종 필터 (우선순위·비용·관점) | 겹쳐 걸 수 있습니다 |
| **C# · XAML · SQL 하이라이트** | 외부 라이브러리 없이 내장 |
| **[하기로] [보류] [안 함]** + 메모 | `localStorage`, 키 = `oi-refactor-<slug>` |
| 마크다운 / JSON 내보내기 | 회의 결과를 그대로 |
| 인쇄 | 전부 펼쳐진 상태로. **화면이 다크여도 종이는 밝게** |
| **외부 요청 0** | 폐쇄망에서 그냥 열립니다 |

## 8. 처음 쓰는 사람을 위한 순서

### 준비물

| | |
|---|---|
| **Python 3.8+** | `python --version`. **pip 설치 불필요** |
| OpenCode | 프로바이더 인증이 되어 있어야 합니다 |
| git | **선택** |

`gh` 는 필요 없습니다.

### ① 모델 없이 — 스크립트가 도는지

```bash
cd 09-refactor-oi
python .opencode/skills/refactor-oi-scan/assets/ws.py --doctor
python .opencode/skills/refactor-oi-scan/assets/ws.py --selftest
```

**토큰이 들지 않습니다.** 여기서 통과하면 파이프라인은 살아 있는 것입니다.

### ② 오프라인 데모 — 에이전트까지

```bash
opencode run "/refactor-sample"
```

`_workspace/scan-sample/refactor-sample.html` 이 나옵니다.
샘플에는 네 관점 결함과 **WPF 오탐 함정**이 함께 심어져 있으니,
맨 아래 **반려된 제안**을 펴서 `V-4` 가 무엇을 잡았는지 보세요.

### ③ 실제 코드는 Phase 1 부터

```bash
opencode run "/scan-only YOEDSMOV"
```

대상 단위가 맞는지 먼저 봅니다. **여기가 틀리면 뒤가 전부 틀어집니다.**

### ④ 전체 사이클

```bash
opencode run "/refactor YOEDSMOV"
```

### 커맨드 여섯 개

| 커맨드 | 무엇 |
|---|---|
| `/refactor <경로>` | 전체 사이클 |
| `/scan-only <경로>` | Phase 1 만 |
| `/report-only <경로>` | HTML 만 재생성 |
| `/refactor-sample` | 오프라인 데모 |
| `/status` | 진행 중인 모든 분석 |
| `/doctor` | 설치·환경 점검 |

### ⑤ 우리 저장소로 옮기기

`.opencode/` 와 `opencode.jsonc` 를 **저장소 루트에** 복사합니다.
그다음 `mapper-dir.txt` 에 팀의 mapper 경로를 넣고 `/doctor` 를 돌리세요.

`opencode.jsonc` 를 빠뜨리면 **`subagent_depth: 1` 이 사라져 4인 동시 제안이 막힙니다.**

## 9. 막히면

| 증상 | 원인 | 어떻게 |
|---|---|---|
| 제안이 하나도 안 나온다 | 대상 단위가 0개 | `/scan-only` 로 `1-units.md` 를 확인. 경로를 넓히세요 |
| 제안이 200건 나온다 | 대상이 너무 넓음 | 화면 하나로 좁히세요. 규모 게이트가 원래 막습니다 |
| 멀쩡한 코드가 "안 쓰인다"고 나온다 | 인덱서가 못 본 참조 경로 | `1-index.json` 의 `wpfHints` 를 보세요. 새 경로면 `index.py` 에 추가할 자리입니다 |
| SQL 미사용 판정이 없다 | mapper 를 못 가져옴 | `1-meta.json` 의 `mapperNote`. `mapper-dir.txt` 에 매핑을 추가하세요 |
| 리포트에 코드가 안 보인다 | `sourceFile` 경로 어긋남 | mapper 는 `src-sql/…` 로 적어야 합니다 |
| 4인 동시 호출이 안 된다 | `opencode.jsonc` 누락 | 저장소 **루트**에 두세요 |
| 스크립트가 파일을 못 읽는다 | PowerShell 5.1 의 `>` 가 UTF-16LE 로 씀 | 스크립트가 감지해 경고합니다. `collect.py` 를 쓰면 안 생깁니다 |

## 10. 치트시트

```bash
# 점검 (토큰 0)
python .opencode/skills/refactor-oi-scan/assets/ws.py --doctor
python .opencode/skills/refactor-oi-scan/assets/ws.py --selftest
python .opencode/skills/refactor-oi-scan/assets/ws.py --list

# 스크립트 단독
S=.opencode/skills/refactor-oi-scan
python $S/assets/collect.py --path YOEDSMOV --ws _workspace/scan-YOEDSMOV
python $S/assets/index.py --ws _workspace/scan-YOEDSMOV
python $S/assets/build-report.py _workspace/scan-YOEDSMOV/4-findings.json \
                                 _workspace/scan-YOEDSMOV/refactor-YOEDSMOV.html

# 커맨드
opencode run "/doctor"
opencode run "/refactor-sample"
opencode run "/scan-only YOEDSMOV"
opencode run "/refactor YOEDSMOV"
opencode run "/report-only YOEDSMOV"
opencode run "/status"
```

| 어휘 | 값 |
|---|---|
| 우선순위 | `먼저` · `다음` · `참고` |
| 비용 | `작음` · `보통` · `큼` |
| 관점 | `convention` · `hygiene` · `design` · `sql` |
| 단위 유형 | `클래스` · `메서드` · `프로퍼티` · `필드` · `이벤트 핸들러` · `XAML` · `SQL` |
| 판정 | `CONFIRMED` · `NEEDS-INFO` · `REJECTED` |
| 확신 | `높음` · `중간` · `낮음` |

## 더 읽을 것

- [README.md](../README.md) — 실행법, 패턴이 보이는 지점 ①~⑪, 파일 구조
- [../08-code-review-oi/docs/how-it-works.md](../../08-code-review-oi/docs/how-it-works.md) — PR 코드리뷰 하네스
- [SKILL.md](../.opencode/skills/refactor-oi-scan/SKILL.md) — 스킬 진입점
