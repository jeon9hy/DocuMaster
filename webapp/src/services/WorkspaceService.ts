import type {
  AgentId,
  AgentModelConfig,
  ArtifactContent,
  NewProjectInput,
  NewReferenceInput,
  ProjectSummary,
  ProjectWorkspace,
  WorkflowEvent,
} from "@/types";

export type Unsubscribe = () => void;

/**
 * UI가 아는 유일한 백엔드 창구.
 * 지금은 mock/MockWorkspaceService가 구현하고, 실제 오케스트레이터가 생기면
 * 같은 인터페이스로 HttpWorkspaceService를 만들어 services/index.ts에서 바꿔 끼운다.
 *
 * 읽기는 Promise로 돌려받고, 상태 변화는 모두 subscribe()의 이벤트로 받는다.
 */
export interface WorkspaceService {
  listProjects(): Promise<ProjectSummary[]>;
  createProject(input: NewProjectInput): Promise<ProjectSummary>;
  getWorkspace(projectId: string): Promise<ProjectWorkspace>;
  /** 미리보기를 열 때만 부른다. 목록에는 메타데이터만 온다. 아직 본문이 없으면 null. */
  getArtifactContent(projectId: string, artifactId: string): Promise<ArtifactContent | null>;

  subscribe(projectId: string, listener: (event: WorkflowEvent) => void): Unsubscribe;

  runWorkflow(projectId: string): Promise<void>;
  stopWorkflow(projectId: string): Promise<void>;

  sendMessage(projectId: string, text: string, mentionedAgentId?: AgentId): Promise<void>;
  addReference(projectId: string, input: NewReferenceInput): Promise<void>;
  updateAgentConfig(projectId: string, agentId: AgentId, config: AgentModelConfig): Promise<void>;
}
