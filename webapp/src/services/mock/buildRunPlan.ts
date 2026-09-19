import { STAGE_SCRIPTS, type ScriptStep } from "@/data/mock/stageScripts";
import { WORKFLOW_STAGES } from "@/constants/workflow";
import { createId } from "@/lib/ids";
import type {
  ArtifactContent,
  ProjectWorkspace,
  WorkflowEventPayload,
  WorkflowStageId,
} from "@/types";

/** 앞 이벤트 뒤 몇 ms 후에 내보낼지. content가 있으면 그 순간 미리보기 본문도 저장한다. */
export interface PlannedEvent {
  delayMs: number;
  payload: WorkflowEventPayload;
  content?: { artifactId: string; value: ArtifactContent };
}

const DELAY = {
  short: 500,
  medium: 900,
  long: 1500,
} as const;

function planStep(
  step: ScriptStep,
  stageId: WorkflowStageId,
  workspace: ProjectWorkspace,
): PlannedEvent[] {
  switch (step.kind) {
    case "start":
      return [{ delayMs: DELAY.short, payload: { type: "agent.started", agentId: step.agentId, stageId } }];
    case "say":
      return [{ delayMs: DELAY.long, payload: { type: "agent.message", agentId: step.agentId, text: step.text } }];
    case "handoff":
      return [
        {
          delayMs: DELAY.medium,
          payload: {
            type: "handoff.created",
            fromAgentId: step.from,
            toAgentId: step.to,
            artifactName: step.artifactName,
          },
        },
      ];
    case "warning":
      return [{ delayMs: DELAY.medium, payload: { type: "workflow.warning", stageId, message: step.message } }];
    case "done":
      return [{ delayMs: DELAY.short, payload: { type: "agent.completed", agentId: step.agentId } }];
    case "artifact": {
      // 대기 중인 같은 이름의 작업물이 있으면 새로 만들지 않고 그 항목을 채운다.
      const existing = workspace.artifacts.find((artifact) => artifact.name === step.name);
      const artifactId = existing?.id ?? createId("artifact");
      const begin: WorkflowEventPayload = existing
        ? { type: "artifact.updated", artifactId, status: "writing" }
        : {
            type: "artifact.created",
            artifact: {
              id: artifactId,
              name: step.name,
              fileType: step.fileType,
              status: "writing",
              stageId,
              agentId: step.agentId,
              summary: step.summary,
            },
          };
      return [
        { delayMs: DELAY.medium, payload: begin },
        {
          delayMs: DELAY.long,
          payload: { type: "artifact.updated", artifactId, status: "latest" },
          content: { artifactId, value: step.content },
        },
      ];
    }
  }
}

/** 끝나지 않은 첫 단계부터 마지막 단계까지의 목업 이벤트 목록 */
export function buildRunPlan(workspace: ProjectWorkspace): PlannedEvent[] {
  const scripts = STAGE_SCRIPTS[workspace.project.mode];
  const plan: PlannedEvent[] = [{ delayMs: 0, payload: { type: "workflow.started" } }];

  for (const stage of WORKFLOW_STAGES) {
    const status = workspace.stageStatus[stage.id];
    if (status === "completed") continue;
    if (status !== "running") {
      plan.push({ delayMs: DELAY.medium, payload: { type: "workflow.stage.started", stageId: stage.id } });
    }
    for (const step of scripts[stage.id]) {
      plan.push(...planStep(step, stage.id, workspace));
    }
    plan.push({ delayMs: DELAY.short, payload: { type: "workflow.stage.completed", stageId: stage.id } });
  }

  plan.push({ delayMs: DELAY.medium, payload: { type: "workflow.completed" } });
  return plan;
}
