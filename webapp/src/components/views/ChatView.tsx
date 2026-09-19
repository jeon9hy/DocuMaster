"use client";

import { getFocusStageId, isWorkflowComplete } from "@/lib/progress";
import { useAppState, useWorkspace } from "@/state/WorkspaceProvider";
import { ActivityFeed } from "../chat/ActivityFeed";
import { PromptInput } from "../chat/PromptInput";
import { StageDetail } from "../workflow/StageDetail";
import { WorkflowStepper } from "../workflow/WorkflowStepper";

/** 기본 화면: 진행 단계(상단 고정) · 활동 피드(내부 스크롤) · 입력창(하단 고정) */
export function ChatView() {
  const workspace = useWorkspace();
  const { openStageId } = useAppState();

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <WorkflowStepper stageStatus={workspace.stageStatus} openStageId={openStageId} />
      {openStageId && <StageDetail workspace={workspace} stageId={openStageId} />}
      <ActivityFeed
        projectId={workspace.project.id}
        feed={workspace.feed}
        agents={workspace.agents}
        artifacts={workspace.artifacts}
      />
      <PromptInput
        teamIds={workspace.agents.map((agent) => agent.id)}
        isRunning={workspace.isRunning}
        isComplete={isWorkflowComplete(workspace.stageStatus)}
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
