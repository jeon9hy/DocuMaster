import { getAgentProfile } from "@/constants/agents";
import { cn } from "@/lib/cn";
import { formatTime } from "@/lib/format";
import { describeModelConfig } from "@/lib/models";
import type { Agent, AgentId } from "@/types";
import { AgentAvatar } from "../agent/AgentAvatar";

interface AgentMessageProps {
  agentId: AgentId;
  /** 현재 모델 표시용. 프로젝트에서 빠진 에이전트면 없을 수 있다. */
  agent?: Agent;
  text: string;
  createdAt: string;
}

/** LLM 응답 요약이 들어가는 유일한 말풍선 */
export function AgentMessage({ agentId, agent, text, createdAt }: AgentMessageProps) {
  const profile = getAgentProfile(agentId);
  return (
    <article className="flex gap-3">
      <AgentAvatar agentId={agentId} size="md" />
      <div className="min-w-0 flex-1">
        <header className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <span className={cn("text-[15px] font-semibold", profile.accent.text)}>{profile.name}</span>
          <span className="text-xs text-gray-500">
            {profile.role}
            {agent && ` · ${describeModelConfig(agent.config)}`}
          </span>
          <time className="ml-auto text-xs text-gray-400" dateTime={createdAt}>
            {formatTime(createdAt)}
          </time>
        </header>
        <p
          className={cn(
            "mt-1.5 inline-block max-w-[640px] rounded-xl rounded-tl-sm px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-line text-gray-800",
            profile.accent.soft,
          )}
        >
          {text}
        </p>
      </div>
    </article>
  );
}
