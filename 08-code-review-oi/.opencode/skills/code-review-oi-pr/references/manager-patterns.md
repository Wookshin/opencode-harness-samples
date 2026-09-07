# SqlManager · RuleManager 사용 규범

기능 리뷰어가 대조하는 기준입니다. **이름 규칙은 여기서 보지 않습니다** — 리팩토링 리뷰어 담당입니다.
여기서 보는 것은 **이대로 쓰지 않으면 실제로 문제가 생기는 것**입니다.

---

## 1. SqlManager 의 구조

```csharp
public class SqlManager
{
    private string _appName;
    private readonly string DPICALL = "DPICALL";
    private readonly string SQLEXEC = "SQLEXEC";
    private readonly string RV_COM_PUB_SUBJECT  = RvMsg.rv_c1_pub_subject;
    private readonly string RV_DPIMGR_TARGET    = RvMsg.rv_c1_dpimgr_target;
    private readonly string RV_DPIMGR_SUBJECT   = RvMsg.rv_c1_dpimgr_subject;

    // ★ 인스턴스 전체가 공유하는 하나의 빌더입니다.
    private SqlBuilder _sql = new SqlBuilder()
    {
        param     = new Dictionary<string, string>(),
        paramList = new Dictionary<string, string[]>()
    };

    public SqlManager(string appName) { _appName = appName; }
}
```

호출 방식은 두 가지입니다.

| 방식 | 언제 | 형태 |
|---|---|---|
| **DPICALL** | DPImgr 에 등록된 SQL 을 ID 로 호출 | `SendMessageWithJSON(DPICALL, …, "eqp.selectSubstrEventTmstp", _appName, param)` |
| **SQLEXEC** | 화면에서 SQL 본문을 직접 조립 | `_sql.Init()` → `_sql.AddSql(...)` → `SendMessageWithJSON(SQLEXEC, …, _sql.GetSql(), 60)` |

### DPICALL — 파라미터를 Dictionary 로 만든다

```csharp
public RVMessageResult GetEqpHistory(GetEqpHistoryVO vo)
{
    Dictionary<string, string> param = new Dictionary<string, string>
    {
        { "eqpId",    vo.eqpId },
        { "fromDate", vo.fromDate },
        { "toDate",   vo.toDate }
    };

    RVMessageResult rvResult = new TibRVHelper(RV_COM_PUB_SUBJECT)
        .SendMessageWithJSON(DPICALL, RV_DPIMGR_TARGET, RV_DPIMGR_SUBJECT,
                             "eqp.selectSubstrEventTmstp", _appName, param);

    return rvResult;
}
```

### SQLEXEC — Init → param.Add → AddSql → GetSql

```csharp
public RVMessageResult GetMatIdList(GetMatIdListVO vo)
{
    _sql.Init();                        // ★ 반드시 먼저
    _sql.param.Add("lotId", vo.lotId);

    _sql.AddSql($@"
        SELECT /*QR220728-023-01*//*OI_YOEDSMOV_2022-7-28_sw1027.chae*/
               l.lot_id, m.mat_id
          FROM mc_lot l, mc_mat m
         WHERE 1=1
           AND (l.lot_sub_status_seg NOT IN ('WAIT','HELD') OR m.mat_sub_status_seg NOT IN ('WAIT','HELD'))
           AND l.object_id = m.lot_object_id
           AND l.lot_id = {_sql.Bind("lotId")}      // ★ 값은 반드시 Bind 로
    ");

    return new TibRVHelper(RV_COM_PUB_SUBJECT)
        .SendMessageWithJSON(SQLEXEC, RV_DPIMGR_TARGET, RV_DPIMGR_SUBJECT,
                             _appName, _sql.GetSql(), 60);
}
```

### 화면에서의 사용

```csharp
private SqlManager _sqlManager = new SqlManager("YOEDSMOV");

GetMatIdListVO vo = new GetMatIdListVO { lotId = dr["LOT_ID"].ToString() };
_rvResult = _sqlManager.GetMatIdList(vo);
```

---

## 2. RuleManager 의 구조

```csharp
public class RuleManager
{
    private string _appName;
    private readonly string SET_SIMAXDATA        = "SET_SIMAXDATA";
    private readonly string RV_COM_PUB_SUBJECT   = RvMsg.rv_c1_pub_subject;
    private readonly string RV_TRACKING_TARGET   = RvMsg.rv_c1_tracking_target;
    private readonly string RV_TRACKING_SUBJECT  = RvMsg.rv_c1_tracking_subject;

    public RuleManager(string appName) { _appName = appName; }
}
```

| 호출 종류 | 형태 |
|---|---|
| 룰 등록 | `SendMessageWithJSONToTextResult(SET_SIMAXDATA, RV_TRACKING_TARGET, RV_TRACKING_SUBJECT, "etc.insertCustmsLotHist", _appName, param, 30)` |
| 트래킹 전문 | `SendMessage("LOTCOMMENT" / "MODATTR", RV_TRACKING_TARGET, RV_TRACKING_SUBJECT, _appName, param, 30)` |

**전문 파라미터의 key 대소문자 규약이 다릅니다.**

- `SET_SIMAXDATA` 계열 → Camel Case (`slipNo`, `lotId`, `carrId`)
- `SendMessage` 전문 계열 → 대문자 (`LOTID`, `OPERID`, `COMMENT`, `ATTR`)

섞이면 서버에서 값이 비어 들어옵니다. **바뀐 key 가 그 계열의 규약을 지키는지 반드시 확인하세요.**

```csharp
private readonly RuleManager _ruleManager = new RuleManager("YOEDSMOV");

ModAttrVO vo = new ModAttrVO { lotId = lotId, operId = _operId, attr = $"({attrName}={attrValue})" };
_rvResult = _ruleManager.SendModAttr(vo);
```

---

## 3. 점검 체크리스트

변경분에 Manager 호출이 있으면 아래를 **하나씩** 확인합니다.

| # | 점검 | 놓치면 생기는 일 | 기본 심각도 |
|---|---|---|---|
| M-1 | `_sql.Init()` 없이 `_sql.param.Add()` / `AddSql()` 를 했는가 | `_sql` 은 **인스턴스 공유 필드**다. 앞 호출의 param 과 SQL 이 남아 다음 쿼리에 섞인다 | **BLOCKER** |
| M-2 | VO 에 새 필드를 추가하고 `param.Add` / `Bind` 를 빠뜨렸는가 | 바인드 변수 미설정 → 실행 오류 또는 조건 누락된 전체 조회 | **BLOCKER** |
| M-3 | 반대로 `param` 에만 넣고 SQL 에서 `Bind` 로 쓰지 않았는가 | 조용히 무시된다. 조건이 안 걸린 채 결과가 나온다 | MAJOR |
| M-4 | `RVMessageResult` 의 성공 여부를 확인하지 않고 결과를 썼는가 | 실패 전문을 정상 결과로 취급 → NullReference 또는 빈 그리드 | **BLOCKER** |
| M-5 | 타임아웃 인자를 빠뜨렸거나 근거 없이 늘렸는가 | 화면 멈춤. 기존 호출과 다른 값이면 이유가 있어야 한다 | MAJOR |
| M-6 | DPICALL 의 SQL ID 나 param key 가 바뀌었는가 | DPImgr 본문과 어긋나면 런타임에서만 터진다 → **SQL 리뷰어에게 넘긴다** | — |
| M-7 | 전문 계열 param key 의 대소문자 규약을 지켰는가 (2절 참고) | 서버에서 값이 비어 들어온다 | **BLOCKER** |
| M-8 | 예외 경로에서 로딩 표시·버튼 활성화를 되돌리는가 | 예외 발생 시 화면이 잠긴 채 남는다 | MAJOR |
| M-9 | 반복문 안에서 Manager 를 호출하는가 | Lot 수만큼 전문이 나간다. 배치 호출이 있는지 확인 | MAJOR |

---

## 4. 이 관점에서 **보지 않는 것**

- 이름 규칙 (`GetMatIdListVO` 같은 VO 명, 함수명, 변수명) → **리팩토링 리뷰어**
- SQL 본문의 인덱스·조인·튜닝 → **SQL 리뷰어**
- SQL 문자열 보간(`{lotId}`) 자체의 위험 → **SQL 리뷰어**
  (단, `Bind` 를 썼는데 `param.Add` 가 없는 M-2/M-3 은 여기서 봅니다)

경계가 겹치면 **지적하지 말고 넘기세요.** 중복 지적은 리포트를 길게 만들 뿐입니다.

## 지적할 때 반드시 넣을 것

```
근거: M-1 (_sql.Init() 누락 — 공유 빌더에 앞 호출의 param 이 남는다)
```
