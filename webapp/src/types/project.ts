import type { Agent } from "./agent";
import type { Artifact } from "./artifact";
import type { FeedItem } from "./feed";
import type { Reference } from "./reference";
import type { StageStatusMap } from "./workflow";

/** DOCUMENT = 그대로 제출할 최종본, PRESENTATION = 슬라이드 초안 + 발표팩 */
export type ProjectMode = "document" | "presentation";

export interface ProjectSummary {
  id: string;
  name: string;
  description: string;
  mode: ProjectMode;
}

/** 한 프로젝트 화면에 필요한 전부. 프로젝트를 바꾸면 이 객체가 통째로 바뀐다. */
export interface ProjectWorkspace {
  project: ProjectSummary;
  isRunning: boolean;
  stageStatus: StageStatusMap;
  agents: Agent[];
  feed: FeedItem[];
  references: Reference[];
  artifacts: Artifact[];
}

export interface NewProjectInput {
  name: string;
  mode: ProjectMode;
}
