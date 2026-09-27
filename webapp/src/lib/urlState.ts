import { GLOBAL_NAV, PROJECT_NAV, type ViewId } from "@/constants/navigation";

/**
 * 지금 보는 화면과 프로젝트를 주소(?project=…&view=…)에 남긴다.
 * 새로고침이면 보던 화면 그대로, 처음 열 때(서버를 켜고 연 창·새 탭)는 홈에서 시작한다(DEFAULT_VIEW).
 * 프로젝트는 어느 쪽이든 이어받는다.
 */
const VIEW_IDS = new Set<string>([...GLOBAL_NAV, ...PROJECT_NAV].map((item) => item.id));

export interface UrlState {
  /** 새로고침일 때만 채운다 */
  view?: ViewId;
  projectId?: string;
}

function isReload(): boolean {
  const entry = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
  return entry?.type === "reload";
}

export function readUrlState(): UrlState {
  if (typeof window === "undefined") return {};
  const params = new URLSearchParams(window.location.search);
  const view = params.get("view");
  return {
    view: isReload() && view && VIEW_IDS.has(view) ? (view as ViewId) : undefined,
    projectId: params.get("project") ?? undefined,
  };
}

export function writeUrlState(view: ViewId, projectId: string | null): void {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  params.set("view", view);
  if (projectId) params.set("project", projectId);
  else params.delete("project");
  const next = `${window.location.pathname}?${params.toString()}${window.location.hash}`;
  if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
    window.history.replaceState(window.history.state, "", next);
  }
}
