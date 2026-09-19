"use client";

import { Menu, PanelRight } from "lucide-react";
import { computeProgress } from "@/lib/progress";
import { useAppState } from "@/state/WorkspaceProvider";
import { ProjectSelector } from "../project/ProjectSelector";
import { IconButton } from "../ui/Button";
import { ProgressBar } from "../ui/ProgressBar";
import { BrandLogo } from "./BrandLogo";
import { NotificationMenu } from "./NotificationMenu";

interface TopHeaderProps {
  onOpenLeft: () => void;
  onOpenRight: () => void;
}

export function TopHeader({ onOpenLeft, onOpenRight }: TopHeaderProps) {
  const { workspace } = useAppState();
  const progress = workspace ? computeProgress(workspace.stageStatus) : 0;

  return (
    <header className="flex h-16 shrink-0 items-center gap-3 border-b border-line bg-white px-3 md:px-5">
      <IconButton icon={Menu} label="메뉴 열기" onClick={onOpenLeft} className="lg:hidden" />
      <BrandLogo />
      <div className="ml-1 min-w-0 flex-1 md:ml-6 md:flex-none md:basis-[280px]">
        <ProjectSelector />
      </div>

      <div className="mx-auto hidden w-full max-w-sm items-center gap-3 md:flex">
        <span className="shrink-0 text-xs text-gray-500">전체 진행률</span>
        <ProgressBar value={progress} label="전체 진행률" />
        <span className="w-10 shrink-0 text-right text-sm font-semibold text-gray-900">{progress}%</span>
      </div>

      <div className="ml-auto flex shrink-0 items-center gap-1 md:ml-0">
        <IconButton icon={PanelRight} label="작업물 패널 열기" onClick={onOpenRight} className="xl:hidden" />
        <NotificationMenu feed={workspace?.feed ?? []} />
        <div className="ml-1 hidden items-center gap-2 sm:flex">
          <span className="flex size-8 items-center justify-center rounded-full bg-gray-200 text-xs font-semibold text-gray-600">
            나
          </span>
          <span className="hidden leading-tight xl:block">
            <span className="block text-sm font-medium text-gray-800">사용자</span>
            <span className="block text-[11px] text-gray-500">프로젝트 관리자</span>
          </span>
        </div>
      </div>
    </header>
  );
}
