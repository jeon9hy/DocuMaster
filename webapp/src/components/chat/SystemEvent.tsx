import { AlertTriangle, CheckCircle2, Info, XCircle, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import { formatTime } from "@/lib/format";
import type { AgentId, SystemTone } from "@/types";
import { AgentAvatar } from "../agent/AgentAvatar";

const TONE: Record<SystemTone, { icon: LucideIcon; className: string }> = {
  info: { icon: Info, className: "text-label-assistive" },
  success: { icon: CheckCircle2, className: "text-positive-fg" },
  warning: { icon: AlertTriangle, className: "text-caution-fg" },
  error: { icon: XCircle, className: "text-negative-fg" },
};

interface SystemEventProps {
  tone: SystemTone;
  title: string;
  detail?: string;
  agentId?: AgentId;
  createdAt: string;
  /** compact = 에이전트 작업 시작처럼 가벼운 알림 — 상자 없이 아바타 옆 작은 글씨 */
  compact?: boolean;
}

/** 코드가 만든 진행 알림. 말풍선이 아니라 한 줄짜리 기록으로 보여 대화와 구분한다. */
export function SystemEvent({ tone, title, detail, agentId, createdAt, compact = false }: SystemEventProps) {
  const { icon: Icon, className } = TONE[tone];
  if (compact) {
    return (
      <p className="ml-[52px] flex items-center gap-1.5 px-1.5 text-xs text-label-alternative">
        {agentId ? <AgentAvatar agentId={agentId} size="xs" /> : <Icon className={cn("size-3.5", className)} aria-hidden />}
        <span className="min-w-0 truncate">{title}</span>
        <time className="shrink-0 text-label-alternative" dateTime={createdAt}>
          {formatTime(createdAt)}
        </time>
      </p>
    );
  }
  return (
    <div
      className={cn(
        "ml-[52px] flex items-center gap-2.5 rounded-lg border px-3 py-2",
        tone === "warning" ? "border-caution/28 bg-caution/4" : "border-line bg-surface",
        tone === "error" && "border-negative/28 bg-negative/4",
      )}
    >
      {agentId ? (
        <AgentAvatar agentId={agentId} size="xs" />
      ) : (
        <Icon className={cn("size-4 shrink-0", className)} aria-hidden />
      )}
      <p className="min-w-0 flex-1 text-[13px] text-label-neutral">
        <span className="font-medium">{title}</span>
        {detail && <span className="text-label-alternative"> · {detail}</span>}
      </p>
      <span className="shrink-0 text-[11px] text-label-alternative">
        시스템 · {formatTime(createdAt)}
      </span>
    </div>
  );
}
