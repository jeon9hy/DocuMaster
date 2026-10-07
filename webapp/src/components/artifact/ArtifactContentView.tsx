import { Download, FileText } from "lucide-react";
import { cn } from "@/lib/cn";
import { formatBytes } from "@/lib/format";
import type { ArtifactContent } from "@/types";
import { MarkdownLite } from "./MarkdownLite";

/** 본문 종류(markdown·pdf·image·file)에 맞는 미리보기 */
export function ArtifactContentView({
  content,
  large = false,
  fill = false,
}: {
  content: ArtifactContent;
  large?: boolean;
  /** 넓은 작업물 화면: 부모 칸 높이를 꽉 채운다(좁은 화면은 large와 같다) */
  fill?: boolean;
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
      // #view=FitH — 쪽 너비를 칸에 맞춘다(가로 스크롤 없이)
      if (content.src) {
        return (
          <iframe
            src={content.src.includes("#") ? content.src : `${content.src}#view=FitH`}
            title={content.title}
            className={cn(
              "w-full rounded-lg border border-line bg-surface",
              fill ? "h-[75vh] @3xl:h-full" : large ? "h-[75vh]" : "h-72",
            )}
          />
        );
      }
      // 목업: 실제 PDF 대신 첫 쪽 모양의 썸네일
      return (
        <div
          className={cn(
            "mx-auto flex aspect-[1/1.414] flex-col rounded-lg border border-line bg-surface p-5 shadow-sm",
            large ? "max-w-md" : "max-w-full",
          )}
        >
          <div className="h-1 w-10 rounded-full bg-primary" />
          <p className="mt-4 text-lg font-bold text-label">{content.title}</p>
          <p className="mt-1 text-xs text-label-alternative">{content.subtitle}</p>
          <div className="mt-5 flex-1 rounded-md bg-gradient-to-br from-fill to-primary/8" />
          <p className="mt-3 flex items-center gap-1 text-[11px] text-label-alternative">
            <FileText className="size-3" aria-hidden />
            PDF · {content.pageCount}쪽
          </p>
        </div>
      );

    case "file":
      return (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-line bg-surface px-4 py-6 text-center">
          <p className="text-sm font-medium text-label-neutral">{content.fileName}</p>
          <p className="text-xs text-label-alternative">
            {formatBytes(content.sizeBytes)} · 브라우저에서 미리 볼 수 없는 형식입니다.
          </p>
          <a
            href={content.downloadUrl}
            download
            className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-[13px] font-medium text-white hover:bg-primary-strong"
          >
            <Download className="size-4" aria-hidden />
            내려받기
          </a>
        </div>
      );
  }
}
