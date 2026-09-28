import type { AgentId } from "./agent";
import type { RunSummary } from "./events";
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
    | { kind: "agent"; agentId: AgentId; toAgentId?: AgentId; text: string }
    | { kind: "activity"; agentId: AgentId; label: string }
    | { kind: "user"; text: string }
    | {
        kind: "system";
        tone: SystemTone;
        title: string;
        detail?: string;
        agentId?: AgentId;
        /** divider = 단계 전환(가운데 얇은 선) · compact = 에이전트 작업 시작(작은 글씨). 없으면 기본 줄 */
        display?: "divider" | "compact";
        /** 워크플로우 완료 — 결과 요약 카드로 그린다 */
        summary?: RunSummary;
      }
    | { kind: "artifact"; artifactId: string; agentId: AgentId }
    | { kind: "input"; request: UserInputRequest }
  );
