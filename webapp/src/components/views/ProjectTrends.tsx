"use client";

import { useMemo } from "react";
import { BarChart3, CalendarDays } from "lucide-react";
import { formatShortDate, toIsoDate } from "@/lib/library";
import { cumulativeSeries, lastDays } from "@/lib/trends";
import { useAppActions } from "@/state/WorkspaceProvider";
import type { LibraryDocument } from "@/types";
import { kindTone } from "../library/kindTone";
import { Panel } from "../ui/Panel";
import { EmptyState } from "../ui/States";

const WEEK_DAYS = 7;
const WEEKDAY = ["일", "월", "화", "수", "목", "금", "토"];
/** 점 칸이 이 개수를 넘으면 나머지는 「+n」으로 줄인다 */
const MAX_DOTS = 8;

function weekday(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return WEEKDAY[new Date(y, m - 1, d).getDay()];
}

function PanelTitle({ icon: Icon, children }: { icon: typeof BarChart3; children: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <Icon className="size-4 text-label-assistive" aria-hidden />
      {children}
    </span>
  );
}

/** 지금까지 만든 문서의 누적 추이(선). 문서를 만든 날에만 점을 찍는다. */
function OverallTrend({ documents, today }: { documents: readonly LibraryDocument[]; today: string }) {
  const series = useMemo(() => cumulativeSeries(documents, today), [documents, today]);
  const total = series.at(-1)?.total ?? 0;
  const x = (index: number) => (series.length > 1 ? (index / (series.length - 1)) * 100 : 50);
  const y = (value: number) => 100 - (value / Math.max(total, 1)) * 100;
  const line = series.map((point, index) => `${x(index)},${y(point.total)}`).join(" ");
  const middle = series[Math.floor((series.length - 1) / 2)];

  return (
    <Panel title={<PanelTitle icon={BarChart3}>지금까지 만든 프로젝트</PanelTitle>} bodyClassName="px-4 pb-4">
      {series.length === 0 ? (
        <EmptyState icon={BarChart3} title="아직 끝낸 프로젝트가 없습니다" className="py-6" />
      ) : (
        <>
          <p className="mb-3 text-[13px] text-label-alternative">
            누적 <strong className="text-lg font-semibold text-label">{total}건</strong> · {formatShortDate(series[0].date)}부터
          </p>
          <div className="flex gap-2">
            <div className="flex h-36 flex-col justify-between text-right text-[11px] text-label-alternative" aria-hidden>
              <span>{total}</span>
              <span>0</span>
            </div>
            <div className="min-w-0 flex-1">
              <div className="relative h-36 border-b border-l border-line">
                <div className="absolute inset-x-0 top-0 border-t border-dashed border-line-neutral" aria-hidden />
                <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 size-full overflow-visible" aria-hidden>
                  <polygon points={`0,100 ${line} 100,100`} className="fill-primary/8" />
                  <polyline
                    points={line}
                    fill="none"
                    strokeWidth={2}
                    strokeLinejoin="round"
                    vectorEffect="non-scaling-stroke"
                    className="stroke-primary"
                  />
                </svg>
                {series.map(
                  (point, index) =>
                    point.added > 0 && (
                      <span
                        key={point.date}
                        title={`${formatShortDate(point.date)} · 누적 ${point.total}건 (그날 +${point.added})`}
                        className="absolute size-2.5 -translate-x-1/2 translate-y-1/2 rounded-full border-2 border-surface bg-primary"
                        style={{ left: `${x(index)}%`, bottom: `${100 - y(point.total)}%` }}
                      />
                    ),
                )}
              </div>
              <div className="mt-1.5 flex justify-between text-[11px] text-label-alternative">
                <span>{formatShortDate(series[0].date)}</span>
                {series.length > 4 && <span>{formatShortDate(middle.date)}</span>}
                <span>{formatShortDate(series.at(-1)!.date)}</span>
              </div>
            </div>
          </div>
        </>
      )}
    </Panel>
  );
}

/** 최근 7일, 날짜마다 만든 문서를 점으로 쌓는다. 점 색은 문서 유형, 누르면 그 문서로 간다. */
function WeekDots({ documents, today }: { documents: readonly LibraryDocument[]; today: string }) {
  const { openLibraryDocument } = useAppActions();
  const week = useMemo(() => lastDays(documents, WEEK_DAYS, today), [documents, today]);
  const count = week.reduce((sum, bucket) => sum + bucket.documents.length, 0);
  const kinds = useMemo(() => [...new Set(week.flatMap((bucket) => bucket.documents.map((doc) => doc.kind)))], [week]);

  return (
    <Panel title={<PanelTitle icon={CalendarDays}>최근 일주일</PanelTitle>} bodyClassName="px-4 pb-4">
      <p className="mb-3 text-[13px] text-label-alternative">
        최근 7일 <strong className="text-lg font-semibold text-label">{count}건</strong>
        {count === 0 && " · 이번 주에 끝낸 프로젝트가 없습니다"}
      </p>
      <div className="grid grid-cols-7 gap-1">
        {week.map((bucket) => {
          const shown = bucket.documents.slice(0, MAX_DOTS);
          const hidden = bucket.documents.length - shown.length;
          const isToday = bucket.date === today;
          return (
            <div key={bucket.date} className="flex flex-col items-center">
              <div className="flex h-32 w-full flex-col-reverse items-center gap-1.5 border-b border-line pb-2">
                {shown.map((doc) => (
                  <button
                    key={doc.projectId}
                    type="button"
                    title={`${doc.title} · ${doc.kind}`}
                    aria-label={`${doc.title} 열기`}
                    onClick={() => openLibraryDocument(doc.projectId, doc.artifactId)}
                    className={`size-3.5 shrink-0 rounded-full transition-transform hover:scale-125 ${kindTone(doc.kind).dot}`}
                  />
                ))}
                {hidden > 0 && <span className="text-[11px] text-label-alternative">+{hidden}</span>}
              </div>
              <span className={isToday ? "mt-1.5 text-[11px] font-semibold text-primary-strong" : "mt-1.5 text-[11px] text-label-alternative"}>
                {Number(bucket.date.slice(8))}
              </span>
              <span className={isToday ? "text-[11px] text-primary-strong" : "text-[11px] text-label-assistive"}>
                {isToday ? "오늘" : weekday(bucket.date)}
              </span>
            </div>
          );
        })}
      </div>
      {kinds.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-x-3 gap-y-1">
          {kinds.map((kind) => (
            <li key={kind} className="flex items-center gap-1.5 text-[11px] text-label-alternative">
              <span className={`size-2 rounded-full ${kindTone(kind).dot}`} aria-hidden />
              {kind}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

/** 홈의 추이: 지금까지 누적(선) + 최근 7일(날짜별 점). 최종본까지 끝낸 프로젝트 기준. */
export function ProjectTrends({ documents }: { documents: readonly LibraryDocument[] }) {
  const today = useMemo(() => toIsoDate(new Date()), []);
  return (
    <>
      <OverallTrend documents={documents} today={today} />
      <WeekDots documents={documents} today={today} />
    </>
  );
}
