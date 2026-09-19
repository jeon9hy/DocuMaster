"use client";

import { useWorkspace } from "@/state/WorkspaceProvider";
import { AgentSettingsList } from "../agent/AgentSettings";
import { Badge } from "../ui/Badge";
import { Panel } from "../ui/Panel";
import { ViewContainer, ViewHeader } from "./ViewHeader";

/** 에이전트 설정 전용 화면. 모바일에서는 오른쪽 패널 대신 여기서 모델을 바꾼다. */
export function SettingsView() {
  const workspace = useWorkspace();
  return (
    <ViewContainer>
      <ViewHeader title="설정" description={`${workspace.project.name}의 에이전트별 모델과 추론 강도`} />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <Panel title="에이전트 모델">
          <AgentSettingsList agents={workspace.agents} />
        </Panel>
        <Panel title="연결 상태" bodyClassName="space-y-3 px-4 pb-4 text-[13px] text-gray-600">
          <p className="flex items-center gap-2">
            <Badge variant="warning" dot>
              목업 모드
            </Badge>
            실제 AI API에 연결되어 있지 않습니다.
          </p>
          <p>
            모델을 바꾸면 화면 상태만 바뀝니다. 실제 오케스트레이터를 연결하면 같은 설정이
            서비스(<code className="text-xs">updateAgentConfig</code>)로 전달됩니다.
          </p>
        </Panel>
      </div>
    </ViewContainer>
  );
}
