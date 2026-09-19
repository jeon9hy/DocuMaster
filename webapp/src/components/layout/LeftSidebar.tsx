"use client";

import { Plus } from "lucide-react";
import { GLOBAL_NAV, PROJECT_MODE_LABEL, PROJECT_NAV, type ViewId } from "@/constants/navigation";
import { useAppActions, useAppState, useIsOwner } from "@/state/WorkspaceProvider";
import { AddReferenceButton } from "../reference/AddReferenceButton";
import { ReferenceList } from "../reference/ReferenceList";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { SectionLabel } from "../ui/Panel";
import { WorkflowSummary } from "../workflow/WorkflowSummary";
import { NavList } from "./NavList";

/** 탐색 + 현재 프로젝트(메뉴·레퍼런스·워크플로우) */
export function LeftSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { workspace, view, openStageId } = useAppState();
  const { setView, removeReference } = useAppActions();
  const isOwner = useIsOwner();

  const navigate = (next: ViewId) => {
    setView(next);
    onNavigate?.();
  };

  return (
    <nav aria-label="주 메뉴" className="flex flex-col gap-5 px-3 py-4">
      <NavList items={GLOBAL_NAV} activeView={view} onSelect={navigate} />

      {workspace && (
        <>
          <div>
            <SectionLabel>현재 프로젝트</SectionLabel>
            <div className="rounded-xl border border-line bg-white p-2">
              <div className="px-2 pt-1 pb-2">
                <div className="flex items-center gap-2">
                  <p className="min-w-0 flex-1 truncate text-sm font-semibold text-gray-900">
                    {workspace.project.name}
                  </p>
                  <Badge variant="primary">{PROJECT_MODE_LABEL[workspace.project.mode]}</Badge>
                </div>
                <p className="mt-0.5 truncate text-xs text-gray-500">{workspace.project.description}</p>
              </div>
              <NavList items={PROJECT_NAV} activeView={view} onSelect={navigate} />
            </div>
          </div>

          <div>
            <SectionLabel
              action={
                isOwner && !workspace.project.readOnly && (
                <AddReferenceButton>
                  {(open) => (
                    <Button size="sm" variant="ghost" icon={Plus} onClick={open} className="h-6 px-1.5 text-blue-600">
                      추가
                    </Button>
                  )}
                </AddReferenceButton>
                )
              }
            >
              레퍼런스 ({workspace.references.length})
            </SectionLabel>
            {/* 레퍼런스가 많아져도 워크플로우가 밀려나지 않게 이 칸만 안에서 스크롤한다 */}
            <div className="scrollbar-thin max-h-56 overflow-y-auto">
              <ReferenceList
                references={workspace.references}
                limit={3}
                onRemove={isOwner && !workspace.project.readOnly ? removeReference : undefined}
              />
            </div>
          </div>

          <div>
            <SectionLabel>워크플로우</SectionLabel>
            <WorkflowSummary stageStatus={workspace.stageStatus} openStageId={openStageId} />
          </div>
        </>
      )}
    </nav>
  );
}
