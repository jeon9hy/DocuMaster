import { AGENT_PROFILES } from "@/constants/agents";
import { APPLY_POLICY_LABEL } from "@/constants/references";
import { STAGE_BY_ID } from "@/constants/workflow";
import type { FeedItem, ProjectWorkspace, WorkflowEvent } from "@/types";
import { describeModelConfig } from "./models";

/**
 * 이벤트 → 피드 한 줄. 진행·완료·전달 같은 문구는 전부 여기서 코드로 만든다(LLM 호출 없음).
 * 피드에 남길 필요가 없는 이벤트는 null.
 */
export function eventToFeedItem(
  event: WorkflowEvent,
  workspace: ProjectWorkspace,
): FeedItem | null {
  const base = { id: event.id, createdAt: event.at };
  const name = (id: keyof typeof AGENT_PROFILES) => AGENT_PROFILES[id].name;

  switch (event.type) {
    case "user.message":
      return { ...base, kind: "user", text: event.text };

    case "agent.message":
      return { ...base, kind: "agent", agentId: event.agentId, text: event.text };

    case "workflow.started":
      return { ...base, kind: "system", tone: "info", title: "워크플로우 실행 시작" };

    case "workflow.stage.started":
      return {
        ...base,
        kind: "system",
        tone: "info",
        title: `${STAGE_BY_ID[event.stageId].label} 단계 시작`,
      };

    case "workflow.stage.completed":
      return {
        ...base,
        kind: "system",
        tone: "success",
        title: `${STAGE_BY_ID[event.stageId].label} 단계 완료`,
      };

    case "workflow.warning":
      return {
        ...base,
        kind: "system",
        tone: "warning",
        title: `${STAGE_BY_ID[event.stageId].label} 단계 확인 필요`,
        detail: event.message,
      };

    case "workflow.completed":
      return {
        ...base,
        kind: "system",
        tone: "success",
        title: "워크플로우 완료",
        detail: "최종본이 작업물에 추가되었습니다.",
      };

    case "workflow.stopped":
      return {
        ...base,
        kind: "system",
        tone: "warning",
        title: "실행 중지",
        detail: `${STAGE_BY_ID[event.stageId].label} 단계는 대기로 돌아갑니다. 다시 실행하면 이 단계부터 이어서 합니다.`,
      };

    case "workflow.failed":
      return {
        ...base,
        kind: "system",
        tone: "error",
        title: `${STAGE_BY_ID[event.stageId].label} 단계 실패`,
        detail: event.reason,
      };

    case "agent.started":
      return {
        ...base,
        kind: "system",
        tone: "info",
        agentId: event.agentId,
        title: `${name(event.agentId)} · ${STAGE_BY_ID[event.stageId].label} 작업 시작`,
      };

    case "agent.configured":
      return {
        ...base,
        kind: "system",
        tone: "info",
        agentId: event.agentId,
        title: `${name(event.agentId)} 모델 변경`,
        detail: describeModelConfig(event.config),
      };

    case "handoff.created":
      return {
        ...base,
        kind: "system",
        tone: "info",
        title: `${name(event.fromAgentId)} → ${name(event.toAgentId)} 전달 완료`,
        detail: event.artifactName,
      };

    case "reference.added":
      return {
        ...base,
        kind: "system",
        tone: "info",
        title: "새 레퍼런스 추가됨",
        detail: `${event.reference.name} · ${APPLY_POLICY_LABEL[event.reference.applyPolicy]}`,
      };

    // 작업물은 '최신'이 되는 순간에만 카드로 보여 준다.
    case "artifact.created":
      return event.artifact.status === "latest"
        ? { ...base, kind: "artifact", artifactId: event.artifact.id, agentId: event.artifact.agentId }
        : null;

    case "artifact.updated": {
      const artifact = workspace.artifacts.find((item) => item.id === event.artifactId);
      return artifact && event.status === "latest"
        ? { ...base, kind: "artifact", artifactId: artifact.id, agentId: artifact.agentId }
        : null;
    }

    case "agent.completed":
      return null;
  }
}
