"use client";

import { Gauge, Loader2, RefreshCw } from "lucide-react";
import { useUsage } from "@/hooks/useUsage";
import { cn } from "@/lib/cn";
import { formatTime } from "@/lib/format";
import type { ProviderUsage } from "@/types";
import { Badge } from "../ui/Badge";
import { IconButton } from "../ui/Button";
import { Panel } from "../ui/Panel";
import { ErrorState, LoadingState } from "../ui/States";
import { isExhausted, UsageTiles } from "./UsageTiles";

function StatusBadgeFor({ usage }: { usage: ProviderUsage }) {
  if (!usage.available) return <Badge>확인 불가</Badge>;
  if (usage.limitReached || usage.windows.some((window) => isExhausted(window) && !window.expired)) {
    return (
      <Badge variant="danger" dot>
        한도 도달
      </Badge>
    );
  }
  if (usage.stale) {
    return (
      <Badge variant="warning" dot>
        오래됨
      </Badge>
    );
  }
  return (
    <Badge variant="success" dot>
      확인됨
    </Badge>
  );
}

function ProviderUsageRow({ usage }: { usage: ProviderUsage }) {
  return (
    <li className="@container px-2 py-3">
      <div className="mb-2 flex items-center gap-2">
        <p className="min-w-0 flex-1 truncate text-sm font-semibold text-label">{usage.label}</p>
        <StatusBadgeFor usage={usage} />
      </div>
      <UsageTiles usage={usage} showBar />
      {/* 값이 있으면 막대만. 못 읽었을 때만 이유를 적는다 */}
      {!usage.available && <p className="text-[13px] leading-relaxed text-label-alternative">{usage.note}</p>}
    </li>
  );
}

/**
 * 사용량: 실제로 확인되는 값만 보여 준다. 확인할 수 없으면 「확인 불가」와 이유.
 * 마지막으로 받은 값을 흐리게 먼저 보여 주고, 새 값이 오면 바꾼다.
 */
export function UsagePanel() {
  const { data, receivedAt, refreshing, error, reload } = useUsage();
  return (
    <Panel
      title={
        <span className="flex items-center gap-1.5">
          <Gauge className="size-4 text-label-assistive" aria-hidden />
          사용량
          {data && refreshing && (
            <span className="flex items-center gap-1 text-xs font-normal text-label-alternative">
              <Loader2 className="size-3 animate-spin" aria-hidden />
              새 값 확인 중{receivedAt && ` · ${formatTime(receivedAt)} 값`}
            </span>
          )}
        </span>
      }
      action={
        <IconButton icon={RefreshCw} label="사용량 다시 확인" className="size-7" onClick={reload} disabled={refreshing} />
      }
    >
      {!data && refreshing && <LoadingState />}
      {!data && !refreshing && error && <ErrorState message={error} onRetry={reload} className="py-6" />}
      {data && (
        <>
          {error && !refreshing && (
            <p className="mx-2 mb-1 rounded-lg bg-caution/8 px-3 py-2 text-xs text-caution-strong">
              새 값을 받지 못해{receivedAt && ` ${formatTime(receivedAt)}에 받은`} 이전 값을 보여 줍니다. ({error})
            </p>
          )}
          <ul className={cn("divide-y divide-line-alt transition-opacity", refreshing && "opacity-50")} aria-busy={refreshing}>
            {data.map((usage) => (
              <ProviderUsageRow key={usage.provider} usage={usage} />
            ))}
          </ul>
        </>
      )}
    </Panel>
  );
}
