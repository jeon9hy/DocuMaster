import type { ReactNode } from "react";
import { ContentBadge, type ThemeColorsToken } from "@wanteddev/wds";
import type { BadgeVariant, StatusMeta } from "@/constants/status";
import { cn } from "@/lib/cn";

/** 상태 → Montage ContentBadge 색. neutral만 회색 바탕, 나머지는 그 색을 옅게 깐다. */
const ACCENT: Record<Exclude<BadgeVariant, "neutral">, ThemeColorsToken> = {
  primary: "semantic.primary.normal",
  success: "semantic.accent.foreground.green",
  warning: "semantic.accent.foreground.orange",
  danger: "semantic.accent.foreground.red",
  rest: "semantic.accent.foreground.violet",
};

interface BadgeProps {
  variant?: BadgeVariant;
  dot?: boolean;
  className?: string;
  children: ReactNode;
}

export function Badge({ variant = "neutral", dot = false, className, children }: BadgeProps) {
  return (
    <ContentBadge
      size="small"
      color={variant === "neutral" ? "neutral" : "accent"}
      accentColor={variant === "neutral" ? undefined : ACCENT[variant]}
      leadingContent={dot ? <span className="size-1.5 rounded-full bg-current" aria-hidden /> : undefined}
      className={cn("shrink-0 whitespace-nowrap", className)}
    >
      {children}
    </ContentBadge>
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
