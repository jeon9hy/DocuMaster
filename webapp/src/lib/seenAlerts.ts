/**
 * 알림을 어디까지 읽었는지(프로젝트별 마지막으로 본 알림 시각). 이 브라우저에만 남기는 편의 기능이라
 * localStorage에 두고, 읽기·쓰기가 막힌 환경(사생활 모드 등)에서는 조용히 넘어간다.
 */
const KEY = "documaster.seenAlerts";
const listeners = new Set<() => void>();

export function subscribeSeenAlerts(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** useSyncExternalStore용 스냅샷 — 문자열이라 값이 같으면 다시 그리지 않는다 */
export function readSeenAlertsRaw(): string {
  try {
    return window.localStorage.getItem(KEY) ?? "{}";
  } catch {
    return "{}";
  }
}

export function seenAtFor(raw: string, projectId: string): string {
  try {
    const value = (JSON.parse(raw) as Record<string, unknown>)[projectId];
    return typeof value === "string" ? value : "";
  } catch {
    return "";
  }
}

export function markAlertsSeen(projectId: string, seenAt: string): void {
  try {
    const current = JSON.parse(readSeenAlertsRaw()) as Record<string, string>;
    if ((current[projectId] ?? "") >= seenAt) return;
    window.localStorage.setItem(KEY, JSON.stringify({ ...current, [projectId]: seenAt }));
  } catch {
    return;
  }
  listeners.forEach((listener) => listener());
}
