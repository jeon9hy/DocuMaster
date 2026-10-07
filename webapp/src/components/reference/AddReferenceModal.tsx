"use client";

import { useState, type FormEvent } from "react";
import { DEFAULT_APPLY_POLICY } from "@/constants/references";
import { useReferenceFileUpload } from "@/hooks/useReferenceFileUpload";
import { useAppActions } from "@/state/WorkspaceProvider";
import type { NewReferenceInput, ReferenceApplyPolicy } from "@/types";
import { Button } from "../ui/Button";
import { TextArea, TextField } from "../ui/Field";
import { Modal } from "../ui/Modal";
import { SegmentedControl } from "../ui/SegmentedControl";
import { ApplyPolicyField } from "./ApplyPolicyField";
import { FileDropZone } from "./FileDropZone";

type Source = NewReferenceInput["source"];

const SOURCES: readonly { id: Source; label: string }[] = [
  { id: "file", label: "파일 업로드" },
  { id: "url", label: "URL 추가" },
  { id: "text", label: "텍스트 입력" },
];

const FORM_ID = "add-reference-form";

/** URL·텍스트 입력이 다 갖춰졌을 때만 서비스에 넘길 객체를 만든다. 모자라면 null. */
function toInput(
  source: Exclude<Source, "file">,
  fields: { url: string; title: string; text: string },
  applyPolicy: ReferenceApplyPolicy,
): NewReferenceInput | null {
  switch (source) {
    case "url":
      return fields.url.trim() ? { source, applyPolicy, url: fields.url.trim(), title: fields.title.trim() } : null;
    case "text":
      return fields.title.trim() && fields.text.trim()
        ? { source, applyPolicy, title: fields.title.trim(), text: fields.text }
        : null;
  }
}

/** 모달 안의 폼. 모달이 닫히면 언마운트되어 입력값이 자연히 초기화된다. */
function AddReferenceForm({ onDone, onBusyChange }: { onDone: () => void; onBusyChange: (busy: boolean) => void }) {
  const { addReference } = useAppActions();
  const { upload, progress, uploading } = useReferenceFileUpload();
  const [source, setSource] = useState<Source>("file");
  const [files, setFiles] = useState<File[]>([]);
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [applyPolicy, setApplyPolicy] = useState<ReferenceApplyPolicy>(DEFAULT_APPLY_POLICY);
  const [error, setError] = useState<string | null>(null);

  const submitFiles = async () => {
    if (files.length === 0) {
      setError("올릴 파일을 골라 주세요.");
      return;
    }
    onBusyChange(true);
    const result = await upload(files, applyPolicy);
    onBusyChange(false);
    if (result.failed.length === 0) {
      onDone();
      return;
    }
    // 올라간 것은 목록에서 빼고, 실패한 것만 남겨 다시 시도하게 한다
    setFiles(result.failed);
    setError(`${result.failed.length}개를 올리지 못했습니다: ${result.error}`);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (source === "file") return submitFiles();
    const input = toInput(source, { url, title, text }, applyPolicy);
    if (!input) {
      setError("필요한 항목을 채워 주세요.");
      return;
    }
    try {
      await addReference(input);
      onDone();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "레퍼런스를 추가하지 못했습니다. 다시 시도해 주세요.");
    }
  };

  return (
    <form id={FORM_ID} onSubmit={handleSubmit} className="space-y-4">
      <SegmentedControl label="추가 방식" options={SOURCES} value={source} onChange={setSource} />

      {source === "file" && <FileDropZone files={files} onChange={setFiles} disabled={uploading} />}

      {source === "url" && (
        <div className="space-y-2">
          <TextField
            type="url"
            placeholder="https://"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
          <TextField
            placeholder="제목 (선택)"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </div>
      )}

      {source === "text" && (
        <div className="space-y-2">
          <TextField
            placeholder="제목"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <TextArea
            minRows={5}
            maxRows={12}
            placeholder="참고할 내용을 붙여 넣으세요"
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
        </div>
      )}

      <ApplyPolicyField value={applyPolicy} onChange={setApplyPolicy} />

      {progress && (
        <p className="text-sm text-label-alternative">
          올리는 중… {progress.done}/{progress.total}
        </p>
      )}
      {error && <p className="text-sm text-negative-fg">{error}</p>}
    </form>
  );
}

export function AddReferenceModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [busy, setBusy] = useState(false);
  // 올리는 도중에 닫으면 남은 파일이 조용히 빠진다 — 끝날 때까지 닫지 않는다
  const close = () => !busy && onClose();
  return (
    <Modal
      open={open}
      title="레퍼런스 추가"
      onClose={close}
      footer={
        <>
          <Button onClick={close} disabled={busy}>
            취소
          </Button>
          <Button variant="primary" type="submit" form={FORM_ID} disabled={busy}>
            {busy ? "올리는 중…" : "추가"}
          </Button>
        </>
      }
    >
      <AddReferenceForm onDone={onClose} onBusyChange={setBusy} />
    </Modal>
  );
}
