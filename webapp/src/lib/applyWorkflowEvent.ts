import type { Agent, AgentStatus, ProjectWorkspace, WorkflowEvent } from "@/types";
import { createDefaultAgents } from "./agents";
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
        runStatus: "running",
        agents: setAgentStatus(workspace.agents, () => true, "idle"),
      };

    case "workflow.completed":
      return { ...workspace, runStatus: "completed", pendingInputs: [] };

    case "workflow.stop.requested":
      return { ...workspace, runStatus: "stopping" };

    case "workflow.stopped":
      return {
        ...workspace,
        runStatus: "stopped",
        pendingInputs: [],
        stageStatus:
          workspace.stageStatus[event.stageId] === "running"
            ? { ...workspace.stageStatus, [event.stageId]: "pending" }
            : workspace.stageStatus,
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
        runStatus: "failed",
        pendingInputs: [],
        stageStatus: { ...workspace.stageStatus, [event.stageId]: "error" },
        agents: setAgentStatus(workspace.agents, (agent) => agent.status === "working", "error"),
      };

    case "project.mode.decided": {
      // 판정된 모드의 팀으로 맞추되, 이미 받은 설정·상태는 유지한다.
      const previous = new Map(workspace.agents.map((agent) => [agent.id, agent]));
      return {
        ...workspace,
        project: { ...workspace.project, mode: event.mode },
        agents: createDefaultAgents(event.mode).map((agent) => previous.get(agent.id) ?? agent),
      };
    }

    case "user.input.required":
      return {
        ...workspace,
        runStatus: "awaitingInput",
        pendingInputs: [
          ...workspace.pendingInputs.filter((input) => input.promptId !== event.request.promptId),
          event.request,
        ],
      };

    case "user.input.resolved": {
      const pendingInputs = workspace.pendingInputs.filter(
        (input) => input.promptId !== event.promptId,
      );
      return {
        ...workspace,
        pendingInputs,
        runStatus:
          workspace.runStatus === "awaitingInput" && pendingInputs.length === 0
            ? "running"
            : workspace.runStatus,
      };
    }

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
      // 예전 프로젝트별 모델 설정 기록. 모델 설정은 이제 전역(설정 화면)이라 상태를 바꾸지 않는다.
      return workspace;

    case "artifact.created":
      return {
        ...workspace,
        artifacts: [
          ...workspace.artifacts.filter((artifact) => artifact.id !== event.artifact.id),
          { ...event.artifact, updatedAt: event.at },
        ],
      };

    case "artifact.updated":
      return {
        ...workspace,
        artifacts: workspace.artifacts.map((artifact) =>
          artifact.id === event.artifactId
            ? {
                ...artifact,
                status: event.status,
                updatedAt: event.at,
                visibility: event.visibility ?? artifact.visibility,
                summary: event.summary ?? artifact.summary,
              }
            : artifact,
        ),
      };

    case "artifact.removed":
      return {
        ...workspace,
        artifacts: workspace.artifacts.filter((artifact) => artifact.id !== event.artifactId),
        feed: workspace.feed.filter(
          (item) => item.kind !== "artifact" || item.artifactId !== event.artifactId,
        ),
      };

    case "reference.added":
      return {
        ...workspace,
        references: [...workspace.references, { ...event.reference, addedAt: event.at }],
      };

    case "reference.removed":
      return {
        ...workspace,
        references: workspace.references.filter((reference) => reference.id !== event.referenceId),
      };

    case "workflow.warning":
    case "validation.verdict":
    case "agent.message":
    case "agent.activity":
    case "handoff.created":
    case "user.message":
      return workspace;
  }
}

/**
 * 화면 상태를 바꾸는 유일한 함수. 목업 서비스·HTTP 서비스·React 상태가 같은 함수를 써서
 * 어디서 계산해도 상태가 어긋나지 않는다. 이미 반영한 seq의 이벤트는 무시한다(중복 전송 대비).
 */
export function applyWorkflowEvent(
  workspace: ProjectWorkspace,
  event: WorkflowEvent,
): ProjectWorkspace {
  if (event.seq <= workspace.lastEventSeq) return workspace;
  const next = { ...applyToState(workspace, event), lastEventSeq: event.seq };
  const feedItem = eventToFeedItem(event, next);
  return feedItem ? { ...next, feed: [...next.feed, feedItem] } : next;
}
