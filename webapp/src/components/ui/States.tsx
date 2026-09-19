import type { ReactNode } from "react";
import { AlertCircle, Loader2, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "./Button";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

/** 빈 목록 · 준비 중 화면 */
export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-2 px-6 py-10 text-center", className)}>
      <span className="flex size-10 items-center justify-center rounded-full bg-gray-100 text-gray-400">
        <Icon className="size-5" aria-hidden />
      </span>
      <p className="text-sm font-medium text-gray-700">{title}</p>
      {description && <p className="max-w-sm text-[13px] text-gray-500">{description}</p>}
      {action}
    </div>
  );
}

export function LoadingState({ label = "불러오는 중…", className }: { label?: string; className?: string }) {
  return (
    <div className={cn("flex items-center justify-center gap-2 py-10 text-sm text-gray-500", className)}>
      <Loader2 className="size-4 animate-spin" aria-hidden />
      {label}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
  className,
}: {
  message: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <EmptyState
      icon={AlertCircle}
      title={message}
      className={className}
      action={
        onRetry && (
          <Button size="sm" onClick={onRetry}>
            다시 시도
          </Button>
        )
      }
    />
  );
}
