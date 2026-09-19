"use client";

import { useState, type FormEvent } from "react";
import { PROJECT_MODE_LABEL } from "@/constants/navigation";
import { useAppActions } from "@/state/WorkspaceProvider";
import type { ProjectModeChoice } from "@/types";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { SegmentedControl } from "../ui/SegmentedControl";

const FORM_ID = "new-project-form";

const MODE_OPTIONS: readonly { id: ProjectModeChoice; label: string }[] = [
  { id: "auto", label: PROJECT_MODE_LABEL.auto },
  { id: "document", label: `${PROJECT_MODE_LABEL.document} · 최종본` },
  { id: "presentation", label: `${PROJECT_MODE_LABEL.presentation} · 초안` },
];

const MODE_HINT: Record<ProjectModeChoice, string> = {
  auto: "로이드가 요청을 읽고 문서/발표를 판정합니다. 애매하면 한 번 묻습니다.",
  document: "보고서·분석·제안서 — 그대로 제출할 최종 PDF를 만듭니다.",
  presentation: "발표·슬라이드 — 발표팩과 슬라이드 초안을 만듭니다. 최종 디자인은 따로 합니다.",
};

function NewProjectForm({ onDone }: { onDone: () => void }) {
  const { createProject, setView } = useAppActions();
  const [name, setName] = useState("");
  const [mode, setMode] = useState<ProjectModeChoice>("auto");
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
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "프로젝트를 만들지 못했습니다.");
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
        <p className="text-xs text-gray-500">{MODE_HINT[mode]}</p>
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
