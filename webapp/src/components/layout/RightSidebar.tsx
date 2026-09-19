"use client";

import { AlertTriangle, CheckCircle2, Loader2, Settings2, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import { useAppActions, useAppState, useWorkspace } from "@/state/WorkspaceProvider";
import type { Agent } from "@/types";
import { AgentSettingsList } from "../agent/AgentSettings";
import { ArtifactList } from "../artifact/ArtifactList";
import { ArtifactPreview } from "../artifact/ArtifactPreview";
import { Button } from "../ui/Button";
import { Panel } from "../ui/Panel";

function describeTeam(agents: Agent[]): { icon: LucideIcon; text: string; tone: string } {
  const failed = agents.filter((agent) => agent.status === "error").length;
  if (failed) {
    return { icon: AlertTriangle, text: `에이전트 ${failed}명에게 오류가 있습니다.`, tone: "bg-red-50 text-red-700" };
  }
  const working = agents.filter((agent) => agent.status === "working").length;
  if (working) {
    return { icon: Loader2, text: `에이전트 ${working}명이 작업 중입니다.`, tone: "bg-blue-50 text-blue-700" };
  }
  return { icon: CheckCircle2, text: "모든 에이전트가 정상 대기 중입니다.", tone: "bg-emerald-50 text-emerald-700" };
}

function TeamHealth({ agents }: { agents: Agent[] }) {
  const { icon: Icon, text, tone } = describeTeam(agents);
  return (
    <p className={cn("mx-2 mt-1 flex items-center gap-2 rounded-lg px-3 py-2 text-xs", tone)}>
      <Icon className="size-3.5 shrink-0" aria-hidden />
      {text}
    </p>
  );
}

/** 결과물 중심: 작업물 목록 · 미리보기 · 에이전트 설정 */
export function RightSidebar() {
  const workspace = useWorkspace();
  const { selectedArtifactId } = useAppState();
  const { selectArtifact, setView } = useAppActions();
  const selected = workspace.artifacts.find((artifact) => artifact.id === selectedArtifactId) ?? null;

  return (
    <div className="flex flex-col gap-3 p-3">
      <Panel
        title={`작업물 (${workspace.artifacts.length})`}
        action={
          <Button size="sm" variant="ghost" onClick={() => setView("artifacts")} className="h-7 text-blue-600">
            전체 보기
          </Button>
        }
      >
        <ArtifactList
          artifacts={workspace.artifacts}
          selectedId={selectedArtifactId}
          onSelect={selectArtifact}
        />
      </Panel>

      <Panel title={selected ? `미리보기 · ${selected.name}` : "미리보기"}>
        <ArtifactPreview projectId={workspace.project.id} artifact={selected} />
      </Panel>

      <Panel
        title="에이전트 설정"
        action={
          <Button
            size="sm"
            variant="ghost"
            icon={Settings2}
            onClick={() => setView("settings")}
            className="h-7 text-blue-600"
          >
            설정 관리
          </Button>
        }
      >
        <AgentSettingsList agents={workspace.agents} />
        <TeamHealth agents={workspace.agents} />
      </Panel>
    </div>
  );
}
