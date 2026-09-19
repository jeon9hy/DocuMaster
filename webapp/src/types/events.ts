import type { AgentId, AgentModelConfig } from "./agent";
import type { Artifact, ArtifactStatus } from "./artifact";
import type { Reference } from "./reference";
import type { WorkflowStageId } from "./workflow";

/**
 * 오케스트레이터 → UI 이벤트. 화면의 모든 변화는 이 이벤트로만 일어난다.
 * 실제 백엔드를 붙일 때도 이 형식(SSE·WebSocket 등)으로 보내면 UI를 고치지 않아도 된다.
 */
export type WorkflowEventPayload =
  | { type: "workflow.started" }
  | { type: "workflow.stage.started"; stageId: WorkflowStageId }
  | { type: "workflow.stage.completed"; stageId: WorkflowStageId }
  | { type: "workflow.warning"; stageId: WorkflowStageId; message: string }
  | { type: "workflow.completed" }
  | { type: "workflow.stopped"; stageId: WorkflowStageId }
  | { type: "workflow.failed"; stageId: WorkflowStageId; reason: string }
  | { type: "agent.started"; agentId: AgentId; stageId: WorkflowStageId }
  | { type: "agent.message"; agentId: AgentId; text: string }
  | { type: "agent.completed"; agentId: AgentId }
  | { type: "agent.configured"; agentId: AgentId; config: AgentModelConfig }
  /** updatedAt은 이벤트 시각(at)으로 채운다 */
  | { type: "artifact.created"; artifact: Omit<Artifact, "updatedAt"> }
  | { type: "artifact.updated"; artifactId: string; status: ArtifactStatus }
  | { type: "handoff.created"; fromAgentId: AgentId; toAgentId: AgentId; artifactName?: string }
  /** addedAt은 이벤트 시각(at)으로 채운다 */
  | { type: "reference.added"; reference: Omit<Reference, "addedAt"> }
  | { type: "user.message"; text: string };

export type WorkflowEvent = WorkflowEventPayload & {
  id: string;
  projectId: string;
  at: string;
};
