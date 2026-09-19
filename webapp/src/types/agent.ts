import type { AgentId } from "@/constants/agents";

export type { AgentId };

/** 모델 공급자. 새 공급자는 constants/models.ts에만 추가하면 된다. */
export type ProviderId = "anthropic" | "openai" | "google";

export type ReasoningLevel = "low" | "medium" | "high" | "xhigh" | "max";

export type AgentStatus = "idle" | "working" | "done" | "error";

/** UI는 이 구조만 안다 — 특정 모델 전용 컴포넌트를 만들지 않는다. */
export interface AgentModelConfig {
  provider: ProviderId;
  modelId: string;
  /** 추론 강도를 지원하지 않는 모델은 null */
  reasoningLevel: ReasoningLevel | null;
}

export interface Agent {
  id: AgentId;
  config: AgentModelConfig;
  status: AgentStatus;
}
