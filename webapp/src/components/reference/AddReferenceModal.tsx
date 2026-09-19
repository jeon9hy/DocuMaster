"use client";

import { useState, type FormEvent } from "react";
import { Upload } from "lucide-react";
import { APPLY_POLICIES, DEFAULT_APPLY_POLICY } from "@/constants/references";
import { cn } from "@/lib/cn";
import { formatBytes } from "@/lib/format";
import { useAppActions } from "@/state/WorkspaceProvider";
import type { NewReferenceInput, ReferenceApplyPolicy } from "@/types";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { SegmentedControl } from "../ui/SegmentedControl";

type Source = NewReferenceInput["source"];

const SOURCES: readonly { id: Source; label: string }[] = [
  { id: "file", label: "파일 업로드" },
  { id: "url", label: "URL 추가" },
  { id: "text", label: "텍스트 입력" },
];

const FORM_ID = "add-reference-form";
const inputClass =
  "w-full rounded-lg border border-line px-3 py-2 text-sm text-gray-800 placeholder:text-gray-400 focus:border-blue-500 focus:outline-none";

/** 입력값이 다 갖춰졌을 때만 서비스에 넘길 객체를 만든다. 모자라면 null. */
function toInput(
  source: Source,
  fields: { file: File | null; url: string; title: string; text: string },
  applyPolicy: ReferenceApplyPolicy,
): NewReferenceInput | null {
  switch (source) {
    case "file":
      return fields.file ? { source, applyPolicy, file: fields.file } : null;
    case "url":
      return fields.url.trim() ? { source, applyPolicy, url: fields.url.trim(), title: fields.title.trim() } : null;
    case "text":
      return fields.title.trim() && fields.text.trim()
        ? { source, applyPolicy, title: fields.title.trim(), text: fields.text }
        : null;
  }
}

/** 모달 안의 폼. 모달이 닫히면 언마운트되어 입력값이 자연히 초기화된다. */
function AddReferenceForm({ onDone }: { onDone: () => void }) {
  const { addReference } = useAppActions();
  const [source, setSource] = useState<Source>("file");
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [applyPolicy, setApplyPolicy] = useState<ReferenceApplyPolicy>(DEFAULT_APPLY_POLICY);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const input = toInput(source, { file, url, title, text }, applyPolicy);
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

      {source === "file" && (
        <label className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border border-dashed border-gray-300 px-4 py-6 text-center hover:bg-gray-50">
          <Upload className="size-5 text-gray-400" aria-hidden />
          <span className="text-sm text-gray-700">
            {file ? `${file.name} · ${formatBytes(file.size)}` : "파일을 선택하세요"}
          </span>
          <span className="text-xs text-gray-400">PDF · 이미지 · Markdown · 텍스트</span>
          <input
            type="file"
            className="sr-only"
            accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.md,.txt"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
      )}

      {source === "url" && (
        <div className="space-y-2">
          <input
            className={inputClass}
            type="url"
            placeholder="https://"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
          <input
            className={inputClass}
            placeholder="제목 (선택)"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </div>
      )}

      {source === "text" && (
        <div className="space-y-2">
          <input
            className={inputClass}
            placeholder="제목"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <textarea
            className={cn(inputClass, "min-h-28 resize-y")}
            placeholder="참고할 내용을 붙여 넣으세요"
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
        </div>
      )}

      <fieldset>
        <legend className="mb-2 text-sm font-medium text-gray-800">새 레퍼런스를 어떻게 반영할까요?</legend>
        <div className="space-y-1.5">
          {APPLY_POLICIES.map((policy) => (
            <label
              key={policy.id}
              className={cn(
                "flex cursor-pointer gap-2.5 rounded-lg border px-3 py-2",
                applyPolicy === policy.id ? "border-blue-300 bg-blue-50/50" : "border-line",
              )}
            >
              <input
                type="radio"
                name="applyPolicy"
                className="mt-0.5 accent-blue-600"
                checked={applyPolicy === policy.id}
                onChange={() => setApplyPolicy(policy.id)}
              />
              <span>
                <span className="block text-sm text-gray-800">{policy.label}</span>
                <span className="block text-xs text-gray-500">{policy.hint}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {error && <p className="text-sm text-red-600">{error}</p>}
    </form>
  );
}

export function AddReferenceModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Modal
      open={open}
      title="레퍼런스 추가"
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>취소</Button>
          <Button variant="primary" type="submit" form={FORM_ID}>
            추가
          </Button>
        </>
      }
    >
      <AddReferenceForm onDone={onClose} />
    </Modal>
  );
}
