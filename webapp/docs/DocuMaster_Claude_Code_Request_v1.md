# Claude Code 구현 요청 — DocuMaster Prototype v1

첨부한 `DocuMaster_WebApp_UIUX_Prototype_v1.1.md`를 제품 요구사항 및 구현 기준으로 사용해 주세요.
함께 제공한 UI 프로토타입 이미지는 시각적 레퍼런스로 사용해 주세요.

이번 단계의 목표는 **실제 AI API가 연결되지 않은, 로컬에서 실행 가능한 클릭형 Web App Prototype**을 완성하는 것입니다.

## 핵심 목표

- Next.js + React + TypeScript + Tailwind CSS 기반
- 실제 회사 내부 협업툴처럼 보이는 정돈된 SaaS UI
- 3열 레이아웃
  - 좌측: 프로젝트 / 레퍼런스 / 워크플로우
  - 중앙: Workflow Stepper / Agent Activity Feed / 입력창
  - 우측: 작업물 / 미리보기 / Agent 설정
- 프로젝트 선택 및 화면 이동
- 6단계 Workflow 상태 표시
- Agent Message / System Event / Artifact Card 구분
- Reference 추가 UI
- Artifact 선택 및 Preview
- Agent별 Model / Reasoning dropdown
- Dummy Data 기반 실행
- 실행 버튼을 누르면 Workflow가 단계별로 진행되는 것처럼 동작
- Workflow 진행에 따라 진행률 및 Agent 상태 변경

## 이번 단계에서 하지 말 것

- 실제 Claude/OpenAI API 연결
- 실제 과금/사용량 조회
- 로그인/회원가입
- 복잡한 데이터베이스
- RAG/Vector DB
- 다중 사용자 실시간 협업
- 과도한 Backend 구현

먼저 UI와 UX를 검증할 수 있는 Prototype을 완성합니다.

## 유지보수성과 코드 품질

단순히 "작동하는 코드"가 아니라 **이후 계속 수정·확장하기 쉬운 코드베이스**를 만들어 주세요.

반드시 다음을 지켜 주세요.

1. Component를 역할별로 분리합니다.
2. 하나의 파일에 UI, 상태, API, 데이터 처리 로직을 몰아넣지 않습니다.
3. 중복 코드를 줄이고 반복되는 UI는 재사용 Component로 분리합니다.
4. TypeScript 타입을 명확하게 정의합니다.
5. Workflow 단계, 상태, Agent 정보 등 반복되는 값은 constants/types로 분리합니다.
6. Mock Data는 UI Component 안에 하드코딩하지 말고 별도 data/service 계층으로 분리합니다.
7. 향후 실제 Backend를 붙일 때 UI를 크게 다시 만들지 않도록 Service Interface를 고려합니다.
8. 특정 Claude/GPT 모델에 UI가 종속되지 않도록 Agent 모델을 일반화된 데이터 구조로 다룹니다.
9. 불필요한 dependency를 추가하지 않습니다.
10. 과도한 추상화, 과도한 상태관리 라이브러리, 과도한 최적화를 하지 않습니다.
11. 성능 최적화는 필요한 범위에서 적용합니다.
12. 불필요한 re-render, 중복 fetch, 중복 계산을 피합니다.
13. 시스템 이벤트와 진행률 표시를 위해 LLM을 호출하는 구조를 만들지 않습니다.
14. 향후 실제 LLM 연결 시 Agent별 최소 Context만 전달할 수 있는 구조를 고려합니다.
15. 사용하지 않는 import, dead code, 임시 console.log를 최종 단계에서 제거합니다.
16. TypeScript strict, lint, build 검증을 통과시킵니다.
17. 프로젝트 구조와 수정 포인트를 설명하는 README.md를 작성합니다.

우선순위는 다음과 같습니다.

**유지보수성 > 가독성 > 책임 분리 > 안정성 > 필요한 수준의 성능 최적화 > 구현 속도**

미세한 성능 이득 때문에 구조를 지나치게 복잡하게 만들지 마세요.

## 구현 방식

작업을 바로 시작하기 전에:

1. 현재 프로젝트 폴더 구조를 확인
2. 요구사항 MD를 읽기
3. 구현할 Component 구조 제안
4. 데이터/상태 흐름 제안
5. 변경/생성할 주요 파일 목록 제안

을 짧게 정리한 후 구현을 진행해 주세요.

권장 구현 순서:

```text
Phase 1
App Shell / 3열 Layout

Phase 2
Navigation / Workflow / Dummy Data

Phase 3
Agent Activity Feed / System Event / Artifact

Phase 4
Reference 추가 UI / Artifact Preview / Agent 설정

Phase 5
Dummy Workflow 실행 및 Progress 상태 변화

Phase 6
반응형 기본 처리

Phase 7
코드 정리 / lint / build / README
```

## UI 관련 원칙

- 중앙 Agent Activity Feed가 가장 중요한 영역입니다.
- 채팅/Activity 영역은 남은 높이 대부분을 사용하고 내부 스크롤을 사용합니다.
- Workflow Stepper와 하단 Prompt Input은 가능한 한 항상 보이도록 합니다.
- 화면이 좁아지면 우측 패널부터 접히게 합니다.
- Agent별 Accent Color는 구분용으로만 사용하고 과도한 색 사용을 피합니다.
- 실제 회사 협업툴처럼 차분하고 읽기 쉽게 구성합니다.

## 중요한 설계 원칙

사용자에게 보이는 Agent 대화와 실제 LLM 호출은 분리해야 합니다.

예:

- 작업 시작
- 작업 완료
- 기획자 → 조사자 handoff
- Reference 추가
- Artifact 생성
- 진행률 변경

같은 메시지는 향후에도 코드에서 생성되는 **System Event**로 처리할 수 있도록 구조화합니다.

UI 메시지 하나를 보여주기 위해 LLM을 호출하는 구조는 만들지 마세요.

## 완료 후 보고

작업이 끝나면 다음을 정리해 주세요.

1. 실행 방법
2. 생성/수정한 주요 파일과 역할
3. 구현된 기능
4. 아직 Dummy인 기능
5. 향후 실제 DocuMaster Orchestrator를 연결할 위치
6. 향후 Claude/OpenAI API를 연결할 위치
7. 유지보수를 위해 적용한 구조적 결정
8. 성능 최적화로 적용한 내용
9. lint / type check / build 결과
10. 현재 남아 있는 기술 부채 또는 주의사항

웹개발 초보자가 이후에도 AI의 도움을 받아 직접 수정할 수 있도록,
코드를 과도하게 복잡하게 만들지 말고 명확하고 일관된 구조를 유지해 주세요.
