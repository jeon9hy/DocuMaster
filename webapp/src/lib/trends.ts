import type { LibraryDocument } from "@/types";
import { toIsoDate } from "./library";

/** from~to(양 끝 포함) 날짜를 하루씩 YYYY-MM-DD로 */
export function dayRange(from: string, to: string): string[] {
  const days: string[] = [];
  const [fy, fm, fd] = from.split("-").map(Number);
  const cursor = new Date(fy, fm - 1, fd);
  for (let guard = 0; guard < 4000; guard += 1) {
    const iso = toIsoDate(cursor);
    if (iso > to) break;
    days.push(iso);
    cursor.setDate(cursor.getDate() + 1);
  }
  return days;
}

export interface CumulativePoint {
  date: string;
  /** 그날까지 만든 문서 수 */
  total: number;
  /** 그날 만든 문서 수 */
  added: number;
}

/** 첫 문서 날짜부터 오늘까지, 날마다 쌓인 문서 수. 문서가 없으면 빈 배열. */
export function cumulativeSeries(documents: readonly LibraryDocument[], today: string): CumulativePoint[] {
  if (documents.length === 0) return [];
  const perDay = new Map<string, number>();
  for (const doc of documents) perDay.set(doc.date, (perDay.get(doc.date) ?? 0) + 1);
  const first = [...perDay.keys()].sort()[0];
  let total = 0;
  return dayRange(first, today > first ? today : first).map((date) => {
    const added = perDay.get(date) ?? 0;
    total += added;
    return { date, total, added };
  });
}

export interface DayBucket {
  date: string;
  documents: LibraryDocument[];
}

/** 오늘 포함 최근 days일, 날짜별로 만든 문서(오래된 날이 먼저) */
export function lastDays(documents: readonly LibraryDocument[], days: number, today: string): DayBucket[] {
  const [y, m, d] = today.split("-").map(Number);
  const from = toIsoDate(new Date(y, m - 1, d - (days - 1)));
  return dayRange(from, today).map((date) => ({ date, documents: documents.filter((doc) => doc.date === date) }));
}
