import { DEFAULT_VIEW, type ViewId } from "@/constants/navigation";
import { applyWorkflowEvent } from "@/lib/applyWorkflowEvent";
import type {
  ProjectSummary,
  ProjectWorkspace,
  WorkflowEvent,
  WorkflowStageId,
} from "@/types";

export type LoadStatus = "loading" | "success" | "error";

export interface AppState {
  projects: ProjectSummary[];
  projectId: string | null;
  workspace: ProjectWorkspace | null;
  workspaceStatus: LoadStatus;
  /** 값이 바뀌면 워크스페이스를 다시 불러온다(오류 후 재시도) */
  reloadToken: number;
  view: ViewId;
  /** 단계 상세를 펼친 단계. null이면 닫힘 */
  openStageId: WorkflowStageId | null;
  selectedArtifactId: string | null;
}

export type AppAction =
  | { type: "projects/loaded"; projects: ProjectSummary[] }
  | { type: "project/selected"; projectId: string }
  | { type: "workspace/loaded"; workspace: ProjectWorkspace }
  | { type: "workspace/failed" }
  | { type: "workspace/retried" }
  | { type: "event/received"; event: WorkflowEvent }
  | { type: "view/changed"; view: ViewId }
  | { type: "stage/toggled"; stageId: WorkflowStageId }
  | { type: "artifact/selected"; artifactId: string };

export const initialAppState: AppState = {
  projects: [],
  projectId: null,
  workspace: null,
  workspaceStatus: "loading",
  reloadToken: 0,
  view: DEFAULT_VIEW,
  openStageId: null,
  selectedArtifactId: null,
};

/** 가장 최근에 완성된 작업물을 기본 미리보기로 */
function pickDefaultArtifact(workspace: ProjectWorkspace): string | null {
  const latest = workspace.artifacts.filter((artifact) => artifact.status === "latest");
  return latest.at(-1)?.id ?? workspace.artifacts[0]?.id ?? null;
}

export function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "projects/loaded":
      return { ...state, projects: action.projects };

    case "project/selected":
      if (action.projectId === state.projectId) return state;
      return {
        ...state,
        projectId: action.projectId,
        workspace: null,
        workspaceStatus: "loading",
        openStageId: null,
        selectedArtifactId: null,
      };

    case "workspace/loaded":
      if (action.workspace.project.id !== state.projectId) return state;
      return {
        ...state,
        workspace: action.workspace,
        workspaceStatus: "success",
        selectedArtifactId: pickDefaultArtifact(action.workspace),
      };

    case "workspace/failed":
      return { ...state, workspaceStatus: "error" };

    case "workspace/retried":
      return { ...state, workspaceStatus: "loading", reloadToken: state.reloadToken + 1 };

    case "event/received":
      // 다른 프로젝트로 넘어간 뒤 늦게 도착한 이벤트는 버린다.
      if (!state.workspace || action.event.projectId !== state.projectId) return state;
      return { ...state, workspace: applyWorkflowEvent(state.workspace, action.event) };

    case "view/changed":
      return { ...state, view: action.view };

    case "stage/toggled":
      return {
        ...state,
        openStageId: state.openStageId === action.stageId ? null : action.stageId,
      };

    case "artifact/selected":
      return { ...state, selectedArtifactId: action.artifactId };
  }
}
