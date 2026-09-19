/* eslint-disable @next/next/no-img-element -- 작은 정적 로고라 next/image 최적화가 필요 없다 */
import { BRAND } from "@/constants/brand";

/** 헤더 로고. 누르면 홈으로 간다. */
export function BrandLogo({ onHome }: { onHome: () => void }) {
  return (
    <button
      type="button"
      onClick={onHome}
      aria-label={`${BRAND.name} 홈으로`}
      className="flex shrink-0 items-center gap-2 rounded-lg p-0.5 focus-visible:outline-2 focus-visible:outline-blue-500"
    >
      <img src={BRAND.markSrc} alt="" className="size-9" />
      <span className="hidden leading-none lg:block">
        {BRAND.wordmarkSrc ? (
          <img src={BRAND.wordmarkSrc} alt="" className="h-6 w-auto" />
        ) : (
          <span className="font-wordmark text-[22px] font-extrabold tracking-tight">
            <span className="text-blue-600">docu</span>
            <span className="text-navy">master</span>
          </span>
        )}
      </span>
    </button>
  );
}
