import { ArrowUpRight, FileText, Presentation } from "lucide-react";
import { documentKindLabel } from "@/constants/library";
import { cn } from "@/lib/cn";
import { formatShortDate } from "@/lib/library";
import type { LibraryDocument } from "@/types";
import { kindTone } from "./kindTone";

/** 라이브러리 카드 한 장. 누르면 그 프로젝트의 작업물 화면에서 최종본을 연다. */
export function LibraryDocumentCard({ doc, onOpen }: { doc: LibraryDocument; onOpen: () => void }) {
  const tone = kindTone(doc.kind);
  const Icon = doc.mode === "presentation" ? Presentation : FileText;

  return (
    <button
      type="button"
      onClick={onOpen}
      className="group flex h-full w-full gap-3.5 rounded-xl border border-line bg-white p-4 text-left transition-all hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md hover:shadow-blue-900/5 focus-visible:border-blue-400 focus-visible:ring-2 focus-visible:ring-blue-100 focus-visible:outline-none"
    >
      <span className={cn("flex size-11 shrink-0 items-center justify-center rounded-xl", tone.tile)}>
        <Icon className="size-5" aria-hidden />
      </span>

      <span className="flex min-w-0 flex-1 flex-col gap-1.5">
        <span className="flex items-center gap-2 text-xs">
          <span className={cn("inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 font-semibold", tone.pill)}>
            {documentKindLabel(doc.kind)}
          </span>
          <time dateTime={doc.date} className="text-gray-400">
            {formatShortDate(doc.date)}
          </time>
          <ArrowUpRight
            className="ml-auto size-4 text-gray-300 transition-colors group-hover:text-blue-600"
            aria-hidden
          />
        </span>

        <span className="line-clamp-2 text-[15px] leading-snug font-semibold text-gray-900">{doc.title}</span>

        {doc.request && (
          <span className="line-clamp-2 text-[13px] text-pretty break-keep text-gray-500" title={doc.request}>
            {doc.request}
          </span>
        )}

        {doc.fileName && (
          <span className="mt-auto truncate pt-1 text-xs text-gray-400" title={doc.fileName}>
            {doc.fileName}
          </span>
        )}
      </span>
    </button>
  );
}
