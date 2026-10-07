"use client";

import { useState, type FormEvent } from "react";
import { Info } from "lucide-react";
import { useAppActions } from "@/state/WorkspaceProvider";
import type { Artifact } from "@/types";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";

const FORM_ID = "revise-form";
// 백엔드 runs.MAX_REVISE_CHARS와 같다
const MAX_CHARS = 4000;

function ReviseForm({ target, onDone }: { target: Artifact; onDone: () => void }) {
  const { reviseDocument } = useAppActions();
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (sending) return;
    if (!text.trim()) {
      setError("무엇이 불편한지 적어 주세요.");
      return;
    }
    setSending(true);
    try {
      await reviseDocument(text.trim(), target.name);
      onDone();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "첨삭을 시작하지 못했습니다.");
      setSending(false);
    }
  };

  return (
    <form id={FORM_ID} onSubmit={handleSubmit} className="space-y-3">
      <p className="truncate text-sm text-gray-600" title={target.name}>
        대상 <span className="font-medium text-gray-900">{target.name}</span>
      </p>
      <label className="block space-y-1.5">
        <span className="text-sm font-medium text-gray-800">첨삭 요청</span>
        <textarea
          autoFocus
          rows={7}
          maxLength={MAX_CHARS}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={"예)\n- 2장 첫 문단이 너무 딱딱해요. 더 쉽게 풀어 주세요.\n- 결론이 길어요. 절반으로 줄여 주세요.\n- 3장과 4장 순서를 바꿔 주세요."}
          className="w-full resize-y rounded-lg border border-line px-3 py-2 text-sm leading-relaxed focus:border-blue-500 focus:outline-none"
        />
      </label>
      <p className="flex gap-2 rounded-lg bg-blue-50/70 px-3 py-2.5 text-xs leading-relaxed text-blue-900">
        <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden />
        <span>
          로이드가 요청을 나눠 아냐에게 넘기고, 아냐는 검증된 사실 안에서만 문장·구조를 고칩니다. 새 자료·수치가 있어야
          하는 요청은 반영하지 않고 이유를 알려 드립니다. 끝나면 이 PDF만 새 버전으로 바뀌고, 다른 최종본은 그대로입니다.
        </span>
      </p>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </form>
  );
}

/** 완료된 문서의 최종 PDF 하나(target)에 대한 첨삭 요청을 받는다. 보내면 대화 화면에서 진행을 본다. */
export function ReviseModal({ open, target, onClose }: { open: boolean; target: Artifact; onClose: () => void }) {
  return (
    <Modal
      open={open}
      title="최종본 첨삭"
      onClose={onClose}
      size="lg"
      footer={
        <>
          <Button onClick={onClose}>취소</Button>
          <Button variant="primary" type="submit" form={FORM_ID}>
            첨삭 시작
          </Button>
        </>
      }
    >
      <ReviseForm target={target} onDone={onClose} />
    </Modal>
  );
}
