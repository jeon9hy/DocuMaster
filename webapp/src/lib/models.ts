import { MODEL_OPTIONS, REASONING_LABELS, type ModelOption } from "@/constants/models";
import type { AgentModelConfig } from "@/types";

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
