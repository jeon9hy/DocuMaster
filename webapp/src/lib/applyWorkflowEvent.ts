import type { Agent, AgentStatus, ProjectWorkspace, WorkflowEvent } from "@/types";
import { eventToFeedItem } from "./eventToFeedItem";

function setAgentStatus(agents: Agent[], match: (agent: Agent) => boolean, status: AgentStatus) {
  return agents.map((agent) => (match(agent) ? { ...agent, status } : agent));
}

/** 이벤트 하나를 받아 새 워크스페이스를 돌려준다(원본은 바꾸지 않는다). */
function applyToState(workspace: ProjectWorkspace, event: WorkflowEvent): ProjectWorkspace {
  switch (event.type) {
    case "workflow.started":
      return {
        ...workspace,
        isRunning: true,
        agents: setAgentStatus(workspace.agents, () => true, "idle"),
      };

    case "workflow.completed":
      return { ...workspace, isRunning: false };

    case "workflow.stopped":
      return {
        ...workspace,
        isRunning: false,
        stageStatus: { ...workspace.stageStatus, [event.stageId]: "pending" },
        agents: setAgentStatus(workspace.agents, (agent) => agent.status === "working", "idle"),
        artifacts: workspace.artifacts.map((artifact) =>
          artifact.status === "writing" ? { ...artifact, status: "pending" } : artifact,
        ),
      };

    case "workflow.stage.started":
      return { ...workspace, stageStatus: { ...workspace.stageStatus, [event.stageId]: "running" } };

    case "workflow.stage.completed":
      return {
        ...workspace,
        stageStatus: { ...workspace.stageStatus, [event.stageId]: "completed" },
      };

    case "workflow.failed":
      return {
        ...workspace,
        isRunning: false,
        stageStatus: { ...workspace.stageStatus, [event.stageId]: "error" },
        agents: setAgentStatus(workspace.agents, (agent) => agent.status === "working", "error"),
      };

    case "agent.started":
      return {
        ...workspace,
        agents: setAgentStatus(workspace.agents, (agent) => agent.id === event.agentId, "working"),
      };

    case "agent.completed":
      return {
        ...workspace,
        agents: setAgentStatus(workspace.agents, (agent) => agent.id === event.agentId, "done"),
      };

    case "agent.configured":
      return {
        ...workspace,
        agents: workspace.agents.map((agent) =>
          agent.id === event.agentId ? { ...agent, config: event.config } : agent,
        ),
      };

    case "artifact.created":
      return {
        ...workspace,
        artifacts: [...workspace.artifacts, { ...event.artifact, updatedAt: event.at }],
      };

    case "artifact.updated":
      return {
        ...workspace,
        artifacts: workspace.artifacts.map((artifact) =>
          artifact.id === event.artifactId
            ? { ...artifact, status: event.status, updatedAt: event.at }
            : artifact,
        ),
      };

    case "reference.added":
      return {
        ...workspace,
        references: [...workspace.references, { ...event.reference, addedAt: event.at }],
      };

    case "workflow.warning":
    case "agent.message":
    case "handoff.created":
    case "user.message":
      return workspace;
  }
}

/**
 * 화면 상태를 바꾸는 유일한 함수. 목업 서비스와 React 상태가 같은 함수를 써서
 * 프로젝트를 오가도 두 쪽이 어긋나지 않는다.
 */
export function applyWorkflowEvent(
  workspace: ProjectWorkspace,
  event: WorkflowEvent,
): ProjectWorkspace {
  const next = applyToState(workspace, event);
  const feedItem = eventToFeedItem(event, next);
  return feedItem ? { ...next, feed: [...next.feed, feedItem] } : next;
}
