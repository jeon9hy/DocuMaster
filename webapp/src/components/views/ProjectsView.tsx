"use client";

import { useCallback, useState } from "react";
import { Folder, Plus } from "lucide-react";
import { PROJECT_MODE_LABEL } from "@/constants/navigation";
import { cn } from "@/lib/cn";
import { useAppActions, useAppState } from "@/state/WorkspaceProvider";
import { NewProjectModal } from "../project/NewProjectModal";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { ViewContainer, ViewHeader } from "./ViewHeader";

export function ProjectsView() {
  const { projects, projectId } = useAppState();
  const { selectProject, setView } = useAppActions();
  const [creating, setCreating] = useState(false);
  const closeCreate = useCallback(() => setCreating(false), []);

  return (
    <ViewContainer>
      <ViewHeader
        title="프로젝트"
        action={
          <Button variant="primary" icon={Plus} onClick={() => setCreating(true)}>
            새 프로젝트
          </Button>
        }
      />
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {projects.map((project) => (
          <li key={project.id}>
            <button
              type="button"
              onClick={() => {
                selectProject(project.id);
                setView("chat");
              }}
              className={cn(
                "flex h-full w-full flex-col gap-2 rounded-xl border bg-white p-4 text-left transition-colors hover:border-blue-300",
                project.id === projectId ? "border-blue-400" : "border-line",
              )}
            >
              <span className="flex items-center gap-2">
                <Folder className="size-4 text-blue-600" aria-hidden />
                <span className="min-w-0 flex-1 truncate text-sm font-semibold text-gray-900">
                  {project.name}
                </span>
                <Badge>{PROJECT_MODE_LABEL[project.mode]}</Badge>
              </span>
              <span className="text-[13px] text-gray-500">{project.description}</span>
            </button>
          </li>
        ))}
      </ul>
      <NewProjectModal open={creating} onClose={closeCreate} />
    </ViewContainer>
  );
}
