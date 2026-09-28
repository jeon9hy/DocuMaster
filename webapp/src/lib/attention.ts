/**
 * 브라우저 알림(Notification API). 권한은 사용자가 「워크플로우 실행」을 누를 때 한 번 묻는다
 * (브라우저가 클릭 없이 묻는 것을 막는다). 거절·미지원이면 아무것도 하지 않는다 — 탭 제목 표시는 따로 동작한다.
 */
export function requestNotificationPermission(): void {
  try {
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      void Notification.requestPermission();
    }
  } catch {
    // 지원하지 않는 브라우저
  }
}

/** 탭을 보고 있지 않을 때만 띄운다. 같은 tag는 한 번만 보인다. */
export function notify(title: string, body: string, tag: string): void {
  try {
    if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
    if (document.visibilityState === "visible" && document.hasFocus()) return;
    const notification = new Notification(title, { body, tag });
    notification.onclick = () => {
      window.focus();
      notification.close();
    };
  } catch {
    // 알림을 못 띄워도 화면 동작에는 영향 없음
  }
}

/** 탭 제목 앞 표시. 사용자 확인이 필요하면 ●를 붙인다. */
export function attentionTitle(base: string, needsInput: boolean): string {
  return needsInput ? `● 확인 필요 · ${base}` : base;
}
