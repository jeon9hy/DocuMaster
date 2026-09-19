/** 조건부 className 합치기. 의존성(clsx 등)을 늘리지 않으려고 직접 둔다. */
export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}
