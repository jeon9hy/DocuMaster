import { MODEL_OPTIONS, PROVIDERS, REASONING_LABELS, type ModelOption } from "@/constants/models";
import type { AgentModelConfig, ProviderId } from "@/types";

function getModelOption(modelId: string): ModelOption | undefined {
  return MODEL_OPTIONS.find((model) => model.id === modelId);
}

export function getModelLabel(config: AgentModelConfig): string {
  return getModelOption(config.modelId)?.label ?? config.modelId;
}

/** "GPT-5.6 Sol · XHigh" */
export function describeModelConfig(config: AgentModelConfig): string {
  const model = getModelLabel(config);
  return config.reasoningLevel ? `${model} · ${REASONING_LABELS[config.reasoningLevel]}` : model;
}

/** 모델을 바꿀 때 공급자가 달라지면 추론 강도를 그 공급자의 기본값으로 맞춘다. */
export function withModel(config: AgentModelConfig, modelId: string): AgentModelConfig {
  const option = getModelOption(modelId);
  if (!option) return config;
  const provider = PROVIDERS[option.provider];
  const keepsReasoning =
    config.reasoningLevel !== null && provider.reasoningLevels.includes(config.reasoningLevel);
  return {
    provider: option.provider,
    modelId,
    reasoningLevel: keepsReasoning ? config.reasoningLevel : provider.defaultReasoning,
  };
}

export function groupModelsByProvider(): { provider: ProviderId; models: ModelOption[] }[] {
  return (Object.keys(PROVIDERS) as ProviderId[]).map((provider) => ({
    provider,
    models: MODEL_OPTIONS.filter((model) => model.provider === provider),
  }));
}
