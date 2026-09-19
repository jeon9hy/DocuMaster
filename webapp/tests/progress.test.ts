import { test } from "node:test";
import assert from "node:assert/strict";
import { createStageStatusMap } from "@/constants/workflow";
import { computeProgress, getFocusStageId, isWorkflowComplete } from "@/lib/progress";

test("진행률: 완료 1 · 진행 0.5 · 대기/오류 0 (2개 완료 + 3번째 진행 = 42%)", () => {
  const status = createStageStatusMap({ requirements: "completed", planning: "completed", research: "running" });
  assert.equal(computeProgress(status), 42);
  assert.equal(computeProgress(createStageStatusMap()), 0);
  assert.equal(computeProgress(createStageStatusMap({ research: "error" })), 0);
});

test("지금 볼 단계: 오류 → 진행 중 → 첫 대기", () => {
  assert.equal(getFocusStageId(createStageStatusMap({ requirements: "completed" })), "planning");
  assert.equal(getFocusStageId(createStageStatusMap({ writing: "running", research: "error" })), "research");
});

test("모든 단계가 완료일 때만 완료", () => {
  const all = createStageStatusMap({
    requirements: "completed", planning: "completed", research: "completed",
    validation: "completed", writing: "completed", finalReview: "completed",
  });
  assert.equal(isWorkflowComplete(all), true);
  assert.equal(isWorkflowComplete({ ...all, finalReview: "running" }), false);
});
