"use client";

import { useId } from "react";
import { APPLY_POLICIES } from "@/constants/references";
import { cn } from "@/lib/cn";
import type { ReferenceApplyPolicy } from "@/types";

/** 새 레퍼런스를 언제 반영할지 고르는 라디오 묶음 */
export function ApplyPolicyField({
  value,
  onChange,
}: {
  value: ReferenceApplyPolicy;
  onChange: (policy: ReferenceApplyPolicy) => void;
}) {
  const name = useId();
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-medium text-label-neutral">새 레퍼런스를 어떻게 반영할까요?</legend>
      <div className="space-y-1.5">
        {APPLY_POLICIES.map((policy) => (
          <label
            key={policy.id}
            className={cn(
              "flex cursor-pointer gap-2.5 rounded-lg border px-3 py-2",
              value === policy.id ? "border-primary/43 bg-primary/4" : "border-line",
            )}
          >
            <input
              type="radio"
              name={name}
              className="mt-0.5 accent-primary"
              checked={value === policy.id}
              onChange={() => onChange(policy.id)}
            />
            <span>
              <span className="block text-sm text-label-neutral">{policy.label}</span>
              <span className="block text-xs text-label-alternative">{policy.hint}</span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
