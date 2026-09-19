"use client";

import { memo } from "react";
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
}

export function ArtifactList({ artifacts, selectedId, onSelect }: ArtifactListProps) {
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
  return (
    <ul className="space-y-0.5">
      {artifacts.map((artifact) => (
        <ArtifactListItem
          key={artifact.id}
          artifact={artifact}
          selected={artifact.id === selectedId}
          onSelect={onSelect}
        />
      ))}
    </ul>
  );
}
