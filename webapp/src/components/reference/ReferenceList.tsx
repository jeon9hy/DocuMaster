"use client";

import { useState } from "react";
import {
  FileText,
  Image as ImageIcon,
  Link2,
  Loader2,
  Paperclip,
  Type,
  X,
  type LucideIcon,
} from "lucide-react";
import { formatDay } from "@/lib/format";
import type { Reference, ReferenceKind } from "@/types";
import { EmptyState } from "../ui/States";

const KIND_ICON: Record<ReferenceKind, { icon: LucideIcon; className: string }> = {
  pdf: { icon: FileText, className: "bg-red-50 text-red-600" },
  image: { icon: ImageIcon, className: "bg-sky-50 text-sky-600" },
  url: { icon: Link2, className: "bg-blue-50 text-blue-600" },
  text: { icon: Type, className: "bg-gray-100 text-gray-600" },
  markdown: { icon: FileText, className: "bg-gray-100 text-gray-600" },
  file: { icon: Paperclip, className: "bg-gray-100 text-gray-600" },
};

const PARSE_STATUS_TEXT = { uploaded: "업로드됨", processing: "처리 중", error: "처리 오류" } as const;

function ReferenceItem({
  reference,
  onRemove,
}: {
  reference: Reference;
  onRemove?: (referenceId: string) => void;
}) {
  const { icon: Icon, className } = KIND_ICON[reference.kind];
  const status = reference.parseStatus && reference.parseStatus !== "ready" ? reference.parseStatus : null;
  return (
    <li className="group flex items-center gap-2.5 rounded-lg px-2 py-1.5">
      <span className={`flex size-7 shrink-0 items-center justify-center rounded-md ${className}`}>
        {status === "processing" ? (
          <Loader2 className="size-3.5 animate-spin" aria-hidden />
        ) : (
          <Icon className="size-3.5" aria-hidden />
        )}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[13px] font-medium text-gray-800">{reference.name}</span>
        <span className="block truncate text-xs text-gray-500">
          {reference.detail} · {formatDay(reference.addedAt)}
          {status && <span className={status === "error" ? " text-red-600" : ""}> · {PARSE_STATUS_TEXT[status]}</span>}
        </span>
      </span>
      {onRemove && (
        <button
          type="button"
          onClick={() => onRemove(reference.id)}
          aria-label={`${reference.name} 삭제`}
          className="rounded p-1 text-gray-400 opacity-0 group-hover:opacity-100 hover:bg-gray-100 hover:text-gray-600 focus:opacity-100"
        >
          <X className="size-3.5" aria-hidden />
        </button>
      )}
    </li>
  );
}

interface ReferenceListProps {
  references: Reference[];
  /** 처음에 보여 줄 개수. 넘치면 「N개 더 보기」로 접는다(사이드바에서 워크플로우가 밀리지 않게). */
  limit?: number;
  onRemove?: (referenceId: string) => void;
}

export function ReferenceList({ references, limit, onRemove }: ReferenceListProps) {
  const [expanded, setExpanded] = useState(false);
  if (references.length === 0) {
    return <EmptyState icon={Paperclip} title="레퍼런스가 없습니다" className="py-4" />;
  }
  const hidden = limit && !expanded ? Math.max(references.length - limit, 0) : 0;
  const visible = hidden ? references.slice(0, limit) : references;
  return (
    <div>
      <ul className="space-y-0.5">
        {visible.map((reference) => (
          <ReferenceItem key={reference.id} reference={reference} onRemove={onRemove} />
        ))}
      </ul>
      {limit !== undefined && references.length > limit && (
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className="mt-1 px-2 text-xs font-medium text-blue-600 hover:underline"
        >
          {expanded ? "접기" : `+ ${hidden}개 더 보기`}
        </button>
      )}
    </div>
  );
}
