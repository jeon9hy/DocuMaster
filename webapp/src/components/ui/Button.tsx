import type { ButtonHTMLAttributes } from "react";
import type { LucideIcon } from "lucide-react";
import { Button as WdsButton, IconButton as WdsIconButton, TextButton } from "@wanteddev/wds";
import { cn } from "@/lib/cn";

/*
 * Montage(원티드 디자인 시스템) 버튼을 앱의 이름으로 감싼 것. 화면 코드는 이 API만 안다.
 * primary = solid·primary · secondary = outlined·assistive · ghost = TextButton · danger = outlined + 빨간 글자
 */
type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md";

interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "color"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: LucideIcon;
}

export function Button({
  variant = "secondary",
  size = "md",
  icon: Icon,
  className,
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  const leadingContent = Icon && <Icon className="size-4" aria-hidden />;
  const wdsSize = size === "sm" ? "small" : "medium";

  if (variant === "ghost") {
    return (
      <TextButton
        type={type}
        color="assistive"
        size={wdsSize}
        leadingContent={leadingContent}
        className={cn("shrink-0", className)}
        {...rest}
      >
        {children}
      </TextButton>
    );
  }

  return (
    <WdsButton
      type={type}
      variant={variant === "primary" ? "solid" : "outlined"}
      color={variant === "primary" ? "primary" : "assistive"}
      size={wdsSize}
      leadingContent={leadingContent}
      sx={variant === "danger" ? (theme) => ({ color: theme.semantic.status.negative }) : undefined}
      className={cn("shrink-0", className)}
      {...rest}
    >
      {children}
    </WdsButton>
  );
}

interface IconButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "color"> {
  icon: LucideIcon;
  label: string;
  /** normal = 아이콘만(눌렀을 때 둥근 반응) · outlined = 테두리 있는 네모 버튼 */
  variant?: "normal" | "outlined";
  tone?: "default" | "primary";
}

/**
 * 아이콘만 있는 버튼. label은 스크린리더와 툴팁에 쓴다.
 * normal은 Montage IconButton(아이콘 크기만큼, 반응 영역 +16px)을 36px 칸 가운데에 둔다 — className은 그 칸에 붙는다.
 */
export function IconButton({
  icon: Icon,
  label,
  variant = "normal",
  tone = "default",
  className,
  type = "button",
  ...rest
}: IconButtonProps) {
  const color = tone === "primary" ? "semantic.primary.normal" : "semantic.label.alternative";

  if (variant === "outlined") {
    return (
      <WdsIconButton
        type={type}
        variant="outlined"
        size="medium"
        color={color}
        aria-label={label}
        title={label}
        className={cn("shrink-0", className)}
        {...rest}
      >
        <Icon aria-hidden />
      </WdsIconButton>
    );
  }

  return (
    <span className={cn("inline-flex size-9 shrink-0 items-center justify-center", className)}>
      <WdsIconButton type={type} size={18} color={color} aria-label={label} title={label} {...rest}>
        <Icon aria-hidden />
      </WdsIconButton>
    </span>
  );
}
