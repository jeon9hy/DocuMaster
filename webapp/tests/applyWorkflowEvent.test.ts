import { test } from "node:test";
import assert from "node:assert/strict";
import { applyWorkflowEvent } from "@/lib/applyWorkflowEvent";
import { buildWorkspace, emptyWorkspace } from "@/lib/workspace";
import { PROJECT, toEvents } from "./helpers";

test("실행 상태: 시작 → 입력 필요 → 응답 → 중지 요청 → 중지", () => {
  const request = { promptId: "q1", title: "검증 보류", message: "핵심 주장 A 확인 불가", choices: ["제거 후 계속"], allowFreeText: true };
  const steps = toEvents([
    { type: "workflow.started" },
    { type: "workflow.stage.started", stageId: "validation" },
    { type: "user.input.required", request },
    { type: "user.input.resolved", promptId: "q1", answer: "제거 후 계속" },
    { type: "workflow.stop.requested" },
    { type: "workflow.stopped", stageId: "validation" },
  ]);
  const seen = [];
  let workspace = emptyWorkspace(PROJECT);
  for (const event of steps) {
    workspace = applyWorkflowEvent(workspace, event);
    seen.push(workspace.runStatus);
  }
  assert.deepEqual(seen, ["running", "running", "awaitingInput", "running", "stopping", "stopped"]);
  assert.equal(workspace.pendingInputs.length, 0);
  // 진행 중이던 단계는 대기로 돌아가 다음 실행 때 이어서 한다
  assert.equal(workspace.stageStatus.validation, "pending");
  assert.equal(workspace.lastEventSeq, 6);
});

test("같은 seq를 두 번 받아도 한 번만 반영한다(재연결 중복 대비)", () => {
  const [started, message] = toEvents([{ type: "workflow.started" }, { type: "user.message", text: "안녕" }]);
  let workspace = emptyWorkspace(PROJECT);
  workspace = applyWorkflowEvent(workspace, started);
  workspace = applyWorkflowEvent(workspace, message);
  const again = applyWorkflowEvent(workspace, message);
  assert.equal(again, workspace);
  assert.equal(workspace.feed.filter((item) => item.kind === "user").length, 1);
});

test("실제 발언과 도구 활동이 도착 순서대로 대화 피드에 붙는다", () => {
  const events = toEvents([
    { type: "agent.message", agentId: "loid", toAgentId: "yuri", text: "자료를 확인하겠습니다." },
    { type: "agent.activity", agentId: "loid", label: "파일 읽기 · 자료.pdf" },
    { type: "agent.message", agentId: "yuri", text: "출처를 다시 확인해야 합니다." },
  ]);
  const workspace = buildWorkspace(PROJECT, events);
  assert.deepEqual(workspace.feed.map((item) => item.kind), ["agent", "activity", "agent"]);
  assert.equal(workspace.feed[1].kind === "activity" && workspace.feed[1].label, "파일 읽기 · 자료.pdf");
  assert.equal(workspace.feed[0].kind === "agent" && workspace.feed[0].toAgentId, "yuri");
  assert.equal(workspace.lastEventSeq, 3);
});

test("자동 판정: 모드가 정해지면 그 모드의 팀으로 바뀐다", () => {
  let workspace = emptyWorkspace(PROJECT);
  assert.equal(workspace.agents.length, 5);
  workspace = buildWorkspace(PROJECT, toEvents([{ type: "project.mode.decided", mode: "presentation" }]));
  assert.equal(workspace.project.mode, "presentation");
  assert.deepEqual(workspace.agents.map((agent) => agent.id), ["loid", "yor", "yuri", "bond"]);
});

test("작업물: 내부 작업물 카드는 접힘(detail)으로, 주요 작업물은 그대로", () => {
  const base = { status: "latest" as const, stageId: "validation" as const, agentId: "yuri" as const, summary: "", fileType: "markdown" as const };
  const workspace = buildWorkspace(PROJECT, toEvents([
    { type: "artifact.created", artifact: { ...base, id: "a3", name: "03_verification_questions.md", visibility: "internal" } },
    { type: "artifact.created", artifact: { ...base, id: "a5", name: "05_verified_research_pack.md" } },
  ]));
  const cards = workspace.feed.filter((item) => item.kind === "artifact");
  assert.deepEqual(cards.map((item) => item.importance), ["detail", undefined]);
});

test("검증 판정·레퍼런스 추가/삭제", () => {
  const workspace = buildWorkspace(PROJECT, toEvents([
    { type: "validation.verdict", verdict: "blocked", firstLine: "검증 보류 — 확인 불가" },
    { type: "reference.added", reference: { id: "r1", name: "a.pdf", kind: "pdf", detail: "PDF", applyPolicy: "nextStage" } },
    { type: "reference.removed", referenceId: "r1" },
  ]));
  const verdict = workspace.feed[0];
  assert.equal(verdict.kind === "system" && verdict.tone, "error");
  assert.equal(workspace.references.length, 0);
});

test("같은 파일 갱신과 같은 검증 판정은 피드에 반복 표시하지 않는다", () => {
  const base = { id: "a5", name: "05_verified_research_pack.md", fileType: "markdown" as const,
    status: "latest" as const, stageId: "validation" as const, agentId: "yuri" as const,
    summary: "검증 결과", visibility: "primary" as const };
  const workspace = buildWorkspace(PROJECT, toEvents([
    { type: "artifact.created", artifact: base },
    { type: "validation.verdict", verdict: "conditional", firstLine: "검증 통과 — 조건부" },
    { type: "artifact.updated", artifactId: "a5", status: "latest", visibility: "primary", summary: "수정됨" },
    { type: "validation.verdict", verdict: "conditional", firstLine: "검증 통과 — 조건부" },
  ]));
  assert.equal(workspace.feed.filter((item) => item.kind === "artifact").length, 1);
  assert.equal(workspace.feed.filter((item) => item.kind === "system" && item.title.startsWith("05 검증 결과:")).length, 1);
  assert.equal(workspace.artifacts[0].summary, "수정됨");
});
