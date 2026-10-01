"use client";

import { Menu, PanelRight } from "lucide-react";
import { computeProgress } from "@/lib/progress";
import { useAppActions, useAppState } from "@/state/WorkspaceProvider";
import { UserMenu } from "../auth/UserMenu";
import { ProjectSelector } from "../project/ProjectSelector";
import { IconButton } from "../ui/Button";
import { ProgressBar } from "../ui/ProgressBar";
import { RunStatusBadge } from "../workflow/RunStatusBadge";
import { BrandLogo } from "./BrandLogo";
import { NotificationMenu } from "./NotificationMenu";

interface TopHeaderProps {
  onOpenLeft: () => void;
  onOpenRight: () => void;
}

export function TopHeader({ onOpenLeft, onOpenRight }: TopHeaderProps) {
  const { workspace } = useAppState();
  const { setView } = useAppActions();
  const progress = workspace ? computeProgress(workspace.stageStatus) : 0;

  // md 미만: 아이콘 줄과 프로젝트 선택 줄을 나눈다 — 한 줄에 두면 이름이 「A…」로 잘린다
  return (
    <header className="shrink-0 border-b border-line bg-white">
      <div className="flex h-14 items-center gap-3 px-3 md:h-16 md:px-5">
        <IconButton icon={Menu} label="메뉴 열기" onClick={onOpenLeft} className="lg:hidden" />
        <BrandLogo onHome={() => setView("home")} />
        <div className="ml-6 hidden min-w-0 flex-none basis-[326px] md:block">
          <ProjectSelector />
        </div>

        {/* 누르면 대화창으로 — 진행 상황은 대화에서 본다 */}
        <button
          type="button"
          onClick={() => setView("chat")}
          disabled={!workspace}
          title="대화창으로 이동"
          className="mx-auto hidden w-full max-w-sm items-center gap-3 rounded-lg px-2 py-1 text-left transition-colors hover:bg-gray-50 disabled:pointer-events-none md:flex"
        >
          <span className="shrink-0 text-xs text-gray-500">전체 진행률</span>
          <ProgressBar value={progress} label="전체 진행률" />
          <span className="w-10 shrink-0 text-right text-sm font-semibold text-gray-900">{progress}%</span>
        </button>
        {workspace && (
          <span className="shrink-0">
            <RunStatusBadge status={workspace.runStatus} />
          </span>
        )}

        <div className="ml-auto flex shrink-0 items-center gap-1 md:ml-0">
          <IconButton icon={PanelRight} label="작업물 패널 열기" onClick={onOpenRight} className="xl:hidden" />
          <NotificationMenu projectId={workspace?.project.id ?? null} feed={workspace?.feed ?? []} />
          <div className="ml-1">
            <UserMenu />
          </div>
        </div>
      </div>
      <div className="px-3 pb-2 md:hidden">
        <ProjectSelector wide />
      </div>
    </header>
  );
}
