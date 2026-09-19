export type WorkflowStageId =
  | "requirements"
  | "planning"
  | "research"
  | "validation"
  | "writing"
  | "finalReview";

export type StageStatus = "pending" | "running" | "completed" | "error";

export type StageStatusMap = Record<WorkflowStageId, StageStatus>;
