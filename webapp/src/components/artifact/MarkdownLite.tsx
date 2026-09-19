import type { ReactNode } from "react";

/**
 * 미리보기용 아주 단순한 Markdown 표시(제목·목록·문단만).
 * 완전한 렌더링이 필요해지면 이 컴포넌트만 react-markdown 등으로 바꾸면 된다.
 */
export function MarkdownLite({ text }: { text: string }) {
  return (
    <div className="space-y-1.5 text-[13px] leading-relaxed text-gray-700">
      {text.split("\n").map((line, index) => renderLine(line, index))}
    </div>
  );
}

function renderLine(line: string, key: number): ReactNode {
  if (line.startsWith("# ")) {
    return (
      <h3 key={key} className="pt-1 text-base font-semibold text-gray-900">
        {line.slice(2)}
      </h3>
    );
  }
  if (line.startsWith("## ")) {
    return (
      <h4 key={key} className="pt-2 text-sm font-semibold text-gray-800">
        {line.slice(3)}
      </h4>
    );
  }
  const listItem = line.match(/^(-|\d+\.)\s+(.*)$/);
  if (listItem) {
    return (
      <p key={key} className="flex gap-2 pl-1">
        <span className="shrink-0 text-gray-400">{listItem[1] === "-" ? "•" : listItem[1]}</span>
        <span>{listItem[2]}</span>
      </p>
    );
  }
  if (line.trim() === "") return null;
  return <p key={key}>{line}</p>;
}
