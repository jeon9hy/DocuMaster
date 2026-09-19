import type { AgentId, StageStatusMap, WorkflowStageId } from "@/types";

export interface StageDefinition {
  id: WorkflowStageId;
  label: string;
  description: string;
  ownerIds: readonly AgentId[];
  /**
   * 이 단계가 읽는 앞 단계 산출물. 실제 LLM을 붙이면 여기 적힌 것만 넘긴다
   * (전체 대화·전체 로그를 넘기지 않는다 — lib/stageContext.ts).
   */
  readsFrom: readonly WorkflowStageId[];
  usesReferences: boolean;
}

export const WORKFLOW_STAGES: readonly StageDefinition[] = [
  {
    id: "requirements",
    label: "요구분석",
    description: "주제·독자·분량·형식을 정리하고 문서/발표 모드를 판정합니다.",
    ownerIds: ["loid"],
    readsFrom: [],
    usesReferences: true,
  },
  {
    id: "planning",
    label: "기획",
    description: "핵심 질문과 목차를 세우고 기획 게이트를 통과시킵니다.",
    ownerIds: ["loid"],
    readsFrom: ["requirements"],
    usesReferences: false,
  },
  {
    id: "research",
    label: "자료조사",
    description: "요르가 원문을 직접 열어 근거를 모읍니다. 열지 않은 것은 [미확인]으로 남깁니다.",
    ownerIds: ["yor"],
    readsFrom: ["planning"],
    usesReferences: true,
  },
  {
    id: "validation",
    label: "검증",
    description: "유리가 위험한 주장을 묻고 요르가 답합니다. 로이드가 판정을 채택합니다.",
    ownerIds: ["yuri", "yor", "loid"],
    readsFrom: ["research"],
    usesReferences: false,
  },
  {
    id: "writing",
    label: "작성",
    description: "세부 구성을 확정한 뒤 문서는 아냐가, 발표는 요르·본드가 만듭니다.",
    ownerIds: ["yor", "anya", "bond"],
    readsFrom: ["planning", "validation"],
    usesReferences: false,
  },
  {
    id: "finalReview",
    label: "최종검수",
    description: "크게 박힌 수치와 결론의 강도를 원문과 대조한 뒤 최종본으로 옮깁니다.",
    ownerIds: ["loid"],
    readsFrom: ["validation", "writing"],
    usesReferences: false,
  },
];

export const STAGE_BY_ID = Object.fromEntries(
  WORKFLOW_STAGES.map((stage) => [stage.id, stage]),
) as Record<WorkflowStageId, StageDefinition>;

export function createStageStatusMap(
  overrides: Partial<StageStatusMap> = {},
): StageStatusMap {
  const map = Object.fromEntries(
    WORKFLOW_STAGES.map((stage) => [stage.id, "pending"]),
  ) as StageStatusMap;
  return { ...map, ...overrides };
}
