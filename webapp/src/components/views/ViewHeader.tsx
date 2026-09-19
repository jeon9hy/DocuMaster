import type { ReactNode } from "react";

interface ViewHeaderProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

/** 대화 외 화면의 공통 제목 줄 */
export function ViewHeader({ title, description, action }: ViewHeaderProps) {
  return (
    <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
        {description && <p className="mt-1 text-sm text-gray-500">{description}</p>}
      </div>
      {action}
    </header>
  );
}

/**
 * 대화 외 화면의 스크롤 영역. @container라서 안쪽 격자는 화면 폭이 아니라 **가운데 영역의 실제 폭**으로 열 수를 정한다
 * (양옆 패널이 열려 있어도 칸이 좁아져 글자가 줄바꿈되지 않게). 격자에는 `@3xl:`처럼 @ 접두사를 쓴다.
 */
export function ViewContainer({ children }: { children: ReactNode }) {
  return (
    <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto">
      <div className="@container mx-auto max-w-[1080px] px-4 py-6 md:px-8">{children}</div>
    </div>
  );
}
