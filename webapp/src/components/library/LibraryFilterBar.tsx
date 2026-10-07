"use client";

import { Check, ChevronDown, X } from "lucide-react";
import {
  DOCUMENT_KINDS,
  EMPTY_LIBRARY_FILTER,
  LIBRARY_DATE_PRESETS,
  LIBRARY_FILTER_FIELDS,
  documentKindLabel,
} from "@/constants/library";
import { cn } from "@/lib/cn";
import { daysAgo, formatShortDate, toIsoDate } from "@/lib/library";
import type { LibraryFilter, LibraryFilterField } from "@/types";
import { Dropdown, DropdownItem } from "../ui/Dropdown";
import { SearchField } from "../ui/Field";
import { kindTone } from "./kindTone";

interface LibraryFilterBarProps {
  field: LibraryFilterField;
  onFieldChange: (field: LibraryFilterField) => void;
  filter: LibraryFilter;
  onFilterChange: (filter: LibraryFilter) => void;
  /** 유형 칩 옆 숫자 */
  kindCounts: Map<string, number>;
}

const CHIP = "inline-flex h-8 items-center gap-1.5 rounded-full border px-3 text-[13px] font-medium transition-colors";
const DATE_INPUT =
  "h-10 w-full min-w-0 rounded-lg border border-line bg-surface px-3 text-sm text-label-neutral [color-scheme:light] hover:border-line focus:border-primary focus:ring-2 focus:ring-primary/16 focus:outline-none";

/** 드롭다운으로 필터 종류(제목·날짜·유형)를 고르고, 고른 종류에 맞는 입력을 보여 준다. 세 조건은 함께 적용된다. */
export function LibraryFilterBar({ field, onFieldChange, filter, onFilterChange, kindCounts }: LibraryFilterBarProps) {
  const current = LIBRARY_FILTER_FIELDS.find((item) => item.id === field) ?? LIBRARY_FILTER_FIELDS[0];
  const update = (patch: Partial<LibraryFilter>) => onFilterChange({ ...filter, ...patch });

  return (
    <section className="rounded-2xl border border-line bg-surface p-3 shadow-sm shadow-primary-heavy/[0.03]">
      <div className="flex flex-col gap-2.5 @lg:flex-row @lg:items-start">
        <Dropdown
          trigger={({ open, toggle }) => (
            <button
              type="button"
              onClick={toggle}
              aria-haspopup="menu"
              aria-expanded={open}
              aria-label={`필터 종류: ${current.label}`}
              className={cn(
                "flex h-10 w-full items-center gap-2 rounded-lg border bg-primary/4 px-3 text-sm font-semibold text-primary-strong transition-colors @lg:w-28",
                open ? "border-primary" : "border-primary/16 hover:border-primary/43",
              )}
            >
              <current.icon className="size-4" aria-hidden />
              <span className="flex-1 text-left">{current.label}</span>
              <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} aria-hidden />
            </button>
          )}
          className="min-w-40"
        >
          {(close) =>
            LIBRARY_FILTER_FIELDS.map((item) => (
              <DropdownItem
                key={item.id}
                active={item.id === field}
                onSelect={() => {
                  onFieldChange(item.id);
                  close();
                }}
              >
                <item.icon className="size-4" aria-hidden />
                <span className="flex-1">{item.label}</span>
                {item.id === field && <Check className="size-4" aria-hidden />}
              </DropdownItem>
            ))
          }
        </Dropdown>

        <div className="min-w-0 flex-1">
          {field === "title" && (
            <SearchField
              autoFocus
              value={filter.title}
              onChange={(event) => update({ title: event.target.value })}
              onClear={() => update({ title: "" })}
              placeholder="제목이나 요청 내용으로 찾기"
              aria-label="제목 검색"
            />
          )}

          {field === "date" && (
            <div className="flex flex-col gap-2.5">
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={filter.dateFrom}
                  max={filter.dateTo || undefined}
                  onChange={(event) => update({ dateFrom: event.target.value })}
                  aria-label="시작 날짜"
                  className={DATE_INPUT}
                />
                <span className="shrink-0 text-sm text-label-alternative">~</span>
                <input
                  type="date"
                  value={filter.dateTo}
                  min={filter.dateFrom || undefined}
                  onChange={(event) => update({ dateTo: event.target.value })}
                  aria-label="끝 날짜"
                  className={DATE_INPUT}
                />
              </div>
              <div className="flex flex-wrap gap-1.5">
                {LIBRARY_DATE_PRESETS.map((preset) => {
                  const from = daysAgo(preset.days);
                  const to = toIsoDate(new Date());
                  const active = filter.dateFrom === from && filter.dateTo === to;
                  return (
                    <button
                      key={preset.id}
                      type="button"
                      aria-pressed={active}
                      onClick={() => update(active ? { dateFrom: "", dateTo: "" } : { dateFrom: from, dateTo: to })}
                      className={cn(
                        CHIP,
                        active
                          ? "border-primary bg-primary text-white"
                          : "border-line bg-surface text-label-alternative hover:border-primary/43 hover:text-primary-strong",
                      )}
                    >
                      {preset.label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {field === "kind" && (
            <div className="flex flex-wrap gap-1.5 py-1">
              {DOCUMENT_KINDS.map((kind) => {
                const count = kindCounts.get(kind.id) ?? 0;
                const active = filter.kinds.includes(kind.id);
                const tone = kindTone(kind.id);
                return (
                  <button
                    key={kind.id}
                    type="button"
                    aria-pressed={active}
                    disabled={count === 0 && !active}
                    onClick={() =>
                      update({
                        kinds: active ? filter.kinds.filter((id) => id !== kind.id) : [...filter.kinds, kind.id],
                      })
                    }
                    className={cn(
                      CHIP,
                      "disabled:cursor-not-allowed disabled:opacity-40",
                      active ? tone.chipActive : "border-line bg-surface text-label-alternative hover:border-line",
                    )}
                  >
                    <span className={cn("size-2 rounded-full", tone.dot)} aria-hidden />
                    {kind.label}
                    <span className={cn("text-xs", active ? "opacity-80" : "text-label-alternative")}>{count}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <ActiveFilters filter={filter} onFilterChange={onFilterChange} onFieldChange={onFieldChange} />
    </section>
  );
}

/** 지금 걸린 조건. 다른 종류를 보고 있어도 무엇이 걸려 있는지 보이게 한다. */
function ActiveFilters({
  filter,
  onFilterChange,
  onFieldChange,
}: {
  filter: LibraryFilter;
  onFilterChange: (filter: LibraryFilter) => void;
  onFieldChange: (field: LibraryFilterField) => void;
}) {
  const chips: { id: LibraryFilterField; label: string; clear: Partial<LibraryFilter> }[] = [];
  if (filter.title.trim()) chips.push({ id: "title", label: `제목 “${filter.title.trim()}”`, clear: { title: "" } });
  if (filter.dateFrom || filter.dateTo) {
    const from = filter.dateFrom ? formatShortDate(filter.dateFrom) : "처음";
    const to = filter.dateTo ? formatShortDate(filter.dateTo) : "오늘";
    chips.push({ id: "date", label: `날짜 ${from} ~ ${to}`, clear: { dateFrom: "", dateTo: "" } });
  }
  if (filter.kinds.length > 0) {
    chips.push({ id: "kind", label: `유형 ${filter.kinds.map(documentKindLabel).join(", ")}`, clear: { kinds: [] } });
  }
  if (chips.length === 0) return null;

  return (
    <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-line pt-3">
      {chips.map((chip) => (
        <span
          key={chip.id}
          className="inline-flex h-7 items-center gap-1 rounded-full bg-primary/8 pr-1 pl-1 text-xs font-medium text-primary-strong"
        >
          <button
            type="button"
            onClick={() => onFieldChange(chip.id)}
            className="rounded-full px-2 py-1 hover:underline"
          >
            {chip.label}
          </button>
          <button
            type="button"
            onClick={() => onFilterChange({ ...filter, ...chip.clear })}
            aria-label={`${chip.label} 조건 지우기`}
            className="flex size-5 items-center justify-center rounded-full hover:bg-primary/12"
          >
            <X className="size-3" aria-hidden />
          </button>
        </span>
      ))}
      {chips.length > 1 && (
        <button
          type="button"
          onClick={() => onFilterChange(EMPTY_LIBRARY_FILTER)}
          className="ml-1 text-xs font-medium text-label-alternative hover:text-label-neutral"
        >
          모두 지우기
        </button>
      )}
    </div>
  );
}
