"use client";

import { MOBILE_TABS, type MobileTab } from "@/constants/navigation";
import { cn } from "@/lib/cn";

interface MobileTabBarProps {
  active: MobileTab;
  onChange: (tab: MobileTab) => void;
}

/** 휴대폰 화면 하단 탭. 패널을 동시에 다 보여 주지 않고 하나씩 바꿔 보여 준다. */
export function MobileTabBar({ active, onChange }: MobileTabBarProps) {
  return (
    <nav aria-label="모바일 탭" className="flex shrink-0 border-t border-line bg-white md:hidden">
      {MOBILE_TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          aria-current={active === tab.id ? "page" : undefined}
          className={cn(
            "flex-1 py-3 text-[13px] font-medium",
            active === tab.id ? "text-blue-600" : "text-gray-500",
          )}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
