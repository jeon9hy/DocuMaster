import type { AgentId, AgentModelConfig } from "./agent";
import type { Artifact, ArtifactStatus, ArtifactVisibility } from "./artifact";
import type { ProjectMode, UserInputRequest } from "./project";
import type { Reference } from "./reference";
import type { WorkflowStageId } from "./workflow";

/** 05 판정(CLAUDE.md §5). 첫 줄로 정해진다. */
export type ValidationVerdict = "passed" | "conditional" | "blocked";

/**
 * 오케스트레이터 → UI 이벤트. 화면의 모든 변화는 이 이벤트로만 일어난다.
 * 백엔드(webapp/server)도 같은 모양으로 보낸다 — 타입을 바꾸면 server/app/events.py도 맞춘다.
 */
export type WorkflowEventPayload =
  | { type: "workflow.started" }
  | { type: "workflow.stage.started"; stageId: WorkflowStageId }
  | { type: "workflow.stage.completed"; stageId: WorkflowStageId }
  | { type: "workflow.warning"; stageId: WorkflowStageId; message: string }
  | { type: "workflow.completed" }
  /** 사용자가 중지를 요청함 — 현재 단계가 끝나면 멈춘다(graceful stop) */
  | { type: "workflow.stop.requested" }
  | { type: "workflow.stopped"; stageId: WorkflowStageId }
  | { type: "workflow.failed"; stageId: WorkflowStageId; reason: string }
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
