"use client";

import { useCallback, useMemo } from "react";
import { Bot, Info } from "lucide-react";
import { useServiceData } from "@/hooks/useServiceData";
import { serviceKind, workspaceService } from "@/services";
import { useIsOwner } from "@/state/WorkspaceProvider";
import type { AgentModelConfig, AgentSetting, ProviderId, ProviderUsage } from "@/types";
import { AgentSettingsList } from "../agent/AgentSettings";
import { AccountPanel } from "../settings/AccountPanel";
import { loadUsage, UsagePanel } from "../settings/UsagePanel";
import { Badge } from "../ui/Badge";
import { Panel } from "../ui/Panel";
import { ErrorState, LoadingState } from "../ui/States";
import { ViewContainer, ViewHeader } from "./ViewHeader";

const loadSettings = () => workspaceService.listAgentSettings();
const loadHealth = () => workspaceService.getHealth();

function PanelTitle({ icon: Icon, children }: { icon: typeof Bot; children: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <Icon className="size-4 text-gray-400" aria-hidden />
      {children}
    </span>
  );
}

/** 모델 설정: Owner만 바꾸고, 바꾼 값은 다음 실행부터 적용된다. */
function ModelSettingsPanel() {
  const isOwner = useIsOwner();
  const { state, reload, set } = useServiceData(loadSettings);
  const usage = useServiceData(loadUsage).state;
  const usageByProvider = useMemo(() => {
    const map: Partial<Record<ProviderId, ProviderUsage>> = {};
    if (usage.status === "success") for (const item of usage.data) map[item.provider] = item;
    return map;
  }, [usage]);

  const change = useCallback(
    async (setting: AgentSetting, config: AgentModelConfig) =>
      set(await workspaceService.updateAgentSetting(setting.agentId, config)),
    [set],
  );
  const reset = useCallback(
    async (setting: AgentSetting) => set(await workspaceService.resetAgentSetting(setting.agentId)),
    [set],
  );

  return (
    <Panel title={<PanelTitle icon={Bot}>모델 설정</PanelTitle>}>
      <p className="mx-2 mb-1 rounded-lg bg-blue-50 px-3 py-2 text-xs text-blue-800">
        변경사항은 다음 실행부터 적용됩니다. 진행 중인 실행은 시작할 때의 설정을 그대로 씁니다.
      </p>
      {!isOwner && (
        <p className="mx-2 mb-1 rounded-lg bg-gray-100 px-3 py-2 text-xs text-gray-600">
          🔒 모델 설정은 Owner 로그인 후 변경할 수 있습니다.
        </p>
      )}
      {state.status === "loading" && <LoadingState />}
      {state.status === "error" && <ErrorState message={state.message} onRetry={reload} className="py-6" />}
      {state.status === "success" && (
        <AgentSettingsList
          settings={state.data}
          editable={isOwner}
          onChange={change}
          onReset={reset}
          usageByProvider={usageByProvider}
        />
      )}
    </Panel>
  );
}

/** 앱 설정: 지금 어떤 백엔드·오케스트레이터에 붙어 있는지(LLM을 부르지 않고 확인한 값) */
function AppInfoPanel() {
  const { state } = useServiceData(loadHealth);
  const health = state.status === "success" ? state.data : null;
  return (
    <Panel title={<PanelTitle icon={Info}>앱 설정</PanelTitle>} bodyClassName="space-y-2 px-4 pb-4 text-[13px] text-gray-600">
      <p className="flex items-center justify-between gap-3">
        <span className="shrink-0 whitespace-nowrap">연결</span>
        {serviceKind === "mock" ? (
          <Badge variant="warning" dot>
            목업 모드 (백엔드 없음)
          </Badge>
        ) : state.status === "error" ? (
          <Badge variant="danger" dot>
            백엔드 연결 안 됨
          </Badge>
        ) : (
          <Badge variant="success" dot>
            로컬 백엔드
          </Badge>
        )}
      </p>
      {health && (
        <p className="flex items-center justify-between gap-3">
          <span className="shrink-0 whitespace-nowrap">오케스트레이터</span>
          <Badge variant={health.orchestrator === "fake" ? "neutral" : "primary"}>
            {health.orchestrator === "fake" ? "fake (비용 없는 가짜 실행)" : `${health.orchestrator} (실제 실행)`}
          </Badge>
        </p>
      )}
      {health && health.missingTools.length > 0 && (
        <p className="text-xs text-red-600">설치되지 않은 도구: {health.missingTools.join(", ")}</p>
      )}
    </Panel>
  );
}

/** 설정: 모델 설정 · 사용량 · 앱 설정 · 계정 (바꾸는 것은 Owner만) */
export function SettingsView() {
  return (
    <ViewContainer>
      <ViewHeader title="설정" description="에이전트 모델과 추론 강도, 사용량, 계정" />
      <div className="grid gap-4 @4xl:grid-cols-2">
        <ModelSettingsPanel />
        <div className="flex flex-col gap-4">
          <UsagePanel />
          <AppInfoPanel />
          <AccountPanel />
        </div>
      </div>
    </ViewContainer>
  );
}
