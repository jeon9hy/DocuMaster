import { AlertCircle, Check } from "lucide-react";
import { cn } from "@/lib/cn";
import type { StageStatus } from "@/types";

interface StageStatusIconProps {
  status: StageStatus;
  /** 대기·진행 중일 때 원 안에 보일 번호. 없으면 빈 원 */
  index?: number;
  size?: "sm" | "md";
}

/** 단계 상태 표시 원: 완료 ✓ · 진행 중(파란 테두리) · 대기(회색) · 오류 ! */
export function StageStatusIcon({ status, index, size = "md" }: StageStatusIconProps) {
  const box = size === "md" ? "size-7 text-[13px]" : "size-5 text-[11px]";
  const icon = size === "md" ? "size-4" : "size-3";

  if (status === "completed") {
    return (
      <span className={cn("flex shrink-0 items-center justify-center rounded-full bg-emerald-500 text-white", box)}>
        <Check className={icon} strokeWidth={3} aria-hidden />
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className={cn("flex shrink-0 items-center justify-center rounded-full bg-red-500 text-white", box)}>
        <AlertCircle className={icon} aria-hidden />
      </span>
    );
  }
  return (
    <span
      className={cn(
        "flex shrink-0 items-center justify-center rounded-full font-semibold",
        box,
        status === "running"
          ? "bg-blue-600 text-white ring-4 ring-blue-100"
          : "border border-gray-300 bg-white text-gray-400",
      )}
    >
      {index}
    </span>
  );
}
