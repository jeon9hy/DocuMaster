"use client";

import { useCallback, useState, type ReactElement, type ReactNode } from "react";
import type { MobileTab } from "@/constants/navigation";
import { cn } from "@/lib/cn";
import { useAppActions, useAppState, useIsOwner, useWorkspace } from "@/state/WorkspaceProvider";
import { FolderPlus, Plus } from "lucide-react";
import { AddReferenceButton } from "../reference/AddReferenceButton";
import { ReferenceList } from "../reference/ReferenceList";
import { Button } from "../ui/Button";
import { Drawer } from "../ui/Drawer";
import { Panel } from "../ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "../ui/States";
import { ArtifactsView } from "../views/ArtifactsView";
import { ProgressPanel } from "../views/ChatView";
import { GLOBAL_VIEWS, VIEWS } from "../views/viewRegistry";
import { LeftSidebar } from "./LeftSidebar";
import { MobileTabBar } from "./MobileTabBar";
import { RightSidebar } from "./RightSidebar";
import { TopHeader } from "./TopHeader";

function MobileReferencesPanel() {
  const workspace = useWorkspace();
  const canEdit = useIsOwner() && !workspace.project.readOnly;
  return (
    <div className="min-h-0 flex-1 overflow-y-auto p-3">
      <Panel
        title={`레퍼런스 (${workspace.references.length})`}
        action={
          canEdit && (
          <AddReferenceButton>
            {(open) => (
              <Button size="sm" variant="ghost" icon={Plus} onClick={open} className="h-7 text-blue-600">
                추가
              </Button>
            )}
          </AddReferenceButton>
          )
        }
      >
        <ReferenceList references={workspace.references} />
      </Panel>
    </div>
  );
}

/** 모바일 하단 탭 중 「대화」가 아닌 탭의 내용 */
const MOBILE_PANELS: Record<Exclude<MobileTab, "chat">, () => ReactElement> = {
  progress: ProgressPanel,
  references: MobileReferencesPanel,
  artifacts: ArtifactsView,
};

/**
 * 화면 뼈대. 넓은 화면은 3열, 좁아지면 오른쪽 → 왼쪽 순으로 접어 서랍(Drawer)으로 연다.
 * - xl 이상: 왼쪽 · 가운데 · 오른쪽
 * - lg: 왼쪽 · 가운데 (오른쪽은 헤더 버튼으로)
 * - lg 미만: 가운데만 (양쪽 모두 서랍), md 미만은 하단 탭
 */
export function AppShell() {
  const { workspace, workspaceStatus, view, projectId, projectsLoaded } = useAppState();
  const { reloadWorkspace, setView } = useAppActions();
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);
  const [mobileTab, setMobileTab] = useState<MobileTab>("chat");

  const openLeft = useCallback(() => setLeftOpen(true), []);
  const closeLeft = useCallback(() => setLeftOpen(false), []);
  const openRight = useCallback(() => setRightOpen(true), []);
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
    main = (
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
      <TopHeader onOpenLeft={openLeft} onOpenRight={openRight} />
      <div className="flex min-h-0 flex-1">
        <aside className="scrollbar-thin hidden w-[260px] shrink-0 overflow-y-auto border-r border-line bg-canvas lg:block">
          <LeftSidebar />
        </aside>
        <main className="flex min-w-0 flex-1 flex-col bg-white">{main}</main>
        {workspace && (
          <aside className="scrollbar-thin hidden w-[340px] shrink-0 overflow-y-auto border-l border-line bg-canvas xl:block">
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
