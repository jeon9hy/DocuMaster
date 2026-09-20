# DocuMaster 리팩터링 보고서

## 1. Executive Summary

2026-09-21 현재 코드를 기준으로 실행 경로를 추적하고, 사용자 기능과 데이터 계약을 바꾸지 않는 두 곳의 중복 처리를 줄였다. 이벤트 저장 직후의 재조회 1회를 없앴고, 실행 감시의 매 폴링 DB 재조회 1회와 변함없는 run 상태 쓰기를 없앴다. 실제 Claude 호출은 하지 않았다.

기존 미커밋 변경(`CLAUDE.md`, `AGENTS.md`, `webapp/.env.example`, `webapp/README.md`, `webapp/server/app/config.py`, `webapp/start.bat`)은 이 작업의 변경으로 포함하지 않았다. 현재 코드의 기본 오케스트레이터는 그 미커밋 설정에 따라 `claude`이며, 테스트는 명시적으로 `fake`를 사용한다.

## 2. Architecture Before / After

실제 경로: Next.js의 `WorkspaceProvider` → `HttpWorkspaceService` → FastAPI REST → `RunManager` → `OrchestratorAdapter`의 `claude -p` 또는 fake 프로세스 → `작업/<ID>/workspace` 및 `최종/<ID>` 파일 → `scanner`/`ArtifactSync` → SQLite `events` → SSE → 프런트 reducer. SQLite는 프로젝트·실행·이벤트·작업물 메타데이터를 저장하고 본문 파일은 파일시스템에 둔다. Codex는 백엔드의 독립 provider가 아니라 Claude 로이드가 `.claude/로이드/실행.md`에 따라 호출하는 CLI다. README의 `stageContext`는 화면의 단계 상세 표시용이며 실제 LLM 프롬프트를 구성하지 않는다.

변경 후에도 구성요소와 API·DB 스키마·artifact 경로·6단계 순서는 같다. `EventStore.append`는 INSERT에 쓴 값으로 SSE envelope을 만들고, replay는 저장된 행을 읽는다. `RunManager._tick`은 `ArtifactSync`가 갱신한 프로젝트 모드를 그대로 사용하며, 단계 담당자가 바뀌었을 때만 run 상태를 저장한다.

## 3. Token Optimization

실제 첫 턴 프롬프트는 사용자 원문, 명시된 형식, 참고자료 **경로**만 포함한다. 재개 턴은 같은 Claude 세션에 답변 또는 짧은 이어가기 문장만 전달한다. Codex 조사와 기획은 별도 세션이며, 06 기획은 조사 대화 전체를 다시 싣지 않고 05 검증본을 파일로 읽게 한다. 07 작성도 00·05·06·06B 파일 경로만 전달한다. 공통 근거 정책과 역할 지침은 `.claude/` 파일이 원본이다.

토큰을 줄이기 위해 지침이나 검증된 사실을 제거하지 않았다. 서로 다른 새 Codex 세션에서 역할 지침을 다시 전달하는 부분은 존재하지만, 생략 시 역할·품질 계약 손실 위험이 있어 유지했다. **이번 변경으로 입증된 LLM 토큰 감소량은 0 또는 측정 불가**다. 기존 로그만으로 단계별 입력 토큰과 재사용 캐시 효과를 분리할 수 없어 추정치를 만들지 않았다. 실제 Claude 재검증 전까지 토큰 절감 효과를 주장하지 않는다.

## 4. Performance

코드 경로 기준으로 이벤트 append마다 INSERT 후 `SELECT * FROM events WHERE id = ?` 1회를 제거했다. 실행 감시 폴링마다 프로젝트 모드 재조회 1회를 제거했다. 단계 담당자가 그대로인 폴링에서는 run UPDATE와 그에 따른 write transaction 1회를 제거했다. 폴링 주기·파일 스캔·SSE 이벤트 수는 바꾸지 않았다. 실제 API 응답시간과 LLM 호출 전 지연의 before/after 수치는 측정하지 못했다. 두 번의 빌드 시간 차이는 캐시와 실행 환경의 영향이 커서 성능 개선 수치로 사용하지 않는다.

## 5. Maintainability

모드 결정의 소유자가 `ArtifactSync`임을 감시 경로에 명확히 하고, 한 번 조회한 project 객체를 재사용한다. event append가 저장값과 전달값을 각각 구성하되 같은 원본 필드를 사용하도록 했다. 새 회귀 테스트는 append 결과와 DB replay의 envelope 일치를 확인한다.

## 6. Removed Code

이벤트 append 직후 동일 행 재조회, 폴링 중 중복 프로젝트 조회, 값이 변하지 않은 run 상태 UPDATE를 제거했다. dead code나 dependency 삭제는 사용 여부를 충분히 입증하지 못해 하지 않았다.

## 7. Risk Assessment

event envelope의 즉시 생성 경로가 replay와 달라질 위험은 동일성 테스트로 확인했다. 모드 판정 직후 단계 추적이 바뀔 위험은 기존 fake 실행 테스트로 확인했다. 저장된 프로젝트·DB 스키마·인증·API·SSE seq/replay 형식은 수정하지 않았다. 실제 Claude의 자식 에이전트 품질은 이번 검증 범위 밖이다.

## 8. Test Results

| 검사 | 변경 전 | 변경 후 |
| --- | --- | --- |
| 백엔드 pytest, fake provider | 59 통과 | 60 통과 |
| 프런트 전체 `npm test` | 12 통과 | 12 통과 |
| TypeScript `tsc --noEmit` | 통과 | 통과 |
| ESLint `src tests` | 통과 | 통과 |
| Next.js production build | 통과 | 통과 |
| `git diff --check` | 해당 없음 | 통과 |

기존 백엔드 테스트는 프로젝트 재시작·DB 호환성, 작업 생성, artifact 생성/조회, 단계 전달, 모델 선택·Claude adapter 명령, 오류, 중지, SSE 재연결/replay를 포함한다. 프런트 통합 테스트는 fake 실행을 REST/SSE와 reducer까지 연결한다. 실제 사용자 DB·작업 폴더는 변경하지 않았다. 검사 명령의 최초 sandbox 실행은 임시 디렉터리 접근 및 자식 프로세스 권한 문제로 실패했고, 승인된 실행 환경에서 통과했다.

## 9. Claude Real Verification Pending

`CLAUDE_REAL_VERIFICATION_PENDING`: 사용량 회복 뒤 별도 작은 작업 한 번으로 실제 `claude` 실행을 검증한다. 실행 ID를 기준으로 6단계 순서, 모델 설정 반영, 05/06 계약, 최종 artifact와 DB 파일 목록, SSE 새로고침·재연결, 오류 및 사용량 표시를 대조한다. 실제 호출이 필요한 토큰·품질 비교도 그때만 수행한다.

## 10. Remaining Technical Debt

- 파일 스캐너는 폴링마다 workspace를 다시 훑는다. 파일 변경 감지와 중지 시점 계약이 얽혀 있어 계측 없이 캐시를 넣지 않았다.
- 큰 `RunManager`와 프런트 Context의 렌더 범위는 후보지만, 현재 근거만으로 분리 또는 memoization의 이득을 확인할 수 없다.
- 상태 DB와 이벤트 append가 별도 transaction인 경로가 있다. 원자화는 실패 시 복구 의미가 바뀌므로 별도 설계·검증이 필요하다.
- 실제 prompt/context 토큰 크기, 중복 전달 횟수, API p95, 폴링별 I/O의 절대량은 측정 불가다. 민감한 프롬프트 전문을 로깅하는 방식은 도입하지 않았다.
