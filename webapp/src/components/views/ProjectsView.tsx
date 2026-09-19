"use client";

import { useCallback, useState } from "react";
import { Folder, Plus, Trash2 } from "lucide-react";
import { PROJECT_MODE_LABEL } from "@/constants/navigation";
import { cn } from "@/lib/cn";
import { useAppActions, useAppState, useIsOwner } from "@/state/WorkspaceProvider";
import type { ProjectSummary } from "@/types";
import { NewProjectModal } from "../project/NewProjectModal";
import { Badge } from "../ui/Badge";
import { Button, IconButton } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { ViewContainer, ViewHeader } from "./ViewHeader";

/** 삭제 확인. 목록에서만 지우고 작업/·최종/ 파일은 남는다는 것을 분명히 알린다. */
function DeleteProjectModal({ project, onClose }: { project: ProjectSummary; onClose: () => void }) {
  const { deleteProject } = useAppActions();
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const confirm = async () => {
    setDeleting(true);
    setError(null);
    try {
      await deleteProject(project.id);
      onClose();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "삭제하지 못했습니다.");
      setDeleting(false);
    }
  };

  return (
    <Modal
      open
      title="프로젝트 삭제"
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>취소</Button>
          <Button variant="danger" icon={Trash2} disabled={deleting} onClick={confirm}>
            {deleting ? "삭제 중…" : "삭제"}
          </Button>
        </>
      }
    >
      <p className="text-sm text-gray-800">
        <strong>{project.name}</strong>을(를) 목록에서 삭제할까요?
      </p>
      <p className="mt-2 text-[13px] text-gray-500">
        화면의 대화·작업물 목록에서 사라집니다. 저장소의 작업/·최종/ 파일은 지우지 않으니, 결과물은 폴더에 그대로 남습니다.
      </p>
      {error && (
        <p role="alert" className="mt-3 text-xs text-red-600">
          {error}
        </p>
      )}
    </Modal>
  );
}

export function ProjectsView() {
  const { projects, projectId } = useAppState();
  const { selectProject, setView } = useAppActions();
  const isOwner = useIsOwner();
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<ProjectSummary | null>(null);
  const closeCreate = useCallback(() => setCreating(false), []);
  const closeDelete = useCallback(() => setDeleting(null), []);

  return (
    <ViewContainer>
      <ViewHeader
        title="프로젝트"
        action={
          isOwner && (
            <Button variant="primary" icon={Plus} onClick={() => setCreating(true)}>
              새 프로젝트
            </Button>
          )
        }
      />
      <ul className="grid gap-3 @lg:grid-cols-2 @4xl:grid-cols-3">
        {projects.map((project) => (
          <li key={project.id} className="group relative">
            <button
              type="button"
              onClick={() => {
                selectProject(project.id);
                setView("chat");
              }}
              className={cn(
                "flex h-full w-full flex-col gap-2 rounded-xl border bg-white p-4 text-left transition-colors hover:border-blue-300",
                project.id === projectId ? "border-blue-400" : "border-line",
                isOwner && "pr-12",
              )}
            >
              <span className="flex items-center gap-2">
                <Folder className="size-4 shrink-0 text-blue-600" aria-hidden />
                <span className="min-w-0 flex-1 truncate text-sm font-semibold text-gray-900">
                  {project.name}
                </span>
                <Badge>{PROJECT_MODE_LABEL[project.mode]}</Badge>
              </span>
              <span className="text-[13px] text-gray-500">{project.description}</span>
            </button>
            {isOwner && (
              <IconButton
                icon={Trash2}
                label={`${project.name} 삭제`}
                onClick={() => setDeleting(project)}
                className="absolute top-2.5 right-2 size-8 text-gray-400 hover:bg-red-50 hover:text-red-600"
              />
            )}
          </li>
        ))}
      </ul>
      <NewProjectModal open={creating} onClose={closeCreate} />
      {deleting && <DeleteProjectModal project={deleting} onClose={closeDelete} />}
    </ViewContainer>
  );
}
