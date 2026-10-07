import { useCallback, useSyncExternalStore } from "react";

const listeners = new Set<() => void>();

/** 브라우저에 기억하는 켜기/끄기 값. 서버 렌더링과 저장소를 못 쓸 때는 false. 탭끼리·컴포넌트끼리 같이 바뀐다. */
export function useStoredFlag(key: string): [boolean, (next: boolean) => void] {
  const subscribe = useCallback((notify: () => void) => {
    listeners.add(notify);
    window.addEventListener("storage", notify);
    return () => {
      listeners.delete(notify);
      window.removeEventListener("storage", notify);
    };
  }, []);
  const read = useCallback(() => {
    try {
      return window.localStorage.getItem(key) === "1";
    } catch {
      return false;
    }
  }, [key]);
  const value = useSyncExternalStore(subscribe, read, () => false);

  const set = useCallback(
    (next: boolean) => {
      try {
        window.localStorage.setItem(key, next ? "1" : "0");
      } catch {
        /* 기억하지 못해도 이번 화면에서는 바뀐다 */
      }
      listeners.forEach((notify) => notify());
    },
    [key],
  );
  return [value, set];
}
