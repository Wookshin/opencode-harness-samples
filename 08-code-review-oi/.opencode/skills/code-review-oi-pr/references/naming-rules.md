# 네이밍 · 리팩토링 규칙

리팩토링 리뷰어가 대조하는 **유일한 기준**입니다.
여기 없는 것을 규칙이라고 지적하면 검증 단계에서 반려됩니다.

---

## 1. 함수명

| # | 규칙 | O | X |
|---|---|---|---|
| 1-1 | Pascal Case, 대문자로 시작 | `Search`, `ValidateInput` | `search`, `validate_input` |
| 1-2 | 기능을 설명하는 구체적인 이름 | `ValidateLotStatus`, `InitGridColumns` | `CheckLot`, `InitData` |
| 1-3 | 반환이 목적이면 `Get` 으로 시작 (bool 제외) | `GetMatIdList`, `GetNewSlipId` | `MatIdList()`, `FindSlipId()` |
| 1-4 | 반환 타입이 bool 이면 `Is` 로 시작 | `IsValidLotStatus`, `IsLinedIdEqualToSendArea` | `CheckValid()`, `HasLot()` |
| 1-5 | 값 할당이 목적이면 `Set` 으로 시작 | `SetEqpInfo`, `SetSelectedQty` | `ApplyEqpInfo()` |

**1-2 를 판정하는 법**: 이름만 보고 "무엇을 검사/초기화/조회하는지"를 말할 수 있으면 통과입니다.
`CheckLot` 은 Lot 의 무엇을 검사하는지 알 수 없으므로 위반입니다.

**1-3 과 1-4 가 충돌할 때**: bool 반환이면 1-4 가 이깁니다. `GetIsValid` 가 아니라 `IsValid` 입니다.

## 2. VO 명

| # | 규칙 | O | X |
|---|---|---|---|
| 2-1 | `함수명 + VO` | `GetEqpHistoryVO`, `GetLotListToConfirmVO` | `EqpHistoryVO`, `LotInfoVO` |

VO 를 쓰는 함수의 이름이 `GetMatIdList` 라면 VO 는 반드시 `GetMatIdListVO` 입니다.
**함수명이 바뀌었는데 VO 명이 그대로면 위반**입니다 — 리네이밍 PR 에서 가장 자주 새는 곳입니다.

## 3. 지역변수명

| # | 규칙 | O | X |
|---|---|---|---|
| 3-1 | Camel Case, 소문자로 시작 | `lotId`, `localLineId` | `LotId`, `lot_id` |
| 3-2 | 값을 잘 표현하는 이름. 타입은 특수한 경우에만 | `lotId`, `lotQty`, `isSuccess` | `str1`, `tmp`, `a` |
| 3-3 | 변수명과 타입이 어긋나면 타입을 앞에 붙인다 | `sLotQty` (수량을 string 으로 변환한 값) | `lotQtyString` |
| 3-4 | 복수면 끝에 `s` 또는 `List` | `string[] lines`, `List<string> lotIdList` | `List<string> lotId` |

`lotQty` 는 수량이므로 int, `isSuccess` 는 bool 이 이름에 내포되어 있습니다.
**타입을 굳이 붙이는 것도 위반**입니다 (`intLotQty`). 3-3 은 타입이 어긋날 때만입니다.

## 4. 전역변수명

| # | 규칙 | O | X |
|---|---|---|---|
| 4-1 | `_` 로 시작 | `_appName`, `_lineId`, `_isFirstLoaded` | `appName`, `m_appName` |
| 4-2 | `_` 뒤는 지역변수와 동일 규칙 (Camel Case) | `_operId` | `_OperId`, `_oper_id` |

## 5. 상수명

| # | 규칙 | O | X |
|---|---|---|---|
| 5-1 | 타입은 `const` 또는 `readonly` | `private readonly string DPICALL = "DPICALL";` | `private string DPICALL = ...` |
| 5-2 | SNAKE_CASE (대문자 + 언더스코어) | `EMC_UNIT_QTY`, `MAX_ROW_COUNT`, `RV_COM_PUB_SUBJECT` | `maxRowCount`, `MaxRowCount` |

**리터럴이 코드에 직접 박혀 있으면 5 번 위반이 아니라 매직 넘버 지적**입니다. 구분해서 쓰세요.

## 6. 테스트 프로젝트명 · 소스명

| # | 규칙 | 예 |
|---|---|---|
| 6-1 | `화면 프로젝트명 + UnitTest` | 프로젝트: `YOMATSRCVUnitTest`, `YOSEELOTUnitTest` |
| 6-2 | 소스명도 동일 | `YOMATSRCVUnitTest.cs`, `YOSEELOTUnitTest.cs` |

## 7. 테스트 함수명

| # | 규칙 | 예 |
|---|---|---|
| 7-1 | `TXXX_함수명_테스트설명` (한글 가능) | `T001_GetLotAttrsFromMcLot_McLot으로부터_Lot속성을_조회한다` |
| | | `T002_GetLotAttrsFromGetLotAttr_GetLotAttr로부터_Lot속성을_조회한다` |

번호가 중복되거나 건너뛰는 것, 설명이 없는 것(`T001_GetLot`)은 위반입니다.

## 8. `this` 키워드

| # | 규칙 |
|---|---|
| 8-1 | **기본적으로 사용하지 않습니다.** 필수 상황(생성자 파라미터와 필드명이 같은 경우 등)만 예외 |

---

## 심각도를 붙이는 기준

이 문서의 위반은 대부분 **MINOR** 입니다. 다음일 때만 올립니다.

| 심각도 | 언제 |
|---|---|
| **BLOCKER** | 이름이 실제 동작과 **반대**여서 호출부가 오해할 때. 예: `IsValidLot()` 이 유효할 때 `false` 를 반환 |
| **MAJOR** | 규칙 2-1 위반으로 VO 와 함수의 대응이 깨져 다음 사람이 못 찾을 때, 또는 규칙 1-2 위반이 여러 곳에 퍼져 있을 때 |
| **MINOR** | 그 외 전부 |

**이름이 어색하다는 느낌만으로 MAJOR 를 주지 마세요.** 규칙 번호를 댈 수 없으면 지적하지 않습니다.

## 지적할 때 반드시 넣을 것

```
근거: 규칙 1-4 (bool 반환은 Is 로 시작)
```

규칙 번호가 없는 지적은 검증에서 `REJECTED` 됩니다.
