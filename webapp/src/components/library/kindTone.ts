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
    tile: "bg-fill text-label-alternative",
    pill: "bg-fill text-label-neutral",
    dot: "bg-label-assistive",
    chipActive: "border-label bg-label text-white",
  },
  설명해설: {
    tile: "bg-accent-cyan/8 text-accent-cyan",
    pill: "bg-accent-cyan/8 text-accent-cyan",
    dot: "bg-accent-cyan",
    chipActive: "border-accent-cyan bg-accent-cyan text-white",
  },
  분석: {
    tile: "bg-accent-violet/8 text-accent-violet",
    pill: "bg-accent-violet/8 text-accent-violet",
    dot: "bg-accent-violet",
    chipActive: "border-accent-violet bg-accent-violet text-white",
  },
  평가비평: {
    tile: "bg-accent-red/8 text-accent-red",
    pill: "bg-accent-red/8 text-accent-red",
    dot: "bg-accent-red",
    chipActive: "border-accent-red bg-accent-red text-white",
  },
  제안설득: {
    tile: "bg-caution/8 text-caution-fg",
    pill: "bg-caution/8 text-caution-strong",
    dot: "bg-caution",
    chipActive: "border-caution bg-caution text-white",
  },
  안내절차: {
    tile: "bg-positive/8 text-positive-fg",
    pill: "bg-positive/8 text-positive-fg",
    dot: "bg-positive",
    chipActive: "border-positive bg-positive text-white",
  },
  서사소개: {
    tile: "bg-accent-pink/8 text-accent-pink",
    pill: "bg-accent-pink/8 text-accent-pink",
    dot: "bg-accent-pink",
    chipActive: "border-accent-pink bg-accent-pink text-white",
  },
  발표: {
    tile: "bg-primary/8 text-primary",
    pill: "bg-primary/8 text-primary-strong",
    dot: "bg-primary",
    chipActive: "border-primary bg-primary text-white",
  },
};

const FALLBACK: KindTone = {
  tile: "bg-fill text-label-alternative",
  pill: "bg-fill text-label-alternative",
  dot: "bg-label-assistive",
  chipActive: "border-label bg-label text-white",
};

export function kindTone(kind: string): KindTone {
  return TONES[kind] ?? FALLBACK;
}
