import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * 아주 단순한 Markdown 표시(제목·목록·문단 + 줄 안의 **굵게**·`코드`).
 * 작업물 미리보기·확인 카드·에이전트 말풍선이 같이 쓴다. 글자 크기·색은 className으로 바꾼다.
 * 완전한 렌더링이 필요해지면 이 컴포넌트만 react-markdown 등으로 바꾸면 된다.
 */
export function MarkdownLite({ text, className }: { text: string; className?: string }) {
  return (
    <div className={cn("space-y-1.5 text-[13px] leading-relaxed text-label-neutral", className)}>
      {text.split("\n").map((line, index) => renderLine(line, index))}
    </div>
  );
}

function renderLine(line: string, key: number): ReactNode {
  if (line.startsWith("# ")) {
    return (
      <h3 key={key} className="pt-1 text-base font-semibold text-label">
        {renderInline(line.slice(2))}
      </h3>
    );
  }
  if (line.startsWith("## ")) {
    return (
      <h4 key={key} className="pt-2 text-sm font-semibold text-label-neutral">
        {renderInline(line.slice(3))}
      </h4>
    );
  }
  const listItem = line.match(/^\s*(-|\d+\.)\s+(.*)$/);
  if (listItem) {
    return (
      <p key={key} className="flex gap-2 pl-1">
        <span className="shrink-0 text-label-alternative">{listItem[1] === "-" ? "•" : listItem[1]}</span>
        <span className="min-w-0">{renderInline(listItem[2])}</span>
      </p>
    );
  }
  if (line.trim() === "") return null;
  return <p key={key}>{renderInline(line)}</p>;
}

/** `코드`와 **굵게**만 알아본다. 짝이 맞지 않는 기호는 글자 그대로 둔다. */
function renderInline(text: string): ReactNode[] {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.length > 2 && part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={index} className="rounded bg-label/[0.06] px-1 py-px font-mono text-[0.9em] break-all text-label-neutral">
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.length > 4 && part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={index} className="font-semibold text-label">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}
