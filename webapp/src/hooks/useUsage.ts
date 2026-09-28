import { useEffect, useSyncExternalStore } from "react";
import { serviceKind, workspaceService } from "@/services";
import type { ProviderUsage } from "@/types";

/**
 * 사용량: 마지막으로 받은 값을 먼저 보여 주고(흐리게), 새 값이 오면 바꾼다.
 * 설정 화면의 여러 곳이 같은 값을 쓰므로 요청은 한 번만 보낸다(진행 중이면 그 요청을 같이 기다린다).
 * 마지막 값은 브라우저에만 둔다 — 없거나 못 읽어도 처음 받을 때까지 로딩으로 보일 뿐이다.
 */
export interface UsageSnapshot {
  data: ProviderUsage[] | null;
  /** data를 받은 시각(ISO) */
  receivedAt: string | null;
  refreshing: boolean;
  error: string | null;
}

const STORAGE_KEY = `documaster.usage.last.${serviceKind}`;
const SERVER_SNAPSHOT: UsageSnapshot = { data: null, receivedAt: null, refreshing: true, error: null };

let snapshot: UsageSnapshot = SERVER_SNAPSHOT;
let hydrated = false;
let inflight: Promise<void> | null = null;
const listeners = new Set<() => void>();

function update(next: Partial<UsageSnapshot>) {
  snapshot = { ...snapshot, ...next };
  listeners.forEach((listener) => listener());
}

function hydrateFromStorage() {
  if (hydrated) return;
  hydrated = true;
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null") as Pick<UsageSnapshot, "data" | "receivedAt"> | null;
    if (saved && Array.isArray(saved.data)) snapshot = { ...snapshot, data: saved.data, receivedAt: saved.receivedAt };
  } catch {
    // 저장소를 못 쓰면 이전 값 없이 시작한다
  }
}

export function refreshUsage(): Promise<void> {
  if (inflight) return inflight;
  hydrateFromStorage();
  update({ refreshing: true, error: null });
  inflight = workspaceService
    .getUsage()
    .then((data) => {
      const receivedAt = new Date().toISOString();
      update({ data, receivedAt, refreshing: false });
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ data, receivedAt }));
      } catch {
        // 저장 못 해도 화면에는 영향 없음
      }
    })
    .catch((error: unknown) =>
      update({ refreshing: false, error: error instanceof Error ? error.message : "불러오지 못했습니다." }),
    )
    .finally(() => {
      inflight = null;
    });
  return inflight;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** 화면이 열릴 때 새 값을 요청한다. 그동안은 마지막 값(있으면)을 돌려준다. */
export function useUsage() {
  const state = useSyncExternalStore(
    subscribe,
    () => snapshot,
    () => SERVER_SNAPSHOT,
  );
  useEffect(() => {
    void refreshUsage();
  }, []);
  return { ...state, reload: refreshUsage };
}
