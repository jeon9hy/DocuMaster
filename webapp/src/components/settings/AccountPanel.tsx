"use client";

import { useState, type FormEvent } from "react";
import { UserRound } from "lucide-react";
import { formatDateTime } from "@/lib/format";
import { useAppActions, useAppState } from "@/state/WorkspaceProvider";
import { OwnerAvatar } from "../auth/OwnerAvatar";
import { PinInput } from "../auth/PinInput";
import { ProfileEditModal } from "../auth/ProfileEditModal";
import { LoginButton } from "../auth/UserMenu";
import { Button } from "../ui/Button";
import { Panel } from "../ui/Panel";

function PinChangeForm({ managedByEnv }: { managedByEnv: boolean }) {
  const { changePin } = useAppActions();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (managedByEnv) {
    return (
      <p className="text-xs text-gray-500">
        PIN이 환경변수(DOCUMASTER_OWNER_PIN_HASH)로 설정되어 있어 여기서 바꿀 수 없습니다.
      </p>
    );
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (next !== confirm) return setError("새 PIN 두 번이 다릅니다.");
    setSaving(true);
    setError(null);
    try {
      await changePin(current, next); // 성공하면 모든 세션이 끊겨 로그아웃된다
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "PIN을 바꾸지 못했습니다.");
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="@container space-y-3">
      <PinInput label="현재 PIN" value={current} onChange={setCurrent} />
      <div className="grid gap-3 @md:grid-cols-2">
        <PinInput label="새 PIN" value={next} onChange={setNext} autoComplete="new-password" />
        <PinInput label="새 PIN 확인" value={confirm} onChange={setConfirm} autoComplete="new-password" />
      </div>
      {error && (
        <p role="alert" className="text-xs text-red-600">
          {error}
        </p>
      )}
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-gray-500">바꾸면 모든 브라우저에서 로그아웃됩니다.</p>
        <Button
          type="submit"
          size="sm"
          variant="primary"
          disabled={saving || current.length !== 6 || next.length !== 6 || confirm.length !== 6}
        >
          PIN 변경
        </Button>
      </div>
    </form>
  );
}

/** 계정: 프로필 · PIN 변경 (Owner만) */
export function AccountPanel() {
  const { session } = useAppState();
  const [editing, setEditing] = useState(false);
  const profile = session?.authenticated ? session.profile : null;

  return (
    <Panel
      title={
        <span className="flex items-center gap-1.5">
          <UserRound className="size-4 text-gray-400" aria-hidden />
          계정
        </span>
      }
      bodyClassName="space-y-5 px-4 pb-4"
    >
      {!profile ? (
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-gray-600">
          🔒 로그인하면 프로필과 PIN을 관리할 수 있습니다.
          <LoginButton size="sm" />
        </div>
      ) : (
        <>
          <div className="flex items-center gap-3">
            <OwnerAvatar profile={profile} size="lg" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-gray-900">{profile.nickname}</p>
              <p className="text-xs text-gray-500">
                Owner{profile.updatedAt && ` · 마지막 변경 ${formatDateTime(profile.updatedAt)}`}
              </p>
            </div>
            <Button size="sm" onClick={() => setEditing(true)}>
              정보 변경
            </Button>
          </div>
          <div className="border-t border-line pt-4">
            <h3 className="mb-3 text-[13px] font-semibold text-gray-800">PIN 변경</h3>
            <PinChangeForm managedByEnv={session?.pinManagedByEnv ?? false} />
          </div>
          {editing && <ProfileEditModal profile={profile} onClose={() => setEditing(false)} />}
        </>
      )}
    </Panel>
  );
}
