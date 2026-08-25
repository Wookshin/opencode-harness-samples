# OpenCode 하네스 패턴 샘플

에이전트 팀 설계 패턴 다섯 가지를 **실제로 돌아가는 OpenCode 하네스**로 만들어 둔 모음입니다.
각 폴더는 독립적으로 동작하며, 그 폴더에서 `opencode` 를 실행하면 해당 패턴만 깔끔하게 굴러갑니다.

## 무엇이 들어 있나

| # | 폴더 | 패턴 | 예시 | 핵심 장치 |
|---|---|---|---|---|
| 01 | [`01-pipeline`](01-pipeline/) | **파이프라인** | 영어 문서 번역 | 앞 단계 결과를 오케스트레이터가 손으로 인계 |
| 02 | [`02-expert-pool`](02-expert-pool/) | **전문가 풀** | 테스트·리팩터링·문서화 | `description` 이 곧 라우팅 근거 |
| 03 | [`03-generate-verify`](03-generate-verify/) | **생성-검증** | 숫자야구 게임 만들기 | 검증자에게 `edit: deny` |
| 04 | [`04-fanout-fanin`](04-fanout-fanin/) | **팬아웃-팬인** | 코드리뷰 4인 동시 | 한 응답에서 4번 호출 + 형식 고정 |
| 05 | [`05-combined`](05-combined/) | **조합** | 할 일 앱 기능 추가 | 게이트로 단계 강제 · `subagent_depth: 2` |

## 시작하기

### 준비

1. [OpenCode](https://opencode.ai) 가 설치돼 있어야 합니다.
2. 프로바이더 인증이 되어 있어야 합니다.

   이 샘플들은 아래 세 모델을 **비용 계층**으로 씁니다.

   | 모델 | 등급 | 쓰는 곳 |
   |---|---|---|
   | `codemate/CodeLLMImage` | 저렴 | 기계적인 작업 — 초벌 번역, 문서화, 가독성 확인 |
   | `codemate/CodeLLMPro` | 무난 | 판단이 필요한 작업 — 구현, 감수, 일반 리뷰 |
   | `codemate/CodeLLMMax` | 고가 | 놓치면 비싼 작업 — 최종 판정, 보안 리뷰, 계획 |

### 다른 프로바이더를 쓰신다면

각 폴더의 `opencode.jsonc` 맨 위에 모델 세 개가 주석과 함께 모여 있고,
에이전트별 모델은 `.opencode/agents/*.md` 의 `model:` 한 줄에 있습니다.

전부 한 번에 바꾸려면:

```bash
# 예: Anthropic 으로 바꾸기
cd opencode-harness-samples
grep -rl 'codemate/CodeLLM' . | xargs sed -i \
  -e 's|codemate/CodeLLMImage|anthropic/claude-haiku-4-5|g' \
  -e 's|codemate/CodeLLMPro|anthropic/claude-sonnet-4-5|g' \
  -e 's|codemate/CodeLLMMax|anthropic/claude-opus-4-5|g'
```

모델을 아예 지정하지 않으려면 각 에이전트에서 `model:` 줄을 지우면 됩니다.
그러면 서브에이전트는 자기를 부른 주 에이전트의 모델을 그대로 씁니다.

### 실행

**패턴 폴더 안으로 들어가서** 실행해야 합니다.

```bash
cd 01-pipeline
opencode
```

그다음 입력창에 `/translate sample/article.md` 를 칩니다.
TUI 없이 한 번에 돌리려면:

```bash
cd 01-pipeline
opencode run "/translate sample/article.md"
```

## 폴더가 서로 섞이지 않는 이유

OpenCode 는 설정을 **현재 폴더에서 git 저장소 루트까지만 거슬러 올라가며** 찾습니다.
형제 폴더는 그 경로에 없으므로 절대 읽히지 않습니다.

```
opencode-harness-samples/
├── README.md              ← 루트에는 설정을 두지 않았습니다 (두면 전부에 섞입니다)
├── 01-pipeline/
│   ├── opencode.jsonc     ← 여기서 실행하면 이것만
│   └── .opencode/
└── 04-fanout-fanin/
    ├── opencode.jsonc     ← 01 에서 실행할 땐 안 읽힘
    └── .opencode/
```

그래서 04의 리뷰어를 05에서 쓰려면 **파일을 실제로 복사**해야 합니다. 05는 그렇게 해 두었습니다.

## 어떤 순서로 보면 좋은가

처음이시라면 **01 → 02 → 03 → 04 → 05** 순서를 권합니다. 뒤로 갈수록 장치가 늘어납니다.

각 폴더 README 는 같은 구조입니다.

1. **바로 실행하기** — 복사해서 붙여 넣을 명령
2. **무엇을 보여주는 샘플인가** — 등장인물과 역할 표
3. **패턴이 보이는 지점** — 실제 파일의 어느 줄이 그 패턴인지
4. **직접 바꿔 보기** — 망가뜨려 보면서 이해하는 실험 목록
5. **파일 구조**

특히 **4번**을 권합니다. 권한 한 줄을 열었을 때 무엇이 무너지는지 보는 게 가장 빨리 이해되는 방법입니다.

## 공통 설계 규칙

다섯 샘플 전부 아래 규칙을 지켰습니다. 직접 하네스를 만드실 때 그대로 가져다 쓰셔도 됩니다.

- **`description` 은 "무엇을 하고 언제 부르는지"** — 오케스트레이터가 위임 대상을 고를 때 보는 것이 이 문장입니다.
- **전문가 프롬프트는 출력 형식을 고정** — 위임 결과는 마지막 텍스트 한 덩어리로만 올라오므로, 형식이 없으면 취합할 수 없습니다.
- **"하지 않는 일"을 명시** — 역할 침범이 팀을 무너뜨리는 가장 흔한 방식입니다.
- **오케스트레이터는 직접 일하지 않음** — 순서·조건·금지를 프롬프트에 적고, 판단을 모델에게 맡기지 않습니다.
- **프롬프트와 권한을 둘 다 검** — "고치지 마세요"라고 쓰기만 하면 모델이 급할 때 무시합니다. `edit: deny` 로 닫으면 시도 자체가 막힙니다.
- **`tools:` 를 쓰지 않음** — 공식 문서에서 deprecated 되었습니다. `permission:` 을 씁니다.

## 알아 두면 좋은 것

- **`edit` 권한 하나가 `write`·`edit`·`apply_patch` 세 도구를 막습니다.** `write:` 같은 키를 따로 쓸 필요가 없고, 써도 효과가 없습니다.
- **`subagent_depth` 기본값은 1입니다.** 서브에이전트가 또 서브에이전트를 부를 수 없다는 뜻입니다. 05만 2로 올려 두었습니다.
- **`bash` 권한은 패턴별로 열 수 있습니다.** 04의 리뷰어들이 `git diff*` 만 허용받은 것이 그 예입니다.
- **내장 서브에이전트 `general` 과 `explore`** 를 그대로 쓸 수 있습니다. 새로 만들 필요가 없습니다.
- 공식 문서에 나오는 `scout` 서브에이전트는 현재 소스에 정의가 없어 **이 샘플들에서는 쓰지 않았습니다.**

## 참고

- [OpenCode 공식 문서](https://opencode.ai/docs) — Agents · Commands · Permissions · Config · Skills
- 같은 주제를 문서로 정리한 글
  - [소스로 읽은 OpenCode 에이전트 팀](https://github.com/Wookshin/ai-insights-hub)
  - [OmO는 어떻게 AI 팀을 굴리는가](https://github.com/Wookshin/ai-insights-hub)
