import { useCallback, useEffect, useState } from "react";

export type ServiceData<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: T };

/**
 * 워크스페이스 이벤트와 무관한 조회(설정·사용량·도구 상태)를 화면에 붙인다.
 * 화면이 열릴 때 한 번 받고, reload로 다시 받는다. 값을 바꾼 응답은 set으로 바로 반영한다.
 */
export function useServiceData<T>(load: () => Promise<T>) {
  const [state, setState] = useState<ServiceData<T>>({ status: "loading" });
  const [token, setToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    load()
      .then((data) => !cancelled && setState({ status: "success", data }))
      .catch(
        (error: unknown) =>
          !cancelled &&
          setState({ status: "error", message: error instanceof Error ? error.message : "불러오지 못했습니다." }),
      );
    return () => {
      cancelled = true;
    };
  }, [load, token]);

  const reload = useCallback(() => setToken((value) => value + 1), []);
  const set = useCallback((data: T) => setState({ status: "success", data }), []);
  return { state, reload, set };
}
