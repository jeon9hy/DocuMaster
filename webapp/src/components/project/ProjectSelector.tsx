"use client";

import { useCallback, useState } from "react";
import { ChevronDown, Folder, Plus } from "lucide-react";
import { PROJECT_MODE_LABEL } from "@/constants/navigation";
import { cn } from "@/lib/cn";
import { useAppActions, useAppState } from "@/state/WorkspaceProvider";
import { Badge } from "../ui/Badge";
import { Dropdown, DropdownItem } from "../ui/Dropdown";
import { NewProjectModal } from "./NewProjectModal";

/** 헤더의 프로젝트 전환 드롭다운. 바꾸면 좌·중·우 패널 전체가 그 프로젝트 기준으로 바뀐다. */
export function ProjectSelector() {
  const { projects, projectId } = useAppState();
  const { selectProject } = useAppActions();
  const [creating, setCreating] = useState(false);
  const closeCreate = useCallback(() => setCreating(false), []);
  const current = projects.find((project) => project.id === projectId);

  return (
    <>
      <Dropdown
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
            <p className="px-2.5 pt-1 pb-1.5 text-xs font-medium text-gray-500">최근 프로젝트</p>
            {projects.map((project) => (
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
      </Dropdown>
      <NewProjectModal open={creating} onClose={closeCreate} />
    </>
  );
}
