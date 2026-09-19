import type { AgentId } from "./agent";
import type { WorkflowStageId } from "./workflow";

export type ArtifactFileType = "markdown" | "pdf" | "image";

export type ArtifactStatus = "latest" | "writing" | "pending" | "error";

/** 목록에 필요한 메타데이터만. 본문은 ArtifactContent로 필요할 때 따로 불러온다. */
export interface Artifact {
  id: string;
  name: string;
  fileType: ArtifactFileType;
  status: ArtifactStatus;
  stageId: WorkflowStageId;
  agentId: AgentId;
  summary: string;
  updatedAt: string;
}

export type ArtifactContent =
  | { type: "markdown"; text: string }
  | { type: "pdf"; title: string; subtitle: string; pageCount: number }
  | { type: "image"; src: string; alt: string };
