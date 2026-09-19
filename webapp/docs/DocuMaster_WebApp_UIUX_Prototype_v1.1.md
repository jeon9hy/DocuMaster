# DocuMaster Web App UI/UX Prototype v1

> 목적: 기존 DocuMaster 멀티에이전트 오케스트레이션을 **회사 협업툴처럼 보이는 웹앱 UI**로 시각화하고,  
> 사용자가 프로젝트를 생성하고 → 에이전트 작업을 실행하고 → 진행 상황을 보고 → 레퍼런스를 추가하고 → 결과물을 확인하는 흐름을  
> 직관적으로 사용할 수 있는 **1차 프로토타입**을 구현한다.

---

## 0. 이 문서의 우선순위

이 단계의 목표는 **완성된 서비스가 아니라, 실제로 눌러보고 화면을 오갈 수 있는 웹앱 프로토타입**이다.

우선순위는 다음과 같다.

1. 화면 구조와 이동이 자연스러울 것
2. 처음 보는 사용자도 현재 작업 상태를 이해할 수 있을 것
3. 채팅, 진행도, 레퍼런스, 작업물이 한 화면에서 유기적으로 연결될 것
4. 실제 오케스트레이션 구조와 나중에 연결하기 쉬울 것
5. 디자인이 과하게 화려하지 않고, 실제 사내 협업툴처럼 정돈되어 보일 것
6. 기능 확장을 고려하되, 1차 구현에서는 과도한 기능을 넣지 않을 것

---


## 추가 핵심 원칙: 유지보수성과 최적화

이 프로젝트는 단기 데모가 아니라 이후 기능을 계속 붙일 수 있는 구조를 목표로 한다.

따라서 구현 시 다음 우선순위를 따른다.

1. **유지보수성**
2. **가독성**
3. **명확한 책임 분리**
4. **안정성**
5. **필요한 범위의 성능 최적화**
6. 개발 속도

단순히 "작동하는 코드"를 만드는 것이 아니라, 웹개발 초보 사용자도 이후 파일 구조와 컴포넌트 역할을 이해하고 수정할 수 있는 코드를 작성한다.


# 1. 제품 개념

DocuMaster는 여러 AI 에이전트가 역할을 분담해 문서, 보고서, 발표자료 등을 만드는 과정을  
사용자가 하나의 협업 워크스페이스에서 확인하고 개입할 수 있도록 하는 웹앱이다.

사용자는 단순히 "프롬프트를 입력하고 결과를 받는 것"이 아니라 다음 과정을 본다.

- 누가 기획 중인지
- 누가 조사 중인지
- 어떤 단계가 완료되었는지
- 어떤 레퍼런스가 사용되었는지
- 어떤 작업물이 생성되었는지
- 어느 단계에서 사용자가 개입할 수 있는지

즉, 일반 챗봇보다는 **AI 프로젝트 협업툴**에 가깝다.

---

# 2. 1차 프로토타입의 핵심 사용자 흐름

가장 중요한 기본 흐름은 아래와 같다.

```text
프로젝트 선택 또는 생성
        ↓
작업 요청 입력
        ↓
오케스트레이션 실행
        ↓
진행 단계 표시
        ↓
에이전트별 활동 로그 표시
        ↓
필요 시 레퍼런스 추가
        ↓
에이전트 간 작업 전달
        ↓
작업물 생성
        ↓
오른쪽 패널에서 작업물 확인
        ↓
미리보기 또는 다운로드
```

사용자는 가능하면 **페이지를 여러 번 이동하지 않아도** 핵심 정보를 확인할 수 있어야 한다.

---

# 3. 전체 화면 구조

데스크톱 기준으로 3열 구조를 기본으로 한다.

```text
┌────────────────────────────────────────────────────────────────────┐
│ Top Header                                                        │
├───────────────┬─────────────────────────────────┬──────────────────┤
│ Left Sidebar  │ Main Workspace                  │ Right Sidebar    │
│               │                                 │                  │
│ 프로젝트      │ 진행 단계                       │ 작업물           │
│ 레퍼런스      │                                 │ 미리보기         │
│ 워크플로우    │ 에이전트 활동 / 대화             │ 에이전트 설정     │
│               │                                 │                  │
│               │ 작업 입력창                     │                  │
└───────────────┴─────────────────────────────────┴──────────────────┘
```

권장 폭 비율:

- Left Sidebar: **18%**
- Main Workspace: **57~60%**
- Right Sidebar: **22~25%**

최소 데스크톱 기준:

- 1440px 화면을 기준으로 설계
- 중앙 대화 영역은 최소 약 720px 이상 확보
- 좌측은 약 240~260px
- 우측은 약 300~340px

중앙 작업영역이 가장 중요하므로 화면이 좁아질수록  
**우측 패널 → 좌측 패널 순서로 접을 수 있게 한다.**

---

# 4. Top Header

상단 헤더는 항상 고정한다.

구성:

- 왼쪽: DocuMaster 로고 + 서비스명
- 중앙 왼쪽: 현재 프로젝트 선택 드롭다운
- 중앙: 전체 진행률 Progress Bar
- 오른쪽: 알림, 사용자 프로필

예시:

```text
DocuMaster     [ 2026 주거 정책 보고서 ▼ ]     ███████░░░ 68%     🔔   사용자
```

상단 진행률은 단순 장식이 아니라 현재 프로젝트 상태를 한눈에 보여준다.

---

# 5. Left Sidebar

좌측은 **탐색 + 현재 프로젝트 정보** 영역이다.

## 5.1 상단 글로벌 메뉴

다음 메뉴를 둔다.

- 홈
- 프로젝트
- 에이전트
- 지식 라이브러리
- 설정

1차 프로토타입에서는 실제 기능이 없어도  
클릭 시 화면 또는 placeholder 페이지가 나타나도록 한다.

---

## 5.2 현재 프로젝트 메뉴

현재 선택된 프로젝트 아래에 다음 탭을 둔다.

- 대시보드
- 대화
- 작업물
- 멤버
- 프로젝트 설정

기본 진입 화면은 **대화**로 한다.

### 이동 방식

페이지 전체를 완전히 새로 로드하기보다는  
SPA처럼 자연스럽게 중앙 콘텐츠만 전환되는 느낌을 권장한다.

---

## 5.3 레퍼런스 영역

현재 프로젝트에 연결된 레퍼런스를 보여준다.

지원 예시:

- PDF
- 이미지
- URL
- 텍스트
- Markdown

표시 정보:

```text
📕 국토교통부_2026_보고서.pdf
PDF · 12.4MB · 오늘

🔗 주거정책 통계 데이터
웹 링크 · 오늘
```

상단에 `+ 추가` 버튼을 둔다.

클릭 시 작은 Modal 또는 Drawer가 열린다.

선택지:

- 파일 업로드
- URL 추가
- 텍스트 직접 입력

---

# 6. Workflow / Progress

현재 프로토타입에서는 **6단계**를 기본으로 한다.

1. 요구분석
2. 기획
3. 자료조사
4. 검증
5. 작성
6. 최종검수

6개 정도가 적절하다.

이유:

- 너무 적으면 실제 멀티에이전트 작업 과정이 보이지 않는다.
- 너무 많으면 사용자 입장에서 복잡하게 느껴진다.
- 5~7개가 한눈에 보기 적절하다.

상태는 4종류만 사용한다.

```text
완료
진행 중
대기
오류
```

예시:

```text
✅ 요구분석
✅ 기획
🔵 자료조사
○ 검증
○ 작성
○ 최종검수
```

중앙 상단에는 가로 Stepper로 보여주고,  
좌측 하단에는 세로 Workflow 형태로 한 번 더 요약 표시할 수 있다.

---

# 7. 중앙 Main Workspace

가장 중요한 화면이다.

구성은 크게 3부분이다.

```text
Workflow Stepper
────────────────────────
Agent Activity / Chat
────────────────────────
Prompt Input
```

---

# 8. Agent Activity / Chat

## 8.1 기본 방향

일반 메신저처럼 보여주되, 단순 인간 채팅방이 아니라  
**에이전트 실행 상태와 작업 결과를 섞어서 보여주는 Activity Feed** 형태로 한다.

예시:

```text
마리코 · 기획
발표 목표와 슬라이드 구조 초안을 정리했습니다.

[01_기획안.md]

티와리 · 조사
관련 자료 14건을 수집했습니다.
정부 통계와 논문 중심으로 검토 중입니다.

[수집한 레퍼런스 14건]

SYSTEM
새 레퍼런스가 추가되었습니다.

서린 · 검수
통계 수치의 출처와 기준 연도를 다시 확인하겠습니다.
```

---

## 8.2 메시지 종류

UI에서 4종류로 구분한다.

### A. Agent Message

실제 에이전트의 요약 메시지

### B. System Event

예:

```text
📎 새 레퍼런스 추가됨
🔄 기획자 → 조사자 전달 완료
✅ 작업물 생성 완료
⚠ 검증 오류 발견
```

### C. Artifact Card

생성 파일 표시

```text
01_기획안.md
02_근거자료.md
final.pdf
```

### D. User Message

사용자가 중간에 추가 지시를 입력한 경우

---

# 9. 매우 중요한 토큰 절약 원칙

**UI에 보이는 모든 대화를 실제 LLM 호출로 만들지 않는다.**

예를 들어 다음 메시지는 시스템에서 직접 생성할 수 있다.

```text
기획 단계 시작
기획 완료
조사 에이전트로 전달
새 레퍼런스 추가
작업물 생성
검증 단계 시작
```

즉,

```text
UI 메시지 ≠ 항상 LLM 메시지
```

실제 LLM 호출은 필요한 작업에만 사용한다.

권장 원칙:

- 진행 상태 메시지 → 시스템 이벤트로 생성
- 파일 생성 알림 → 시스템 이벤트
- handoff → 시스템 이벤트
- 완료 메시지 → 시스템 이벤트
- 모델 응답 요약이 필요한 경우에만 Agent Message 사용

---

# 10. 채팅 영역 크기

채팅은 메인 화면에서 가장 큰 비중을 차지해야 한다.

1440px 기준 권장:

- 상단 Header: 약 64px
- Workflow Stepper: 약 70~90px
- Bottom Prompt Bar: 약 80~100px
- 나머지 전체 공간: Chat / Activity Feed

채팅 영역은 **페이지 높이의 약 65~75%**가 적절하다.

스크롤은 전체 페이지가 아니라  
**중앙 Chat 영역 내부에서 독립적으로 스크롤**되게 한다.

이렇게 해야 상단 진행도와 하단 입력창이 항상 보인다.

---

# 11. Bottom Prompt Input

하단 입력창은 고정한다.

구성:

```text
[ + ]  에이전트에게 작업 지시를 입력하세요...       @    [레퍼런스 추가] [실행]
```

지원 동작:

- 일반 텍스트 지시
- @Agent 호출
- 레퍼런스 추가
- 실행
- Enter 전송
- Shift + Enter 줄바꿈

---

# 12. Right Sidebar

오른쪽은 결과물 중심 영역이다.

구성:

1. 작업물
2. 미리보기
3. 에이전트 설정

---

# 13. 작업물 / Artifacts

작업물이 생성될 때마다 자동 추가된다.

예:

```text
작업물 (4)

📄 01_기획안.md        최신
📄 02_근거자료.md      작성 중
📄 03_발표팩.md        대기
📕 final.pdf           대기
```

상태:

- 최신
- 작성 중
- 대기
- 오류

파일 클릭 시 아래 미리보기 영역에 표시한다.

---

# 14. Artifact Preview

우측에 간단한 미리보기를 제공한다.

1차 프로토타입에서는 완전한 문서 렌더링까지 하지 않아도 된다.

지원:

- Markdown → 텍스트 미리보기
- PDF → 첫 페이지 썸네일
- 이미지 → 이미지 표시

클릭하면 중앙 또는 Modal로 확대 가능하게 한다.

---

# 15. Agent Settings

오른쪽 하단에 간단한 에이전트 설정 영역을 둔다.

예:

```text
마리코
역할: 기획
Model: Claude Opus 5
Reasoning: High

서린
역할: 검수
Model: Claude Opus 5
Reasoning: High

티와리
역할: 조사
Model: GPT-5.6 Sol
Reasoning: High
```

1차 프로토타입에서는 dropdown UI만 구현해도 된다.

실제 모델 변경 연결은 추후 구현 가능.

---

# 16. Reference 실시간 추가 UX

작업 실행 중에도 레퍼런스를 추가할 수 있어야 한다.

버튼:

```text
+ 레퍼런스 추가
```

추가 후 선택 옵션:

```text
새 레퍼런스를 어떻게 반영할까요?

○ 다음 단계부터 반영
○ 현재 Agent에게 전달
○ 관련 단계부터 다시 실행
```

기본값은:

```text
다음 단계부터 반영
```

이유:

불필요한 Agent 재실행과 토큰 낭비 방지.

---

# 17. 프로젝트 이동 UX

프로젝트 전환은 상단 Project Selector를 사용한다.

예:

```text
2026 주거 정책 보고서 ▼
```

클릭 시:

```text
최근 프로젝트

2026 주거 정책 보고서
치이카와 세계관 발표
수환경공학 보고서
+ 새 프로젝트
```

프로젝트를 변경하면 좌측 레퍼런스 / Workflow / 중앙 대화 / 우측 작업물 전체가 해당 프로젝트 기준으로 변경된다.

---

# 18. 반응형 UI

## Desktop

기본 3열

```text
Left | Center | Right
```

## Tablet

좌측 Sidebar 접기

```text
Center | Right
```

좌측은 햄버거 버튼으로 열 수 있다.

## Mobile

모든 패널을 동시에 표시하지 않는다.

하단 탭 추천:

```text
대화 | 진행 | 레퍼런스 | 작업물
```

모바일에서 Agent Settings는 별도 설정 페이지로 이동.

---

# 19. 프로토타입에서 실제로 클릭 가능해야 하는 요소

최소 다음은 실제 동작해야 한다.

### Navigation

- 프로젝트
- 대화
- 작업물
- 설정

### Workflow

- 각 단계 클릭
- 선택한 단계의 간단한 상세 정보 표시

### Reference

- + 추가
- 파일 선택 UI
- 리스트에 추가

### Artifact

- 작업물 클릭
- 미리보기 변경

### Agent

- Agent 설정 dropdown

### Chat

- 메시지 입력
- 실행 클릭
- 샘플 Agent 메시지 추가

### Project

- 프로젝트 Dropdown
- 프로젝트 변경

---

# 20. 1차 MVP에서 구현하지 않아도 되는 것

다음은 나중에 구현한다.

- 사용자 로그인
- 결제
- 실제 사용량 과금
- 복잡한 권한 시스템
- 다중 사용자 실시간 협업
- 댓글
- 버전 관리
- 모든 파일 형식 완벽한 Preview
- 모바일 완전 최적화
- Push Notification
- 실제 모델 비용 통계
- 복잡한 RAG 시스템
- Vector DB

지금은 UI/UX 흐름이 먼저다.

---

# 21. 디자인 방향

전체 분위기:

> 실제 회사 내부에서 사용하는 AI 협업툴

키워드:

- clean
- professional
- calm
- productivity
- enterprise SaaS
- minimal
- readable

피해야 할 것:

- 과도한 gradient
- 너무 많은 색상
- 게임 같은 UI
- 지나치게 큰 아이콘
- 정보가 빽빽한 화면
- 강한 그림자
- 지나치게 둥근 카드
- 불필요한 animation

---

# 22. 색상 가이드

기본 색상:

- Background: #F7F8FA 계열
- Panel: White
- Border: #E5E7EB
- Primary: Blue 계열
- Success: Green
- Warning: Orange
- Error: Red
- Text Primary: 거의 Black
- Text Secondary: Gray

Agent별 Accent Color는 구분용으로만 사용한다.

예:

- 마리코: Purple
- 서린: Violet
- 티와리: Teal

하지만 메시지 전체를 강한 색으로 칠하지 않는다.

---

# 23. 타이포그래피

추천:

- Pretendard
- Inter
- system-ui

우선순위:

```css
font-family:
Pretendard,
Inter,
system-ui,
sans-serif;
```

본문:

14~15px

Agent 이름:

15~16px SemiBold

Panel Title:

16~18px SemiBold

Project Title:

18~20px

---

# 24. Component 설계

가능하면 재사용 가능한 Component로 나눈다.

예:

```text
AppShell
TopHeader
LeftSidebar
ProjectSelector

WorkflowStepper
WorkflowItem

AgentMessage
SystemEvent
ArtifactCard
ReferenceCard

PromptInput

RightSidebar
ArtifactList
ArtifactPreview
AgentSettings

Modal
Drawer
Dropdown
Badge
ProgressBar
```

---

# 25. Frontend 기술 방향

현재 프로토타입 추천:

```text
Next.js
React
TypeScript
Tailwind CSS
```

UI Component는 필요하면 다음 계열 사용 가능:

```text
shadcn/ui
Radix UI
Lucide Icons
```

단, 특정 라이브러리에 지나치게 의존하지 않는다.

---

# 26. 상태 관리

1차 프로토타입에서는 복잡한 상태 관리 라이브러리는 필수가 아니다.

React state 또는 Context 정도로 시작한다.

예:

```text
currentProject
selectedWorkflow
messages
references
artifacts
agents
progress
```

---

# 27. Prototype용 Dummy Data

실제 API 연결 전에는 Dummy Data를 사용한다.

예:

```json
{
  "project": "2026 주거 정책 보고서",
  "progress": 68,
  "currentStage": "research",
  "agents": [
    {
      "name": "마리코",
      "role": "기획",
      "model": "Claude Opus 5",
      "reasoning": "High"
    },
    {
      "name": "서린",
      "role": "검수",
      "model": "Claude Opus 5",
      "reasoning": "High"
    },
    {
      "name": "티와리",
      "role": "조사",
      "model": "GPT-5.6 Sol",
      "reasoning": "High"
    }
  ]
}
```

---

# 28. 실제 Backend 연결을 고려한 Event 구조

향후 실제 오케스트레이터와 연결하기 쉽게  
UI 이벤트를 다음처럼 생각한다.

```text
project.created

workflow.started
workflow.stage.started
workflow.stage.completed

agent.started
agent.message
agent.completed

artifact.created
artifact.updated

reference.added

handoff.created

workflow.completed
workflow.failed
```

예:

```json
{
  "type": "agent.started",
  "agent": "티와리",
  "stage": "research"
}
```

UI에서는 이것을:

```text
티와리
자료조사를 시작했습니다.
```

로 표시한다.

---

# 29. 토큰 / Context 관리 원칙

이 원칙은 실제 구현 단계에서 반드시 유지한다.

## 금지

모든 에이전트에게:

```text
전체 채팅
+
전체 레퍼런스
+
전체 이전 결과
+
전체 시스템 로그
```

를 매번 전달하는 방식.

## 권장

각 Agent가 필요한 정보만 전달받는다.

```text
기획 Agent
↓
plan.md

조사 Agent
↓
plan.md + 필요한 reference

검수 Agent
↓
evidence.md + 핵심 source

작성 Agent
↓
plan.md + verified evidence
```

즉:

> Context는 역할별 최소 단위로 전달한다.

---

# 30. UI와 실제 Agent 실행의 분리

매우 중요.

```text
화면상의 대화
≠
실제 Agent끼리 자유로운 대화
```

사용자에게는 협업하는 것처럼 보여도 된다.

하지만 Backend에서는:

```text
Agent A 결과 생성
↓
Artifact 저장
↓
Agent B 호출
```

만으로 충분하다.

UI에서는:

```text
마리코 → 티와리
기획안 전달 완료
```

로 표현한다.

이 방식이 더 안정적이며 토큰도 절약된다.

---

# 31. 프로토타입 초기 화면

처음 실행 시 다음 화면이 기본이다.

### Header

DocuMaster  
2026 주거 정책 보고서  
전체 진행률 68%

### Left

Project / Reference / Workflow

### Center

6단계 Workflow

Agent Chat

### Right

Artifacts  
Preview  
Agent Settings

### Bottom

Prompt Input + Reference + Run

---

# 32. 현재 참고할 Prototype 이미지의 핵심 구조

현재 생성된 UI Prototype의 구조와 느낌을 기준으로 구현한다.

핵심은 다음과 같다.

- 3 Column Layout
- White / Light Gray Base
- Blue Primary Accent
- Agent별 부드러운 Accent Color
- 회사 협업툴 느낌
- 중앙 Chat이 가장 큰 영역
- 진행 상태가 항상 보임
- 작업물이 오른쪽에 항상 보임
- 레퍼런스가 왼쪽에 항상 보임
- 입력창은 하단 고정

디자인을 완전히 동일하게 복제할 필요는 없지만  
**정보 구조와 사용 흐름은 최대한 유지한다.**

---

# 33. 1차 구현 완료 조건

다음이 모두 가능하면 Prototype v1 완료로 본다.

- [ ] 프로젝트를 선택할 수 있다.
- [ ] 좌측 메뉴를 클릭해 화면을 이동할 수 있다.
- [ ] Workflow 6단계가 표시된다.
- [ ] 각 단계 상태가 시각적으로 구분된다.
- [ ] Agent 메시지가 메신저처럼 표시된다.
- [ ] System Event가 Agent Message와 구분된다.
- [ ] 레퍼런스를 UI에서 추가할 수 있다.
- [ ] Artifact 리스트가 표시된다.
- [ ] Artifact 클릭 시 Preview가 변경된다.
- [ ] Agent별 Model / Reasoning dropdown이 있다.
- [ ] 하단 Prompt 입력이 가능하다.
- [ ] 실행 버튼 클릭 시 Dummy Workflow가 진행되는 것처럼 보인다.
- [ ] 진행률이 단계에 따라 변화한다.
- [ ] 전체 디자인이 실제 SaaS / 회사 협업툴 수준으로 정돈되어 있다.

---

# 34. Claude Code에게 요청할 구현 방식

먼저 한 번에 Backend와 실제 AI API까지 연결하지 않는다.

순서:

```text
Phase 1
UI Prototype 구현

Phase 2
Dummy workflow animation / state 구현

Phase 3
Local backend 연결

Phase 4
기존 DocuMaster orchestration 연결

Phase 5
LLM API 연결

Phase 6
실제 Reference / Artifact 처리
```

---

# 35. Claude에게 전달할 최종 지시

다음 원칙으로 구현한다.

> 이 프로젝트는 웹개발 초보 사용자가 앞으로 직접 수정하며 사용할 예정이다.  
> 따라서 코드 구조를 과도하게 복잡하게 만들지 말고, 파일과 Component의 역할을 명확히 구분한다.  
> 먼저 실제 AI API 없이 Dummy Data로 동작하는 클릭 가능한 Prototype을 완성한다.  
> 프로토타입이 승인된 이후 Backend와 기존 DocuMaster 오케스트레이션을 연결한다.
>
> UI는 일반 챗봇보다는 회사의 프로젝트 협업툴처럼 보여야 한다.  
> 가장 중요한 화면은 중앙 Agent Activity / Chat이며, 사용자는 항상 현재 Workflow 진행 상태, Reference, Artifact를 확인할 수 있어야 한다.
>
> 사용자에게 보이는 Agent 대화와 실제 LLM 호출은 분리한다.  
> 진행 알림, 파일 생성, Handoff 등의 UI 메시지는 시스템 이벤트로 생성하여 불필요한 LLM 호출을 만들지 않는다.
>
> 각 Agent에게 전체 Context를 반복 전달하지 말고, 해당 단계에 필요한 최소 Context와 Artifact만 전달할 수 있도록 향후 Backend 구조를 고려한다.
>
> 먼저 Prototype v1을 구현하고, 구현 완료 후 사용자에게 실제 화면을 보여준 뒤 레이아웃과 UX를 수정한다.



# 36. 유지보수성 및 코드 최적화 요구사항

이 항목은 Prototype v1 구현에서도 반드시 적용한다.

## 36.1 기본 원칙

코드는 다음 기준으로 작성한다.

- 한 파일에 너무 많은 역할을 넣지 않는다.
- UI, 상태 관리, 데이터, API/서비스 로직을 가능한 한 분리한다.
- 중복 코드를 최소화한다.
- 같은 패턴이 2~3회 이상 반복되면 재사용 Component 또는 Utility로 분리한다.
- 의미 없는 추상화나 지나친 패턴 적용은 피한다.
- "나중에 쓸 수도 있음"을 이유로 불필요한 구조를 미리 만들지 않는다.
- 초보자가 파일명을 보고 역할을 추측할 수 있도록 명확한 이름을 사용한다.
- 함수와 Component는 한 가지 책임을 갖도록 한다.

목표는 **복잡한 엔터프라이즈 구조**가 아니라,
**작고 명확하며 확장 가능한 구조**다.

---

## 36.2 권장 폴더 구조

예시:

```text
src/
├─ app/
│  ├─ page.tsx
│  └─ ...
│
├─ components/
│  ├─ layout/
│  │  ├─ TopHeader.tsx
│  │  ├─ LeftSidebar.tsx
│  │  └─ RightSidebar.tsx
│  │
│  ├─ workflow/
│  │  ├─ WorkflowStepper.tsx
│  │  └─ WorkflowItem.tsx
│  │
│  ├─ chat/
│  │  ├─ AgentMessage.tsx
│  │  ├─ SystemEvent.tsx
│  │  ├─ ArtifactCard.tsx
│  │  └─ PromptInput.tsx
│  │
│  ├─ reference/
│  ├─ artifact/
│  └─ agent/
│
├─ data/
│  └─ mock/
│
├─ hooks/
│
├─ lib/
│
├─ services/
│
├─ types/
│
└─ constants/
```

폴더는 실제 필요에 따라 조정할 수 있지만,
한 기능이 여러 위치에 무질서하게 흩어지지 않도록 한다.

---

## 36.3 UI와 비즈니스 로직 분리

Component 안에 다음을 모두 넣지 않는다.

```text
UI 표시
+
workflow 계산
+
API 호출
+
파일 처리
+
상태 변경
```

가능하면 다음처럼 분리한다.

```text
Component
    ↓
Hook / State
    ↓
Service
    ↓
Backend / API
```

예:

```text
PromptInput.tsx
    ↓
useWorkflow()
    ↓
workflowService.ts
```

UI Component는 가능한 한
"무엇을 보여줄지"와 "사용자 입력을 전달하는 일"에 집중한다.

---

## 36.4 타입 정의

TypeScript의 타입을 적극 사용한다.

예:

```ts
type WorkflowStage =
  | "requirements"
  | "planning"
  | "research"
  | "validation"
  | "writing"
  | "finalReview";

type StageStatus =
  | "pending"
  | "running"
  | "completed"
  | "error";
```

Agent, Artifact, Reference, Project, Message도 공통 타입으로 정의한다.

문자열을 여러 파일에서 직접 반복하지 않는다.

---

## 36.5 상수 관리

Workflow 단계, 상태 이름, 기본 모델, UI Label 등은
가능하면 중앙에서 관리한다.

예:

```text
constants/workflow.ts
constants/agents.ts
```

금지 예:

여러 Component 내부에 다음 값을 각각 직접 작성:

```text
"자료조사"
"research"
"진행 중"
```

---

## 36.6 Mock Data와 실제 Data 분리

Prototype에서는 Dummy Data를 사용하지만,
나중에 실제 Backend를 붙일 때 UI를 대규모로 수정하지 않도록 한다.

권장:

```text
UI
 ↓
Service Interface
 ↓
Mock Service
```

향후:

```text
UI
 ↓
Service Interface
 ↓
Real API Service
```

즉, UI가 Mock Data 구조에 강하게 종속되지 않도록 한다.

---

## 36.7 실제 Orchestrator 연결을 고려한 추상화

UI가 특정 모델 이름이나 API 공급자에 직접 묶이지 않도록 한다.

좋은 방향:

```ts
Agent {
  id
  name
  role
  provider
  model
  reasoningLevel
}
```

피해야 할 방향:

```text
Claude 전용 Component
GPT 전용 Component
```

모델이 추가되더라도 같은 UI 구조를 재사용할 수 있어야 한다.

---

## 36.8 상태 관리 원칙

Prototype 단계에서는 복잡한 전역 상태 라이브러리를 먼저 도입하지 않는다.

가능하면 다음 순서로 판단한다.

1. Local State
2. React Context
3. 필요성이 확인된 경우에만 별도 상태관리 라이브러리

불필요하게 Redux, Zustand 등을 먼저 넣지 않는다.

단, 상태가 복잡해지면 향후 교체하기 쉽도록
상태 접근 로직을 Hook으로 분리한다.

---

## 36.9 성능 최적화 원칙

최적화는 반드시 하되, **측정되지 않은 과도한 최적화는 하지 않는다.**

Prototype 단계에서 우선 적용:

- 불필요한 re-render 방지
- 큰 목록에는 안정적인 key 사용
- 불필요한 API 호출 방지
- 같은 데이터를 중복으로 fetch하지 않음
- 이미지 크기 최적화
- 대형 Component 분리
- 필요 시 lazy loading
- 파일 preview는 필요한 시점에만 로딩
- 긴 Agent Activity Feed는 추후 virtualization 적용 가능하도록 구조 고려

피해야 할 것:

- 단순 화면에 복잡한 memoization 남발
- 지나친 캐싱
- 의미 없는 micro-optimization

---

## 36.10 LLM/API 비용 최적화

Web UI 때문에 불필요한 토큰 사용량이 증가하지 않도록 한다.

반드시 지킬 것:

- 진행률 계산을 LLM에게 요청하지 않는다.
- "작업 시작", "완료", "handoff" 같은 UI 문구를 생성하기 위해 LLM을 호출하지 않는다.
- 시스템 이벤트는 코드에서 생성한다.
- 모든 Agent에게 전체 대화를 매번 전달하지 않는다.
- 각 Agent에 필요한 최소 Context만 전달한다.
- 같은 Reference를 불필요하게 반복 전송하지 않는다.
- 새 Reference 추가 시 전체 Workflow를 기본적으로 다시 실행하지 않는다.
- 결과물은 Artifact로 저장하고 필요한 Agent가 필요한 Artifact만 읽도록 한다.

---

## 36.11 에러 처리

사용자에게 빈 화면이나 알 수 없는 오류를 보여주지 않는다.

최소 상태:

```text
loading
success
empty
error
```

예:

```text
레퍼런스를 불러오지 못했습니다.
[다시 시도]
```

Agent Workflow가 실패한 경우에도
어느 단계에서 실패했는지 표시할 수 있도록 구조를 만든다.

---

## 36.12 환경변수

API Key, Secret 등은 코드에 직접 작성하지 않는다.

예:

```text
.env.local
```

그리고 `.env.example`을 제공한다.

실제 Secret은 Git에 포함하지 않는다.

---

## 36.13 코드 품질 도구

가능하면 다음을 활성화한다.

- TypeScript strict mode
- ESLint
- Prettier 또는 일관된 Formatter
- Next.js 기본 lint/type check

최종 구현 후 최소 다음을 확인한다.

```text
npm run lint
npm run build
```

또는 프로젝트에 대응되는 검증 명령.

오류가 남은 상태로 완료 처리하지 않는다.

---

## 36.14 주석 원칙

코드를 그대로 읽으면 알 수 있는 내용을 반복해서 주석으로 쓰지 않는다.

주석은 다음에 집중한다.

- 왜 이 구조를 사용했는지
- 일반적이지 않은 처리
- 중요한 제약사항
- 향후 실제 Backend 연결 포인트

---

## 36.15 불필요한 코드 제거

Prototype 구현 과정에서 발생한 다음 요소는 완료 전 정리한다.

- 사용하지 않는 Component
- 사용하지 않는 import
- 임시 console.log
- 테스트용 코드
- 중복된 CSS
- 사용하지 않는 state
- 죽은 코드(dead code)

---

## 36.16 README 작성

프로젝트 루트에 README.md를 작성한다.

최소 포함:

```text
프로젝트 설명
실행 방법
폴더 구조
주요 Component
현재 구현된 기능
Dummy 기능
실제 API 연결 예정 지점
환경변수 설명
```

웹개발 초보 사용자도 README만 보고
프로젝트 구조를 다시 이해할 수 있어야 한다.

---

# 37. Prototype 완료 전 코드 검수 체크리스트

Claude Code는 구현 완료 전에 스스로 다음을 확인한다.

- [ ] 동일한 UI 코드가 불필요하게 반복되지 않는가
- [ ] Component가 과도하게 비대해지지 않았는가
- [ ] 파일명과 함수명이 역할을 명확하게 설명하는가
- [ ] TypeScript 타입이 적절하게 정의되어 있는가
- [ ] Mock Data와 UI가 지나치게 결합되어 있지 않은가
- [ ] 향후 실제 Backend 연결이 쉬운 구조인가
- [ ] 불필요한 dependency가 추가되지 않았는가
- [ ] 불필요한 re-render 또는 반복 계산이 없는가
- [ ] 시스템 이벤트 때문에 LLM을 호출하지 않는 구조인가
- [ ] 사용하지 않는 코드가 남아 있지 않은가
- [ ] lint/type/build 오류가 없는가
- [ ] README가 최신 상태인가

---

# 38. 구현 시 최종 판단 기준

두 가지 구현 방식이 모두 동작한다면 다음 순서로 선택한다.

```text
더 단순한 구조
>
더 읽기 쉬운 구조
>
수정 범위가 작은 구조
>
의존성이 적은 구조
>
확장하기 쉬운 구조
>
미세한 성능 우위
```

성능상 명확한 문제가 없는 상황에서
복잡한 최적화를 위해 유지보수성을 희생하지 않는다.

목표는:

> "웹개발 초보자가 AI의 도움을 받아 앞으로 계속 고쳐 쓸 수 있는 코드베이스"

이다.
