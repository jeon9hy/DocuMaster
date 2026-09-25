import type {
  AgentId,
  AgentModelConfig,
  AgentSetting,
  ArtifactContent,
  AuthSession,
  NewProjectInput,
  NewReferenceInput,
  ProjectSummary,
  ProfileUpdate,
  ProjectWorkspace,
  ProviderUsage,
  SystemHealth,
  WorkflowEvent,
} from "@/types";

export type Unsubscribe = () => void;

/** 실시간 연결 상태. 끊겨도 서비스가 스스로 다시 붙고, 놓친 이벤트를 이어 받는다. */
export type ConnectionState = "connected" | "reconnecting";

export interface SubscribeHandlers {
  onEvent: (event: WorkflowEvent) => void;
  onConnectionChange?: (state: ConnectionState) => void;
}

/**
 * UI가 아는 유일한 백엔드 창구.
 * 구현은 mock/MockWorkspaceService(브라우저 메모리)와 http/HttpWorkspaceService(로컬 백엔드) 두 가지이고,
 * services/index.ts가 환경변수로 고른다.
 *
 * 읽기는 Promise로 돌려받고, 상태 변화는 모두 subscribe()의 이벤트로 받는다.
 */
export interface WorkspaceService {
  listProjects(): Promise<ProjectSummary[]>;
  createProject(input: NewProjectInput): Promise<ProjectSummary>;
  /** 프로젝트 전용 작업/·최종/·참고자료 폴더와 목록 항목을 함께 지운다. 실행 중이면 거절한다. */
  deleteProject(projectId: string): Promise<void>;
  /** 스냅샷. lastEventSeq까지 반영된 상태를 돌려준다 — 이어서 subscribe(afterSeq=lastEventSeq)로 받는다. */
  getWorkspace(projectId: string): Promise<ProjectWorkspace>;
  /** 미리보기를 열 때만 부른다. 목록에는 메타데이터만 온다. 아직 본문이 없으면 null. */
  getArtifactContent(projectId: string, artifactId: string): Promise<ArtifactContent | null>;
  /** 원본 파일을 내려받을 주소. 목업처럼 실제 파일이 없으면 null. */
  getArtifactDownloadUrl(projectId: string, artifactId: string): string | null;

  /** afterSeq보다 뒤의 이벤트만 받는다(스냅샷과 구독 사이에 생긴 이벤트도 빠지지 않는다). */
  subscribe(projectId: string, afterSeq: number, handlers: SubscribeHandlers): Unsubscribe;

  runWorkflow(projectId: string): Promise<void>;
  /** 현재 단계가 끝난 뒤 멈춘다(graceful stop). */
  stopWorkflow(projectId: string): Promise<void>;
  respondToInput(projectId: string, promptId: string, answer: string): Promise<void>;

  sendMessage(projectId: string, text: string, mentionedAgentId?: AgentId): Promise<void>;
  addReference(projectId: string, input: NewReferenceInput): Promise<void>;
  removeReference(projectId: string, referenceId: string): Promise<void>;

  // --- 단일 Owner 인증. 바꾸는 요청은 모두 Owner만(백엔드가 다시 검사한다) ---
  getSession(): Promise<AuthSession>;
  login(pin: string): Promise<AuthSession>;
  logout(): Promise<AuthSession>;
  updateProfile(update: ProfileUpdate): Promise<AuthSession>;
  changePin(currentPin: string, newPin: string): Promise<AuthSession>;
  /** 프로필 이미지 주소. version을 바꾸면 새로 받는다. 이미지가 없으면 null. */
  getAvatarUrl(version: string | null): string | null;

  // --- 에이전트 모델 설정(전역). 지원하지 않는 값이면 거절(throw)한다 — 다른 값으로 바꾸지 않는다 ---
  listAgentSettings(): Promise<AgentSetting[]>;
  updateAgentSetting(agentId: AgentId, config: AgentModelConfig): Promise<AgentSetting[]>;
  resetAgentSetting(agentId: AgentId): Promise<AgentSetting[]>;

  /** 실제로 확인되는 사용량만. 확인할 수 없는 공급자는 available=false */
  getUsage(): Promise<ProviderUsage[]>;
  /** 도구 설치 상태. 백엔드가 없으면(목업) null */
  getHealth(): Promise<SystemHealth | null>;
}
