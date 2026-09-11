# 09 · 실전 · 리팩토링 제안 → 팀 회의용 HTML

> **한 줄로**: 08 이 **바뀐 것**을 보는 하네스라면, 09 는 **이미 있는 것**을 보는 하네스입니다.
> 코드를 고치지 않고, **"그래서 뭐부터 할까"** 에 답하는 파일 하나를 내놓습니다.

08 은 PR 변경분을 리뷰합니다. diff 가 "무엇을 볼지"를 공짜로 정해 줍니다.
09 에는 그런 경계가 없습니다. **소스 전체가 대상**이기 때문입니다.

그래서 이 하네스는 **기계적 인덱서**를 Phase 1 에 넣었습니다.
`index.py` 가 심볼·참조·중복·SQL 을 전수 조사하고, 네 제안자는 그 후보를 **판정만** 합니다.

> 📖 **동작 원리를 알고 싶거나 남에게 설명해야 한다면 → [docs/how-it-works.md](docs/how-it-works.md)**

## 바로 실행하기

```bash
cd 09-refactor-oi

# 모델을 한 번도 부르지 않고 스크립트가 도는지 확인 — 여기부터 권합니다
python .opencode/skills/refactor-oi-scan/assets/ws.py --selftest

# 딸린 샘플로 도는 오프라인 데모
opencode run "/refactor-sample"

# 실제 경로 전체 사이클
opencode run "/refactor YOEDSMOV"

# Phase 1 만 — 무엇을 볼지가 맞는지 먼저 확인
opencode run "/scan-only YOEDSMOV"

# HTML 만 다시 생성 / 진행 중인 모든 분석
opencode run "/report-only YOEDSMOV"
opencode run "/status"

# 돌 준비가 됐는지 점검
opencode run "/doctor"
```

**두 화면을 동시에 분석할 수 있습니다.** 터미널 두 개에서 각각 돌리면 됩니다.

```bash
# 터미널 1                        # 터미널 2
opencode run "/refactor YOEDSMOV"  opencode run "/refactor YOSTKMGR"
#   → _workspace/scan-YOEDSMOV/        → _workspace/scan-YOSTKMGR/
```

**LLM 없이 렌더링만 보고 싶다면** 빌드 스크립트를 단독으로 돌릴 수 있습니다.

```bash
S=.opencode/skills/refactor-oi-scan
python $S/assets/build-report.py $S/sample/expected-findings.json /tmp/out.html
# → /tmp/out.html 을 브라우저로 열어 보세요
```

## 무엇을 보여주는 샘플인가

C# WPF(MES 화면) 코드를 훑습니다. 등장인물은 여덟입니다.

| Phase | 담당 | 패턴 | 하는 일 | 모델 |
|---|---|---|---|---|
| 0~4 | `refactor-lead` | 오케스트레이션 | 게이트 판단 · 동시 호출 · **개선 로드맵 서술** | **고가** |
| 1 | `code-scoper` | 파이프라인 | `collect.py` · `index.py` → **대상 단위(U1, U2 …) 확정** | **고가** |
| 2 | `refac-convention` | **팬아웃** | 명명·컨벤션 (`naming-rules.md`) | 무난 |
| 2 | `refac-hygiene` | **팬아웃** | 중복·미참조 (`hygiene-rules.md`) | **고가** |
| 2 | `refac-design` | **팬아웃** | 가독성·성능 구조 (`design-rules.md`) | **고가** |
| 2 | `refac-sql` | **팬아웃** | mapper·인라인 SQL (`read-sql.md`) | **고가** |
| 3 | `refac-verifier` | **생성-검증** | 제안을 원문·인덱스와 대조해 오탐 반려 | **고가** |
| 4 | `report-builder` | 파이프라인 | findings.json → 스크립트 → HTML | 무난 |

**08 과 마찬가지로 저렴 등급을 쓰지 않습니다.** 틀린 제안의 비용이 모델 비용보다 큽니다.

| 자리 | 틀리면 |
|---|---|
| `code-scoper` | 무엇을 볼지를 여기서 정합니다. 틀리면 **뒤의 네 제안자가 전부 틀린 것을 봅니다** |
| `refac-hygiene` | **"이 코드는 아무도 안 씁니다"** 를 말하는 자리입니다. 이 하네스에서 오탐 비용이 가장 큽니다 |
| `refac-design` | 구조를 바꾸자고 말합니다. 근거가 약하면 회의가 통째로 구조 논쟁이 됩니다 |
| `refac-sql` | 운영 DB 로 나가는 쿼리입니다 |
| `refac-verifier` | 오탐을 놓치면 **회의 시간이 통째로 날아갑니다** |
| `refactor-lead` | 게이트를 여기서 열고, **로드맵을 직접 씁니다.** `primary` 라 대화 턴마다 도는 자리입니다 |

## 패턴이 보이는 지점

### ① 기계가 먼저 세고, 모델은 판정만 한다

08 은 diff 가 경계를 줬습니다. 09 에는 없습니다.
그래서 `index.py` 가 먼저 **전수 조사**를 합니다.

```
index.py 가 센 것          제안자가 할 일
──────────────────────     ──────────────────────────────
unreferenced[]        →    정말 지워도 되나? 확신은 몇인가?
duplicateCandidates[] →    합칠 수 있나? 합치면 무엇이 나아지나?
sql.unusedIds         →    정말 아무도 안 부르나?
```

LLM 에게 `grep` 을 시켜 "안 쓰는 코드를 찾아라" 하면 **반드시 몇 개를 놓칩니다.**
전수 조사는 기계가 해야 합니다. 모델은 그 후보에 **맥락을 붙이는 일**을 합니다.

리포트에도 그 구분이 남습니다 — 「기계가 센 것」 절에
**"모델이 쓴 숫자가 아닙니다"** 라고 적혀 있습니다.

### ② WPF 에서 "안 쓰인다"고 말하기가 어렵다

이 하네스가 가장 크게 틀릴 수 있는 자리입니다.
WPF 는 **C# 에 호출부가 없는 것이 정상인 코드**를 잔뜩 만듭니다.

```csharp
private void btnSearch_Click(object sender, RoutedEventArgs e)  // C# 호출부: 0곳
```
```xml
<Button Click="btnSearch_Click" />                              <!-- 여기서 부릅니다 -->
```

순진한 grep 은 이걸 죽은 코드로 봅니다. 그래서 인덱서가 **열네 가지 경로**를 봅니다.

| 경로 | 예 |
|---|---|
| 이벤트 핸들러 | `Click=` · `Loaded=` · `EventSetter Handler=` |
| `x:Name` | `x:Name="btnGo"` ↔ C# 의 `btnGo` |
| 데이터 바인딩 | `{Binding LotStatus}` · `{Binding Path=Foo.Bar}` |
| 명령 | `Command="{Binding SaveCommand}"` |
| 리소스 키 | `x:Key` ↔ `{StaticResource}` · `{DynamicResource}` |
| 컨버터 | `IValueConverter` 구현이 `x:Key` 로만 등록됨 |
| 의존 속성 | `FooProperty` ↔ `Foo` ↔ XAML 속성 |
| 속성 변경 알림 | `OnPropertyChanged("Foo")` — **문자열** |
| 타입 참조 | `{x:Type local:Bar}` · `TargetType` · `DataType` · `x:Class` |
| 인터페이스 계약 | `IValueConverter.Convert` 는 프레임워크가 부릅니다 |
| 리플렉션 | `GetMethod("Foo")` |
| 이벤트 구독 | `foo.Bar += Baz;` |
| resx | `.resx` 키 ↔ `Resources.Foo` |
| SQL ID | `DPICALL("lot.selectMcLot")` ↔ mapper `<select id=…>` |

하나라도 빠지면 **그 종류의 코드가 전부 "죽었다"고 나옵니다.**
샘플에 이 함정 10종을 일부러 심어 두었고, `--selftest` 가 매번 확인합니다.

### ③ 확신 등급이 우선순위의 상한이다

인덱서는 "안 쓰인다"를 세 등급으로 말합니다. 단정하지 않습니다.

| 확신 | 언제 | 제안자가 올릴 수 있는 최대 |
|---|---|---|
| **높음** | `private`/`internal` 이고 WPF 경로 어디에도 안 걸림 | `먼저` |
| **중간** | `public`/`protected` — **대상 경로 밖**에서 쓸 수 있음 | `다음` |
| **낮음** | 상속·특성·리플렉션이 얽힘 | `참고` |

`중간` 은 **"지우세요"가 아니라 "확인하고 지우세요"** 로 씁니다.
이 하네스는 대상 경로만 봤기 때문에, 그 이상을 말할 수 없습니다.

### ④ 검증이 오탐을 잡는다 — `V-4`

08 의 `V-1` 이 "기존 코드 지적"을 막았듯, 여기서는 `V-4` 가
**"XAML 에서만 쓰이는 코드를 죽었다고 말하는 것"** 을 막습니다.

| 검사 | 반려 사유 |
|---|---|
| V-1 | 인용한 단위가 표에 없음 → 범위 밖 |
| V-2 | 인용 코드가 `src/` 원문과 불일치 → 존재하지 않는 코드 |
| V-3 | 근거로 든 규칙이 참조 문서에 없음 → 지어낸 규칙 |
| **V-4** | **미참조 지적인데 인덱스에 `wpfHints` 가 있음 → WPF 오탐** |
| V-5 | 중복 지적인데 인덱스의 중복 후보가 아님 |
| V-6 | `먼저` 인데 무엇이 나아지는지 없음 → **`다음` 으로 강등** |
| V-7 | `비용: 작음` 인데 영향을 세지 않음 → **`보통` 으로 상향** |

반려된 제안은 **지우지 않고** HTML 맨 아래 접이식 절에 남습니다. 감사 흔적입니다.

### ⑤ 두 축이 "어디부터"를 결정한다

08 은 주의 등급 하나였습니다. 리팩토링 제안은 그것으로 부족합니다.
팀이 실제로 묻는 것은 **"그래서 뭐부터 해요?"** 이고, 그 답에는 축이 둘 필요합니다.

```
          비용 작음      비용 보통      비용 큼
먼저   │ ★ 이번 주   │  다음 스프린트 │  계획에 넣기
다음   │  틈날 때    │  다음 분기     │  당장은 아님
참고   │  기록만     │  기록만        │  기록만
```

리포트 맨 위 **`먼저 · 비용 작음`** 칩 하나가 왼쪽 위 칸만 남깁니다.
그게 이번 주에 할 일입니다.

### ⑥ 로드맵에 「지금은 두는 게 낫습니다」가 있다

**이 절이 리포트의 신뢰를 만듭니다.**

전부 고치라고 적힌 문서는 아무도 따르지 않습니다.
"이건 두세요" 가 있어야 나머지가 진짜 권고로 읽힙니다.

> - `Bind()` 는 `public` 이라 다른 화면이 쓸 수 있습니다. 저장소 전체를 훑기 전에는 지우지 마세요
> - `LotStatusConverter` 처럼 XAML 에서만 불리는 코드는 그대로 두세요. C# 에 호출부가 없는 것이 정상입니다
> - 그리드 컬럼을 양쪽에 적은 것은 중복이지만, 지금 한쪽을 지우면 화면이 바뀝니다

비어 있으면 `build-report.py` 가 경고합니다.

### ⑦ 순서를 만드는 것이 오케스트레이터의 일이다

제안자 넷은 각자 자기 것만 봅니다.
네 묶음을 한자리에 놓고 **순서**를 만들 수 있는 것은 오케스트레이터뿐입니다.

그래서 `3-roadmap.md` 는 **위임하지 않습니다.** 08 의 종합 평가와 같은 자리입니다.

제안자들은 `영향` 칸에 의존 관계를 적어 그 일을 돕습니다.

> D001 로 `MoveOutLots()` 를 떼어 낸 뒤에 하면 바꿀 자리가 한 함수로 좁혀집니다.

### ⑧ LLM 이 코드를 옮겨 적지 않는다

08 과 같은 원칙입니다. `report-builder` 가 만드는 것은 `4-findings.json` 하나이고,
HTML 은 `build-report.py` 가 만듭니다.

```
src/…          ─┐
1-index.json   ─┼→ build-report.py → HTML
4-findings.json ┘   (제안 내용 + 좌표만)
```

**기계가 센 숫자도 LLM 을 거치지 않습니다.** `indexSummary` 는 스크립트가
`1-index.json` 에서 직접 읽어 싣습니다.

유일한 예외가 `suggestion` 입니다 — 제안 코드는 본래 원문에 없으니 JSON 에 들어올
수밖에 없습니다. 그래서 리포트가 그 칸을 **「제안」으로 따로 표시**해 원문과 섞이지 않게 합니다.

### ⑨ 문법 하이라이트를 08 에서 그대로 물려받았다

폐쇄망에서 열려야 하므로 CDN 을 못 씁니다(외부 요청 0).
C# · XAML · SQL 토크나이저가 템플릿 안에 들어 있고, **여러 줄에 걸친 블록 주석과
축자 문자열(`@"…"`), 줄을 넘어가는 XAML 속성**까지 상태를 들고 갑니다.

diff 렌더링만 걷어냈습니다 — 여기서는 바뀐 것이 없으니 **원문을 그대로** 싣습니다.

### ⑩ 규모 게이트가 있다

소스 전체를 대상으로 삼을 수 있다는 것은 **너무 크게 잡을 수 있다**는 뜻이기도 합니다.

파일 200개 또는 30,000줄을 넘으면 오케스트레이터가 **멈추고 경로를 좁히라고 요구**합니다.
그 규모에서 나온 제안 200건은 아무도 읽지 않습니다.

### ⑪ 모델 없이 하네스를 점검할 수 있다

`ws.py --selftest` 가 **수집 → 인덱싱 → 리포트 렌더**를 샘플로 한 번 돌리고,
심어 둔 결함이 잡히는지와 **WPF 함정이 걸러지는지**를 확인합니다.

```
4. WPF 함정을 피했나  ← 이 하네스의 핵심
  ✓ `btnSearch_Click` 를 죽은 코드로 오인하지 않았습니다
  ✓ `LotStatusConverter` 를 죽은 코드로 오인하지 않았습니다
  …
```

복사해 간 저장소에서도 그대로 돕니다. **토큰이 한 푼도 들지 않습니다.**

## HTML 리포트가 회의에서 하는 일

`_workspace/scan-<slug>/refactor-<slug>.html` — 브라우저로 그냥 열면 됩니다.
**외부 요청 0건**, 폐쇄망에서 동작합니다.

| 순서 | 무엇 | 쓰임 |
|---|---|---|
| 1 | **이 코드가 하는 일** | 무엇을 하는 코드이고 규모가 얼마인지 |
| 2 | **개선 로드맵** | 그래서 뭐부터 할지 (+ 지금은 두는 게 나은 것) |
| 3 | **기계가 센 것** | 미참조·중복·미사용 SQL 건수. 모델이 쓴 숫자가 아님을 명시 |
| 4 | **대상 요약** | 단위별 "무엇인가" + 제안 건수 |
| 5 | 파일 → 단위 → 제안 카드 | **코드 블록은 기본으로 접혀 있습니다** |

| 기능 | 쓰임 |
|---|---|
| **`먼저 · 비용 작음` 칩** | 한 번 눌러 이번 주에 할 일만 남깁니다. 이 리포트의 핵심 장치 |
| 우선순위 · 비용 · 관점 **3종 필터** | 겹쳐 걸 수 있습니다 |
| **C# · XAML · SQL 문법 하이라이트** | 외부 라이브러리 없이 내장 |
| 검색 | 제안 내용·파일·근거를 한 번에 |
| **[하기로] [보류] [안 함]** + 메모 | 브라우저에 저장 (`oi-refactor-<slug>`) |
| **⚙ 설정 메뉴** | 마크다운 복사 · 결정 JSON 저장 · 코드 펼치기 · 결정 초기화 · 테마 · 인쇄 |
| 인쇄 (`Ctrl+P`) | 필터·메뉴가 사라지고 전부 펼쳐진 상태로 출력. 화면이 다크여도 종이는 밝게 |

> `findings[].title` 과 `units[].summary` 가 이 리포트의 얼굴입니다.

## 직접 바꿔 보기

- **`--selftest` 를 먼저 돌리세요.** 토큰이 들지 않고, 무엇이 확인되는지 한눈에 보입니다.
- **`index.py` 의 `EVENT_ATTRS` 에서 `Click` 을 빼 보세요.** `btnSearch_Click` 이 갑자기
  "죽은 코드" 로 잡힙니다. 인덱서가 WPF 를 모르면 어떻게 되는지 바로 보입니다.
- **`/scan-only` 로 실제 화면을 걸어 보세요.** 대상 단위가 맞는지만 확인하는 커맨드입니다.
  **여기가 틀리면 뒤가 전부 틀어지므로** 실 적용은 이것부터 하는 게 안전합니다.
- **검증관을 빼 보세요.** `refac-verifier.md` 를 `.bak` 으로 바꾸면 WPF 오탐이 그대로
  회의 자료에 실립니다. 샘플 `expected-findings.json` 의 `rejected` 3건이 본문에 섞이는 상태입니다.
- **제안자를 하나 빼 보세요.** `refac-sql.md` 를 `.bak` 으로 바꾸면 SQL 제안이 통째로 사라집니다.
- **`4-findings.json` 을 일부러 망가뜨려 보세요.** `effort` 를 `중간` 으로 바꾸고 스크립트를
  돌리면 검증에서 걸립니다. LLM 이 스키마를 어겼을 때 무엇이 막아 주는지 볼 수 있습니다.
- **`DUP_THRESHOLD` 를 0.5 로 내려 보세요.** 중복 후보가 쏟아집니다.
  임계값이 왜 0.75 인지, 후보가 너무 많으면 왜 쓸모없는지 알 수 있습니다.
- **자기 팀 규칙으로 바꿔 보세요.** `references/naming-rules.md` 를 팀 컨벤션으로 갈아 끼우면
  컨벤션 제안자의 판정 기준이 통째로 바뀝니다. 에이전트는 손대지 않습니다.

## Windows · PowerShell 에서 돌릴 때

08 과 같은 입장입니다. **PowerShell 을 기본 환경으로 가정**했습니다.

| Unix 에서 쓰던 것 | PowerShell 에서 |
|---|---|
| `ls -la` | `-la` 라는 파라미터가 없어 **오류** |
| `mkdir -p foo/bar` | `-p` 가 없어 **오류** |
| `$(dirname …)` · `$(date +%Y%m%d)` | 그런 명령이 **없음** |
| **`명령 > 파일`** | Windows PowerShell 5.1 은 **UTF-16LE** 로 씁니다 |

마지막 줄이 가장 위험합니다. **오류가 나지 않습니다.** 그래서 파일을 만드는 일은
전부 Python 스크립트가 합니다. 에이전트에게 남은 bash 권한도 그래서 짧습니다.

| 에이전트 | 열린 명령 |
|---|---|
| `code-scoper` | `python` · `git log` · `git rev-parse` |
| `report-builder` | `python` |
| `refactor-lead` | `python`(ws.py 만) · `git status` · `git rev-parse` |
| 제안자 3인 | `git log` |
| `refac-sql` | 위 + 검색기 (`rg` · `findstr` · `Select-String` · `grep`) |

`collect.py` · `index.py` · `build-report.py` 는 **UTF-16 을 감지해 디코딩하고 경고**합니다.
다른 경로로 만든 파일이 섞여 들어와도 조용히 깨지지 않습니다.

### 필요한 것

| | |
|---|---|
| **Python 3.8+** | 스크립트 넷이 씁니다. **pip 설치는 필요 없습니다** — 표준 라이브러리만 |
| git | **선택**입니다. 있으면 파일별 최종 수정일이 붙습니다 |
| ripgrep | 선택. mapper 수집이 실패했을 때 저장소 밖 검색이 빨라집니다 |

**`gh` 는 필요 없습니다.** 이 하네스는 PR 이 아니라 소스 경로를 봅니다.

## 실제 저장소에 적용하려면

**저장소 루트에 두 가지를 놓으면 끝입니다.**

| 옮길 것 | 어디에 | 왜 |
|---|---|---|
| `.opencode/` | 저장소 루트 | 에이전트·커맨드·스킬·스크립트·데모 재료가 전부 이 안에 있습니다 |
| `opencode.jsonc` | 저장소 루트 | **`.opencode/` 안에 두면 안 읽힙니다** |

```powershell
# PowerShell
Copy-Item -Recurse 09-refactor-oi\.opencode      D:\Git\OY_SWP\
Copy-Item          09-refactor-oi\opencode.jsonc D:\Git\OY_SWP\
```

```bash
# bash / zsh
cp -r 09-refactor-oi/.opencode      /path/to/OY_SWP/
cp    09-refactor-oi/opencode.jsonc /path/to/OY_SWP/
```

### `opencode.jsonc` 를 빠뜨리면

빠뜨려도 겉으로는 잘 도는 것처럼 보입니다 — 에이전트마다 `model:` 과 `permission:` 을
자기 frontmatter 에 다 갖고 있기 때문입니다. 하지만 **`subagent_depth: 1` 이 사라져
Phase 2 의 4인 동시 호출(팬아웃)이 막힙니다.**

대상 저장소에 이미 `opencode.jsonc` 가 있으면 덮어쓰지 말고 **병합**하세요.

```jsonc
"subagent_depth": 1,                                  // 필수 — 팬아웃
"permission": { "edit": "deny", "bash": "ask" }       // 권장 — 전역 안전망
```

### 그다음 고칠 곳 세 군데

| 파일 | 고칠 것 |
|---|---|
| `.opencode/skills/refactor-oi-scan/mapper-dir.txt` | 팀의 mapper 경로 매핑. **없으면 SQL 미사용 판정을 건너뜁니다**(분석 자체는 됩니다) |
| `.opencode/agents/*.md` 의 `model:` | 쓰는 프로바이더의 모델 이름 |
| `.gitignore` | `_workspace/*` 를 무시하도록 (`!_workspace/README.md` 예외) |

### 잘 옮겨졌는지 확인

```bash
opencode run "/doctor"     # 빠진 게 있으면 무엇을 하라는지까지 알려 줍니다

# 그다음, 모델 없이 스크립트가 도는지
python .opencode/skills/refactor-oi-scan/assets/ws.py --selftest

# 마지막으로 오프라인 데모 (모델을 씁니다)
opencode run "/refactor-sample"
```

`_workspace/scan-sample/refactor-sample.html` 이 나오면 하네스가 살아 있는 것입니다.

## 08 과 무엇이 다른가

| | 08 코드리뷰 | 09 리팩토링 제안 |
|---|---|---|
| 입력 | PR 번호 | **소스 경로** |
| 경계 | diff 가 정해 줌 | **`index.py` 가 후보를 뽑고 `code-scoper` 가 고름** |
| 단위 ID | `L1` (변경단위) | `U1` (대상 단위 — 클래스·메서드·XAML·SQL) |
| 관점 | 3인 (리팩토링·기능·SQL) | **4인** (컨벤션·중복/미사용·구조·SQL) |
| 등급 | 꼭 확인·확인 권장·참고 | **먼저·다음·참고 × 작음·보통·큼** |
| 코드 표시 | diff (add/del·좌우 보기) | **원문 그대로** |
| 마무리 | 종합 평가 | **개선 로드맵** (+ 「지금은 두는 게 낫습니다」) |
| 외부 의존 | `gh` 필요 | **없음** (git 도 선택) |
| 자체 점검 | 없음 | **`--selftest`** — 모델 없이 파이프라인 검증 |
| 같은 것 | `.opencode/` 배치 · 파일로 잇는 Phase · `edit: deny` · 게이트 · 얇은 SKILL.md · **내장 하이라이터** · 인쇄 · 폐쇄망 | |

## 파일 구조

```
09-refactor-oi/
├── opencode.jsonc                     ← 복사 대상. 전역 edit: deny · subagent_depth: 1
├── .opencode/                         ← 복사 대상 (아래 전부)
│   ├── agents/
│   │   ├── refactor-lead.md             오케스트레이터 (primary, 고가) ← 게이트·로드맵
│   │   ├── code-scoper.md               Phase 1 · 대상 단위 확정 (고가) ← 틀리면 뒤가 전부 틀어짐
│   │   ├── refac-convention.md          Phase 2 · 명명·컨벤션 (무난)
│   │   ├── refac-hygiene.md             Phase 2 · 중복·미참조 (고가) ← 오탐 비용 최대
│   │   ├── refac-design.md              Phase 2 · 구조·가독성·성능 (고가)
│   │   ├── refac-sql.md                 Phase 2 · SQL (고가) ← 유일하게 저장소 밖을 볼 수 있음
│   │   ├── refac-verifier.md            Phase 3 · 제안 검증 V-1~V-7 (고가)
│   │   └── report-builder.md            Phase 4 · findings.json (무난)
│   ├── commands/
│   │   ├── refactor.md                  /refactor <경로>        전체 사이클
│   │   ├── scan-only.md                 /scan-only <경로>       Phase 1 만
│   │   ├── report-only.md               /report-only <경로>     HTML 만 재생성
│   │   ├── refactor-sample.md           /refactor-sample        오프라인 데모
│   │   ├── status.md                    /status                 진행 중인 모든 분석
│   │   └── doctor.md                    /doctor                 설치·환경 점검
│   └── skills/refactor-oi-scan/
│       ├── SKILL.md                     진입점 (얇게 유지)
│       ├── mapper-dir.txt               ★ 팀 환경에 맞게 고치는 파일
│       ├── references/
│       │   ├── naming-rules.md          명명 규칙 8종 (08 에서 가져와 2축으로 손봄)
│       │   ├── hygiene-rules.md         K-* 죽은 코드 · P-* 중복 + ★WPF 참조 경로 표
│       │   ├── design-rules.md          A-1~A-11 가독성·성능 체크리스트
│       │   ├── read-sql.md              mapper 읽는 절차 · Q-1~Q-9
│       │   ├── suggest-format.md        4인 공통 출력 형식 · 우선순위·비용 기준
│       │   └── html-report.md           findings.json 스키마
│       ├── assets/
│       │   ├── collect.py               경로 → src/ · src-sql/ 수집 (셸 비의존, UTF-8 고정)
│       │   ├── index.py                 ★ 심볼·참조·중복·SQL 인덱서 (WPF 경로 14종)
│       │   ├── ws.py                    목록 · 점검 · ★자체 점검 (/status · /doctor)
│       │   ├── report-template.html     단일 파일 HTML 골격 (인라인 CSS/JS)
│       │   └── build-report.py          스키마 검증 + 렌더 (표준 라이브러리만)
│       └── sample/                      /refactor-sample 재료
│           ├── src/YOEDSMOV/…           네 관점 결함 + ★WPF 오탐 함정 10종
│           ├── mapper/lot/lot.xml       가짜 iBATIS mapper (미사용·중복 SQL 포함)
│           ├── expected-index.json      --selftest 기대값
│           └── expected-findings.json   build-report.py 단독 테스트용 고정 입력
├── docs/
│   └── how-it-works.md                  ★ 동작 원리 · 발표용 · 입문용
└── _workspace/
    ├── README.md                        단계 사이 우편함 규약
    └── scan-<slug>/                     실행할 때 생김 — 대상 하나에 폴더 하나 (.gitignore)
```

**실무 저장소로 옮기는 단위는 `.opencode/` 와 `opencode.jsonc` 두 개뿐입니다.**
