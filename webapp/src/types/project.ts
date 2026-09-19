import type { Agent } from "./agent";
import type { Artifact } from "./artifact";
import type { FeedItem } from "./feed";
import type { Reference } from "./reference";
import type { StageStatusMap, WorkflowStageId } from "./workflow";

/** DOCUMENT = 그대로 제출할 최종본, PRESENTATION = 슬라이드 초안 + 발표팩 */
export type ProjectMode = "document" | "presentation";

/** 프로젝트를 만들 때 고르는 값. auto면 로이드가 요청을 읽고 판정한다(판정 전까지 auto). */
export type ProjectModeChoice = ProjectMode | "auto";

export interface ProjectSummary {
  id: string;
  name: string;
  description: string;
  mode: ProjectModeChoice;
  /** 기존 CLI 작업(작업/<ID>)을 가져와 보기만 하는 프로젝트 */
  readOnly?: boolean;
  /** 마지막 활동 시각(백엔드가 줄 때만) */
  lastActivityAt?: string;
}

/**
 * 실행 상태. 진행률(단계 상태로 계산)과 따로 둔다 — 같은 42%라도
 * 진행 중·입력 대기·중지 요청·오류가 다르기 때문이다.
 */
export type RunStatus =
  | "idle"
  | "running"
  | "awaitingInput"
  | "stopping"
  | "stopped"
  | "failed"
  | "completed";

/** 오케스트레이터가 사용자 판단을 기다릴 때(모드 애매·범위 충돌·검증 blocked·도구 설정 등) */
export interface UserInputRequest {
  promptId: string;
  title: string;
  message: string;
  /** 비어 있으면 자유 입력만 받는다 */
  choices: string[];
  allowFreeText: boolean;
  stageId?: WorkflowStageId;
}

/** 한 프로젝트 화면에 필요한 전부. 프로젝트를 바꾸면 이 객체가 통째로 바뀐다. */
export interface ProjectWorkspace {
  project: ProjectSummary;
  runStatus: RunStatus;
  stageStatus: StageStatusMap;
  agents: Agent[];
  feed: FeedItem[];
  references: Reference[];
  artifacts: Artifact[];
  pendingInputs: UserInputRequest[];
  /** 이 상태에 반영된 마지막 이벤트 번호. 이어 받기(replay)와 중복 제거에 쓴다. */
  lastEventSeq: number;
}

export interface NewProjectInput {
  name: string;
  mode: ProjectModeChoice;
}
