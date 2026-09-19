import { test } from "node:test";
import assert from "node:assert/strict";
import { selectStageContext } from "@/lib/stageContext";
import { buildWorkspace } from "@/lib/workspace";
import { PROJECT, toEvents } from "./helpers";

test("단계별 최소 Context: 읽는 단계의 최신 작업물과 필요할 때만 레퍼런스", () => {
  const artifact = (id: string, stageId: "research" | "validation", status: "latest" | "writing") => ({
    type: "artifact.created" as const,
    artifact: { id, name: id, fileType: "markdown" as const, status, stageId, agentId: "yor" as const, summary: "" },
  });
  const workspace = buildWorkspace(PROJECT, toEvents([
    artifact("02", "research", "latest"),
    artifact("05", "validation", "latest"),
    artifact("05b", "validation", "writing"),
    { type: "reference.added", reference: { id: "r1", name: "a.pdf", kind: "pdf", detail: "", applyPolicy: "nextStage" } },
  ]));
  const writing = selectStageContext(workspace, "writing");
  assert.deepEqual(writing.artifacts.map((a) => a.id), ["05"]);
  assert.equal(writing.references.length, 0);
  assert.equal(selectStageContext(workspace, "research").references.length, 1);
});
