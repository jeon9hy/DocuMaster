import type { ViewId } from "@/constants/navigation";

/**
 * 지금 보는 화면과 프로젝트를 주소(?project=…&view=…)에 남긴다.
 * 다시 열 때는 프로젝트만 이어받고, 화면은 항상 홈에서 시작한다(DEFAULT_VIEW).
 */
export interface UrlState {
  projectId?: string;
}

export function readUrlState(): UrlState {
  if (typeof window === "undefined") return {};
  const params = new URLSearchParams(window.location.search);
  return { projectId: params.get("project") ?? undefined };
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
