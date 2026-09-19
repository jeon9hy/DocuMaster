# DocuMaster Web App — Prototype v1

DocuMaster의 멀티 에이전트 작업(로이드·요르·유리·아냐·본드)을 **회사 협업툴 같은 화면**으로 보여 주는 클릭형 프로토타입입니다.
실제 AI API에는 연결되어 있지 않습니다. 「실행」을 누르면 목업 대본이 이벤트를 시간차로 내보내고, 화면은 그 이벤트로만 바뀝니다.

## 실행

```bash
cd webapp
npm install
npm run dev      # http://localhost:3000
```

| 명령 | 용도 |
| --- | --- |
| `npm run lint` | ESLint |
| `npx tsc --noEmit` | 타입 검사(strict) |
| `npm run build` | 배포용 빌드(타입 검사 포함) |

## 화면 구성

```
┌ TopHeader: 로고 · 프로젝트 선택 · 전체 진행률 · 알림 ─────────────────┐
│ LeftSidebar      │ 중앙 View (기본: 대화)          │ RightSidebar      │
│ 메뉴             │ WorkflowStepper (6단계)          │ 작업물 목록       │
│ 현재 프로젝트    │ ActivityFeed (내부 스크롤)       │ 미리보기          │
│ 레퍼런스         │ PromptInput (하단 고정)          │ 에이전트 설정     │
│ 워크플로우 요약  │                                  │                   │
└──────────────────┴──────────────────────────────────┴───────────────────┘
```

- **xl(1280px) 이상**: 3열 / **lg**: 오른쪽이 접힘(헤더 버튼으로 서랍) / **lg 미만**: 왼쪽도 접힘(햄버거) / **md 미만**: 하단 탭(대화·진행·레퍼런스·작업물), 에이전트 설정은 「설정」 화면

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
에이전트별 모델 / 추론 강도 드롭다운 · 실행 → 단계별 진행·진행률·에이전트 상태 변화 · 중지 후 이어서 실행 · 알림 목록 · 로딩·빈 상태·오류(다시 시도)

## 아직 목업인 것

| 기능 | 지금 | 나중에 |
| --- | --- | --- |
| 실행 | `data/mock/stageScripts.ts` 대본 재생 | 실제 오케스트레이터 이벤트 |
| 에이전트 답변 | 고정 문구 | LLM 응답 요약 |
| 레퍼런스 파일 | 이름·크기만 기록(내용 안 읽음) | 업로드·저장 |
| 「관련 단계부터 다시 실행」 | 경고 알림만 | 실제 재실행 |
| PDF 미리보기 | 표지 모양 썸네일 | 실제 첫 쪽 렌더 |
| 모델 변경 | 화면 상태만 | 서비스로 전달 |
| 데이터 보존 | 새로고침하면 초기화(메모리) | 백엔드 저장 |
| 홈 · 지식 라이브러리 · 프로젝트 설정 | 준비 중 화면 | — |

## 실제 백엔드 연결 지점

1. `src/services/WorkspaceService.ts`를 구현한 `HttpWorkspaceService`를 만듭니다 — 읽기는 REST, `subscribe`는 SSE/WebSocket으로 `WorkflowEvent`를 받습니다.
2. `src/services/index.ts`의 한 줄을 그 구현으로 바꿉니다. UI 코드는 고치지 않습니다.
3. **DocuMaster 오케스트레이터(로이드 절차)** 는 백엔드에서 돌리고, 단계 전환·파일 생성마다 위 이벤트를 보냅니다.
4. **Claude / OpenAI API** 는 백엔드에서만 부릅니다. 단계에 넘길 자료는 `selectStageContext`와 같은 규칙(`readsFrom`)으로 고릅니다. API 키는 브라우저에 두지 않습니다.

## 환경변수

`.env.example`을 `.env.local`로 복사해 씁니다. 지금은 읽는 값이 없습니다(목업).

| 이름 | 용도 |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | 실제 오케스트레이터 API 주소(연결 후) |
| `ANTHROPIC_API_KEY` · `OPENAI_API_KEY` | 백엔드 전용. 프론트엔드에 넣지 않습니다 |

## 알아 둘 점

- 본문 서체 Pretendard는 CDN에서 불러옵니다(오프라인이면 시스템 서체로 대체). 워드마크 서체 Nunito는 빌드 때 Google Fonts에서 받습니다.
- 캐릭터 초상은 머리색·배경색만 따온 단순 SVG입니다. 실제 이미지는 `public/avatars/`에 직접 넣으세요.
- 목록이 수백 줄 이상 길어지면 `ActivityFeed`의 `FeedRow`를 가상 스크롤 목록에 넣으면 됩니다(행 컴포넌트는 이미 분리·memo 처리됨).
