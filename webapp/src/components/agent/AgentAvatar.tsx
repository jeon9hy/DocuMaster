import { getAgentProfile } from "@/constants/agents";
import { cn } from "@/lib/cn";
import type { AgentId } from "@/types";
import { PORTRAITS } from "./portraits";

const SIZE_CLASS = {
  xs: "size-5 rounded-md",
  sm: "size-8 rounded-lg",
  md: "size-10 rounded-xl",
  lg: "size-20 rounded-2xl",
} as const;

interface AgentAvatarProps {
  agentId: AgentId;
  size?: keyof typeof SIZE_CLASS;
  className?: string;
}

export function AgentAvatar({ agentId, size = "md", className }: AgentAvatarProps) {
  const profile = getAgentProfile(agentId);
  const Portrait = PORTRAITS[agentId];
  const frame = cn("shrink-0 overflow-hidden ring-1 ring-black/5", SIZE_CLASS[size], className);

  if (profile.avatarSrc) {
    return (
      // 사용자가 넣는 로컬 초상 이미지라 next/image 최적화가 필요 없다.
      // eslint-disable-next-line @next/next/no-img-element
      <img src={profile.avatarSrc} alt={profile.name} className={cn(frame, "object-cover")} />
    );
  }
  return (
    <svg viewBox="0 0 64 64" role="img" aria-label={profile.name} className={frame}>
      <Portrait />
    </svg>
  );
}
