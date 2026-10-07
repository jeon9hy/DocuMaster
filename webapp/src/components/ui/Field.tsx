import type { InputHTMLAttributes, TextareaHTMLAttributes } from "react";
import { SearchField as WdsSearchField, TextArea as WdsTextArea, TextField as WdsTextField } from "@wanteddev/wds";

/*
 * Montage 입력창을 일반 input·textarea 속성 그대로 받도록 감싼 것. 너비는 늘 100%(부모 칸을 따른다).
 * 값은 부모가 쥔다(value + onChange).
 */
type FieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "size" | "width" | "height" | "color" | "onReset">;

export function TextField({ height = 44, invalid, ...rest }: FieldProps & { height?: number; invalid?: boolean }) {
  return <WdsTextField width="100%" height={height} invalid={invalid} {...rest} />;
}

type TextAreaFieldProps = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "value" | "color" | "onReset"> & {
  value: string;
  invalid?: boolean;
  minRows?: number;
  maxRows?: number;
};

export function TextArea({ invalid, ...rest }: TextAreaFieldProps) {
  return <WdsTextArea width="100%" invalid={invalid} {...rest} />;
}

/** 검색창. 지우기(x) 버튼은 Montage가 그리고, 눌리면 onClear를 부른다. */
export function SearchField({ onClear, ...rest }: FieldProps & { onClear: () => void }) {
  return <WdsSearchField width="100%" size="medium" onReset={() => onClear()} {...rest} />;
}
