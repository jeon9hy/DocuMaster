"use client";

import { AGENT_IDS, getAgentProfile } from "@/constants/agents";
import { useWorkspace } from "@/state/WorkspaceProvider";
import { AgentCard } from "../agent/AgentCard";
import { ViewContainer, ViewHeader } from "./ViewHeader";

const GRID = "grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5";

/** 「멤버」: 이 프로젝트에서 일하는 에이전트와 현재 상태 */
export function MembersView() {
  const workspace = useWorkspace();
  return (
    <ViewContainer>
      <ViewHeader title="멤버" description="위장 가족 — 이 프로젝트에 참여하는 에이전트" />
      <div className={GRID}>
        {workspace.agents.map((agent) => (
          <AgentCard key={agent.id} agentId={agent.id} config={agent.config} status={agent.status} />
        ))}
      </div>
    </ViewContainer>
  );
}

/** 「에이전트」: 팀 전체 명단과 기본 모델 */
export function AgentsView() {
  return (
    <ViewContainer>
      <ViewHeader
        title="에이전트"
        description="DocuMaster 팀 전체입니다. 아냐는 문서, 본드는 발표 프로젝트에만 참여합니다."
      />
      <div className={GRID}>
        {AGENT_IDS.map((id) => (
          <AgentCard key={id} agentId={id} config={getAgentProfile(id).defaultConfig} />
        ))}
      </div>
    </ViewContainer>
  );
}
