# DocuMaster Prototype Audit + Real Service Phase 2 Request

> 대상: 현재 `DocuMaster.zip` 안의 `webapp/` 프로토타입과 기존 DocuMaster 오케스트레이션  
> 목적: **현재 프로토타입이 기존 요구사항대로 구현되었는지 검토하고, 다음 단계에서 실제 사용 가능한 로컬 서비스로 전환하기 위한 구현 지침**을 제공한다.

---

# 0. 결론

현재 프로토타입은 **초기 UI/UX 요구사항과 유지보수성 요구사항을 전반적으로 잘 반영했다.**

특히 다음 구조는 유지하는 것이 좋다.

- Frontend와 서비스 계층 분리
- `WorkspaceService` 인터페이스
- `WorkflowEvent` 중심의 화면 상태 변경
- Mock Data와 UI 분리
- `types / constants / lib / services / state / components` 분리
- System Event와 LLM 메시지 분리
- Workflow 진행률을 코드로 계산
- Agent별 최소 Context 선택 구조
- Artifact 본문 Lazy Load
- 반응형 3열 UI
- TypeScript strict mode
- 최소한의 dependency

**따라서 현재 Frontend를 다시 만들지 않는다.**

다음 단계는 UI 재작성보다:

> `MockWorkspaceService`를 실제 Local Backend + Orchestrator에 연결하는 작업

이 핵심이다.

---

# 1. 검토 범위

검토한 주요 항목:

- `webapp/src/`
- `webapp/docs/`
- `webapp/README.md`
- `webapp/CLAUDE.md`
- `webapp/package.json`
- Root `CLAUDE.md`
- Root `README.md`
- 기존 DocuMaster Agent 역할 및 Pipeline
- 현재 Prototype Screenshot

코드 검증:

```text
ESLint: 통과
TypeScript strict type check: 통과
```

현재 검토 환경에서는 `next build` 도중 Linux용 Next SWC package를 npm registry에서 받으려 했으나
외부 네트워크가 차단되어 다운로드에 실패했다.

따라서:

```text
코드 오류로 build가 실패했다고 판단할 근거는 없음
```

하지만 실제 개발 PC에서는 최종적으로 반드시:

```bash
npm run lint
npx tsc --noEmit
npm run build
```

세 명령을 모두 통과시킨다.

---

# 2. 기존 요구사항 반영 여부

## 2.1 UI 구조

요구사항:

```text
Left Sidebar | Main Workspace | Right Sidebar
```

현재 구현:

```text
Left Sidebar
- 글로벌 메뉴
- 현재 프로젝트
- 레퍼런스
- Workflow

Center
- 6단계 Workflow
- Agent Activity Feed
- Prompt Input

Right
- Artifact
- Preview
- Agent Settings
```

판정:

**잘 반영됨.**

현재 Screenshot의 화면 비율도 최초 기획의 약:

```text
18% / 59% / 23%
```

구조에 가깝다.

---

## 2.2 Workflow

기획했던 6단계:

```text
1. 요구분석
2. 기획
3. 자료조사
4. 검증
5. 작성
6. 최종검수
```

현재 그대로 구현되어 있다.

진행률도 LLM에게 판단시키지 않고:

```text
완료 = 1
진행 중 = 0.5
대기 = 0
오류 = 0
```

로 계산한다.

예:

```text
2개 완료 + 3번째 진행 중
= 2.5 / 6
= 약 42%
```

현재 Screenshot의 `42%`와 일치한다.

이 방식은 유지한다.

---

## 2.3 Agent Activity Feed

다음이 분리되어 있다.

- Agent Message
- User Message
- System Event
- Artifact Card

이 구조는 실제 Backend 연결 이후에도 유지하기 좋다.

특히 다음과 같은 UI 메시지를 LLM에게 생성시키지 않는 설계가 좋다.

```text
단계 시작
단계 완료
Agent Handoff
Reference 추가
Artifact 생성
진행률 변경
```

이들은 앞으로도 Backend/System Event에서 생성한다.

---

## 2.4 유지보수 구조

현재 다음 계층이 분리되어 있다.

```text
components/
types/
constants/
data/mock/
services/
state/
lib/
hooks/
```

또한:

```text
WorkspaceService
        ↓
MockWorkspaceService
```

구조를 사용한다.

이 설계 덕분에 실제 Backend를 붙일 때 UI 전체를 뜯지 않고:

```text
MockWorkspaceService
        ↓ 교체
HttpWorkspaceService
```

방식으로 전환할 수 있다.

**이 부분은 현재 코드의 가장 중요한 장점 중 하나이므로 유지한다.**

---

# 3. 현재 코드에서 특히 잘한 부분

## 3.1 Event Driven UI

현재 화면 상태 변경은 `WorkflowEvent`를 중심으로 처리한다.

향후:

```text
Backend
   ↓
SSE
   ↓
WorkflowEvent
   ↓
applyWorkflowEvent()
   ↓
React UI
```

구조로 자연스럽게 연결할 수 있다.

---

## 3.2 최소 Context 설계

현재 `stageContext`에서:

```text
현재 단계가 읽어야 하는 Artifact
+
필요한 Reference
```

만 선택하도록 되어 있다.

실제 LLM 연결 후에도 다음은 금지한다.

```text
전체 채팅
+
전체 Log
+
전체 Artifact
+
전체 Reference
```

를 매 Agent마다 반복 전달.

---

## 3.3 Artifact Lazy Load

Artifact 목록에서는 metadata만 받고,

사용자가 Preview를 열 때만 실제 본문을 요청하는 구조다.

실제 PDF/Markdown 파일이 커지더라도 이 구조가 유리하다.

---

## 3.4 최소 Dependency

현재 Frontend dependency가 과도하지 않다.

이 원칙도 유지한다.

새 라이브러리는:

> 실제 필요성이 명확할 때만 추가한다.

---

# 4. 실제 서비스 전환 전에 수정할 부분

다음부터는 중요도 순서다.

---

# 4.1 [P0] Event에 runId와 sequence를 추가한다

현재 Event에는 대체로:

```text
event id
project id
timestamp
type
```

가 있다.

실제 서비스에서는 부족하다.

추가 권장:

```ts
{
  schemaVersion: 1,
  eventId: "...",
  projectId: "...",
  runId: "...",
  seq: 127,
  at: "...",
  type: "...",
  payload: {}
}
```

이유:

브라우저가 새로고침되거나 SSE 연결이 잠깐 끊기면:

```text
어디까지 받았는지
어떤 실행의 이벤트인지
중복 이벤트인지
빠진 이벤트가 있는지
```

알아야 한다.

`seq`는 한 Run 안에서 계속 증가하는 번호다.

```text
101
102
103
104
```

---

# 4.2 [P0] Snapshot → Subscribe 사이 Event 유실 방지

현재 Prototype은:

```text
getWorkspace()
↓
subscribe()
```

순서다.

Mock에서는 큰 문제가 없다.

하지만 실제 Backend에서는:

```text
Workspace Snapshot 받은 직후
↓
SSE 연결 전에
↓
Agent Event 발생
```

하면 Event 하나를 놓칠 수 있다.

실제 서비스에서는:

```text
GET Workspace
→ lastEventSeq 함께 반환

SSE 연결
→ afterSeq=lastEventSeq

Backend
→ 그 이후 Event를 replay
```

방식으로 해결한다.

---

# 4.3 [P0] 사용자 응답 필요 상태 추가

현재 DocuMaster Root Pipeline은 다음 상황에서 사용자의 판단이 필요하다.

- 모드가 애매함
- 범위 충돌
- 검증 blocked
- 핵심 근거 확인 불가
- 일부 외부 도구 설정 필요

따라서 새로운 Event를 추가한다.

예:

```text
workflow.awaiting_user
```

또는:

```text
user.input.required
```

예시 Payload:

```json
{
  "type": "user.input.required",
  "promptId": "p_001",
  "title": "검증 보류",
  "message": "핵심 주장 A의 원문을 확인할 수 없습니다.",
  "choices": [
    "해당 주장 제거 후 계속",
    "추가 자료 제공",
    "작업 중단"
  ]
}
```

UI에서는 일반 채팅 메시지가 아니라
눈에 띄는 **Action Card**로 보여준다.

---

# 4.4 [P0] 실행 상태를 Progress와 별도로 표시

Progress `42%`만으로는 상태를 전부 표현할 수 없다.

예:

```text
42% + 진행 중
42% + 사용자 응답 대기
42% + 중지 요청
42% + 오류
```

가 다르다.

Header 또는 Stepper 근처에 상태 Badge를 추가한다.

```text
진행 중
입력 필요
중지됨
오류
완료
```

---

# 4.5 [P0] 실제 File Reference 모델 확장

현재 Prototype은 file의:

```text
파일명
파일 크기
```

정도만 Mock으로 기록한다.

실제 서비스에서는 Reference에 다음이 필요하다.

```text
id
projectId
originalName
storedName
relativePath
mimeType
size
sha256
sourceType
parseStatus
addedAt
applyPolicy
```

`parseStatus` 예:

```text
uploaded
processing
ready
error
```

파일명은 사용자가 입력한 값을 그대로 경로로 사용하지 않는다.

Path Traversal 방지를 위해 Backend가 안전한 파일명을 생성한다.

---

# 4.6 [P0] Artifact Type을 일반화한다

현재:

```text
markdown
pdf
image
```

중심이다.

실제 DocuMaster는:

```text
md
pdf
pptx
png/jpg
기타 중간 산출물
```

이 존재할 수 있다.

따라서 장기적으로:

```ts
mimeType
extension
category
```

중심으로 바꾼다.

예:

```text
category:
- document
- presentation
- image
- data
- internal
```

---

# 4.7 [P0] Agent Model 설정과 실제 Orchestrator 규칙 일치

현재 UI에서는 Agent별 모델을 자유롭게 변경할 수 있다.

하지만 Root `CLAUDE.md`에는 Agent 역할과 모델이 이미 정해져 있다.

예:

```text
요르 → GPT 계열
유리 → Claude Sonnet
아냐 → Claude Opus
본드 → NotebookLM
```

실제 연결 전까지는:

### 권장

지원되지 않는 임의 조합은 선택하지 못하게 한다.

또는:

```text
UI 설정
→ Backend가 지원 가능 여부 확인
→ 지원되는 경우만 적용
```

실제 Backend가 반영하지 못하는 설정을
화면에서만 바꾸는 상태는 피한다.

---

# 4.8 [P0] `auto` Mode 추가

현재 Project Mode는:

```text
document
presentation
```

이다.

하지만 기존 DocuMaster는 사용자의 자연어 요청을 보고
로이드가 Mode를 판단한다.

따라서 실제 프로젝트 생성 시:

```text
자동 판정
문서
발표
```

3개를 제공하는 것이 좋다.

기본값:

```text
자동 판정
```

---

# 5. UI/UX에서 수정하면 좋은 부분

---

# 5.1 Send와 실행 버튼 차이를 더 명확하게

현재 하단에:

```text
전송 아이콘
+
실행 버튼
```

이 함께 있어 초보 사용자 입장에서는:

> 둘의 차이가 무엇인가?

헷갈릴 수 있다.

권장:

```text
[지시 보내기]
[워크플로우 실행]
```

또는 Tooltip을 명확히 제공한다.

작업 진행 중에는:

```text
[지시 보내기]
[중지 요청]
```

으로 변경한다.

---

# 5.2 실제 서비스에서는 System Event를 일부 접는다

Prototype에서는 Event 수가 적다.

실제 Pipeline에서는:

```text
단계 시작
Agent 시작
파일 생성
파일 수정
검증
Handoff
Gate
Render
Cross-check
```

등 Event가 많아진다.

모든 Event를 Chat에 한 줄씩 쌓으면
사용자가 중요한 대화를 찾기 어려워진다.

권장:

### 항상 표시

- 단계 시작
- 단계 완료
- 중요 Artifact 생성
- 검증 결과
- 사용자 입력 필요
- 오류

### 접어서 표시

- 내부 handoff
- 세부 파일 갱신
- 기술 로그

예:

```text
자료조사 진행 중

└ 세부 활동 8건 보기
```

---

# 5.3 Left Sidebar에서 Workflow가 너무 아래로 밀리지 않게 한다

현재 화면에서:

```text
Global Nav
Current Project
Reference
Workflow
```

순서다.

Reference가 많아지면 Workflow가 화면 아래로 내려갈 수 있다.

권장:

Reference Preview는 최대 3~5개만 보이고:

```text
+ 12개 더 보기
```

를 제공한다.

Workflow는 가능한 한 Sidebar에서 항상 확인 가능하게 한다.

---

# 5.4 Right Sidebar 높이 관리

현재 Artifact가 많아지면:

```text
Artifact List
↓
Preview
↓
Agent Settings
```

중 아래 영역이 멀어질 수 있다.

권장:

- Artifact List 내부 scroll
- Preview max-height
- Agent Settings는 접을 수 있는 Accordion

Agent Settings는 자주 쓰는 기능이 아니므로
항상 크게 노출할 필요는 없다.

---

# 5.5 주요 작업물과 내부 작업물 구분

실제 Pipeline에서는:

```text
00
01
02
03
04
05
06
06B
07
final
```

등이 생긴다.

사용자에게 전부 똑같은 중요도로 보여주면 복잡하다.

Artifact에:

```text
visibility = primary | internal
```

또는:

```text
importance = primary | detail
```

같은 구분을 둔다.

기본 화면:

```text
00 User Brief
01 Plan
02 Research
05 Verified Research
07 Draft
Final
```

정도만 보여준다.

`전체 보기`에서 내부 Artifact까지 보여준다.

---

# 6. 실제 서비스의 권장 목표

이번 다음 단계의 목표는:

> **공개 SaaS가 아니라, 사용자 한 명이 자신의 PC에서 실제 DocuMaster를 웹 UI로 실행할 수 있는 Local Service MVP**

로 한다.

아직 하지 않는다:

- 회원가입
- 결제
- 다중 사용자
- 조직 권한
- Cloud 배포
- Redis
- Kubernetes
- 복잡한 Queue
- Vector DB
- Public API

이것들은 실제 Local Service가 안정화된 뒤 고려한다.

---

# 7. 실제 서비스 권장 구조

```text
┌───────────────────────────────┐
│        Next.js Frontend       │
│                               │
│ 현재 Prototype 거의 유지      │
└──────────────┬────────────────┘
               │ REST + SSE
               ▼
┌───────────────────────────────┐
│      Local Backend Server     │
│                               │
│ ProjectService                │
│ RunManager                    │
│ EventStore                    │
│ FileStore                     │
│ OrchestratorAdapter           │
└───────┬─────────────┬─────────┘
        │             │
        │             └── SQLite
        │
        ▼
┌───────────────────────────────┐
│ Existing DocuMaster           │
│                               │
│ CLAUDE.md                     │
│ .claude/                      │
│ 작업/<ID>/                    │
│ 최종/<ID>/                    │
│ Python tools                  │
│ Claude Code / Codex / nlm     │
└───────────────────────────────┘
```

---

# 8. Backend 기술 선택

## 기본 권장

```text
Python 3.12
FastAPI
SQLite
```

이유:

- 기존 DocuMaster가 이미 Python 3.12를 사용
- 기존 `.claude/tools/*.py`와 같은 환경 사용 가능
- subprocess 관리가 비교적 단순
- SQLite가 Python 표준 라이브러리에 포함
- File System 접근이 편함
- SSE endpoint 구현 가능

단:

> 기존 환경을 조사했을 때 명확한 이유가 있다면 다른 Backend Stack을 제안할 수 있다.

Stack을 임의로 바꾸기 전에 사용자에게 이유를 설명한다.

---

# 9. Source of Truth를 명확히 한다

중요하다.

## 실제 파일의 Source of Truth

기존 DocuMaster File System을 유지한다.

```text
작업/<ID>/
최종/<ID>/
```

실제:

```text
Markdown
PDF
PPTX
Reference
```

파일을 DB에 Blob으로 넣지 않는다.

---

## SQLite의 역할

SQLite에는 다음을 저장한다.

```text
Project metadata
Run 상태
Event log
Agent 설정
Reference metadata
Artifact metadata
사용자 응답 요청
UI 상태 중 필요한 것
```

즉:

```text
DB = 관리대장
File System = 실제 문서
```

---

# 10. 권장 SQLite Table

최소:

```text
projects
runs
events
references
artifacts
agent_configs
pending_inputs
```

---

## projects

```text
id
display_name
workspace_id
mode
status
created_at
updated_at
```

---

## runs

```text
id
project_id
status
current_stage
started_at
finished_at
stop_requested
```

---

## events

```text
id
project_id
run_id
seq
type
payload_json
created_at
```

`project_id + run_id + seq`는 유일해야 한다.

---

## references

```text
id
project_id
name
relative_path
mime_type
size
hash
source_type
parse_status
apply_policy
created_at
```

---

## artifacts

```text
id
project_id
run_id
stage_id
name
relative_path
mime_type
status
visibility
version
updated_at
```

---

# 11. SSE 구조

Frontend는 Backend의 Event Stream을 구독한다.

예:

```text
GET /api/projects/{projectId}/events
```

Event:

```json
{
  "schemaVersion": 1,
  "eventId": "evt_123",
  "projectId": "p_001",
  "runId": "run_001",
  "seq": 35,
  "at": "2026-09-19T17:00:00+09:00",
  "type": "workflow.stage.completed",
  "payload": {
    "stageId": "research"
  }
}
```

재연결 시:

```text
Last-Event-ID
```

또는:

```text
afterSeq
```

를 사용해서 빠진 Event를 다시 전송한다.

---

# 12. REST API 권장 초안

## Project

```text
GET    /api/projects
POST   /api/projects
GET    /api/projects/{id}/workspace
```

---

## Workflow

```text
POST   /api/projects/{id}/runs
POST   /api/projects/{id}/runs/{runId}/stop
GET    /api/projects/{id}/events
```

---

## User Message

```text
POST   /api/projects/{id}/messages
```

---

## User Required Input

```text
POST   /api/projects/{id}/inputs/{promptId}/response
```

---

## Reference

```text
POST   /api/projects/{id}/references
DELETE /api/projects/{id}/references/{referenceId}
```

File Upload는:

```text
multipart/form-data
```

---

## Artifact

```text
GET /api/projects/{id}/artifacts
GET /api/projects/{id}/artifacts/{artifactId}
GET /api/projects/{id}/artifacts/{artifactId}/content
GET /api/projects/{id}/artifacts/{artifactId}/download
```

---

## Agent Settings

```text
PATCH /api/projects/{id}/agents/{agentId}
```

---

# 13. 실제 Orchestrator 연결 원칙

가장 중요한 원칙:

> 기존 DocuMaster Agent Pipeline을 Backend 안에서 새로 다시 작성하지 않는다.

현재:

```text
CLAUDE.md
.claude/
작업/
최종/
tools/
```

를 그대로 사용한다.

Backend에는:

```text
OrchestratorAdapter
```

를 둔다.

예:

```python
class OrchestratorAdapter:
    async def start_run(...)
    async def request_stop(...)
    async def resume_run(...)
```

실제 구현:

```text
ClaudeCodeOrchestratorAdapter
```

---

# 14. CLI 명령은 추측하지 않는다

Claude Code / Codex / NotebookLM을
Backend에서 실행할 때:

```text
"아마 이 옵션이겠지"
```

라고 추측해서 구현하지 않는다.

먼저 실제 PC에서:

```text
claude --help
codex --help
nlm --help
```

와 현재 Root 실행 지침을 확인한다.

그리고:

- 비대화형 실행 가능 여부
- 세션 Resume 방식
- 종료 코드
- stdout/stderr 형식
- 인증 방식

을 실제로 확인한 뒤 Adapter를 작성한다.

---

# 14A. 기존 DocuMaster 산출물 품질 보존 원칙

웹앱 전환은 **기존 DocuMaster의 산출물 생성 품질을 변경하는 작업이 아니다.**

따라서 Web App 또는 Backend 구현 편의를 이유로 다음 항목을 임의로 변경·축소·생략하지 않는다.

- Agent별 System Prompt 및 역할 지침
- Agent 역할 분담
- Agent 실행 순서
- Agent별 사용 모델
- 추론 강도 / Reasoning 설정
- Agent 간 Context 전달 규칙
- Reference 전달 및 활용 방식
- 자료조사 절차
- 사실 검증 및 Hallucination 검수 절차
- Gate / 승인 / Block 조건
- 기존 Artifact 계약
- 단계별 파일 번호 체계
- 최종 산출물 생성 절차
- 최종 산출물 검수 절차

Backend는 기존 DocuMaster Orchestrator를 대체하거나 단순화하는 계층이 아니다.

권장 구조:

```text
Web App
   ↓
Local Backend
   ↓
Thin Adapter
   ↓
Existing DocuMaster Orchestrator
```

여기서 Adapter는 다음 역할만 담당한다.

```text
실행 요청 전달
상태 수집
Event 변환
파일 메타데이터 연결
중지/재개 요청 전달
오류 전달
```

다음 역할을 Adapter가 임의로 수행하지 않는다.

```text
Agent Prompt 재작성
기존 Agent 단계 통합
모델 임의 변경
Context 임의 축약
자료조사 결과 임의 요약
검증 단계 생략
Gate 조건 완화
Artifact 구조 재설계
```

---

## 품질 보존과 토큰 최적화의 우선순위

토큰 절약이나 속도 최적화 때문에 산출물 품질을 희생하지 않는다.

특히 다음 방식은 사용자 승인 없이 적용하지 않는다.

```text
전체 Context를 짧은 요약으로 대체
고성능 모델을 저비용 모델로 교체
High Reasoning을 낮은 설정으로 변경
Agent 수 또는 검증 단계를 축소
Research 결과 원문 대신 요약만 전달
Reference 일부를 비용 절감을 위해 제외
검증 Agent를 생략
기존 Gate를 자동 통과 처리
```

토큰 최적화는 우선 다음 영역에서 수행한다.

```text
UI System Event
중복 전달
중복 파일 읽기
중복 API 호출
불필요한 History
사용하지 않는 Log
동일 Artifact 반복 전송
```

즉:

> **필요한 Context는 유지하고, 불필요한 중복만 제거한다.**

---

## 품질에 영향을 줄 가능성이 있는 변경 절차

다음 중 하나라도 변경할 필요가 있다고 판단되면
Claude Code가 바로 수정하지 않는다.

먼저 사용자에게 다음 형식으로 보고한다.

```text
변경 대상:
변경이 필요한 이유:
현재 동작:
제안 동작:
예상 장점:
산출물 품질에 미칠 수 있는 영향:
토큰/속도 영향:
대안:
```

사용자의 승인을 받은 뒤에만 적용한다.

---

## 웹앱 적용 전후 동등성 원칙

가능한 한 동일한 입력에 대해:

```text
기존 CLI/현재 방식
```

과

```text
Web App → Backend → Adapter → Existing Orchestrator
```

가 동일한:

- Pipeline
- Agent 역할
- 모델 구성
- Context 계약
- Artifact 계약
- 검증 절차

를 사용해야 한다.

Web App은 **실행 경로의 새로운 UI**이지,
별도의 저품질 Orchestrator가 되어서는 안 된다.

---

## 품질 회귀 방지 테스트

실제 Orchestrator 연결 후
기존 방식과 Web App 방식의 결과가 구조적으로 동일하게 생성되는지
최소 1개의 동일한 테스트 요청으로 비교한다.

검증 대상:

```text
실행된 Agent 순서
사용 모델
생성된 Artifact 목록
파일 번호
검증 단계 수행 여부
Gate 결과
Reference 전달 여부
최종 산출물 생성 여부
```

단, LLM의 확률적 특성상 문장 내용이 완전히 동일해야 하는 것은 아니다.

검증 목적은:

> 웹앱 연결 때문에 기존 Pipeline의 단계나 품질 보장 절차가 빠지지 않았는지 확인하는 것

이다.

---

## 품질 보존 불변조건

아래 항목은 별도 승인 없는 한 **Invariant(불변조건)** 으로 취급한다.

```text
기존 Agent 역할 체계 유지
기존 Model 배치 유지
기존 Reasoning 설정 유지
기존 Context 계약 유지
기존 Research/Validation 단계 유지
기존 Gate 규칙 유지
기존 Artifact 번호 계약 유지
기존 Finalization 절차 유지
```

Backend나 UI 구현 편의를 이유로
이 불변조건을 우회하지 않는다.

# 15. Raw Terminal Log를 Chat에 그대로 보여주지 않는다

사용자가 원하는 것은:

```text
Agent가 무엇을 하고 있는지
```

이지:

```text
CLI debug log 전체
```

가 아니다.

또한 모델의 내부 reasoning / chain-of-thought는 UI에 노출하지 않는다.

화면에는 다음만 보여준다.

```text
작업 시작
어떤 단계인지
어떤 Artifact가 생성됐는지
검증 결과
중요한 Agent summary
오류
사용자 판단 필요
```

---

# 16. 기존 파일 생성으로 실제 진행 상태를 판단할 수 있다

현재 DocuMaster는 단계별 파일명이 이미 계약으로 정해져 있다.

예:

```text
00
01
02
03
04
05
06
06B
07
```

Backend는 이것을 활용할 수 있다.

UI 6단계 Mapping 예:

```text
요구분석
→ 00

기획
→ 01

자료조사
→ 02

검증
→ 03 + 04 + 05

작성
→ 06 + 06B + 07

최종검수
→ doc-finish / cross-check / render gate / 최종
```

가능하면 단순히 CLI stdout 문자열을 파싱해서
상태를 판단하지 않는다.

기존:

```text
상태.md
파일 생성
검증 결과 파일
최종 파일
```

같은 구조화된 결과를 우선 사용한다.

---

# 17. 사용자 실시간 개입은 V1에서 단순화한다

현재 Agent가 작업 중일 때 사용자가 메시지를 보냈다고 해서
실행 중인 LLM Process에 즉시 끼어들게 만들 필요는 없다.

Local Service V1:

```text
현재 단계 종료 후 반영
```

을 기본으로 한다.

또는:

```text
다음 단계부터 반영
```

사용자가 명시적으로:

```text
현재 단계 다시 실행
```

을 선택한 경우만 재실행한다.

이렇게 하면 상태 관리가 훨씬 안정적이다.

---

# 18. Stop의 의미

실제 서비스에서 `Stop`은 우선:

> 현재 단계가 안전하게 끝난 뒤 다음 단계로 넘어가지 않는 Graceful Stop

으로 구현하는 것을 권장한다.

즉시 Process Kill은
파일이 반쯤 써진 상태를 만들 수 있다.

UI에서는:

```text
중지 요청됨
현재 단계 종료 후 멈춥니다.
```

로 표시한다.

긴급 강제 종료는 나중에 별도 기능으로 추가한다.

---

# 19. 오류 처리

최소:

```text
backend unavailable
orchestrator unavailable
claude auth required
codex auth required
notebooklm login required
file upload error
file parse error
agent process error
workflow blocked
```

를 구분한다.

사용자에게:

```text
알 수 없는 오류
```

만 보여주지 않는다.

예:

```text
NotebookLM 로그인이 필요합니다.
터미널에서 nlm login을 완료한 뒤 다시 시도하세요.
```

---

# 20. 보안 기본

Local Service여도 다음은 지킨다.

- API Key를 Browser에 보내지 않는다.
- `.env.local`을 Git에 포함하지 않는다.
- 업로드 파일 경로를 sanitize한다.
- `..` path traversal을 막는다.
- Backend가 허용한 Root 밖의 파일을 읽지 않는다.
- Shell command에 사용자 문자열을 그대로 이어붙이지 않는다.
- subprocess는 argument array 방식으로 실행한다.
- 사용자 입력을 shell interpolation하지 않는다.

---

# 21. 테스트를 이번 단계부터 추가한다

Prototype에는 테스트가 거의 없어도 괜찮았지만
실제 Backend 연결부터는 최소 테스트가 필요하다.

Frontend 최소:

```text
progress 계산
applyWorkflowEvent
stageContext
Event 순서
```

Backend 최소:

```text
Project CRUD
Event sequence
SSE replay
Reference upload
Path traversal 방지
Run 중복 실행 방지
Backend restart 후 상태 복원
```

통합 Test:

```text
Fake Orchestrator
↓
Backend Event
↓
SSE
↓
Frontend State
```

이 Happy Path를 하나 만든다.

---

# 22. Phase 계획

한 번에 전부 구현하지 않는다.

---

## Phase A — Prototype UX 정리

수정:

- Send / Run 의미 명확화
- Run Status Badge
- 사용자 입력 필요 Action Card
- Reference Preview 개수 제한
- Right Sidebar 높이 관리
- System Event 접기 구조 준비
- Agent Model 설정 실제 지원범위 표시
- Auto Mode 추가

완료 후 화면을 확인한다.

---

## Phase B — Local Backend Foundation

구현:

```text
FastAPI
SQLite
REST
SSE
HttpWorkspaceService
Event replay
Project persistence
```

아직 실제 LLM은 실행하지 않는다.

`FakeOrchestratorAdapter`로 실제 Backend 통신만 검증한다.

완료 조건:

```text
브라우저 새로고침
→ 상태 유지

Backend 재시작
→ 프로젝트 유지

SSE 연결 끊김 후 재연결
→ 빠진 Event replay

Mock Service 없이
→ HTTP Backend로 동일 UI 작동
```

---

## Phase C — 실제 File Handling

구현:

- File upload
- Reference 저장
- Artifact Metadata
- Markdown Preview
- PDF 실제 Preview 또는 Download
- PPTX Download
- Existing `작업/` / `최종/` 파일 Mapping

완료 조건:

실제 기존 프로젝트 하나를
Read-only로 Web UI에서 열어 볼 수 있다.

---

## Phase D — Existing Orchestrator Adapter

먼저 비용 없는 Read-only / Dry Run으로 검증한다.

다음:

```text
웹에서 Run
↓
Backend
↓
기존 DocuMaster Orchestrator
↓
실제 작업 폴더 생성
↓
Event 발생
↓
UI 실시간 표시
```

처음에는:

> 한 번에 하나의 Project Run

만 허용한다.

병렬 실행은 하지 않는다.

---

## Phase E — 실제 1회 Smoke Test

전체 구조가 준비된 뒤에만
실제 LLM Run을 한다.

비싼 Full Project를 반복 실행하지 않는다.

작은 테스트 작업 하나로:

```text
요구분석
기획
자료조사
검증
작성
최종검수
```

이 UI와 실제 File에 일치하는지 확인한다.

실제 모델 호출 테스트를 실행하기 전에는
사용자에게 알려준다.

---

# 23. 이번 Phase에서 하지 말 것

다음은 아직 금지한다.

- Multi-user
- OAuth
- 결제
- Cloud 배포
- Public SaaS
- Redis
- Kubernetes
- Agent 병렬 실행
- 여러 Workflow 동시 실행
- 복잡한 Vector DB
- Raw chain-of-thought 표시
- UI System Event를 위한 LLM 호출
- 기존 Root Orchestration 전면 재작성

---

# 24. Claude Code에게 보낼 실제 구현 요청

아래부터가 실제 작업 명령이다.

---

## IMPLEMENTATION REQUEST

첨부된 현재 DocuMaster Repository와 이 문서를 기준으로 작업해 주세요.

현재 `webapp/` Prototype은 UI를 다시 작성하지 않습니다.

기존 구조:

```text
WorkspaceService
WorkflowEvent
applyWorkflowEvent
MockWorkspaceService
```

를 유지하면서 실제 서비스 연결이 가능한 구조로 확장합니다.

이번 작업의 목표는 **Local Single-user Real Service MVP의 기반을 만드는 것**입니다.

### 가장 중요한 원칙

1. 기존 DocuMaster Root Orchestration을 다시 구현하지 마세요.
2. Root `CLAUDE.md`, `.claude/`, `작업/`, `최종/`, tools 구조를 유지하세요.
3. Web App은 기존 Orchestrator를 Adapter를 통해 호출하도록 만드세요.
4. Frontend가 Claude Code / Codex / NotebookLM을 직접 실행하지 않게 하세요.
5. UI System Event를 만들기 위해 LLM을 호출하지 마세요.
6. Raw terminal log나 chain-of-thought를 사용자 Chat에 표시하지 마세요.
7. 실제 Artifact와 Reference 파일 내용은 DB Blob으로 저장하지 말고 File System에 저장하세요.
8. SQLite는 metadata / state / event log 중심으로 사용하세요.
9. API Key와 Secret을 Browser에 노출하지 마세요.
10. 유지보수성 > 가독성 > 안정성 > 필요한 성능 최적화 > 속도 순서로 판단하세요.

11. 웹앱 연결로 인해 기존 DocuMaster의 Agent Prompt, 역할 분담, 모델 배치, Reasoning 설정, Context 전달 규칙, Research/Validation/Gate 절차가 바뀌지 않도록 하세요.
12. 품질에 영향을 줄 수 있는 변경은 임의 적용하지 말고, 변경 이유와 예상 영향을 먼저 사용자에게 보고하고 승인받은 뒤 적용하세요.


---

# 25. 작업 시작 전 먼저 할 일

코드를 수정하기 전에 다음을 조사해 보고해 주세요.

### A. 현재 Frontend 구조

다음이 실제 Backend 교체에 적합한지 다시 확인:

```text
WorkspaceService
WorkspaceProvider
WorkflowEvent
applyWorkflowEvent
stageContext
```

### B. 기존 Root Orchestrator

다음 파일을 필요한 부분만 확인:

```text
Root CLAUDE.md
Root README.md
.claude/로이드/실행.md
.claude/로이드/상태파일.md
관련 tools
```

### C. 현재 Local Tool

실제 설치된 명령을 확인:

```text
claude
codex
nlm
python
```

지원 옵션은 반드시 `--help` 등 실제 환경에서 확인하세요.

CLI 옵션을 추측하지 마세요.

### D. 구현 계획

수정 전에 다음을 먼저 보여 주세요.

```text
1. 추가할 폴더/파일
2. Backend 구조
3. SQLite Schema
4. API Endpoint
5. Event Schema
6. SSE reconnect 방식
7. Existing Orchestrator 연결 방식
8. 기존 코드 중 수정할 파일
```

계획을 짧게 보고한 후 구현을 진행하세요.

---

# 26. Backend 기본 구조

기본적으로 다음을 권장합니다.

```text
webapp/
├─ src/                    # 기존 Next frontend
├─ server/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/
│  │  ├─ domain/
│  │  ├─ services/
│  │  ├─ repositories/
│  │  ├─ orchestrator/
│  │  └─ infrastructure/
│  ├─ tests/
│  └─ requirements.txt 또는 pyproject.toml
└─ ...
```

단, 불필요하게 파일을 잘게 쪼개지 마세요.

각 파일은 명확한 책임을 가져야 합니다.

---

# 27. Backend 핵심 Component

최소:

```text
ProjectService
RunManager
EventStore
FileStore
OrchestratorAdapter
```

---

## RunManager

책임:

```text
Run 시작
중복 실행 방지
현재 Run 상태
Graceful Stop 요청
Orchestrator Process 관리
Run 종료
```

---

## EventStore

책임:

```text
Event append
seq 생성
Event replay
SSE subscriber 전달
```

---

## FileStore

책임:

```text
Reference 저장
Artifact 경로 관리
허용 Root 검사
파일명 sanitize
hash 계산
```

---

## OrchestratorAdapter

Interface:

```text
start
resume
request_stop
status
```

첫 구현:

```text
FakeOrchestratorAdapter
```

실제 연결:

```text
ClaudeCodeOrchestratorAdapter
```

는 Backend 기반 검증이 끝난 뒤 추가하세요.

---

# 28. Event Schema 변경

현재 Frontend Event 구조를 최대한 유지하되:

```text
schemaVersion
eventId
projectId
runId
seq
at
```

를 포함하도록 확장하세요.

중요:

기존 Component가 Event transport 세부사항을 알 필요는 없습니다.

---

# 29. Frontend 실제 Backend Adapter

추가:

```text
src/services/http/HttpWorkspaceService.ts
```

구현:

```text
REST
+
SSE
```

환경변수:

```text
NEXT_PUBLIC_API_URL
```

`services/index.ts`에서:

```text
Mock
Http
```

를 쉽게 전환 가능하게 유지하세요.

가능하면 개발 환경 flag를 사용하세요.

---

# 30. UI 수정 항목

이번에 함께 반영:

### 반드시

- Run Status Badge
- `user.input.required` Action Card
- Send / Workflow Run 구분 명확화
- Auto Mode
- unsupported Agent model 조합 방지
- Reference List overflow 관리
- Right Sidebar 내부 높이 관리

### 구조만 준비

- System Event collapse
- Primary/Internal Artifact 구분

---

# 31. 저장

Local Service 기준:

```text
SQLite
+
Existing DocuMaster File System
```

를 사용합니다.

DB 위치 예:

```text
webapp/.data/documaster.db
```

`.gitignore`에 추가하세요.

Artifact path는 absolute path가 아니라
가능하면 repository root 기준 relative path로 저장하세요.

---

# 32. 실제 Agent 연결은 마지막 단계

Backend/FakeOrchestrator가 완전히 동작하기 전에는
Claude/OpenAI/NotebookLM 실제 호출을 연결하지 마세요.

먼저:

```text
Fake Event
→ Backend
→ SQLite
→ SSE
→ HttpWorkspaceService
→ UI
```

전체 경로를 검증합니다.

---

# 33. 실제 Orchestrator 연결 시 추가 규칙

기존 DocuMaster 계약:

```text
00
01
02
03
04
05
06
06B
07
```

파일 번호를 변경하지 마세요.

기존:

```text
05 = 사실 원천
06 = 구조 원천
```

규칙을 유지하세요.

Backend 편의를 위해 Root Agent 지침을 크게 수정하지 마세요.

Web App 연결을 위해 필요한 경우에도:

> 최소한의 Bridge/Hook만 추가

하세요.

---

# 34. Agent Activity 표시 기준

Frontend에서 보여줄 내용:

```text
로이드 · 요구분석 시작
00_user_brief.md 생성
기획 단계 시작
01_plan.md 생성
요르 · 자료조사 시작
Reference 14건 확인
05 검증 결과: conditional
사용자 확인 필요
Final PDF 생성
```

표시하지 않을 내용:

```text
모델 내부 reasoning
chain-of-thought
CLI 디버그 전문
매 Tool call 원문
전체 Prompt
Secret
API Key
```

---

# 35. 실제 Run 전 확인

실제 Agent Run 전에 사용자에게:

```text
실제 Agent 실행 테스트를 시작할 준비가 되었습니다.
모델 사용량이 발생할 수 있습니다.
```

라고 알려 주세요.

사용자 승인 전에는 반복적인 Full Run을 실행하지 마세요.

기존 완료 프로젝트를 이용한 Read-only Test를 먼저 하세요.

---

# 36. 완료 조건

Phase B 완료:

- [ ] FastAPI Local Backend 실행
- [ ] SQLite 생성
- [ ] Project 저장
- [ ] Browser 새로고침 후 유지
- [ ] Backend 재시작 후 유지
- [ ] REST 동작
- [ ] SSE 동작
- [ ] Event seq 존재
- [ ] SSE reconnect/replay 동작
- [ ] HttpWorkspaceService 연결
- [ ] Frontend가 Mock이 아닌 Backend 상태로 작동
- [ ] Fake Workflow가 Backend를 통해 실행
- [ ] user.input.required 표시
- [ ] lint 통과
- [ ] type check 통과
- [ ] frontend build 통과
- [ ] backend tests 통과
- [ ] README 업데이트

Phase C 완료:

- [ ] 실제 File Reference upload
- [ ] 실제 Artifact metadata
- [ ] Markdown Preview
- [ ] PDF download/preview
- [ ] PPTX download
- [ ] 기존 완료 Project Read-only import

Phase D 완료:

- [ ] Existing DocuMaster Orchestrator Adapter
- [ ] 한 Project 한 Run
- [ ] Stage Event 변환
- [ ] Artifact 생성 실시간 반영
- [ ] 검증 blocked 처리
- [ ] Graceful Stop
- [ ] Resume 가능 여부 검증

---

# 37. 완료 후 보고 형식

작업이 끝나면 다음 순서로 보고하세요.

```text
1. 실제 구현한 범위
2. 변경 파일 목록
3. Backend 구조
4. DB Schema
5. API 목록
6. Event Schema
7. SSE reconnect 방식
8. File 저장 방식
9. 보안 처리
10. 테스트 결과
11. lint/type/build 결과
12. 아직 Fake인 부분
13. 실제 Orchestrator 연결 전 남은 일
14. 기술 부채
```

---

# 38. 최종 원칙

현재 Prototype은 버리는 것이 아니라
**실제 Backend를 끼워 넣을 수 있도록 이미 준비된 Frontend**다.

다음 단계의 목표는:

```text
예쁜 Demo
```

를 다시 만드는 것이 아니라:

```text
UI
↓
실제 Backend
↓
실제 File System
↓
기존 DocuMaster Orchestrator
```

를 안정적으로 연결하는 것이다.

가장 중요한 기준:

> 기능을 많이 만드는 것보다  
> **중간에 꺼져도 다시 이어지고, 이벤트를 놓치지 않고, 파일을 잃지 않는 구조**를 먼저 만든다.
