---
description: 이미 있는 제안·검증 결과로 HTML 리포트만 다시 생성합니다. 대상 경로를 인자로 받습니다
agent: refactor-lead
---

`$ARGUMENTS` 로 작업 폴더를 정합니다. 비어 있으면
`python .opencode/skills/refactor-oi-scan/assets/ws.py --list` 를 돌려 목록을 보여 주고 물으세요.

이것들이 다 있어야 합니다. 없으면 **무엇이 없는지 말하고 멈추세요.**

- `<작업폴더>/1-units.md`
- `<작업폴더>/2-suggest-*.md`
- `<작업폴더>/3-verify.md`
- `<작업폴더>/3-roadmap.md`

`report-builder` 를 **작업 폴더 전체 경로와 함께** 부릅니다.
제안과 검증은 그대로 두고 JSON 과 HTML 만 다시 만듭니다.

**같은 입력이면 같은 HTML 이 나와야 합니다.** 내용을 새로 판단하지 마세요.
