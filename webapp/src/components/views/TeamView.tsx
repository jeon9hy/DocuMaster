"use client";

import { AGENT_IDS } from "@/constants/agents";
import { RESTING_NOTE, type AgentDisplayStatus } from "@/constants/status";
import { isRestingInMode } from "@/lib/agents";
import { useWorkspace } from "@/state/WorkspaceProvider";
import type { AgentId, ProjectWorkspace } from "@/types";
import { AgentCard } from "../agent/AgentCard";
import { ViewContainer, ViewHeader } from "./ViewHeader";

/**
 * 카드 격자. 에이전트 수로 폭을 계산하지 않는다 — 칸 수는 최소 240px로 정하고(auto-fit),
 * 카드는 칸 안에서 최대 340px로 가운데 놓는다(GRID_ITEM). 넓이에 따라 4열 · 3열 · 2열 · 1열이 저절로 정해진다.
 */
const GRID = "grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(min(240px,100%),1fr))]";
const GRID_ITEM = "w-full max-w-[340px] justify-self-center";

function displayStatus(workspace: ProjectWorkspace, id: AgentId): AgentDisplayStatus {
  if (isRestingInMode(id, workspace.project.mode)) return "resting";
  // 사용자에게 묻는 것은 로이드다(오케스트레이터)
  if (id === "loid" && workspace.runStatus === "awaitingInput") return "awaitingInput";
  return workspace.agents.find((agent) => agent.id === id)?.status ?? "idle";
}

/** 「멤버」: 팀 전체를 항상 보여 주고, 이 모드에서 쓰지 않는 에이전트는 휴식 중으로 표시한다(부르지 않는다). */
export function MembersView() {
  const workspace = useWorkspace();
  const mode = workspace.project.mode;
  return (
    <ViewContainer>
      <ViewHeader title="멤버" description="위장 가족 — 이 프로젝트의 에이전트와 지금 상태" />
      <div className={GRID}>
        {AGENT_IDS.map((id) => (
          <div key={id} className={GRID_ITEM}>
            <AgentCard
              agentId={id}
              status={displayStatus(workspace, id)}
              restingNote={mode === "auto" ? undefined : RESTING_NOTE[mode]}
            />
          </div>
        ))}
      </div>
    </ViewContainer>
  );
}

/** 「에이전트」: 팀 전체 명단과 역할(모델·추론 강도는 설정 화면에서) */
export function AgentsView() {
  return (
    <ViewContainer>
      <ViewHeader
        title="에이전트"
        description="DocuMaster 팀 전체입니다. 아냐는 문서, 본드는 발표 업무에만 참여합니다."
      />
      <div className={GRID}>
        {AGENT_IDS.map((id) => (
          <div key={id} className={GRID_ITEM}>
            <AgentCard agentId={id} />
          </div>
        ))}
      </div>
    </ViewContainer>
  );
}
