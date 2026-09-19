import { cn } from "@/lib/cn";

interface ProgressBarProps {
  /** 0~100 */
  value: number;
  label: string;
  className?: string;
}

export function ProgressBar({ value, label, className }: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cn("h-2 w-full overflow-hidden rounded-full bg-gray-100", className)}
    >
      <div
        className="h-full rounded-full bg-blue-600 transition-[width] duration-500"
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
