import { FileText } from "lucide-react";
import { cn } from "@/lib/cn";
import type { ArtifactContent } from "@/types";
import { MarkdownLite } from "./MarkdownLite";

/** 본문 종류(markdown·pdf·image)에 맞는 미리보기 */
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
      // 1차 프로토타입: 실제 PDF 대신 첫 쪽 모양의 썸네일
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
  }
}
