# DocuMaster Web App — Local Single-user Service

DocuMaster의 멀티 에이전트 작업(로이드·요르·유리·아냐·본드)을 **회사 협업툴 같은 화면**으로 실행·관찰하는 로컬 웹앱입니다.

```
Web App(Next.js) ── REST + SSE ──▶ Local Backend(FastAPI + SQLite) ──▶ Thin Adapter ──▶ 기존 DocuMaster 오케스트레이터
                                                                        (claude -p = 로이드 세션, 루트의 CLAUDE.md·.claude/ 그대로)
```

- 백엔드는 오케스트레이터를 **대체하지 않습니다.** 로이드 세션을 띄우고, `작업/<ID>/`의 계약 파일(00~07 · `상태.md`)과 `최종/<ID>/`를 읽어 화면 이벤트로 바꿀 뿐입니다. 프롬프트·역할·모델·검증·게이트는 루트 규칙이 정합니다.
- **파일이 원본**입니다. SQLite(`webapp/.data/documaster.db`)에는 메타데이터·실행 상태·이벤트 기록만 둡니다.
- 백엔드 없이 `npm run dev`만 켜면 브라우저 목업(MockWorkspaceService)으로 돕니다.

구현 지침: [`docs/DocuMaster_Prototype_Audit_and_RealService_Phase2_v1.1.md`](docs/DocuMaster_Prototype_Audit_and_RealService_Phase2_v1.1.md)

## 실행

`start.bat`을 더블클릭하면 백엔드(127.0.0.1:8000)와 화면(127.0.0.1:3000)이 함께 켜집니다. 처음에는 필요한 것을 설치하고,
Owner PIN이 없으면 **6자리 PIN을 두 번 묻습니다**(원문은 저장하지 않고 scrypt 해시만 `webapp/.data/owner.json`에 씀 — Git 제외).
PIN을 바꾸려면 설정 → 계정, 또는 `server`에서 `.venv\Scripts\python setup_owner.py`.

| 누구 | 할 수 있는 것 |
| --- | --- |
| Guest(로그인 전) | 프로젝트·대화 기록·작업물 보기와 내려받기, 에이전트 설명, 설정 보기 |
| Owner(PIN 로그인) | 위 전부 + 프로젝트 생성 · 지시 · 실행/중지 · 확인 응답 · 레퍼런스 추가/삭제 · 모델 설정 · 프로필/PIN |

바꾸는 요청은 백엔드도 세션 쿠키(HttpOnly · SameSite=Lax)와 Origin으로 다시 검사합니다(`api.py`의 `require_owner`).

| 오케스트레이터 | 켜는 법 | 하는 일 |
| --- | --- | --- |
| `fake`(기본) | 그대로 실행 | 비용 없음. 가짜 로이드가 `webapp/.data/sandbox/`에 계약 파일을 써서 전체 경로를 흉내 냄 |
| `claude` | `set DOCUMASTER_ORCHESTRATOR=claude` 후 실행 | 저장소 루트에서 실제 로이드 세션을 엶 — **모델 사용량이 발생합니다** |

기존 CLI 작업(`작업/<ID>/상태.md`가 있는 폴더)은 백엔드가 켜질 때 **읽기 전용 프로젝트**로 목록에 나옵니다.

| 명령 | 용도 |
| --- | --- |
| `npm run lint` · `npx tsc --noEmit` · `npm run build` | 화면 검사·빌드 |
| `npm test` | 화면 테스트(Node 내장 러너, 의존성 없음) + 백엔드와 붙는 통합 테스트 |
| `server\.venv\Scripts\python -m pytest` (server에서) | 백엔드 테스트 |

## 백엔드 (`server/`)

| 파일 | 책임 |
| --- | --- |
| `app/main.py` · `api.py` | 앱 조립 · REST/SSE 라우트 |
| `app/db.py` | SQLite 스키마(projects · runs · events · references · artifacts · agent_overrides · sessions · owner_profile · pending_inputs · user_messages) |
| `app/auth.py` | 단일 Owner — PIN 해시 확인 · 5회 실패 30초 잠금 · 세션(토큰 sha256만 저장) · 프로필 |
| `app/agent_settings.py` | 모델 설정(전역) — 실제로 반영되는 선택지만 · 실행 시작 때 스냅샷 |
| `app/usage.py` · `claude_statusline.py` | 사용량 — Codex는 `codex app-server`의 `account/rateLimits/read`(실시간), Claude는 statusLine이 남긴 `.data/claude_usage.json`. 확인할 수 없으면 「확인 불가」 |
| `app/events.py` | EventStore — seq 부여 · replay · SSE 구독자 전달 |
| `app/projects.py` · `files.py` | 프로젝트·지시·레퍼런스·작업물 메타데이터 · 안전한 파일 저장(허용 폴더·파일명 정리·sha256) |
| `app/contract.py` · `scanner.py` | 파일 계약 읽기(00~07 → 6단계·담당 에이전트, 05 첫 줄 판정) · 바뀐 것만 이벤트로 |
| `app/runs.py` · `orchestrator.py` | 한 번에 한 실행 · graceful stop · 응답 후 `--resume` · 재시작 복구 · 오류 분류 |
| `app/fake_orchestrator.py` · `imports.py` | 비용 없는 가짜 로이드 · 기존 작업 읽기 전용 가져오기 |

- **이벤트**: `{schemaVersion, id, projectId, runId, seq, at, type, ...payload}`. `seq`는 프로젝트마다 1부터 증가합니다.
- **재연결**: 스냅샷(`GET /workspace`)이 `lastEventSeq`를 주고 → `GET /events?afterSeq=N`(SSE). 끊기면 브라우저가 `Last-Event-ID`로 이어 받고, 서버·화면 양쪽에서 seq로 중복을 거릅니다.
- **로이드와의 대화**: 로이드가 사용자에게 묻고 턴을 끝내면 그 질문이 「사용자 확인 필요」 카드가 되고, 답은 같은 세션(`--resume <session-id>`)으로 전달됩니다. 실행 중 보낸 지시는 현재 턴이 끝난 뒤 전달됩니다.

## 화면 구성

```
┌ TopHeader: 로고(→홈) · 프로젝트 선택 · 진행률 · 상태 · 알림 · 로그인 ─┐
│ LeftSidebar      │ 중앙 View (기본: 대화)          │ RightSidebar      │
│ 메뉴             │ WorkflowStepper (6단계)          │ 작업물 목록       │
│ 현재 프로젝트    │ ActivityFeed (내부 스크롤)       │ 미리보기          │
│ 레퍼런스(스크롤) │ PromptInput (하단 고정)          │                   │
│ 워크플로우 요약  │                                  │                   │
└──────────────────┴──────────────────────────────────┴───────────────────┘
```

- **xl(1280px) 이상**: 3열 / **lg**: 오른쪽이 접힘(헤더 버튼으로 서랍) / **lg 미만**: 왼쪽도 접힘(햄버거) / **md 미만**: 하단 탭(대화·진행·레퍼런스·작업물). 모델 설정은 「설정」 화면에서만 합니다.
- 멤버·에이전트 카드는 `repeat(auto-fit, minmax(240px, 320px))` 격자로 가운데 정렬합니다(에이전트 수로 폭을 계산하지 않음).
  모드에서 쓰지 않는 에이전트(문서=본드, 발표=아냐)는 숨기지 않고 「💤 휴식 중」으로 보여 줍니다 — 화면 표시일 뿐 실행하지 않습니다.

## 폴더 구조 — 무엇을 고치려면 어디로

```
src/
├─ app/                 layout.tsx(폰트·메타) · page.tsx(Provider + AppShell) · globals.css(색 테마)
├─ types/               도메인 타입: Agent · Artifact · Reference · FeedItem · WorkflowEvent · ProjectWorkspace
├─ constants/           한곳에서 관리하는 값
│  ├─ agents.ts         팀 명단(이름·역할·색·기본 모델·avatarSrc)
│  ├─ models.ts         모델·공급자·추론 강도 목록 ← 모델 추가는 여기만
│  ├─ workflow.ts       6단계 정의(이름·설명·담당·받는 자료)
│  ├─ status.ts         상태 라벨과 배지 색
│  ├─ navigation.ts     메뉴·화면 ID·모바일 탭
│  ├─ references.ts     레퍼런스 반영 방식
│  └─ brand.ts          로고 경로
├─ data/mock/           목업 데이터(UI 코드와 분리)
│  ├─ seedProjects.ts   처음 보이는 프로젝트 3개 — "지금까지 일어난 이벤트"로 적음
│  └─ stageScripts.ts   「실행」 때 단계별 대본과 에이전트 답변 문구
├─ services/            백엔드 창구
│  ├─ WorkspaceService.ts   인터페이스(UI가 아는 유일한 API)
│  ├─ mock/                 목업 구현(MockWorkspaceService · buildRunPlan)
│  └─ index.ts              어떤 구현을 쓸지 고르는 한 줄
├─ state/               appReducer.ts(화면 상태) · WorkspaceProvider.tsx(Context + 동작)
├─ lib/                 순수 함수: applyWorkflowEvent · eventToFeedItem · progress · stageContext · models …
├─ hooks/               useArtifactContent · useStickToBottom · useDismiss
└─ components/
   ├─ ui/               Badge · Button · Modal · Drawer · Dropdown · Select · Panel · ProgressBar · States
   ├─ layout/           AppShell · TopHeader · LeftSidebar · RightSidebar · MobileTabBar · BrandLogo
   ├─ workflow/         WorkflowStepper · StageDetail · WorkflowSummary · StageStatusIcon
   ├─ chat/             ActivityFeed · AgentMessage · SystemEvent · ArtifactCard · UserMessage · PromptInput
   ├─ reference/        ReferenceList · AddReferenceModal · AddReferenceButton
   ├─ artifact/         ArtifactList · ArtifactPreview · ArtifactContentView · MarkdownLite
   ├─ agent/            AgentAvatar · portraits(SVG 초상) · AgentSettings · AgentCard
   ├─ project/          ProjectSelector · NewProjectModal
   └─ views/            화면별 컴포넌트와 viewRegistry(메뉴 → 화면 연결표)
public/
├─ brand/               로고 (README 참고)
├─ avatars/             캐릭터 이미지 넣는 곳 (README 참고)
└─ mock/                목업 미리보기용 그림
```

| 하고 싶은 일 | 고칠 곳 |
| --- | --- |
| 색 바꾸기 | `src/app/globals.css`의 `@theme` (blue 계열 = 로고 파랑) |
| 로고를 원본 PNG로 | `public/brand/`에 파일 → `constants/brand.ts` 경로 |
| 캐릭터 실제 이미지 | `public/avatars/`에 파일 → `constants/agents.ts`의 `avatarSrc` |
| 모델 추가 | `constants/models.ts` |
| 단계 이름·설명 | `constants/workflow.ts` |
| 목업 대화 문구 | `data/mock/stageScripts.ts` · `seedProjects.ts` |
| 시스템 알림 문구 | `lib/eventToFeedItem.ts` |
| 새 화면 | `constants/navigation.ts`에 메뉴 추가 → `components/views/viewRegistry.tsx`에 한 줄 |

## 데이터 흐름

```
사용자 클릭 ─▶ useAppActions() ─▶ workspaceService (지금은 Mock)
                                         │ WorkflowEvent 발행 (workflow.stage.started, agent.message, artifact.created …)
                                         ▼
               appReducer ◀── subscribe() ── applyWorkflowEvent(워크스페이스, 이벤트) + eventToFeedItem
                    │
                    ▼
               컴포넌트 다시 그림
```

- **화면을 바꾸는 길은 이벤트 하나뿐입니다.** 목업 서비스와 React 상태가 같은 `applyWorkflowEvent`를 써서 프로젝트를 오가도 상태가 어긋나지 않습니다.
- **LLM이 쓰는 문장은 `agent.message`뿐입니다.** 단계 시작·완료, 전달(handoff), 레퍼런스 추가, 작업물 생성, 진행률은 모두 코드가 만듭니다(`lib/eventToFeedItem.ts`, `lib/progress.ts`).
- **에이전트별 최소 Context**: `constants/workflow.ts`의 `readsFrom`·`usesReferences`와 `lib/stageContext.ts`가 단계마다 넘길 자료만 고릅니다. 단계 상세의 「넘겨받는 자료」에 표시됩니다.
- 작업물 목록에는 메타데이터만 오고, 본문은 미리보기를 열 때 `getArtifactContent`로 한 번만 불러와 캐시합니다.

## 구현된 기능

프로젝트 선택·새로 만들기 · 좌측 메뉴 화면 이동(대화·대시보드·작업물·멤버·프로젝트·에이전트·설정) · 6단계 Stepper와 단계 상세 ·
Agent Message / System Event / Artifact Card / User Message 구분 · @에이전트 호출 · Enter 전송 / Shift+Enter 줄바꿈(한글 조합 처리) ·
레퍼런스 추가(파일·URL·텍스트 + 반영 방식 선택) · 작업물 미리보기(Markdown·PDF 표지·이미지)와 확대 모달 ·
홈(최근 프로젝트·활동·도구 설치 상태) · Owner 로그인·프로필·Guest 읽기 전용 · 모델 설정(로이드·요르·유리·아냐 선택, 실행 뒤 실제 호출과 대조) · 사용량(확인되는 값만) · 실행 → 단계별 진행·진행률·에이전트 상태 변화 · 중지 후 이어서 실행 · 알림 목록 · 로딩·빈 상태·오류(다시 시도)

## 아직 하지 않은 것

| 기능 | 지금 |
| --- | --- |
| 「관련 단계부터 다시 실행」 | 레퍼런스는 저장·목록만. 반영은 다음 턴의 로이드 판단 |
| 실행 중 즉시 개입 | 지시는 현재 턴이 끝난 뒤 전달(지침서 §17) |
| 긴급 강제 종료 | 없음 — 중지는 현재 단계가 끝난 뒤(graceful) |
| 유리·아냐 추론 강도 | 지정 불가 — 서브에이전트 호출에 넘길 방법이 없음(도구 기본값) |
| Claude 사용량 | 터미널 Claude Code의 statusLine(`~/.claude/settings.json`)이 응답마다 캐시에 남김 — 터미널에서 한 번 써야 나타남 |
| NotebookLM 사용량 | 확인 불가 — 공식 인터페이스 없음 |
| 지식 라이브러리 · 프로젝트 설정 | 준비 중 화면 |

## 환경변수

`.env.example` 참고. 화면은 `NEXT_PUBLIC_API_URL`(없으면 목업)만 읽고, `DOCUMASTER_*`는 백엔드 전용입니다.
API 키는 두지 않습니다 — claude·codex·nlm은 각 CLI에 로그인된 계정을 씁니다.

## 알아 둘 점

- 본문 서체 Pretendard는 CDN에서 불러옵니다(오프라인이면 시스템 서체로 대체). 워드마크 서체 Nunito는 빌드 때 Google Fonts에서 받습니다.
- 캐릭터 초상은 머리색·배경색만 따온 단순 SVG입니다. 실제 이미지는 `public/avatars/`에 직접 넣으세요.
- 목록이 수백 줄 이상 길어지면 `ActivityFeed`의 `FeedRow`를 가상 스크롤 목록에 넣으면 됩니다(행 컴포넌트는 이미 분리·memo 처리됨).
