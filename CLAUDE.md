# 이 저장소에서 일할 때

OpenCode 하네스 샘플 모음입니다. 각 폴더가 독립된 하네스이고,
`opencode.jsonc` · `.opencode/agents/` · `.opencode/commands/` 로 구성됩니다.

## 하네스를 실제로 돌리지 마세요

`opencode run "/review-pr 1234"` · `opencode run "/review-sample"` 처럼
**에이전트를 깨우는 실행은 하지 않습니다.** 모델 호출이 많아 토큰을 크게 씁니다
(08 의 전체 사이클은 한 번에 lead → scoper → 리뷰어 3 → 검증관 → 빌더로 7회).

**기준은 모델 토큰이 나가느냐입니다.** 안 나가면 마음껏 쓰세요.

| 쓰지 않음 | 얼마든지 |
|---|---|
| `opencode run …` (모든 커맨드) | `build-report.py` · `collect.py` 직접 실행 |
| 서브에이전트 팬아웃을 유발하는 것 | Playwright/Chromium 으로 렌더 결과 확인 |
| | grep · YAML 파싱 · 복사 시뮬레이션 · sha256 비교 |

## 그래서 무엇으로 검증하나

산출물을 만드는 코드는 전부 표준 라이브러리 Python 이라 단독으로 돌아갑니다.
지금까지 실제 결함을 잡아낸 것도 이쪽입니다.

```bash
cd 08-code-review-oi
S=.opencode/skills/code-review-oi-pr
python3 $S/assets/build-report.py $S/sample/expected-findings.json /tmp/out.html $S/sample/pr-sample.patch
```

- **HTML 을 고쳤으면** 브라우저로 열어 JS 오류 0 · 외부 요청 0 · 라이트/다크 ×
  420~1440px 가로 스크롤 없음을 확인합니다. JS 오류 개수는 마크업이 잘못 지워졌을 때
  가장 먼저 걸리는 신호입니다.
- **경로나 구조를 옮겼으면** 빈 git 저장소에 `.opencode/` 와 `opencode.jsonc` 만
  복사해 넣고, 참조 경로가 전부 실재하는지와 파이프라인이 도는지를 봅니다.
  산출물 sha256 이 이전과 같아야 "경로만 바뀌었다"가 증명됩니다.
- **frontmatter 를 건드렸으면** 에이전트·커맨드 `.md` 의 YAML 을 전부 파싱해 봅니다.
  따옴표 안 친 `: ` 하나로 커맨드가 로드되지 않은 적이 있습니다.

**프롬프트(`agents/*.md` · `commands/*.md` · `references/*.md`)만 고친 변경은
스크립트로 확인할 수 없습니다.** 그럴 때는 무엇이 검증되지 않은 채 나가는지
명시하고 넘깁니다 — 돌려 봤다고 말하지 않습니다.

## 그 밖에

- 문서와 주석은 **한국어**로 씁니다. 기존 문체(설명 → 표 → 근거)를 따릅니다.
- 팀 실행 환경은 **PowerShell** 입니다. `ls -la` · `mkdir -p` · `dirname` 은 없고,
  PS 5.1 의 `>` 는 UTF-16LE 로 써서 파일을 조용히 깨뜨립니다.
  그래서 파일을 만드는 일은 셸이 아니라 Python 스크립트가 합니다.
- Node 를 요구하지 않습니다. 팀 PC 에는 Python 이 깔려 있습니다.
- 하네스가 쓰는 모델은 Pro 또는 Max 만 씁니다. Image 등급은 쓰지 않습니다.
