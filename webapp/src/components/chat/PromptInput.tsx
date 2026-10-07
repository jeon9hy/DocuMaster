"use client";

import { useRef, useState, type KeyboardEvent } from "react";
import { AtSign, CalendarClock, CheckCircle2, Hourglass, Lock, Paperclip, Play, Send, Square, X } from "lucide-react";
import { getAgentProfile } from "@/constants/agents";
import { findMentionedAgent } from "@/lib/mentions";
import { ServiceError } from "@/services";
import { useAppActions, useIsOwner } from "@/state/WorkspaceProvider";
import type { AgentId, RunStatus } from "@/types";
import { AgentAvatar } from "../agent/AgentAvatar";
import { LoginButton } from "../auth/UserMenu";
import { AddReferenceButton } from "../reference/AddReferenceButton";
import { Button, IconButton } from "../ui/Button";
import { Dropdown, DropdownItem } from "../ui/Dropdown";

interface PromptInputProps {
  teamIds: AgentId[];
  runStatus: RunStatus;
  /** 다른 프로젝트가 끝나면 시작하도록 예약됨 */
  queued?: boolean;
  isComplete: boolean;
  /** 중지·오류(사용량 한도 등)로 끊긴 첨삭이 고치던 PDF 이름 — 있으면 완료된 작업이어도 「첨삭 이어서」 */
  pausedRevise?: string | null;
  /** 기존 CLI 작업을 읽기 전용으로 연 프로젝트 */
  readOnly?: boolean;
}

/**
 * 하단 입력창. Enter = 지시 보내기, Shift+Enter = 줄바꿈.
 * - 「지시 보내기」: 메시지만 남긴다. 실행 중이면 현재 단계가 끝난 뒤 반영된다.
 * - 「워크플로우 실행」: 입력한 지시가 있으면 먼저 보낸 뒤 멈춘 단계부터 실행한다.
 * - 실행 중에는 「중지 요청」: 현재 단계가 끝나면 멈춘다(graceful stop).
 * - 끊긴 첨삭이 있으면 완료된 작업이어도 「첨삭 이어서」 — 같은 로이드 세션으로 멈춘 곳부터 잇는다.
 * - 다른 프로젝트가 실행 중이면 「끝나면 자동 시작 예약」을 제안하고, 예약 중에는 「예약 취소」.
 */
export function PromptInput({
  teamIds,
  runStatus,
  queued = false,
  isComplete,
  pausedRevise = null,
  readOnly = false,
}: PromptInputProps) {
  const { sendMessage, runWorkflow, queueWorkflow, cancelQueuedWorkflow, stopWorkflow } = useAppActions();
  const [offerQueue, setOfferQueue] = useState(false);
  const isOwner = useIsOwner();
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const trimmed = text.trim();

  const [error, setError] = useState<string | null>(null);

  /** 명령이 실패하면(백엔드 없음·중복 실행 등) 백엔드가 준 이유를 입력창 아래에 보여 준다. */
  const attempt = async (action: () => Promise<void>) => {
    setError(null);
    setOfferQueue(false);
    try {
      await action();
    } catch (caught) {
      if (caught instanceof ServiceError && caught.code === "busy") {
        setOfferQueue(true); // 오류가 아니라 선택지다 — 예약 버튼을 보여 준다
        return;
      }
      setError(caught instanceof Error ? caught.message : "요청을 처리하지 못했습니다.");
    }
  };

  const submitMessage = () =>
    attempt(async () => {
      if (!trimmed) return;
      setText("");
      try {
        await sendMessage(trimmed, findMentionedAgent(trimmed));
      } catch (caught) {
        setText(trimmed); // 보내지 못한 지시는 되돌려 둔다
        throw caught;
      }
    });

  const handleRun = () =>
    attempt(async () => {
      if (trimmed) {
        setText("");
        await sendMessage(trimmed, findMentionedAgent(trimmed));
      }
      await runWorkflow();
    });

  const handleStop = () => attempt(stopWorkflow);
  const handleQueue = () => attempt(queueWorkflow);
  const handleCancelQueue = () => attempt(cancelQueuedWorkflow);

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

  if (readOnly) {
    return (
      <div className="border-t border-line bg-surface px-3 py-3 text-center text-xs text-label-alternative md:px-5">
        기존 CLI 작업을 읽기 전용으로 연 프로젝트입니다. 이어서 작업하려면 터미널의 Claude Code에서 진행하세요.
      </div>
    );
  }

  if (!isOwner) {
    return (
      <div className="flex flex-wrap items-center justify-center gap-3 border-t border-line bg-surface px-3 py-3 text-sm text-label-alternative md:px-5">
        <Lock className="size-4 shrink-0 text-label-assistive" aria-hidden />
        로그인하면 에이전트에게 작업을 지시할 수 있습니다.
        <LoginButton size="sm" />
      </div>
    );
  }

  const isActive = runStatus === "running" || runStatus === "awaitingInput";
  const resumeRevise = isComplete && pausedRevise !== null;
  const done = isComplete && !resumeRevise;

  return (
    <div className="border-t border-line bg-surface px-3 py-3 md:px-5">
      <div className="mx-auto flex max-w-[860px] flex-col gap-2 rounded-xl border border-line bg-surface p-2 focus-within:border-primary">
        <div className="flex min-w-0 items-start gap-2">
          <textarea
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="작업 지시를 입력하세요"
            aria-label="작업 지시"
            className="field-sizing-content max-h-40 min-h-9 min-w-0 flex-1 resize-none bg-transparent px-2 py-2 text-sm text-label-neutral placeholder:text-label-alternative focus:outline-none"
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
                  <span className="text-xs text-label-alternative">{getAgentProfile(id).role}</span>
                </DropdownItem>
              ))
            }
          </Dropdown>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Button
            icon={Send}
            onClick={submitMessage}
            disabled={!trimmed}
            title={isActive ? "메시지만 보냅니다. 현재 단계가 끝난 뒤 반영됩니다. (Enter)" : "메시지만 보냅니다. 실행은 하지 않습니다. (Enter)"}
            className="px-3"
          >
            <span className="sm:hidden">보내기</span>
            <span className="hidden sm:inline">지시 보내기</span>
          </Button>
          <AddReferenceButton>
            {(open) => (
              <Button icon={Paperclip} onClick={open}>
                <span className="sm:hidden">레퍼런스</span>
                <span className="hidden sm:inline">레퍼런스 추가</span>
              </Button>
            )}
          </AddReferenceButton>
          {runStatus === "stopping" ? (
            <Button variant="danger" icon={Hourglass} disabled title="현재 단계가 끝나면 멈춥니다.">
              중지 요청됨
            </Button>
          ) : isActive ? (
            <Button variant="danger" icon={Square} onClick={handleStop} title="현재 단계가 끝나면 멈춥니다.">
              중지 요청
            </Button>
          ) : queued ? (
            <Button icon={X} onClick={handleCancelQueue} title="예약을 취소합니다. 다른 실행에는 영향이 없습니다.">
              예약 취소
            </Button>
          ) : (
            <Button
              variant="primary"
              icon={done ? CheckCircle2 : Play}
              onClick={handleRun}
              disabled={done}
              title={
                resumeRevise
                  ? `입력한 지시가 있으면 먼저 보낸 뒤, 멈춘 ${pausedRevise || "최종본"} 첨삭을 같은 세션으로 이어서 합니다.`
                  : "입력한 지시가 있으면 먼저 보낸 뒤, 멈춘 단계부터 워크플로우를 실행합니다."
              }
            >
              <span className="sm:hidden">{done ? "완료됨" : resumeRevise ? "이어서" : "실행"}</span>
              <span className="hidden sm:inline">
                {done ? "완료됨" : resumeRevise ? "첨삭 이어서" : "워크플로우 실행"}
              </span>
            </Button>
          )}
        </div>
      </div>
      {queued && (
        <p className="mx-auto flex max-w-[860px] items-center gap-1.5 px-1 pt-1.5 text-xs text-label-alternative">
          <CalendarClock className="size-3.5 shrink-0 text-primary" aria-hidden />
          실행 예약됨 — 지금 실행 중인 다른 프로젝트가 완료·오류로 끝나면 자동으로 시작합니다.
        </p>
      )}
      {offerQueue && !queued && (
        <div
          role="status"
          className="mx-auto mt-1.5 flex max-w-[860px] flex-wrap items-center gap-2 rounded-lg bg-primary/8 px-3 py-2 text-xs text-primary-heavy"
        >
          <span className="min-w-0 flex-1">다른 프로젝트가 실행 중입니다. 한 번에 하나만 실행합니다.</span>
          <Button size="sm" variant="primary" icon={CalendarClock} onClick={handleQueue}>
            끝나면 자동 시작 예약
          </Button>
        </div>
      )}
      {error && (
        <p role="alert" className="mx-auto max-w-[860px] px-1 pt-1.5 text-xs text-negative-fg">
          {error}
        </p>
      )}
    </div>
  );
}
