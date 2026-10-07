import { DEFAULT_VIEW, GLOBAL_NAV, type ViewId } from "@/constants/navigation";
import { applyWorkflowEvent } from "@/lib/applyWorkflowEvent";
import type { ConnectionState } from "@/services/WorkspaceService";
import type {
  AuthSession,
  ProjectSummary,
  ProjectWorkspace,
  WorkflowEvent,
  WorkflowStageId,
} from "@/types";

export type LoadStatus = "loading" | "success" | "error";

export interface AppState {
  projects: ProjectSummary[];
  /** 프로젝트 목록을 한 번이라도 받았는지(0개일 때 「로딩 중」과 구분) */
  projectsLoaded: boolean;
  /** 로그인 상태. null = 아직 확인 전(그동안은 Guest처럼 잠가 둔다) */
  session: AuthSession | null;
  projectId: string | null;
  workspace: ProjectWorkspace | null;
  workspaceStatus: LoadStatus;
  /** 값이 바뀌면 워크스페이스를 다시 불러온다(오류 후 재시도) */
  reloadToken: number;
  view: ViewId;
  /** 단계 상세를 펼친 단계. null이면 닫힘 */
  openStageId: WorkflowStageId | null;
  selectedArtifactId: string | null;
  /** 라이브러리에서 연 문서. 워크스페이스가 로드되면 이 작업물을 고른다 */
  pendingArtifactId: string | null;
  /** 실시간 이벤트 연결. 끊기면 화면에 「재연결 중」을 보여 준다. */
  connection: ConnectionState;
}

export type AppAction =
  | { type: "projects/loaded"; projects: ProjectSummary[] }
  | { type: "session/changed"; session: AuthSession }
  /** keepView: 처음 열 때 주소의 프로젝트를 이어받는 경우 — 보던 화면을 바꾸지 않는다 */
  | { type: "project/selected"; projectId: string; keepView?: boolean }
  | { type: "library/opened"; projectId: string; artifactId: string | null }
  | { type: "project/cleared" }
  | { type: "workspace/loaded"; workspace: ProjectWorkspace }
  | { type: "workspace/failed" }
  | { type: "workspace/retried" }
  | { type: "event/received"; event: WorkflowEvent }
  | { type: "view/changed"; view: ViewId }
  | { type: "stage/toggled"; stageId: WorkflowStageId }
  | { type: "artifact/selected"; artifactId: string }
  | { type: "connection/changed"; connection: ConnectionState };

export const initialAppState: AppState = {
  projects: [],
  projectsLoaded: false,
  session: null,
  projectId: null,
  workspace: null,
  workspaceStatus: "loading",
  reloadToken: 0,
  view: DEFAULT_VIEW,
  openStageId: null,
  selectedArtifactId: null,
  pendingArtifactId: null,
  connection: "connected",
};

/** 가장 최근에 완성된 작업물을 기본 미리보기로 */
function pickDefaultArtifact(workspace: ProjectWorkspace): string | null {
  const latest = workspace.artifacts.filter((artifact) => artifact.status === "latest");
  return latest.at(-1)?.id ?? workspace.artifacts[0]?.id ?? null;
}

export function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "projects/loaded":
      return { ...state, projects: action.projects, projectsLoaded: true };

    case "session/changed":
      return { ...state, session: action.session };

    case "project/selected": {
      // 프로젝트를 골라 들어오면 기본 화면은 대시보드. 이미 프로젝트 안 화면(대화·작업물…)에 있으면 그대로 둔다
      const view =
        !action.keepView && GLOBAL_NAV.some((item) => item.id === state.view) ? "dashboard" : state.view;
      if (action.projectId === state.projectId) return view === state.view ? state : { ...state, view };
      return {
        ...state,
        view,
        projectId: action.projectId,
        workspace: null,
        workspaceStatus: "loading",
        openStageId: null,
        selectedArtifactId: null,
        pendingArtifactId: null,
      };
    }

    case "library/opened":
      // 같은 프로젝트면 워크스페이스를 다시 받지 않고 고르기만 한다
      if (action.projectId === state.projectId) {
        return { ...state, view: "artifacts", selectedArtifactId: action.artifactId ?? state.selectedArtifactId };
      }
      return {
        ...state,
        view: "artifacts",
        projectId: action.projectId,
        workspace: null,
        workspaceStatus: "loading",
        openStageId: null,
        selectedArtifactId: null,
        pendingArtifactId: action.artifactId,
      };

    case "project/cleared":
      return { ...state, projectId: null, workspace: null, openStageId: null, selectedArtifactId: null };

    case "workspace/loaded":
      if (action.workspace.project.id !== state.projectId) return state;
      return {
        ...state,
        workspace: action.workspace,
        workspaceStatus: "success",
        selectedArtifactId:
          state.pendingArtifactId && action.workspace.artifacts.some((item) => item.id === state.pendingArtifactId)
            ? state.pendingArtifactId
            : pickDefaultArtifact(action.workspace),
        pendingArtifactId: null,
      };

    case "workspace/failed":
      return { ...state, workspaceStatus: "error" };

    case "workspace/retried":
      return { ...state, workspaceStatus: "loading", reloadToken: state.reloadToken + 1 };

    case "event/received": {
      // 다른 프로젝트로 넘어간 뒤 늦게 도착한 이벤트는 버린다. 이미 반영한 seq도 버린다.
      if (!state.workspace || action.event.projectId !== state.projectId) return state;
      const workspace = applyWorkflowEvent(state.workspace, action.event);
      if (workspace === state.workspace) return state;
      const selectedArtifactId =
        state.selectedArtifactId && !workspace.artifacts.some((item) => item.id === state.selectedArtifactId)
          ? pickDefaultArtifact(workspace)
          : state.selectedArtifactId;
      return { ...state, workspace, selectedArtifactId };
    }

    case "connection/changed":
      return state.connection === action.connection ? state : { ...state, connection: action.connection };

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
