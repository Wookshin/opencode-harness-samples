---
description: 하네스가 돌 준비가 됐는지 점검합니다. 처음 설치했거나 분석이 시작부터 막힐 때 여기부터
agent: refactor-lead
---

두 가지를 차례로 돌리고 **출력을 그대로** 전하세요.

```bash
python .opencode/skills/refactor-oi-scan/assets/ws.py --doctor
python .opencode/skills/refactor-oi-scan/assets/ws.py --list
```

`✗` 가 있으면 그 줄의 `→` 를 **그대로 옮기고 멈추세요.** 임의로 고치지 마세요.

전부 `✓` 면 자체 점검까지 권하세요. **모델을 부르지 않고** 스크립트 파이프라인이
실제로 도는지 봅니다 (수집 → 인덱싱 → 리포트 렌더까지).

```bash
python .opencode/skills/refactor-oi-scan/assets/ws.py --selftest
```

## 자주 막히는 것

| 증상 | 원인 | 어떻게 |
|---|---|---|
| `opencode.jsonc 가 없습니다` | 복사할 때 빠뜨림 | 저장소 **루트**에 두세요. `.opencode/` 안이면 안 읽힙니다. 없으면 `subagent_depth` 가 빠져 **4인 동시 제안이 막힙니다** |
| `python` 을 못 찾음 | 인터프리터 이름 차이 | Windows 는 `py`, 리눅스·맥은 `python3` |
| mapper 매핑이 없다 | 이 저장소가 `mapper-dir.txt` 에 없음 | `<저장소이름>: <mapper 폴더 경로>` 한 줄을 추가하세요. 안 넣으면 **SQL 미사용 판정을 건너뜁니다** (분석 자체는 됩니다) |
| mapper 를 0개 가져왔다 | 코드에서 부르는 SQL ID 의 네임스페이스에 맞는 파일이 없음 | `1-meta.json` 의 `namespacesNeeded` 와 mapper 폴더의 파일 이름을 대조하세요. 파일명과 `namespace=` 가 둘 다 다르면 못 찾습니다 |
| mapper 를 너무 많이 가져왔다 | `--all-mappers` 를 줬거나 네임스페이스가 지나치게 넓음 | 선별이 기본입니다. `--all-mappers` 는 빼세요 |
| 수집한 파일이 0개 | 대상 경로에 소스가 없음 | `bin/` · `obj/` · 생성 코드는 일부러 건너뜁니다 |
| 리포트에 코드가 안 보임 | `sourceFile` 경로가 어긋남 | mapper 는 `src-sql/…` 로 적어야 합니다 |
