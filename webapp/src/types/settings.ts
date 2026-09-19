import type { AgentId, AgentModelConfig, ReasoningLevel } from "./agent";

/** 단일 Owner 로그인 상태. 세션 토큰은 HttpOnly 쿠키에만 있고 화면은 모른다. */
export interface OwnerProfile {
  nickname: string;
  hasAvatar: boolean;
  updatedAt: string | null;
}

export interface AuthSession {
  /** Owner PIN이 설정되어 있는지(setup_owner.py) */
  configured: boolean;
  authenticated: boolean;
  /** PIN이 환경변수로 관리되어 화면에서 바꿀 수 없는지 */
  pinManagedByEnv: boolean;
  profile: OwnerProfile | null;
}

export interface ProfileUpdate {
  nickname?: string;
  avatar?: File;
  removeAvatar?: boolean;
}

/**
 * 에이전트 모델 설정(전역). 선택지는 오케스트레이터가 실제로 반영하는 값만 온다.
 * lockedReason이 있으면 루트 오케스트레이터가 고정한 값이라 바꿀 수 없다.
 */
export interface AgentSetting {
  agentId: AgentId;
  config: AgentModelConfig;
  defaultConfig: AgentModelConfig;
  overridden: boolean;
  updatedAt: string | null;
  modelIds: string[];
  /** null = 추론 강도를 넘기지 않음(도구 기본값) */
  reasoningLevels: (ReasoningLevel | null)[];
  /** 모델마다 지원 추론 강도가 다를 때(요르·Codex). 없으면 reasoningLevels를 모든 모델에 쓴다 */
  reasoningByModel: Record<string, ReasoningLevel[]> | null;
  lockedReason: string | null;
}

export interface UsageWindow {
  /** 공급자가 쓰는 이름(Codex: primary·secondary, Claude: five_hour·seven_day). 표시는 windowMinutes로 한다 */
  kind: string;
  usedPercent: number;
  windowMinutes: number | null;
  resetsAt: string | null;
  /** 리셋 시각이 지나 끝난 창의 값(Claude 캐시) */
  expired?: boolean;
}

/** 실제로 확인한 값만. available=false면 windows는 비어 있고 note에 이유가 있다. */
export interface ProviderUsage {
  provider: "anthropic" | "openai" | "google";
  label: string;
  available: boolean;
  /** 값이 지금과 다를 수 있다(리셋이 지난 창이 있음) */
  stale: boolean;
  windows: UsageWindow[];
  /** 이 값을 받은 시각(마지막 실행 기준) */
  observedAt: string | null;
  source: string | null;
  note: string;
  plan?: string | null;
  limitReached?: string | null;
}

/** 백엔드가 LLM을 부르지 않고 확인한 도구 상태(PATH에 있는지) */
export interface SystemHealth {
  orchestrator: string;
  missingTools: string[];
  /** CLI가 PATH에 있는지(설치 여부만 — 로그인·한도는 모른다) */
  tools: Record<"claude" | "codex" | "nlm", boolean>;
  activeRun: { id: string; projectId: string; status: string } | null;
}
