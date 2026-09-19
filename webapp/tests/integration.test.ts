/**
 * 통합 Happy Path: 가짜 오케스트레이터 → 백엔드 이벤트 → SSE → HttpWorkspaceService → 화면 상태.
 * 임시 폴더에 백엔드를 띄우므로 실제 작업/·최종/과 LLM을 건드리지 않는다.
 * 백엔드 가상환경(server/.venv)이 없으면 건너뛴다.
 */
import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { applyWorkflowEvent } from "@/lib/applyWorkflowEvent";
import { computeProgress } from "@/lib/progress";
import { HttpWorkspaceService } from "@/services/http/HttpWorkspaceService";
import type { ProjectWorkspace } from "@/types";

const SERVER_DIR = join(import.meta.dirname, "..", "server");
const PYTHON = join(SERVER_DIR, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const skip = !existsSync(PYTHON) || typeof EventSource === "undefined";

/** 테스트 전용 PIN(실제 PIN이 아니다). 백엔드에는 해시만 넘긴다. */
const TEST_PIN = "135790";

let backend: ChildProcess | undefined;
let baseUrl = "";
let tempRoot = "";

async function freePort(): Promise<number> {
  return new Promise((resolve) => {
    const server = createServer().listen(0, () => {
      const address = server.address();
      server.close(() => resolve(typeof address === "object" && address ? address.port : 0));
    });
  });
}

/**
 * Node의 fetch에는 브라우저 같은 쿠키 저장소가 없다. 백엔드가 준 세션 쿠키(HttpOnly)를 기억했다가
 * 다음 요청에 실어, 브라우저의 credentials: "include"와 같은 조건을 만든다.
 */
const realFetch = globalThis.fetch;
let sessionCookie = "";
function useCookieJar() {
  globalThis.fetch = async (input, init) => {
    const headers = new Headers(init?.headers);
    if (sessionCookie) headers.set("cookie", sessionCookie);
    const response = await realFetch(input, { ...init, headers });
    const cookies = response.headers.getSetCookie();
    if (cookies.length) sessionCookie = cookies.map((cookie) => cookie.split(";")[0]).join("; ");
    return response;
  };
}

async function waitFor<T>(check: () => T | undefined | false, timeoutMs = 20_000): Promise<T> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const value = check();
    if (value) return value;
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error("시간 안에 조건을 만족하지 못했습니다");
}

before(async () => {
  if (skip) return;
  tempRoot = mkdtempSync(join(tmpdir(), "documaster-it-"));
  const dataDir = join(tempRoot, "webapp", ".data");
  mkdirSync(dataDir, { recursive: true });
  const port = await freePort();
  baseUrl = `http://127.0.0.1:${port}`;
  const hashed = spawnSync(PYTHON, ["-c", `from app.auth import hash_pin; print(hash_pin("${TEST_PIN}"))`], {
    cwd: SERVER_DIR,
    encoding: "utf-8",
  });
  if (hashed.status !== 0) throw new Error(`PIN 해시를 만들지 못했습니다: ${hashed.stderr}`);
  backend = spawn(PYTHON, ["-m", "uvicorn", "app.main:app", "--port", String(port), "--log-level", "warning"], {
    cwd: SERVER_DIR,
    env: {
      ...process.env,
      DOCUMASTER_REPO_ROOT: tempRoot,
      DOCUMASTER_DATA_DIR: dataDir,
      DOCUMASTER_ORCHESTRATOR: "fake",
      DOCUMASTER_FAKE_STEP_SECONDS: "0.1",
      DOCUMASTER_POLL_SECONDS: "0.02",
      DOCUMASTER_OWNER_PIN_HASH: hashed.stdout.trim(),
    },
    stdio: "ignore",
  });
  const deadline = Date.now() + 20_000;
  while (Date.now() < deadline) {
    try {
      if ((await fetch(`${baseUrl}/api/system/health`)).ok) {
        useCookieJar();
        return;
      }
    } catch {
      /* 아직 뜨는 중 */
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("백엔드가 뜨지 않았습니다");
});

after(async () => {
  globalThis.fetch = realFetch;
  if (backend && backend.exitCode === null) {
    const exited = new Promise((resolve) => backend?.once("exit", resolve));
    backend.kill();
    await exited;
  }
  try {
    if (tempRoot) rmSync(tempRoot, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 });
  } catch {
    // Windows가 파일을 늦게 놓는 경우 — 임시 폴더라 남아도 테스트 결과와 무관하다
  }
});

test("가짜 실행이 SSE로 화면 상태까지 이어지고, 끊겼다 다시 붙어도 상태가 같다", { skip }, async () => {
  const service = new HttpWorkspaceService(baseUrl);
  // 로그인 전(Guest)에는 만들 수 없다 — 백엔드가 막는다
  await assert.rejects(service.createProject({ name: "x", mode: "auto" }), /Owner/);
  await assert.rejects(service.login("000000"), /PIN이 올바르지 않습니다/);
  const session = await service.login(TEST_PIN);
  assert.equal(session.authenticated, true);
  const project = await service.createProject({ name: "통합 테스트", mode: "auto" });
  await service.sendMessage(project.id, "주거 정책 보고서를 써줘");

  let state: ProjectWorkspace = await service.getWorkspace(project.id);
  const listen = () =>
    service.subscribe(project.id, state.lastEventSeq, {
      onEvent: (event) => {
        state = applyWorkflowEvent(state, event);
      },
    });
  let unsubscribe = listen();

  await service.runWorkflow(project.id);
  const request = await waitFor(() => state.pendingInputs[0]);
  assert.equal(state.runStatus, "awaitingInput");
  assert.equal(state.project.mode, "document");

  // 연결을 끊은 채 진행시키고, 마지막 seq부터 다시 붙는다(빠진 이벤트 replay)
  unsubscribe();
  await service.respondToInput(project.id, request.promptId, "네, 진행하세요");
  await new Promise((resolve) => setTimeout(resolve, 400));
  unsubscribe = listen();

  await waitFor(() => state.runStatus === "completed");
  unsubscribe();
  assert.equal(computeProgress(state.stageStatus), 100);

  const fresh = await service.getWorkspace(project.id);
  assert.equal(state.lastEventSeq, fresh.lastEventSeq);
  assert.equal(state.feed.length, fresh.feed.length);
  assert.deepEqual(state.stageStatus, fresh.stageStatus);
  assert.ok(state.artifacts.some((artifact) => artifact.name === "07_final_document.md"));

  const final = state.artifacts.find((artifact) => artifact.fileType === "pdf" && artifact.visibility === "primary");
  assert.ok(final);
  const content = await service.getArtifactContent(project.id, final.id);
  assert.equal(content?.type, "pdf");
});
