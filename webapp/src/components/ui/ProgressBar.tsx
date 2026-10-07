import { ProgressIndicator } from "@wanteddev/wds";
import { cn } from "@/lib/cn";

interface ProgressBarProps {
  /** 0~100 */
  value: number;
  label: string;
  className?: string;
  /** thick = 두 배 굵기(설정 화면의 사용량) */
  size?: "default" | "thick";
}

/** Montage ProgressIndicator. 기본 2px 선을 앱 크기(8·16px)의 둥근 막대로 키운다. */
export function ProgressBar({ value, label, className, size = "default" }: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <ProgressIndicator
      percent={clamped}
      aria-label={label}
      sx={{ height: size === "thick" ? 16 : 8, borderRadius: 9999 }}
      className={cn("w-full", className)}
    />
  );
}
