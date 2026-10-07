"use client";

import { useState } from "react";
import { BadgeCheck, ChevronDown, History, PenLine } from "lucide-react";
import { cn } from "@/lib/cn";
import { formatTime } from "@/lib/format";
import type { Artifact } from "@/types";
import { ArtifactIcon } from "./ArtifactIcon";

interface FinalArtifactsBlockProps {
  /** PDF가 앞에 오게 정렬된 최종본(splitFinalArtifacts) */
  finals: Artifact[];
  /** 첨삭으로 교체되기 전의 최종본(`<이름>_vNN.pdf`), 최근 것부터 */
  previous: Artifact[];
  selectedId: string | null;
  onSelect: (artifactId: string) => void;
  /** 첨삭은 문서 모드만(아냐가 DOC 전용) */
  revisable: boolean;
  /** 첨삭 버튼을 못 누르는 이유(로그인 전·실행 중). 없으면 누를 수 있다 */
  reviseBlockedReason: string | null;
  /** 최종 PDF마다 따로 첨삭한다(본문 + 연습문제처럼 여러 부일 때) */
  onRevise: (artifact: Artifact) => void;
}

/** `<이름>.pdf`의 이전판(`<이름>_vNN.pdf`)이 있는가 */
function hasPrevious(artifact: Artifact, previous: Artifact[]): boolean {
  const stem = artifact.name.replace(/\.pdf$/i, "");
  return previous.some((item) => item.name.replace(/_v\d{2}\.pdf$/i, "") === stem);
}

/** 최종검수를 통과한 파일만 따로 모은 맨 위 블록. 파일 줄은 전체 폭, 누르면 아래 미리보기에 연다. */
export function FinalArtifactsBlock({
  finals,
  previous,
  selectedId,
  onSelect,
  revisable,
  reviseBlockedReason,
  onRevise,
}: FinalArtifactsBlockProps) {
  // 이전판을 보고 있으면 펼친 채로 둔다
  const [showPrevious, setShowPrevious] = useState(() => previous.some((artifact) => artifact.id === selectedId));

  return (
    <section className="mb-4 rounded-2xl border border-blue-200 bg-gradient-to-br from-blue-50/80 via-white to-white p-4 shadow-sm shadow-blue-900/[0.04]">
      <h2 className="mb-3 flex items-center gap-2 px-1 text-[15px] font-semibold text-gray-900">
        <BadgeCheck className="size-5 text-blue-600" aria-hidden />
        최종본
        <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">최종검수 통과</span>
      </h2>

      <ul className="flex flex-col gap-2">
        {finals.map((artifact) => {
          const selected = artifact.id === selectedId;
          return (
            <li
              key={artifact.id}
              className={cn(
                "flex items-center gap-2 rounded-xl border bg-white pr-3 transition-colors",
                selected ? "border-blue-400 ring-2 ring-blue-100" : "border-line hover:border-blue-300",
              )}
            >
              <button
                type="button"
                onClick={() => onSelect(artifact.id)}
                aria-current={selected}
                className="flex min-w-0 flex-1 items-center gap-3 rounded-xl px-3 py-2.5 text-left"
              >
                <ArtifactIcon fileType={artifact.fileType} className="size-9" />
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-1.5">
                    <span className="truncate text-sm font-medium text-gray-900" title={artifact.name}>
                      {artifact.name}
                    </span>
                    {artifact.fileType === "pdf" && hasPrevious(artifact, previous) && (
                      <span className="shrink-0 rounded bg-emerald-50 px-1.5 py-0.5 text-[11px] font-medium text-emerald-700">
                        최신
                      </span>
                    )}
                  </span>
                  <span className="block truncate text-xs text-gray-500">{formatTime(artifact.updatedAt)}</span>
                </span>
              </button>
              {revisable && artifact.fileType === "pdf" && (
                <button
                  type="button"
                  onClick={() => onRevise(artifact)}
                  disabled={reviseBlockedReason !== null}
                  title={reviseBlockedReason ?? "문장·구조를 고쳐 이 PDF를 새 버전으로 바꿉니다"}
                  className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg bg-blue-600 px-3 text-[13px] font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-50 disabled:text-blue-700/50"
                >
                  <PenLine className="size-3.5" aria-hidden />
                  첨삭하기
                </button>
              )}
            </li>
          );
        })}
      </ul>

      {previous.length > 0 && (
        <div className="mt-2 px-1">
          <button
            type="button"
            onClick={() => setShowPrevious((value) => !value)}
            aria-expanded={showPrevious}
            className="flex items-center gap-1.5 py-1 text-xs font-medium text-gray-500 hover:text-blue-700"
          >
            <History className="size-3.5" aria-hidden />
            이전판 {previous.length}개
            <ChevronDown className={cn("size-3.5 transition-transform", showPrevious && "rotate-180")} aria-hidden />
          </button>
          {showPrevious && (
            <ul className="mt-1 flex flex-col gap-0.5">
              {previous.map((artifact) => (
                <li key={artifact.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(artifact.id)}
                    aria-current={artifact.id === selectedId}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left transition-colors",
                      artifact.id === selectedId ? "bg-blue-50/70" : "hover:bg-white",
                    )}
                  >
                    <ArtifactIcon fileType={artifact.fileType} className="size-7" />
                    <span className="min-w-0 flex-1 truncate text-[13px] text-gray-700" title={artifact.name}>
                      {artifact.name}
                    </span>
                    <span className="shrink-0 text-xs text-gray-400">{formatTime(artifact.updatedAt)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
