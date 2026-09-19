import { cn } from "@/lib/cn";

interface SegmentedControlProps<T extends string> {
  label: string;
  options: readonly { id: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}

/** 가로 탭 선택. 모달 안의 입력 방식 전환 등에 쓴다. */
export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
}: SegmentedControlProps<T>) {
  return (
    <div role="tablist" aria-label={label} className="flex gap-1 rounded-lg bg-gray-100 p-1">
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          role="tab"
          aria-selected={option.id === value}
          onClick={() => onChange(option.id)}
          className={cn(
            "flex-1 rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors",
            option.id === value ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
