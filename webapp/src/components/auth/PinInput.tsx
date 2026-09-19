import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface PinInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange"> {
  label: string;
  value: string;
  onChange: (value: string) => void;
}

/** 숫자 6자리 PIN 입력. 숫자 외 글자는 받지 않는다. 정답 확인은 백엔드만 한다. */
export function PinInput({ label, value, onChange, className, ...rest }: PinInputProps) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[13px] font-medium text-gray-700">{label}</span>
      <input
        type="password"
        inputMode="numeric"
        autoComplete="current-password"
        maxLength={6}
        value={value}
        onChange={(event) => onChange(event.target.value.replace(/\D/g, "").slice(0, 6))}
        className={cn(
          "h-11 w-full rounded-lg border border-line bg-white px-3 text-center text-lg tracking-[0.6em] text-gray-900 focus:border-blue-500 focus:outline-none",
          className,
        )}
        {...rest}
      />
    </label>
  );
}
