import {
  BookOpen,
  Bot,
  Folder,
  FolderCog,
  Home,
  LayoutDashboard,
  MessagesSquare,
  FileText,
  Settings,
  Users,
  type LucideIcon,
} from "lucide-react";

export type ViewId =
  | "home"
  | "projects"
  | "agents"
  | "library"
  | "settings"
  | "dashboard"
  | "chat"
  | "artifacts"
  | "members"
  | "projectSettings";

export interface NavItem {
  id: ViewId;
  label: string;
  icon: LucideIcon;
}

export const GLOBAL_NAV: readonly NavItem[] = [
  { id: "home", label: "홈", icon: Home },
  { id: "projects", label: "프로젝트", icon: Folder },
  { id: "agents", label: "에이전트", icon: Bot },
  { id: "library", label: "지식 라이브러리", icon: BookOpen },
  { id: "settings", label: "설정", icon: Settings },
];

export const PROJECT_NAV: readonly NavItem[] = [
  { id: "dashboard", label: "대시보드", icon: LayoutDashboard },
  { id: "chat", label: "대화", icon: MessagesSquare },
  { id: "artifacts", label: "작업물", icon: FileText },
  { id: "members", label: "멤버", icon: Users },
  { id: "projectSettings", label: "프로젝트 설정", icon: FolderCog },
];

export const DEFAULT_VIEW: ViewId = "chat";

/** 모바일 하단 탭. 한 번에 한 패널만 보여 준다. */
export type MobileTab = "chat" | "progress" | "references" | "artifacts";

export const MOBILE_TABS: readonly { id: MobileTab; label: string }[] = [
  { id: "chat", label: "대화" },
  { id: "progress", label: "진행" },
  { id: "references", label: "레퍼런스" },
  { id: "artifacts", label: "작업물" },
];

export const PROJECT_MODE_LABEL = {
  document: "문서",
  presentation: "발표",
} as const;
