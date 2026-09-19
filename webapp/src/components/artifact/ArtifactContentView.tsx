import { Download, FileText } from "lucide-react";
import { cn } from "@/lib/cn";
import { formatBytes } from "@/lib/format";
import type { ArtifactContent } from "@/types";
import { MarkdownLite } from "./MarkdownLite";

/** 본문 종류(markdown·pdf·image·file)에 맞는 미리보기 */
export function ArtifactContentView({
  content,
  large = false,
}: {
  content: ArtifactContent;
  large?: boolean;
}) {
  switch (content.type) {
    case "markdown":
      return <MarkdownLite text={content.text} />;

    case "image":
      return (
        // 목업 SVG·사용자 파일이라 크기를 미리 알 수 없다 — 원본 그대로 보여 준다.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={content.src} alt={content.alt} className="w-full rounded-lg border border-line" />
      );

    case "pdf":
      // 실제 파일이면 브라우저 기본 PDF 뷰어로 보여 준다(추가 라이브러리 없음).
      if (content.src) {
        return (
          <iframe
            src={content.src}
            title={content.title}
            className={cn("w-full rounded-lg border border-line bg-white", large ? "h-[75vh]" : "h-72")}
          />
        );
      }
      // 목업: 실제 PDF 대신 첫 쪽 모양의 썸네일
      return (
        <div
          className={cn(
            "mx-auto flex aspect-[1/1.414] flex-col rounded-lg border border-line bg-white p-5 shadow-sm",
            large ? "max-w-md" : "max-w-full",
          )}
        >
          <div className="h-1 w-10 rounded-full bg-blue-600" />
          <p className="mt-4 text-lg font-bold text-gray-900">{content.title}</p>
          <p className="mt-1 text-xs text-gray-500">{content.subtitle}</p>
          <div className="mt-5 flex-1 rounded-md bg-gradient-to-br from-slate-100 to-blue-50" />
          <p className="mt-3 flex items-center gap-1 text-[11px] text-gray-400">
            <FileText className="size-3" aria-hidden />
            PDF · {content.pageCount}쪽
          </p>
        </div>
      );

    case "file":
      return (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-gray-300 bg-white px-4 py-6 text-center">
          <p className="text-sm font-medium text-gray-800">{content.fileName}</p>
          <p className="text-xs text-gray-500">
            {formatBytes(content.sizeBytes)} · 브라우저에서 미리 볼 수 없는 형식입니다.
          </p>
          <a
            href={content.downloadUrl}
            download
            className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-blue-600 px-3 text-[13px] font-medium text-white hover:bg-blue-700"
          >
            <Download className="size-4" aria-hidden />
            내려받기
          </a>
        </div>
      );
  }
}
