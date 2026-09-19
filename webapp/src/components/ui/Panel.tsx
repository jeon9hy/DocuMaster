import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

interface PanelProps {
  title: ReactNode;
  action?: ReactNode;
  className?: string;
  bodyClassName?: string;
  children: ReactNode;
}

/** 제목 + 우측 동작 + 본문으로 된 흰 카드. 사이드바의 각 구역에 쓴다. */
export function Panel({ title, action, className, bodyClassName, children }: PanelProps) {
  return (
    <section className={cn("rounded-xl border border-line bg-white", className)}>
      <header className="flex items-center justify-between gap-2 px-4 pt-3.5 pb-2">
        <h2 className="text-[15px] font-semibold text-gray-900">{title}</h2>
        {action}
      </header>
      <div className={cn("px-2 pb-2", bodyClassName)}>{children}</div>
    </section>
  );
}

/** 사이드바 안의 작은 소제목 */
export function SectionLabel({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between px-3 pb-1.5">
      <h3 className="text-xs font-medium text-gray-500">{children}</h3>
      {action}
    </div>
  );
}
