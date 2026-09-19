"use client";

import type { ReactNode } from "react";
import { getAgentProfile } from "@/constants/agents";
import { STAGE_STATUS } from "@/constants/status";
import { WORKFLOW_STAGES } from "@/constants/workflow";
import { computeProgress } from "@/lib/progress";
import { useWorkspace } from "@/state/WorkspaceProvider";
import { AgentAvatar } from "../agent/AgentAvatar";
import { StatusBadge } from "../ui/Badge";
import { ProgressBar } from "../ui/ProgressBar";
import { StageStatusIcon } from "../workflow/StageStatusIcon";
import { ViewContainer, ViewHeader } from "./ViewHeader";

function StatCard({ label, value, children }: { label: string; value: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-white p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
      {children}
    </div>
  );
}

/** 프로젝트 한눈에 보기: 수치 요약 + 단계별 담당·산출물 */
export function DashboardView() {
  const workspace = useWorkspace();
  const progress = computeProgress(workspace.stageStatus);
  const completed = WORKFLOW_STAGES.filter((stage) => workspace.stageStatus[stage.id] === "completed").length;
  const latestArtifacts = workspace.artifacts.filter((artifact) => artifact.status === "latest").length;
  const teamIds = new Set(workspace.agents.map((agent) => agent.id));

  return (
    <ViewContainer>
      <ViewHeader title="대시보드" description={workspace.project.name} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="전체 진행률" value={`${progress}%`}>
          <ProgressBar value={progress} label="전체 진행률" className="mt-3" />
        </StatCard>
        <StatCard label="완료 단계" value={`${completed} / ${WORKFLOW_STAGES.length}`} />
        <StatCard label="완성된 작업물" value={`${latestArtifacts} / ${workspace.artifacts.length}`} />
        <StatCard label="레퍼런스" value={`${workspace.references.length}건`} />
      </div>

      <section className="mt-6 overflow-hidden rounded-xl border border-line bg-white">
        <h2 className="border-b border-line px-5 py-3 text-[15px] font-semibold text-gray-900">전체 계획</h2>
        <ol className="divide-y divide-gray-100">
          {WORKFLOW_STAGES.map((stage, index) => {
            const status = workspace.stageStatus[stage.id];
            const outputs = workspace.artifacts.filter((artifact) => artifact.stageId === stage.id);
            return (
              <li key={stage.id} className="flex flex-col gap-3 px-5 py-4 md:flex-row md:items-center">
                <div className="flex min-w-0 flex-1 gap-3">
                  <StageStatusIcon status={status} index={index + 1} />
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-gray-900">{stage.label}</p>
                    <p className="mt-0.5 text-[13px] text-gray-500">{stage.description}</p>
                    {outputs.length > 0 && (
                      <p className="mt-1 truncate text-xs text-gray-400">
                        산출물: {outputs.map((artifact) => artifact.name).join(", ")}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3 pl-10 md:pl-0">
                  <div className="flex -space-x-1.5">
                    {stage.ownerIds
                      .filter((id) => teamIds.has(id))
                      .map((id) => (
                        <AgentAvatar
                          key={id}
                          agentId={id}
                          size="sm"
                          className="ring-2 ring-white"
                        />
                      ))}
                  </div>
                  <span className="w-28 truncate text-xs text-gray-500">
                    {stage.ownerIds
                      .filter((id) => teamIds.has(id))
                      .map((id) => getAgentProfile(id).name)
                      .join(" · ")}
                  </span>
                  <StatusBadge meta={STAGE_STATUS[status]} />
                </div>
              </li>
            );
          })}
        </ol>
      </section>
    </ViewContainer>
  );
}
