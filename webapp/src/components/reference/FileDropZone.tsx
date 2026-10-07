"use client";

import { useState, type DragEvent } from "react";
import { Upload, X } from "lucide-react";
import { REFERENCE_FILE_ACCEPT, REFERENCE_FILE_HINT } from "@/constants/references";
import { cn } from "@/lib/cn";
import { formatBytes } from "@/lib/format";

const fileKey = (file: File) => `${file.name}:${file.size}:${file.lastModified}`;

/** 이미 담긴 파일과 같은 것(이름·크기·수정 시각)은 빼고 덧붙인다 */
function mergeFiles(current: File[], added: Iterable<File>): File[] {
  const seen = new Set(current.map(fileKey));
  const next = [...current];
  for (const file of added) {
    if (seen.has(fileKey(file))) continue;
    seen.add(fileKey(file));
    next.push(file);
  }
  return next;
}

interface FileDropZoneProps {
  files: File[];
  onChange: (files: File[]) => void;
  disabled?: boolean;
  className?: string;
}

/** 파일을 끌어다 놓거나 눌러서 여러 개 고르는 칸 + 올릴 목록. 올리기는 쓰는 쪽이 한다. */
export function FileDropZone({ files, onChange, disabled = false, className }: FileDropZoneProps) {
  const [dragging, setDragging] = useState(false);

  const onDragOver = (event: DragEvent) => {
    if (disabled || !event.dataTransfer.types.includes("Files")) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    setDragging(true);
  };
  const onDragLeave = (event: DragEvent) => {
    // 안쪽 요소로 옮겨 갈 때도 leave가 온다 — 칸 밖으로 나갔을 때만 끈다
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false);
  };
  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    if (!disabled && event.dataTransfer.files.length) onChange(mergeFiles(files, event.dataTransfer.files));
  };

  return (
    <div className={cn("space-y-2", className)}>
      <label
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={cn(
          "flex flex-col items-center gap-2 rounded-xl border border-dashed px-4 py-6 text-center transition-colors",
          disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:bg-gray-50",
          dragging ? "border-blue-500 bg-blue-50/60" : "border-gray-300",
        )}
      >
        <Upload className={cn("size-5", dragging ? "text-blue-600" : "text-gray-400")} aria-hidden />
        <span className="text-sm text-gray-700">
          {dragging ? "여기에 놓으세요" : "파일을 끌어다 놓거나 눌러서 고르세요"}
        </span>
        <span className="text-xs text-gray-400">{REFERENCE_FILE_HINT}</span>
        <input
          type="file"
          multiple
          className="sr-only"
          accept={REFERENCE_FILE_ACCEPT}
          disabled={disabled}
          onChange={(event) => {
            if (event.target.files?.length) onChange(mergeFiles(files, event.target.files));
            event.target.value = ""; // 같은 파일을 지웠다가 다시 고를 수 있게
          }}
        />
      </label>

      {files.length > 0 && (
        <ul className="scrollbar-thin max-h-48 space-y-0.5 overflow-y-auto rounded-lg border border-line p-1">
          {files.map((file) => (
            <li key={fileKey(file)} className="flex items-center gap-2 rounded-md px-2 py-1 text-[13px]">
              <span className="min-w-0 flex-1 truncate text-gray-800">{file.name}</span>
              <span className="shrink-0 text-xs text-gray-500">{formatBytes(file.size)}</span>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onChange(files.filter((item) => item !== file))}
                aria-label={`${file.name} 빼기`}
                className="rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 disabled:opacity-40"
              >
                <X className="size-3.5" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
