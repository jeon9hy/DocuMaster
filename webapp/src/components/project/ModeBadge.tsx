import type { ProjectModeChoice } from "@/types";
import { PROJECT_MODE_LABEL } from "@/constants/navigation";
import { Badge } from "../ui/Badge";

/** 프로젝트 형식 배지(문서 · 발표). 아직 판정되지 않은 auto는 형식이 아니므로 아무것도 그리지 않는다. */
export function ModeBadge({
  mode,
  variant,
  className,
}: {
  mode: ProjectModeChoice;
  variant?: "neutral" | "primary";
  className?: string;
}) {
  if (mode === "auto") return null;
  return (
    <Badge variant={variant} className={className}>
      {PROJECT_MODE_LABEL[mode]}
    </Badge>
  );
}
