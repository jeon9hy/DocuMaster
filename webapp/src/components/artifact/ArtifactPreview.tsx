"use client";

import { useCallback, useState } from "react";
import { Clock, Maximize2, MousePointerClick } from "lucide-react";
import { useArtifactContent, type ContentResult } from "@/hooks/useArtifactContent";
import { cn } from "@/lib/cn";
import type { Artifact } from "@/types";
import { IconButton } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { EmptyState, ErrorState, LoadingState } from "../ui/States";
import { ArtifactContentView } from "./ArtifactContentView";

function PreviewBody({ result, large = false }: { result: ContentResult; large?: boolean }) {
  switch (result.status) {
    case "loading":
      return <LoadingState label="미리보기를 불러오는 중…" />;
    case "empty":
      return (
        <EmptyState
          icon={Clock}
          title="아직 생성되지 않았습니다"
          description="이 단계가 끝나면 미리보기가 나타납니다."
          className="py-6"
        />
      );
    case "error":
      return <ErrorState message={result.message} className="py-6" />;
    case "success":
      return <ArtifactContentView content={result.content} large={large} />;
  }
}

interface ArtifactPreviewModalProps {
  projectId: string;
  artifact: Artifact;
  onClose: () => void;
}

/** 작업물을 크게 보는 모달. 열려 있을 때만 마운트해서 쓴다. */
export function ArtifactPreviewModal({ projectId, artifact, onClose }: ArtifactPreviewModalProps) {
  const result = useArtifactContent(projectId, artifact);
  return (
    <Modal open title={artifact.name} onClose={onClose} size="lg">
      <PreviewBody result={result} large />
    </Modal>
  );
}

interface ArtifactPreviewProps {
  projectId: string;
  artifact: Artifact | null;
  /** 작업물 화면처럼 넓은 곳에서 더 길게 보여 준다 */
  tall?: boolean;
}

/** 선택한 작업물의 미리보기. 확대 버튼을 누르면 모달로 크게 본다. */
export function ArtifactPreview({ projectId, artifact, tall = false }: ArtifactPreviewProps) {
  const result = useArtifactContent(projectId, artifact);
  const [expanded, setExpanded] = useState(false);
  const close = useCallback(() => setExpanded(false), []);

  if (!artifact) {
    return (
      <EmptyState icon={MousePointerClick} title="작업물을 선택하세요" className="py-6" />
    );
  }

  return (
    <>
      <div className="flex items-center justify-between gap-2 px-2 pb-2">
        <p className="truncate text-xs text-gray-500">{artifact.summary}</p>
        {result.status === "success" && (
          <IconButton
            icon={Maximize2}
            label="크게 보기"
            className="size-7"
            onClick={() => setExpanded(true)}
          />
        )}
      </div>
      <div
        className={cn(
          "overflow-y-auto rounded-lg border border-line bg-canvas/60 p-3",
          tall ? "max-h-[70vh]" : "max-h-72",
        )}
      >
        <PreviewBody result={result} />
      </div>
      {expanded && <ArtifactPreviewModal projectId={projectId} artifact={artifact} onClose={close} />}
    </>
  );
}
