"use client";

import { useMemo } from "react";
import { Activity, ArrowRight, Folder, Server } from "lucide-react";
import { PROJECT_MODE_LABEL } from "@/constants/navigation";
import { useServiceData } from "@/hooks/useServiceData";
import { formatRelative, formatTime } from "@/lib/format";
import { serviceKind, workspaceService } from "@/services";
import { useAppActions, useAppState } from "@/state/WorkspaceProvider";
import type { FeedItem, ProjectSummary, ProjectWorkspace } from "@/types";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Panel } from "../ui/Panel";
import { EmptyState, LoadingState } from "../ui/States";
import { ViewContainer, ViewHeader } from "./ViewHeader";

const RECENT_PROJECTS = 3;
const RECENT_ACTIVITY = 6;
const loadHealth = () => workspaceService.getHealth();

/** 홈의 시스템 상태에 보이는 도구. 설치 여부만 확인한다(로그인·한도는 모른다). */
const TOOLS = [
  { id: "claude", label: "Claude Code" },
  { id: "codex", label: "Codex" },
  { id: "nlm", label: "NotebookLM (nlm)" },
] as const;

function byRecent(projects: ProjectSummary[]): ProjectSummary[] {
  return [...projects]
    .filter((project) => project.lastActivityAt)
    .sort((a, b) => (b.lastActivityAt ?? "").localeCompare(a.lastActivityAt ?? ""));
}

function RecentProjects() {
  const { projects } = useAppState();
  const { selectProject, setView } = useAppActions();
  const recent = byRecent(projects).slice(0, RECENT_PROJECTS);
  const shown = recent.length ? recent : projects.slice(0, RECENT_PROJECTS);

  return (
    <Panel title="최근 프로젝트" className="@3xl:col-span-2" bodyClassName="px-2 pb-2">
      {shown.length === 0 ? (
        <EmptyState icon={Folder} title="아직 프로젝트가 없습니다" className="py-6" />
      ) : (
        <ul className="divide-y divide-gray-100">
          {shown.map((project) => (
            <li key={project.id} className="flex items-center gap-3 px-2 py-3">
              <Folder className="size-4 shrink-0 text-blue-600" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="flex items-center gap-2">
                  <span className="truncate text-sm font-semibold text-gray-900">{project.name}</span>
                  <Badge>{PROJECT_MODE_LABEL[project.mode]}</Badge>
                </p>
                {project.lastActivityAt && (
                  <p className="mt-0.5 text-xs text-gray-500">마지막 작업 {formatRelative(project.lastActivityAt)}</p>
                )}
              </div>
              <Button
                size="sm"
                icon={ArrowRight}
                onClick={() => {
                  selectProject(project.id);
                  setView("chat");
                }}
              >
                계속 작업
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

/** 피드 한 줄을 홈용 짧은 문장으로. 코드에서 만든 문장만 쓴다(LLM 문장은 옮기지 않는다). */
function describe(item: FeedItem, workspace: ProjectWorkspace): string | null {
  switch (item.kind) {
    case "system":
      return item.title;
    case "artifact":
      return `${workspace.artifacts.find((artifact) => artifact.id === item.artifactId)?.name ?? "작업물"} 생성`;
    case "input":
      return `사용자 확인 요청 · ${item.request.title}`;
    case "user":
      return "작업 지시";
    case "agent":
    case "activity":
      return null;
  }
}

function RecentActivity() {
  const { workspace } = useAppState();
  const items = useMemo(() => {
    if (!workspace) return [];
    return workspace.feed
      .filter((item) => item.importance !== "detail")
      .map((item) => ({ item, text: describe(item, workspace) }))
      .filter((row): row is { item: FeedItem; text: string } => row.text !== null)
      .slice(-RECENT_ACTIVITY)
      .reverse();
  }, [workspace]);

  return (
    <Panel
      title={
        <span className="flex items-center gap-1.5">
          <Activity className="size-4 text-gray-400" aria-hidden />
          최근 활동{workspace && <span className="font-normal text-gray-500"> · {workspace.project.name}</span>}
        </span>
      }
    >
      {items.length === 0 ? (
        <EmptyState icon={Activity} title="최근 활동이 없습니다" className="py-6" />
      ) : (
        <ol className="space-y-1 px-2 pb-1">
          {items.map(({ item, text }) => (
            <li key={item.id} className="flex gap-3 text-[13px]">
              <time className="w-16 shrink-0 text-gray-400" dateTime={item.createdAt}>
                {formatTime(item.createdAt)}
              </time>
              <span className="min-w-0 flex-1 truncate text-gray-700">{text}</span>
            </li>
          ))}
        </ol>
      )}
    </Panel>
  );
}

function SystemStatus() {
  const { state } = useServiceData(loadHealth);
  const health = state.status === "success" ? state.data : null;
  return (
    <Panel
      title={
        <span className="flex items-center gap-1.5">
          <Server className="size-4 text-gray-400" aria-hidden />
          시스템 상태
        </span>
      }
      bodyClassName="px-4 pb-4"
    >
      {serviceKind === "mock" ? (
        <p className="text-[13px] text-gray-500">목업 모드라 도구를 확인하지 않습니다.</p>
      ) : state.status === "loading" ? (
        <LoadingState />
      ) : !health ? (
        <p className="text-[13px] text-red-600">로컬 백엔드에 연결할 수 없습니다.</p>
      ) : (
        <>
          <ul className="space-y-2 text-[13px] text-gray-700">
            {TOOLS.map((tool) => (
              <li key={tool.id} className="flex items-center justify-between gap-3">
                <span className="whitespace-nowrap">{tool.label}</span>
                {health.tools[tool.id] ? (
                  <Badge variant="success" dot>
                    설치됨
                  </Badge>
                ) : (
                  <Badge variant="danger" dot>
                    없음
                  </Badge>
                )}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[11px] leading-relaxed text-gray-400">
            설치 여부만 확인합니다. 로그인·사용량 한도는 실행할 때 알 수 있습니다(사용량은 설정 화면).
          </p>
        </>
      )}
    </Panel>
  );
}

/** 홈: 최근 프로젝트 · 최근 활동 · 시스템 상태 */
export function HomeView() {
  return (
    <ViewContainer>
      <ViewHeader title="홈" />
      <div className="grid gap-4 @3xl:grid-cols-2">
        <RecentProjects />
        <RecentActivity />
        <SystemStatus />
      </div>
    </ViewContainer>
  );
}
