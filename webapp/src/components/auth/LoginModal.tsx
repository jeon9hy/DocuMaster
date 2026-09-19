"use client";

import { useState, type FormEvent } from "react";
import { serviceKind } from "@/services";
import { useAppActions, useAppState } from "@/state/WorkspaceProvider";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { PinInput } from "./PinInput";

/** Owner 로그인(6자리 PIN). 열려 있을 때만 마운트해서 쓴다 — 닫으면 입력이 지워진다. */
export function LoginModal({ onClose }: { onClose: () => void }) {
  const { session } = useAppState();
  const { login } = useAppActions();
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (pin.length !== 6 || sending) return;
    setSending(true);
    setError(null);
    try {
      await login(pin);
      onClose();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "로그인하지 못했습니다.");
      setPin("");
    } finally {
      setSending(false);
    }
  };

  return (
    <Modal open title="Owner 로그인" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <PinInput label="6자리 PIN" value={pin} onChange={setPin} autoFocus disabled={sending} />
        {session && !session.configured && serviceKind === "http" && (
          <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
            아직 PIN이 설정되지 않았습니다. webapp/server에서 <code>python setup_owner.py</code>를 먼저 실행하세요.
          </p>
        )}
        {serviceKind === "mock" && (
          <p className="rounded-lg bg-gray-100 px-3 py-2 text-xs text-gray-600">
            목업 모드입니다. PIN을 확인하지 않습니다(백엔드를 켜면 실제로 확인합니다).
          </p>
        )}
        {error && (
          <p role="alert" className="text-xs text-red-600">
            {error}
          </p>
        )}
        <p className="text-xs text-gray-500">로그인하지 않아도 프로젝트와 작업물은 볼 수 있고 내려받을 수 있습니다.</p>
        <div className="flex justify-end gap-2">
          <Button onClick={onClose}>취소</Button>
          <Button type="submit" variant="primary" disabled={pin.length !== 6 || sending}>
            {sending ? "확인 중…" : "로그인"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
