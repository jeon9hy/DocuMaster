"use client";

import { useCallback, useState } from "react";
import { ChevronDown, Folder, Plus } from "lucide-react";
import { PROJECT_MODE_LABEL } from "@/constants/navigation";
import { cn } from "@/lib/cn";
import { useAppActions, useAppState, useIsOwner } from "@/state/WorkspaceProvider";
import type { ProjectSummary } from "@/types";
import { Badge } from "../ui/Badge";
import { Dropdown, DropdownItem } from "../ui/Dropdown";
import { NewProjectModal } from "./NewProjectModal";

const RECENT_COUNT = 3;

/** 최근 활동 순 몇 개 + 나머지. 프로젝트가 많아지면 「전체」 쪽에 검색을 붙일 자리다. */
function groupProjects(projects: ProjectSummary[]): { label: string; projects: ProjectSummary[] }[] {
  const recent = [...projects]
    .sort((a, b) => (b.lastActivityAt ?? "").localeCompare(a.lastActivityAt ?? ""))
    .slice(0, RECENT_COUNT);
  const rest = projects.filter((project) => !recent.includes(project));
  return [
    { label: "최근 프로젝트", projects: recent },
    ...(rest.length ? [{ label: "전체 프로젝트", projects: rest }] : []),
  ];
}

/** 헤더의 프로젝트 전환 드롭다운. 바꾸면 좌·중·우 패널 전체가 그 프로젝트 기준으로 바뀐다. */
export function ProjectSelector() {
  const { projects, projectId } = useAppState();
  const { selectProject } = useAppActions();
  const isOwner = useIsOwner();
  const [creating, setCreating] = useState(false);
  const closeCreate = useCallback(() => setCreating(false), []);
  const current = projects.find((project) => project.id === projectId);
  const groups = groupProjects(projects);

  return (
    <>
      <Dropdown
        className="scrollbar-thin max-h-[70vh] overflow-y-auto"
        trigger={({ open, toggle }) => (
          <button
            type="button"
            onClick={toggle}
            aria-expanded={open}
            className="flex h-10 w-full max-w-[280px] items-center gap-2 rounded-lg border border-line bg-white px-3 text-left text-sm hover:bg-gray-50"
          >
            <Folder className="size-4 shrink-0 text-gray-500" aria-hidden />
            <span className="min-w-0 flex-1 truncate font-medium text-gray-800">
              {current?.name ?? "프로젝트 선택"}
            </span>
            <ChevronDown className={cn("size-4 shrink-0 text-gray-400 transition-transform", open && "rotate-180")} />
          </button>
        )}
      >
        {(close) => (
          <>
            {groups.map((group) => (
              <div key={group.label}>
                <p className="px-2.5 pt-1 pb-1.5 text-xs font-medium text-gray-500">{group.label}</p>
                {group.projects.map((project) => (
                  <DropdownItem
                    key={project.id}
                    active={project.id === projectId}
                    onSelect={() => {
                      selectProject(project.id);
                      close();
                    }}
                  >
                    <span className="min-w-0 flex-1 truncate">{project.name}</span>
                    <Badge>{PROJECT_MODE_LABEL[project.mode]}</Badge>
                  </DropdownItem>
                ))}
              </div>
            ))}
            {isOwner && (
              <>
                <div className="my-1 border-t border-line" />
                <DropdownItem
                  onSelect={() => {
                    close();
                    setCreating(true);
                  }}
                >
                  <Plus className="size-4 text-blue-600" aria-hidden />
                  <span className="text-blue-700">새 프로젝트</span>
                </DropdownItem>
              </>
            )}
          </>
        )}
      </Dropdown>
      <NewProjectModal open={creating} onClose={closeCreate} />
    </>
  );
}
