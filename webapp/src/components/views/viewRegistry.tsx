import type { ComponentType } from "react";
import type { ViewId } from "@/constants/navigation";
import { ArtifactsView } from "./ArtifactsView";
import { ChatView } from "./ChatView";
import { DashboardView } from "./DashboardView";
import { PlaceholderView } from "./PlaceholderView";
import { ProjectsView } from "./ProjectsView";
import { SettingsView } from "./SettingsView";
import { AgentsView, MembersView } from "./TeamView";

/** 메뉴 → 화면 연결표. 새 화면은 constants/navigation.ts에 메뉴를 추가하고 여기에 한 줄 더한다. */
export const VIEWS: Record<ViewId, ComponentType> = {
  chat: ChatView,
  dashboard: DashboardView,
  artifacts: ArtifactsView,
  members: MembersView,
  projects: ProjectsView,
  agents: AgentsView,
  settings: SettingsView,
  home: () => (
    <PlaceholderView title="홈" description="모든 프로젝트의 최근 활동과 알림을 모아 보여 줄 자리입니다." />
  ),
  library: () => (
    <PlaceholderView
      title="지식 라이브러리"
      description="여러 프로젝트에서 다시 쓸 레퍼런스와 검증된 근거를 보관할 자리입니다."
    />
  ),
  projectSettings: () => (
    <PlaceholderView
      title="프로젝트 설정"
      description="독자·분량·형식과 기획 개정 번호(r1→r2)를 관리할 자리입니다."
    />
  ),
};
