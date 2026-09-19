"use client";

import { useState, type FormEvent } from "react";
import { PROJECT_MODE_LABEL } from "@/constants/navigation";
import { useAppActions } from "@/state/WorkspaceProvider";
import type { ProjectMode } from "@/types";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { SegmentedControl } from "../ui/SegmentedControl";

const FORM_ID = "new-project-form";

const MODE_OPTIONS: readonly { id: ProjectMode; label: string }[] = [
  { id: "document", label: `${PROJECT_MODE_LABEL.document} · 제출용 최종본` },
  { id: "presentation", label: `${PROJECT_MODE_LABEL.presentation} · 슬라이드 초안` },
];

function NewProjectForm({ onDone }: { onDone: () => void }) {
  const { createProject, setView } = useAppActions();
  const [name, setName] = useState("");
  const [mode, setMode] = useState<ProjectMode>("document");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) {
      setError("프로젝트 이름을 입력해 주세요.");
      return;
    }
    try {
      await createProject({ name: name.trim(), mode });
      setView("chat");
      onDone();
    } catch {
      setError("프로젝트를 만들지 못했습니다.");
    }
  };

  return (
    <form id={FORM_ID} onSubmit={handleSubmit} className="space-y-4">
      <label className="block space-y-1.5">
        <span className="text-sm font-medium text-gray-800">프로젝트 이름</span>
        <input
          autoFocus
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="예: 수질 관리 사례 보고서"
          className="w-full rounded-lg border border-line px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        />
      </label>
      <div className="space-y-1.5">
        <span className="text-sm font-medium text-gray-800">결과물 형식</span>
        <SegmentedControl label="결과물 형식" options={MODE_OPTIONS} value={mode} onChange={setMode} />
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </form>
  );
}

export function NewProjectModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Modal
      open={open}
      title="새 프로젝트"
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>취소</Button>
          <Button variant="primary" type="submit" form={FORM_ID}>
            만들기
          </Button>
        </>
      }
    >
      <NewProjectForm onDone={onClose} />
    </Modal>
  );
}
