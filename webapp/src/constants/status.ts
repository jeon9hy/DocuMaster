import type { AgentStatus, ArtifactStatus, StageStatus, SystemTone } from "@/types";

/** 모든 상태 배지의 모양. 색 계열: neutral(회색) · primary(파랑) · success · warning · danger */
export type BadgeVariant = "neutral" | "primary" | "success" | "warning" | "danger";

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
  working: { label: "진행 중", variant: "primary" },
  done: { label: "완료", variant: "success" },
  idle: { label: "대기", variant: "neutral" },
  error: { label: "오류", variant: "danger" },
};

export const TONE_VARIANT: Record<SystemTone, BadgeVariant> = {
  info: "neutral",
  success: "success",
  warning: "warning",
  error: "danger",
};
