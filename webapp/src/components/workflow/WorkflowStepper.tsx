"use client";

import { ListChecks } from "lucide-react";
import { STAGE_STATUS } from "@/constants/status";
import { WORKFLOW_STAGES } from "@/constants/workflow";
import { cn } from "@/lib/cn";
import { useAppActions } from "@/state/WorkspaceProvider";
import type { StageStatusMap, WorkflowStageId } from "@/types";
import { Button } from "../ui/Button";
import { StageStatusIcon } from "./StageStatusIcon";

const STATUS_TEXT_CLASS = {
  completed: "text-positive-fg",
  running: "text-primary",
  pending: "text-label-assistive",
  error: "text-negative-fg",
} as const;

interface WorkflowStepperProps {
  stageStatus: StageStatusMap;
  openStageId: WorkflowStageId | null;
}

/** 중앙 상단의 가로 6단계. 단계를 누르면 아래에 상세가 펼쳐진다. */
export function WorkflowStepper({ stageStatus, openStageId }: WorkflowStepperProps) {
  const { toggleStage, setView } = useAppActions();

  return (
    <div className="flex items-center gap-3 border-b border-line bg-surface px-3 py-3 md:px-5">
      <ol className="flex min-w-0 flex-1 items-center overflow-x-auto">
        {WORKFLOW_STAGES.map((stage, index) => {
          const status = stageStatus[stage.id];
          return (
            <li key={stage.id} className="flex min-w-0 flex-1 items-center last:flex-none">
              <button
                type="button"
                onClick={() => toggleStage(stage.id)}
                aria-expanded={openStageId === stage.id}
                className={cn(
                  "flex shrink-0 items-center gap-2 rounded-lg px-1.5 py-1 text-left transition-colors hover:bg-fill-alt",
                  openStageId === stage.id && "bg-fill-alt",
                )}
              >
                <StageStatusIcon status={status} index={index + 1} />
                <span className="hidden flex-col leading-tight sm:flex">
                  <span className="text-[13px] font-semibold text-label-neutral">{stage.label}</span>
                  <span className={cn("text-[11px]", STATUS_TEXT_CLASS[status])}>
                    {STAGE_STATUS[status].label}
                  </span>
                </span>
              </button>
              {index < WORKFLOW_STAGES.length - 1 && (
                <span
                  className={cn(
                    "mx-1.5 h-px min-w-3 flex-1",
                    status === "completed" ? "bg-positive/43" : "bg-fill-strong",
                  )}
                  aria-hidden
                />
              )}
            </li>
          );
        })}
      </ol>
      <span className="hidden lg:block">
        <Button size="sm" icon={ListChecks} onClick={() => setView("dashboard")}>
          전체 계획 보기
        </Button>
      </span>
    </div>
  );
}
