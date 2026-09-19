import { MockWorkspaceService } from "./mock/MockWorkspaceService";
import type { WorkspaceService } from "./WorkspaceService";

export type { WorkspaceService } from "./WorkspaceService";

/**
 * 앱 전체가 쓰는 서비스 하나. 실제 백엔드를 붙일 때는 이 줄만 바꾼다.
 * 예: export const workspaceService: WorkspaceService = new HttpWorkspaceService(process.env.NEXT_PUBLIC_API_URL);
 */
export const workspaceService: WorkspaceService = new MockWorkspaceService();
