import { EVENT_SCHEMA_VERSION } from "@/types/events";
import type { ProjectSummary, WorkflowEvent, WorkflowEventPayload } from "@/types";

export const PROJECT: ProjectSummary = { id: "p1", name: "테스트", description: "", mode: "auto" };

/** payload 목록에 seq를 1부터 붙여 이벤트로 만든다 */
export function toEvents(payloads: WorkflowEventPayload[], startSeq = 1): WorkflowEvent[] {
  return payloads.map((payload, index) => ({
    ...payload,
    schemaVersion: EVENT_SCHEMA_VERSION,
    id: `e${startSeq + index}`,
    projectId: PROJECT.id,
    runId: "run1",
    seq: startSeq + index,
    at: new Date(Date.UTC(2026, 8, 19, 0, 0, startSeq + index)).toISOString(),
  }));
}
