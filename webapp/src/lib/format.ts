const timeFormatter = new Intl.DateTimeFormat("ko-KR", {
  hour: "numeric",
  minute: "2-digit",
});

const dateFormatter = new Intl.DateTimeFormat("ko-KR", {
  month: "long",
  day: "numeric",
});

const dateTimeFormatter = new Intl.DateTimeFormat("ko-KR", {
  month: "numeric",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

/** "9. 19. 오후 9:30" */
export function formatDateTime(iso: string): string {
  return dateTimeFormatter.format(new Date(iso));
}

/** "방금" · "12분 전" · "3시간 전" · "2일 전" */
export function formatRelative(iso: string, now: Date = new Date()): string {
  const minutes = Math.floor((now.getTime() - new Date(iso).getTime()) / 60_000);
  if (minutes < 1) return "방금";
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  return `${Math.floor(hours / 24)}일 전`;
}

const clockFormatter = new Intl.DateTimeFormat("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false });

/**
 * 리셋·재개 시각을 짧게. 오늘이면 "19:18", 다른 날이면 "9/26 10:07". date는 "9/26".
 * 브라우저의 시간대로 보여 준다(시간대를 코드에 박지 않는다).
 */
export function formatResetShort(iso: string, now: Date = new Date()): { label: string; date: string } {
  const at = new Date(iso);
  const time = clockFormatter.format(at);
  const date = `${at.getMonth() + 1}/${at.getDate()}`;
  const sameDay = at.toDateString() === now.toDateString();
  return { label: sameDay ? time : `${date} ${time}`, date };
}

/** "오전 10:14" */
export function formatTime(iso: string): string {
  return timeFormatter.format(new Date(iso));
}

/** "오늘" · "어제" · "9월 17일" */
export function formatDay(iso: string, now: Date = new Date()): string {
  const date = new Date(iso);
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const dayMs = 24 * 60 * 60 * 1000;
  if (date.getTime() >= startOfToday) return "오늘";
  if (date.getTime() >= startOfToday - dayMs) return "어제";
  return dateFormatter.format(date);
}

/** 1536 → "1.5KB" */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(1)}${units[unit]}`;
}
