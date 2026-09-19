import { useEffect, type RefObject } from "react";

/**
 * 열린 팝업을 닫는 공통 규칙: Esc 키, 그리고 ref가 있으면 바깥 클릭.
 * 드롭다운·모달·드로어가 같이 쓴다.
 */
export function useDismiss(
  open: boolean,
  onDismiss: () => void,
  ref?: RefObject<HTMLElement | null>,
) {
  useEffect(() => {
    if (!open) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onDismiss();
    };
    const onPointerDown = (event: PointerEvent) => {
      if (ref?.current && !ref.current.contains(event.target as Node)) onDismiss();
    };

    document.addEventListener("keydown", onKeyDown);
    if (ref) document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [open, onDismiss, ref]);
}
