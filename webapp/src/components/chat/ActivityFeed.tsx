"use client";

import { memo, useMemo, useState, type ReactNode } from "react";
import { ArrowDown, CalendarDays, ChevronDown, ChevronRight, MessagesSquare } from "lucide-react";
import { getAgentProfile } from "@/constants/agents";
import { useStickToBottom } from "@/hooks/useStickToBottom";
import { dayKey, formatFullDate, formatTime } from "@/lib/format";
import { useAppActions, useIsOwner } from "@/state/WorkspaceProvider";
import type { AgentId, Artifact, FeedItem } from "@/types";
import { EmptyState } from "../ui/States";
import { ActionCard } from "./ActionCard";
import { AgentMessage } from "./AgentMessage";
import { ArtifactCard } from "./ArtifactCard";
import { RunSummaryCard } from "./RunSummaryCard";
import { SystemEvent } from "./SystemEvent";
import { UserMessage } from "./UserMessage";

interface FeedRowProps {
  projectId: string;
  item: FeedItem;
  artifact?: Artifact;
  /** 완료 카드의 최종 PDF들 */
  finalArtifacts?: Artifact[];
  inputPending?: boolean;
  /** Guest면 응답 버튼 대신 로그인 안내 */
  canRespond: boolean;
  onSelectArtifact: (artifactId: string) => void;
  onRespond: (promptId: string, answer: string) => Promise<void>;
}

/**
 * 피드 한 줄. memo로 감싸 새 메시지가 붙어도 기존 줄은 다시 그리지 않는다.
 * 피드가 아주 길어지면 이 컴포넌트를 그대로 가상 스크롤(virtualization) 목록에 넣으면 된다.
 */
const FeedRow = memo(function FeedRow({
  projectId,
  item,
  artifact,
  finalArtifacts,
  inputPending = false,
  canRespond,
  onSelectArtifact,
  onRespond,
}: FeedRowProps) {
  switch (item.kind) {
    case "agent":
      return <AgentMessage agentId={item.agentId} toAgentId={item.toAgentId} text={item.text} createdAt={item.createdAt} />;
    case "activity":
      return <span className="text-[13px] text-label-alternative">{item.label}</span>;
    case "user":
      return <UserMessage text={item.text} createdAt={item.createdAt} />;
    case "system":
      if (item.summary)
        return (
          <RunSummaryCard
            projectId={projectId}
            summary={item.summary}
            finalArtifacts={finalArtifacts ?? []}
            createdAt={item.createdAt}
            onSelectArtifact={onSelectArtifact}
          />
        );
      return (
        <SystemEvent
          compact={item.display === "compact"}
          tone={item.tone}
          title={item.title}
          detail={item.detail}
          agentId={item.agentId}
          createdAt={item.createdAt}
        />
      );
    case "artifact":
      return artifact ? (
        <ArtifactCard projectId={projectId} artifact={artifact} onSelect={onSelectArtifact} />
      ) : null;
    case "input":
      return (
        <ActionCard
          request={item.request}
          pending={inputPending}
          canRespond={canRespond}
          createdAt={item.createdAt}
          onRespond={onRespond}
        />
      );
  }
});

/** 카카오톡처럼 날짜가 바뀌는 곳에 넣는 구분선 */
function DateDivider({ iso }: { iso: string }) {
  return (
    <li className="flex justify-center py-1" role="separator">
      <span className="flex items-center gap-1.5 rounded-full bg-fill px-3 py-1 text-xs text-label-alternative">
        <CalendarDays className="size-3.5 text-label-assistive" aria-hidden />
        <time dateTime={iso}>{formatFullDate(iso)}</time>
      </span>
    </li>
  );
}

/** 단계 전환: 가운데 얇은 선 한 줄. 이어진 전환은 「요구사항 완료 → 기획 시작」처럼 합친다. */
function StageDivider({ items }: { items: FeedItem[] }) {
  const last = items[items.length - 1];
  const titles = items.map((item) => (item.kind === "system" ? item.title : "")).filter(Boolean);
  return (
    <li className="flex items-center gap-3 text-xs text-label-alternative" role="separator">
      <span className="h-px flex-1 bg-fill-strong" aria-hidden />
      <span className="max-w-[80%] text-center">
        {titles.join(" → ")} · <time dateTime={last.createdAt}>{formatTime(last.createdAt)}</time>
      </span>
      <span className="h-px flex-1 bg-fill-strong" aria-hidden />
    </li>
  );
}

function firstCreatedAt(block: FeedBlock): string {
  return block.kind === "item" ? block.item.createdAt : block.items[0].createdAt;
}

/** 연속된 세부 활동(importance: "detail")은 한 묶음으로 접고, 이어진 단계 전환은 한 줄로 합친다. */
type FeedBlock =
  | { kind: "item"; item: FeedItem }
  | { kind: "details"; key: string; items: FeedItem[] }
  | { kind: "dividers"; key: string; items: FeedItem[] }
  | { kind: "activities"; key: string; agentId: AgentId; items: FeedItem[] };

function groupFeed(feed: FeedItem[]): FeedBlock[] {
  const blocks: FeedBlock[] = [];
  for (const item of feed) {
    const last = blocks.at(-1);
    if (item.kind === "system" && item.display === "divider") {
      if (last?.kind === "dividers") last.items.push(item);
      else blocks.push({ kind: "dividers", key: item.id, items: [item] });
    }
    else if (item.kind === "activity") {
      if (last?.kind === "activities" && last.agentId === item.agentId) last.items.push(item);
      else blocks.push({ kind: "activities", key: item.id, agentId: item.agentId, items: [item] });
    }
    else if (item.importance !== "detail") blocks.push({ kind: "item", item });
    else if (last?.kind === "details") last.items.push(item);
    else blocks.push({ kind: "details", key: item.id, items: [item] });
  }
  return blocks;
}

function DetailGroup({ count, children }: { count: number; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const Icon = open ? ChevronDown : ChevronRight;
  return (
    <div className="ml-[52px]">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs text-label-alternative hover:bg-fill"
      >
        <Icon className="size-3.5" aria-hidden />
        세부 활동 {count}건 {open ? "접기" : "보기"}
      </button>
      {open && <ol className="-ml-[52px] mt-2 flex flex-col gap-2">{children}</ol>}
    </div>
  );
}

interface ActivityFeedProps {
  projectId: string;
  feed: FeedItem[];
  artifacts: Artifact[];
  pendingPromptIds: string[];
}

export function ActivityFeed({ projectId, feed, artifacts, pendingPromptIds }: ActivityFeedProps) {
  const { selectArtifact, respondToInput } = useAppActions();
  const isOwner = useIsOwner();
  const { ref: scrollRef, atBottom, scrollToBottom } = useStickToBottom<HTMLDivElement>(feed.length);

  const artifactById = useMemo(
    () => new Map(artifacts.map((artifact) => [artifact.id, artifact])),
    [artifacts],
  );
  const blocks = useMemo(() => groupFeed(feed), [feed]);
  // 완료 카드마다 최종 PDF 전부 — 배열을 렌더마다 새로 만들면 memo된 줄이 다시 그려진다
  const finalsBySummary = useMemo(() => {
    const map = new Map<string, Artifact[]>();
    for (const item of feed) {
      if (item.kind !== "system" || !item.summary) continue;
      const ids = item.summary.finalArtifactIds
        ?? (item.summary.finalArtifactId ? [item.summary.finalArtifactId] : []);
      map.set(item.id, ids.flatMap((id) => artifactById.get(id) ?? []));
    }
    return map;
  }, [feed, artifactById]);

  const renderRow = (item: FeedItem) => (
    <li key={item.id}>
      <FeedRow
        projectId={projectId}
        item={item}
        artifact={item.kind === "artifact" ? artifactById.get(item.artifactId) : undefined}
        finalArtifacts={item.kind === "system" ? finalsBySummary.get(item.id) : undefined}
        inputPending={item.kind === "input" && pendingPromptIds.includes(item.request.promptId)}
        onSelectArtifact={selectArtifact}
        onRespond={respondToInput}
        canRespond={isOwner}
      />
    </li>
  );

  const renderBlock = (block: FeedBlock) =>
    block.kind === "item" ? (
      renderRow(block.item)
    ) : block.kind === "dividers" ? (
      <StageDivider key={block.key} items={block.items} />
    ) : block.kind === "activities" ? (
      <li key={block.key} className="ml-[52px] text-[13px] text-label-alternative">
        <span className="font-medium">{getAgentProfile(block.agentId).name} · 작업 기록</span>
        <ul className="mt-1 space-y-1 border-l border-line pl-3">
          {block.items.map((item) => <li key={item.id} className="break-words">{item.kind === "activity" ? item.label : null}</li>)}
        </ul>
      </li>
    ) : (
      <li key={block.key}>
        <DetailGroup count={block.items.length}>{block.items.map(renderRow)}</DetailGroup>
      </li>
    );

  let lastDay: string | null = null;
  const rows: ReactNode[] = [];
  for (const block of blocks) {
    const at = firstCreatedAt(block);
    if (dayKey(at) !== lastDay) {
      lastDay = dayKey(at);
      rows.push(<DateDivider key={`day-${lastDay}`} iso={at} />);
    }
    rows.push(renderBlock(block));
  }

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto" aria-live="polite">
        {feed.length === 0 ? (
          <EmptyState
            icon={MessagesSquare}
            title="아직 대화가 없습니다"
            description="아래 입력창에 작업을 지시하고 「워크플로우 실행」을 누르면 에이전트들이 단계별로 일을 시작합니다."
            className="h-full"
          />
        ) : (
          <ol className="mx-auto flex max-w-[860px] flex-col gap-4 px-4 py-5 md:px-6">
            {rows}
          </ol>
        )}
      </div>
      {!atBottom && (
        <button
          type="button"
          onClick={scrollToBottom}
          aria-label="맨 아래로"
          className="absolute right-4 bottom-3 flex size-10 items-center justify-center rounded-full border border-line bg-surface/95 text-label-alternative shadow-md transition-colors hover:bg-fill-alt md:right-6"
        >
          <ArrowDown className="size-5" aria-hidden />
        </button>
      )}
    </div>
  );
}
