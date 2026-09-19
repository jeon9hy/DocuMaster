import type { AgentStatus, ArtifactStatus, RunStatus, StageStatus, SystemTone } from "@/types";

/** 모든 상태 배지의 모양. 색 계열: neutral(회색) · primary(파랑) · success · warning · danger · rest(연보라) */
export type BadgeVariant = "neutral" | "primary" | "success" | "warning" | "danger" | "rest";

export interface StatusMeta {
  label: string;
  variant: BadgeVariant;
}

export const STAGE_STATUS: Record<StageStatus, StatusMeta> = {
  completed: { label: "완료", variant: "success" },
  running: { label: "진행 중", variant: "primary" },
  pending: { label: "대기", variant: "neutral" },
  error: { label: "오류", variant: "danger" },
};

export const ARTIFACT_STATUS: Record<ArtifactStatus, StatusMeta> = {
  latest: { label: "최신", variant: "success" },
  writing: { label: "작성 중", variant: "primary" },
  pending: { label: "대기", variant: "neutral" },
  error: { label: "오류", variant: "danger" },
};

export const AGENT_STATUS: Record<AgentStatus, StatusMeta> = {
  working: { label: "작업 중", variant: "primary" },
  done: { label: "완료", variant: "success" },
  idle: { label: "대기", variant: "neutral" },
  error: { label: "오류", variant: "danger" },
};

/**
 * 멤버 카드에만 쓰는 화면 상태. 실행 상태가 아니라 표시일 뿐이다.
 * - awaitingInput: 로이드가 사용자 답을 기다림
 * - resting: 이 프로젝트 모드에서 쓰지 않는 에이전트(부르지 않는다)
 */
export type AgentDisplayStatus = AgentStatus | "awaitingInput" | "resting";

export const AGENT_DISPLAY_STATUS: Record<AgentDisplayStatus, StatusMeta> = {
  ...AGENT_STATUS,
  awaitingInput: { label: "입력 필요", variant: "warning" },
  resting: { label: "💤 휴식 중", variant: "rest" },
};

/** 휴식 중 카드의 한 줄. 모드마다 쉬는 이유가 다르다. */
export const RESTING_NOTE = {
  document: "문서 업무라 잠깐 자러 갔어요.",
  presentation: "발표 업무라 잠깐 자러 갔어요.",
} as const;

export const RESTING_TOOLTIP = "이 에이전트는 현재 프로젝트 모드에서 사용되지 않습니다.";

/** 헤더의 실행 상태 배지. 진행률과 따로 보여 준다. */
export const RUN_STATUS: Record<RunStatus, StatusMeta & { hint: string }> = {
  idle: { label: "대기", variant: "neutral", hint: "아직 실행하지 않았습니다." },
  running: { label: "진행 중", variant: "primary", hint: "에이전트가 작업하고 있습니다." },
  awaitingInput: { label: "입력 필요", variant: "warning", hint: "사용자의 판단을 기다리고 있습니다." },
  stopping: { label: "중지 요청됨", variant: "warning", hint: "현재 단계가 끝나면 멈춥니다." },
  stopped: { label: "중지됨", variant: "neutral", hint: "다시 실행하면 멈춘 단계부터 이어서 합니다." },
  failed: { label: "오류", variant: "danger", hint: "오류로 멈췄습니다. 피드의 오류 내용을 확인하세요." },
  completed: { label: "완료", variant: "success", hint: "모든 단계를 마쳤습니다." },
};

export const TONE_VARIANT: Record<SystemTone, BadgeVariant> = {
  info: "neutral",
  success: "success",
  warning: "warning",
  error: "danger",
};
