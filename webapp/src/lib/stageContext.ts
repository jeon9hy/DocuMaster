import { STAGE_BY_ID } from "@/constants/workflow";
import type { Artifact, ProjectWorkspace, Reference, WorkflowStageId } from "@/types";

export interface StageContext {
  artifacts: Artifact[];
  references: Reference[];
}

/**
 * 한 단계의 에이전트에게 넘길 최소 자료.
 * 실제 LLM을 붙이면 이 결과만 프롬프트에 싣는다 — 대화 기록·시스템 로그는 넘기지 않는다.
 */
export function selectStageContext(
  workspace: ProjectWorkspace,
  stageId: WorkflowStageId,
): StageContext {
  const stage = STAGE_BY_ID[stageId];
  return {
    artifacts: workspace.artifacts.filter(
      (artifact) => artifact.status === "latest" && stage.readsFrom.includes(artifact.stageId),
    ),
    references: stage.usesReferences ? workspace.references : [],
  };
}
