import { WORKFLOW_STAGES } from "@/constants/workflow";
import type { StageStatusMap, WorkflowStageId } from "@/types";

/** 진행 중인 단계는 절반만큼 친다. 진행률은 LLM에 묻지 않고 단계 상태로만 계산한다. */
const STAGE_WEIGHT = { completed: 1, running: 0.5, pending: 0, error: 0 } as const;

export function computeProgress(stageStatus: StageStatusMap): number {
  const done = WORKFLOW_STAGES.reduce(
    (sum, stage) => sum + STAGE_WEIGHT[stageStatus[stage.id]],
    0,
  );
  return Math.round((done / WORKFLOW_STAGES.length) * 100);
}

/** 지금 봐야 할 단계: 오류 → 진행 중 → 첫 대기 → 마지막 단계 순 */
export function getFocusStageId(stageStatus: StageStatusMap): WorkflowStageId {
  const find = (status: string) =>
    WORKFLOW_STAGES.find((stage) => stageStatus[stage.id] === status)?.id;
  return (
    find("error") ??
    find("running") ??
    find("pending") ??
    WORKFLOW_STAGES[WORKFLOW_STAGES.length - 1].id
  );
}

export function isWorkflowComplete(stageStatus: StageStatusMap): boolean {
  return WORKFLOW_STAGES.every((stage) => stageStatus[stage.id] === "completed");
}
