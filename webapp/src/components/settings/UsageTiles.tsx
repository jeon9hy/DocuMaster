import { cn } from "@/lib/cn";
import { formatResetShort } from "@/lib/format";
import type { ProviderUsage, UsageWindow } from "@/types";
import { ProgressBar } from "../ui/ProgressBar";

/** 창 길이 → 이름. 모르는 길이는 그대로 적는다(추측하지 않는다). */
export function windowName(window: UsageWindow): string {
  if (window.windowMinutes === 300) return "현재";
  if (window.windowMinutes === 10080) return "주간";
  if (window.windowMinutes) return `${Math.round(window.windowMinutes / 60)}시간`;
  return window.kind;
}

/** 한도를 다 쓴 창인지(사용 100%) */
export function isExhausted(window: UsageWindow): boolean {
  return window.usedPercent >= 100;
}

/**
 * 한 창의 사용량 타일. 제목에 리셋 시각을 붙인다: 「현재 · 9/28 02:22 리셋」 · 「주간 · 10/1 리셋」.
 * 다 썼으면 값 자리에 「19:18 재개」, 리셋이 지난 값은 흐리게 「리셋됨」.
 * showBar면 제목 줄 아래에 굵은 막대만 둔다(설정 화면). 설명 문구는 두지 않는다.
 */
export function UsageTile({ window, showBar = false }: { window: UsageWindow; showBar?: boolean }) {
  const exhausted = isExhausted(window) && !window.expired;
  const weekly = window.windowMinutes === 10080;
  const reset = window.resetsAt ? formatResetShort(window.resetsAt) : null;
  const resetAt = reset && (weekly ? reset.date : `${reset.date} ${reset.time}`);
  const title = resetAt && !exhausted && !window.expired ? `${windowName(window)} · ${resetAt} 리셋` : windowName(window);
  let value: string;
  if (window.expired) value = "리셋됨";
  else if (exhausted && reset) value = `${reset.label} 재개`;
  else value = `${Math.round(window.usedPercent)}%`;

  return (
    <div
      className={cn(
        "rounded-lg border px-3 py-2",
        exhausted ? "border-red-200 bg-red-50/60" : "border-line bg-gray-50/60",
        window.expired && "opacity-60",
      )}
      title={window.resetsAt ? `리셋 ${new Date(window.resetsAt).toLocaleString("ko-KR")}` : undefined}
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="truncate text-xs whitespace-nowrap text-gray-500">{title}</span>
        <span className={cn("shrink-0 text-sm font-semibold whitespace-nowrap", exhausted ? "text-red-600" : "text-gray-900")}>
          {value}
        </span>
      </div>
      {showBar && !window.expired && (
        <ProgressBar value={window.usedPercent} label={`${title} 사용량`} size="thick" className="mt-2.5 mb-1" />
      )}
    </div>
  );
}

/** 공급자의 창들을 나란히(5시간 | 주간). 사용량이 없으면 아무것도 그리지 않는다. */
export function UsageTiles({ usage, showBar = false }: { usage: ProviderUsage | undefined; showBar?: boolean }) {
  if (!usage?.available || usage.windows.length === 0) return null;
  return (
    <div className="grid gap-2 @md:grid-cols-2">
      {usage.windows.map((window) => (
        <UsageTile key={window.kind} window={window} showBar={showBar} />
      ))}
    </div>
  );
}
