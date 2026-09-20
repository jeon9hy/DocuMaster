@AGENTS.md

# webapp — 작업 지도 (세션마다 자동으로 실린다. 3.5KB 이하 유지)

**코드를 통째로 읽지 않는다.** 이 지도로 고칠 파일을 고르고 그 파일만 연다. `node_modules/`·`.next/`는 열지 않는다.
Next.js 문서(AGENTS.md)는 처음 쓰는 API가 있을 때만 해당 파일을 grep한다. 사람용 설명은 `README.md`(열 필요 없음). 원 요구사항은 `docs/`(요청서·UIUX 명세) — 요구사항을 확인할 때만 해당 절을 grep한다.

## 어디를 고치나
| 할 일 | 파일 (`src/` 기준) |
| --- | --- |
| 타입 | `types/*.ts` — 이벤트는 `types/events.ts` |
| 팀·모델·단계·상태·메뉴·로고 값 | `constants/agents · models · workflow · status · navigation · brand.ts` |
| 목업 데이터·대본 | `data/mock/seedProjects.ts`(초기 이벤트) · `stageScripts.ts`(실행 대본·답변) |
| 백엔드 창구 | `services/WorkspaceService.ts`(인터페이스) · `services/index.ts`(API URL 있으면 http, 없으면 mock) · `services/http/` · `services/mock/` |
| 로컬 백엔드 | `server/app/` — 파일별 책임은 README 「백엔드」 표. 이벤트 타입은 `types/events.ts`와 `server/app/events.py`를 함께 고친다 |
| 상태 반영 | `lib/applyWorkflowEvent.ts`(이벤트→상태) · `lib/eventToFeedItem.ts`(시스템 문구) |
| 화면 상태·동작 | `state/appReducer.ts` · `state/WorkspaceProvider.tsx`(`useAppState`·`useAppActions`·`useWorkspace`) |
| 계산 | `lib/progress · stageContext · models · mentions · references · format.ts` |
| 화면 | `components/views/*` + `viewRegistry.tsx` · 뼈대 `components/layout/AppShell.tsx` |
| 부품 | `components/{ui,chat,workflow,artifact,reference,agent,project}/` — 이름 = 역할 |
| 색·서체 | `app/globals.css`의 `@theme`(blue 계열을 로고색으로 덮어씀) · `app/layout.tsx` |
| 이미지 | `public/brand/`(로고) · `public/avatars/`(캐릭터) · `public/mock/` |

## 지킬 것
- 화면 변화는 **서비스가 내는 `WorkflowEvent` 하나로만** 일어난다. 새 동작 = 이벤트 타입 추가 → `applyWorkflowEvent` → (필요하면) `eventToFeedItem`.
- 진행·완료·전달 같은 문구는 코드에서 만든다. UI 때문에 LLM을 부르지 않는다. LLM 문장은 `agent.message`뿐.
- 반복 값은 `constants/`, 목업은 `data/mock/`. 컴포넌트에 문자열·목업을 박지 않는다. 모델명에 묶인 컴포넌트를 만들지 않는다.
- 의존성은 `next · react · tailwind · lucide-react`만. 더하기 전에 사용자에게 묻는다.
- `Button`/`IconButton`에 `hidden md:…`를 직접 주지 않는다(`inline-flex`와 충돌) — 감싼 `span`에 준다.

## 확인
`npx tsc --noEmit` → `npm run lint` → `npm test` → `npm run build`(dev 서버가 꺼져 있을 때만 — `.next`를 같이 써서 켜진 화면이 깨진다) · 백엔드 `server/.venv/Scripts/python -m pytest`.
실제 에이전트(`DOCUMASTER_ORCHESTRATOR=claude`)는 사용자 승인 없이 돌리지 않는다.
화면은 `npx next start -p 3123` 후 Edge 헤드리스(DevTools 프로토콜로 몇 초 뒤) 캡처. 끝나면 서버를 끈다.

## 현재 상태 (세션 끝에 이 절만 고친다)
- A~D 로컬 기능과 fake 전체 경로 검증 완료. Auth: 쓰기 API엔 `OWNER`, 화면은 `useIsOwner()`.
- E: 실제 Claude 실행 `run_0d6e8af110e8`(작업 ID `최저임금2026_20260920`)이 6단계 완료. 83개 이벤트, DB 작업물 17개와 실제 파일, UI 이벤트 재생 완료 상태를 대조했다. 상세 증거와 재테스트 방법은 README 「Phase E 인수인계」.
- 이번 안정화: 누적 실행 비용 중복 합산, 동일한 검증 판정 이벤트와 채팅 작업물 카드 중복을 수정. 기존 스모크 DB의 비용도 로그값으로 교정했다. Claude 사용량은 statusLine 캐시 또는 실제 headless 로그에서 읽고, 확인되지 않는 값은 표시하지 않는다.
- 대화 실시간화: `stream-json`의 실제 발언과 도구 활동을 실행 중 SSE로 보낸다. 역할을 확인한 하위 에이전트와 수신자가 확인되는 실제 전달 메시지만 이름을 붙인다. 사고 과정·쉘 명령·일반 도구 입력 전문은 보내지 않는다. 프롬프트·모델 호출·오케스트레이터 동작은 바꾸지 않았다.
- `Development / Local Verification: COMPLETE` / `Real Claude Final Acceptance: PENDING - quota`. 새 Claude 모델 호출은 한도 회복 뒤 소형 최종 재테스트 한 번에만 사용한다.
