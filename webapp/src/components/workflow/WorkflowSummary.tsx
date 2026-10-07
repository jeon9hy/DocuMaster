"use client";

import { WORKFLOW_STAGES } from "@/constants/workflow";
import { cn } from "@/lib/cn";
import { useAppActions } from "@/state/WorkspaceProvider";
import type { StageStatusMap, WorkflowStageId } from "@/types";
import { StageStatusIcon } from "./StageStatusIcon";

interface WorkflowSummaryProps {
  stageStatus: StageStatusMap;
  openStageId: WorkflowStageId | null;
}

/** 좌측 사이드바의 세로 단계 요약. 누르면 대화 화면에서 그 단계 상세를 연다. */
export function WorkflowSummary({ stageStatus, openStageId }: WorkflowSummaryProps) {
  const { toggleStage, setView } = useAppActions();
  return (
    <ol className="relative space-y-0.5">
      {WORKFLOW_STAGES.map((stage, index) => {
        const status = stageStatus[stage.id];
        return (
          <li key={stage.id}>
            <button
              type="button"
              onClick={() => {
                setView("chat");
                if (openStageId !== stage.id) toggleStage(stage.id);
              }}
              className={cn(
                "flex w-full items-center gap-2.5 rounded-lg px-3 py-1.5 text-left text-[13px] transition-colors hover:bg-fill",
                status === "running" ? "bg-primary/8 font-medium text-primary-strong" : "text-label-neutral",
              )}
            >
              <StageStatusIcon status={status} index={index + 1} size="sm" />
              {stage.label}
            </button>
          </li>
        );
      })}
    </ol>
  );
}
