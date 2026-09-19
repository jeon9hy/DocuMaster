"use client";

import type { NavItem, ViewId } from "@/constants/navigation";
import { cn } from "@/lib/cn";

interface NavListProps {
  items: readonly NavItem[];
  activeView: ViewId;
  onSelect: (view: ViewId) => void;
}

export function NavList({ items, activeView, onSelect }: NavListProps) {
  return (
    <ul className="space-y-0.5">
      {items.map(({ id, label, icon: Icon }) => (
        <li key={id}>
          <button
            type="button"
            onClick={() => onSelect(id)}
            aria-current={activeView === id ? "page" : undefined}
            className={cn(
              "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
              activeView === id
                ? "bg-blue-50 font-medium text-blue-700"
                : "text-gray-700 hover:bg-gray-100",
            )}
          >
            <Icon className="size-4" aria-hidden />
            {label}
          </button>
        </li>
      ))}
    </ul>
  );
}
