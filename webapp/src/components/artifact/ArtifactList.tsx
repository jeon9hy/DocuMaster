"use client";

import { memo, useState } from "react";
import { FileText } from "lucide-react";
import { getAgentProfile } from "@/constants/agents";
import { ARTIFACT_STATUS } from "@/constants/status";
import { cn } from "@/lib/cn";
import { formatTime } from "@/lib/format";
import type { Artifact } from "@/types";
import { StatusBadge } from "../ui/Badge";
import { EmptyState } from "../ui/States";
import { ArtifactIcon } from "./ArtifactIcon";

interface ArtifactListItemProps {
  artifact: Artifact;
  selected: boolean;
  onSelect: (artifactId: string) => void;
}

const ArtifactListItem = memo(function ArtifactListItem({
  artifact,
  selected,
  onSelect,
}: ArtifactListItemProps) {
  const meta =
    artifact.status === "pending"
      ? "아직 생성되지 않음"
      : `${getAgentProfile(artifact.agentId).name} · ${formatTime(artifact.updatedAt)}`;
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(artifact.id)}
        aria-current={selected}
        className={cn(
          "flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left transition-colors",
          selected ? "bg-blue-50/70" : "hover:bg-gray-50",
        )}
      >
        <ArtifactIcon fileType={artifact.fileType} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-gray-900">{artifact.name}</span>
          <span className="block truncate text-xs text-gray-500">{meta}</span>
        </span>
        <StatusBadge meta={ARTIFACT_STATUS[artifact.status]} dot={false} />
      </button>
    </li>
  );
});

interface ArtifactListProps {
  artifacts: Artifact[];
  selectedId: string | null;
  onSelect: (artifactId: string) => void;
  /** 내부 작업물(03·04·06·옛 버전 등)을 처음엔 숨기고 「내부 작업물 N개 보기」로 펼친다 */
  collapseInternal?: boolean;
}

export function ArtifactList({ artifacts, selectedId, onSelect, collapseInternal = false }: ArtifactListProps) {
  const [showInternal, setShowInternal] = useState(false);
  if (artifacts.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="아직 작업물이 없습니다"
        description="실행하면 단계마다 생긴 파일이 여기에 쌓입니다."
        className="py-6"
      />
    );
  }
  const internalCount = artifacts.filter((artifact) => artifact.visibility === "internal").length;
  const visible =
    collapseInternal && !showInternal
      ? artifacts.filter((artifact) => artifact.visibility !== "internal")
      : artifacts;
  return (
    <div>
      <ul className="space-y-0.5">
        {visible.map((artifact) => (
          <ArtifactListItem
            key={artifact.id}
            artifact={artifact}
            selected={artifact.id === selectedId}
            onSelect={onSelect}
          />
        ))}
      </ul>
      {collapseInternal && internalCount > 0 && (
        <button
          type="button"
          onClick={() => setShowInternal((value) => !value)}
          className="mt-1 px-2 text-xs font-medium text-blue-600 hover:underline"
        >
          {showInternal ? "주요 작업물만 보기" : `내부 작업물 ${internalCount}개 보기`}
        </button>
      )}
    </div>
  );
}
