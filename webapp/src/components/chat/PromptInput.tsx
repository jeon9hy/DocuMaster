"use client";

import { useRef, useState, type KeyboardEvent } from "react";
import { AtSign, CheckCircle2, Paperclip, Play, Send, Square } from "lucide-react";
import { getAgentProfile } from "@/constants/agents";
import { findMentionedAgent } from "@/lib/mentions";
import { useAppActions } from "@/state/WorkspaceProvider";
import type { AgentId } from "@/types";
import { AgentAvatar } from "../agent/AgentAvatar";
import { AddReferenceButton } from "../reference/AddReferenceButton";
import { Button, IconButton } from "../ui/Button";
import { Dropdown, DropdownItem } from "../ui/Dropdown";

interface PromptInputProps {
  teamIds: AgentId[];
  isRunning: boolean;
  isComplete: boolean;
}

/**
 * 하단 입력창. Enter = 지시 보내기, Shift+Enter = 줄바꿈.
 * 「실행」은 입력한 지시가 있으면 먼저 보낸 뒤 워크플로우를 이어서 돌린다.
 */
export function PromptInput({ teamIds, isRunning, isComplete }: PromptInputProps) {
  const { sendMessage, runWorkflow, stopWorkflow } = useAppActions();
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const trimmed = text.trim();

  const submitMessage = async () => {
    if (!trimmed) return;
    setText("");
    await sendMessage(trimmed, findMentionedAgent(trimmed));
  };

  const handleRun = async () => {
    await submitMessage();
    await runWorkflow();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // 한글 조합 중 Enter는 글자 확정용이므로 전송하지 않는다.
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
    event.preventDefault();
    void submitMessage();
  };

  const insertMention = (agentId: AgentId) => {
    setText((current) => `${current}${current && !current.endsWith(" ") ? " " : ""}@${getAgentProfile(agentId).name} `);
    textareaRef.current?.focus();
  };

  return (
    <div className="border-t border-line bg-white px-3 py-3 md:px-5">
      <div className="mx-auto flex max-w-[860px] items-end gap-2 rounded-xl border border-line bg-white p-2 focus-within:border-blue-400">
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="에이전트에게 작업 지시를 입력하세요… (@로 에이전트 호출)"
          aria-label="작업 지시"
          className="field-sizing-content max-h-40 min-h-9 flex-1 resize-none bg-transparent px-2 py-2 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none"
        />
        <Dropdown
          align="right"
          placement="top"
          trigger={({ toggle }) => <IconButton icon={AtSign} label="에이전트 호출" onClick={toggle} />}
        >
          {(close) =>
            teamIds.map((id) => (
              <DropdownItem
                key={id}
                onSelect={() => {
                  insertMention(id);
                  close();
                }}
              >
                <AgentAvatar agentId={id} size="xs" />
                <span className="font-medium">{getAgentProfile(id).name}</span>
                <span className="text-xs text-gray-500">{getAgentProfile(id).role}</span>
              </DropdownItem>
            ))
          }
        </Dropdown>
        <IconButton icon={Send} label="지시 보내기 (Enter)" disabled={!trimmed} onClick={submitMessage} className="disabled:opacity-40" />
        <AddReferenceButton>
          {(open) => (
            <span className="hidden sm:block">
              <Button icon={Paperclip} onClick={open}>
                레퍼런스 추가
              </Button>
            </span>
          )}
        </AddReferenceButton>
        {isRunning ? (
          <Button variant="danger" icon={Square} onClick={stopWorkflow}>
            중지
          </Button>
        ) : (
          <Button
            variant="primary"
            icon={isComplete ? CheckCircle2 : Play}
            onClick={handleRun}
            disabled={isComplete}
          >
            {isComplete ? "완료됨" : "실행"}
          </Button>
        )}
      </div>
    </div>
  );
}
