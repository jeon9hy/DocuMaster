"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  type ReactNode,
} from "react";
import type { ViewId } from "@/constants/navigation";
import { workspaceService } from "@/services";
import type {
  AgentId,
  AgentModelConfig,
  NewProjectInput,
  NewReferenceInput,
  ProjectWorkspace,
  WorkflowStageId,
} from "@/types";
import { appReducer, initialAppState, type AppState } from "./appReducer";

export interface AppActions {
  selectProject(projectId: string): void;
  createProject(input: NewProjectInput): Promise<void>;
  reloadWorkspace(): void;
  setView(view: ViewId): void;
  toggleStage(stageId: WorkflowStageId): void;
  selectArtifact(artifactId: string): void;
  runWorkflow(): Promise<void>;
  stopWorkflow(): Promise<void>;
  sendMessage(text: string, mentionedAgentId?: AgentId): Promise<void>;
  addReference(input: NewReferenceInput): Promise<void>;
  updateAgentConfig(agentId: AgentId, config: AgentModelConfig): Promise<void>;
}

// 상태와 동작을 다른 Context로 나눠, 동작만 쓰는 컴포넌트는 상태가 바뀌어도 다시 그리지 않게 한다.
const StateContext = createContext<AppState | null>(null);
const ActionsContext = createContext<AppActions | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialAppState);
  const { projectId, reloadToken } = state;

  const loadProjects = useCallback(async (selectId?: string) => {
    const projects = await workspaceService.listProjects();
    dispatch({ type: "projects/loaded", projects });
    const target = selectId ?? projects[0]?.id;
    if (target) dispatch({ type: "project/selected", projectId: target });
  }, []);

  useEffect(() => {
    loadProjects().catch(() => dispatch({ type: "workspace/failed" }));
  }, [loadProjects]);

  // 프로젝트가 바뀔 때만 스냅샷을 한 번 받고, 이후 변화는 이벤트 구독으로만 받는다(중복 조회 없음).
  useEffect(() => {
    if (!projectId) return;
    let unsubscribe: (() => void) | undefined;
    let cancelled = false;

    workspaceService
      .getWorkspace(projectId)
      .then((workspace) => {
        if (cancelled) return;
        dispatch({ type: "workspace/loaded", workspace });
        unsubscribe = workspaceService.subscribe(projectId, (event) =>
          dispatch({ type: "event/received", event }),
        );
      })
      .catch(() => !cancelled && dispatch({ type: "workspace/failed" }));

    return () => {
      cancelled = true;
      unsubscribe?.();
    };
  }, [projectId, reloadToken]);

  const actions = useMemo<AppActions>(() => {
    const requireProject = () => {
      if (!projectId) throw new Error("선택된 프로젝트가 없습니다.");
      return projectId;
    };
    return {
      selectProject: (id) => dispatch({ type: "project/selected", projectId: id }),
      createProject: async (input) => {
        const created = await workspaceService.createProject(input);
        await loadProjects(created.id);
      },
      reloadWorkspace: () => {
        dispatch({ type: "workspace/retried" });
        if (!projectId) loadProjects().catch(() => dispatch({ type: "workspace/failed" }));
      },
      setView: (view) => dispatch({ type: "view/changed", view }),
      toggleStage: (stageId) => dispatch({ type: "stage/toggled", stageId }),
      selectArtifact: (artifactId) => dispatch({ type: "artifact/selected", artifactId }),
      runWorkflow: () => workspaceService.runWorkflow(requireProject()),
      stopWorkflow: () => workspaceService.stopWorkflow(requireProject()),
      sendMessage: (text, agentId) => workspaceService.sendMessage(requireProject(), text, agentId),
      addReference: (input) => workspaceService.addReference(requireProject(), input),
      updateAgentConfig: (agentId, config) =>
        workspaceService.updateAgentConfig(requireProject(), agentId, config),
    };
  }, [projectId, loadProjects]);

  return (
    <ActionsContext.Provider value={actions}>
      <StateContext.Provider value={state}>{children}</StateContext.Provider>
    </ActionsContext.Provider>
  );
}

export function useAppState(): AppState {
  const state = useContext(StateContext);
  if (!state) throw new Error("useAppState는 WorkspaceProvider 안에서만 쓸 수 있습니다.");
  return state;
}

export function useAppActions(): AppActions {
  const actions = useContext(ActionsContext);
  if (!actions) throw new Error("useAppActions는 WorkspaceProvider 안에서만 쓸 수 있습니다.");
  return actions;
}

/** 워크스페이스가 로드된 뒤에만 그려지는 컴포넌트용 */
export function useWorkspace(): ProjectWorkspace {
  const { workspace } = useAppState();
  if (!workspace) throw new Error("워크스페이스가 아직 로드되지 않았습니다.");
  return workspace;
}
