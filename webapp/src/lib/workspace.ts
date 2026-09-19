import { createStageStatusMap } from "@/constants/workflow";
import type { ProjectSummary, ProjectWorkspace, WorkflowEvent } from "@/types";
import { createDefaultAgents } from "./agents";
import { applyWorkflowEvent } from "./applyWorkflowEvent";

export function emptyWorkspace(summary: ProjectSummary): ProjectWorkspace {
  return {
    project: summary,
    runStatus: "idle",
    stageStatus: createStageStatusMap(),
    agents: createDefaultAgents(summary.mode),
    feed: [],
    references: [],
    artifacts: [],
    pendingInputs: [],
    lastEventSeq: 0,
  };
}

/**
 * 이벤트 기록을 처음부터 다시 적용해 워크스페이스를 만든다.
 * 목업 시드와 백엔드 스냅샷이 모두 이 함수를 써서, 실시간으로 받은 결과와 똑같은 규칙이 적용된다.
 */
export function buildWorkspace(
  summary: ProjectSummary,
  events: readonly WorkflowEvent[],
): ProjectWorkspace {
  return events.reduce(applyWorkflowEvent, emptyWorkspace(summary));
}
