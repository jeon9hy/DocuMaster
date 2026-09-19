"use client";

import { useAppActions, useAppState, useWorkspace } from "@/state/WorkspaceProvider";
import { ArtifactList } from "../artifact/ArtifactList";
import { ArtifactPreview } from "../artifact/ArtifactPreview";
import { Panel } from "../ui/Panel";
import { ViewContainer, ViewHeader } from "./ViewHeader";

/** 작업물 전체 목록 + 큰 미리보기. 모바일 「작업물」 탭에서도 쓴다. */
export function ArtifactsView() {
  const workspace = useWorkspace();
  const { selectedArtifactId } = useAppState();
  const { selectArtifact } = useAppActions();
  const selected = workspace.artifacts.find((artifact) => artifact.id === selectedArtifactId) ?? null;

  return (
    <ViewContainer>
      <ViewHeader title="작업물" description="단계마다 만들어진 파일입니다. 최종본은 최종검수를 통과한 뒤 생깁니다." />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <Panel title={`전체 (${workspace.artifacts.length})`}>
          <ArtifactList
            artifacts={workspace.artifacts}
            selectedId={selectedArtifactId}
            onSelect={selectArtifact}
          />
        </Panel>
        <Panel title={selected ? selected.name : "미리보기"}>
          <ArtifactPreview projectId={workspace.project.id} artifact={selected} tall />
        </Panel>
      </div>
    </ViewContainer>
  );
}
