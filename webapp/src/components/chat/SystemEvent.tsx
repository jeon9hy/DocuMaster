import { AlertTriangle, CheckCircle2, Info, XCircle, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import { formatTime } from "@/lib/format";
import type { AgentId, SystemTone } from "@/types";
import { AgentAvatar } from "../agent/AgentAvatar";

const TONE: Record<SystemTone, { icon: LucideIcon; className: string }> = {
  info: { icon: Info, className: "text-gray-400" },
  success: { icon: CheckCircle2, className: "text-emerald-500" },
  warning: { icon: AlertTriangle, className: "text-amber-500" },
  error: { icon: XCircle, className: "text-red-500" },
};

interface SystemEventProps {
  tone: SystemTone;
  title: string;
  detail?: string;
  agentId?: AgentId;
  createdAt: string;
}

/** 코드가 만든 진행 알림. 말풍선이 아니라 한 줄짜리 기록으로 보여 대화와 구분한다. */
export function SystemEvent({ tone, title, detail, agentId, createdAt }: SystemEventProps) {
  const { icon: Icon, className } = TONE[tone];
  return (
    <div
      className={cn(
        "ml-[52px] flex items-center gap-2.5 rounded-lg border px-3 py-2",
        tone === "warning" ? "border-amber-200 bg-amber-50/60" : "border-line bg-white",
        tone === "error" && "border-red-200 bg-red-50/60",
      )}
    >
      {agentId ? (
        <AgentAvatar agentId={agentId} size="xs" />
      ) : (
        <Icon className={cn("size-4 shrink-0", className)} aria-hidden />
      )}
      <p className="min-w-0 flex-1 text-[13px] text-gray-700">
        <span className="font-medium">{title}</span>
        {detail && <span className="text-gray-500"> · {detail}</span>}
      </p>
      <span className="shrink-0 text-[11px] text-gray-400">
        시스템 · {formatTime(createdAt)}
      </span>
    </div>
  );
}
