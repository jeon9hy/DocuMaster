"use client";

import { Plus } from "lucide-react";
import { GLOBAL_NAV, PROJECT_NAV, type ViewId } from "@/constants/navigation";
import { useAppActions, useAppState, useIsOwner } from "@/state/WorkspaceProvider";
import { AddReferenceButton } from "../reference/AddReferenceButton";
import { ReferenceList } from "../reference/ReferenceList";
import { ModeBadge } from "../project/ModeBadge";
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
            <div className="rounded-xl border border-line bg-surface p-2">
              {/* 제목과 형식은 메뉴와 같은 파란 바탕 상자에 담아, 아래 메뉴 줄과 같은 폭·왼쪽선으로 맞춘다 */}
              <div className="mb-1 flex items-center gap-2 rounded-lg bg-primary/8 px-3 py-2.5">
                <p className="min-w-0 truncate text-sm font-semibold text-primary-heavy">{workspace.project.name}</p>
                <ModeBadge mode={workspace.project.mode} variant="primary" className="bg-surface" />
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
                    <Button size="sm" variant="ghost" icon={Plus} onClick={open} className="h-6 px-1.5 text-primary">
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
