import { getAgentProfile } from "@/constants/agents";
import { AGENT_DISPLAY_STATUS, RESTING_TOOLTIP, type AgentDisplayStatus } from "@/constants/status";
import { cn } from "@/lib/cn";
import type { AgentId } from "@/types";
import { StatusBadge } from "../ui/Badge";
import { AgentAvatar } from "./AgentAvatar";

interface AgentCardProps {
  agentId: AgentId;
  /** 프로젝트 밖(에이전트 화면)에서는 생략 */
  status?: AgentDisplayStatus;
  /** 휴식 중일 때 설명 대신 보여 줄 한 줄 */
  restingNote?: string;
}

/**
 * 멤버·에이전트 화면의 프로필 카드: 누가 무슨 역할을 하는지만 보여 준다(모델은 설정 화면에서).
 * 설명 칸이 남는 높이를 채워, 글 길이가 달라도 상태 배지가 같은 줄에 온다.
 */
export function AgentCard({ agentId, status, restingNote }: AgentCardProps) {
  const profile = getAgentProfile(agentId);
  const resting = status === "resting";
  return (
    <article
      title={resting ? RESTING_TOOLTIP : undefined}
      className={cn(
        "flex h-full flex-col items-center rounded-xl border border-line bg-white p-5 text-center",
        resting && "bg-gray-50/80",
      )}
    >
      <div className={cn("relative", resting && "opacity-60 saturate-50")}>
        <AgentAvatar agentId={agentId} size="lg" />
        {resting && (
          <span
            aria-hidden
            className="animate-zzz absolute -top-2 -right-4 font-wordmark text-sm font-extrabold tracking-tight text-violet-400"
          >
            Zzz
          </span>
        )}
      </div>
      <div className={cn("flex w-full flex-1 flex-col items-center", resting && "opacity-70")}>
        <div className="mt-3 w-full rounded-md border border-line py-1 text-sm font-semibold text-gray-900">
          {profile.fullName}
        </div>
        <p className="mt-2 text-[13px] text-gray-500">{profile.persona}</p>
        <p className={cn("mt-3 inline-flex items-center gap-1.5 text-sm font-medium", profile.accent.text)}>
          <span className={cn("size-1.5 rounded-full", profile.accent.dot)} />
          {profile.role}
        </p>
        <p className="mt-2 flex-1 text-[13px] leading-relaxed text-gray-600">
          {resting && restingNote ? restingNote : profile.description}
        </p>
      </div>
      {status && (
        <div className="mt-4">
          <StatusBadge meta={AGENT_DISPLAY_STATUS[status]} dot={!resting} />
        </div>
      )}
    </article>
  );
}
