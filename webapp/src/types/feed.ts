import type { AgentId } from "./agent";

export type SystemTone = "info" | "success" | "warning" | "error";

interface FeedItemBase {
  id: string;
  createdAt: string;
}

/**
 * 중앙 Activity Feed의 한 줄.
 * LLM이 만든 문장은 `agent`뿐이다. `system`·`artifact`는 이벤트에서 코드로 만든다.
 */
export type FeedItem = FeedItemBase &
  (
    | { kind: "agent"; agentId: AgentId; text: string }
    | { kind: "user"; text: string }
    | { kind: "system"; tone: SystemTone; title: string; detail?: string; agentId?: AgentId }
    | { kind: "artifact"; artifactId: string; agentId: AgentId }
  );
