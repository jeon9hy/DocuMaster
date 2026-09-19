import { AGENT_IDS, AGENT_PROFILES, DEFAULT_ASSIGNEE } from "@/constants/agents";
import { MOCK_REPLIES } from "@/data/mock/stageScripts";
import { PROJECT_SEEDS, type ProjectSeed } from "@/data/mock/seedProjects";
import { applyWorkflowEvent } from "@/lib/applyWorkflowEvent";
import { createId } from "@/lib/ids";
import { getFocusStageId, isWorkflowComplete } from "@/lib/progress";
import { buildReference } from "@/lib/references";
import { emptyWorkspace } from "@/lib/workspace";
import { EVENT_SCHEMA_VERSION } from "@/types/events";
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
  WorkflowEvent,
  WorkflowEventPayload,
} from "@/types";
import type { SubscribeHandlers, Unsubscribe, WorkspaceService } from "../WorkspaceService";
import { buildRunPlan, type PlannedEvent } from "./buildRunPlan";

/** 네트워크처럼 보이게 하는 지연. 로딩 상태 확인용. */
const LATENCY_MS = 250;
const REPLY_DELAY_MS = 900;
/** 목업의 graceful stop: 중지 요청 뒤 이만큼 기다렸다가 멈춘다 */
const STOP_DELAY_MS = 1200;

/** 목업의 모델 선택지 — 백엔드(server/app/agent_settings.py)와 같은 규칙: 로이드만 바꿀 수 있다. */
const MOCK_LOID_OPTIONS: Pick<AgentSetting, "modelIds" | "reasoningLevels"> = {
  modelIds: ["claude-code-default", "claude-fable-5-1", "claude-opus-5", "claude-sonnet-5"],
  reasoningLevels: [null, "low", "medium", "high", "xhigh", "max"],
};
const MOCK_SUBAGENT_MODELS = ["claude-fable-5-1", "claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"];
const MOCK_LOCK_REASON = "NotebookLM(nlm CLI)에는 모델 선택이 없습니다.";
const MOCK_USAGE_NOTE = "목업 모드에서는 사용량을 확인하지 않습니다(백엔드를 켜면 실제 값만 보여 줍니다).";

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

interface ProjectStore {
  workspace: ProjectWorkspace;
  contents: Map<string, ArtifactContent>;
  listeners: Set<(event: WorkflowEvent) => void>;
  timers: ReturnType<typeof setTimeout>[];
  /** 사용자 응답을 기다리느라 멈춘 나머지 대본 */
  pausedPlan: PlannedEvent[];
  runId: string | null;
}

function newStore(workspace: ProjectWorkspace, contents = new Map<string, ArtifactContent>()): ProjectStore {
  return { workspace, contents, listeners: new Set(), timers: [], pausedPlan: [], runId: null };
}

/** 시드 이벤트를 실제 실행과 같은 규칙(applyWorkflowEvent)으로 재생한다. */
function replaySeed(seed: ProjectSeed, now: number): ProjectStore {
  const workspace = seed.events.reduce<ProjectWorkspace>(
    (state, { minutesAgo, payload }) =>
      applyWorkflowEvent(state, {
        ...payload,
        schemaVersion: EVENT_SCHEMA_VERSION,
        id: createId("seed"),
        projectId: seed.summary.id,
        runId: null,
        seq: state.lastEventSeq + 1,
        at: new Date(now - minutesAgo * 60_000).toISOString(),
      }),
    emptyWorkspace(seed.summary),
  );
  // 기록상 진행 중이던 프로젝트도 목업에서는 멈춘 상태로 연다.
  return newStore({ ...workspace, runStatus: "stopped" }, new Map(Object.entries(seed.contents)));
}

/**
 * 브라우저 메모리 안에서 돌아가는 가짜 오케스트레이터.
 * LLM을 부르지 않는다 — 대본(data/mock/stageScripts.ts)을 시간차로 이벤트로 내보낼 뿐이다.
 */
export class MockWorkspaceService implements WorkspaceService {
  private readonly stores = new Map<string, ProjectStore>();

  constructor(seeds: readonly ProjectSeed[] = PROJECT_SEEDS) {
    const now = Date.now();
    for (const seed of seeds) this.stores.set(seed.summary.id, replaySeed(seed, now));
  }

  async listProjects(): Promise<ProjectSummary[]> {
    await wait(LATENCY_MS);
    return [...this.stores.values()].map((store) => store.workspace.project);
  }

  async createProject(input: NewProjectInput): Promise<ProjectSummary> {
    await wait(LATENCY_MS);
    const summary: ProjectSummary = {
      id: createId("project"),
      name: input.name,
      description: "새 프로젝트",
      mode: input.mode,
    };
    this.stores.set(summary.id, newStore(emptyWorkspace(summary)));
    return summary;
  }

  async deleteProject(projectId: string): Promise<void> {
    const store = this.getStore(projectId);
    if (store.runId) throw new Error("실행 중인 프로젝트는 삭제할 수 없습니다. 먼저 중지하세요.");
    store.timers.forEach(clearTimeout);
    this.stores.delete(projectId);
  }

  async getWorkspace(projectId: string): Promise<ProjectWorkspace> {
    await wait(LATENCY_MS);
    return this.getStore(projectId).workspace;
  }

  async getArtifactContent(projectId: string, artifactId: string): Promise<ArtifactContent | null> {
    await wait(LATENCY_MS);
    return this.getStore(projectId).contents.get(artifactId) ?? null;
  }

  getArtifactDownloadUrl(): string | null {
    return null;
  }

  subscribe(projectId: string, _afterSeq: number, handlers: SubscribeHandlers): Unsubscribe {
    // 메모리 안이라 놓치는 이벤트가 없다. 중복은 applyWorkflowEvent가 seq로 거른다.
    const { listeners } = this.getStore(projectId);
    listeners.add(handlers.onEvent);
    handlers.onConnectionChange?.("connected");
    return () => listeners.delete(handlers.onEvent);
  }

  async runWorkflow(projectId: string): Promise<void> {
    const store = this.getStore(projectId);
    const { runStatus, stageStatus } = store.workspace;
    if (["running", "awaitingInput", "stopping"].includes(runStatus) || isWorkflowComplete(stageStatus)) {
      return;
    }
    store.runId = createId("run");
    this.schedule(projectId, buildRunPlan(store.workspace));
  }

  async stopWorkflow(projectId: string): Promise<void> {
    const store = this.getStore(projectId);
    if (!["running", "awaitingInput"].includes(store.workspace.runStatus)) return;
    this.emit(projectId, { type: "workflow.stop.requested" });
    this.later(store, STOP_DELAY_MS, () => {
      this.clearTimers(store);
      store.pausedPlan = [];
      this.emit(projectId, {
        type: "workflow.stopped",
        stageId: getFocusStageId(store.workspace.stageStatus),
      });
    });
  }

  async respondToInput(projectId: string, promptId: string, answer: string): Promise<void> {
    const store = this.getStore(projectId);
    if (!store.workspace.pendingInputs.some((input) => input.promptId === promptId)) return;
    this.emit(projectId, { type: "user.input.resolved", promptId, answer });
    const rest = store.pausedPlan;
    store.pausedPlan = [];
    if (answer === "작업 중단") {
      this.emit(projectId, {
        type: "workflow.stopped",
        stageId: getFocusStageId(store.workspace.stageStatus),
      });
      return;
    }
    this.schedule(projectId, rest);
  }

  async sendMessage(projectId: string, text: string, mentionedAgentId?: AgentId): Promise<void> {
    const store = this.getStore(projectId);
    this.emit(projectId, { type: "user.message", text });

    const workingAgent = store.workspace.agents.find((agent) => agent.status === "working");
    const replier = mentionedAgentId ?? workingAgent?.id ?? DEFAULT_ASSIGNEE;
    this.later(store, REPLY_DELAY_MS, () =>
      this.emit(projectId, { type: "agent.message", agentId: replier, text: MOCK_REPLIES[replier] }),
    );
  }

  async addReference(projectId: string, input: NewReferenceInput): Promise<void> {
    await wait(LATENCY_MS);
    const store = this.getStore(projectId);
    const reference = buildReference(input, createId("ref"));
    this.emit(projectId, { type: "reference.added", reference });

    const workingAgent = store.workspace.agents.find((agent) => agent.status === "working");
    if (input.applyPolicy === "currentAgent" && workingAgent) {
      this.later(store, REPLY_DELAY_MS, () =>
        this.emit(projectId, {
          type: "agent.message",
          agentId: workingAgent.id,
          text: `「${reference.name}」을 받았습니다. 지금 작업에 반영하겠습니다.`,
        }),
      );
    }
    if (input.applyPolicy === "rerunStage") {
      this.emit(projectId, {
        type: "workflow.warning",
        stageId: getFocusStageId(store.workspace.stageStatus),
        message: "관련 단계 재실행은 실제 오케스트레이터 연결 후 동작합니다(목업에서는 표시만).",
      });
    }
  }

  async removeReference(projectId: string, referenceId: string): Promise<void> {
    this.emit(projectId, { type: "reference.removed", referenceId });
  }

  // --- 인증: 목업은 PIN을 확인하지 않는다(백엔드 없이 화면만 볼 때). 로그인 상태로 시작한다. ---

  private session: AuthSession = {
    configured: true,
    authenticated: true,
    pinManagedByEnv: false,
    profile: { nickname: "로컬 사용자", hasAvatar: false, updatedAt: null },
  };

  async getSession(): Promise<AuthSession> {
    return this.session;
  }

  async login(pin: string): Promise<AuthSession> {
    if (!/^\d{6}$/.test(pin)) throw new Error("PIN은 숫자 6자리여야 합니다.");
    this.session = {
      ...this.session,
      authenticated: true,
      profile: this.session.profile ?? { nickname: "로컬 사용자", hasAvatar: false, updatedAt: null },
    };
    return this.session;
  }

  async logout(): Promise<AuthSession> {
    this.session = { ...this.session, authenticated: false };
    return this.session;
  }

  async updateProfile(update: ProfileUpdate): Promise<AuthSession> {
    const profile = this.session.profile ?? { nickname: "로컬 사용자", hasAvatar: false, updatedAt: null };
    this.session = {
      ...this.session,
      profile: {
        nickname: update.nickname?.trim() || profile.nickname,
        hasAvatar: false, // 목업은 이미지를 보관하지 않는다
        updatedAt: new Date().toISOString(),
      },
    };
    return this.session;
  }

  async changePin(): Promise<AuthSession> {
    throw new Error("목업 모드에는 PIN이 없습니다. 백엔드를 켠 뒤 바꾸세요.");
  }

  getAvatarUrl(): string | null {
    return null;
  }

  // --- 모델 설정 ---

  private overrides = new Map<AgentId, { config: AgentModelConfig; updatedAt: string }>();

  private agentSettings(): AgentSetting[] {
    return AGENT_IDS.map((agentId) => {
      const defaultConfig = AGENT_PROFILES[agentId].defaultConfig;
      const override = this.overrides.get(agentId);
      const loid = agentId === "loid";
      const subagent = agentId === "yuri" || agentId === "anya";
      return {
        agentId,
        config: override?.config ?? defaultConfig,
        defaultConfig,
        overridden: Boolean(override),
        updatedAt: override?.updatedAt ?? null,
        modelIds: loid ? MOCK_LOID_OPTIONS.modelIds : subagent ? MOCK_SUBAGENT_MODELS : [defaultConfig.modelId],
        reasoningLevels: loid ? MOCK_LOID_OPTIONS.reasoningLevels : [defaultConfig.reasoningLevel],
        reasoningByModel: null,
        lockedReason: agentId === "bond" ? MOCK_LOCK_REASON : null,
      };
    });
  }

  async listAgentSettings(): Promise<AgentSetting[]> {
    await wait(LATENCY_MS);
    return this.agentSettings();
  }

  async updateAgentSetting(agentId: AgentId, config: AgentModelConfig): Promise<AgentSetting[]> {
    const current = this.agentSettings().find((setting) => setting.agentId === agentId);
    const supported =
      current &&
      config.provider === current.defaultConfig.provider &&
      current.modelIds.includes(config.modelId) &&
      current.reasoningLevels.includes(config.reasoningLevel);
    if (!supported) throw new Error("현재 선택한 모델 설정을 사용할 수 없습니다.");
    this.overrides.set(agentId, { config, updatedAt: new Date().toISOString() });
    return this.agentSettings();
  }

  async resetAgentSetting(agentId: AgentId): Promise<AgentSetting[]> {
    this.overrides.delete(agentId);
    return this.agentSettings();
  }

  async getUsage(): Promise<ProviderUsage[]> {
    const unavailable = (provider: ProviderUsage["provider"], label: string): ProviderUsage => ({
      provider,
      label,
      available: false,
      stale: false,
      windows: [],
      observedAt: null,
      source: null,
      note: MOCK_USAGE_NOTE,
    });
    return [
      unavailable("anthropic", "Anthropic · Claude Code"),
      unavailable("openai", "OpenAI · Codex"),
      unavailable("google", "Google · NotebookLM"),
    ];
  }

  async getHealth(): Promise<null> {
    return null;
  }

  private getStore(projectId: string): ProjectStore {
    const store = this.stores.get(projectId);
    if (!store) throw new Error(`프로젝트를 찾을 수 없습니다: ${projectId}`);
    return store;
  }

  /** 대본을 시간차로 내보낸다. pause 이벤트를 만나면 나머지는 응답이 올 때까지 보관한다. */
  private schedule(projectId: string, plan: PlannedEvent[]) {
    const store = this.getStore(projectId);
    const pauseIndex = plan.findIndex((planned) => planned.pause);
    const now = pauseIndex === -1 ? plan : plan.slice(0, pauseIndex + 1);
    const rest = pauseIndex === -1 ? [] : plan.slice(pauseIndex + 1);

    let elapsed = 0;
    now.forEach((planned, index) => {
      elapsed += planned.delayMs;
      this.later(store, elapsed, () => {
        if (planned.content) store.contents.set(planned.content.artifactId, planned.content.value);
        this.emit(projectId, planned.payload);
        if (index === now.length - 1 && rest.length) store.pausedPlan = rest;
      });
    });
  }

  private emit(projectId: string, payload: WorkflowEventPayload) {
    const store = this.getStore(projectId);
    const event: WorkflowEvent = {
      ...payload,
      schemaVersion: EVENT_SCHEMA_VERSION,
      id: createId("evt"),
      projectId,
      runId: store.runId,
      seq: store.workspace.lastEventSeq + 1,
      at: new Date().toISOString(),
    };
    store.workspace = applyWorkflowEvent(store.workspace, event);
    if (payload.type === "workflow.completed") this.clearTimers(store);
    store.listeners.forEach((listener) => listener(event));
  }

  private later(store: ProjectStore, delayMs: number, run: () => void) {
    store.timers.push(setTimeout(run, delayMs));
  }

  private clearTimers(store: ProjectStore) {
    store.timers.forEach(clearTimeout);
    store.timers = [];
  }
}
