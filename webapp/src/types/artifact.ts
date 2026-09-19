import type { AgentId } from "./agent";
import type { WorkflowStageId } from "./workflow";

export type ArtifactFileType = "markdown" | "pdf" | "image" | "pptx" | "file";

export type ArtifactStatus = "latest" | "writing" | "pending" | "error";

/** primary = 기본 목록(00·01·02·05·07·최종), internal = 「전체 보기」에서만(03·04·06·옛 버전 등) */
export type ArtifactVisibility = "primary" | "internal";

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
  /** 없으면 primary */
  visibility?: ArtifactVisibility;
}

export type ArtifactContent =
  | { type: "markdown"; text: string }
  /** src가 있으면 실제 PDF를 브라우저 기본 뷰어로, 없으면(목업) 표지 모양 썸네일 */
  | { type: "pdf"; title: string; subtitle: string; pageCount: number; src?: string }
  | { type: "image"; src: string; alt: string }
  /** 브라우저에서 미리 볼 수 없는 파일(pptx 등) — 내려받기만 */
  | { type: "file"; fileName: string; sizeBytes: number; downloadUrl: string };
