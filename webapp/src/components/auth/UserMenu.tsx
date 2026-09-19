"use client";

import { useCallback, useRef, useState, type PointerEvent } from "react";
import { ChevronDown, LogIn, LogOut, UserPen } from "lucide-react";
import { useDismiss } from "@/hooks/useDismiss";
import { cn } from "@/lib/cn";
import { useAppActions, useAppState } from "@/state/WorkspaceProvider";
import type { OwnerProfile } from "@/types";
import { Button } from "../ui/Button";
import { LoginModal } from "./LoginModal";
import { OwnerAvatar } from "./OwnerAvatar";
import { ProfileEditModal } from "./ProfileEditModal";

/**
 * 로그인한 Owner의 메뉴. 마우스를 올리면 미리 열리고, 누르면 고정된다(터치는 누르기만).
 */
function ProfileMenu({ profile }: { profile: OwnerProfile }) {
  const { logout } = useAppActions();
  const ref = useRef<HTMLDivElement>(null);
  const [pinned, setPinned] = useState(false);
  const [hovering, setHovering] = useState(false);
  const [editing, setEditing] = useState(false);
  const open = pinned || hovering;
  const close = useCallback(() => {
    setPinned(false);
    setHovering(false);
  }, []);
  useDismiss(open, close, ref);

  const onHover = (entering: boolean) => (event: PointerEvent) => {
    if (event.pointerType === "mouse") setHovering(entering);
  };

  return (
    <div ref={ref} className="relative" onPointerEnter={onHover(true)} onPointerLeave={onHover(false)}>
      <button
        type="button"
        onClick={() => setPinned((value) => !value)}
        aria-expanded={open}
        aria-haspopup="menu"
        className="flex items-center gap-2 rounded-lg py-1 pr-1.5 pl-1 hover:bg-gray-100"
      >
        <OwnerAvatar profile={profile} />
        <span className="hidden max-w-[120px] truncate text-sm font-medium text-gray-800 xl:block">
          {profile.nickname}
        </span>
        <ChevronDown className={cn("size-4 text-gray-400 transition-transform", open && "rotate-180")} aria-hidden />
      </button>
      {open && (
        // pt로 버튼과 메뉴 사이의 틈을 메워, 마우스로 옮겨 가는 동안 닫히지 않게 한다
        <div className="absolute top-full right-0 z-30 pt-1.5">
          <div role="menu" className="min-w-44 rounded-xl border border-line bg-white p-1.5 shadow-lg">
            <p className="truncate px-2.5 pt-1 pb-2 text-xs text-gray-500">{profile.nickname} · Owner</p>
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                close();
                setEditing(true);
              }}
              className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
            >
              <UserPen className="size-4 text-gray-500" aria-hidden />
              정보 변경
            </button>
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                close();
                void logout();
              }}
              className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
            >
              <LogOut className="size-4 text-gray-500" aria-hidden />
              로그아웃
            </button>
          </div>
        </div>
      )}
      {editing && <ProfileEditModal profile={profile} onClose={() => setEditing(false)} />}
    </div>
  );
}

/** 로그인 버튼 하나. 다른 화면의 「로그인」 안내에서도 쓴다. */
export function LoginButton({ size = "md", label = "로그인" }: { size?: "sm" | "md"; label?: string }) {
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);
  return (
    <>
      <Button size={size} variant="primary" icon={LogIn} onClick={() => setOpen(true)}>
        {label}
      </Button>
      {open && <LoginModal onClose={close} />}
    </>
  );
}

/** 헤더 오른쪽: 로그아웃 상태면 「로그인」, 로그인 상태면 [사진] 닉네임 ▼ */
export function UserMenu() {
  const { session } = useAppState();
  if (!session) return <span className="size-8" aria-hidden />; // 확인 중 — 자리만 잡아 둔다
  if (session.authenticated && session.profile) return <ProfileMenu profile={session.profile} />;
  return <LoginButton size="sm" />;
}
