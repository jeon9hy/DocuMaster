import type { SelectHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
}

/** 브라우저 기본 select에 모양만 입힌 것. 접근성과 키보드 조작을 그대로 얻는다. */
export function Select({ label, className, children, ...rest }: SelectProps) {
  return (
    <div className={cn("relative", className)}>
      <select
        aria-label={label}
        className="h-8 w-full cursor-pointer appearance-none rounded-lg border border-line bg-white pr-7 pl-2.5 text-[13px] text-gray-700 hover:border-gray-300 focus:border-blue-500 focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-400"
        {...rest}
      >
        {children}
      </select>
      <ChevronDown
        className="pointer-events-none absolute top-1/2 right-2 size-3.5 -translate-y-1/2 text-gray-400"
        aria-hidden
      />
    </div>
  );
}
