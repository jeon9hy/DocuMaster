/* eslint-disable @next/next/no-img-element -- 작은 정적 로고라 next/image 최적화가 필요 없다 */
import { BRAND } from "@/constants/brand";

export function BrandLogo() {
  return (
    <div className="flex shrink-0 items-center gap-2">
      <img src={BRAND.markSrc} alt="" className="size-9" />
      <span className="hidden leading-none lg:block">
        {BRAND.wordmarkSrc ? (
          <img src={BRAND.wordmarkSrc} alt={BRAND.name} className="h-6 w-auto" />
        ) : (
          <span className="font-wordmark text-[22px] font-extrabold tracking-tight" aria-label={BRAND.name}>
            <span className="text-blue-600">docu</span>
            <span className="text-navy">master</span>
          </span>
        )}
        <span className="mt-1 block text-[11px] text-gray-500">{BRAND.tagline}</span>
      </span>
    </div>
  );
}
