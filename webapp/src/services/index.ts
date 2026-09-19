import { HttpWorkspaceService } from "./http/HttpWorkspaceService";
import { MockWorkspaceService } from "./mock/MockWorkspaceService";
import type { WorkspaceService } from "./WorkspaceService";

export type { WorkspaceService } from "./WorkspaceService";

/**
 * 앱 전체가 쓰는 서비스 하나.
 * - NEXT_PUBLIC_API_URL이 있으면 로컬 백엔드(HttpWorkspaceService)
 * - 없으면 브라우저 메모리 목업(MockWorkspaceService) — 백엔드 없이 화면만 볼 때
 */
const apiUrl = process.env.NEXT_PUBLIC_API_URL;

export const workspaceService: WorkspaceService = apiUrl
  ? new HttpWorkspaceService(apiUrl)
  : new MockWorkspaceService();

export const serviceKind: "http" | "mock" = apiUrl ? "http" : "mock";
