import { FileText, Presentation, Sparkles } from "lucide-react";
import { documentKindLabel } from "@/constants/library";
import { PROJECT_MODE_LABEL } from "@/constants/navigation";
import { cn } from "@/lib/cn";
import { formatShortDate } from "@/lib/library";
import type { LibraryDocument, ProjectSummary } from "@/types";
import { kindTone } from "../library/kindTone";

interface ProjectInfoCardProps {
  project: ProjectSummary;
  /** 최종본이 있으면 라이브러리 항목(유형·날짜·원문 요청). 없으면 null */
  doc: LibraryDocument | null;
}

/** 작업물 화면 맨 위 — 라이브러리 카드와 같은 색으로 유형·날짜·제목·원문 요청을 보여 준다. */
export function ProjectInfoCard({ project, doc }: ProjectInfoCardProps) {
  const mode = doc?.mode ?? project.mode;
  const tone = doc ? kindTone(doc.kind) : null;
  const Icon = mode === "presentation" ? Presentation : mode === "auto" ? Sparkles : FileText;

  return (
    <section className="mb-4 flex items-start gap-4 rounded-2xl border border-line bg-white p-5 shadow-sm shadow-blue-900/[0.03]">
      <span
        className={cn(
          "flex size-12 shrink-0 items-center justify-center rounded-xl",
          tone ? tone.tile : "bg-gray-100 text-gray-500",
        )}
      >
        <Icon className="size-6" aria-hidden />
      </span>

      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {doc && tone && (
            <span className={cn("inline-flex items-center rounded-md px-1.5 py-0.5 font-semibold", tone.pill)}>
              {documentKindLabel(doc.kind)}
            </span>
          )}
          <span className="rounded-md bg-gray-100 px-1.5 py-0.5 font-medium text-gray-600">
            {PROJECT_MODE_LABEL[mode]}
          </span>
          {doc && (
            <time dateTime={doc.date} className="text-gray-400">
              {formatShortDate(doc.date)}
            </time>
          )}
        </div>
        <h1 className="text-xl leading-snug font-semibold text-balance break-keep text-gray-900">{project.name}</h1>
        {doc?.request && (
          <p className="line-clamp-2 text-sm text-gray-500" title={doc.request}>
            요청 · {doc.request}
          </p>
        )}
      </div>
    </section>
  );
}
