import type { AgentId, AgentModelConfig } from "./agent";
import type { Artifact, ArtifactStatus, ArtifactVisibility } from "./artifact";
import type { ProjectMode, UserInputRequest } from "./project";
import type { Reference } from "./reference";
import type { WorkflowStageId } from "./workflow";

/** 05 판정(CLAUDE.md §5). 첫 줄로 정해진다. */
export type ValidationVerdict = "passed" | "conditional" | "blocked";

/** 완료 카드에 모으는 값. 백엔드가 DB·파일에 이미 있는 값만 채운다 — 모르는 값은 빠지거나 null. */
export interface RunSummary {
  durationSeconds?: number;
  costUsd?: number | null;
  verdict?: ValidationVerdict | null;
  removeCount?: number | null;
  cautionCount?: number | null;
  /** 실행 시작 때 고정한 에이전트별 모델 ID */
  models?: Partial<Record<AgentId, string>>;
  /** 첫 최종 PDF(예전 이벤트도 이 값만 있다) */
  finalArtifactId?: string | null;
  /** 최종 PDF 전부(본문 + 연습문제처럼 여러 부일 수 있다) */
  finalArtifactIds?: string[];
}

/**
 * 오케스트레이터 → UI 이벤트. 화면의 모든 변화는 이 이벤트로만 일어난다.
 * 백엔드(webapp/server)도 같은 모양으로 보낸다 — 타입을 바꾸면 server/app/events.py도 맞춘다.
 */
export type WorkflowEventPayload =
  | { type: "workflow.started" }
  | { type: "workflow.stage.started"; stageId: WorkflowStageId }
  | { type: "workflow.stage.completed"; stageId: WorkflowStageId }
  | { type: "workflow.warning"; stageId: WorkflowStageId; message: string }
  | { type: "workflow.completed"; summary?: RunSummary }
  /** 사용자가 중지를 요청함 — 현재 단계가 끝나면 멈춘다(graceful stop) */
  | { type: "workflow.stop.requested" }
  /** revise: 완료 문서의 첨삭 실행이 멈춤 — 원래 작업의 단계 상태는 그대로 둔다 */
  | { type: "workflow.stopped"; stageId: WorkflowStageId; revise?: boolean }
  | { type: "workflow.failed"; stageId: WorkflowStageId; reason: string; revise?: boolean }
  /** 첨삭이 중지·오류(사용량 한도 등)로 끊김 — 실행 버튼이 같은 세션으로 이어 간다. target = 고치던 최종 PDF 이름 */
  | { type: "revise.paused"; target: string }
  /** 다른 프로젝트가 실행 중이라 예약함 — 앞 실행이 완료·오류로 끝나면 시작한다 */
  | { type: "workflow.queued" }
  /** 예약 취소(사용자 · 시작할 수 없게 됨). 예약이 실제로 시작되면 이 이벤트 없이 workflow.started가 온다 */
  | { type: "workflow.queue.cancelled"; reason?: string }
  | { type: "project.mode.decided"; mode: ProjectMode }
  | { type: "validation.verdict"; verdict: ValidationVerdict; firstLine: string }
  | { type: "user.input.required"; request: UserInputRequest }
  | { type: "user.input.resolved"; promptId: string; answer: string }
  | { type: "agent.started"; agentId: AgentId; stageId: WorkflowStageId }
  | { type: "agent.message"; agentId: AgentId; toAgentId?: AgentId; text: string }
  | { type: "agent.activity"; agentId: AgentId; label: string }
  | { type: "agent.completed"; agentId: AgentId }
  | { type: "agent.configured"; agentId: AgentId; config: AgentModelConfig }
  /** updatedAt은 이벤트 시각(at)으로 채운다 */
  | { type: "artifact.created"; artifact: Omit<Artifact, "updatedAt"> }
  | {
      type: "artifact.updated";
      artifactId: string;
      status: ArtifactStatus;
      visibility?: ArtifactVisibility;
      summary?: string;
      /** 옛 버전으로 내려가는 것처럼 알릴 필요 없는 갱신 — 피드에 카드를 만들지 않는다 */
      silent?: boolean;
    }
  | { type: "artifact.removed"; artifactId: string }
  | { type: "handoff.created"; fromAgentId: AgentId; toAgentId: AgentId; artifactName?: string }
  /** addedAt은 이벤트 시각(at)으로 채운다 */
  | { type: "reference.added"; reference: Omit<Reference, "addedAt"> }
  | { type: "reference.removed"; referenceId: string }
  | { type: "user.message"; text: string };

export const EVENT_SCHEMA_VERSION = 1;

/** 전송 정보. 컴포넌트는 이 필드를 몰라도 된다(서비스·reducer만 쓴다). */
export interface EventEnvelope {
  schemaVersion: number;
  id: string;
  projectId: string;
  /** 실행 밖에서 생긴 이벤트(레퍼런스 추가 등)는 null */
  runId: string | null;
  /** 프로젝트 안에서 1부터 계속 증가. 이어 받기·중복 제거의 기준 */
  seq: number;
  at: string;
}

export type WorkflowEvent = WorkflowEventPayload & EventEnvelope;
