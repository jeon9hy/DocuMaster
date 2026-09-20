"use client";

import { memo, useMemo, useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight, MessagesSquare } from "lucide-react";
import { getAgentProfile } from "@/constants/agents";
import { useStickToBottom } from "@/hooks/useStickToBottom";
import { useAppActions, useIsOwner } from "@/state/WorkspaceProvider";
import type { AgentId, Artifact, FeedItem } from "@/types";
import { EmptyState } from "../ui/States";
import { ActionCard } from "./ActionCard";
import { AgentMessage } from "./AgentMessage";
import { ArtifactCard } from "./ArtifactCard";
import { SystemEvent } from "./SystemEvent";
import { UserMessage } from "./UserMessage";

interface FeedRowProps {
  projectId: string;
  item: FeedItem;
  artifact?: Artifact;
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
  inputPending = false,
  canRespond,
  onSelectArtifact,
  onRespond,
}: FeedRowProps) {
  switch (item.kind) {
    case "agent":
      return <AgentMessage agentId={item.agentId} toAgentId={item.toAgentId} text={item.text} createdAt={item.createdAt} />;
    case "activity":
      return <span className="text-[13px] text-gray-600">{item.label}</span>;
    case "user":
      return <UserMessage text={item.text} createdAt={item.createdAt} />;
    case "system":
      return (
        <SystemEvent
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

/** 연속된 세부 활동(importance: "detail")은 한 묶음으로 접는다. */
type FeedBlock =
  | { kind: "item"; item: FeedItem }
  | { kind: "details"; key: string; items: FeedItem[] }
  | { kind: "activities"; key: string; agentId: AgentId; items: FeedItem[] };

function groupFeed(feed: FeedItem[]): FeedBlock[] {
  const blocks: FeedBlock[] = [];
  for (const item of feed) {
    const last = blocks.at(-1);
    if (item.kind === "activity") {
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
        className="flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs text-gray-500 hover:bg-gray-100"
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
  const scrollRef = useStickToBottom<HTMLDivElement>(feed.length);

  const artifactById = useMemo(
    () => new Map(artifacts.map((artifact) => [artifact.id, artifact])),
    [artifacts],
  );
  const blocks = useMemo(() => groupFeed(feed), [feed]);

  const renderRow = (item: FeedItem) => (
    <li key={item.id}>
      <FeedRow
        projectId={projectId}
        item={item}
        artifact={item.kind === "artifact" ? artifactById.get(item.artifactId) : undefined}
        inputPending={item.kind === "input" && pendingPromptIds.includes(item.request.promptId)}
        onSelectArtifact={selectArtifact}
        onRespond={respondToInput}
        canRespond={isOwner}
      />
    </li>
  );

  return (
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
          {blocks.map((block) =>
            block.kind === "item" ? (
              renderRow(block.item)
            ) : block.kind === "activities" ? (
              <li key={block.key} className="ml-[52px] text-[13px] text-gray-500">
                <span className="font-medium">{getAgentProfile(block.agentId).name} · 작업 기록</span>
                <ul className="mt-1 space-y-1 border-l border-line pl-3">
                  {block.items.map((item) => <li key={item.id} className="break-words">{item.kind === "activity" ? item.label : null}</li>)}
                </ul>
              </li>
            ) : (
              <li key={block.key}>
                <DetailGroup count={block.items.length}>{block.items.map(renderRow)}</DetailGroup>
              </li>
            ),
          )}
        </ol>
      )}
    </div>
  );
}
