/* eslint-disable @next/next/no-img-element -- 사용자가 올린 작은 프로필 이미지라 next/image 최적화가 필요 없다 */
import { cn } from "@/lib/cn";
import { workspaceService } from "@/services";
import type { OwnerProfile } from "@/types";

const SIZE = { sm: "size-8 text-xs", lg: "size-16 text-lg" } as const;

/** Owner 프로필 사진(정사각형으로 잘라 보여 준다). 없으면 닉네임 첫 글자. */
export function OwnerAvatar({
  profile,
  previewSrc,
  size = "sm",
}: {
  profile: OwnerProfile;
  /** 저장 전 미리보기 이미지 */
  previewSrc?: string | null;
  size?: keyof typeof SIZE;
}) {
  const src =
    previewSrc ??
    workspaceService.getAvatarUrl(profile.hasAvatar ? (profile.updatedAt ?? "1") : null);
  const frame = cn("shrink-0 overflow-hidden rounded-full", SIZE[size]);
  if (src) return <img src={src} alt="" className={cn(frame, "object-cover")} />;
  return (
    <span className={cn(frame, "flex items-center justify-center bg-blue-100 font-semibold text-blue-700")}>
      {profile.nickname.slice(0, 1)}
    </span>
  );
}
