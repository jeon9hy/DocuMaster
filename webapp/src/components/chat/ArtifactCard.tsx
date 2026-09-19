"use client";

import { useCallback, useState } from "react";
import { Eye } from "lucide-react";
import { getAgentProfile } from "@/constants/agents";
import type { Artifact } from "@/types";
import { ArtifactIcon } from "../artifact/ArtifactIcon";
import { ArtifactPreviewModal } from "../artifact/ArtifactPreview";
import { Button } from "../ui/Button";

interface ArtifactCardProps {
  projectId: string;
  artifact: Artifact;
  onSelect: (artifactId: string) => void;
}

/**
 * 피드 안의 "작업물 생성" 카드. 「미리보기」를 누르면 오른쪽 패널의 선택도 이 파일로 바뀌고,
 * 오른쪽 패널이 접힌 좁은 화면에서도 보이도록 모달로 연다.
 */
export function ArtifactCard({ projectId, artifact, onSelect }: ArtifactCardProps) {
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);

  return (
    <div className="ml-[52px] flex max-w-[480px] items-center gap-3 rounded-xl border border-line bg-white px-3 py-2.5">
      <ArtifactIcon fileType={artifact.fileType} className="size-9" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-gray-900">{artifact.name}</p>
        <p className="truncate text-xs text-gray-500">
          {getAgentProfile(artifact.agentId).name} · {artifact.summary}
        </p>
      </div>
      <Button
        size="sm"
        variant="ghost"
        icon={Eye}
        onClick={() => {
          onSelect(artifact.id);
          setOpen(true);
        }}
      >
        미리보기
      </Button>
      {open && <ArtifactPreviewModal projectId={projectId} artifact={artifact} onClose={close} />}
    </div>
  );
}
