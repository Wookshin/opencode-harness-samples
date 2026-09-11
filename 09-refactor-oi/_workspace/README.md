# `_workspace/` — 단계 사이의 우편함

에이전트끼리는 **직접 대화할 수 없습니다.** 각자 별도 세션에서 일하기 때문입니다.
그래서 각 단계는 여기에 파일을 남기고, 다음 단계가 그것을 읽습니다.

오케스트레이터는 프롬프트에 **경로만** 적습니다.

```
task(subagent_type="refac-hygiene",
     prompt="작업 폴더는 _workspace/scan-YOEDSMOV 입니다.
             _workspace/scan-YOEDSMOV/1-index.md 와 1-units.md 를 읽고 …")
```

계획서 전문을 붙여 넣지 않습니다. **경로 한 줄이면 됩니다.**

## 대상 하나에 폴더 하나

```
_workspace/
├── README.md                  이 파일 (유일하게 커밋됩니다)
├── scan-YOEDSMOV/             세션 A
├── scan-YOSTKMGR/             세션 B — 완전히 독립
└── scan-YOEDSMOV.prev-20260911-1430/   밀어 둔 이전 실행
```

폴더를 안 나누면 파일 이름이 전부 같아 서로를 덮어씁니다.
특히 `src/` 에 두 대상의 원문이 섞이면 **리포트에 엉뚱한 코드가 실립니다.**
눈에 잘 안 띄는 사고입니다.

폴더 이름의 slug 는 대상 경로에서 만듭니다 — 영숫자가 아닌 것은 `-` 로, `.` 은 `root` 로.

| 대상 경로 | 작업 폴더 |
|---|---|
| `YOEDSMOV` | `scan-YOEDSMOV` |
| `src/Screens/YOEDSMOV` | `scan-src-Screens-YOEDSMOV` |
| `.` | `scan-root` |

## 한 폴더 안의 구성

| 파일 | 누가 만드나 | 누가 읽나 |
|---|---|---|
| `1-meta.json` · `1-files.json` | `collect.py` | `code-scoper` → `1-scope.md` |
| `src/**` · `src-sql/**` | `collect.py` | 제안자 4인 · 검증관 · `build-report.py` |
| `1-index.json` | `index.py` | **검증관(`V-4`·`V-5`)** · `hygiene`·`sql` 제안자 · `build-report.py` |
| `1-index.md` | `index.py` | 제안자 4인 |
| `1-scope.md` | `code-scoper` | 제안자 4인 · `report-builder` → `overview` |
| `1-units.md` | `code-scoper` | 제안자 4인 · 검증관 · `report-builder` → `units` |
| `2-suggest-*.md` | 제안자 4인 | 검증관 · `report-builder` |
| `3-verify.md` | `refac-verifier` | 오케스트레이터(게이트) · `report-builder` |
| `3-roadmap.md` | **오케스트레이터가 직접** | `report-builder` → `roadmap` |
| `4-findings.json` | `report-builder` | `build-report.py` |
| `refactor-<slug>.html` | `build-report.py` | **사람** |
| `STATUS.md` | 오케스트레이터만 | `/status` (읽기만) |

## 규약 여섯 가지

| | |
|---|---|
| **작업 폴더** | `_workspace/scan-<slug>/`. 오케스트레이터가 Phase 0 에서 확정합니다 |
| **경계** | `_workspace/` 루트에 **공유 파일을 만들지 않습니다.** 진행 인덱스를 하나 두면 그 파일이 다시 경합 지점이 됩니다 |
| **파일 이름** | `<Phase>-<단계>[-<관점>].<확장자>` |
| **자기 것만 씁니다** | 남의 보고서를 고치지 않습니다. 권한으로도 막혀 있습니다 |
| **앞 단계는 직접 읽습니다** | 오케스트레이터가 내용을 옮겨 주지 않습니다 |
| **STATUS.md** | 오케스트레이터만 씁니다 |

## 아무도 지우지 않습니다

같은 대상을 새로 돌릴 때도 `collect.py` 가 이전 폴더를
`scan-YOEDSMOV.prev-<시각>` 으로 **밀어냅니다.**

bash 권한은 명령 문자열 글롭이라 `rm -rf _workspace/scan-*` 같은 와일드카드를
패턴만으로 막을 수 없습니다. 그래서 **`rm` 권한 자체를 주지 않았습니다.**
정리는 사람이 합니다.

```powershell
# PowerShell
Remove-Item -Recurse -Force _workspace\scan-*
```

```bash
# bash / zsh
rm -rf _workspace/scan-*
```

## 권한과의 관계

제안자·검증관처럼 **소스는 못 고치는** 에이전트도 자기 보고서는 써야 합니다.

```yaml
permission:
  edit:
    "*": deny                # 소스 코드는 못 고침
    "_workspace/*": allow    # 저장소 루트에 바로 있을 때
    "*_workspace/*": allow   # 하위 폴더에 있을 때
```

> ⚠️ 패턴은 **git 저장소 루트 기준 상대 경로**와 매칭되고, `*` 는 `/` 를 넘어갑니다.
> 그래서 `_workspace/*` 로만 쓰면 `09-refactor-oi/_workspace/scan-…` 을 못 잡습니다.
> **두 줄을 다 넣으세요.**

## 이렇게 하면 좋은 점

| | |
|---|---|
| **컨텍스트 절약** | 긴 산출물이 오케스트레이터의 기억을 잡아먹지 않습니다 |
| **감사 흔적** | 무슨 일이 있었는지 파일로 남습니다. 실패해도 어디서 틀어졌는지 보입니다 |
| **재개 가능** | 중간에 끊겨도 `/status` 로 이어서 할 수 있습니다 |
| **병렬 안전** | 동시에 도는 제안자 4인이 각자 다른 파일에 쓰므로 충돌하지 않습니다 |
| **검증 가능** | `1-index.json` 이 파일로 남아 있어, 검증관이 제안을 **기계가 센 사실과 대조**할 수 있습니다 |

산출물은 `.gitignore` 되어 있어 커밋되지 않습니다. 이 `README.md` 만 예외입니다.
