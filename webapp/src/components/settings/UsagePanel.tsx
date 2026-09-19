"use client";

import { Gauge, RefreshCw } from "lucide-react";
import { useServiceData } from "@/hooks/useServiceData";
import { formatDateTime } from "@/lib/format";
import { workspaceService } from "@/services";
import type { ProviderUsage } from "@/types";
import { Badge } from "../ui/Badge";
import { IconButton } from "../ui/Button";
import { Panel } from "../ui/Panel";
import { ErrorState, LoadingState } from "../ui/States";
import { isExhausted, UsageTiles } from "./UsageTiles";

export const loadUsage = () => workspaceService.getUsage();

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
        <p className="min-w-0 flex-1 truncate text-sm font-semibold text-gray-900">{usage.label}</p>
        <StatusBadgeFor usage={usage} />
      </div>
      <UsageTiles usage={usage} showBar />
      <p className="mt-2 text-[11px] leading-relaxed text-gray-400">
        {usage.available && usage.observedAt && `기준 ${formatDateTime(usage.observedAt)} · `}
        {usage.available && usage.source && `${usage.source} · `}
        {usage.note}
      </p>
    </li>
  );
}

/** 사용량: 실제로 확인되는 값만 보여 준다. 확인할 수 없으면 「확인 불가」와 이유. */
export function UsagePanel() {
  const { state, reload } = useServiceData(loadUsage);
  return (
    <Panel
      title={
        <span className="flex items-center gap-1.5">
          <Gauge className="size-4 text-gray-400" aria-hidden />
          사용량
        </span>
      }
      action={<IconButton icon={RefreshCw} label="사용량 다시 확인" className="size-7" onClick={reload} />}
    >
      {state.status === "loading" && <LoadingState />}
      {state.status === "error" && <ErrorState message={state.message} onRetry={reload} className="py-6" />}
      {state.status === "success" && (
        <ul className="divide-y divide-gray-100">
          {state.data.map((usage) => (
            <ProviderUsageRow key={usage.provider} usage={usage} />
          ))}
        </ul>
      )}
    </Panel>
  );
}
