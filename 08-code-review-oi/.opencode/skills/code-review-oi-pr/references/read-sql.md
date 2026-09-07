# DPICALL SQL 본문 읽기

SQL 리뷰어가 **DPICALL 로 호출되는 SQL 의 본문**을 찾아 읽는 절차입니다.
화면 코드에는 `lot.selectMcLot` 같은 **ID 만** 있고 본문은 별도 저장소(DPImgr)에 있습니다.
본문을 안 보면 파라미터가 맞는지, 인덱스를 타는지 알 수 없습니다.

## DPI SQL ID 의 구조

```
lot.selectMcLot
└┬┘ └────┬────┘
 │       └─ SQL_ID     : xml 파일 안의 <select id="..."> 값
 └───────── SQL_MAP_ID : 폴더 이름
```

| 예 | SQL_MAP_ID | SQL_ID |
|---|---|---|
| `lot.selectMcLot` | `lot` | `selectMcLot` |
| `eqp.selectSubstrEventTmstp` | `eqp` | `selectSubstrEventTmstp` |
| `etc.insertCustmsLotHist` | `etc` | `insertCustmsLotHist` |

## 작업 순서

### 1. 리뷰 중인 프로젝트의 Git root repository 이름을 확인한다

```bash
git rev-parse --show-toplevel      # → D:/Git/OY_SWP 또는 /home/…/OY_SWP
```

출력 경로의 **마지막 폴더 이름**이 저장소 이름입니다 — `OY_SWP`, `CA_SWP`, `XA_SWP`.

> `basename` 은 PowerShell 에 없습니다. 잘라내는 명령을 따로 쓰지 말고
> **출력에서 눈으로 읽으세요.** 한 줄짜리 경로입니다.

### 2. `dpimgr-dir.txt` 에서 그 저장소에 매핑된 경로를 찾는다

`../dpimgr-dir.txt`(이 문서 기준 상위 폴더)에 `저장소: 경로` 형식으로 들어 있습니다.

```
OY_SWP: D:\Git\DPImgr\COMP\DPImgr\src\main\common\dao\
```

**매핑에 없는 저장소면 본문 조회를 시도하지 마세요.** 그 사실을 리포트에 적고 넘어갑니다
(`## 확인 못 한 것` 절).

### 3. 매핑된 경로에서 SQL_MAP_ID 폴더를 찾아 SQL_ID 를 검색한다

SQL_MAP_ID 는 **폴더 이름**이고, 그 안의 xml 파일에 본문이 있습니다.

```
<매핑 경로>/
├── lot/
│   ├── lot.xml           ← selectMcLot 이 여기 있을 수 있음
│   └── lotHist.xml
├── mat/
└── eqp/
```

**셸이 팀마다 다릅니다.** 아래에서 **환경에 맞는 것 하나**를 고르세요.

```powershell
# PowerShell (Windows 기본 환경)
Select-String -Path "<매핑 경로>\lot\*.xml" -Pattern 'id="selectMcLot"'
Select-String -Path "<매핑 경로>\lot\*.xml" -Pattern 'id="selectMcLot"' -Context 0,40
```

```bash
# ripgrep — 설치돼 있으면 어느 셸에서든 가장 빠릅니다
rg -n --no-heading 'id="selectMcLot"' "<매핑 경로>/lot/"
rg -n -A 40 'id="selectMcLot"'        "<매핑 경로>/lot/"

# Unix / Git Bash
grep -rn 'id="selectMcLot"' "<매핑 경로>/lot/"
```

**어느 것이 되는지 모르면 `rg` 를 먼저 시도하고, 실패하면 그다음을 시도하세요.**
셋 다 실패하면 `## 확인 못 한 것` 에 적고 넘어갑니다. 지어내지 마세요.

> `ls -la`, `cat`, `basename` 같은 Unix 전용 명령은 PowerShell 에서 통하지 않습니다.
> 파일 내용을 읽을 때는 `Get-Content`(PowerShell) 또는 `cat`(Unix)을 쓰거나,
> **경로를 알면 `read` 도구가 더 확실합니다.**

**DPImgr 는 리뷰 중인 저장소 밖에 있습니다.** `grep`/`glob` 툴은 프로젝트 안만 보므로
저장소 밖 검색만 `bash` 로 합니다. SQL 리뷰어에게만 검색기가 열려 있는 이유입니다.

### 4. 본문을 리포트에 옮긴다

찾은 본문은 `2-review-sql.md` 의 `## SQL 본문` 절에 **경로와 함께** 적습니다.
경로를 적어야 팀원이 회의 중에 직접 열어볼 수 있습니다.

```markdown
### S001 · lot.selectMcLot
- 경로: D:\Git\DPImgr\COMP\DPImgr\src\main\common\dao\lot\lot.xml:142
- 본문:
  ```sql
  SELECT /*QR...*/ …
  ```
```

## 언제 이 절차를 타는가

| 변경 내용 | 본문 조회 |
|---|---|
| DPICALL 의 **SQL ID 가 바뀜** | **필수** — 새 ID 의 본문을 읽고 param 과 대조 |
| DPICALL 의 **param key/개수가 바뀜** | **필수** — 본문의 바인드 변수와 일치하는지 확인 |
| DPICALL 호출이 **새로 추가됨** | **필수** |
| 화면 코드만 바뀌고 DPICALL 은 그대로 | 불필요 |
| SQLEXEC 인라인 SQL 만 바뀜 | 불필요 (본문이 화면 코드 안에 있음) |

## 본문을 읽은 뒤 확인할 것

1. **바인드 변수 대응** — 화면의 `param` key 가 본문의 바인드 변수와 **개수·이름 모두** 맞는가
2. **조건 누락** — param 을 추가했는데 본문 WHERE 절에 반영되지 않았는가 (조용히 무시된다)
3. **인덱스** — 새로 추가된 조건 컬럼이 인덱스 선두 컬럼인가, 함수로 감싸지 않았는가
4. **결과 컬럼** — 화면이 읽는 컬럼명이 SELECT 절에 실제로 있는가
