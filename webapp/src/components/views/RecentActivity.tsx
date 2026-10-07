"use client";

import { useMemo } from "react";
import { Activity } from "lucide-react";
import { formatTime } from "@/lib/format";
import type { FeedItem, ProjectWorkspace } from "@/types";
import { Panel } from "../ui/Panel";
import { EmptyState } from "../ui/States";

const RECENT_ACTIVITY = 6;

/** 피드 한 줄을 홈용 짧은 문장으로. 코드에서 만든 문장만 쓴다(LLM 문장은 옮기지 않는다). */
function describe(item: FeedItem, workspace: ProjectWorkspace): string | null {
  switch (item.kind) {
    case "system":
      return item.title;
    case "artifact":
      return `${workspace.artifacts.find((artifact) => artifact.id === item.artifactId)?.name ?? "작업물"} 생성`;
    case "input":
      return `사용자 확인 요청 · ${item.request.title}`;
    case "user":
      return "작업 지시";
    case "agent":
    case "activity":
      return null;
  }
}

export function RecentActivity({ workspace }: { workspace: ProjectWorkspace }) {
  const items = useMemo(() => {
    return workspace.feed
      .filter((item) => item.importance !== "detail")
      .map((item) => ({ item, text: describe(item, workspace) }))
      .filter((row): row is { item: FeedItem; text: string } => row.text !== null)
      .slice(-RECENT_ACTIVITY)
      .reverse();
  }, [workspace]);

  return (
    <Panel
      title={
        <span className="flex items-center gap-1.5">
          <Activity className="size-4 text-label-assistive" aria-hidden />
          최근 활동
        </span>
      }
    >
      {items.length === 0 ? (
        <EmptyState icon={Activity} title="최근 활동이 없습니다" className="py-6" />
      ) : (
        <ol className="space-y-1 px-2 pb-1">
          {items.map(({ item, text }) => (
            <li key={item.id} className="flex gap-3 text-[13px]">
              <time className="w-16 shrink-0 text-label-alternative" dateTime={item.createdAt}>
                {formatTime(item.createdAt)}
              </time>
              <span className="min-w-0 flex-1 truncate text-label-neutral">{text}</span>
            </li>
          ))}
        </ol>
      )}
    </Panel>
  );
}
