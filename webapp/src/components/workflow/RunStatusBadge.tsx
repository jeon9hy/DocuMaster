import { RUN_STATUS } from "@/constants/status";
import type { RunStatus } from "@/types";
import { StatusBadge } from "../ui/Badge";

/** 진행률과 별개인 실행 상태(진행 중·입력 필요·중지 요청됨·오류·완료). 설명은 툴팁으로. */
export function RunStatusBadge({ status }: { status: RunStatus }) {
  const meta = RUN_STATUS[status];
  return (
    <span title={meta.hint} aria-label={`실행 상태: ${meta.label}. ${meta.hint}`}>
      <StatusBadge meta={meta} />
    </span>
  );
}
