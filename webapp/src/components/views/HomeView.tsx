"use client";

import { ArrowRight, Folder, Server } from "lucide-react";
import { useServiceData } from "@/hooks/useServiceData";
import { formatRelative } from "@/lib/format";
import { serviceKind, workspaceService } from "@/services";
import { useAppActions, useAppState } from "@/state/WorkspaceProvider";
import type { ProjectSummary } from "@/types";
import { Badge } from "../ui/Badge";
import { ModeBadge } from "../project/ModeBadge";
import { Button } from "../ui/Button";
import { Panel } from "../ui/Panel";
import { EmptyState, LoadingState } from "../ui/States";
import { ProjectTrends } from "./ProjectTrends";
import { ViewContainer, ViewHeader } from "./ViewHeader";

const RECENT_PROJECTS = 3;
const loadHealth = () => workspaceService.getHealth();
const loadLibrary = () => workspaceService.listLibrary();

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
  const { selectProject } = useAppActions();
  const recent = byRecent(projects).slice(0, RECENT_PROJECTS);
  const shown = recent.length ? recent : projects.slice(0, RECENT_PROJECTS);

  return (
    <Panel title="최근 프로젝트" className="@3xl:col-span-2" bodyClassName="px-2 pb-2">
      {shown.length === 0 ? (
        <EmptyState icon={Folder} title="아직 프로젝트가 없습니다" className="py-6" />
      ) : (
        <ul className="divide-y divide-line-alt">
          {shown.map((project) => {
            const open = () => {
              selectProject(project.id); // 프로젝트를 고르면 대시보드로 들어간다
            };
            return (
              <li key={project.id} className="flex items-center gap-3 px-2 py-3">
                {/* 폴더·이름 줄 어디를 눌러도 프로젝트로 넘어간다 */}
                <button
                  type="button"
                  onClick={open}
                  className="-my-1 -ml-1 flex min-w-0 flex-1 items-center gap-3 rounded-lg px-1 py-1 text-left hover:bg-fill-alt"
                >
                  <Folder className="size-4 shrink-0 text-primary" aria-hidden />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2">
                      <span className="truncate text-sm font-semibold text-label">{project.name}</span>
                      <ModeBadge mode={project.mode} />
                    </span>
                    {project.lastActivityAt && (
                      <span className="mt-0.5 block text-xs text-label-alternative">
                        마지막 작업 {formatRelative(project.lastActivityAt)}
                      </span>
                    )}
                  </span>
                </button>
                <Button size="sm" icon={ArrowRight} onClick={open}>
                  계속 작업
                </Button>
              </li>
            );
          })}
        </ul>
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
          <Server className="size-4 text-label-assistive" aria-hidden />
          시스템 상태
        </span>
      }
      bodyClassName="px-4 pb-4"
    >
      {serviceKind === "mock" ? (
        <p className="text-[13px] text-label-alternative">목업 모드라 도구를 확인하지 않습니다.</p>
      ) : state.status === "loading" ? (
        <LoadingState />
      ) : !health ? (
        <p className="text-[13px] text-negative-fg">로컬 백엔드에 연결할 수 없습니다.</p>
      ) : (
        <>
          <ul className="space-y-2 text-[13px] text-label-neutral">
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
          <p className="mt-3 text-[11px] leading-relaxed text-label-alternative">
            설치 여부만 확인합니다. 로그인·사용량 한도는 실행할 때 알 수 있습니다(사용량은 설정 화면).
          </p>
        </>
      )}
    </Panel>
  );
}

/** 홈: 최근 프로젝트 · 만든 프로젝트 추이 · 시스템 상태. 프로젝트 안의 정보(최근 활동 등)는 대시보드에 있다. */
export function HomeView() {
  const { state } = useServiceData(loadLibrary);
  return (
    <ViewContainer>
      <ViewHeader title="홈" />
      <div className="grid gap-4 @3xl:grid-cols-2">
        <RecentProjects />
        {state.status === "success" && <ProjectTrends documents={state.data} />}
        <SystemStatus />
      </div>
    </ViewContainer>
  );
}
