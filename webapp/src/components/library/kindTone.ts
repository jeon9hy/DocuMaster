/** 유형별 색. 라이브러리 화면 안에서만 쓰는 구분색이라 Badge의 상태 색과 따로 둔다. */
interface KindTone {
  /** 카드 왼쪽 아이콘 칸 */
  tile: string;
  /** 카드의 유형 표시 */
  pill: string;
  /** 칩·표시의 점 */
  dot: string;
  /** 눌린 유형 칩 */
  chipActive: string;
}

const TONES: Record<string, KindTone> = {
  현황기록: {
    tile: "bg-slate-100 text-slate-600",
    pill: "bg-slate-100 text-slate-700",
    dot: "bg-slate-400",
    chipActive: "border-slate-500 bg-slate-600 text-white",
  },
  설명해설: {
    tile: "bg-sky-50 text-sky-600",
    pill: "bg-sky-50 text-sky-700",
    dot: "bg-sky-400",
    chipActive: "border-sky-500 bg-sky-600 text-white",
  },
  분석: {
    tile: "bg-violet-50 text-violet-600",
    pill: "bg-violet-50 text-violet-700",
    dot: "bg-violet-400",
    chipActive: "border-violet-500 bg-violet-600 text-white",
  },
  평가비평: {
    tile: "bg-rose-50 text-rose-600",
    pill: "bg-rose-50 text-rose-700",
    dot: "bg-rose-400",
    chipActive: "border-rose-500 bg-rose-600 text-white",
  },
  제안설득: {
    tile: "bg-amber-50 text-amber-600",
    pill: "bg-amber-50 text-amber-700",
    dot: "bg-amber-400",
    chipActive: "border-amber-500 bg-amber-500 text-white",
  },
  안내절차: {
    tile: "bg-emerald-50 text-emerald-600",
    pill: "bg-emerald-50 text-emerald-700",
    dot: "bg-emerald-400",
    chipActive: "border-emerald-500 bg-emerald-600 text-white",
  },
  서사소개: {
    tile: "bg-pink-50 text-pink-600",
    pill: "bg-pink-50 text-pink-700",
    dot: "bg-pink-400",
    chipActive: "border-pink-500 bg-pink-500 text-white",
  },
  발표: {
    tile: "bg-blue-50 text-blue-600",
    pill: "bg-blue-50 text-blue-700",
    dot: "bg-blue-500",
    chipActive: "border-blue-500 bg-blue-600 text-white",
  },
};

const FALLBACK: KindTone = {
  tile: "bg-gray-100 text-gray-500",
  pill: "bg-gray-100 text-gray-600",
  dot: "bg-gray-400",
  chipActive: "border-gray-500 bg-gray-600 text-white",
};

export function kindTone(kind: string): KindTone {
  return TONES[kind] ?? FALLBACK;
}
