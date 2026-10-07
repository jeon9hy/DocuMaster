import { useEffect } from "react";

/** 마우스가 올라간 곳에서 위로 몇 단계까지 잘린 글을 찾을지(말줄임 칸은 보통 바로 위 부모다) */
const MAX_DEPTH = 4;

function isTruncated(element: HTMLElement): boolean {
  const style = window.getComputedStyle(element);
  if (style.textOverflow === "ellipsis" && element.scrollWidth > element.clientWidth + 1) return true;
  // line-clamp(여러 줄 줄임)
  const clamp = style.getPropertyValue("-webkit-line-clamp");
  return clamp !== "" && clamp !== "none" && element.scrollHeight > element.clientHeight + 1;
}

/**
 * 「…」로 줄어든 글은 마우스를 올리면 전체가 말풍선(title)으로 보이게 한다.
 * 화면마다 title을 달지 않아도 되고, 팝업·메뉴 안의 글도 같이 된다. 이미 title이 있는 곳은 건드리지 않는다.
 * 잘리지 않은 글에는 달지 않는다(글이 늘어나 잘리게 되면 그때 올려 본 순간 달린다).
 */
export function useTruncationTitles() {
  useEffect(() => {
    const onOver = (event: MouseEvent) => {
      let element = event.target instanceof HTMLElement ? event.target : null;
      for (let depth = 0; element && depth < MAX_DEPTH; depth += 1, element = element.parentElement) {
        if (element.title || element.tagName === "BODY") continue;
        const text = element.textContent?.trim();
        if (text && isTruncated(element)) {
          element.title = text;
          return;
        }
      }
    };
    document.addEventListener("mouseover", onOver);
    return () => document.removeEventListener("mouseover", onOver);
  }, []);
}
