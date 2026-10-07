import { test } from "node:test";
import assert from "node:assert/strict";
import { cumulativeSeries, dayRange, lastDays } from "@/lib/trends";
import type { LibraryDocument } from "@/types";

function doc(workspaceId: string, kind: string, date: string): LibraryDocument {
  return { projectId: workspaceId, workspaceId, title: workspaceId, request: "", kind, mode: "document", date, fileName: null, artifactId: null };
}

const DOCS = [doc("a", "분석", "2026-10-01"), doc("b", "발표", "2026-10-01"), doc("c", "안내절차", "2026-10-03")];

test("날짜 범위는 월 경계를 넘어도 하루씩 이어진다", () => {
  assert.deepEqual(dayRange("2026-09-29", "2026-10-02"), ["2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02"]);
});

test("누적 추이: 첫 문서 날부터 오늘까지, 빈 날도 이어서 센다", () => {
  const series = cumulativeSeries(DOCS, "2026-10-04");
  assert.deepEqual(series.map((p) => p.total), [2, 2, 3, 3]);
  assert.deepEqual(series.map((p) => p.added), [2, 0, 1, 0]);
  assert.deepEqual(cumulativeSeries([], "2026-10-04"), []);
});

test("최근 N일: 오늘 포함 N칸, 날짜별 문서", () => {
  const week = lastDays(DOCS, 3, "2026-10-03");
  assert.deepEqual(week.map((b) => b.date), ["2026-10-01", "2026-10-02", "2026-10-03"]);
  assert.deepEqual(week.map((b) => b.documents.length), [2, 0, 1]);
});
