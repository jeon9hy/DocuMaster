"use client";

import { memo, useMemo } from "react";
import { MessagesSquare } from "lucide-react";
import { useStickToBottom } from "@/hooks/useStickToBottom";
import { useAppActions } from "@/state/WorkspaceProvider";
import type { Agent, AgentId, Artifact, FeedItem } from "@/types";
import { EmptyState } from "../ui/States";
import { AgentMessage } from "./AgentMessage";
import { ArtifactCard } from "./ArtifactCard";
import { SystemEvent } from "./SystemEvent";
import { UserMessage } from "./UserMessage";

interface FeedRowProps {
  projectId: string;
  item: FeedItem;
  agent?: Agent;
  artifact?: Artifact;
  onSelectArtifact: (artifactId: string) => void;
}

/**
 * 피드 한 줄. memo로 감싸 새 메시지가 붙어도 기존 줄은 다시 그리지 않는다.
 * 피드가 아주 길어지면 이 컴포넌트를 그대로 가상 스크롤(virtualization) 목록에 넣으면 된다.
 */
const FeedRow = memo(function FeedRow({
  projectId,
  item,
  agent,
  artifact,
  onSelectArtifact,
}: FeedRowProps) {
  switch (item.kind) {
    case "agent":
      return <AgentMessage agentId={item.agentId} agent={agent} text={item.text} createdAt={item.createdAt} />;
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
  }
});

interface ActivityFeedProps {
  projectId: string;
  feed: FeedItem[];
  agents: Agent[];
  artifacts: Artifact[];
}

export function ActivityFeed({ projectId, feed, agents, artifacts }: ActivityFeedProps) {
  const { selectArtifact } = useAppActions();
  const scrollRef = useStickToBottom<HTMLDivElement>(feed.length);

  const agentById = useMemo(
    () => new Map<AgentId, Agent>(agents.map((agent) => [agent.id, agent])),
    [agents],
  );
  const artifactById = useMemo(
    () => new Map(artifacts.map((artifact) => [artifact.id, artifact])),
    [artifacts],
  );

  return (
    <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto" aria-live="polite">
      {feed.length === 0 ? (
        <EmptyState
          icon={MessagesSquare}
          title="아직 대화가 없습니다"
          description="아래 입력창에 작업을 지시하고 「실행」을 누르면 에이전트들이 단계별로 일을 시작합니다."
          className="h-full"
        />
      ) : (
        <ol className="mx-auto flex max-w-[860px] flex-col gap-4 px-4 py-5 md:px-6">
          {feed.map((item) => (
            <li key={item.id}>
              <FeedRow
                projectId={projectId}
                item={item}
                agent={item.kind === "agent" ? agentById.get(item.agentId) : undefined}
                artifact={item.kind === "artifact" ? artifactById.get(item.artifactId) : undefined}
                onSelectArtifact={selectArtifact}
              />
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
