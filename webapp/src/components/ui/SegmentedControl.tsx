import { SegmentedControl as WdsSegmentedControl, SegmentedControlItem } from "@wanteddev/wds";

interface SegmentedControlProps<T extends string> {
  label: string;
  options: readonly { id: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}

/** 가로 탭 선택(Montage SegmentedControl). 모달 안의 입력 방식 전환 등에 쓴다. */
export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
}: SegmentedControlProps<T>) {
  return (
    <WdsSegmentedControl
      aria-label={label}
      size="small"
      value={value}
      onValueChange={(next) => onChange(next as T)}
    >
      {options.map((option) => (
        <SegmentedControlItem key={option.id} value={option.id}>
          {option.label}
        </SegmentedControlItem>
      ))}
    </WdsSegmentedControl>
  );
}
