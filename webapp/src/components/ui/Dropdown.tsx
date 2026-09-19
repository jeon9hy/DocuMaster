"use client";

import { useCallback, useRef, useState, type ReactNode } from "react";
import { useDismiss } from "@/hooks/useDismiss";
import { cn } from "@/lib/cn";

interface DropdownProps {
  /** 트리거를 그리는 함수. 열기/닫기 토글과 현재 상태를 받는다. */
  trigger: (props: { open: boolean; toggle: () => void }) => ReactNode;
  /** 메뉴 내용. close를 불러 선택 후 닫는다. */
  children: (close: () => void) => ReactNode;
  align?: "left" | "right";
  placement?: "bottom" | "top";
  className?: string;
}

export function Dropdown({
  trigger,
  children,
  align = "left",
  placement = "bottom",
  className,
}: DropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const close = useCallback(() => setOpen(false), []);
  const toggle = useCallback(() => setOpen((value) => !value), []);
  useDismiss(open, close, ref);

  return (
    <div ref={ref} className="relative">
      {trigger({ open, toggle })}
      {open && (
        <div
          role="menu"
          className={cn(
            "absolute z-30 min-w-56 rounded-xl border border-line bg-white p-1.5 shadow-lg",
            align === "left" ? "left-0" : "right-0",
            placement === "bottom" ? "top-full mt-1.5" : "bottom-full mb-1.5",
            className,
          )}
        >
          {children(close)}
        </div>
      )}
    </div>
  );
}

interface DropdownItemProps {
  onSelect: () => void;
  active?: boolean;
  children: ReactNode;
}

export function DropdownItem({ onSelect, active = false, children }: DropdownItemProps) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onSelect}
      className={cn(
        "flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors",
        active ? "bg-blue-50 text-blue-700" : "text-gray-700 hover:bg-gray-50",
      )}
    >
      {children}
    </button>
  );
}
