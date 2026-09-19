import { GLOBAL_NAV, PROJECT_NAV, type ViewId } from "@/constants/navigation";

/**
 * 지금 보는 화면과 프로젝트를 주소(?project=…&view=…)에 남긴다.
 * 새로고침해도 같은 화면으로 돌아오고, 주소를 복사하면 같은 화면이 열린다.
 */
const VIEW_IDS = new Set<string>([...GLOBAL_NAV, ...PROJECT_NAV].map((item) => item.id));

export interface UrlState {
  view?: ViewId;
  projectId?: string;
}

export function readUrlState(): UrlState {
  if (typeof window === "undefined") return {};
  const params = new URLSearchParams(window.location.search);
  const view = params.get("view");
  return {
    view: view && VIEW_IDS.has(view) ? (view as ViewId) : undefined,
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
