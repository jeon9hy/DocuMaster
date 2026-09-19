import type { ReactNode } from "react";
import type { BadgeVariant, StatusMeta } from "@/constants/status";
import { cn } from "@/lib/cn";

const VARIANT_CLASS: Record<BadgeVariant, string> = {
  neutral: "bg-gray-100 text-gray-600",
  primary: "bg-blue-50 text-blue-700",
  success: "bg-emerald-50 text-emerald-700",
  warning: "bg-amber-50 text-amber-700",
  danger: "bg-red-50 text-red-700",
  rest: "bg-violet-50 text-violet-600",
};

const DOT_CLASS: Record<BadgeVariant, string> = {
  neutral: "bg-gray-400",
  primary: "bg-blue-500",
  success: "bg-emerald-500",
  warning: "bg-amber-500",
  danger: "bg-red-500",
  rest: "bg-violet-300",
};

interface BadgeProps {
  variant?: BadgeVariant;
  dot?: boolean;
  className?: string;
  children: ReactNode;
}

export function Badge({ variant = "neutral", dot = false, className, children }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        VARIANT_CLASS[variant],
        className,
      )}
    >
      {dot && <span className={cn("size-1.5 rounded-full", DOT_CLASS[variant])} />}
      {children}
    </span>
  );
}

/** constants/status.ts의 상태 정의를 그대로 배지로 */
export function StatusBadge({ meta, dot = true }: { meta: StatusMeta; dot?: boolean }) {
  return (
    <Badge variant={meta.variant} dot={dot}>
      {meta.label}
    </Badge>
  );
}
