import { DEFAULT_ASSIGNEE } from "@/constants/agents";
import { createStageStatusMap } from "@/constants/workflow";
import { MOCK_REPLIES } from "@/data/mock/stageScripts";
import { PROJECT_SEEDS, type ProjectSeed } from "@/data/mock/seedProjects";
import { createDefaultAgents } from "@/lib/agents";
import { applyWorkflowEvent } from "@/lib/applyWorkflowEvent";
import { createId } from "@/lib/ids";
import { getFocusStageId, isWorkflowComplete } from "@/lib/progress";
import { buildReference } from "@/lib/references";
import type {
  AgentId,
  AgentModelConfig,
  ArtifactContent,
  NewProjectInput,
  NewReferenceInput,
  ProjectSummary,
  ProjectWorkspace,
  WorkflowEvent,
  WorkflowEventPayload,
} from "@/types";
import type { Unsubscribe, WorkspaceService } from "../WorkspaceService";
import { buildRunPlan } from "./buildRunPlan";

/** 네트워크처럼 보이게 하는 지연. 로딩 상태 확인용. */
const LATENCY_MS = 250;
const REPLY_DELAY_MS = 900;

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

interface ProjectStore {
  workspace: ProjectWorkspace;
  contents: Map<string, ArtifactContent>;
  listeners: Set<(event: WorkflowEvent) => void>;
  timers: ReturnType<typeof setTimeout>[];
}

function emptyWorkspace(summary: ProjectSummary): ProjectWorkspace {
  return {
    project: summary,
    isRunning: false,
    stageStatus: createStageStatusMap(),
    agents: createDefaultAgents(summary.mode),
    feed: [],
    references: [],
    artifacts: [],
  };
}

/** 시드 이벤트를 실제 실행과 같은 규칙(applyWorkflowEvent)으로 재생한다. */
function replaySeed(seed: ProjectSeed, now: number): ProjectStore {
  const workspace = seed.events.reduce<ProjectWorkspace>(
    (state, { minutesAgo, payload }) =>
      applyWorkflowEvent(state, {
        ...payload,
        id: createId("seed"),
        projectId: seed.summary.id,
        at: new Date(now - minutesAgo * 60_000).toISOString(),
      }),
    emptyWorkspace(seed.summary),
  );
  return {
    // 기록상 진행 중이던 프로젝트도 목업에서는 멈춘 상태로 연다.
    workspace: { ...workspace, isRunning: false },
    contents: new Map(Object.entries(seed.contents)),
    listeners: new Set(),
    timers: [],
  };
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
    this.stores.set(summary.id, {
      workspace: emptyWorkspace(summary),
      contents: new Map(),
      listeners: new Set(),
      timers: [],
    });
    return summary;
  }

  async getWorkspace(projectId: string): Promise<ProjectWorkspace> {
    await wait(LATENCY_MS);
    return this.getStore(projectId).workspace;
  }

  async getArtifactContent(projectId: string, artifactId: string): Promise<ArtifactContent | null> {
    await wait(LATENCY_MS);
    return this.getStore(projectId).contents.get(artifactId) ?? null;
  }

  subscribe(projectId: string, listener: (event: WorkflowEvent) => void): Unsubscribe {
    const { listeners } = this.getStore(projectId);
    listeners.add(listener);
    return () => listeners.delete(listener);
  }

  async runWorkflow(projectId: string): Promise<void> {
    const store = this.getStore(projectId);
    if (store.workspace.isRunning || isWorkflowComplete(store.workspace.stageStatus)) return;

    let elapsed = 0;
    for (const planned of buildRunPlan(store.workspace)) {
      elapsed += planned.delayMs;
      const timer = setTimeout(() => {
        if (planned.content) store.contents.set(planned.content.artifactId, planned.content.value);
        this.emit(projectId, planned.payload);
      }, elapsed);
      store.timers.push(timer);
    }
  }

  async stopWorkflow(projectId: string): Promise<void> {
    const store = this.getStore(projectId);
    if (!store.workspace.isRunning) return;
    this.clearTimers(store);
    this.emit(projectId, {
      type: "workflow.stopped",
      stageId: getFocusStageId(store.workspace.stageStatus),
    });
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

  async updateAgentConfig(
    projectId: string,
    agentId: AgentId,
    config: AgentModelConfig,
  ): Promise<void> {
    this.emit(projectId, { type: "agent.configured", agentId, config });
  }

  private getStore(projectId: string): ProjectStore {
    const store = this.stores.get(projectId);
    if (!store) throw new Error(`프로젝트를 찾을 수 없습니다: ${projectId}`);
    return store;
  }

  private emit(projectId: string, payload: WorkflowEventPayload) {
    const store = this.getStore(projectId);
    const event: WorkflowEvent = {
      ...payload,
      id: createId("evt"),
      projectId,
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
