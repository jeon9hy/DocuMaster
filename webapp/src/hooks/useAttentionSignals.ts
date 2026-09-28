import { useEffect, useRef } from "react";
import { BRAND } from "@/constants/brand";
import { attentionTitle, notify } from "@/lib/attention";
import { RUN_STATUS } from "@/constants/status";
import type { ProjectWorkspace } from "@/types";

/**
 * 긴 실행 중 다른 창을 보고 있어도 놓치지 않게:
 * - 사용자 확인이 필요하면 탭 제목에 「● 확인 필요」
 * - 이 화면이 열려 있는 동안 새로 생긴 확인 요청·완료·오류는 브라우저 알림(권한이 있을 때만)
 * 화면을 연 시점에 이미 있던 요청은 알림을 다시 띄우지 않는다(제목 표시만).
 */
export function useAttentionSignals(workspace: ProjectWorkspace | null) {
  const needsInput = (workspace?.pendingInputs.length ?? 0) > 0;
  const seen = useRef<{ projectId: string; prompts: Set<string>; runStatus: string } | null>(null);

  useEffect(() => {
    document.title = attentionTitle(BRAND.name, needsInput);
  }, [needsInput]);

  useEffect(() => {
    if (!workspace) return;
    const { project, pendingInputs, runStatus } = workspace;
    const previous = seen.current;
    const prompts = new Set(pendingInputs.map((request) => request.promptId));
    seen.current = { projectId: project.id, prompts, runStatus };
    if (!previous || previous.projectId !== project.id) return; // 처음 연 화면·프로젝트 전환은 알리지 않는다

    for (const request of pendingInputs) {
      if (!previous.prompts.has(request.promptId)) {
        notify(`${project.name} · 확인 필요`, request.title, request.promptId);
      }
    }
    if (runStatus !== previous.runStatus && (runStatus === "completed" || runStatus === "failed")) {
      notify(`${project.name} · ${RUN_STATUS[runStatus].label}`, RUN_STATUS[runStatus].hint, `${project.id}:${runStatus}`);
    }
  }, [workspace]);
}
