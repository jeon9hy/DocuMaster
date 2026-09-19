import { AGENT_IDS } from "@/constants/agents";
import type { Agent, AgentId, ProjectModeChoice } from "@/types";

/**
 * 모드마다 일하지 않는 에이전트. 아냐는 문서 전용, 본드는 발표 전용이다(CLAUDE.md §1).
 * 자동 판정(auto)은 모드가 정해질 때까지 전원을 보여 준다.
 */
const INACTIVE_IN_MODE: Record<ProjectModeChoice, readonly AgentId[]> = {
  auto: [],
  document: ["bond"],
  presentation: ["anya"],
};

export function getTeamForMode(mode: ProjectModeChoice): AgentId[] {
  return AGENT_IDS.filter((id) => !INACTIVE_IN_MODE[mode].includes(id));
}

export function createDefaultAgents(mode: ProjectModeChoice): Agent[] {
  return getTeamForMode(mode).map((id) => ({
    id,
    status: "idle",
  }));
}

/** 이 모드에서 쉬는 에이전트인지(화면 표시용 — 실행과 무관하다) */
export function isRestingInMode(id: AgentId, mode: ProjectModeChoice): boolean {
  return INACTIVE_IN_MODE[mode].includes(id);
}
