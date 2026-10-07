import type { InputHTMLAttributes } from "react";
import { TextField } from "../ui/Field";

interface PinInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange" | "size" | "width" | "height" | "color" | "onReset"> {
  label: string;
  value: string;
  onChange: (value: string) => void;
}

/** 숫자 6자리 PIN 입력. 숫자 외 글자는 받지 않는다. 정답 확인은 백엔드만 한다. */
export function PinInput({ label, value, onChange, ...rest }: PinInputProps) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[13px] font-medium text-label-neutral">{label}</span>
      <TextField
        type="password"
        inputMode="numeric"
        autoComplete="current-password"
        maxLength={6}
        value={value}
        onChange={(event) => onChange(event.target.value.replace(/\D/g, "").slice(0, 6))}
        className="text-center tracking-[0.6em]"
        {...rest}
      />
    </label>
  );
}
