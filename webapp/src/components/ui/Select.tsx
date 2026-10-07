import { Option, Select as WdsSelect } from "@wanteddev/wds";
import { cn } from "@/lib/cn";

interface SelectProps {
  label: string;
  value: string;
  options: readonly { value: string; label: string }[];
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
}

/** Montage Select(펼침 메뉴). 좁은 줄에 놓는 용도라 높이를 낮춘다. 너비는 className(flex 비율)으로 정한다. */
export function Select({ label, value, options, onChange, disabled, className }: SelectProps) {
  return (
    <div className={cn("min-w-0", className)}>
      <WdsSelect
        aria-label={label}
        width="100%"
        height={36}
        value={value}
        disabled={disabled}
        onChange={onChange}
      >
        {options.map((option) => (
          <Option key={option.value} value={option.value}>
            {option.label}
          </Option>
        ))}
      </WdsSelect>
    </div>
  );
}
