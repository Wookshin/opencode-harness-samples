---
description: 하네스가 돌 준비가 됐는지 점검합니다. 처음 설치했거나 리뷰가 시작부터 막힐 때 쓰세요
agent: review-lead
---

**점검만 합니다.** 에이전트를 부르지 말고, 파일을 만들거나 고치지 마세요.

아래 한 줄을 실행하고, 결과를 그대로 사용자에게 보여 주세요.

```bash
python .opencode/skills/code-review-oi-pr/assets/ws.py --doctor
```

> `python` 이 안 먹히면 `py`(Windows) 또는 `python3`(리눅스·맥)로 다시 부르세요.
> 셋 다 안 되면 **그게 바로 첫 번째 문제입니다** — Python 을 설치해야 한다고 알리세요.

스크립트가 `✗` 를 하나라도 냈으면, 그 항목의 `→` 조치를 그대로 전하고 **거기서 멈춥니다.**
대신 고쳐 주려 하지 마세요. `gh` 설치나 `gh auth login` 은 사용자가 할 일입니다.

이어서 진행 중인 리뷰가 있는지도 보여 줍니다.

```bash
python .opencode/skills/code-review-oi-pr/assets/ws.py --list
```

## 자주 나오는 것

| 나오는 말 | 뜻과 조치 |
|---|---|
| `gh 를 찾을 수 없습니다` | 실 PR 리뷰는 못 합니다. 설치 전에도 `/review-sample` 은 됩니다 |
| `gh 인증이 안 돼 있습니다` | `gh auth login` |
| `… collect.py 가 없습니다` | `.opencode/` 를 저장소 루트에 통째로 복사했는지 보세요 |
| `opencode.jsonc 가 저장소 루트에 없습니다` | 복사를 빠뜨린 것입니다. 이게 없으면 3인 동시 리뷰가 막힙니다 |
| `작업 폴더 없음` | **정상입니다.** 아직 리뷰를 한 번도 안 돌린 것뿐입니다 |

`.opencode/` 는 숨김 폴더라 `grep` · `glob` 으로는 안 잡힙니다.
**파일이 없다고 나와도 검색으로 다시 확인하지 마세요** — 이 스크립트가 이미 직접 본 결과입니다.
