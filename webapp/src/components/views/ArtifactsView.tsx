"use client";

import { useCallback, useMemo, useState } from "react";
import { useServiceData } from "@/hooks/useServiceData";
import { splitFinalArtifacts } from "@/lib/library";
import { workspaceService } from "@/services";
import { useAppActions, useAppState, useIsOwner, useWorkspace } from "@/state/WorkspaceProvider";
import type { LibraryDocument } from "@/types";
import { ArtifactList } from "../artifact/ArtifactList";
import { ArtifactPreview } from "../artifact/ArtifactPreview";
import { FinalArtifactsBlock } from "../artifact/FinalArtifactsBlock";
import { ReviseModal } from "../artifact/ReviseModal";
import { ProjectInfoCard } from "../project/ProjectInfoCard";
import { Panel } from "../ui/Panel";
import { ViewContainer } from "./ViewHeader";

/** 프로젝트 정보 → 최종본(있을 때만) → 나머지 작업물 + 큰 미리보기. 모바일 「작업물」 탭에서도 쓴다. */
export function ArtifactsView() {
  const workspace = useWorkspace();
  const { selectedArtifactId } = useAppState();
  const { selectArtifact } = useAppActions();
  const { finals, previous, others } = useMemo(() => splitFinalArtifacts(workspace.artifacts), [workspace.artifacts]);
  const selected = workspace.artifacts.find((artifact) => artifact.id === selectedArtifactId) ?? null;

  // 유형·날짜·원문 요청은 라이브러리가 최종본 폴더에서 읽는다 — 최종본이 생기면 다시 받는다
  const finalCount = finals.length;
  const load = useCallback(
    () => (finalCount > 0 ? workspaceService.listLibrary() : Promise.resolve<LibraryDocument[]>([])),
    [finalCount],
  );
  const { state } = useServiceData(load);
  const doc =
    state.status === "success" ? (state.data.find((item) => item.projectId === workspace.project.id) ?? null) : null;
  const mode = doc?.mode ?? workspace.project.mode;

  const isOwner = useIsOwner();
  const [revising, setRevising] = useState(false);
  const busy = ["running", "awaitingInput", "stopping"].includes(workspace.runStatus);
  const reviseBlockedReason = !isOwner
    ? "로그인하면 첨삭할 수 있습니다"
    : busy
      ? "실행이 끝난 뒤 첨삭할 수 있습니다"
      : null;

  return (
    <ViewContainer>
      <ProjectInfoCard project={workspace.project} doc={doc} />
      {finals.length > 0 && (
        <FinalArtifactsBlock
          finals={finals}
          previous={previous}
          selectedId={selectedArtifactId}
          onSelect={selectArtifact}
          revisable={mode === "document"}
          reviseBlockedReason={reviseBlockedReason}
          onRevise={() => setRevising(true)}
        />
      )}
      <div className="grid gap-4 @3xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <Panel title={`작업물 (${others.length})`}>
          <ArtifactList artifacts={others} selectedId={selectedArtifactId} onSelect={selectArtifact} />
        </Panel>
        <Panel
          title={selected ? selected.name : "미리보기"}
          className="@3xl:flex @3xl:flex-col"
          bodyClassName="@3xl:flex @3xl:flex-1 @3xl:flex-col"
        >
          <ArtifactPreview projectId={workspace.project.id} artifact={selected} tall />
        </Panel>
      </div>
      {revising && <ReviseModal open onClose={() => setRevising(false)} />}
    </ViewContainer>
  );
}
