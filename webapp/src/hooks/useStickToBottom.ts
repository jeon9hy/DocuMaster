import { useCallback, useEffect, useRef, useState } from "react";

/** 바닥에서 이만큼(px) 안쪽이면 "바닥을 보고 있다"로 친다 */
const THRESHOLD = 80;

/**
 * 새 항목이 오면 맨 아래로 스크롤한다. 단, 사용자가 위로 올려 예전 기록을 읽는 중이면 건드리지 않는다.
 * `trigger`는 항목 수처럼 "새 내용이 생겼음"을 나타내는 값.
 * `atBottom`이 false면 화면에 「아래로」 버튼을 띄우고, 누르면 `scrollToBottom`을 부른다.
 */
export function useStickToBottom<T extends HTMLElement>(trigger: unknown) {
  const ref = useRef<T>(null);
  const pinned = useRef(true);
  const [atBottom, setAtBottom] = useState(true);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const onScroll = () => {
      pinned.current =
        element.scrollHeight - element.scrollTop - element.clientHeight < THRESHOLD;
      setAtBottom(pinned.current);
    };
    element.addEventListener("scroll", onScroll, { passive: true });
    return () => element.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const element = ref.current;
    if (element && pinned.current) element.scrollTop = element.scrollHeight;
  }, [trigger]);

  const scrollToBottom = useCallback(() => {
    const element = ref.current;
    if (!element) return;
    pinned.current = true;
    setAtBottom(true);
    element.scrollTo({ top: element.scrollHeight, behavior: "smooth" });
  }, []);

  return { ref, atBottom, scrollToBottom };
}
