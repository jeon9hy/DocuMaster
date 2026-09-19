"use client";

import { X } from "lucide-react";
import { getAgentProfile } from "@/constants/agents";
import { STAGE_STATUS } from "@/constants/status";
import { STAGE_BY_ID } from "@/constants/workflow";
import { selectStageContext } from "@/lib/stageContext";
import { useAppActions } from "@/state/WorkspaceProvider";
import type { ProjectWorkspace, WorkflowStageId } from "@/types";
import { AgentAvatar } from "../agent/AgentAvatar";
import { StatusBadge } from "../ui/Badge";
import { IconButton } from "../ui/Button";

interface StageDetailProps {
  workspace: ProjectWorkspace;
  stageId: WorkflowStageId;
}

/** 선택한 단계의 설명 · 담당 · 이 단계가 받는 최소 자료 */
export function StageDetail({ workspace, stageId }: StageDetailProps) {
  const { toggleStage } = useAppActions();
  const stage = STAGE_BY_ID[stageId];
  const teamIds = new Set(workspace.agents.map((agent) => agent.id));
  const owners = stage.ownerIds.filter((id) => teamIds.has(id));
  const context = selectStageContext(workspace, stageId);
  const inputs = [
    ...context.artifacts.map((artifact) => artifact.name),
    ...(context.references.length > 0 ? [`레퍼런스 ${context.references.length}건`] : []),
  ];

  return (
    <section className="border-b border-line bg-gray-50/70 px-4 py-3 md:px-6">
      <div className="mx-auto flex max-w-[860px] items-start gap-4">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-gray-900">{stage.label}</h2>
            <StatusBadge meta={STAGE_STATUS[workspace.stageStatus[stageId]]} />
          </div>
          <p className="text-[13px] text-gray-600">{stage.description}</p>
          <dl className="flex flex-wrap gap-x-6 gap-y-2 text-[13px]">
            <div className="flex items-center gap-2">
              <dt className="text-gray-500">담당</dt>
              <dd className="flex items-center gap-1.5">
                {owners.map((id) => (
                  <span key={id} className="flex items-center gap-1 text-gray-800">
                    <AgentAvatar agentId={id} size="xs" />
                    {getAgentProfile(id).name}
                  </span>
                ))}
              </dd>
            </div>
            <div className="flex items-center gap-2">
              <dt className="text-gray-500">넘겨받는 자료</dt>
              <dd className="text-gray-800">{inputs.length > 0 ? inputs.join(", ") : "없음"}</dd>
            </div>
          </dl>
        </div>
        <IconButton icon={X} label="단계 상세 닫기" onClick={() => toggleStage(stageId)} className="size-7" />
      </div>
    </section>
  );
}
