"use client";

import { memo, useState } from "react";
import { Lock, RotateCcw } from "lucide-react";
import { getAgentProfile } from "@/constants/agents";
import { PROVIDERS, REASONING_LABELS } from "@/constants/models";
import { formatDateTime } from "@/lib/format";
import { getModelLabel } from "@/lib/models";
import type { AgentModelConfig, AgentSetting, ProviderId, ProviderUsage, ReasoningLevel } from "@/types";
import { UsageTiles } from "../settings/UsageTiles";
import { Button } from "../ui/Button";
import { Select } from "../ui/Select";
import { AgentAvatar } from "./AgentAvatar";

/** 추론 강도를 넘기지 않을 때(도구 기본값) select에 쓰는 값 */
const TOOL_DEFAULT = "";
const ORDER: ReasoningLevel[] = ["low", "medium", "high", "xhigh", "max", "ultra"];

interface AgentSettingsRowProps {
  setting: AgentSetting;
  /** Owner만 true. false면 보기만 한다 */
  editable: boolean;
  onChange: (config: AgentModelConfig) => Promise<void>;
  onReset: () => Promise<void>;
  /** 이 에이전트가 쓰는 공급자의 사용량(로이드·유리·아냐 = Claude, 요르 = Codex) */
  usage?: ProviderUsage;
}

/**
 * 에이전트 한 명의 모델·추론 강도. 공급자와 상관없이 같은 UI를 쓴다.
 * 선택지는 백엔드가 준 「실제로 반영되는 값」뿐이다. 잠긴 에이전트는 이유를 함께 보여 준다.
 */
const AgentSettingsRow = memo(function AgentSettingsRow({ setting, editable, onChange, onReset, usage }: AgentSettingsRowProps) {
  const profile = getAgentProfile(setting.agentId);
  const { config } = setting;
  const locked = setting.lockedReason !== null;
  const disabled = !editable || locked;
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async (action: () => Promise<void>) => {
    setSaving(true);
    setError(null);
    try {
      await action();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "현재 선택한 모델 설정을 사용할 수 없습니다.");
    } finally {
      setSaving(false);
    }
  };

  const reasoningLabel = (level: ReasoningLevel | null) => (level ? REASONING_LABELS[level] : "도구 기본값");
  const levelsFor = (modelId: string): (ReasoningLevel | null)[] =>
    setting.reasoningByModel?.[modelId] ?? setting.reasoningLevels;
  const levels = levelsFor(config.modelId);
  const changeModel = (modelId: string) => {
    const next = levelsFor(modelId);
    const keep = next.includes(config.reasoningLevel);
    const lower = next.filter((level) => level !== null && ORDER.indexOf(level) <= ORDER.indexOf(config.reasoningLevel ?? "low"));
    return { ...config, modelId, reasoningLevel: keep ? config.reasoningLevel : (lower.at(-1) ?? next[0] ?? null) };
  };

  return (
    <li className="px-2 py-3">
      <div className="mb-2 flex items-center gap-2.5">
        <AgentAvatar agentId={setting.agentId} size="sm" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-gray-900">
            {profile.name}
            <span className="ml-2 text-xs font-normal text-gray-500">{profile.role}</span>
          </p>
          <p className="truncate text-xs text-gray-500">{PROVIDERS[config.provider].label}</p>
        </div>
        {editable && setting.overridden && (
          <Button size="sm" variant="ghost" icon={RotateCcw} disabled={saving} onClick={() => save(onReset)}>
            기본값으로
          </Button>
        )}
      </div>
      {usage?.available && (
        <div className="@container mb-2">
          <UsageTiles usage={usage} />
        </div>
      )}
      <div className="flex gap-2">
        <Select
          label={`${profile.name} 모델`}
          className="flex-[3]"
          value={config.modelId}
          disabled={disabled || saving}
          onChange={(event) => save(() => onChange(changeModel(event.target.value)))}
        >
          {setting.modelIds.map((modelId) => (
            <option key={modelId} value={modelId}>
              {getModelLabel({ ...config, modelId })}
            </option>
          ))}
        </Select>
        <Select
          label={`${profile.name} 추론 강도`}
          className="flex-[2]"
          value={config.reasoningLevel ?? TOOL_DEFAULT}
          disabled={disabled || saving || levels.length <= 1}
          onChange={(event) =>
            save(() =>
              onChange({
                ...config,
                reasoningLevel: event.target.value === TOOL_DEFAULT ? null : (event.target.value as ReasoningLevel),
              }),
            )
          }
        >
          {levels.map((level) => (
            <option key={level ?? TOOL_DEFAULT} value={level ?? TOOL_DEFAULT}>
              {reasoningLabel(level)}
            </option>
          ))}
        </Select>
      </div>
      <p className="mt-1.5 flex items-start gap-1 text-[11px] text-gray-400">
        {locked && <Lock className="mt-px size-3 shrink-0" aria-hidden />}
        {locked
          ? setting.lockedReason
          : setting.overridden && setting.updatedAt
            ? `Owner 설정 · 마지막 변경 ${formatDateTime(setting.updatedAt)}`
            : "기본값(DocuMaster 기본 배치)"}
        {!locked && levels.length === 1 && levels[0] === null && " · 서브에이전트는 추론 강도를 지정할 수 없습니다"}
      </p>
      {error && (
        <p role="alert" className="mt-1 text-xs text-red-600">
          {error}
        </p>
      )}
    </li>
  );
});

interface AgentSettingsListProps {
  settings: AgentSetting[];
  editable: boolean;
  onChange: (setting: AgentSetting, config: AgentModelConfig) => Promise<void>;
  onReset: (setting: AgentSetting) => Promise<void>;
  usageByProvider?: Partial<Record<ProviderId, ProviderUsage>>;
}

export function AgentSettingsList({ settings, editable, onChange, onReset, usageByProvider }: AgentSettingsListProps) {
  return (
    <ul className="divide-y divide-gray-100">
      {settings.map((setting) => (
        <AgentSettingsRow
          key={setting.agentId}
          setting={setting}
          editable={editable}
          onChange={(config) => onChange(setting, config)}
          onReset={() => onReset(setting)}
          usage={usageByProvider?.[setting.config.provider]}
        />
      ))}
    </ul>
  );
}
