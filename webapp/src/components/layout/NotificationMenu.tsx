"use client";

import { useMemo, useSyncExternalStore } from "react";
import { Bell } from "lucide-react";
import { TONE_VARIANT } from "@/constants/status";
import { formatTime } from "@/lib/format";
import { markAlertsSeen, readSeenAlertsRaw, seenAtFor, subscribeSeenAlerts } from "@/lib/seenAlerts";
import type { FeedItem } from "@/types";
import { Badge } from "../ui/Badge";
import { IconButton } from "../ui/Button";
import { Dropdown } from "../ui/Dropdown";

const RECENT_COUNT = 6;

type SystemItem = Extract<FeedItem, { kind: "system" }>;

/** 헤더 종 아이콘: 최근 시스템 이벤트 몇 개. 아직 안 읽은 경고·오류가 있으면 빨간 점(열면 읽음) */
export function NotificationMenu({ projectId, feed }: { projectId: string | null; feed: FeedItem[] }) {
  const recent = useMemo(
    () =>
      feed
        .filter((item): item is SystemItem => item.kind === "system")
        .slice(-RECENT_COUNT)
        .reverse(),
    [feed],
  );
  const seenRaw = useSyncExternalStore(subscribeSeenAlerts, readSeenAlertsRaw, () => "{}");
  const seenAt = projectId ? seenAtFor(seenRaw, projectId) : "";
  const hasAlert = recent.some(
    (item) => (item.tone === "warning" || item.tone === "error") && item.createdAt > seenAt,
  );
  const markSeen = () => {
    if (projectId && recent[0]) markAlertsSeen(projectId, recent[0].createdAt);
  };

  return (
    <Dropdown
      align="right"
      className="w-80"
      trigger={({ open, toggle }) => (
        <div className="relative">
          <IconButton
            icon={Bell}
            label={hasAlert ? "알림 (읽지 않은 경고 있음)" : "알림"}
            onClick={() => {
              if (!open) markSeen();
              toggle();
            }}
          />
          {hasAlert && <span className="absolute top-2 right-2 size-2 rounded-full bg-red-500 ring-2 ring-white" />}
        </div>
      )}
    >
      {() => (
        <>
          <p className="px-2.5 pt-1 pb-1.5 text-xs font-medium text-gray-500">최근 알림</p>
          {recent.length === 0 ? (
            <p className="px-2.5 py-3 text-sm text-gray-500">알림이 없습니다.</p>
          ) : (
            <ul>
              {recent.map((item) => (
                <li key={item.id} className="flex items-start gap-2 rounded-lg px-2.5 py-2">
                  <Badge variant={TONE_VARIANT[item.tone]} dot className="mt-0.5 px-1.5">
                    {formatTime(item.createdAt)}
                  </Badge>
                  <span className="min-w-0 text-[13px] text-gray-700">
                    {item.title}
                    {item.detail && <span className="block truncate text-xs text-gray-500">{item.detail}</span>}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </Dropdown>
  );
}
