"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { getAgentProfile } from "@/constants/agents";
import { formatTime } from "@/lib/format";
import { summarizeHandoff } from "@/lib/handoff";
import type { AgentId } from "@/types";
import { AgentAvatar } from "../agent/AgentAvatar";

interface HandoffMessageProps {
  agentId: AgentId;
  toAgentId: AgentId;
  text: string;
  createdAt: string;
}

/** 에이전트 사이 전달문. 기계용 지시라 한 줄 요약만 보이고, 원문은 눌러야 펼친다. */
export function HandoffMessage({ agentId, toAgentId, text, createdAt }: HandoffMessageProps) {
  const [open, setOpen] = useState(false);
  const Icon = open ? ChevronDown : ChevronRight;
  return (
    <div className="ml-[52px] text-xs text-label-alternative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex max-w-full items-center gap-1.5 rounded-md px-1.5 py-0.5 text-left hover:bg-fill"
      >
        <AgentAvatar agentId={agentId} size="xs" />
        <span className="truncate">
          <span className="font-medium text-label-alternative">
            {getAgentProfile(agentId).name} → {getAgentProfile(toAgentId).name}
          </span>{" "}
          · {summarizeHandoff(text)}
        </span>
        <Icon className="size-3.5 shrink-0" aria-hidden />
        <time className="shrink-0 text-label-alternative" dateTime={createdAt}>
          {formatTime(createdAt)}
        </time>
      </button>
      {open && (
        <p className="mt-1 ml-1.5 max-w-[640px] rounded-lg border border-line bg-fill-alt px-3 py-2 text-[12px] leading-relaxed break-words whitespace-pre-line text-label-alternative">
          {text}
        </p>
      )}
    </div>
  );
}
