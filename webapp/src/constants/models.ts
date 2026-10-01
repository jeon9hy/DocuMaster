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
    reasoningLevels: ["low", "medium", "high", "xhigh", "max", "ultra"],
    defaultReasoning: "high",
  },
  google: {
    label: "Google",
    reasoningLevels: [],
    defaultReasoning: null,
  },
};

export const MODEL_OPTIONS: readonly ModelOption[] = [
  { id: "claude-fable-5-1", label: "Claude Fable 5.1", provider: "anthropic" },
  { id: "claude-opus-5-5", label: "Claude Opus 5.5", provider: "anthropic" },
  { id: "claude-sonnet-5-5", label: "Claude Sonnet 5.5", provider: "anthropic" },
  { id: "claude-haiku-4-5", label: "Claude Haiku 4.5", provider: "anthropic" },
  // Codex: 실제 선택지는 백엔드가 ~/.codex/models_cache.json에서 읽는다. 여기는 표시 이름만.
  { id: "gpt-6.1-sol", label: "GPT-6.1 Sol", provider: "openai" },
  { id: "gpt-6-astra", label: "GPT-6 Astra", provider: "openai" },
  { id: "gpt-6-sol", label: "GPT-6 Sol", provider: "openai" },
  { id: "gpt-6-luna", label: "GPT-6 Luna", provider: "openai" },
  { id: "gpt-5.6-sol", label: "GPT-5.6 Sol", provider: "openai" },
  { id: "gpt-5.6-terra", label: "GPT-5.6 Terra", provider: "openai" },
  { id: "gpt-5.6-luna", label: "GPT-5.6 Luna", provider: "openai" },
  { id: "gpt-5.5", label: "GPT-5.5", provider: "openai" },
  { id: "notebooklm", label: "NotebookLM", provider: "google" },
];

export const REASONING_LABELS: Record<ReasoningLevel, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  xhigh: "XHigh",
  max: "Max",
  ultra: "Ultra",
};
