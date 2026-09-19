import { buildWorkspace } from "@/lib/workspace";
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
import type { SubscribeHandlers, Unsubscribe, WorkspaceService } from "../WorkspaceService";

const BACKEND_UNAVAILABLE =
  "로컬 백엔드에 연결할 수 없습니다. webapp/start.bat(또는 webapp/server)을 실행했는지 확인하세요.";
/** 브라우저가 재연결을 포기했을 때(서버 오류 응답 등) 직접 다시 붙기까지 기다리는 시간 */
const RECONNECT_DELAY_MS = 3000;

const LOOPBACK = new Set(["localhost", "127.0.0.1", "[::1]"]);

/**
 * 로그인 쿠키는 같은 사이트에만 실린다. 화면을 localhost로 열고 API를 127.0.0.1로 부르면 다른 사이트라
 * 쿠키가 빠지므로, 둘 다 이 컴퓨터(loopback)면 API 호스트를 화면 호스트에 맞춘다.
 */
function alignLoopbackHost(baseUrl: string): string {
  if (typeof window === "undefined") return baseUrl;
  try {
    const url = new URL(baseUrl);
    const pageHost = window.location.hostname;
    if (LOOPBACK.has(url.hostname) && LOOPBACK.has(pageHost) && url.hostname !== pageHost) {
      url.hostname = pageHost;
    }
    return url.toString().replace(/\/+$/, "");
  } catch {
    return baseUrl;
  }
}

interface WorkspaceSnapshot {
  project: ProjectSummary;
  events: WorkflowEvent[];
  lastEventSeq: number;
}

/**
 * 로컬 백엔드(webapp/server)에 붙는 구현. 읽기·명령은 REST, 상태 변화는 SSE로 받는다.
 * 스냅샷은 이벤트 기록을 같은 reducer(applyWorkflowEvent)로 다시 적용해 만든다 —
 * 백엔드에 화면 상태 계산을 두 벌 두지 않기 위해서다.
 */
export class HttpWorkspaceService implements WorkspaceService {
  private readonly configuredUrl: string;
  private alignedUrl: string | null = null;

  constructor(baseUrl: string) {
    this.configuredUrl = baseUrl.replace(/\/+$/, "");
  }

  /** 브라우저에서 처음 쓸 때 한 번 정한다(서버 렌더 중에는 window가 없다). */
  private get baseUrl(): string {
    if (typeof window === "undefined") return this.configuredUrl;
    this.alignedUrl ??= alignLoopbackHost(this.configuredUrl);
    return this.alignedUrl;
  }

  listProjects(): Promise<ProjectSummary[]> {
    return this.request("/api/projects");
  }

  createProject(input: NewProjectInput): Promise<ProjectSummary> {
    return this.request("/api/projects", { method: "POST", json: input });
  }

  async deleteProject(projectId: string): Promise<void> {
    await this.request(`/api/projects/${projectId}`, { method: "DELETE" });
  }

  async getWorkspace(projectId: string): Promise<ProjectWorkspace> {
    const snapshot = await this.request<WorkspaceSnapshot>(`/api/projects/${projectId}/workspace`);
    return buildWorkspace(snapshot.project, snapshot.events);
  }

  getArtifactContent(projectId: string, artifactId: string): Promise<ArtifactContent | null> {
    return this.request(`/api/projects/${projectId}/artifacts/${artifactId}/content`);
  }

  getArtifactDownloadUrl(projectId: string, artifactId: string): string {
    return `${this.baseUrl}/api/projects/${projectId}/artifacts/${artifactId}/download`;
  }

  subscribe(projectId: string, afterSeq: number, handlers: SubscribeHandlers): Unsubscribe {
    let lastSeq = afterSeq;
    let source: EventSource | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let closed = false;

    // 처음 연결은 afterSeq로, 자동 재연결은 브라우저가 Last-Event-ID(= 마지막 seq)로 이어 받는다.
    const connect = () => {
      source = new EventSource(`${this.baseUrl}/api/projects/${projectId}/events?afterSeq=${lastSeq}`, {
        withCredentials: true,
      });
      source.onopen = () => handlers.onConnectionChange?.("connected");
      source.onmessage = (message) => {
        const event = JSON.parse(message.data) as WorkflowEvent;
        if (event.seq <= lastSeq) return;
        lastSeq = event.seq;
        handlers.onEvent(event);
      };
      source.onerror = () => {
        handlers.onConnectionChange?.("reconnecting");
        if (source?.readyState === EventSource.CLOSED && !closed) {
          retryTimer = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };
    };
    connect();

    return () => {
      closed = true;
      clearTimeout(retryTimer);
      source?.close();
    };
  }

  async runWorkflow(projectId: string): Promise<void> {
    await this.request(`/api/projects/${projectId}/runs`, { method: "POST" });
  }

  async stopWorkflow(projectId: string): Promise<void> {
    await this.request(`/api/projects/${projectId}/runs/current/stop`, { method: "POST" });
  }

  async respondToInput(projectId: string, promptId: string, answer: string): Promise<void> {
    await this.request(`/api/projects/${projectId}/inputs/${promptId}/response`, {
      method: "POST",
      json: { answer },
    });
  }

  // @호출(mentionedAgentId)은 따로 보내지 않는다 — 문장 그대로 로이드에게 가고, 누구에게 맡길지는 오케스트레이터가 정한다.
  async sendMessage(projectId: string, text: string): Promise<void> {
    await this.request(`/api/projects/${projectId}/messages`, { method: "POST", json: { text } });
  }

  async addReference(projectId: string, input: NewReferenceInput): Promise<void> {
    const form = new FormData();
    form.set("source", input.source);
    form.set("applyPolicy", input.applyPolicy);
    if (input.source === "file") form.set("file", input.file);
    if (input.source === "url") {
      form.set("url", input.url);
      form.set("title", input.title);
    }
    if (input.source === "text") {
      form.set("title", input.title);
      form.set("text", input.text);
    }
    await this.request(`/api/projects/${projectId}/references`, { method: "POST", body: form });
  }

  async removeReference(projectId: string, referenceId: string): Promise<void> {
    await this.request(`/api/projects/${projectId}/references/${referenceId}`, { method: "DELETE" });
  }

  getSession(): Promise<AuthSession> {
    return this.request("/api/auth/session");
  }

  login(pin: string): Promise<AuthSession> {
    return this.request("/api/auth/login", { method: "POST", json: { pin } });
  }

  logout(): Promise<AuthSession> {
    return this.request("/api/auth/logout", { method: "POST" });
  }

  updateProfile(update: ProfileUpdate): Promise<AuthSession> {
    const form = new FormData();
    if (update.nickname !== undefined) form.set("nickname", update.nickname);
    if (update.avatar) form.set("avatar", update.avatar);
    if (update.removeAvatar) form.set("removeAvatar", "true");
    return this.request("/api/auth/profile", { method: "PATCH", body: form });
  }

  changePin(currentPin: string, newPin: string): Promise<AuthSession> {
    return this.request("/api/auth/pin", { method: "POST", json: { currentPin, newPin } });
  }

  getAvatarUrl(version: string | null): string | null {
    return version ? `${this.baseUrl}/api/auth/avatar?v=${encodeURIComponent(version)}` : null;
  }

  listAgentSettings(): Promise<AgentSetting[]> {
    return this.request("/api/settings/agents");
  }

  updateAgentSetting(agentId: AgentId, config: AgentModelConfig): Promise<AgentSetting[]> {
    return this.request(`/api/settings/agents/${agentId}`, { method: "PATCH", json: config });
  }

  resetAgentSetting(agentId: AgentId): Promise<AgentSetting[]> {
    return this.request(`/api/settings/agents/${agentId}`, { method: "DELETE" });
  }

  getUsage(): Promise<ProviderUsage[]> {
    return this.request("/api/system/usage");
  }

  getHealth(): Promise<SystemHealth> {
    return this.request("/api/system/health");
  }

  /** 오류는 백엔드가 준 문장(detail.message)을 그대로 올린다 — '알 수 없는 오류'만 보여 주지 않는다. */
  private async request<T>(
    path: string,
    init: { method?: string; json?: unknown; body?: BodyInit } = {},
  ): Promise<T> {
    let response: Response;
    try {
      response = await fetch(this.baseUrl + path, {
        method: init.method ?? "GET",
        credentials: "include", // HttpOnly 세션 쿠키(토큰은 스크립트가 읽지 못한다)
        headers: init.json === undefined ? undefined : { "Content-Type": "application/json" },
        body: init.json === undefined ? init.body : JSON.stringify(init.json),
      });
    } catch {
      throw new Error(BACKEND_UNAVAILABLE);
    }
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      const message = detail?.detail?.message ?? detail?.detail;
      throw new Error(typeof message === "string" ? message : `요청이 실패했습니다 (HTTP ${response.status}).`);
    }
    return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
  }
}
