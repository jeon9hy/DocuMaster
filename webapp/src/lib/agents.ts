import { AGENT_IDS, AGENT_PROFILES } from "@/constants/agents";
import type { Agent, AgentId, ProjectMode } from "@/types";

/** 모드마다 일하지 않는 에이전트. 아냐는 문서 전용, 본드는 발표 전용이다(CLAUDE.md §1). */
const INACTIVE_IN_MODE: Record<ProjectMode, readonly AgentId[]> = {
  document: ["bond"],
  presentation: ["anya"],
};

function getTeamForMode(mode: ProjectMode): AgentId[] {
  return AGENT_IDS.filter((id) => !INACTIVE_IN_MODE[mode].includes(id));
}

export function createDefaultAgents(mode: ProjectMode): Agent[] {
  return getTeamForMode(mode).map((id) => ({
    id,
    config: { ...AGENT_PROFILES[id].defaultConfig },
    status: "idle",
  }));
}
