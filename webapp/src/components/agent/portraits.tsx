import type { ReactElement } from "react";
import type { AgentId } from "@/types";

/**
 * 에이전트 기본 초상(SVG). 캐릭터의 머리색·배경색만 따온 단순한 그림이다.
 * 실제 이미지를 쓰려면 constants/agents.ts의 avatarSrc를 채우면 이 그림 대신 그 이미지가 나온다.
 * 모든 그림은 64×64 좌표계.
 */

const SKIN = "#F8E1CF";
const LINE = "#5B4636";

function Face({ cy = 31, rx = 12, ry = 14 }: { cy?: number; rx?: number; ry?: number }) {
  return (
    <>
      <rect x="28" y={cy + 8} width="8" height="9" fill={SKIN} />
      <ellipse cx="32" cy={cy} rx={rx} ry={ry} fill={SKIN} />
    </>
  );
}

function Eyes({ color, y = 32, size = 1.6 }: { color: string; y?: number; size?: number }) {
  return (
    <>
      <ellipse cx="27" cy={y} rx={size} ry={size * 1.15} fill={color} />
      <ellipse cx="37" cy={y} rx={size} ry={size * 1.15} fill={color} />
    </>
  );
}

function Loid() {
  return (
    <>
      <rect width="64" height="64" fill="#7FC1B7" />
      <path d="M6 64C8 51 19 47 32 47s24 4 26 17Z" fill="#434D45" />
      <path d="M27 47l5 9 5-9Z" fill="#FFFFFF" />
      <path d="M31 50h2l1 9h-4Z" fill="#2D3431" />
      <Face />
      <path
        d="M19 31C16 17 25 10 34 11c9 1 15 8 12 20-1-6-5-10-10-11-4 3-10 5-17 11Z"
        fill="#E6D38F"
      />
      <path d="M23 21c5 2 8 6 7 11-2-4-5-6-9-6Z" fill="#D2BD72" />
      <path d="M24 28.5l5 1M35 29.5l5-1" stroke="#B39E55" strokeWidth="1.1" strokeLinecap="round" />
      <Eyes color="#2F5D50" y={32} size={1.4} />
      <path d="M29.5 39.5h5" stroke={LINE} strokeWidth="1" strokeLinecap="round" />
    </>
  );
}

function Yor() {
  return (
    <>
      <rect width="64" height="64" fill="#D9574A" />
      <path d="M17 30c0-13 7-19 15-19s15 6 15 19l2 34H15Z" fill="#1E2A2B" />
      <path d="M10 64c2-11 11-16 22-16s20 5 22 16Z" fill="#232323" />
      <Face />
      <path
        d="M19 29c0-11 6-16 13-16s13 5 13 16l-4-4-3 3-3-4-3 4-3-4-3 4-3-3Z"
        fill="#1E2A2B"
      />
      <path d="M18 24h4v24h-4ZM42 24h4v24h-4Z" fill="#1E2A2B" />
      <path d="M19 22c4-10 22-10 26 0" stroke="#C9A544" strokeWidth="1.4" fill="none" />
      <circle cx="18.5" cy="27" r="3" fill="#D4AF4F" />
      <circle cx="18.5" cy="27" r="1.3" fill="#A8822B" />
      <circle cx="45.5" cy="27" r="3" fill="#D4AF4F" />
      <circle cx="45.5" cy="27" r="1.3" fill="#A8822B" />
      <Eyes color="#B3322C" y={32} size={1.6} />
      <ellipse cx="32" cy="39.5" rx="1.6" ry="0.9" fill="#D98A86" />
    </>
  );
}

function Anya() {
  return (
    <>
      <rect width="64" height="64" fill="#FBF1D2" />
      <path d="M16 36c-2-15 6-23 16-23s18 8 16 23v9c-4 1-6-2-6-4H22c0 2-2 5-6 4Z" fill="#F4B6B8" />
      <path d="M12 64c2-10 10-15 20-15s18 5 20 15Z" fill="#2B2B2B" />
      <path d="M22 50c3 5 7 5 10 1 3 4 7 4 10-1-4-1-7-2-10-2s-6 1-10 2Z" fill="#FFFFFF" />
      <path d="M30.5 52h3l-1.5 4Z" fill="#C0392B" />
      <Face cy={33} rx={12} ry={12} />
      <path d="M20 31c0-10 6-15 12-15s12 5 12 15c-3-4-7-6-12-6s-9 2-12 6Z" fill="#F4B6B8" />
      <path d="M31 16c0-3 2-5 4-5" stroke="#E79FA2" strokeWidth="1.3" fill="none" strokeLinecap="round" />
      <path d="M16 21l5-10 4 8ZM39 19l4-8 5 10Z" fill="#2A2A2A" />
      <ellipse cx="27" cy="34" rx="2.4" ry="2.9" fill="#4E9A6B" />
      <ellipse cx="37" cy="34" rx="2.4" ry="2.9" fill="#4E9A6B" />
      <circle cx="27.8" cy="33" r="0.8" fill="#FFFFFF" />
      <circle cx="37.8" cy="33" r="0.8" fill="#FFFFFF" />
      <circle cx="23" cy="38" r="1.8" fill="#F6B8B0" opacity="0.7" />
      <circle cx="41" cy="38" r="1.8" fill="#F6B8B0" opacity="0.7" />
      <ellipse cx="32" cy="40" rx="1.1" ry="0.8" fill="#C97B73" />
    </>
  );
}

function Yuri() {
  return (
    <>
      <rect width="64" height="64" fill="#AFC0CF" />
      <path d="M8 64c2-11 12-16 24-16s22 5 24 16Z" fill="#8A7A5C" />
      <path d="M27 48l5 9 5-9Z" fill="#FFFFFF" />
      <path d="M31 50h2l1 9h-4Z" fill="#3B3B3B" />
      <Face />
      <path
        d="M18 31c-2-13 6-20 14-20 9 0 16 6 14 20l-2-6-3 5-2-7-4 5-2-6-4 5-2-6-3 6-3-4Z"
        fill="#1F2328"
      />
      <path d="M24 28l5 1.5M40 28l-5 1.5" stroke="#1F2328" strokeWidth="1.2" strokeLinecap="round" />
      <Eyes color="#8A3A2A" y={32.5} size={1.5} />
      <ellipse cx="32" cy="40" rx="1.6" ry="1.2" fill="#8C5A4F" />
    </>
  );
}

function Bond() {
  return (
    <>
      <rect width="64" height="64" fill="#9EB3AF" />
      <path d="M0 22C8 12 22 8 34 8c14 0 24 6 30 14v42H0Z" fill="#B8413A" />
      <path d="M8 64c0-12 10-18 24-18s24 6 24 18Z" fill="#F1F1EE" />
      <ellipse cx="17.5" cy="23" rx="4" ry="5.5" transform="rotate(-25 17.5 23)" fill="#E4E4E0" />
      <ellipse cx="46.5" cy="23" rx="4" ry="5.5" transform="rotate(25 46.5 23)" fill="#E4E4E0" />
      <ellipse cx="32" cy="31" rx="16" ry="15" fill="#F7F7F5" />
      <ellipse cx="32" cy="38" rx="7.5" ry="5.5" fill="#FFFFFF" />
      <ellipse cx="32" cy="34.5" rx="3" ry="2.2" fill="#2A2A2A" />
      <path d="M32 36.5v3M29 40c1.5 1 4.5 1 6 0" stroke="#6B6B6B" strokeWidth="0.9" fill="none" strokeLinecap="round" />
      <circle cx="25.5" cy="28.5" r="1.6" fill="#2A2A2A" />
      <circle cx="38.5" cy="28.5" r="1.6" fill="#2A2A2A" />
      <path d="M24 49l7 3-7 3ZM40 49l-7 3 7 3Z" fill="#2A2A2A" />
      <circle cx="32" cy="52" r="2" fill="#1A1A1A" />
    </>
  );
}

export const PORTRAITS: Record<AgentId, () => ReactElement> = {
  loid: Loid,
  yor: Yor,
  yuri: Yuri,
  anya: Anya,
  bond: Bond,
};
