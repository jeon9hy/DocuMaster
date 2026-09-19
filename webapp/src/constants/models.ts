import type { ProviderId, ReasoningLevel } from "@/types";

interface ProviderInfo {
  label: string;
  /** 비어 있으면 추론 강도 선택 칸을 숨긴다 */
  reasoningLevels: readonly ReasoningLevel[];
  defaultReasoning: ReasoningLevel | null;
}

export interface ModelOption {
  id: string;
  label: string;
  provider: ProviderId;
}

/** 모델·공급자 목록은 여기만 고친다. UI는 이 목록으로 드롭다운을 그린다. */
export const PROVIDERS: Record<ProviderId, ProviderInfo> = {
  anthropic: {
    label: "Anthropic",
    reasoningLevels: ["low", "medium", "high", "xhigh", "max"],
    defaultReasoning: "high",
  },
  openai: {
    label: "OpenAI",
    reasoningLevels: ["low", "medium", "high", "xhigh"],
    defaultReasoning: "high",
  },
  google: {
    label: "Google",
    reasoningLevels: [],
    defaultReasoning: null,
  },
};

export const MODEL_OPTIONS: readonly ModelOption[] = [
  { id: "claude-opus-5", label: "Claude Opus 5", provider: "anthropic" },
  { id: "claude-sonnet-5", label: "Claude Sonnet 5", provider: "anthropic" },
  { id: "claude-haiku-4-5", label: "Claude Haiku 4.5", provider: "anthropic" },
  { id: "gpt-5.6-sol", label: "GPT-5.6 Sol", provider: "openai" },
  { id: "notebooklm", label: "NotebookLM", provider: "google" },
];

export const REASONING_LABELS: Record<ReasoningLevel, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  xhigh: "XHigh",
  max: "Max",
};
