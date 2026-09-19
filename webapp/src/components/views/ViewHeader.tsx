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

/** 대화 외 화면의 스크롤 영역 */
export function ViewContainer({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1080px] px-4 py-6 md:px-8">{children}</div>
    </div>
  );
}
