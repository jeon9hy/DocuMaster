import { getAgentProfile } from "@/constants/agents";
import { cn } from "@/lib/cn";
import { formatTime } from "@/lib/format";
import type { AgentId } from "@/types";
import { AgentAvatar } from "../agent/AgentAvatar";
import { MarkdownLite } from "../artifact/MarkdownLite";
import { HandoffMessage } from "./HandoffMessage";

interface AgentMessageProps {
  agentId: AgentId;
  toAgentId?: AgentId;
  text: string;
  createdAt: string;
}

/** LLM 응답 요약이 들어가는 유일한 말풍선. 에이전트끼리 주고받은 전달문은 한 줄로 접는다. */
export function AgentMessage({ agentId, toAgentId, text, createdAt }: AgentMessageProps) {
  if (toAgentId) return <HandoffMessage agentId={agentId} toAgentId={toAgentId} text={text} createdAt={createdAt} />;
  const profile = getAgentProfile(agentId);
  return (
    <article className="flex gap-3">
      <AgentAvatar agentId={agentId} size="md" />
      <div className="min-w-0 flex-1">
        <header className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <span className={cn("text-[15px] font-semibold", profile.accent.text)}>{profile.name}</span>
          <span className="text-xs text-label-alternative">{profile.role}</span>
          <time className="ml-auto text-xs text-label-alternative" dateTime={createdAt}>
            {formatTime(createdAt)}
          </time>
        </header>
        <div
          className={cn(
            "mt-1.5 inline-block max-w-[640px] break-words rounded-2xl rounded-tl-sm px-4 py-3",
            profile.accent.soft,
          )}
        >
          <MarkdownLite text={text} className="space-y-1 text-sm text-label-neutral" />
        </div>
      </div>
    </article>
  );
}
