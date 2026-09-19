import type { AgentModelConfig } from "@/types";

/** 에이전트별 구분색. 이름·아바타 테두리·상태 점에만 쓰고 메시지 전체를 칠하지 않는다. */
export interface AgentAccent {
  text: string;
  soft: string;
  dot: string;
}

export interface AgentProfile {
  name: string;
  fullName: string;
  /** 위장 가족 설정 — 화면 장식용 */
  persona: string;
  /** DocuMaster 안에서 맡는 일 */
  role: string;
  description: string;
  accent: AgentAccent;
  /**
   * 실제 이미지를 쓰려면 public/avatars/에 파일을 넣고 경로를 적는다. 예: "/avatars/loid.png"
   * 비워 두면 components/agent/portraits.tsx의 SVG 초상을 쓴다.
   */
  avatarSrc?: string;
  defaultConfig: AgentModelConfig;
}

/** DocuMaster 팀(CLAUDE.md §1). 에이전트를 추가하면 portraits.tsx에도 초상을 하나 더한다. */
export const AGENT_PROFILES = {
  loid: {
    name: "로이드",
    fullName: "로이드 포저",
    persona: "아빠 · 스파이(황혼)",
    role: "총괄 · 게이트",
    description: "모드 판정과 기획(00·01), 검증 결과 채택, 게이트 판정, 최종 교차 확인을 맡습니다.",
    accent: { text: "text-teal-700", soft: "bg-teal-50", dot: "bg-teal-500" },
    defaultConfig: { provider: "anthropic", modelId: "claude-opus-5", reasoningLevel: "high" },
  },
  yor: {
    name: "요르",
    fullName: "요르 포저",
    persona: "엄마 · 암살자(가시공주)",
    role: "조사 · 세부기획",
    description: "유일한 사실 공급원입니다. 조사(02)·검증 응답(04)·세부 기획(06)·비주얼(06B)을 맡습니다.",
    accent: { text: "text-rose-700", soft: "bg-rose-50", dot: "bg-rose-500" },
    defaultConfig: { provider: "openai", modelId: "gpt-5.6-sol", reasoningLevel: "xhigh" },
  },
  yuri: {
    name: "유리",
    fullName: "유리 브라이어",
    persona: "친동생 · 비밀경찰",
    role: "독립 검증",
    description: "위험한 주장 10개 이하를 따져 묻고 출처 3건 이하를 직접 열어 검증(03·05)합니다.",
    accent: { text: "text-indigo-700", soft: "bg-indigo-50", dot: "bg-indigo-500" },
    defaultConfig: { provider: "anthropic", modelId: "claude-sonnet-5", reasoningLevel: "high" },
  },
  anya: {
    name: "아냐",
    fullName: "아냐 포저",
    persona: "딸 · 초능력자(마음읽기)",
    role: "문서 집필",
    description: "문서 모드 전용입니다. 세부 기획(06·06B)대로 최종 문서(07)를 쓰고 퇴고합니다.",
    accent: { text: "text-pink-700", soft: "bg-pink-50", dot: "bg-pink-400" },
    defaultConfig: { provider: "anthropic", modelId: "claude-opus-5", reasoningLevel: "high" },
  },
  bond: {
    name: "본드",
    fullName: "본드",
    persona: "반려견 · 예지력",
    role: "슬라이드 초안",
    description: "발표 모드 전용입니다. 발표팩을 NotebookLM으로 넘겨 슬라이드 초안을 만듭니다.",
    accent: { text: "text-amber-700", soft: "bg-amber-50", dot: "bg-amber-500" },
    defaultConfig: { provider: "google", modelId: "notebooklm", reasoningLevel: null },
  },
} as const satisfies Record<string, AgentProfile>;

export type AgentId = keyof typeof AGENT_PROFILES;

export const AGENT_IDS = Object.keys(AGENT_PROFILES) as AgentId[];

/** 사용자가 @를 붙이지 않았을 때 지시를 받는 에이전트 */
export const DEFAULT_ASSIGNEE: AgentId = "loid";

export function getAgentProfile(id: AgentId): AgentProfile {
  return AGENT_PROFILES[id];
}
