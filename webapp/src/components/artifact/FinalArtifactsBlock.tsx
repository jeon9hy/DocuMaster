"use client";

import { BadgeCheck, PenLine } from "lucide-react";
import { cn } from "@/lib/cn";
import { formatTime } from "@/lib/format";
import type { Artifact } from "@/types";
import { Button } from "../ui/Button";
import { ArtifactIcon } from "./ArtifactIcon";

interface FinalArtifactsBlockProps {
  finals: Artifact[];
  selectedId: string | null;
  onSelect: (artifactId: string) => void;
  /** 첨삭은 문서 모드만(아냐가 DOC 전용) */
  revisable: boolean;
}

/** 최종검수를 통과한 파일만 따로 모은 맨 위 블록. 누르면 아래 미리보기에 연다. */
export function FinalArtifactsBlock({ finals, selectedId, onSelect, revisable }: FinalArtifactsBlockProps) {
  return (
    <section className="mb-4 rounded-2xl border border-blue-200 bg-gradient-to-br from-blue-50/80 via-white to-white p-4 shadow-sm shadow-blue-900/[0.04]">
      <header className="mb-3 flex flex-wrap items-center justify-between gap-2 px-1">
        <h2 className="flex items-center gap-2 text-[15px] font-semibold text-gray-900">
          <BadgeCheck className="size-5 text-blue-600" aria-hidden />
          최종본
          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">최종검수 통과</span>
        </h2>
        {revisable && (
          // 첨삭 실행(로이드·아냐)은 아직 연결 전이다
          <Button size="sm" variant="primary" icon={PenLine} disabled title="첨삭 기능은 준비 중입니다">
            첨삭하기
          </Button>
        )}
      </header>

      <ul className="grid gap-2 @2xl:grid-cols-2">
        {finals.map((artifact) => {
          const selected = artifact.id === selectedId;
          return (
            <li key={artifact.id}>
              <button
                type="button"
                onClick={() => onSelect(artifact.id)}
                aria-current={selected}
                className={cn(
                  "flex w-full items-center gap-3 rounded-xl border bg-white px-3 py-2.5 text-left transition-colors",
                  selected ? "border-blue-400 ring-2 ring-blue-100" : "border-line hover:border-blue-300",
                )}
              >
                <ArtifactIcon fileType={artifact.fileType} className="size-9" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-gray-900" title={artifact.name}>
                    {artifact.name}
                  </span>
                  <span className="block truncate text-xs text-gray-500">{formatTime(artifact.updatedAt)}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
