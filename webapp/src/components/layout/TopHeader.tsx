"use client";

import { Menu, PanelRightClose, PanelRightOpen } from "lucide-react";
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
  /** xl 이상에서는 오른쪽 패널을 접고 펴고, 그보다 좁으면 서랍으로 연다 */
  onToggleRight: () => void;
  rightCollapsed: boolean;
}

export function TopHeader({ onOpenLeft, onToggleRight, rightCollapsed }: TopHeaderProps) {
  const { workspace } = useAppState();
  const { setView } = useAppActions();
  const progress = workspace ? computeProgress(workspace.stageStatus) : 0;

  // md 미만: 아이콘 줄과 프로젝트 선택 줄을 나눈다 — 한 줄에 두면 이름이 「A…」로 잘린다
  return (
    <header className="shrink-0 border-b border-line bg-surface">
      <div className="flex h-14 items-center gap-3 px-3 md:h-16 md:px-5">
        {/* lg 이상에서는 왼쪽 사이드바 폭(260px) − 헤더 여백 20px − 간격 12px만큼 채워 프로젝트 선택의 왼쪽 끝이 사이드바 경계선(가운데 화면의 모서리)에 맞는다 */}
        <div className="flex items-center gap-3 lg:w-[228px] lg:shrink-0">
          <IconButton icon={Menu} label="메뉴 열기" onClick={onOpenLeft} className="lg:hidden" />
          <BrandLogo onHome={() => setView("home")} />
        </div>
        <div className="ml-3 hidden min-w-0 flex-none basis-[326px] md:block lg:ml-0">
          <ProjectSelector />
        </div>

        {/* 누르면 대화창으로 — 진행 상황은 대화에서 본다 */}
        {workspace ? (
          <button
            type="button"
            onClick={() => setView("chat")}
            title="대화창으로 이동"
            className="mx-auto hidden w-full max-w-sm items-center gap-3 rounded-lg px-2 py-1 text-left transition-colors hover:bg-fill-alt md:flex"
          >
            <span className="shrink-0 text-xs text-label-alternative">전체 진행률</span>
            <ProgressBar value={progress} label="전체 진행률" />
            <span className="w-10 shrink-0 text-right text-sm font-semibold text-label">{progress}%</span>
          </button>
        ) : (
          <div className="mx-auto hidden w-full max-w-sm md:block" aria-hidden />
        )}
        {workspace && (
          <span className="shrink-0">
            <RunStatusBadge status={workspace.runStatus} />
          </span>
        )}

        <div className="ml-auto flex shrink-0 items-center gap-1 md:ml-0">
          <IconButton
            icon={rightCollapsed ? PanelRightOpen : PanelRightClose}
            label={rightCollapsed ? "작업물 패널 펴기" : "작업물 패널 접기"}
            onClick={onToggleRight}
            disabled={!workspace}
          />
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
