"use client";

import { useCallback, useState, type ReactNode } from "react";
import { Popover, PopoverContent, PopoverTrigger } from "@wanteddev/wds";
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

/**
 * Montage Popover 위에 얹은 펼침 메뉴. 바깥 누르기·Esc 닫기·초점·위치 계산(화면 밖으로 안 나감)은 Montage가 한다.
 * 안쪽 여백은 DropdownItem이 줄 수 있게 6px로 줄였다.
 */
export function Dropdown({ trigger, children, align = "left", placement = "bottom", className }: DropdownProps) {
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);
  const toggle = useCallback(() => setOpen(!open), [open]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger>
        <div className="relative">{trigger({ open, toggle })}</div>
      </PopoverTrigger>
      <PopoverContent
        variant="custom"
        position={`${placement}-${align === "left" ? "start" : "end"}`}
        offset={6}
        sx={{ padding: "6px", minWidth: 224 }}
        className={cn("scrollbar-thin max-h-[70vh] overflow-y-auto", className)}
        role="menu"
      >
        {/* Montage 팝오버 안쪽은 가로 배치라 세로로 쌓는 칸을 하나 둔다 */}
        <div className="flex w-full min-w-0 flex-col">{children(close)}</div>
      </PopoverContent>
    </Popover>
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
        active ? "bg-primary/8 text-primary-strong" : "text-label-neutral hover:bg-fill",
      )}
    >
      {children}
    </button>
  );
}
