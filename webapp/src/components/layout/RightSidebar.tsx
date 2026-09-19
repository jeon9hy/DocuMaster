"use client";

import { useAppActions, useAppState, useWorkspace } from "@/state/WorkspaceProvider";
import { ArtifactList } from "../artifact/ArtifactList";
import { ArtifactPreview } from "../artifact/ArtifactPreview";
import { Button } from "../ui/Button";
import { Panel } from "../ui/Panel";

/** 결과물 중심: 작업물 목록 → 미리보기. 모델 설정은 설정 화면에서만 한다. */
export function RightSidebar() {
  const workspace = useWorkspace();
  const { selectedArtifactId } = useAppState();
  const { selectArtifact, setView } = useAppActions();
  const selected = workspace.artifacts.find((artifact) => artifact.id === selectedArtifactId) ?? null;

  return (
    <div className="flex flex-col gap-3 p-3">
      <Panel
        title={`작업물 (${workspace.artifacts.length})`}
        action={
          <Button size="sm" variant="ghost" onClick={() => setView("artifacts")} className="h-7 text-blue-600">
            전체 보기
          </Button>
        }
      >
        <div className="max-h-72 overflow-y-auto">
          <ArtifactList
            artifacts={workspace.artifacts}
            selectedId={selectedArtifactId}
            onSelect={selectArtifact}
            collapseInternal
          />
        </div>
      </Panel>

      <Panel title={selected ? `미리보기 · ${selected.name}` : "미리보기"}>
        <ArtifactPreview projectId={workspace.project.id} artifact={selected} />
      </Panel>
    </div>
  );
}
