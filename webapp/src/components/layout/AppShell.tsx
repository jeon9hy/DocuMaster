"use client";

import { useCallback, useState, type ReactElement, type ReactNode } from "react";
import type { MobileTab } from "@/constants/navigation";
import { useAttentionSignals } from "@/hooks/useAttentionSignals";
import { useStoredFlag } from "@/hooks/useStoredFlag";
import { useTruncationTitles } from "@/hooks/useTruncationTitles";
import { cn } from "@/lib/cn";
import { useAppActions, useAppState } from "@/state/WorkspaceProvider";
import { FolderPlus } from "lucide-react";
import { Drawer } from "../ui/Drawer";
import { EmptyState, ErrorState, LoadingState } from "../ui/States";
import { ArtifactsView } from "../views/ArtifactsView";
import { ReferencesView } from "../views/ReferencesView";
import { ProgressPanel } from "../views/ChatView";
import { GLOBAL_VIEWS, VIEWS } from "../views/viewRegistry";
import { LeftSidebar } from "./LeftSidebar";
import { MobileTabBar } from "./MobileTabBar";
import { RightSidebar } from "./RightSidebar";
import { TopHeader } from "./TopHeader";

/** 모바일 하단 탭 중 「대화」가 아닌 탭의 내용 */
const RIGHT_COLLAPSED_KEY = "documaster.rightPanelCollapsed";

const MOBILE_PANELS: Record<Exclude<MobileTab, "chat">, () => ReactElement> = {
  progress: ProgressPanel,
  references: ReferencesView,
  artifacts: ArtifactsView,
};

/**
 * 화면 뼈대. 넓은 화면은 3열, 좁아지면 오른쪽 → 왼쪽 순으로 접어 서랍(Drawer)으로 연다.
 * - xl 이상: 왼쪽 · 가운데 · 오른쪽
 * - lg: 왼쪽 · 가운데 (오른쪽은 헤더 버튼으로)
 * - lg 미만: 가운데만 (양쪽 모두 서랍), md 미만은 하단 탭
 */
export function AppShell() {
  const { workspace, workspaceStatus, view, projectId, projects, projectsLoaded } = useAppState();
  const { reloadWorkspace, setView } = useAppActions();
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);
  // xl 이상에서 오른쪽 작업물 패널을 접어 둔 상태(브라우저에 기억). 좁은 화면에서는 서랍이라 쓰지 않는다
  const [rightCollapsed, setRightCollapsed] = useStoredFlag(RIGHT_COLLAPSED_KEY);
  const [mobileTab, setMobileTab] = useState<MobileTab>("chat");
  useAttentionSignals(workspace);
  useTruncationTitles();

  const openLeft = useCallback(() => setLeftOpen(true), []);
  const closeLeft = useCallback(() => setLeftOpen(false), []);
  const toggleRight = useCallback(() => {
    if (window.matchMedia("(min-width: 1280px)").matches) setRightCollapsed(!rightCollapsed);
    else setRightOpen(true);
  }, [rightCollapsed, setRightCollapsed]);
  const closeRight = useCallback(() => setRightOpen(false), []);

  const changeMobileTab = (tab: MobileTab) => {
    setMobileTab(tab);
    if (tab === "chat") setView("chat");
  };
  const navigateFromDrawer = () => {
    closeLeft();
    setMobileTab("chat");
  };

  const View = VIEWS[view];
  const MobilePanel = mobileTab === "chat" ? null : MOBILE_PANELS[mobileTab];

  let main: ReactNode;
  if (GLOBAL_VIEWS.has(view)) {
    // 홈·프로젝트·에이전트·설정은 프로젝트와 상관없이 보인다
    main = <View />;
  } else if (projectsLoaded && !projectId) {
    main =
      projects.length > 0 ? (
        <EmptyState
          icon={FolderPlus}
          title="프로젝트를 선택하세요"
          description="위쪽 프로젝트 선택에서 열거나, 프로젝트 화면에서 찾아 열 수 있습니다."
          className="flex-1"
        />
      ) : (
        <EmptyState
          icon={FolderPlus}
          title="프로젝트가 없습니다"
          description="프로젝트 화면에서 새 프로젝트를 만들 수 있습니다(Owner 로그인 필요)."
          className="flex-1"
        />
      );
  } else if (workspaceStatus === "error") {
    main = <ErrorState message="프로젝트를 불러오지 못했습니다." onRetry={reloadWorkspace} className="flex-1" />;
  } else if (!workspace) {
    main = <LoadingState className="flex-1" />;
  } else {
    main = (
      <>
        {MobilePanel && (
          <div className="flex min-h-0 flex-1 flex-col md:hidden">
            <MobilePanel />
          </div>
        )}
        <div className={cn("min-h-0 flex-1 flex-col", MobilePanel ? "hidden md:flex" : "flex")}>
          <View />
        </div>
      </>
    );
  }

  return (
    <div className="flex h-dvh flex-col">
      <TopHeader onOpenLeft={openLeft} onToggleRight={toggleRight} rightCollapsed={rightCollapsed} />
      <div className="flex min-h-0 flex-1">
        <aside className="scrollbar-thin hidden w-[260px] shrink-0 overflow-y-auto border-r border-line bg-surface-alt lg:block">
          <LeftSidebar />
        </aside>
        <main className="flex min-w-0 flex-1 flex-col bg-surface">{main}</main>
        {workspace && (
          <aside
            className={cn(
              "scrollbar-thin hidden w-[340px] shrink-0 overflow-y-auto border-l border-line bg-surface-alt",
              !rightCollapsed && "xl:block",
            )}
          >
            <RightSidebar />
          </aside>
        )}
      </div>
      <MobileTabBar active={mobileTab} onChange={changeMobileTab} />

      <Drawer open={leftOpen} side="left" label="메뉴" onClose={closeLeft}>
        <LeftSidebar onNavigate={navigateFromDrawer} />
      </Drawer>
      {workspace && (
        <Drawer open={rightOpen} side="right" label="작업물 패널" onClose={closeRight}>
          <RightSidebar />
        </Drawer>
      )}
    </div>
  );
}
