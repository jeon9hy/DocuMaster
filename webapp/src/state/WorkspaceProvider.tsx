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
import { readUrlState, writeUrlState } from "@/lib/urlState";
import { workspaceService } from "@/services";
import type {
  AgentId,
  AuthSession,
  NewProjectInput,
  NewReferenceInput,
  ProfileUpdate,
  ProjectWorkspace,
  WorkflowStageId,
} from "@/types";
import { appReducer, initialAppState, type AppState } from "./appReducer";

export interface AppActions {
  selectProject(projectId: string): void;
  createProject(input: NewProjectInput): Promise<void>;
  deleteProject(projectId: string): Promise<void>;
  reloadWorkspace(): void;
  setView(view: ViewId): void;
  toggleStage(stageId: WorkflowStageId): void;
  selectArtifact(artifactId: string): void;
  runWorkflow(): Promise<void>;
  stopWorkflow(): Promise<void>;
  respondToInput(promptId: string, answer: string): Promise<void>;
  sendMessage(text: string, mentionedAgentId?: AgentId): Promise<void>;
  addReference(input: NewReferenceInput): Promise<void>;
  removeReference(referenceId: string): Promise<void>;
  /** 로그인 상태를 다시 확인한다(세션 만료 등) */
  refreshSession(): Promise<void>;
  login(pin: string): Promise<void>;
  logout(): Promise<void>;
  updateProfile(update: ProfileUpdate): Promise<void>;
  changePin(currentPin: string, newPin: string): Promise<void>;
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
    // 없는 프로젝트(삭제·다른 DB의 주소)면 첫 프로젝트로
    const target = projects.some((project) => project.id === selectId) ? selectId : projects[0]?.id;
    dispatch(target ? { type: "project/selected", projectId: target } : { type: "project/cleared" });
  }, []);

  const applySession = useCallback((session: AuthSession) => dispatch({ type: "session/changed", session }), []);
  const refreshSession = useCallback(
    () => workspaceService.getSession().then(applySession),
    [applySession],
  );

  useEffect(() => {
    // 주소에 남은 화면·프로젝트로 시작한다(새로고침해도 보던 화면 그대로)
    const fromUrl = readUrlState();
    if (fromUrl.view) dispatch({ type: "view/changed", view: fromUrl.view });
    loadProjects(fromUrl.projectId).catch(() => dispatch({ type: "workspace/failed" }));
    // 백엔드가 없으면 로그인 확인도 실패한다 — 그때는 Guest(읽기 전용)로 둔다
    refreshSession().catch(() =>
      applySession({ configured: false, authenticated: false, pinManagedByEnv: false, profile: null }),
    );
  }, [loadProjects, refreshSession, applySession]);

  // 프로젝트가 바뀔 때만 스냅샷을 한 번 받고, 이후 변화는 이벤트 구독으로만 받는다(중복 조회 없음).
  // 구독은 스냅샷의 lastEventSeq 다음부터 받으므로 그 사이에 생긴 이벤트도 빠지지 않는다.
  useEffect(() => {
    if (!projectId) return;
    let unsubscribe: (() => void) | undefined;
    let cancelled = false;

    workspaceService
      .getWorkspace(projectId)
      .then((workspace) => {
        if (cancelled) return;
        dispatch({ type: "workspace/loaded", workspace });
        unsubscribe = workspaceService.subscribe(projectId, workspace.lastEventSeq, {
          onEvent: (event) => dispatch({ type: "event/received", event }),
          onConnectionChange: (connection) => dispatch({ type: "connection/changed", connection }),
        });
      })
      .catch(() => !cancelled && dispatch({ type: "workspace/failed" }));

    return () => {
      cancelled = true;
      unsubscribe?.();
    };
  }, [projectId, reloadToken]);

  // 목록을 받기 전에는 쓰지 않는다 — 시작 직후의 기본값이 주소를 덮어쓰지 않게
  const { view, projectsLoaded } = state;
  useEffect(() => {
    if (projectsLoaded) writeUrlState(view, projectId);
  }, [view, projectId, projectsLoaded]);

  const actions = useMemo<AppActions>(() => {
    const requireProject = () => {
      if (!projectId) throw new Error("선택된 프로젝트가 없습니다.");
      return projectId;
    };
    /** 바꾸는 요청이 실패하면(세션 만료 등) 로그인 상태를 다시 확인한 뒤 오류를 그대로 올린다. */
    const mutate = async <T,>(action: () => Promise<T>): Promise<T> => {
      try {
        return await action();
      } catch (error) {
        await refreshSession().catch(() => undefined);
        throw error;
      }
    };
    return {
      selectProject: (id) => dispatch({ type: "project/selected", projectId: id }),
      createProject: async (input) => {
        const created = await mutate(() => workspaceService.createProject(input));
        await loadProjects(created.id);
      },
      deleteProject: async (id) => {
        await mutate(() => workspaceService.deleteProject(id));
        // 지금 보던 프로젝트를 지웠으면 첫 프로젝트로(없으면 빈 화면)
        await loadProjects(id === projectId ? undefined : (projectId ?? undefined));
      },
      reloadWorkspace: () => {
        dispatch({ type: "workspace/retried" });
        if (!projectId) loadProjects().catch(() => dispatch({ type: "workspace/failed" }));
      },
      setView: (view) => dispatch({ type: "view/changed", view }),
      toggleStage: (stageId) => dispatch({ type: "stage/toggled", stageId }),
      selectArtifact: (artifactId) => dispatch({ type: "artifact/selected", artifactId }),
      runWorkflow: () => mutate(() => workspaceService.runWorkflow(requireProject())),
      stopWorkflow: () => mutate(() => workspaceService.stopWorkflow(requireProject())),
      respondToInput: (promptId, answer) =>
        mutate(() => workspaceService.respondToInput(requireProject(), promptId, answer)),
      sendMessage: (text, agentId) => mutate(() => workspaceService.sendMessage(requireProject(), text, agentId)),
      addReference: (input) => mutate(() => workspaceService.addReference(requireProject(), input)),
      removeReference: (referenceId) =>
        mutate(() => workspaceService.removeReference(requireProject(), referenceId)),
      refreshSession,
      login: async (pin) => applySession(await workspaceService.login(pin)),
      logout: async () => applySession(await workspaceService.logout()),
      updateProfile: async (update) => applySession(await mutate(() => workspaceService.updateProfile(update))),
      changePin: async (currentPin, newPin) =>
        applySession(await mutate(() => workspaceService.changePin(currentPin, newPin))),
    };
  }, [projectId, loadProjects, refreshSession, applySession]);

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

/** 로그인한 Owner인지. 확인 전·로그아웃·백엔드 없음이면 false(읽기 전용). 백엔드도 따로 막는다. */
export function useIsOwner(): boolean {
  return useAppState().session?.authenticated === true;
}

/** 워크스페이스가 로드된 뒤에만 그려지는 컴포넌트용 */
export function useWorkspace(): ProjectWorkspace {
  const { workspace } = useAppState();
  if (!workspace) throw new Error("워크스페이스가 아직 로드되지 않았습니다.");
  return workspace;
}
