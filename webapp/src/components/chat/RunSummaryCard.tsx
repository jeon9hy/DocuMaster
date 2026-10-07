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
      <dt className="text-[11px] text-label-alternative">{label}</dt>
      <dd className="mt-0.5 text-sm font-semibold text-label">{children}</dd>
    </div>
  );
}

interface RunSummaryCardProps {
  projectId: string;
  summary: RunSummary;
  /** 최종 PDF 전부(여러 부면 줄마다 따로 연다) */
  finalArtifacts: Artifact[];
  createdAt: string;
  onSelectArtifact: (artifactId: string) => void;
}

/** 완료 카드: 최종본 · 판정 · REMOVE/CAUTION 수 · 걸린 시간 · 비용 · 모델을 한곳에. 값은 백엔드가 모은 것만 쓴다. */
export function RunSummaryCard({ projectId, summary, finalArtifacts, createdAt, onSelectArtifact }: RunSummaryCardProps) {
  const [openId, setOpenId] = useState<string | null>(null);
  const close = useCallback(() => setOpenId(null), []);
  const opened = finalArtifacts.find((artifact) => artifact.id === openId);
  const mode = useAppState().workspace?.project.mode ?? "auto";
  const verdict = summary.verdict ? VERDICT_STATUS[summary.verdict] : null;
  const models = AGENT_IDS.filter((id) => summary.models?.[id] && !isRestingInMode(id, mode));

  return (
    <section className="ml-[52px] max-w-[560px] rounded-xl border border-positive/28 bg-surface px-4 py-3" aria-label="실행 결과 요약">
      <header className="flex items-center gap-2">
        <CheckCircle2 className="size-4 text-positive-fg" aria-hidden />
        <h3 className="flex-1 text-sm font-semibold text-label">워크플로우 완료</h3>
        <time className="text-[11px] text-label-alternative" dateTime={createdAt}>
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
            <span className="text-label-alternative">—</span>
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
        <p className="mt-2.5 text-xs leading-relaxed text-label-alternative">
          {models.map((id, index) => (
            <span key={id}>
              {index > 0 && " · "}
              <span className="text-label-neutral">{getAgentProfile(id).name}</span> {getModelLabel({ modelId: summary.models![id]! })}
            </span>
          ))}
        </p>
      )}

      {finalArtifacts.length > 0 && (
        <ul className="mt-3 flex flex-col gap-2 border-t border-line pt-3">
          {finalArtifacts.map((artifact) => (
            <li key={artifact.id} className="flex items-center gap-2">
              <FileText className="size-4 shrink-0 text-label-assistive" aria-hidden />
              <span className="min-w-0 flex-1 truncate text-[13px] text-label-neutral" title={artifact.name}>
                {artifact.name}
              </span>
              <Button
                size="sm"
                variant="primary"
                onClick={() => {
                  onSelectArtifact(artifact.id);
                  setOpenId(artifact.id);
                }}
              >
                {finalArtifacts.length > 1 ? "열기" : "최종 PDF 열기"}
              </Button>
            </li>
          ))}
        </ul>
      )}
      {opened && <ArtifactPreviewModal projectId={projectId} artifact={opened} onClose={close} />}
    </section>
  );
}
