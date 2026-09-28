"use client";

import { useCallback, useState, type ReactNode } from "react";
import { CheckCircle2, FileText } from "lucide-react";
import { AGENT_IDS, getAgentProfile } from "@/constants/agents";
import { VERDICT_STATUS } from "@/constants/status";
import { isRestingInMode } from "@/lib/agents";
import { formatDuration, formatTime } from "@/lib/format";
import { getModelLabel } from "@/lib/models";
import { useAppState } from "@/state/WorkspaceProvider";
import type { Artifact, RunSummary } from "@/types";
import { ArtifactPreviewModal } from "../artifact/ArtifactPreview";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

function Stat({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] text-gray-500">{label}</dt>
      <dd className="mt-0.5 text-sm font-semibold text-gray-900">{children}</dd>
    </div>
  );
}

interface RunSummaryCardProps {
  projectId: string;
  summary: RunSummary;
  finalArtifact?: Artifact;
  createdAt: string;
  onSelectArtifact: (artifactId: string) => void;
}

/** 완료 카드: 최종본 · 판정 · REMOVE/CAUTION 수 · 걸린 시간 · 비용 · 모델을 한곳에. 값은 백엔드가 모은 것만 쓴다. */
export function RunSummaryCard({ projectId, summary, finalArtifact, createdAt, onSelectArtifact }: RunSummaryCardProps) {
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);
  const mode = useAppState().workspace?.project.mode ?? "auto";
  const verdict = summary.verdict ? VERDICT_STATUS[summary.verdict] : null;
  const models = AGENT_IDS.filter((id) => summary.models?.[id] && !isRestingInMode(id, mode));

  return (
    <section className="ml-[52px] max-w-[560px] rounded-xl border border-emerald-200 bg-white px-4 py-3" aria-label="실행 결과 요약">
      <header className="flex items-center gap-2">
        <CheckCircle2 className="size-4 text-emerald-500" aria-hidden />
        <h3 className="flex-1 text-sm font-semibold text-gray-900">워크플로우 완료</h3>
        <time className="text-[11px] text-gray-400" dateTime={createdAt}>
          {formatTime(createdAt)}
        </time>
      </header>

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5 sm:grid-cols-4">
        <Stat label="검증 판정">
          {verdict ? (
            <Badge variant={verdict.variant} dot>
              {verdict.label}
            </Badge>
          ) : (
            <span className="text-gray-400">—</span>
          )}
        </Stat>
        <Stat label="REMOVE · CAUTION">
          {summary.removeCount ?? "—"} · {summary.cautionCount ?? "—"}
        </Stat>
        <Stat label="걸린 시간">
          {summary.durationSeconds !== undefined ? formatDuration(summary.durationSeconds) : "—"}
        </Stat>
        <Stat label="비용">{typeof summary.costUsd === "number" ? `$${summary.costUsd.toFixed(2)}` : "—"}</Stat>
      </dl>

      {models.length > 0 && (
        <p className="mt-2.5 text-xs leading-relaxed text-gray-500">
          {models.map((id, index) => (
            <span key={id}>
              {index > 0 && " · "}
              <span className="text-gray-700">{getAgentProfile(id).name}</span> {getModelLabel({ modelId: summary.models![id]! })}
            </span>
          ))}
        </p>
      )}

      {finalArtifact && (
        <div className="mt-3 flex items-center gap-2 border-t border-line pt-3">
          <FileText className="size-4 shrink-0 text-gray-400" aria-hidden />
          <span className="min-w-0 flex-1 truncate text-[13px] text-gray-700">{finalArtifact.name}</span>
          <Button
            size="sm"
            variant="primary"
            onClick={() => {
              onSelectArtifact(finalArtifact.id);
              setOpen(true);
            }}
          >
            최종 PDF 열기
          </Button>
        </div>
      )}
      {open && finalArtifact && <ArtifactPreviewModal projectId={projectId} artifact={finalArtifact} onClose={close} />}
    </section>
  );
}
