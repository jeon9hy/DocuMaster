"use client";

import { memo } from "react";
import { getAgentProfile } from "@/constants/agents";
import { PROVIDERS, REASONING_LABELS } from "@/constants/models";
import { AGENT_STATUS } from "@/constants/status";
import { groupModelsByProvider, withModel } from "@/lib/models";
import { useAppActions } from "@/state/WorkspaceProvider";
import type { Agent, ReasoningLevel } from "@/types";
import { StatusBadge } from "../ui/Badge";
import { Select } from "../ui/Select";
import { AgentAvatar } from "./AgentAvatar";

const MODEL_GROUPS = groupModelsByProvider();

/** 에이전트 한 명의 모델·추론 강도 선택. 공급자와 상관없이 같은 UI를 쓴다. */
export const AgentSettingsRow = memo(function AgentSettingsRow({ agent }: { agent: Agent }) {
  const { updateAgentConfig } = useAppActions();
  const profile = getAgentProfile(agent.id);
  const reasoningLevels = PROVIDERS[agent.config.provider].reasoningLevels;

  return (
    <li className="rounded-lg px-2 py-2.5">
      <div className="mb-2 flex items-center gap-2.5">
        <AgentAvatar agentId={agent.id} size="sm" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-gray-900">{profile.name}</p>
          <p className="truncate text-xs text-gray-500">{profile.role}</p>
        </div>
        <StatusBadge meta={AGENT_STATUS[agent.status]} />
      </div>
      <div className="flex gap-2">
        <Select
          label={`${profile.name} 모델`}
          className="flex-[3]"
          value={agent.config.modelId}
          onChange={(event) => updateAgentConfig(agent.id, withModel(agent.config, event.target.value))}
        >
          {MODEL_GROUPS.map(({ provider, models }) => (
            <optgroup key={provider} label={PROVIDERS[provider].label}>
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.label}
                </option>
              ))}
            </optgroup>
          ))}
        </Select>
        <Select
          label={`${profile.name} 추론 강도`}
          className="flex-[2]"
          value={agent.config.reasoningLevel ?? ""}
          disabled={reasoningLevels.length === 0}
          onChange={(event) =>
            updateAgentConfig(agent.id, {
              ...agent.config,
              reasoningLevel: event.target.value as ReasoningLevel,
            })
          }
        >
          {reasoningLevels.length === 0 && <option value="">해당 없음</option>}
          {reasoningLevels.map((level) => (
            <option key={level} value={level}>
              {REASONING_LABELS[level]}
            </option>
          ))}
        </Select>
      </div>
    </li>
  );
});

export function AgentSettingsList({ agents }: { agents: Agent[] }) {
  return (
    <ul className="divide-y divide-gray-100">
      {agents.map((agent) => (
        <AgentSettingsRow key={agent.id} agent={agent} />
      ))}
    </ul>
  );
}
