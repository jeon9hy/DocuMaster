import { test } from "node:test";
import assert from "node:assert/strict";
import { EMPTY_LIBRARY_FILTER } from "@/constants/library";
import { daysAgo, filterLibrary, groupByMonth, splitFinalArtifacts } from "@/lib/library";
import { emptyWorkspace } from "@/lib/workspace";
import { appReducer, initialAppState } from "@/state/appReducer";
import type { Artifact, LibraryDocument } from "@/types";
import { PROJECT } from "./helpers";

function doc(workspaceId: string, title: string, kind: string, date: string, request = ""): LibraryDocument {
  return { projectId: workspaceId, workspaceId, title, request, kind, mode: "document", date, fileName: null, artifactId: null };
}

const DOCS = [
  doc("포켓몬스터의역사_20261001", "포켓몬스터의 역사와 인기 이유", "서사소개", "2026-10-01"),
  doc("최저임금2026_20260920", "2026년 최저임금 해설", "설명해설", "2026-09-20", "최저임금 알려줘"),
  doc("렘_20260918", "렘 캐릭터 소개", "발표", "2026-09-18"),
];

test("라이브러리 필터: 제목은 띄어쓰기·대소문자 무시, 요청 내용도 찾는다", () => {
  const ids = (title: string) => filterLibrary(DOCS, { ...EMPTY_LIBRARY_FILTER, title }).map((d) => d.workspaceId);
  assert.deepEqual(ids("포켓몬스터의역사"), ["포켓몬스터의역사_20261001"]);
  assert.deepEqual(ids("알려줘"), ["최저임금2026_20260920"]);
  assert.equal(ids("").length, 3);
});

test("라이브러리 필터: 날짜 양 끝 포함 · 유형 여러 개 · 조건은 함께 적용", () => {
  const range = filterLibrary(DOCS, { ...EMPTY_LIBRARY_FILTER, dateFrom: "2026-09-18", dateTo: "2026-09-20" });
  assert.deepEqual(range.map((d) => d.date), ["2026-09-20", "2026-09-18"]);
  const kinds = filterLibrary(DOCS, { ...EMPTY_LIBRARY_FILTER, kinds: ["발표", "서사소개"] });
  assert.equal(kinds.length, 2);
  const both = filterLibrary(DOCS, { ...EMPTY_LIBRARY_FILTER, kinds: ["발표", "서사소개"], dateTo: "2026-09-30" });
  assert.deepEqual(both.map((d) => d.kind), ["발표"]);
});

test("월별 묶음과 최근 N일", () => {
  assert.deepEqual(groupByMonth(DOCS).map((g) => [g.label, g.items.length]), [["2026년 10월", 1], ["2026년 9월", 2]]);
  assert.equal(daysAgo(7, new Date(2026, 9, 1)), "2026-09-25");
});

test("라이브러리에서 연 문서는 워크스페이스가 로드되면 그 작업물이 선택된다", () => {
  const opened = appReducer(initialAppState, { type: "library/opened", projectId: PROJECT.id, artifactId: "a2" });
  assert.equal(opened.view, "artifacts");
  assert.equal(opened.projectId, PROJECT.id);
  const workspace = {
    ...emptyWorkspace(PROJECT),
    artifacts: ["a1", "a2", "a3"].map((id) => ({
      id, name: id, fileType: "pdf" as const, status: "latest" as const, stageId: "finalReview" as const,
      agentId: "loid" as const, summary: "", updatedAt: "",
    })),
  };
  const loaded = appReducer(opened, { type: "workspace/loaded", workspace });
  assert.equal(loaded.selectedArtifactId, "a2");
  assert.equal(loaded.pendingArtifactId, null);
});

test("최종본 나누기: 최종 폴더 파일만 위로, PDF 먼저 · 이전판은 따로 최근 것부터 · 렌더 결과와 대기 자리는 작업물", () => {
  const artifact = (id: string, stageId: Artifact["stageId"], extra: Partial<Artifact> = {}): Artifact => ({
    id, name: id, fileType: "markdown", status: "latest", stageId, agentId: "loid", summary: "", updatedAt: "2026-10-01T00:00:00Z", ...extra,
  });
  const { finals, previous, others } = splitFinalArtifacts([
    artifact("00", "requirements"),
    artifact("render", "finalReview", { visibility: "internal", fileType: "pdf" }),
    artifact("pack", "finalReview", { visibility: "primary" }),
    artifact("doc", "finalReview", { visibility: "primary", fileType: "pdf" }),
    artifact("slot", "finalReview", { status: "pending", fileType: "pdf" }),
    artifact("doc_v01", "finalReview", { visibility: "internal", fileType: "pdf", summary: "이전 최종본 · v01" }),
    artifact("doc_v02", "finalReview", { visibility: "internal", fileType: "pdf", summary: "이전 최종본 · v02" }),
  ]);
  assert.deepEqual(finals.map((a) => a.id), ["doc", "pack"]);
  assert.deepEqual(previous.map((a) => a.id), ["doc_v02", "doc_v01"]);
  assert.deepEqual(others.map((a) => a.id), ["00", "render", "slot"]);
});
