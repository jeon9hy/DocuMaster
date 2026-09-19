"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";

interface PanelProps {
  title: ReactNode;
  action?: ReactNode;
  className?: string;
  bodyClassName?: string;
  /** 제목을 눌러 접고 펼 수 있게 한다(자주 쓰지 않는 구역용) */
  collapsible?: boolean;
  defaultOpen?: boolean;
  children: ReactNode;
}

/** 제목 + 우측 동작 + 본문으로 된 흰 카드. 사이드바의 각 구역에 쓴다. */
export function Panel({
  title,
  action,
  className,
  bodyClassName,
  collapsible = false,
  defaultOpen = true,
  children,
}: PanelProps) {
  const [open, setOpen] = useState(defaultOpen);
  const isOpen = !collapsible || open;
  return (
    <section className={cn("rounded-xl border border-line bg-white", className)}>
      <header className={cn("flex items-center justify-between gap-2 px-4 pt-3.5", isOpen ? "pb-2" : "pb-3.5")}>
        {collapsible ? (
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            className="flex min-w-0 items-center gap-1.5 text-left"
          >
            <ChevronDown
              className={cn("size-4 shrink-0 text-gray-400 transition-transform", !open && "-rotate-90")}
              aria-hidden
            />
            <h2 className="text-[15px] font-semibold text-gray-900">{title}</h2>
          </button>
        ) : (
          <h2 className="text-[15px] font-semibold text-gray-900">{title}</h2>
        )}
        {isOpen && action}
      </header>
      {isOpen && <div className={cn("px-2 pb-2", bodyClassName)}>{children}</div>}
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
