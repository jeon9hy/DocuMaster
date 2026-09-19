"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { ImagePlus, Trash2 } from "lucide-react";
import { useAppActions } from "@/state/WorkspaceProvider";
import type { OwnerProfile } from "@/types";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { OwnerAvatar } from "./OwnerAvatar";

const ACCEPT = "image/png,image/jpeg,image/webp";
const MAX_BYTES = 5 * 1024 * 1024;

/** 정보 변경: 닉네임 · 프로필 사진. 열려 있을 때만 마운트한다. */
export function ProfileEditModal({ profile, onClose }: { profile: OwnerProfile; onClose: () => void }) {
  const { updateProfile } = useAppActions();
  const fileRef = useRef<HTMLInputElement>(null);
  const [nickname, setNickname] = useState(profile.nickname);
  const [file, setFile] = useState<File | null>(null);
  const [removeAvatar, setRemoveAvatar] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview);
  }, [preview]);

  const pickFile = (picked: File | undefined) => {
    setError(null);
    if (!picked) return;
    if (!ACCEPT.split(",").includes(picked.type)) return setError("PNG·JPG·WEBP 이미지만 올릴 수 있습니다.");
    if (picked.size > MAX_BYTES) return setError("5MB 이하 이미지만 올릴 수 있습니다.");
    setFile(picked);
    setRemoveAvatar(false);
    setPreview(URL.createObjectURL(picked));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!nickname.trim() || saving) return;
    setSaving(true);
    setError(null);
    try {
      await updateProfile({ nickname: nickname.trim(), avatar: file ?? undefined, removeAvatar });
      onClose();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "저장하지 못했습니다.");
    } finally {
      setSaving(false);
    }
  };

  const shown = removeAvatar ? { ...profile, hasAvatar: false } : profile;

  return (
    <Modal open title="정보 변경" onClose={onClose}>
      <form onSubmit={submit} className="space-y-5">
        <div className="flex items-center gap-4">
          <OwnerAvatar profile={shown} previewSrc={preview} size="lg" />
          <div className="flex flex-wrap gap-2">
            <Button size="sm" icon={ImagePlus} onClick={() => fileRef.current?.click()}>
              사진 선택
            </Button>
            {(profile.hasAvatar || file) && !removeAvatar && (
              <Button
                size="sm"
                variant="ghost"
                icon={Trash2}
                onClick={() => {
                  setFile(null);
                  setPreview(null);
                  setRemoveAvatar(true);
                }}
              >
                사진 삭제
              </Button>
            )}
            <p className="w-full text-xs text-gray-500">PNG·JPG·WEBP, 5MB 이하. 정사각형으로 잘라 보여 줍니다.</p>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept={ACCEPT}
            hidden
            onChange={(event) => pickFile(event.target.files?.[0])}
          />
        </div>
        <label className="block">
          <span className="mb-1.5 block text-[13px] font-medium text-gray-700">닉네임</span>
          <input
            value={nickname}
            maxLength={30}
            onChange={(event) => setNickname(event.target.value)}
            className="h-10 w-full rounded-lg border border-line px-3 text-sm focus:border-blue-500 focus:outline-none"
          />
        </label>
        {error && (
          <p role="alert" className="text-xs text-red-600">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button onClick={onClose}>취소</Button>
          <Button type="submit" variant="primary" disabled={!nickname.trim() || saving}>
            {saving ? "저장 중…" : "저장"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
