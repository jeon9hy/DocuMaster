import { getAgentProfile } from "@/constants/agents";
import { AGENT_STATUS } from "@/constants/status";
import { cn } from "@/lib/cn";
import { describeModelConfig } from "@/lib/models";
import type { AgentId, AgentModelConfig, AgentStatus } from "@/types";
import { StatusBadge } from "../ui/Badge";
import { AgentAvatar } from "./AgentAvatar";

interface AgentCardProps {
  agentId: AgentId;
  config: AgentModelConfig;
  /** 프로젝트에 속하지 않은 에이전트를 보여 줄 때는 생략 */
  status?: AgentStatus;
}

/** 멤버·에이전트 화면의 프로필 카드 */
export function AgentCard({ agentId, config, status }: AgentCardProps) {
  const profile = getAgentProfile(agentId);
  return (
    <article className="flex flex-col items-center rounded-xl border border-line bg-white p-5 text-center">
      <AgentAvatar agentId={agentId} size="lg" />
      <div className="mt-3 w-full rounded-md border border-line py-1 text-sm font-semibold text-gray-900">
        {profile.fullName}
      </div>
      <p className="mt-2 text-[13px] text-gray-500">{profile.persona}</p>
      <p className={cn("mt-3 inline-flex items-center gap-1.5 text-sm font-medium", profile.accent.text)}>
        <span className={cn("size-1.5 rounded-full", profile.accent.dot)} />
        {profile.role}
      </p>
      <p className="mt-2 text-[13px] leading-relaxed text-gray-600">{profile.description}</p>
      <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
        <span className="rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
          {describeModelConfig(config)}
        </span>
        {status && <StatusBadge meta={AGENT_STATUS[status]} />}
      </div>
    </article>
  );
}
