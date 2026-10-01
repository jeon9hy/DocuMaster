import { CalendarDays, Search, Shapes, type LucideIcon } from "lucide-react";
import type { LibraryFilter, LibraryFilterField } from "@/types";

export const LIBRARY_FILTER_FIELDS: readonly { id: LibraryFilterField; label: string; icon: LucideIcon }[] = [
  { id: "title", label: "제목", icon: Search },
  { id: "date", label: "날짜", icon: CalendarDays },
  { id: "kind", label: "유형", icon: Shapes },
];

export const DEFAULT_LIBRARY_FIELD: LibraryFilterField = "title";

export const EMPTY_LIBRARY_FILTER: LibraryFilter = { title: "", dateFrom: "", dateTo: "", kinds: [] };

/** 날짜 빠른 선택. days = 오늘 포함 며칠 전부터 */
export const LIBRARY_DATE_PRESETS: readonly { id: string; label: string; days: number }[] = [
  { id: "7d", label: "최근 7일", days: 7 },
  { id: "30d", label: "최근 30일", days: 30 },
  { id: "90d", label: "최근 3개월", days: 90 },
];

/**
 * 유형 폴더 이름(`최종/<유형>/`) → 화면 이름. 순서는 루트 `.claude/공통/글유형.md`를 따르고 발표를 끝에 둔다.
 * 여기 없는 폴더(옛 배치의 「미분류」 등)가 오면 이름 그대로 보인다.
 */
export const DOCUMENT_KINDS: readonly { id: string; label: string }[] = [
  { id: "현황기록", label: "현황·기록" },
  { id: "설명해설", label: "설명·해설" },
  { id: "분석", label: "분석" },
  { id: "평가비평", label: "평가·비평" },
  { id: "제안설득", label: "제안·설득" },
  { id: "안내절차", label: "안내·절차" },
  { id: "서사소개", label: "서사·소개" },
  { id: "발표", label: "발표" },
];

export function documentKindLabel(kind: string): string {
  return DOCUMENT_KINDS.find((item) => item.id === kind)?.label ?? kind;
}
