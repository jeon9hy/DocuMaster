"use client";

import { useCallback, useState } from "react";
import { ChevronDown, Folder, Plus } from "lucide-react";
import { PROJECT_MODE_LABEL } from "@/constants/navigation";
import { cn } from "@/lib/cn";
import { useAppActions, useAppState, useIsOwner } from "@/state/WorkspaceProvider";
import type { ProjectSummary } from "@/types";
import { Badge } from "../ui/Badge";
import { IconButton } from "../ui/Button";
import { Dropdown, DropdownItem } from "../ui/Dropdown";
import { NewProjectModal } from "./NewProjectModal";

const RECENT_COUNT = 3;
/** 「전체 프로젝트」는 이만큼씩 펼친다. */
const MORE_STEP = 3;

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

/**
 * 헤더의 프로젝트 전환 드롭다운. 바꾸면 좌·중·우 패널 전체가 그 프로젝트 기준으로 바뀐다.
 * 옆의 + 버튼은 새 프로젝트를 바로 연다(소유자만).
 * wide = 모바일 헤더 둘째 줄 — 폭을 다 쓰고 높이를 줄인다(이름이 잘리지 않게).
 */
export function ProjectSelector({ wide = false }: { wide?: boolean }) {
  const { projects, projectId } = useAppState();
  const { selectProject } = useAppActions();
  const isOwner = useIsOwner();
  const [creating, setCreating] = useState(false);
  const [shownRest, setShownRest] = useState(MORE_STEP);
  const closeCreate = useCallback(() => setCreating(false), []);
  const current = projects.find((project) => project.id === projectId);
  const groups = groupProjects(projects);

  return (
    <div className="flex items-center gap-1.5">
      <div className={cn("min-w-0 flex-1", !wide && "max-w-[280px]")}>
        <Dropdown
          className="scrollbar-thin max-h-[70vh] overflow-y-auto"
          trigger={({ open, toggle }) => (
            <button
              type="button"
              onClick={() => {
                if (!open) setShownRest(MORE_STEP);
                toggle();
              }}
              aria-expanded={open}
              className={cn(
                "flex w-full items-center gap-2 rounded-lg border border-line bg-white px-3 text-left text-sm hover:bg-gray-50",
                wide ? "h-9" : "h-10",
              )}
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
              {groups.map((group, index) => {
                const isRest = index > 0;
                const visible = isRest ? group.projects.slice(0, shownRest) : group.projects;
                const hidden = group.projects.length - visible.length;
                return (
                  <div key={group.label}>
                    <p className="px-2.5 pt-1 pb-1.5 text-xs font-medium text-gray-500">{group.label}</p>
                    {visible.map((project) => (
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
                    {hidden > 0 && (
                      <DropdownItem onSelect={() => setShownRest((count) => count + MORE_STEP)}>
                        <ChevronDown className="size-4 text-gray-400" aria-hidden />
                        <span className="text-gray-500">더보기 ({hidden}개 남음)</span>
                      </DropdownItem>
                    )}
                  </div>
                );
              })}
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
      </div>
      {isOwner && (
        <IconButton
          icon={Plus}
          label="새 프로젝트"
          onClick={() => setCreating(true)}
          className={cn("border border-line bg-white text-blue-600! hover:text-blue-700!", wide ? "size-9" : "size-10")}
        />
      )}
      <NewProjectModal open={creating} onClose={closeCreate} />
    </div>
  );
}
