"use client";

import { WifiOff } from "lucide-react";
import { getFocusStageId, isWorkflowComplete } from "@/lib/progress";
import { useAppState, useWorkspace } from "@/state/WorkspaceProvider";
import { ActivityFeed } from "../chat/ActivityFeed";
import { PromptInput } from "../chat/PromptInput";
import { StageDetail } from "../workflow/StageDetail";
import { WorkflowStepper } from "../workflow/WorkflowStepper";

/** 기본 화면: 진행 단계(상단 고정) · 활동 피드(내부 스크롤) · 입력창(하단 고정) */
export function ChatView() {
  const workspace = useWorkspace();
  const { openStageId, connection } = useAppState();

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <WorkflowStepper stageStatus={workspace.stageStatus} openStageId={openStageId} />
      {connection === "reconnecting" && (
        <p role="status" className="flex items-center gap-2 border-b border-amber-200 bg-amber-50 px-4 py-1.5 text-xs text-amber-800">
          <WifiOff className="size-3.5 shrink-0" aria-hidden />
          백엔드와 연결이 끊겨 다시 연결하는 중입니다. 연결되면 놓친 이벤트를 이어서 받습니다.
        </p>
      )}
      {openStageId && <StageDetail workspace={workspace} stageId={openStageId} />}
      <ActivityFeed
        projectId={workspace.project.id}
        feed={workspace.feed}
        artifacts={workspace.artifacts}
        pendingPromptIds={workspace.pendingInputs.map((input) => input.promptId)}
      />
      <PromptInput
        teamIds={workspace.agents.map((agent) => agent.id)}
        runStatus={workspace.runStatus}
        isComplete={isWorkflowComplete(workspace.stageStatus)}
        readOnly={workspace.project.readOnly}
      />
    </div>
  );
}

/** 모바일 「진행」 탭: 단계 목록과 지금 단계의 상세 */
export function ProgressPanel() {
  const workspace = useWorkspace();
  const { openStageId } = useAppState();
  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <WorkflowStepper stageStatus={workspace.stageStatus} openStageId={openStageId} />
      <StageDetail workspace={workspace} stageId={openStageId ?? getFocusStageId(workspace.stageStatus)} />
    </div>
  );
}
