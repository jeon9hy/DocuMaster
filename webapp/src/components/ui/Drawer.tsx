"use client";

import type { ReactNode } from "react";
import { useDismiss } from "@/hooks/useDismiss";
import { cn } from "@/lib/cn";

interface DrawerProps {
  open: boolean;
  side: "left" | "right";
  label: string;
  onClose: () => void;
  children: ReactNode;
}

/** 좁은 화면에서 접힌 사이드바를 옆에서 밀어 여는 패널 */
export function Drawer({ open, side, label, onClose, children }: DrawerProps) {
  useDismiss(open, onClose);
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-gray-900/30" onClick={onClose} aria-hidden />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={label}
        className={cn(
          "absolute top-0 bottom-0 flex w-[320px] max-w-[88vw] flex-col overflow-y-auto bg-canvas shadow-lg",
          side === "left" ? "left-0" : "right-0",
        )}
      >
        {children}
      </aside>
    </div>
  );
}
