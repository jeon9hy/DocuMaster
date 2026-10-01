import type { LibraryDocument, LibraryFilter } from "@/types";

/** 띄어쓰기·대소문자를 무시하고 비교한다(「포켓몬 역사」로 「포켓몬스터의역사」도 찾게) */
function normalize(text: string): string {
  return text.toLowerCase().replace(/\s+/g, "");
}

/** 제목 검색은 제목·원문 요청·작업 ID를 함께 본다. 날짜는 양 끝을 포함한다. */
export function filterLibrary(documents: readonly LibraryDocument[], filter: LibraryFilter): LibraryDocument[] {
  const query = normalize(filter.title);
  const kinds = new Set(filter.kinds);
  return documents.filter((doc) => {
    if (query && ![doc.title, doc.request, doc.workspaceId].some((text) => normalize(text).includes(query))) {
      return false;
    }
    if (filter.dateFrom && doc.date < filter.dateFrom) return false;
    if (filter.dateTo && doc.date > filter.dateTo) return false;
    if (kinds.size > 0 && !kinds.has(doc.kind)) return false;
    return true;
  });
}

/** 유형별 문서 수(필터 칩에 숫자로 보인다) */
export function countByKind(documents: readonly LibraryDocument[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const doc of documents) counts.set(doc.kind, (counts.get(doc.kind) ?? 0) + 1);
  return counts;
}

/** 「2026년 10월」처럼 월 단위로 묶는다. 입력 순서(최신순)를 유지한다. */
export function groupByMonth(documents: readonly LibraryDocument[]): { key: string; label: string; items: LibraryDocument[] }[] {
  const groups: { key: string; label: string; items: LibraryDocument[] }[] = [];
  for (const doc of documents) {
    const key = doc.date.slice(0, 7);
    let group = groups.at(-1);
    if (!group || group.key !== key) {
      const [year, month] = key.split("-");
      group = { key, label: `${year}년 ${Number(month)}월`, items: [] };
      groups.push(group);
    }
    group.items.push(doc);
  }
  return groups;
}

/** 오늘 포함 days일 전 날짜(YYYY-MM-DD, 로컬 시간) */
export function daysAgo(days: number, today: Date = new Date()): string {
  const date = new Date(today.getFullYear(), today.getMonth(), today.getDate() - (days - 1));
  return toIsoDate(date);
}

export function toIsoDate(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

/** 2026-10-01 → 10월 1일 */
export function formatShortDate(iso: string): string {
  const [, month, day] = iso.split("-");
  return `${Number(month)}월 ${Number(day)}일`;
}
