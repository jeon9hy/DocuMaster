import type { AgentId } from "./agent";
import type { UserInputRequest } from "./project";

export type SystemTone = "info" | "success" | "warning" | "error";

interface FeedItemBase {
  id: string;
  createdAt: string;
  /** "detail"이면 피드에서 「세부 활동 N건」으로 접어 보여 준다(내부 전달·파일 갱신 등) */
  importance?: "detail";
}

/**
 * 중앙 Activity Feed의 한 줄.
 * LLM이 만든 문장은 `agent`와 `input`의 message뿐이다. `system`·`artifact`는 이벤트에서 코드로 만든다.
 */
export type FeedItem = FeedItemBase &
  (
    | { kind: "agent"; agentId: AgentId; text: string }
    | { kind: "user"; text: string }
    | { kind: "system"; tone: SystemTone; title: string; detail?: string; agentId?: AgentId }
    | { kind: "artifact"; artifactId: string; agentId: AgentId }
    | { kind: "input"; request: UserInputRequest }
  );
